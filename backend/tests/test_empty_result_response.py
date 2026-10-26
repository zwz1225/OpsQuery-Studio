from __future__ import annotations

import unittest
from unittest.mock import Mock

from app.querying.models import SqlExecution
from app.querying.response_generator import ResponseGenerator
from app.workflows.result_builder import ResultBuilder


class EmptyResultResponseTest(unittest.TestCase):
    def test_direct_clarification_type_is_available_to_the_report(self) -> None:
        result = ResultBuilder.direct_response(
            "task1", "请选择指标", {
                "response_type": "clarification", "reason": "指标不明确",
            }, [],
        )
        self.assertEqual(result.direct_response_type, "clarification")
        self.assertEqual(result.route_reason, "指标不明确")

    def test_successful_empty_sql_is_a_completed_result_with_reason(self) -> None:
        model = Mock()
        execution = SqlExecution(
            sql="SELECT user_id FROM user_registrations WHERE registered_at = '1900-01-01'",
            success=True, columns=["user_id"], rows=[],
        )
        final = ResponseGenerator(model).finalize(
            "列出1900年1月1日的注册用户", execution, "", "",
        )
        self.assertTrue(final["valid"])
        self.assertIn("结果为空", final["reason"])
        model.chat_json.assert_not_called()
        result = ResultBuilder.completed(
            {"task_id": "task1", "schema_graph": {"tables": [], "fields": []}},
            [execution], execution, final,
            [{"success": True, "row_count": 0}],
            [{"stage": "execute_duckdb", "success": True}],
        )
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.rows, [])
        self.assertEqual(result.result_validation_reason, final["reason"])


if __name__ == "__main__":
    unittest.main()
