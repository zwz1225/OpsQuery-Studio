from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from evaluation.report import BenchmarkReportBuilder


def case(**overrides):
    row = {
        "case_id": "CASE-001",
        "sql_execution_success": True,
        "execution_ms": 100.0,
        "result_correct": True,
        "column_match": True,
        "schema_recall": 1.0,
        "schema_precision": 0.8,
        "retrieval_ms": 10.0,
        "benchmark_error": "",
        "error_stage": "",
        "agent_metrics": {
            "tool_call_count": 2,
            "tool_success_rate": 1.0,
            "average_tool_latency_ms": 50.0,
            "permission_check_count": 1,
            "permission_success_rate": 1.0,
            "permission_denied_count": 0,
            "clarification_rate": 0.0,
            "clarification_trigger_count": 0,
            "clarification_resolution_count": 0,
        },
    }
    row.update(overrides)
    return row


class BenchmarkReportBuilderTest(unittest.TestCase):
    def test_empty_results(self) -> None:
        summary = BenchmarkReportBuilder.build([]).to_dict()["summary_metrics"]

        self.assertEqual(summary["overall"]["case_count"], 0)
        self.assertEqual(summary["overall"]["result_accuracy"], 0.0)
        self.assertEqual(summary["agent_behavior"]["tool_call_count"], 0)
        self.assertIsNone(summary["agent_behavior"]["clarification_resolution_rate"])

    def test_single_success_case(self) -> None:
        summary = BenchmarkReportBuilder.build([case()]).to_dict()["summary_metrics"]

        self.assertEqual(summary["overall"]["sql_execution_success_rate"], 1.0)
        self.assertEqual(summary["overall"]["result_accuracy"], 1.0)
        self.assertEqual(summary["overall"]["average_execution_ms"], 100.0)
        self.assertEqual(summary["schema_retrieval"]["schema_recall"], 1.0)

    def test_multiple_cases_aggregate_agent_metrics(self) -> None:
        rows = [
            case(case_id="CASE-001"),
            case(case_id="CASE-002", execution_ms=300.0, result_correct=False,
                 agent_metrics={
                     "tool_call_count": 1,
                     "tool_success_rate": 0.0,
                     "average_tool_latency_ms": 100.0,
                     "permission_check_count": 1,
                     "permission_success_rate": 0.0,
                     "permission_denied_count": 1,
                     "clarification_rate": 1.0,
                     "clarification_trigger_count": 1,
                     "clarification_resolution_count": 1,
                 }),
        ]
        summary = BenchmarkReportBuilder.build(rows).to_dict()["summary_metrics"]

        self.assertEqual(summary["overall"]["case_count"], 2)
        self.assertEqual(summary["overall"]["result_accuracy"], 0.5)
        self.assertEqual(summary["agent_behavior"]["tool_call_count"], 3)
        self.assertAlmostEqual(summary["agent_behavior"]["tool_success_rate"], 2 / 3)
        self.assertEqual(summary["agent_behavior"]["permission_denied_count"], 1)
        self.assertEqual(summary["agent_behavior"]["clarification_resolution_rate"], 1.0)

    def test_error_classification(self) -> None:
        rows = [
            case(benchmark_error="向量模型失败", error_stage="query_embedding"),
            case(case_id="CASE-002", benchmark_error="当前用户无权访问的数据表",
                 error_stage="schema_access_control"),
            case(case_id="CASE-003", benchmark_error="DuckDB执行失败", error_stage="sql_execution"),
        ]
        analysis = BenchmarkReportBuilder.build(rows).to_dict()["summary_metrics"]["error_analysis"]

        self.assertEqual(analysis["error_count"], 3)
        self.assertEqual(analysis["error_distribution"], {
            "query_embedding": 1,
            "permission": 1,
            "sql_execution": 1,
        })

    def test_markdown_generation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "benchmark_report.md"
            BenchmarkReportBuilder.write_markdown([case()], output)
            content = output.read_text(encoding="utf-8")

        self.assertIn("# AskData Studio Benchmark Report", content)
        self.assertIn("## Overall Performance", content)
        self.assertIn("## Schema Retrieval", content)
        self.assertIn("## Agent Behavior", content)
        self.assertIn("## Error Analysis", content)

    def test_nested_result_fields_are_supported(self) -> None:
        row = {
            "sql_metrics": {"execution_success": True, "execution_ms": 20},
            "result_metrics": {"correct": True, "column_match": True},
            "schema_metrics": {"recall": 0.5, "precision": 0.25, "retrieval_ms": 5},
            "agent_metrics": {},
        }
        summary = BenchmarkReportBuilder.build([row]).to_dict()["summary_metrics"]
        self.assertEqual(summary["overall"]["result_accuracy"], 1.0)
        self.assertEqual(summary["schema_retrieval"]["schema_recall"], 0.5)
        json.dumps(summary, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
