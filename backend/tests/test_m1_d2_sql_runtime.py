"""Runtime SQL contracts; real MCP transport, stub models/executors, no PG server."""
from copy import deepcopy
from dataclasses import replace
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import sqlglot

from app.config import settings
from app.database import SCHEMA, RELATIONS
from app.datasources import DataSourceRuntime
from app.datasources.contracts import CatalogSnapshot, SourceIdentity
from app.datasources.dialects import dialect_for_backend
from app.errors import PipelineStageError
from app.mcp_runtime import LocalMcpClient, create_local_mcp_server
from app.querying.constraint_planner import ConstraintPlanner, ConstraintPlan
from app.querying.constraint_validator import ConstraintValidator
from app.querying.metric_planner import MetricPlanner, MetricPlan
from app.querying.models import SqlExecution
from app.querying.single_database_agent import SingleDatabaseAgent
from app.querying.sql_context import SqlContext
from app.querying.sql_validator import SQLValidator
from app.retrieval import SchemaGraphBuilder
from app.security import AccessController
from app.skills import SkillRegistry
from app.workflows.query_graph import QueryWorkflow


DATABASE = "short_video_ops"


class D2SqlRuntimeTest(unittest.TestCase):
    def make_runtime(self, backend="postgresql", tables=None):
        catalog = CatalogSnapshot(json.dumps({"tables": tables or deepcopy(SCHEMA),
            "relations": deepcopy(RELATIONS)}, ensure_ascii=False, sort_keys=True))
        d = dialect_for_backend(backend)
        identity = SourceIdentity(DATABASE, "d2_" + backend, backend, d.parser, d.prompt,
            "askdata_ops" if backend == "postgresql" else "main", catalog.version, "2"*64)
        executor = Mock(source_identity=identity)
        executor.execute.side_effect = lambda database, sql, *args, **kwargs: SqlExecution(
            sql=sql, success=True, columns=["pg_only_value"], rows=[])
        runtime = DataSourceRuntime(identity, catalog, executor,
            SimpleNamespace(load_catalog=lambda: catalog))
        self.addCleanup(runtime.close)
        return runtime

    def setUp(self):
        tables = deepcopy(SCHEMA)
        users = next(t for t in tables if t["name"] == "users")
        self.removed_field = next(f["name"] for f in users["fields"] if f["name"] != "user_id")
        users["fields"] = [f for f in users["fields"] if f["name"] != self.removed_field]
        users["fields"].append({"name": "pg_reviewed_at", "type": "时间", "label": "复核时间"})
        registrations = next(t for t in tables if t["name"] == "user_registrations")
        registrations["fields"].append({"name": "pg_only_value", "type": "文本", "label": "测试值"})
        self.runtime = self.make_runtime(tables=tables)
        self.graph = {"source_identity": self.runtime.identity.public(),
            "database": DATABASE,
            "tables": [{"id": t["id"], "name": t["name"], "label": t["label"], "description": t["description"]}
                       for t in self.runtime.catalog.tables], "fields": [], "joins": []}
        self.scope = AccessController().resolve("demo_growth_ops")

    def validate(self, sql, graph=None, scope=None):
        return SQLValidator(runtime=self.runtime).validate(sql, DATABASE,
            self.graph if graph is None else graph, scope)

    def agent(self, sqls, runtime=None):
        runtime = runtime or self.runtime
        model = Mock()
        model.chat_json.side_effect = [{"action": "call_tool", "tool_name": "query_short_video_ops",
            "arguments": {"sql": sql}, "query_contract": {}} for sql in sqls]
        client = LocalMcpClient(create_local_mcp_server(runtime=runtime, access_scope=self.scope))
        return SingleDatabaseAgent(model, lambda scope: client,
            SkillRegistry().get("database_query"), runtime=runtime), model

    def prepare(self, agent, graph=None):
        return agent.prepare("查看注册明细", DATABASE, self.graph if graph is None else graph,
            "", {}, {}, self.scope.public())

    def test_runtime_field_absent_from_retrieval_passes(self):
        result = self.validate("SELECT pg_only_value FROM askdata_ops.user_registrations", {"tables": []})
        self.assertEqual(result.status, "PASS")

    def test_removed_static_field_and_forged_graph_field_are_blocked(self):
        graph = {"tables": [{"name": "users", "fields": [self.removed_field]}]}
        result = self.validate(f"SELECT u.{self.removed_field} FROM users u", graph)
        self.assertEqual(result.status, "BLOCK")
        self.assertIn(f"u.{self.removed_field}", result.invalid_columns)

    def test_postgres_cast_and_cte_columns_pass(self):
        sql = ("WITH d AS (SELECT registered_at::date AS day FROM askdata_ops.user_registrations) "
               "SELECT d.day, COUNT(*) AS total FROM d GROUP BY d.day ORDER BY d.day")
        self.assertEqual(self.validate(sql).status, "PASS")

    def test_wrong_namespace_unknown_table_and_write_are_blocked(self):
        for sql in ("SELECT user_id FROM main.users", "SELECT user_id FROM short_video_ops.users",
                    "SELECT user_id FROM other.users", "SELECT user_id FROM db.askdata_ops.users",
                    "SELECT user_id FROM unknown_table", "SELECT * FROM users",
                    "DELETE FROM users", "SELECT user_id FROM users; SELECT user_id FROM users"):
            with self.subTest(sql=sql):
                self.assertEqual(self.validate(sql).status, "BLOCK")

    def test_allowed_schema_and_aliases_pass_on_both_backends(self):
        for backend in ("postgresql", "duckdb"):
            runtime = self.make_runtime(backend)
            schema = runtime.identity.physical_schema
            result = SQLValidator(runtime=runtime).validate(
                f"SELECT u.user_id FROM {schema}.users u ORDER BY u.user_id", DATABASE, {})
            self.assertEqual(result.status, "PASS")

    def test_denied_application_table_is_blocked_before_execution(self):
        self.assertEqual(self.validate("SELECT content_id FROM contents", scope=self.scope).status, "BLOCK")
        self.runtime.executor.execute.assert_not_called()

    def test_sql_parser_reads_runtime_dialect(self):
        for backend in ("duckdb", "postgresql"):
            runtime = self.make_runtime(backend)
            with patch("app.querying.sql_validator.sqlglot.parse", wraps=sqlglot.parse) as parse:
                SQLValidator(runtime=runtime).validate("SELECT user_id FROM users", DATABASE, {})
            self.assertTrue(parse.call_args_list)
            self.assertTrue(all(c.kwargs.get("read") == runtime.identity.dialect for c in parse.call_args_list))

    def test_metric_catalog_cannot_fall_back_to_static_fields(self):
        tables = deepcopy(SCHEMA)
        table = next(t for t in tables if t["name"] == "growth_daily_metrics")
        table["fields"] = [f for f in table["fields"] if f["name"] != "new_users"]
        runtime = self.make_runtime(tables=tables)
        with self.assertRaisesRegex(ValueError, "new_users"):
            MetricPlanner(runtime=runtime)

    def test_metric_parser_and_metric_sources_follow_runtime(self):
        planner = MetricPlanner(runtime=self.runtime)
        plan = planner.plan("新增用户数", self.graph)
        self.assertTrue(plan.metrics)
        with patch("app.querying.metric_planner.sqlglot.parse_one", wraps=sqlglot.parse_one) as parse:
            errors = planner.validate_sql(
                "SELECT SUM(g.new_users)::numeric FROM askdata_ops.growth_daily_metrics g", plan)
        self.assertEqual(errors, [])
        self.assertEqual(parse.call_args.kwargs["read"], "postgres")
        self.assertTrue(planner.validate_sql("SELECT COUNT(*) FROM users", plan))

    def test_detail_date_resolution_uses_full_runtime_catalog(self):
        planner = ConstraintPlanner(runtime=self.runtime)
        graph = {**self.graph, "tables": [{"name": "users"}]}
        with patch("app.querying.constraint_planner.sqlglot.parse_one", wraps=sqlglot.parse_one) as parse:
            plan = planner.plan_for_sql("2026-01-02复核时间明细", MetricPlan(), graph,
                "SELECT pg_reviewed_at::date FROM askdata_ops.users")
        self.assertEqual(parse.call_args.kwargs["read"], "postgres")
        self.assertEqual(plan.time_field_resolution["selected_fields"], ["users.pg_reviewed_at"])

    def test_date_resolution_does_not_expand_outside_sql_sources(self):
        planner = ConstraintPlanner(runtime=self.runtime)
        graph = {**self.graph, "tables": [{"name": "users"}, {"name": "user_registrations"}]}
        plan = planner.plan_for_sql("2026-01-02复核时间明细", MetricPlan(), graph,
            "SELECT user_id FROM user_registrations")
        self.assertEqual(plan.time_field_resolution["selected_fields"], [])

    def test_day_predicate_resolves_runtime_only_unqualified_field(self):
        plan = ConstraintPlan(time_constraints=[{"field": "users.pg_reviewed_at",
            "operator": "day_equals", "value": "2026-01-02"}])
        validator = ConstraintValidator(runtime=self.runtime)
        result = validator.validate("SELECT user_id FROM askdata_ops.users "
            "WHERE pg_reviewed_at >= TIMESTAMP '2026-01-02' AND pg_reviewed_at < TIMESTAMP '2026-01-03'",
            DATABASE, plan)
        self.assertEqual(result.status, "PASS")
        result = validator.validate("SELECT user_id FROM users WHERE pg_reviewed_at >= '2026-01-02'",
            DATABASE, plan)
        self.assertEqual(result.status, "BLOCK")

    def test_postgres_to_char_month_and_day_grouping(self):
        validator = ConstraintValidator(runtime=self.runtime)
        month = ConstraintPlan(time_constraints=[{"field": "user_registrations.registered_at",
            "operator": "month_equals", "value": "2026-01"}])
        sql = "SELECT COUNT(*) FROM askdata_ops.user_registrations WHERE to_char(registered_at,'YYYY-MM')='2026-01'"
        with patch("app.querying.constraint_validator.sqlglot.parse", wraps=sqlglot.parse) as parse:
            result = validator.validate(sql, DATABASE, month)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(parse.call_args.kwargs["read"], "postgres")
        day = ConstraintPlan(group_constraints=[{"field": "user_registrations.registered_at", "grain": "day"}])
        for expr in ("to_char(registered_at,'YYYY-MM-DD')", "date_trunc('day', registered_at)"):
            self.assertEqual(validator.validate(
                f"SELECT {expr} AS day, COUNT(*) FROM user_registrations GROUP BY day", DATABASE, day).status, "PASS")
        self.assertEqual(validator.validate(
            "SELECT to_char(registered_at,'YYYY-MM') AS day, COUNT(*) FROM user_registrations GROUP BY day",
            DATABASE, day).status, "BLOCK")

    def test_closed_runtime_is_rejected_even_without_metrics_or_constraints(self):
        validators = (SQLValidator(runtime=self.runtime), MetricPlanner(runtime=self.runtime),
                      ConstraintPlanner(runtime=self.runtime), ConstraintValidator(runtime=self.runtime))
        self.runtime.close()
        calls = (lambda: validators[0].validate("SELECT 1", DATABASE, {}),
                 lambda: validators[1].validate_sql("SELECT 1", MetricPlan()),
                 lambda: validators[2].plan("query", MetricPlan(), {}),
                 lambda: validators[3].validate("SELECT 1", DATABASE, ConstraintPlan()))
        for call in calls:
            with self.assertRaisesRegex(RuntimeError, "closed"):
                call()

    def test_wrong_database_and_contradictory_dialect_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "database"):
            SQLValidator(runtime=self.runtime).validate("SELECT 1", "other", {})
        bad = replace(self.runtime.identity, dialect="duckdb")
        executor = Mock(source_identity=bad)
        runtime = DataSourceRuntime(bad, self.runtime.catalog, executor, self.runtime.metadata)
        self.addCleanup(runtime.close)
        with self.assertRaisesRegex(ValueError, "dialect"):
            SqlContext(runtime)

    def test_postgres_graph_without_runtime_has_no_duckdb_fallback(self):
        for call in (lambda: SQLValidator().validate("SELECT user_id FROM users", DATABASE, self.graph),
                     lambda: MetricPlanner().plan("查看明细", self.graph),
                     lambda: ConstraintPlanner().plan("查看明细", MetricPlan(), self.graph)):
            with self.assertRaisesRegex(ValueError, "explicit runtime"):
                call()

    def test_sql_and_planners_reject_mixed_graph_identity(self):
        graph = {**self.graph, "source_identity": self.make_runtime("duckdb").identity.public()}
        for call in (lambda: SQLValidator(runtime=self.runtime).validate("SELECT user_id FROM users", DATABASE, graph),
                     lambda: MetricPlanner(runtime=self.runtime).plan("查看明细", graph),
                     lambda: ConstraintPlanner(runtime=self.runtime).plan("查看明细", MetricPlan(), graph)):
            with self.assertRaisesRegex(ValueError, "datasource mismatch"):
                call()

    def test_agent_prompt_tools_and_validators_share_runtime(self):
        agent, model = self.agent(["SELECT pg_only_value FROM askdata_ops.user_registrations"])
        result = self.prepare(agent)
        self.runtime.assert_shared(agent, agent.sql_validator, agent.metric_planner,
                                   agent.constraint_planner, agent.constraint_validator)
        system, payload = model.chat_json.call_args.args
        payload = json.loads(payload)
        self.assertIn("PostgreSQL", system)
        self.assertIn("askdata_ops", system)
        self.assertNotIn("DuckDB", system)
        self.assertEqual(payload["sql_context"], self.runtime.identity.public())
        trace = result["tool_trace"][0]
        self.assertEqual(trace["sql_context"], self.runtime.identity.public())
        self.assertEqual(trace["sql_validation"]["status"], "PASS")
        self.runtime.executor.execute.assert_called_once()

    def test_invalid_sql_is_repaired_before_real_mcp_call(self):
        agent, model = self.agent(["SELECT registered_at FROM main.user_registrations",
                                  "SELECT pg_only_value FROM askdata_ops.user_registrations"])
        result = self.prepare(agent)
        self.assertEqual(model.chat_json.call_count, 2)
        self.runtime.executor.execute.assert_called_once()
        self.assertEqual([i["status"] for i in result["tool_trace"][0]["sql_validation_attempts"]],
                         ["BLOCK", "PASS"])

    def test_postgres_nested_order_alias_is_expanded_before_tool_call(self):
        sql = ("SELECT SUM(g.new_users) AS total_users "
               "FROM askdata_ops.growth_daily_metrics g "
               "ORDER BY ABS(total_users) DESC")
        validator = SQLValidator(runtime=self.runtime)
        blocked = validator.validate(sql, DATABASE, self.graph)
        self.assertEqual(blocked.status, "BLOCK")
        self.assertIn("PostgreSQL ORDER BY expression cannot use SELECT alias",
                      blocked.errors[0])
        repaired = validator.repair_postgres_nested_order_aliases(sql, DATABASE, self.graph)
        self.assertNotEqual(repaired, sql)
        self.assertIn("ABS(SUM(g.new_users))", repaired)
        self.assertEqual(validator.validate(repaired, DATABASE, self.graph).status, "PASS")
        self.assertEqual(validator.validate(
            sql.replace("ABS(total_users)", "total_users"), DATABASE, self.graph,
        ).status, "PASS")

        agent, model = self.agent([sql])
        result = self.prepare(agent)
        self.assertEqual(model.chat_json.call_count, 1)
        self.runtime.executor.execute.assert_called_once()
        trace = result["tool_trace"][0]
        self.assertEqual(trace["sql_order_alias_repair"]["original_sql"], sql)
        self.assertEqual(trace["sql_validation"]["status"], "PASS")
        self.assertEqual([attempt["status"] for attempt in trace["sql_validation_attempts"]],
                         ["BLOCK", "PASS"])

    def test_repeated_wrong_schema_never_executes(self):
        agent, model = self.agent(["SELECT registered_at FROM main.user_registrations"]*3)
        with self.assertRaises(PipelineStageError):
            self.prepare(agent)
        self.assertEqual(model.chat_json.call_count, 3)
        self.runtime.executor.execute.assert_not_called()

    def test_mixed_graph_is_rejected_before_model_or_tool_call(self):
        agent, model = self.agent(["SELECT registered_at FROM user_registrations"])
        with self.assertRaisesRegex(ValueError, "datasource mismatch"):
            self.prepare(agent, {**self.graph, "source_identity": self.make_runtime("duckdb").identity.public()})
        model.chat_json.assert_not_called()
        self.runtime.executor.execute.assert_not_called()

    def test_mcp_tool_schema_and_graph_text_describe_physical_namespace(self):
        client = LocalMcpClient(create_local_mcp_server(runtime=self.runtime, access_scope=self.scope))
        tool = next(t for t in client.list_tools() if t["name"] == "query_short_video_ops")
        for text in (tool["description"], tool["input_schema"]["properties"]["sql"]["description"],
                     SchemaGraphBuilder.context_text(self.graph)):
            self.assertIn("PostgreSQL", text)
            self.assertIn("askdata_ops", text)
            self.assertIn("业务数据库ID", text)
            self.assertNotIn("DuckDB", text)

    def test_workflow_execution_report_uses_runtime_backend_and_graph_labels(self):
        workflow = QueryWorkflow(Mock(), SimpleNamespace(runtime=self.runtime),
            replace(settings, time_field_supplement_enabled=False), runtime=self.runtime)
        workflow.response_generator.finalize = Mock(return_value={"valid": True, "analysis": "empty"})
        graph = {**self.graph, "tables": [{"id": "short_video_ops.users", "name": "users", "label": "实时用户表"}]}
        state = {"task_id": "d2", "standalone_query": "查看明细", "schema_graph": graph,
            "schema_context": "", "source_identity": self.runtime.identity.public(),
            "mcp_execution": {"sql": "SELECT user_id FROM users", "success": True, "columns": ["user_id"], "rows": []}}
        result = workflow._execute_single_database(state)
        log = result["execution_log"][-1]
        self.assertEqual(log["stage"], "sql_execution")
        self.assertEqual(log["backend"], "postgresql")
        self.assertEqual(log["dialect"], "postgres")
        self.assertEqual(log["source_identity"], self.runtime.identity.public())
        self.assertIn("PostgreSQL", " ".join(result["result"]["steps"]))
        self.assertNotIn("DuckDB", " ".join(result["result"]["steps"]))
        self.assertEqual(result["result"]["interpretation"]["table"], "实时用户表")


if __name__ == "__main__":
    unittest.main()
