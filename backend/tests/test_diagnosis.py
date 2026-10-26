from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from evaluation.analytics import BenchmarkAnalytics
from evaluation.diagnosis import FailureDiagnosis
from evaluation.report import BenchmarkReportBuilder


def case(**overrides):
    row = {
        "case_id": "CASE-001",
        "scenario": "growth_ops",
        "category": "trend",
        "difficulty": "easy",
        "query_type": "time_trend",
        "sql_execution_success": True,
        "generated_sql": "SELECT 1",
        "result_correct": True,
    }
    row.update(overrides)
    return row


class FailureDiagnosisTest(unittest.TestCase):
    def test_single_error_and_successful_case_count(self) -> None:
        diagnosis = FailureDiagnosis.analyze([
            case(result_correct=False),
            case(case_id="CASE-002"),
        ])
        self.assertEqual(diagnosis["error_distribution"], {"RESULT_COMPARISON_ERROR": 1})
        self.assertEqual(diagnosis["failure_rate"], 0.5)
        self.assertEqual(diagnosis["successful_case_count"], 1)
        self.assertEqual(diagnosis["failed_case_count"], 1)

    def test_multiple_errors_count_each_case_once(self) -> None:
        rows = [
            case(result_correct=False, error_stage="query_embedding", benchmark_error="failed"),
            case(case_id="CASE-002", result_correct=False, sql_execution_success=False,
                 trace={"permission": {"sql_blocked": True}}),
            case(case_id="CASE-003", result_correct=False,
                 trace={"tool_calls": [{"success": False}]},
                 error_stage="mcp_tool", benchmark_error="failed"),
        ]
        diagnosis = FailureDiagnosis.build(rows)
        self.assertEqual(diagnosis["failed_case_count"], 3)
        self.assertEqual(diagnosis["failure_rate"], 1.0)
        self.assertEqual(diagnosis["error_distribution"], {
            "MODEL_ERROR": 1, "PERMISSION_ERROR": 1, "MCP_TOOL_ERROR": 1,
        })

    def test_scenario_error_analysis(self) -> None:
        rows = [
            case(result_correct=False, error_stage="query_embedding"),
            case(case_id="CASE-002", scenario="finance", result_correct=False),
        ]
        analysis = FailureDiagnosis.analyze(rows)["scenario_error_analysis"]
        self.assertEqual(analysis["growth_ops"], {"MODEL_ERROR": 1})
        self.assertEqual(analysis["finance"], {"RESULT_COMPARISON_ERROR": 1})

    def test_category_error_analysis(self) -> None:
        analysis = FailureDiagnosis.analyze([
            case(result_correct=False, category="ranking", error_stage="schema_retrieval"),
        ])["category_error_analysis"]
        self.assertEqual(analysis["ranking"], {"SCHEMA_RETRIEVAL_ERROR": 1})

    def test_difficulty_error_analysis(self) -> None:
        analysis = FailureDiagnosis.analyze([
            case(result_correct=False, difficulty="hard", sql_execution_success=False,
                 generated_sql=""),
        ])["difficulty_error_analysis"]
        self.assertEqual(analysis["hard"], {"SQL_GENERATION_ERROR": 1})

    def test_empty_results(self) -> None:
        diagnosis = FailureDiagnosis.analyze([])
        self.assertEqual(diagnosis["error_distribution"], {})
        self.assertEqual(diagnosis["failure_rate"], 0.0)
        self.assertEqual(diagnosis["successful_case_count"], 0)
        self.assertEqual(diagnosis["failed_case_count"], 0)
        self.assertEqual(diagnosis["scenario_error_analysis"], {})
        self.assertEqual(diagnosis["category_error_analysis"], {})
        self.assertEqual(diagnosis["difficulty_error_analysis"], {})

    def test_analytics_and_markdown_include_diagnosis(self) -> None:
        rows = [case(result_correct=False, error_stage="query_embedding")]
        analytics = BenchmarkAnalytics.analyze(rows)
        self.assertEqual(analytics["error_metrics"]["error_distribution"], {"MODEL_ERROR": 1})
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "benchmark_live_classic_report.md"
            summary = BenchmarkReportBuilder.write_markdown(rows, output)
            content = output.read_text(encoding="utf-8")
        self.assertEqual(summary.summary_metrics["error_metrics"]["failed_case_count"], 1)
        for section in (
            "## Failure Diagnosis", "### Error Distribution",
            "### Scenario Failure Analysis", "### Category Failure Analysis",
            "### Difficulty Failure Analysis",
        ):
            self.assertIn(section, content)
        self.assertIn("| growth_ops | MODEL_ERROR | 1 |", content)


if __name__ == "__main__":
    unittest.main()
