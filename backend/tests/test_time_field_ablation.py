from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evaluation.time_field_ablation import (
    TimeFieldExperiment,
    build_time_field_ablation,
    current_schema_version,
    has_explicit_time_request,
    main,
    render_markdown,
)


PREFIX = "short_video_ops."


def make_case(
    *,
    question: str = "查询2026年每个月的新增用户数",
    fields: tuple[str, ...] = ("growth_daily_metrics.new_users",),
    gold: tuple[str, ...] = ("growth_daily_metrics.new_users", "growth_daily_metrics.metric_date"),
    scenario: str = "growth_ops",
    limit: int = 20,
) -> dict:
    return {
        "case_id": "CASE-1",
        "scenario": scenario,
        "query": question,
        "gold_fields": [PREFIX + field for field in gold],
        "retrieval": {
            "index_version": "v1",
            "embedding_model": "embed",
            "rerank_model": "rerank",
            "config": {"max_schema_fields": limit},
            "stages": {
                "final": {
                    "candidates": [{"doc_id": PREFIX + field} for field in fields],
                },
            },
        },
    }


class TimeFieldAblationTest(unittest.TestCase):
    def test_explicit_time_cue(self) -> None:
        self.assertTrue(has_explicit_time_request("查询2026年每个月的新增用户数"))
        self.assertTrue(has_explicit_time_request("2026-04激活率"))
        self.assertFalse(has_explicit_time_request("查询新增用户数"))

    def test_metric_catalog_proposes_time_field_without_using_gold(self) -> None:
        experiment = TimeFieldExperiment()
        case = make_case()
        original = experiment.propose(case)
        changed_gold = copy.deepcopy(case)
        changed_gold["gold_fields"] = ["invented.gold.field"]
        self.assertEqual(experiment.propose(changed_gold), original)
        self.assertEqual(original["matched_metrics"], ["new_users"])
        self.assertEqual(original["proposals"], [{
            "doc_id": PREFIX + "growth_daily_metrics.metric_date",
            "reason": "metric:new_users",
        }])

    def test_no_time_cue_no_source_table_or_no_permission(self) -> None:
        experiment = TimeFieldExperiment()
        self.assertEqual(experiment.propose(make_case(question="查询新增用户数"))["proposals"], [])
        self.assertEqual(experiment.propose(make_case(fields=("users.user_id",)))["proposals"], [])
        self.assertEqual(experiment.propose(make_case(scenario="unknown"))["proposals"], [])

    def test_ratio_and_comparison_rule_propose_two_time_fields(self) -> None:
        case = make_case(
            question="比较2026-04各渠道激活率与目标差距",
            fields=("user_registrations.registration_id", "growth_targets.activation_rate_target"),
        )
        proposals = TimeFieldExperiment().propose(case)["proposals"]
        self.assertEqual(
            [item["doc_id"] for item in proposals],
            [
                PREFIX + "user_registrations.registered_at",
                PREFIX + "growth_targets.target_month",
            ],
        )

    def test_schema_fallback_covers_metric_missing_from_catalog(self) -> None:
        case = make_case(
            question="查询2026年每个月的七日留存用户数",
            fields=("growth_daily_metrics.day7_retained_users",),
        )
        experiment = TimeFieldExperiment()
        self.assertEqual(experiment.propose(case, include_schema_fallback=False)["proposals"], [])
        self.assertEqual(experiment.propose(case)["proposals"], [{
            "doc_id": PREFIX + "growth_daily_metrics.metric_date",
            "reason": "schema_metric:" + PREFIX + "growth_daily_metrics.day7_retained_users",
        }])

    def test_append_and_reserve_expose_field_tradeoff(self) -> None:
        case = make_case(
            fields=("growth_daily_metrics.new_users", "growth_daily_metrics.activated_users"),
            gold=(
                "growth_daily_metrics.new_users", "growth_daily_metrics.activated_users",
                "growth_daily_metrics.metric_date",
            ),
            limit=2,
        )
        result = build_time_field_ablation({"cases": [case]})
        self.assertEqual(result["variants"]["baseline"]["average_recall"], 0.666667)
        self.assertEqual(result["variants"]["append"]["average_recall"], 1.0)
        self.assertEqual(result["variants"]["append"]["average_field_count"], 3.0)
        self.assertEqual(result["variants"]["catalog_append"]["average_recall"], 1.0)
        self.assertEqual(result["variants"]["reserve"]["average_recall"], 0.666667)
        self.assertEqual(
            result["variants"]["reserve"]["lost_gold_fields_vs_final"],
            {"CASE-1": [PREFIX + "growth_daily_metrics.activated_users"]},
        )
        self.assertEqual(
            result["case_details"][0]["reserve_evicted_fields"],
            [PREFIX + "growth_daily_metrics.activated_users"],
        )

    def test_empty_and_mixed_index_versions(self) -> None:
        self.assertEqual(build_time_field_ablation({"cases": []})["analyzed_case_count"], 0)
        first, second = make_case(), make_case()
        second["case_id"] = "CASE-2"
        second["retrieval"]["index_version"] = "v2"
        with self.assertRaisesRegex(ValueError, "different index"):
            build_time_field_ablation({"cases": [first, second]})

    def test_report_and_cli_do_not_change_input(self) -> None:
        diagnosis = {"cases": [make_case()]}
        report = render_markdown(build_time_field_ablation(diagnosis))
        self.assertIn("growth_daily_metrics.metric_date", report)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "diagnosis.json"
            source.write_text(json.dumps(diagnosis), encoding="utf-8")
            before = source.read_bytes()
            with patch("sys.argv", ["time_field_ablation", "--input", str(source)]):
                main()
            self.assertEqual(source.read_bytes(), before)
            self.assertTrue(source.with_name("diagnosis_time_field_ablation.json").exists())
            self.assertTrue(source.with_name("diagnosis_time_field_ablation.md").exists())

    def test_current_schema_version_matches_retrieval_index_algorithm(self) -> None:
        from app.retrieval.service import SchemaIndex

        self.assertEqual(current_schema_version(), SchemaIndex._schema_signature()[:12])


if __name__ == "__main__":
    unittest.main()
