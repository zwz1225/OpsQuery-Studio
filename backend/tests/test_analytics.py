from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from evaluation.analytics import BenchmarkAnalytics
from evaluation.report import BenchmarkReportBuilder


def case(**overrides):
    row = {
        "case_id": "CASE-001",
        "scenario": "growth_ops",
        "category": "trend_summary",
        "query_type": "time_trend",
        "difficulty": "easy",
        "sql_execution_success": True,
        "execution_ms": 100.0,
        "result_correct": True,
        "agent_metrics": {
            "tool_call_count": 1,
            "tool_success_rate": 1.0,
            "permission_check_count": 1,
            "permission_success_rate": 1.0,
            "clarification_rate": 0.0,
        },
    }
    row.update(overrides)
    return row


class BenchmarkAnalyticsTest(unittest.TestCase):
    def test_single_scenario_aggregation(self) -> None:
        result = BenchmarkAnalytics.analyze([case()])
        metrics = result["scenario_metrics"]["growth_ops"]
        self.assertEqual(metrics["case_count"], 1)
        self.assertEqual(metrics["result_accuracy"], 1.0)
        self.assertEqual(metrics["sql_execution_success_rate"], 1.0)
        self.assertEqual(metrics["tool_success_rate"], 1.0)

    def test_multiple_scenarios(self) -> None:
        result = BenchmarkAnalytics.build([
            case(),
            case(case_id="CASE-002", scenario="finance", result_correct=False,
                 sql_execution_success=False, execution_ms=250.0),
        ])
        self.assertEqual(set(result["scenario_metrics"]), {"growth_ops", "finance"})
        self.assertEqual(result["scenario_metrics"]["finance"]["result_accuracy"], 0.0)

    def test_category_statistics(self) -> None:
        result = BenchmarkAnalytics.analyze([
            case(),
            case(case_id="CASE-002", category="trend_summary", result_correct=False),
        ])
        metrics = result["category_metrics"]["trend_summary"]
        self.assertEqual(metrics["case_count"], 2)
        self.assertEqual(metrics["result_accuracy"], 0.5)
        self.assertEqual(metrics["sql_execution_success_rate"], 1.0)

    def test_difficulty_statistics(self) -> None:
        result = BenchmarkAnalytics.analyze([
            case(),
            case(case_id="CASE-002", difficulty="hard", execution_ms=300.0),
        ])
        self.assertEqual(result["difficulty_metrics"]["easy"]["average_execution_ms"], 100.0)
        self.assertEqual(result["difficulty_metrics"]["hard"]["average_execution_ms"], 300.0)

    def test_query_type_statistics(self) -> None:
        result = BenchmarkAnalytics.analyze([
            case(),
            case(case_id="CASE-002", query_type="ranking", result_correct=False),
        ])
        self.assertEqual(result["query_type_metrics"]["time_trend"]["result_accuracy"], 1.0)
        self.assertEqual(result["query_type_metrics"]["ranking"]["result_accuracy"], 0.0)

    def test_empty_cases(self) -> None:
        result = BenchmarkAnalytics.analyze([])
        self.assertEqual(result, {
            "scenario_metrics": {},
            "category_metrics": {},
            "difficulty_metrics": {},
            "query_type_metrics": {},
            "error_metrics": {
                "error_distribution": {},
                "failure_rate": 0.0,
                "successful_case_count": 0,
                "failed_case_count": 0,
                "scenario_error_analysis": {},
                "category_error_analysis": {},
                "difficulty_error_analysis": {},
            },
        })

    def test_report_markdown_contains_all_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "benchmark_report.md"
            BenchmarkReportBuilder.write_markdown([case()], output)
            content = output.read_text(encoding="utf-8")

        self.assertIn("## Overall Performance", content)
        self.assertIn("## Scenario Performance", content)
        self.assertIn("## Category Performance", content)
        self.assertIn("## Difficulty Analysis", content)
        self.assertIn("## Query Type Analysis", content)
        self.assertIn("growth_ops", content)


if __name__ == "__main__":
    unittest.main()
