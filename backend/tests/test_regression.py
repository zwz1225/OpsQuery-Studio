from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from evaluation.regression import RegressionComparator
from evaluation.regression_report import RegressionReportBuilder
from evaluation.snapshot import BenchmarkSnapshotManager
from evaluation.run_manifest import _digest
from evaluation.result_policy import policy_identity


def case(case_id: str, correct: bool, *, latency: float = 100.0,
         error_stage: str = "", tool_rate: float = 1.0, **overrides) -> dict:
    row = {
        "case_id": case_id,
        "scenario": "growth_ops",
        "category": "trend",
        "difficulty": "easy",
        "sql_execution_success": True,
        "execution_ms": latency,
        "generated_sql": "SELECT 1",
        "result_correct": correct,
        "column_match": True,
        "schema_recall": 0.8,
        "schema_precision": 0.5,
        "error_stage": error_stage,
        "benchmark_error": "failed" if error_stage else "",
        "agent_metrics": {
            "tool_call_count": 1,
            "tool_success_rate": tool_rate,
            "permission_check_count": 1,
            "permission_success_rate": 1.0,
            "clarification_rate": 0.0,
        },
    }
    row.update(overrides)
    return row


def snapshot(snapshot_id: str, cases: list[dict], *, accuracy: float | None = None) -> dict:
    summary = {}
    if accuracy is not None:
        summary["result_accuracy"] = accuracy
    report = {
        "snapshot_id": snapshot_id,
        "created_at": "2026-09-24T00:00:00Z",
        "dataset": {"path": "evaluation/cases/all_cases.jsonl", "scope": "classic"},
        "mode": "live",
        "metadata": {"llm_model": "qwen-plus", "embedding_model": "embedding", "rerank_model": "rerank"},
        "summary": summary,
        "cases": cases,
        "run_manifest": {
            "manifest_version": 4,
            "run_id": snapshot_id,
            "scope": "classic",
            "source_identity": {"logical_database_id": "short_video_ops", "source_id": "fixture_duckdb",
                "backend": "duckdb", "dialect": "duckdb", "prompt_dialect": "DuckDB", "physical_schema": "main",
                "data_version": "1"*64, "catalog_version": "2"*64},
            "mode": "live",
            "dataset": {
                "version": ",".join(item["case_id"] for item in cases),
                "case_ids": [item["case_id"] for item in cases],
            },
            "result_policy": policy_identity(cases),
            "source_verification": {"kind": "csv_content_digest", "data_version": "1"*64, "catalog_version": "2"*64},
            "versions": {"data": "1"*64, "schema": "2"*64,
                         "evaluator": "evaluator-v1", "result_policy": _digest(policy_identity(cases))},
            "config": {"user_roles": ["demo_growth_ops"],
                       "evaluation_date": "2026-09-24"},
        },
    }
    report["run_manifest"]["fingerprint"] = _digest({k:v for k,v in report["run_manifest"].items()
        if k not in ("run_id", "created_at", "fingerprint")})
    return report


class RegressionTest(unittest.TestCase):
    def test_snapshot_saves_copy_without_changing_benchmark(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "benchmark_live_classic.json"
            original = {"summary": {"case_count": 1}, "cases": [case("A", True)]}
            source.write_text(json.dumps(original), encoding="utf-8")
            before = source.read_bytes()
            path = BenchmarkSnapshotManager.save(
                source, mode="live", scope="classic",
                snapshot_dir=root / "snapshots",
                created_at=datetime(2026, 9, 24, tzinfo=timezone.utc),
            )
            saved = BenchmarkSnapshotManager.load(path)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(path.name, "benchmark_live_classic_20260924T000000000000Z.json")
            self.assertEqual(saved["snapshot_id"], path.stem)
            self.assertEqual(saved["mode"], "live")
            self.assertEqual(saved["summary"], original["summary"])
            self.assertEqual(saved["cases"], original["cases"])

    def test_snapshot_metadata_has_model_keys_and_uses_supplied_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = BenchmarkSnapshotManager
            path = manager.save(
                {"summary": {}, "cases": []}, mode="gold", scope="all",
                snapshot_dir=directory, metadata={"llm_model": "candidate-model"},
            )
            metadata = manager.load(path)["metadata"]
        self.assertEqual(metadata, {
            "llm_model": "candidate-model", "embedding_model": None, "rerank_model": None,
        })

    def test_accuracy_improvement_and_agent_delta(self) -> None:
        baseline = snapshot("baseline", [case("A", False), case("B", True)], accuracy=0.5)
        candidate = snapshot("candidate", [case("A", True), case("B", True)], accuracy=1.0)
        result = RegressionComparator.compare(baseline, candidate)
        self.assertEqual(result.overall_delta["result_accuracy"], 0.5)
        self.assertEqual(result.overall_delta["sql_execution_success_rate"], 0.0)
        self.assertEqual(result.agent_delta["tool_success_rate"], 0.0)
        self.assertEqual(result.case_changes["failure_to_success"][0]["case_id"], "A")

    def test_latency_delta_uses_candidate_minus_baseline(self) -> None:
        baseline = snapshot("baseline", [case("A", True, latency=100)])
        candidate = snapshot("candidate", [case("A", True, latency=140)])
        result = RegressionComparator.compare(baseline, candidate)
        self.assertEqual(result.overall_delta["average_latency"], 40.0)

    def test_error_distribution_change(self) -> None:
        baseline = snapshot("baseline", [case("A", False, error_stage="query_embedding")])
        candidate = snapshot("candidate", [case("A", True)])
        result = RegressionComparator.compare(baseline, candidate)
        self.assertEqual(result.error_delta["failure_count"], -1)
        self.assertEqual(result.error_delta["error_distribution"]["MODEL_ERROR"], -1)

    def test_case_regressions_improvements_and_result_changes(self) -> None:
        baseline = snapshot("baseline", [case("A", True), case("B", False)])
        candidate = snapshot("candidate", [case("A", False), case("B", True), case("C", True)])
        result = RegressionComparator.compare(
            baseline, candidate, allow_incompatible=True,
        )
        self.assertFalse(result.dataset_match)
        self.assertTrue(result.comparison_warnings)
        self.assertEqual([c["case_id"] for c in result.case_changes["success_to_failure"]], ["A"])
        self.assertEqual([c["case_id"] for c in result.case_changes["failure_to_success"]], ["B"])
        self.assertEqual([c["case_id"] for c in result.case_changes["result_changes"]], ["A", "B"])
        self.assertEqual(result.case_changes["added_cases"], ["C"])

    def test_changed_data_is_not_comparable(self) -> None:
        baseline = snapshot("baseline", [case("A", True)])
        candidate = snapshot("candidate", [case("A", True)])
        candidate["run_manifest"]["versions"]["data"] = "data-v2"
        with self.assertRaisesRegex(ValueError, "data_version differs"):
            RegressionComparator.compare(baseline, candidate)

    def test_missing_case_is_not_counted_as_pass(self) -> None:
        baseline = snapshot("baseline", [case("A", True), case("B", True)])
        candidate = snapshot("candidate", [case("A", True), case("B", True)])
        candidate["cases"].pop()
        with self.assertRaisesRegex(ValueError, "missing or unexpected cases"):
            RegressionComparator.compare(baseline, candidate)

    def test_sql_status_change_is_recorded_when_accuracy_stays_wrong(self) -> None:
        baseline = snapshot("baseline", [case("A", False, sql_execution_success=False)])
        candidate = snapshot("candidate", [case("A", False, sql_execution_success=True)])
        changes = RegressionComparator.compare(baseline, candidate).case_changes
        self.assertEqual(changes["success_to_failure"], [])
        self.assertEqual(changes["result_changes"][0]["baseline_sql_success"], False)
        self.assertEqual(changes["result_changes"][0]["candidate_sql_success"], True)

    def test_markdown_report(self) -> None:
        result = RegressionComparator.compare(
            snapshot("baseline", [case("A", False)]),
            snapshot("candidate", [case("A", True)]),
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "regression_report.md"
            RegressionReportBuilder.write_markdown(result, output)
            content = output.read_text(encoding="utf-8")
        for heading in (
            "## Overall Comparison", "## Metric Delta", "## Improvement Cases",
            "## Regression Cases", "## Error Distribution Change",
        ):
            self.assertIn(heading, content)
        self.assertIn("`A`: failed → successful", content)

    def test_regression_cli_accepts_snapshot_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline = root / "baseline.json"
            candidate = root / "candidate.json"
            output = root / "regression_report.md"
            baseline.write_text(json.dumps(snapshot("baseline", [case("A", False)])), encoding="utf-8")
            candidate.write_text(json.dumps(snapshot("candidate", [case("A", True)])), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "-m", "evaluation.regression", "--baseline", str(baseline),
                 "--candidate", str(candidate), "--output", str(output)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("## Improvement Cases", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
