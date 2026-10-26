from __future__ import annotations

import json
from pathlib import Path
import unittest

from app.querying.metric_planner import MetricPlanner
from app.querying.single_database_agent import SingleDatabaseAgent
from app.skills import SkillDefinition


CASES_PATH = Path(__file__).resolve().parents[1] / "evaluation" / "cases" / "all_cases.jsonl"
DAILY_GRAPH = {"tables": [{"name": "growth_daily_metrics"}]}
COHORT_GRAPH = {"tables": [{"name": name} for name in (
    "user_registrations", "user_activations", "acquisition_channels", "growth_targets",
)]}


def case(case_id: str) -> dict:
    with CASES_PATH.open(encoding="utf-8") as stream:
        return next(row for line in stream if (row := json.loads(line))["case_id"] == case_id)


class MetricPlannerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = MetricPlanner()

    def test_activated_users_uses_canonical_daily_metric(self) -> None:
        plan = self.planner.plan("查询每月激活用户数", DAILY_GRAPH)
        metric = plan.metrics[0]
        self.assertEqual(metric["name"], "activated_users")
        self.assertEqual(metric["source_table"], "growth_daily_metrics")
        self.assertEqual(metric["source_field"], "activated_users")
        self.assertEqual(metric["aggregation"], "SUM")
        self.assertEqual(metric["time_field"]["field"], "metric_date")

    def test_new_users_uses_daily_metric_source_and_sum(self) -> None:
        plan = self.planner.plan("查询2026-01每天的新增用户数", DAILY_GRAPH)
        metric = plan.metrics[0]
        self.assertEqual(metric["name"], "new_users")
        self.assertEqual(metric["source_table"], "growth_daily_metrics")
        self.assertEqual(metric["source_field"], "new_users")
        self.assertEqual(metric["aggregation"], "SUM")
        self.assertEqual(metric["time_field"]["field"], "metric_date")

    def test_daily_active_users_uses_canonical_daily_metric_and_date(self) -> None:
        plan = self.planner.plan("查询2026年每个月的日活用户数", DAILY_GRAPH)
        metric = plan.metrics[0]
        self.assertEqual(metric["name"], "daily_active_users")
        self.assertEqual(metric["source_table"], "growth_daily_metrics")
        self.assertEqual(metric["source_field"], "daily_active_users")
        self.assertEqual(metric["aggregation"], "SUM")
        self.assertEqual(metric["time_field"], {
            "table": "growth_daily_metrics",
            "field": "metric_date",
        })

    def test_real_growth_005_uses_canonical_daily_active_users_metric(self) -> None:
        row = case("GROWTH_OPS-005")
        plan = self.planner.plan(row["query"], DAILY_GRAPH)
        self.assertEqual([metric["name"] for metric in plan.metrics], ["daily_active_users"])
        self.assertEqual(self.planner.validate_sql(row["gold_sql"], plan), [])

    def test_day1_retained_users_uses_canonical_daily_metric_and_date(self) -> None:
        plan = self.planner.plan("查询2026年每个月的次日留存用户数", DAILY_GRAPH)
        metric = plan.metrics[0]
        self.assertEqual(metric["name"], "day1_retained_users")
        self.assertEqual(metric["source_table"], "growth_daily_metrics")
        self.assertEqual(metric["source_field"], "day1_retained_users")
        self.assertEqual(metric["aggregation"], "SUM")
        self.assertEqual(metric["time_field"], {
            "table": "growth_daily_metrics",
            "field": "metric_date",
        })

    def test_real_growth_003_uses_canonical_day1_retention_metric(self) -> None:
        row = case("GROWTH_OPS-003")
        plan = self.planner.plan(row["query"], DAILY_GRAPH)
        self.assertEqual([metric["name"] for metric in plan.metrics], ["day1_retained_users"])
        self.assertEqual(self.planner.validate_sql(row["gold_sql"], plan), [])

    def test_new_users_requires_canonical_sum(self) -> None:
        plan = self.planner.plan("查询2026-01每天的新增用户数", DAILY_GRAPH)
        errors = self.planner.validate_sql(
            "SELECT metric_date, new_users FROM growth_daily_metrics "
            "WHERE metric_date >= '2026-01-01' AND metric_date < '2026-02-01'",
            plan,
        )
        self.assertTrue(any("SUM" in error and "new_users" in error for error in errors))

    def test_alternative_source_warns_when_canonical_table_is_missing(self) -> None:
        plan = self.planner.plan(
            "查询每月激活用户数", {"tables": [{"name": "user_activations"}]}
        )
        self.assertFalse(plan.metrics[0]["available"])
        self.assertIn("备选来源", plan.warnings[0])

    def test_activation_rate_formula_and_components(self) -> None:
        plan = self.planner.plan("查询激活率", COHORT_GRAPH)
        metric = plan.metrics[0]
        self.assertEqual(metric["name"], "activation_rate")
        self.assertEqual(metric["formula"], "activated_registrations / registrations")
        self.assertEqual(metric["numerator"]["field"], "is_activated")
        self.assertEqual(metric["denominator"]["field"], "registration_id")
        self.assertEqual(metric["denominator"]["aggregation"], "COUNT_DISTINCT")
        self.assertEqual(metric["time_field"]["field"], "registered_at")

    def test_registration_id_join_is_in_plan(self) -> None:
        plan = self.planner.plan("查询激活率", COHORT_GRAPH)
        self.assertEqual(plan.joins, [{
            "left": "user_registrations.registration_id",
            "right": "user_activations.registration_id",
        }])

    def test_unknown_metric_falls_back(self) -> None:
        plan = self.planner.plan("查询视频播放量", DAILY_GRAPH)
        self.assertEqual(plan.metrics, [])
        self.assertEqual(plan.warnings, [])

    def test_metric_plan_serializes_to_json(self) -> None:
        plan = self.planner.plan("查询激活率", COHORT_GRAPH)
        self.assertEqual(json.loads(json.dumps(plan.to_dict()))["metrics"][0]["name"],
                         "activation_rate")

    def test_real_growth_002_prefers_daily_metric_and_rejects_event_count(self) -> None:
        row = case("GROWTH_OPS-002")
        plan = self.planner.plan(row["query"], DAILY_GRAPH)
        self.assertEqual([metric["name"] for metric in plan.metrics], ["activated_users"])
        self.assertEqual(self.planner.validate_sql(row["gold_sql"], plan), [])
        errors = self.planner.validate_sql(
            "SELECT STRFTIME(activated_at, '%Y-%m'), COUNT(*) "
            "FROM user_activations GROUP BY 1", plan
        )
        self.assertTrue(any("growth_daily_metrics.activated_users" in e for e in errors))

    def test_real_growth_149_uses_registration_cohort(self) -> None:
        row = case("GROWTH_OPS-149")
        plan = self.planner.plan(row["query"], COHORT_GRAPH)
        self.assertEqual([metric["name"] for metric in plan.metrics], ["activation_rate"])
        self.assertEqual(self.planner.validate_sql(row["gold_sql"], plan), [])
        bad = (
            "SELECT SUM(gdm.activated_users) / COUNT(ur.registration_id) "
            "FROM growth_daily_metrics gdm JOIN user_registrations ur "
            "ON gdm.channel_id = ur.channel_id"
        )
        self.assertTrue(self.planner.validate_sql(bad, plan))

    def test_cohort_output_count_does_not_force_daily_metric(self) -> None:
        row = case("GROWTH_OPS-051")
        plan = self.planner.plan(row["query"], COHORT_GRAPH)
        self.assertEqual([metric["name"] for metric in plan.metrics], ["activation_rate"])
        self.assertEqual(self.planner.validate_sql(row["gold_sql"], plan), [])

    def test_denied_catalog_source_is_not_exposed(self) -> None:
        plan = self.planner.plan(
            "查询激活率", COHORT_GRAPH,
            {"allowed_tables": ["short_video_ops.user_registrations"]},
        )
        self.assertEqual(plan.metrics, [])
        self.assertEqual(plan.selected_sources, [])
        self.assertNotIn("user_activations", json.dumps(plan.to_dict()))


class _Model:
    def __init__(self, sqls: list[str]) -> None:
        self.sqls = iter(sqls)
        self.requests: list[dict] = []

    def chat_json(self, system: str, payload: str) -> dict:
        self.requests.append(json.loads(payload))
        return {
            "action": "call_tool", "tool_name": "query_short_video_ops",
            "arguments": {"sql": next(self.sqls)}, "query_contract": {"grain": "时间趋势"},
        }


class _Mcp:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def list_tools(self) -> list[dict]:
        return [{"name": "query_short_video_ops"}]

    def call_tool(self, name: str, arguments: dict) -> dict:
        self.calls.append(arguments)
        return {"success": True, "columns": ["value"], "rows": []}


class MetricPlannerAgentIntegrationTest(unittest.TestCase):
    def test_wrong_metric_source_is_repaired_before_tool_call(self) -> None:
        model = _Model([
            "SELECT COUNT(*) FROM user_activations",
            "SELECT SUM(activated_users) FROM growth_daily_metrics",
        ])
        mcp = _Mcp()
        skill = SkillDefinition(
            name="database_query", description="", instructions="",
            allowed_tools=("query_*",), max_tool_calls=3,
            output_actions=("call_tool", "clarify"),
        )
        agent = SingleDatabaseAgent(model, lambda scope: mcp, skill)
        result = agent.prepare(
            "查询激活用户数", "short_video_ops", DAILY_GRAPH, "", {}, {}, {}
        )
        self.assertEqual(len(model.requests), 2)
        self.assertIn("growth_daily_metrics.activated_users",
                      model.requests[1]["output_validation_error"])
        self.assertEqual(len(mcp.calls), 1)
        contract = result["tool_trace"][0]["query_contract"]
        self.assertEqual(contract["grain"], "时间趋势")
        self.assertEqual(contract["metric_plan"]["metrics"][0]["name"], "activated_users")
        self.assertEqual(result["tool_trace"][0]["metric_validation"]["errors"], [])
        self.assertEqual(len(result["tool_trace"][0]["metric_validation_attempts"]), 2)
        self.assertTrue(result["tool_trace"][0]["metric_validation_attempts"][0]["errors"])


if __name__ == "__main__":
    unittest.main()
