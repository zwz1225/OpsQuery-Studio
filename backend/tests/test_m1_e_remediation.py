"""Regressions from the first PostgreSQL live and service-entry reports."""

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from app.database import SCHEMA, RELATIONS
from app.datasources import DataSourceRuntime
from app.datasources.contracts import CatalogSnapshot, SourceIdentity
from app.errors import PipelineStageError
from app.querying.constraint_planner import ConstraintPlanner
from app.querying.constraint_validator import ConstraintValidator
from app.querying.duckdb_engine import DuckDbEngine
from app.querying.metric_planner import MetricPlan, MetricPlanner
from app.querying.single_database_agent import SingleDatabaseAgent
from app.querying.sql_validator import SQLValidator
from app.security import AccessController
from app.skills import SkillDefinition
from evaluation.run_benchmark import load_cases, run_live_case
from evaluation.run_benchmark import compare_results_strict
from scripts.check_m1_d3_duckdb_compatibility import diagnostic_sql


BASE = Path(__file__).resolve().parents[1]
CASE_ROWS = {row["case_id"]: row for row in load_cases(
    BASE / "evaluation/cases/all_cases.jsonl", set(), False,
)}
LIVE_ROWS = {
    row["case_id"]: row
    for name in ("m1_e_postgres_live_classic_server.json",
                 "m1_e_postgres_live_phase83_server.json")
    for row in json.loads((BASE / "evaluation/results" / name).read_text(encoding="utf-8"))["cases"]
}


class M1ERemediationTest(unittest.TestCase):
    def setUp(self):
        tables = deepcopy(SCHEMA)
        floating = {
            "growth_targets": {"activation_rate_target"},
            "ad_daily_stats": {"spend"},
            "channel_targets": {"target_cpa"},
        }
        for table in tables:
            for field in table["fields"]:
                if field["name"] in floating.get(table["name"], set()):
                    field["postgresql_type"] = "double precision"
                if table["name"] == "user_activations" and field["name"] == "is_activated":
                    field["postgresql_type"] = "bigint"
        catalog = CatalogSnapshot(json.dumps(
            {"tables": tables, "relations": deepcopy(RELATIONS)},
            ensure_ascii=False, sort_keys=True,
        ))
        identity = SourceIdentity(
            "short_video_ops", "test_postgres", "postgresql", "postgres",
            "PostgreSQL", "askdata_ops", catalog.version, "2" * 64,
        )
        executor = Mock(source_identity=identity)
        self.runtime = DataSourceRuntime(identity, catalog, executor,
                                         SimpleNamespace(load_catalog=lambda: catalog))
        self.addCleanup(self.runtime.close)
        self.graph = {
            "source_identity": identity.public(),
            "tables": [{"name": table["name"]} for table in tables],
        }

    def test_three_failed_postgres_round_expressions_are_blocked_before_execution(self):
        validator = SQLValidator(runtime=self.runtime)
        for case_id in ("GROWTH_OPS-150", "GROWTH_OPS-148", "CHANNEL_OPS-136"):
            with self.subTest(case_id=case_id):
                scope = AccessController().resolve("demo_" + CASE_ROWS[case_id]["scenario"])
                old = validator.validate(LIVE_ROWS[case_id]["generated_sql"],
                                         "short_video_ops", self.graph, scope)
                self.assertEqual(old.status, "BLOCK")
                self.assertTrue(any("ROUND" in error and "numeric" in error
                                    for error in old.errors))
                repaired_sql = validator.repair_postgres_round_numeric(
                    LIVE_ROWS[case_id]["generated_sql"],
                )
                self.assertNotEqual(repaired_sql, LIVE_ROWS[case_id]["generated_sql"])
                repaired = validator.validate(
                    repaired_sql, "short_video_ops", self.graph, scope,
                )
                self.assertNotEqual(repaired.status, "BLOCK", repaired.errors)
                gold = validator.validate(
                    CASE_ROWS[case_id]["gold_sql_by_dialect"]["postgres"],
                    "short_video_ops", self.graph, scope,
                )
                self.assertNotEqual(gold.status, "BLOCK", gold.errors)
        corrected = validator.validate(
            "SELECT ROUND(CAST(t.activation_rate_target + 1.0 AS numeric), 4) "
            "FROM askdata_ops.growth_targets t", "short_video_ops", self.graph,
            AccessController().resolve("demo_growth_ops"),
        )
        self.assertNotEqual(corrected.status, "BLOCK", corrected.errors)

    def test_wrong_population_retention_and_activity_period_are_rejected(self):
        metrics = MetricPlanner(runtime=self.runtime)
        planner = ConstraintPlanner(runtime=self.runtime)
        validator = ConstraintValidator(runtime=self.runtime)
        activation = CASE_ROWS["GROWTH_OPS-066"]
        plan = planner.plan(activation["query"], metrics.plan(activation["query"], self.graph), self.graph)
        self.assertEqual(validator.validate(
            LIVE_ROWS[activation["case_id"]]["generated_sql"], "short_video_ops",
            plan, activation["query"],
        ).status, "BLOCK")
        self.assertEqual(validator.validate(
            activation["gold_sql_by_dialect"]["postgres"], "short_video_ops",
            plan, activation["query"],
        ).status, "PASS")

        for case_id in ("GROWTH_OPS-076", "GROWTH_OPS-100"):
            with self.subTest(case_id=case_id):
                case = CASE_ROWS[case_id]
                metric_plan = metrics.plan(case["query"], self.graph)
                self.assertTrue(metrics.validate_sql(
                    LIVE_ROWS[case_id]["generated_sql"], metric_plan,
                ))
                self.assertEqual(metrics.validate_sql(
                    case["gold_sql_by_dialect"]["postgres"], metric_plan,
                ), [])
                if case_id == "GROWTH_OPS-100":
                    plan = planner.plan(case["query"], metric_plan, self.graph)
                    self.assertEqual(plan.time_constraints[0]["field"],
                                     "user_daily_activity.activity_date")

    def test_round_repair_is_used_before_model_tool_call(self):
        old_sql = LIVE_ROWS["GROWTH_OPS-150"]["generated_sql"]
        model = Mock()
        model.chat_json.return_value = {
            "action": "call_tool", "tool_name": "query_short_video_ops",
            "arguments": {"sql": old_sql}, "query_contract": {},
        }
        skill = SkillDefinition("database_query", "", "", ("query_*",), 3,
                                ("call_tool", "clarify"))
        agent = SingleDatabaseAgent(model, lambda *_: Mock(), skill,
                                    runtime=self.runtime)
        scope = AccessController().resolve("demo_growth_ops").public()
        empty_metric_plan = MetricPlan()
        no_constraints = agent.constraint_planner.plan(
            "show activation target", empty_metric_plan, self.graph,
        )
        decision = agent._validated_decision(
            "", {"database": "short_video_ops", "schema_graph": self.graph,
                 "access_scope": scope, "query": "show activation target",
                 "metric_plan": empty_metric_plan.to_dict()},
            {"query_short_video_ops"}, empty_metric_plan, no_constraints,
        )
        self.assertEqual(model.chat_json.call_count, 1)
        self.assertEqual(decision["sql_round_numeric_repair"]["original_sql"], old_sql)
        self.assertEqual(decision["arguments"]["sql"],
                         decision["sql_round_numeric_repair"]["repaired_sql"])
        self.assertNotEqual(decision["sql_validation"]["status"], "BLOCK")
        self.assertEqual(len(decision["sql_validation_attempts"]), 2)

    def test_growth051_bigint_boolean_is_repaired_before_tool_call(self):
        old_sql = LIVE_ROWS.get("GROWTH_OPS-051")
        if old_sql and old_sql.get("generated_sql"):
            self.skipTest("First-run 051 unexpectedly has a candidate SQL")
        diagnostic = json.loads((BASE / "evaluation/results/m1_e_growth051_diagnostic_server_v2.json")
                                .read_text(encoding="utf-8"))["cases"][0]
        invalid_sql = diagnostic["generated_sql"]
        validator = SQLValidator(runtime=self.runtime)
        scope = AccessController().resolve("demo_growth_ops")
        blocked = validator.validate(invalid_sql, "short_video_ops", self.graph, scope)
        self.assertEqual(blocked.status, "BLOCK")
        self.assertTrue(any("bigint Boolean" in error for error in blocked.errors))
        repaired_sql = validator.repair_postgres_bigint_boolean(invalid_sql)
        self.assertIn("ua.is_activated <> 0", repaired_sql)
        self.assertNotIn("ua.is_activated = TRUE", repaired_sql)
        self.assertNotEqual(validator.validate(
            repaired_sql, "short_video_ops", self.graph, scope,
        ).status, "BLOCK")

        model = Mock()
        model.chat_json.return_value = {
            "action": "call_tool", "tool_name": "query_short_video_ops",
            "arguments": {"sql": invalid_sql}, "query_contract": {},
        }
        skill = SkillDefinition("database_query", "", "", ("query_*",), 3,
                                ("call_tool", "clarify"))
        agent = SingleDatabaseAgent(model, lambda *_: Mock(), skill,
                                    runtime=self.runtime)
        empty = MetricPlan()
        constraints = agent.constraint_planner.plan("show activation", empty, self.graph)
        decision = agent._validated_decision(
            "", {"database": "short_video_ops", "schema_graph": self.graph,
                 "access_scope": scope.public(), "query": "show activation",
                 "metric_plan": empty.to_dict()},
            {"query_short_video_ops"}, empty, constraints,
        )
        self.assertEqual(model.chat_json.call_count, 1)
        self.assertEqual(decision["sql_bigint_boolean_repair"]["original_sql"], invalid_sql)
        self.assertIn("ua.is_activated <> 0", decision["arguments"]["sql"])

        # This checks the business values on the accepted CSV snapshot only;
        # PostgreSQL execution must still be verified on the server.
        case = CASE_ROWS["GROWTH_OPS-051"]
        engine = DuckDbEngine()
        with engine.connect("short_video_ops") as connection:
            connection.execute("CREATE SCHEMA askdata_ops")
            for table in ("user_registrations", "user_activations", "acquisition_channels"):
                connection.execute(
                    f"CREATE VIEW askdata_ops.{table} AS SELECT * FROM main.{table}",
                )
            cursor = connection.execute(diagnostic_sql(repaired_sql))
            columns = [item[0] for item in cursor.description]
            rows = [{name: engine._json_value(value) for name, value in zip(columns, raw)}
                    for raw in cursor.fetchall()]
        self.assertTrue(compare_results_strict(
            columns, rows, case["expected_columns"], case["expected_rows"],
            bool(case.get("order_sensitive", True)),
            order_by_column=case.get("order_by_column"),
            column_aliases=case.get("column_aliases"),
            top_n_tie_policy=case.get("top_n_tie_policy"),
        )[0])

    def test_confirmed_registration_metric_resolves_month_and_no_false_warning(self):
        report = json.loads((BASE / "evaluation/results/m1_e_postgres_e2e_behavior_server.json")
                            .read_text(encoding="utf-8"))
        case = next(row for row in report["cases"] if row["case_id"] == "E2E-CLARIFY-RESUME")
        choice = next(log for log in case["trace"]["execution_log"]
                      if log["stage"] == "clarification_resolved")
        call = next(log for log in case["trace"]["execution_log"]
                    if log["stage"] == "mcp_tool_call")
        graph = {**self.graph, "tables": [{"name": "user_registrations"},
                                         {"name": "acquisition_channels"}]}
        scope = AccessController().resolve("demo_channel_ops").public()
        metrics = MetricPlanner(runtime=self.runtime)
        without_confirmation = metrics.plan(case["standalone_query"], graph, scope)
        self.assertFalse(without_confirmation.metrics)
        selected = metrics.plan(case["standalone_query"], graph, scope,
                                {"performance": choice})
        self.assertEqual(selected.warnings, [])
        self.assertEqual(selected.metrics[0]["source_selection"], "confirmed_clarification")
        self.assertEqual(selected.metrics[0]["source_table"], "user_registrations")
        sql = call["arguments"]["sql"]
        self.assertEqual(metrics.validate_sql(sql, selected), [])
        constraint_plan = ConstraintPlanner(runtime=self.runtime).plan_for_sql(
            case["standalone_query"], selected, graph, sql,
        )
        self.assertEqual(constraint_plan.time_field_resolution["selected_fields"],
                         ["user_registrations.registered_at"])
        self.assertEqual(ConstraintValidator(runtime=self.runtime).validate(
            sql, "short_video_ops", constraint_plan, case["standalone_query"],
        ).status, "PASS")

    def test_rejected_sql_attempts_survive_to_live_report_without_execution(self):
        bad_sql = (
            "SELECT ac.channel_name, COUNT(r.registration_id) AS registrations, "
            "COUNT(a.activation_id) AS activated_users "
            "FROM user_registrations r JOIN user_activations a "
            "ON r.registration_id=a.registration_id "
            "JOIN acquisition_channels ac ON r.channel_id=ac.channel_id "
            "GROUP BY ac.channel_name"
        )
        model = Mock()
        model.chat_json.side_effect = lambda *_: {
            "action": "call_tool", "tool_name": "query_short_video_ops",
            "arguments": {"sql": bad_sql}, "query_contract": {},
        }
        mcp = Mock()
        mcp.list_tools.return_value = [{"name": "query_short_video_ops"}]
        skill = SkillDefinition("database_query", "", "", ("query_*",), 3,
                                ("call_tool", "clarify"))
        agent = SingleDatabaseAgent(model, lambda *_: mcp, skill)
        case = CASE_ROWS["GROWTH_OPS-051"]
        graph = {"tables": [{"name": name} for name in (
            "user_registrations", "user_activations", "acquisition_channels",
        )]}
        with self.assertRaises(PipelineStageError) as caught:
            agent.prepare(case["query"], "short_video_ops", graph, "", {}, {}, {})
        self.assertEqual(mcp.call_tool.call_count, 0)
        attempts = caught.exception.diagnostics["rejected_decisions"]
        self.assertEqual([item["attempt"] for item in attempts], [1, 2, 3])
        self.assertTrue(all(item["candidate_sql"] == bad_sql for item in attempts))
        self.assertTrue(all(item["metric_validation"]["errors"] for item in attempts))

        index = Mock(documents=[])
        index.retrieve.return_value = {"hits": []}
        graph_builder = Mock()
        graph_builder.build.return_value = graph
        graph_builder.context_text.return_value = ""
        workflow = Mock()
        workflow.single_database_agent.prepare.side_effect = caught.exception
        workflow.config.time_field_supplement_enabled = False
        result = run_live_case(case, index, graph_builder, workflow, AccessController())
        recorded = result.to_dict()
        self.assertFalse(recorded["sql_execution_success"])
        self.assertEqual(recorded["errors"]["diagnostics"]["rejected_decisions"], attempts)
        self.assertEqual(recorded["trace"]["errors"][0]["diagnostics"]["rejected_decisions"], attempts)


if __name__ == "__main__":
    unittest.main()
