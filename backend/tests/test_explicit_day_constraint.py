from __future__ import annotations

import unittest
from unittest.mock import Mock

from app.querying.constraint_planner import ConstraintPlanner
from app.querying.constraint_validator import ConstraintValidator
from app.querying.metric_planner import MetricPlanner
from app.querying.single_database_agent import SingleDatabaseAgent
from app.skills import SkillDefinition


class ExplicitDayConstraintTest(unittest.TestCase):
    question = "请列出1900年1月1日注册的用户ID和注册时间，最多20行。"
    good_sql = ("SELECT user_id, registered_at FROM user_registrations "
                "WHERE registered_at >= '1900-01-01' AND registered_at < '1900-01-02'")

    def test_ambiguous_retrieval_is_resolved_by_validated_sql_source(self):
        graph = {"tables": [{"name": "users"}, {"name": "user_registrations"}],
                 "fields": [{"table_name": table, "name": "registered_at",
                             "label": "注册时间", "type": "日期"}
                            for table in ("users", "user_registrations")]}
        planner = ConstraintPlanner()
        metrics = MetricPlanner().plan(self.question, graph)
        self.assertEqual(planner.plan(self.question, metrics, graph).time_field_resolution["status"], "ambiguous")
        plan = planner.plan_for_sql(self.question, metrics, graph, self.good_sql)
        self.assertEqual(plan.time_field_resolution["selected_fields"], ["user_registrations.registered_at"])
        self.assertEqual(plan.warnings, [])
        bad_sql = self.good_sql.replace("1900-01-02", "1900-02-01")
        self.assertEqual(ConstraintValidator().validate(bad_sql, "short_video_ops", plan).status, "BLOCK")

    def test_missing_retrieved_field_uses_real_schema_of_selected_source(self):
        graph = {"tables": [{"name": "user_registrations"}], "fields": []}
        plan = ConstraintPlanner().plan_for_sql(self.question, {}, graph, self.good_sql)
        self.assertEqual(plan.time_constraints[0]["field"], "user_registrations.registered_at")
        self.assertEqual(plan.time_field_resolution["source"], "validated_sql_sources_and_schema")

    def test_catalog_resolution_does_not_add_table_outside_graph(self):
        graph = {"tables": [{"name": "users"}], "fields": []}
        plan = ConstraintPlanner().plan_for_sql(self.question, {}, graph, self.good_sql)
        self.assertEqual(plan.time_constraints, [])
        self.assertEqual(plan.time_field_resolution["status"], "missing")

    def test_two_used_sources_still_need_disambiguation(self):
        graph = {"tables": [{"name": "users"}, {"name": "user_registrations"}],
                 "fields": [{"table_name": table, "name": "registered_at",
                             "label": "注册时间", "type": "日期"}
                            for table in ("users", "user_registrations")]}
        sql = self.good_sql + " AND user_id IN (SELECT user_id FROM users)"
        plan = ConstraintPlanner().plan_for_sql(self.question, {}, graph, sql)
        self.assertEqual(plan.time_constraints, [])
        self.assertEqual(plan.time_field_resolution["status"], "ambiguous")

    def test_agent_blocks_month_range_before_tool_and_records_final_day_plan(self):
        graph = {"tables": [{"name": "user_registrations"}], "fields": []}
        model, mcp = Mock(), Mock()
        bad_sql = self.good_sql.replace("1900-01-02", "1900-02-01")
        model.chat_json.side_effect = [
            {"action": "call_tool", "tool_name": "query_short_video_ops",
             "arguments": {"sql": sql}, "query_contract": {}}
            for sql in (bad_sql, self.good_sql)
        ]
        mcp.list_tools.return_value = [{"name": "query_short_video_ops"}]
        mcp.call_tool.return_value = {"success": True, "sql": self.good_sql, "columns": [], "rows": []}
        skill = SkillDefinition(name="database_query", description="", instructions="",
                                allowed_tools=("query_*",), max_tool_calls=3,
                                output_actions=("call_tool", "clarify"))
        agent = SingleDatabaseAgent(model, lambda scope: mcp, skill)
        result = agent.prepare(self.question, "short_video_ops", graph, "", {}, {}, {})
        mcp.call_tool.assert_called_once_with("query_short_video_ops", {"sql": self.good_sql})
        trace = result["tool_trace"][0]
        self.assertEqual([v["status"] for v in trace["constraint_validation_attempts"]], ["BLOCK", "PASS"])
        self.assertEqual(trace["query_contract"]["constraint_plan"]["time_constraints"][0]["operator"], "day_equals")

    def test_day_detail_accepts_one_day_and_blocks_whole_month(self) -> None:
        question = "请列出1900年1月1日注册的用户ID和注册时间，最多20行。"
        graph = {"tables": [{"name": "user_registrations"}], "fields": [{
            "table_name": "user_registrations", "name": "registered_at",
            "label": "注册时间", "type": "日期",
        }]}
        plan = ConstraintPlanner().plan(
            question, MetricPlanner().plan(question, graph), graph,
        )
        self.assertEqual(plan.time_constraints, [{
            "field": "user_registrations.registered_at",
            "operator": "day_equals", "value": "1900-01-01",
            "source": "user_requirement", "confidence": 1.0,
        }])
        gold_sql = (
            "SELECT user_id, registered_at FROM user_registrations "
            "WHERE registered_at >= DATE '1900-01-01' "
            "AND registered_at < DATE '1900-01-02'"
        )
        month_sql = (
            "SELECT user_id, registered_at FROM user_registrations "
            "WHERE registered_at >= '1900-01-01' "
            "AND registered_at < '1900-02-01'"
        )
        validator = ConstraintValidator()
        self.assertEqual(validator.validate(
            gold_sql, "short_video_ops", plan, question,
        ).status, "PASS")
        rejected = validator.validate(month_sql, "short_video_ops", plan, question)
        self.assertEqual(rejected.status, "BLOCK")
        self.assertIn("日期约束", rejected.errors[0])


if __name__ == "__main__":
    unittest.main()
