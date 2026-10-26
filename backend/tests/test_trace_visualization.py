from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from evaluation.trace import EvaluationTrace
from evaluation.trace_report import TraceReportBuilder
from evaluation.trace_visualizer import TraceVisualizer


def complete_trace() -> EvaluationTrace:
    return EvaluationTrace(
        request={"case_id": "GROWTH_OPS-001", "question": "用户增长是多少？"},
        routing={"route": "database_query"},
        schema_retrieval={
            "retrieved_fields": ["users.user_id"], "recall": 0.5,
            "precision": 0.05, "latency_ms": 571,
        },
        agent_decision={"action": "execute_sql"},
        tool_calls=[{
            "tool_name": "query_short_video_ops", "success": True,
            "latency_ms": 1700, "retry_count": 0,
        }],
        sql_execution={"generated_sql": "SELECT COUNT(*) FROM users", "success": True,
                       "execution_ms": 120},
        result_comparison={"comparison_target": "gold_result", "correct": True},
    )


def by_name(nodes: list[dict], name: str) -> dict:
    return next(node for node in nodes if node["name"] == name)


class TraceVisualizationTest(unittest.TestCase):
    def test_complete_trace_has_successful_core_nodes(self) -> None:
        trace = complete_trace()
        nodes = TraceVisualizer.visualize(trace)["nodes"]
        for name in (
            "Request", "Routing", "Schema Retrieval", "Agent Decision",
            "MCP Tool Call", "SQL Execution", "Result Comparison",
        ):
            self.assertEqual(by_name(nodes, name)["status"], "success")
        self.assertEqual(by_name(nodes, "Schema Retrieval")["metrics"]["recall"], 0.5)
        self.assertEqual(by_name(nodes, "MCP Tool Call")["latency_ms"], 1700)
        self.assertEqual(TraceVisualizer.build(trace.to_dict()), {"nodes": nodes})

    def test_sql_failure_skips_result_comparison(self) -> None:
        trace = complete_trace()
        trace.sql_execution = {
            "generated_sql": "SELECT missing FROM users", "success": False,
            "execution_ms": 30,
        }
        trace.result_comparison = {"correct": False, "reason": "no such column: missing"}
        nodes = TraceVisualizer.visualize(trace)["nodes"]
        self.assertEqual(by_name(nodes, "SQL Execution")["status"], "failed")
        self.assertEqual(by_name(nodes, "SQL Execution")["metrics"]["error"],
                         "no such column: missing")
        self.assertEqual(by_name(nodes, "Result Comparison")["status"], "skipped")

    def test_tool_failure_is_visible(self) -> None:
        trace = complete_trace()
        trace.tool_calls = [{"tool_name": "query_short_video_ops", "success": False,
                             "latency_ms": 50, "error": "connection lost"}]
        node = by_name(TraceVisualizer.visualize(trace)["nodes"], "MCP Tool Call")
        self.assertEqual(node["status"], "failed")
        self.assertEqual(node["metrics"]["error"], "connection lost")

    def test_multiple_tool_calls_are_shown_individually(self) -> None:
        trace = complete_trace()
        trace.tool_calls.append({"tool_name": "execute_sql", "success": False, "latency_ms": 8})
        tools = [node for node in TraceVisualizer.visualize(trace)["nodes"]
                 if node["name"] == "MCP Tool Call"]
        self.assertEqual([node["status"] for node in tools], ["success", "failed"])

    def test_incorrect_result_is_failed_after_successful_sql(self) -> None:
        trace = complete_trace()
        trace.result_comparison = {"correct": False, "reason": "different rows"}
        nodes = TraceVisualizer.visualize(trace)["nodes"]
        self.assertEqual(by_name(nodes, "SQL Execution")["status"], "success")
        self.assertEqual(by_name(nodes, "Result Comparison")["status"], "failed")

    def test_errors_create_failed_node(self) -> None:
        trace = complete_trace()
        trace.errors = [{"stage": "schema_retrieval", "message": "embedding failed"}]
        nodes = TraceVisualizer.visualize(trace)["nodes"]
        self.assertEqual(by_name(nodes, "Schema Retrieval")["status"], "failed")
        self.assertEqual(by_name(nodes, "Error")["status"], "failed")
        self.assertIn("embedding failed", str(by_name(nodes, "Error")["metrics"]))

    def test_html_contains_timeline_metrics_sql_and_escaped_error(self) -> None:
        trace = complete_trace()
        trace.errors = [{"stage": "sql_execution", "message": "bad <script>alert(1)</script>"}]
        html = TraceReportBuilder.render_html(
            trace, case_id="GROWTH_OPS-001", question="<b>用户增长</b>",
        )
        self.assertIn('<ol class="timeline">', html)
        self.assertIn("Schema Retrieval", html)
        self.assertIn("571 ms", html)
        self.assertIn("1700 ms", html)
        self.assertIn("SELECT COUNT(*) FROM users", html)
        self.assertIn('class="node status-failed"', html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;b&gt;用户增长&lt;/b&gt;", html)

    def test_empty_trace_marks_nodes_skipped_and_explains_missing_data(self) -> None:
        nodes = TraceVisualizer.visualize(EvaluationTrace())["nodes"]
        self.assertTrue(all(node["status"] == "skipped" for node in nodes))
        self.assertIn("No recorded EvaluationTrace", TraceReportBuilder.render_html(EvaluationTrace()))

    def test_cli_writes_one_report_per_case_without_changing_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "benchmark.json"
            source.write_text(json.dumps({"summary": {}, "cases": [
                {"case_id": "GROWTH_OPS-001", "query": "count users",
                 "trace": complete_trace().to_dict()},
                {"case_id": "LEGACY-002", "query": "old query"},
            ]}), encoding="utf-8")
            original = source.read_bytes()
            output = root / "traces"
            result = subprocess.run(
                [sys.executable, "-m", "evaluation.trace_report", "--input", str(source),
                 "--output-dir", str(output)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(len(list(output.glob("trace_*.html"))), 2)
            self.assertTrue((output / "trace_GROWTH_OPS-001.html").exists())
            self.assertIn("No recorded EvaluationTrace",
                          (output / "trace_LEGACY-002.html").read_text(encoding="utf-8"))

    def test_filename_cannot_escape_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            path = TraceReportBuilder.write_case({"case_id": "../unsafe", "trace": {}}, output)
            self.assertEqual(path.parent, output)
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
