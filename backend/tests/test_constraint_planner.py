from __future__ import annotations

import json
from pathlib import Path
import unittest

from app.querying.constraint_planner import ConstraintPlanner
from app.querying.constraint_validator import ConstraintValidator
from app.querying.metric_planner import MetricPlanner
from app.querying.single_database_agent import SingleDatabaseAgent
from app.skills import SkillDefinition


CASES_PATH = Path(__file__).resolve().parents[1] / "evaluation" / "cases" / "all_cases.jsonl"
GRAPH = {"tables": [{"name": name} for name in (
    "user_registrations", "user_activations", "acquisition_channels", "growth_targets",
)]}


def case(case_id: str) -> dict:
    with CASES_PATH.open(encoding="utf-8") as stream:
        return next(row for line in stream if (row := json.loads(line))["case_id"] == case_id)


class ConstraintPlannerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.metrics = MetricPlanner()
        self.planner = ConstraintPlanner()
        self.validator = ConstraintValidator()

    def plan_for(self, question: str):
        metric_plan = self.metrics.plan(question, GRAPH)
        return self.planner.plan(question, metric_plan, GRAPH)

    def test_explicit_month_creates_metric_time_constraint(self) -> None:
        question = "2026-05 各渠道激活率"
        plan = self.plan_for(question)
        self.assertIn({
            "field": "user_registrations.registered_at",
            "operator": "month_equals", "value": "2026-05",
            "source": "user_requirement", "confidence": 1.0,
        }, plan.time_constraints)

    def test_chinese_month_is_normalized(self) -> None:
        plan = self.plan_for("2026年5月各渠道激活率")
        self.assertTrue(any(item["value"] == "2026-05" for item in plan.time_constraints))

    def test_target_month_only_added_for_target_comparison(self) -> None:
        plan = self.plan_for("2026-05 各渠道激活率实际值与目标差距")
        targets = [item for item in plan.time_constraints if item["field"] == "growth_targets.target_month"]
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["value"], "2026-05")
        self.assertEqual(targets[0]["source"], "metric_definition")

    def test_regular_activation_rate_does_not_require_target_month(self) -> None:
        plan = self.plan_for("2026-05 各渠道激活率")
        self.assertFalse(any(item["field"] == "growth_targets.target_month" for item in plan.time_constraints))

    def test_no_month_produces_no_time_constraints(self) -> None:
        plan = self.plan_for("各渠道激活率实际值与目标差距")
        self.assertEqual(plan.time_constraints, [])

    def test_explicit_registration_month_is_required(self) -> None:
        question = "2026-05 各渠道激活率实际值与目标差距"
        plan = self.plan_for(question)
        sql = (
            "SELECT r.channel_id, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) * 1.0 / COUNT(*) "
            "FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id "
            "JOIN growth_targets t ON r.channel_id=t.channel_id AND substr(t.target_month,1,7)='2026-05' "
            "GROUP BY r.channel_id"
        )
        result = self.validator.validate(sql, "short_video_ops", plan)
        self.assertEqual(result.status, "BLOCK")
        self.assertEqual(result.missing_constraints[0]["field"], "user_registrations.registered_at")

    def test_missing_target_month_is_blocked(self) -> None:
        question = "2026-05 各渠道激活率实际值与目标差距"
        plan = self.plan_for(question)
        sql = (
            "SELECT r.channel_id, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) * 1.0 / COUNT(*) "
            "FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id "
            "JOIN growth_targets t ON r.channel_id=t.channel_id "
            "WHERE strftime(r.registered_at,'%Y-%m')='2026-05' GROUP BY r.channel_id"
        )
        result = self.validator.validate(sql, "short_video_ops", plan)
        self.assertEqual(result.status, "BLOCK")
        self.assertEqual(result.missing_constraints[0]["field"], "growth_targets.target_month")

    def test_target_month_in_join_on_is_accepted(self) -> None:
        question = "2026-05 各渠道激活率实际值与目标差距"
        plan = self.plan_for(question)
        sql = (
            "SELECT r.channel_id, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) * 1.0 / COUNT(*) "
            "FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id "
            "JOIN growth_targets t ON r.channel_id=t.channel_id AND substr(t.target_month,1,7)='2026-05' "
            "WHERE strftime(r.registered_at,'%Y-%m')='2026-05' GROUP BY r.channel_id"
        )
        self.assertEqual(self.validator.validate(sql, "short_video_ops", plan).status, "PASS")

    def test_month_date_range_is_accepted(self) -> None:
        question = "2026-05 各渠道激活率"
        plan = self.plan_for(question)
        sql = (
            "SELECT r.registration_id FROM user_registrations r "
            "WHERE r.registered_at >= '2026-05-01' AND r.registered_at < '2026-06-01'"
        )
        self.assertEqual(self.validator.validate(sql, "short_video_ops", plan).status, "PASS")

    def test_real_growth_150_constraints_and_gold_sql_pass(self) -> None:
        row = case("GROWTH_OPS-150")
        plan = self.plan_for(row["query"])
        self.assertEqual(self.validator.validate(row["gold_sql"], "short_video_ops", plan).status, "PASS")

    def test_daily_new_users_plan_requires_metric_date_grouping(self) -> None:
        row = case("GROWTH_OPS-006")
        schema = {"tables": [{"name": "growth_daily_metrics"}]}
        metric_plan = self.metrics.plan(row["query"], schema)
        plan = self.planner.plan(row["query"], metric_plan, schema)
        self.assertIn({
            "field": "growth_daily_metrics.metric_date",
            "grain": "day", "source": "user_requirement", "confidence": 1.0,
        }, plan.group_constraints)
        self.assertEqual(plan.conditional_filter_rules, [])
        self.assertEqual(self.validator.validate(row["gold_sql"], "short_video_ops", plan).status,
                         "PASS")

    def test_daily_group_constraint_rejects_missing_group_by(self) -> None:
        question = "查询2026-01每天的新增用户数"
        schema = {"tables": [{"name": "growth_daily_metrics"}]}
        plan = self.planner.plan(question, self.metrics.plan(question, schema), schema)
        sql = (
            "SELECT metric_date, SUM(new_users) FROM growth_daily_metrics "
            "WHERE metric_date >= '2026-01-01' AND metric_date < '2026-02-01'"
        )
        result = self.validator.validate(sql, "short_video_ops", plan, question)
        self.assertEqual(result.status, "BLOCK")
        self.assertEqual(result.missing_group_constraints[0]["field"],
                         "growth_daily_metrics.metric_date")

    def test_daily_group_constraint_accepts_group_by_date_or_ordinal(self) -> None:
        question = "查询2026-01每天的新增用户数"
        schema = {"tables": [{"name": "growth_daily_metrics"}]}
        plan = self.planner.plan(question, self.metrics.plan(question, schema), schema)
        for group_by in ("GROUP BY metric_date", "GROUP BY 1"):
            sql = (
                "SELECT metric_date, SUM(new_users) FROM growth_daily_metrics "
                "WHERE metric_date >= '2026-01-01' AND metric_date < '2026-02-01' "
                f"{group_by}"
            )
            self.assertEqual(self.validator.validate(sql, "short_video_ops", plan).status,
                             "PASS", group_by)

    def test_real_growth_149_keeps_registration_id_grain_and_gold_sql_passes(self) -> None:
        row = case("GROWTH_OPS-149")
        metric_plan = self.metrics.plan(row["query"], GRAPH)
        plan = self.planner.plan(row["query"], metric_plan, GRAPH)
        self.assertEqual(metric_plan.joins[0]["left"], "user_registrations.registration_id")
        self.assertEqual(self.validator.validate(row["gold_sql"], "short_video_ops", plan).status, "PASS")

    def test_unsupported_valid_activity_filter_is_blocked(self) -> None:
        row = case("GROWTH_OPS-086")
        schema = {"tables": [{"name": name} for name in (
            "user_daily_activity", "users", "user_profiles",
        )]}
        plan = self.planner.plan(row["query"], self.metrics.plan(row["query"], schema), schema)
        sql = (
            "SELECT up.region, AVG(uda.active_minutes), AVG(uda.session_count) "
            "FROM user_daily_activity uda JOIN users u ON uda.user_id=u.user_id "
            "JOIN user_profiles up ON u.user_id=up.user_id "
            "WHERE uda.is_valid_active=1 AND up.region='华东' GROUP BY up.region"
        )
        result = self.validator.validate(sql, "short_video_ops", plan, row["query"])
        self.assertEqual(result.status, "BLOCK")
        self.assertEqual(result.unsupported_constraints[0]["field"],
                         "user_daily_activity.is_valid_active")
        self.assertIn("未明确要求", result.errors[0])

    def test_explicit_valid_activity_request_allows_filter(self) -> None:
        question = "只统计有效活跃记录的平均活跃时长"
        schema = {"tables": [{"name": "user_daily_activity"}]}
        plan = self.planner.plan(question, self.metrics.plan(question, schema), schema)
        sql = "SELECT AVG(uda.active_minutes) FROM user_daily_activity uda WHERE uda.is_valid_active=1"
        self.assertNotEqual(
            self.validator.validate(sql, "short_video_ops", plan, question).status,
            "BLOCK",
        )

    def test_metric_case_expression_is_not_treated_as_row_filter(self) -> None:
        question = "2026-04有效活跃记录占比"
        schema = {"tables": [{"name": "user_daily_activity"}]}
        plan = self.planner.plan(question, self.metrics.plan(question, schema), schema)
        sql = (
            "SELECT SUM(CASE WHEN is_valid_active=1 THEN 1 ELSE 0 END)*1.0/COUNT(*) "
            "FROM user_daily_activity"
        )
        self.assertNotEqual(
            self.validator.validate(sql, "short_video_ops", plan, question).status,
            "BLOCK",
        )


class _Model:
    def __init__(self, sqls: list[str]) -> None:
        self.sqls = iter(sqls)
        self.requests: list[dict] = []

    def chat_json(self, system: str, payload: str) -> dict:
        self.requests.append(json.loads(payload))
        return {
            "action": "call_tool", "tool_name": "query_short_video_ops",
            "arguments": {"sql": next(self.sqls)}, "query_contract": {},
        }


class _Mcp:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def list_tools(self) -> list[dict]:
        return [{"name": "query_short_video_ops"}]

    def call_tool(self, name: str, arguments: dict) -> dict:
        self.calls.append(arguments)
        return {"success": True, "columns": [], "rows": []}


class ConstraintAgentIntegrationTest(unittest.TestCase):
    def test_missing_target_month_is_repaired_before_mcp_call(self) -> None:
        question = case("GROWTH_OPS-150")["query"]
        missing_target_sql = (
            "SELECT r.channel_id, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) * 1.0 / COUNT(*) "
            "FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id "
            "JOIN growth_targets t ON r.channel_id=t.channel_id "
            "WHERE strftime(r.registered_at,'%Y-%m')='2026-05' GROUP BY r.channel_id"
        )
        fixed_sql = case("GROWTH_OPS-150")["gold_sql"]
        model, mcp = _Model([missing_target_sql, fixed_sql]), _Mcp()
        skill = SkillDefinition(
            name="database_query", description="", instructions="", allowed_tools=("query_*",),
            max_tool_calls=3, output_actions=("call_tool", "clarify"),
        )
        agent = SingleDatabaseAgent(model, lambda scope: mcp, skill)
        result = agent.prepare(question, "short_video_ops", GRAPH, "", {}, {}, {})

        self.assertEqual(len(model.requests), 2)
        self.assertIn("growth_targets.target_month", model.requests[1]["output_validation_error"])
        self.assertEqual(len(mcp.calls), 1)
        contract = result["tool_trace"][0]["query_contract"]
        self.assertEqual(contract["constraint_validation"]["status"], "PASS")
        self.assertTrue(any(
            item["field"] == "growth_targets.target_month"
            for item in contract["constraint_plan"]["time_constraints"]
        ))

    def test_unsupported_active_filter_is_repaired_before_mcp_call(self) -> None:
        row = case("GROWTH_OPS-086")
        invalid_sql = (
            "SELECT up.region, AVG(uda.active_minutes), AVG(uda.session_count) "
            "FROM user_daily_activity uda JOIN users u ON uda.user_id=u.user_id "
            "JOIN user_profiles up ON u.user_id=up.user_id "
            "WHERE uda.is_valid_active=1 AND up.region='华东' GROUP BY up.region"
        )
        mcp = _Mcp()
        model = _Model([invalid_sql, row["gold_sql"]])
        skill = SkillDefinition(
            name="database_query", description="", instructions="", allowed_tools=("query_*",),
            max_tool_calls=3, output_actions=("call_tool", "clarify"),
        )
        schema = {"tables": [{"name": name} for name in (
            "user_daily_activity", "users", "user_profiles",
        )]}
        agent = SingleDatabaseAgent(model, lambda scope: mcp, skill)
        result = agent.prepare(row["query"], "short_video_ops", schema, "", {}, {}, {})

        self.assertEqual(len(model.requests), 2)
        self.assertIn("is_valid_active", model.requests[1]["output_validation_error"])
        self.assertEqual(len(mcp.calls), 1)
        contract = result["tool_trace"][0]["query_contract"]
        self.assertEqual(contract["constraint_validation"]["status"], "PASS")

    def test_new_users_sql_is_repaired_for_metric_and_daily_grain_before_mcp(self) -> None:
        question = case("GROWTH_OPS-006")["query"]
        missing_sum = (
            "SELECT metric_date, new_users FROM growth_daily_metrics "
            "WHERE metric_date >= '2026-01-01' AND metric_date < '2026-02-01' "
            "ORDER BY metric_date"
        )
        missing_group = (
            "SELECT metric_date, SUM(new_users) AS new_users FROM growth_daily_metrics "
            "WHERE metric_date >= '2026-01-01' AND metric_date < '2026-02-01' "
            "ORDER BY metric_date"
        )
        correct_sql = (
            "SELECT metric_date, SUM(new_users) AS new_users FROM growth_daily_metrics "
            "WHERE metric_date >= '2026-01-01' AND metric_date < '2026-02-01' "
            "GROUP BY metric_date ORDER BY metric_date"
        )
        mcp = _Mcp()
        model = _Model([missing_sum, missing_group, correct_sql])
        skill = SkillDefinition(
            name="database_query", description="", instructions="", allowed_tools=("query_*",),
            max_tool_calls=3, output_actions=("call_tool", "clarify"),
        )
        schema = {"tables": [{"name": "growth_daily_metrics"}]}
        agent = SingleDatabaseAgent(model, lambda scope: mcp, skill)
        result = agent.prepare(question, "short_video_ops", schema, "", {}, {}, {})

        self.assertEqual(len(model.requests), 3)
        self.assertIn("SUM", model.requests[1]["output_validation_error"])
        self.assertIn("growth_daily_metrics.metric_date",
                      model.requests[2]["output_validation_error"])
        self.assertEqual(len(mcp.calls), 1)
        contract = result["tool_trace"][0]["query_contract"]
        self.assertEqual(contract["metric_plan"]["metrics"][0]["name"], "new_users")
        self.assertEqual(contract["constraint_validation"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
