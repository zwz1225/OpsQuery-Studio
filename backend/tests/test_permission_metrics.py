from __future__ import annotations

import unittest

from evaluation.models import EvaluationResult
from evaluation.permission_metrics import PermissionMetricsCalculator
from evaluation.trace import EvaluationTrace


class PermissionMetricsCalculatorTest(unittest.TestCase):
    def test_allowed_permission_check(self) -> None:
        metrics = PermissionMetricsCalculator.calculate({
            "checked": True,
            "user_id": "demo_growth_ops",
            "roles": ["growth_ops"],
            "sql_permission_check": True,
            "sql_blocked": False,
        })

        self.assertEqual(metrics["permission_check_count"], 1)
        self.assertEqual(metrics["permission_success_rate"], 1.0)
        self.assertEqual(metrics["permission_denied_count"], 0)
        self.assertEqual(metrics["sql_permission_blocked_count"], 0)
        self.assertEqual(metrics["role_distribution"], {"growth_ops": 1})

    def test_denied_permission_check(self) -> None:
        metrics = PermissionMetricsCalculator.calculate({
            "checked": True,
            "roles": ["growth_ops"],
            "sql_permission_check": True,
            "sql_blocked": True,
            "denied_reason": "当前用户无权访问的数据表",
        })

        self.assertEqual(metrics["permission_check_count"], 1)
        self.assertEqual(metrics["permission_success_rate"], 0.0)
        self.assertEqual(metrics["permission_denied_count"], 1)
        self.assertEqual(metrics["sql_permission_blocked_count"], 1)

    def test_schema_filter_count(self) -> None:
        metrics = PermissionMetricsCalculator.calculate({
            "checked": True,
            "schema_filter_applied": True,
            "schema_before_filter_count": 10,
            "schema_after_filter_count": 6,
        })

        self.assertEqual(metrics["schema_permission_filter_count"], 4)

    def test_multiple_roles_are_counted(self) -> None:
        metrics = PermissionMetricsCalculator.calculate({
            "checked": True,
            "roles": ["admin", "analyst", "admin"],
        })

        self.assertEqual(metrics["role_distribution"], {"admin": 2, "analyst": 1})

    def test_no_permission_information(self) -> None:
        metrics = PermissionMetricsCalculator.calculate(None)

        self.assertEqual(metrics["permission_check_count"], 0)
        self.assertIsNone(metrics["permission_success_rate"])
        self.assertEqual(metrics["permission_denied_count"], 0)
        self.assertEqual(metrics["schema_permission_filter_count"], 0)
        self.assertEqual(metrics["sql_permission_blocked_count"], 0)
        self.assertEqual(metrics["role_distribution"], {})

    def test_evaluation_result_exposes_permission_metrics(self) -> None:
        result = EvaluationResult(
            case_id="CASE-001",
            question="查询用户数",
            scenario="growth_ops",
            category="汇总",
            query_type="指标",
            difficulty="简单",
            classic=True,
            trace=EvaluationTrace(permission={
                "checked": True,
                "roles": ["growth_ops"],
                "schema_before_filter_count": 10,
                "schema_after_filter_count": 8,
            }),
        )

        self.assertEqual(result.agent_metrics["permission_check_count"], 1)
        self.assertEqual(result.agent_metrics["schema_permission_filter_count"], 2)
        self.assertEqual(result.to_dict()["agent_metrics"]["role_distribution"], {"growth_ops": 1})


if __name__ == "__main__":
    unittest.main()
