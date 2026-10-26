from __future__ import annotations

import unittest

from app.errors import PipelineStageError
from app.querying.single_database_agent import SingleDatabaseAgent
from app.querying.sql_validator import SQLValidator
from app.skills import SkillDefinition


SCHEMA = {
    "tables": [
        {"name": "users", "columns": ["user_id", "registered_at"]},
        {"name": "orders", "columns": ["id", "user_id", "amount"]},
    ]
}


class SQLValidatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = SQLValidator()

    def check(self, sql: str, schema=SCHEMA):
        return self.validator.validate(sql, "short_video_ops", schema)

    def test_nonexistent_qualified_column_is_blocked(self) -> None:
        result = self.check("SELECT ur.registration_month FROM users ur")
        self.assertEqual(result.status, "BLOCK")
        self.assertEqual(result.invalid_columns, ["ur.registration_month"])

    def test_existing_column_passes(self) -> None:
        self.assertEqual(self.check("SELECT user_id FROM users").status, "PASS")

    def test_table_alias_passes(self) -> None:
        self.assertEqual(self.check("SELECT ur.user_id FROM users ur").status, "PASS")

    def test_join_fields_pass(self) -> None:
        result = self.check(
            "SELECT u.user_id, SUM(o.amount) AS total "
            "FROM users u JOIN orders o ON u.user_id = o.user_id "
            "GROUP BY u.user_id"
        )
        self.assertEqual(result.status, "PASS")

    def test_cte_output_is_not_mistaken_for_base_column(self) -> None:
        result = self.check(
            "WITH tmp AS (SELECT user_id FROM users) SELECT tmp.user_id FROM tmp"
        )
        self.assertEqual(result.status, "PASS")

    def test_select_alias_in_order_by_passes(self) -> None:
        result = self.check(
            "SELECT SUM(amount) AS total_amount FROM orders ORDER BY total_amount"
        )
        self.assertEqual(result.status, "PASS")

    def test_unknown_source_warns_instead_of_blocking(self) -> None:
        result = self.check("SELECT x.any_column FROM unknown_source x")
        self.assertEqual(result.status, "WARN")
        self.assertEqual(result.invalid_columns, [])

    def test_complex_cte_with_unknown_output_warns(self) -> None:
        result = self.check(
            "WITH tmp AS (SELECT * FROM users) SELECT tmp.user_id FROM tmp"
        )
        self.assertEqual(result.status, "WARN")

    def test_real_growth_case_blocks_missing_registration_month(self) -> None:
        schema = {"tables": [{"name": name} for name in (
            "acquisition_channels", "growth_daily_metrics",
            "user_registrations", "growth_targets",
        )]}
        result = self.check(
            "SELECT ac.channel_name, "
            "SUM(gdm.activated_users) * 1.0 / NULLIF(SUM(ur.registered_users), 0) "
            "AS actual_activation_rate, gt.activation_rate_target "
            "FROM acquisition_channels ac "
            "JOIN growth_daily_metrics gdm ON ac.channel_id = gdm.channel_id "
            "JOIN user_registrations ur ON ac.channel_id = ur.channel_id "
            "JOIN growth_targets gt ON ac.channel_id = gt.channel_id "
            "WHERE gdm.metric_date >= '2026-04-01' "
            "AND gdm.metric_date < '2026-05-01' "
            "AND ur.registration_month = '2026-04' "
            "AND gt.target_month = '2026-04' "
            "GROUP BY ac.channel_name, gt.activation_rate_target",
            schema,
        )
        self.assertEqual(result.status, "BLOCK")
        self.assertIn("ur.registration_month", result.invalid_columns)
        self.assertIn("ur.registered_users", result.invalid_columns)

    def test_retrieval_subset_does_not_block_valid_canonical_column(self) -> None:
        schema = {
            "tables": [{"name": "user_registrations"}],
            "fields": [{"table_name": "user_registrations", "name": "registration_id"}],
        }
        result = self.check(
            "SELECT ur.registered_at FROM user_registrations ur", schema
        )
        self.assertEqual(result.status, "PASS")


class _FakeModel:
    def __init__(self, sqls: list[str]) -> None:
        self.sqls = iter(sqls)
        self.requests: list[dict] = []

    def chat_json(self, system: str, payload: str) -> dict:
        import json

        self.requests.append(json.loads(payload))
        return {
            "action": "call_tool",
            "tool_name": "query_short_video_ops",
            "arguments": {"sql": next(self.sqls)},
            "query_contract": {},
        }


class _FakeMcpClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def list_tools(self) -> list[dict]:
        return [{"name": "query_short_video_ops"}]

    def call_tool(self, name: str, arguments: dict) -> dict:
        self.calls.append((name, arguments))
        return {"success": True, "columns": ["registered_at"], "rows": []}


class SQLValidatorAgentIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = {"tables": [{"name": "user_registrations"}]}
        self.client = _FakeMcpClient()
        self.skill = SkillDefinition(
            name="database_query",
            description="",
            instructions="",
            allowed_tools=("query_*",),
            max_tool_calls=3,
            output_actions=("call_tool", "clarify"),
        )

    def agent(self, model: _FakeModel) -> SingleDatabaseAgent:
        return SingleDatabaseAgent(model, lambda scope: self.client, self.skill)

    def prepare(self, agent: SingleDatabaseAgent) -> dict:
        return agent.prepare(
            "查询注册日期", "short_video_ops", self.schema, "", {}, {}, {}
        )

    def test_blocked_sql_is_corrected_before_mcp_call(self) -> None:
        model = _FakeModel([
            "SELECT ur.registration_month FROM user_registrations ur",
            "SELECT ur.registered_at FROM user_registrations ur",
        ])
        result = self.prepare(self.agent(model))
        self.assertEqual(len(model.requests), 2)
        self.assertIn("registration_month", model.requests[1]["output_validation_error"])
        self.assertEqual(len(self.client.calls), 1)
        self.assertEqual(result["tool_trace"][0]["sql_validation"]["status"], "PASS")
        self.assertEqual(
            [item["status"] for item in result["tool_trace"][0]["sql_validation_attempts"]],
            ["BLOCK", "PASS"],
        )

    def test_repeated_block_stops_without_mcp_call(self) -> None:
        bad = "SELECT ur.registration_month FROM user_registrations ur"
        model = _FakeModel([bad, bad, bad])
        with self.assertRaises(PipelineStageError):
            self.prepare(self.agent(model))
        self.assertEqual(len(model.requests), 3)
        self.assertEqual(self.client.calls, [])


if __name__ == "__main__":
    unittest.main()
