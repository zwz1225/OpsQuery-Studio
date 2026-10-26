from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from evaluation.insight import BenchmarkInsightGenerator
from evaluation.insight_report import InsightReportBuilder


def healthy_summary(**overrides):
    summary = {
        "case_count": 10,
        "schema_precision": 0.5,
        "schema_recall": 0.9,
        "sql_execution_success_rate": 1.0,
        "result_accuracy": 1.0,
        "average_execution_ms": 200.0,
    }
    summary.update(overrides)
    return summary


def categories(result) -> list[str]:
    return [insight["category"] for insight in result.insights]


class BenchmarkInsightTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = BenchmarkInsightGenerator()

    def test_low_schema_precision_generates_insight(self) -> None:
        result = self.engine.generate(healthy_summary(schema_precision=0.08))
        self.assertEqual(categories(result), ["schema_retrieval"])
        self.assertEqual(result.insights[0]["severity"], "high")
        self.assertIn("8.00%", result.insights[0]["observation"])
        self.assertTrue(result.insights[0]["possible_causes"])
        self.assertTrue(result.insights[0]["suggestions"])

    def test_sql_execution_failure_generates_insight(self) -> None:
        result = self.engine.generate(healthy_summary(sql_execution_success_rate=0.8))
        self.assertEqual(categories(result), ["sql_execution"])

    def test_tool_failure_generates_insight_from_trace_metrics(self) -> None:
        result = self.engine.generate(
            healthy_summary(), trace_metrics={"tool_call_count": 4, "tool_failure_rate": 0.25},
        )
        self.assertEqual(categories(result), ["tool_call"])
        self.assertIn("25.00%", result.insights[0]["observation"])

    def test_permission_denial_generates_investigation_insight(self) -> None:
        result = self.engine.generate(
            healthy_summary(), trace_metrics={"permission_denied_count": 2},
        )
        self.assertEqual(categories(result), ["permission"])
        self.assertTrue(any("预期角色" in step for step in result.insights[0]["suggestions"]))

    def test_latency_above_default_threshold_generates_insight(self) -> None:
        result = self.engine.generate(healthy_summary(average_execution_ms=3001))
        self.assertEqual(categories(result), ["performance"])
        self.assertIn("3000.0 ms", result.insights[0]["observation"])

    def test_healthy_results_generate_no_insight(self) -> None:
        result = self.engine.generate(
            healthy_summary(),
            trace_metrics={"tool_call_count": 1, "tool_failure_rate": 0.0,
                           "permission_denied_count": 0},
        )
        self.assertEqual(result.to_dict(), {"insights": []})
        self.assertEqual(categories(self.engine.generate(healthy_summary(case_count=0))), [])

    def test_regression_triggers_recall_and_accuracy_insights(self) -> None:
        result = self.engine.generate(
            healthy_summary(),
            regression_result={"overall_delta": {"schema_recall": -0.08,
                                                 "result_accuracy": -0.04}},
        )
        self.assertEqual(categories(result), ["schema_retrieval", "result_quality"])
        self.assertIn("下降 8.00%", result.insights[0]["observation"])

    def test_low_absolute_accuracy_generates_quality_insight(self) -> None:
        result = self.engine.generate(healthy_summary(result_accuracy=0.85))
        self.assertEqual(categories(result), ["result_quality"])

    def test_result_comparison_failures_surface_even_above_accuracy_target(self) -> None:
        result = self.engine.generate(
            healthy_summary(result_accuracy=0.95),
            error_metrics={"error_distribution": {"RESULT_COMPARISON_ERROR": 1}},
        )
        self.assertEqual(categories(result), ["result_quality"])
        self.assertIn("1 条", result.insights[0]["observation"])

    def test_existing_agent_and_error_metrics_can_trigger_insights(self) -> None:
        result = self.engine.generate(
            {"summary_metrics": {
                "overall": {"case_count": 4, "sql_execution_success_rate": 1,
                            "result_accuracy": 1, "average_execution_ms": 100},
                "schema_retrieval": {"schema_precision": 0.4},
                "agent_behavior": {"tool_call_count": 2, "tool_success_rate": 0.5,
                                   "permission_denied_count": 0},
            }},
            error_metrics={"error_distribution": {"PERMISSION_ERROR": 1}},
        )
        self.assertEqual(categories(result), ["tool_call", "permission"])

    def test_trace_metrics_fall_back_to_saved_trace(self) -> None:
        metrics = self.engine.trace_metrics_from_cases([{
            "agent_metrics": {"tool_call_count": 2, "permission_denied_count": 0},
            "trace": {"tool_calls": [{"success": True}, {"success": False}],
                      "permission": {"sql_blocked": True},
                      "schema_retrieval": {"latency_ms": 500},
                      "sql_execution": {"execution_ms": 200}},
        }])
        self.assertEqual(metrics["tool_failure_rate"], 0.5)
        self.assertEqual(metrics["permission_denied_count"], 1)
        self.assertEqual(metrics["average_schema_retrieval_ms"], 500.0)
        self.assertEqual(metrics["average_sql_execution_ms"], 200.0)

    def test_latency_observation_includes_recorded_stage_breakdown(self) -> None:
        result = self.engine.generate(
            healthy_summary(average_execution_ms=3500),
            trace_metrics={"average_schema_retrieval_ms": 900,
                           "average_tool_latency_ms": 1400,
                           "average_sql_execution_ms": 3500},
        )
        self.assertIn("Schema Retrieval 900.0 ms", result.insights[0]["observation"])

    def test_sql_error_taxonomy_can_trigger_when_rate_is_missing(self) -> None:
        result = self.engine.generate(
            {"case_count": 2, "result_accuracy": 1.0, "schema_precision": 0.5},
            error_metrics={"error_distribution": {"SQL_EXECUTION_ERROR": 1}},
        )
        self.assertEqual(categories(result), ["sql_execution"])

    def test_markdown_contains_priorities_observation_and_summary(self) -> None:
        result = self.engine.generate(
            healthy_summary(schema_precision=0.05, average_execution_ms=4000),
        )
        with tempfile.TemporaryDirectory() as directory:
            output = InsightReportBuilder.write_markdown(
                result, Path(directory) / "benchmark_insight_report.md",
            )
            content = output.read_text(encoding="utf-8")
        for heading in (
            "# Benchmark Optimization Insight", "## High Priority Issues",
            "## Medium Priority Issues", "## Summary",
        ):
            self.assertIn(heading, content)
        self.assertIn("Observation:", content)
        self.assertIn("Suggestions:", content)
        self.assertIn("Total Issues: 2", content)

    def test_cli_reads_existing_json_without_changing_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "benchmark_live_classic.json"
            output = root / "benchmark_insight_report.md"
            source.write_text(json.dumps({
                "summary": healthy_summary(schema_precision=0.05),
                "cases": [{"case_id": "CASE-001", "result_correct": True}],
            }), encoding="utf-8")
            original = source.read_bytes()
            completed = subprocess.run(
                [sys.executable, "-m", "evaluation.insight_report", "--input", str(source),
                 "--output", str(output)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(source.read_bytes(), original)
            self.assertIn("Schema Retrieval Precision Low", output.read_text(encoding="utf-8"))

    def test_regression_snapshots_add_accuracy_insight(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current_case = {"case_id": "CASE-001", "result_correct": False,
                            "sql_execution_success": True, "generated_sql": "SELECT 1"}
            previous_case = {**current_case, "result_correct": True}
            source = root / "benchmark.json"
            baseline = root / "baseline.json"
            candidate = root / "candidate.json"
            output = root / "insights.md"
            source.write_text(json.dumps({
                "summary": healthy_summary(case_count=1, result_accuracy=0.95),
                "cases": [current_case],
            }), encoding="utf-8")
            from tests.test_regression import snapshot
            manifest = snapshot("insight-fixture", [current_case])["run_manifest"]
            baseline.write_text(json.dumps({"snapshot_id": "base", "summary": {
                "result_accuracy": 1.0}, "cases": [previous_case],
                "run_manifest": manifest}), encoding="utf-8")
            candidate.write_text(json.dumps({"snapshot_id": "new", "summary": {
                "result_accuracy": 0.95}, "cases": [current_case],
                "run_manifest": manifest}), encoding="utf-8")
            result = InsightReportBuilder.from_benchmark(
                source, output=output, baseline=baseline, candidate=candidate,
            )
            self.assertEqual(categories(result), ["result_quality"])
            self.assertIn("下降 5.00%", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
