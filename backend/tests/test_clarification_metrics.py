from __future__ import annotations

import unittest

from evaluation.clarification_metrics import ClarificationMetricsCalculator
from evaluation.models import EvaluationResult
from evaluation.trace import EvaluationTrace


class ClarificationMetricsCalculatorTest(unittest.TestCase):
    def test_no_clarification(self) -> None:
        metrics = ClarificationMetricsCalculator.calculate({"triggered": False})

        self.assertEqual(metrics["clarification_trigger_count"], 0)
        self.assertEqual(metrics["clarification_response_count"], 0)
        self.assertEqual(metrics["clarification_resolution_count"], 0)
        self.assertEqual(metrics["clarification_abandon_count"], 0)
        self.assertEqual(metrics["clarification_rate"], 0.0)
        self.assertIsNone(metrics["clarification_resolution_rate"])

    def test_triggered_without_response_is_abandoned(self) -> None:
        metrics = ClarificationMetricsCalculator.calculate({
            "triggered": True,
            "question": "请选择渠道",
            "option_count": 2,
            "user_responded": False,
            "continued_execution": False,
            "final_status": "waiting_clarification",
        })

        self.assertEqual(metrics["clarification_trigger_count"], 1)
        self.assertEqual(metrics["clarification_response_count"], 0)
        self.assertEqual(metrics["clarification_resolution_count"], 0)
        self.assertEqual(metrics["clarification_abandon_count"], 1)
        self.assertEqual(metrics["clarification_rate"], 1.0)
        self.assertEqual(metrics["clarification_resolution_rate"], 0.0)

    def test_response_followed_by_successful_execution_is_resolved(self) -> None:
        metrics = ClarificationMetricsCalculator.calculate({
            "triggered": True,
            "user_responded": True,
            "selected_option": "paid",
            "continued_execution": True,
            "final_status": "success",
        })

        self.assertEqual(metrics["clarification_response_count"], 1)
        self.assertEqual(metrics["clarification_resolution_count"], 1)
        self.assertEqual(metrics["clarification_abandon_count"], 0)
        self.assertEqual(metrics["clarification_resolution_rate"], 1.0)

    def test_multiple_clarifications(self) -> None:
        metrics = ClarificationMetricsCalculator.calculate([
            {"triggered": True, "user_responded": True, "continued_execution": True,
             "final_status": "success"},
            {"triggered": True, "user_responded": False, "continued_execution": False},
            {"triggered": False},
        ])

        self.assertEqual(metrics["clarification_trigger_count"], 2)
        self.assertEqual(metrics["clarification_response_count"], 1)
        self.assertEqual(metrics["clarification_resolution_count"], 1)
        self.assertEqual(metrics["clarification_abandon_count"], 1)
        self.assertEqual(metrics["clarification_rate"], 1.0)
        self.assertEqual(metrics["clarification_resolution_rate"], 0.5)

    def test_evaluation_result_exposes_clarification_metrics(self) -> None:
        result = EvaluationResult(
            case_id="CASE-001",
            question="查询渠道数据",
            scenario="channel_ops",
            category="渠道",
            query_type="汇总",
            difficulty="中等",
            classic=True,
            trace=EvaluationTrace(clarification={
                "triggered": True,
                "question": "请选择渠道",
                "option_count": 2,
                "user_responded": False,
                "continued_execution": False,
                "final_status": "waiting_clarification",
            }),
        )

        self.assertEqual(result.agent_metrics["clarification_trigger_count"], 1)
        self.assertEqual(result.agent_metrics["clarification_abandon_count"], 1)
        self.assertEqual(result.to_dict()["agent_metrics"]["clarification_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
