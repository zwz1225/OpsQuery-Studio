from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from evaluation.case_selection import load_case_ids, select_cases
from evaluation.retrieval_validation import (
    DEFAULT_CASE_LIST,
    DEFAULT_CASE_SOURCE,
    build_validation_report,
    render_markdown,
)


class RetrievalValidationTest(unittest.TestCase):
    def test_manifest_selects_balanced_nonclassic_gold_cases(self) -> None:
        ids = load_case_ids(DEFAULT_CASE_LIST)
        cases = [
            json.loads(line) for line in DEFAULT_CASE_SOURCE.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        selected = select_cases(cases, ids)
        self.assertEqual(len(selected), 30)
        self.assertEqual(Counter(case["scenario"] for case in selected), {
            "growth_ops": 10, "channel_ops": 10, "content_ops": 10,
        })
        self.assertTrue(all(not case["classic"] for case in selected))
        self.assertTrue(all(case["gold_sql"] and case["gold_fields"] for case in selected))

    def test_rejects_duplicate_and_missing_manifest_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.json"
            path.write_text('{"case_ids":["A","A"]}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                load_case_ids(path)
        with self.assertRaisesRegex(ValueError, "absent"):
            select_cases([{"case_id": "A"}], ["B"])

    def test_baseline_counts_coverage_latency_and_groups(self) -> None:
        cases = [
            {"case_id": "A", "scenario": "growth_ops", "difficulty": "简单",
             "classic": False, "query": "查看每月新增用户", "gold_sql": "SELECT 1",
             "gold_fields": ["db.t.date", "db.t.metric"]},
            {"case_id": "B", "scenario": "channel_ops", "difficulty": "中等",
             "classic": False, "query": "渠道分布", "gold_sql": "SELECT 2",
             "gold_fields": ["db.t.channel"]},
        ]
        benchmark = {"cases": [
            {"case_id": "A", "retrieved_fields": ["db.t.date", "db.t.metric", "db.t.extra"],
             "schema_recall": 1.0, "schema_precision": 2 / 3,
             "retrieval_ms": 100.0, "sql_execution_success": True, "result_correct": True,
             "trace": {"schema_retrieval": {"time_field_supplement": {
                 "added_fields": [{"doc_id": "db.t.date"}]}}}},
            {"case_id": "B", "retrieved_fields": ["db.t.other"],
             "schema_recall": 0.0, "schema_precision": 0.0,
             "retrieval_ms": 200.0, "sql_execution_success": False, "result_correct": False,
             "trace": {"schema_retrieval": {}}},
        ]}
        diagnosis = {"cases": [
            {"case_id": "A", "retrieval": {"timings_ms": {"bm25": 4, "rerank": 20},
                                          "total_latency_ms": 30}},
            {"case_id": "B", "retrieval": {"timings_ms": {"bm25": 6, "rerank": 40},
                                          "total_latency_ms": 50}},
        ]}
        report = build_validation_report(["A", "B"], cases, benchmark, diagnosis)
        self.assertEqual(report["summary"]["complete_gold_coverage_count"], 1)
        self.assertEqual(report["summary"]["average_retrieved_fields"], 2.0)
        self.assertEqual(report["summary"]["p95_retrieval_ms"], 200.0)
        self.assertEqual(report["summary"]["result_accuracy"], 0.5)
        self.assertEqual(report["summary"]["supplemented_case_count"], 1)
        self.assertEqual(report["groups"]["explicit_time_cue=true"]["case_count"], 1)
        self.assertEqual(report["diagnosis_stage_timings"]["rerank"]["average_ms"], 30.0)
        self.assertIn("db.t.channel", render_markdown(report))

    def test_rejects_partial_benchmark_and_diagnosis(self) -> None:
        case = {"case_id": "A", "scenario": "growth_ops", "classic": False,
                "query": "x", "gold_sql": "SELECT 1", "gold_fields": ["db.t.x"]}
        with self.assertRaisesRegex(ValueError, "Benchmark case count"):
            build_validation_report(["A"], [case], {"cases": []})
        with self.assertRaisesRegex(ValueError, "Diagnosis case count"):
            build_validation_report(
                ["A"], [case], {"cases": [{"case_id": "A", "retrieved_fields": []}]},
                {"cases": []},
            )


if __name__ == "__main__":
    unittest.main()
