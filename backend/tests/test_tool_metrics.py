from __future__ import annotations

import unittest

from evaluation.metrics import ToolMetricsCalculator
from evaluation.models import EvaluationResult
from evaluation.trace import EvaluationTrace


class ToolMetricsCalculatorTest(unittest.TestCase):
    def test_single_successful_tool_call(self) -> None:
        metrics = ToolMetricsCalculator.calculate([
            {
                "tool_name": "query_short_video_ops",
                "success": True,
                "latency_ms": 1000,
                "retry_count": 0,
            }
        ])

        self.assertEqual(metrics["tool_call_count"], 1)
        self.assertEqual(metrics["tool_success_rate"], 1.0)
        self.assertEqual(metrics["tool_failure_rate"], 0.0)
        self.assertEqual(metrics["average_tool_latency_ms"], 1000.0)
        self.assertEqual(metrics["p95_tool_latency_ms"], 1000.0)
        self.assertEqual(metrics["tool_usage_distribution"], {"query_short_video_ops": 1})

    def test_mixed_success_and_failure_rates(self) -> None:
        metrics = ToolMetricsCalculator.calculate([
            {"tool_name": "query_short_video_ops", "success": True, "latency_ms": 10},
            {"tool_name": "execute_sql", "success": False, "latency_ms": 20},
        ])

        self.assertEqual(metrics["tool_call_count"], 2)
        self.assertEqual(metrics["tool_success_rate"], 0.5)
        self.assertEqual(metrics["tool_failure_rate"], 0.5)
        self.assertEqual(metrics["tool_usage_distribution"], {
            "query_short_video_ops": 1,
            "execute_sql": 1,
        })

    def test_latency_average_and_p95(self) -> None:
        metrics = ToolMetricsCalculator.calculate([
            {"tool_name": "query", "success": True, "latency_ms": 100},
            {"tool_name": "query", "success": True, "latency_ms": 200},
            {"tool_name": "query", "success": True, "latency_ms": 300},
            {"tool_name": "query", "success": True, "latency_ms": 400},
        ])

        self.assertEqual(metrics["average_tool_latency_ms"], 250.0)
        self.assertEqual(metrics["p95_tool_latency_ms"], 400.0)

    def test_retry_count_is_summed(self) -> None:
        metrics = ToolMetricsCalculator.calculate([
            {"tool_name": "query", "success": False, "retry_count": 2},
            {"tool_name": "query", "success": True, "retry_count": 1},
        ])

        self.assertEqual(metrics["tool_retry_count"], 3)

    def test_no_tool_calls_returns_null_rates_and_empty_distribution(self) -> None:
        metrics = ToolMetricsCalculator.calculate([])

        self.assertEqual(metrics["tool_call_count"], 0)
        self.assertIsNone(metrics["tool_success_rate"])
        self.assertIsNone(metrics["tool_failure_rate"])
        self.assertIsNone(metrics["average_tool_latency_ms"])
        self.assertIsNone(metrics["p95_tool_latency_ms"])
        self.assertEqual(metrics["tool_retry_count"], 0)
        self.assertEqual(metrics["tool_usage_distribution"], {})

    def test_evaluation_result_exposes_metrics_under_agent_metrics(self) -> None:
        result = EvaluationResult(
            case_id="CASE-001",
            question="查询用户数",
            scenario="growth_ops",
            category="汇总",
            query_type="指标",
            difficulty="简单",
            classic=True,
            trace=EvaluationTrace(tool_calls=[
                {"tool_name": "query_short_video_ops", "success": True,
                 "latency_ms": 1751.054, "retry_count": 0}
            ]),
        )

        self.assertEqual(result.agent_metrics["tool_call_count"], 1)
        self.assertEqual(result.agent_metrics["tool_success_rate"], 1.0)
        self.assertEqual(result.agent_metrics["average_tool_latency_ms"], 1751.054)
        self.assertEqual(result.to_dict()["agent_metrics"]["tool_call_count"], 1)


if __name__ == "__main__":
    unittest.main()
