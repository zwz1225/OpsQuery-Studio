from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evaluation.retrieval_ablation import build_ablation, main, render_markdown


CONFIG = {
    "bm25_top_k": 2,
    "dense_top_k": 2,
    "rrf_top_k": 3,
    "rerank_threshold": 0.55,
    "max_schema_fields": 2,
}


def candidates(*items: tuple[str, float]) -> list[dict]:
    return [
        {"doc_id": name, "rank": rank, "score": score}
        for rank, (name, score) in enumerate(items, 1)
    ]


def case(case_id: str, gold: list[str], bm25, dense, rrf, rerank, final) -> dict:
    return {
        "case_id": case_id,
        "gold_fields": gold,
        "retrieval": {
            "index_version": "v1",
            "embedding_model": "embedding",
            "rerank_model": "rerank",
            "config": dict(CONFIG),
            "stages": {
                name: {"candidates": rows}
                for name, rows in {
                    "bm25": bm25, "dense": dense, "rrf": rrf,
                    "rerank": rerank, "final": final,
                }.items()
            },
        },
    }


def fixture() -> dict:
    return {
        "cases": [
            case(
                "A", ["a", "b"],
                candidates(("a", 1), ("c", 0.5)),
                candidates(("b", 0.9), ("c", 0.8)),
                candidates(("a", 0.03), ("b", 0.02), ("c", 0.01)),
                candidates(("a", 0.9), ("b", 0.52), ("c", 0.45)),
                candidates(("a", 0.9)),
            ),
            case(
                "B", ["x"],
                candidates(("x", 1), ("y", 0.5)),
                candidates(("y", 0.9), ("x", 0.8)),
                candidates(("y", 0.03), ("x", 0.02)),
                candidates(("y", 0.8), ("x", 0.7)),
                candidates(("y", 0.8), ("x", 0.7)),
            ),
        ]
    }


class RetrievalAblationTest(unittest.TestCase):
    def test_threshold_recovery_is_reported_against_recorded_final(self) -> None:
        result = build_ablation(fixture(), cutoffs=(1, 2), field_limits=(2,), thresholds=(0.50, 0.55))
        self.assertEqual(result["baseline_final"]["average_recall"], 0.75)
        self.assertEqual(result["baseline_final"]["complete_gold_coverage_count"], 1)
        relaxed = result["selection_experiments"]["rerank_limit_2_threshold_0.50"]
        self.assertEqual(relaxed["complete_gold_coverage_count"], 2)
        self.assertEqual(relaxed["gained_gold_fields_vs_final"], {"A": ["b"]})
        self.assertEqual(relaxed["lost_gold_fields_vs_final"], {})
        current = result["selection_experiments"]["rerank_limit_2_threshold_0.55"]
        self.assertEqual(current["average_recall"], result["baseline_final"]["average_recall"])
        self.assertEqual(current["gained_gold_fields_vs_final"], {})
        self.assertEqual(current["lost_gold_fields_vs_final"], {})

    def test_stage_top_k_can_gain_and_lose_different_gold_fields(self) -> None:
        result = build_ablation(fixture(), cutoffs=(1, 2, 3), field_limits=(), thresholds=())
        dense_top_1 = result["ranking_experiments"]["dense_top_1"]
        self.assertEqual(dense_top_1["gained_gold_fields_vs_final"], {"A": ["b"]})
        self.assertEqual(dense_top_1["lost_gold_fields_vs_final"], {"A": ["a"], "B": ["x"]})
        self.assertNotIn("bm25_top_3", result["ranking_experiments"])
        self.assertIn("rrf_top_3", result["ranking_experiments"])

    def test_recorded_final_mismatch_is_rejected(self) -> None:
        data = fixture()
        data["cases"][0]["retrieval"]["stages"]["final"]["candidates"] = []
        with self.assertRaisesRegex(ValueError, "cannot be reproduced"):
            build_ablation(data)

    def test_mixed_index_versions_are_rejected(self) -> None:
        data = fixture()
        data["cases"][1]["retrieval"]["index_version"] = "v2"
        with self.assertRaisesRegex(ValueError, "different index"):
            build_ablation(data)

    def test_failed_case_is_excluded_and_empty_input_is_safe(self) -> None:
        data = fixture()
        data["cases"].append({"case_id": "FAILED", "error": "timeout"})
        result = build_ablation(data)
        self.assertEqual(result["source_case_count"], 3)
        self.assertEqual(result["analyzed_case_count"], 2)
        self.assertEqual(result["excluded_case_ids"], ["FAILED"])
        empty = build_ablation({"cases": []})
        self.assertIsNone(empty["baseline_final"]["average_recall"])
        self.assertEqual(empty["ranking_experiments"], {})

    def test_markdown_and_json_serialization(self) -> None:
        result = build_ablation(fixture(), cutoffs=(2,), field_limits=(2,), thresholds=(0.5,))
        markdown = render_markdown(result)
        self.assertIn("Schema Retrieval Offline Ablation", markdown)
        self.assertIn("rerank_limit_2_threshold_0.50", markdown)
        self.assertIn("cannot predict latency", markdown)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ablation.json"
            path.write_text(json.dumps(result), encoding="utf-8")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["analyzed_case_count"], 2)

    def test_cli_reads_diagnosis_without_overwriting_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "diagnosis.json"
            source.write_text(json.dumps(fixture()), encoding="utf-8")
            original = source.read_bytes()
            with patch("sys.argv", ["retrieval_ablation", "--input", str(source)]):
                main()
            self.assertEqual(source.read_bytes(), original)
            output = source.with_name("diagnosis_ablation.json")
            self.assertTrue(output.exists())
            self.assertTrue(output.with_suffix(".md").exists())
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["analyzed_case_count"], 2)


if __name__ == "__main__":
    unittest.main()
