from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from evaluation.run_benchmark import (
    CASES_PATH, compare_results, compare_results_strict, load_cases, summarize,
)
from evaluation.cases.calibrate_order import EXPLICIT_ORDER_PHRASES
from evaluation.run_manifest import build_run_manifest, comparison_identity, EVALUATOR_FILES


class StrictComparisonTest(unittest.TestCase):
    def test_equal_numbers_under_wrong_business_column_fail(self) -> None:
        correct, reason = compare_results_strict(
            ["gross_revenue"], [{"gross_revenue": 100}],
            ["net_revenue"], [{"net_revenue": 100}], False,
        )
        self.assertFalse(correct)
        self.assertIn("net_revenue", reason)

    def test_declared_alias_and_auxiliary_column_are_allowed(self) -> None:
        correct, _ = compare_results_strict(
            ["user_total", "debug"], [{"user_total": 2, "debug": "a"}],
            ["users"], [{"users": 2}], False,
            column_aliases={"users": ["user_total"]},
            allowed_auxiliary_columns=["debug"],
        )
        self.assertTrue(correct)

    def test_duplicate_rows_and_order_are_checked(self) -> None:
        self.assertFalse(compare_results_strict(
            ["name"], [{"name": "A"}, {"name": "B"}],
            ["name"], [{"name": "A"}, {"name": "A"}], False,
        )[0])

    def test_unscored_results_do_not_lower_accuracy(self) -> None:
        summary = summarize([
            {"result_correct": True, "strict_result_correct": True,
             "sql_execution_success": True, "execution_ms": 1},
            {"result_correct": None, "strict_result_correct": None,
             "sql_execution_success": False},
        ], "gold")
        self.assertEqual(summary["result_accuracy"], 1.0)
        self.assertEqual(summary["result_scored_count"], 1)
        self.assertEqual(summary["unscored_count"], 1)

    def test_cached_gold_does_not_report_zero_execution_latency(self) -> None:
        summary = summarize([{
            "result_correct": True, "strict_result_correct": True,
            "sql_execution_success": True, "execution_ms": None,
        }], "gold")
        self.assertIsNone(summary["average_execution_ms"])
        self.assertIsNone(summary["p95_execution_ms"])

    def test_primary_order_allows_ties_but_not_unsorted_groups(self) -> None:
        columns = ["name", "score"]
        expected = [
            {"name": "A", "score": 2}, {"name": "B", "score": 2},
            {"name": "C", "score": 1},
        ]
        tied = [expected[1], expected[0], expected[2]]
        unsorted = [expected[2], expected[0], expected[1]]
        for comparator in (compare_results, compare_results_strict):
            self.assertTrue(comparator(
                columns, tied, columns, expected, True, order_by_column="score",
            )[0])
            self.assertFalse(comparator(
                columns, unsorted, columns, expected, True, order_by_column="score",
            )[0])

    def test_explicitly_sorted_cases_have_order_annotations(self) -> None:
        cases = load_cases(CASES_PATH, set(), False)
        explicit = [case for case in cases if any(
            phrase in case["query"] for phrase in EXPLICIT_ORDER_PHRASES
        )]
        self.assertEqual(len(explicit), 180)
        self.assertTrue(all(case["order_sensitive"] for case in explicit))
        self.assertTrue(all(
            case.get("order_by_column") in case["expected_columns"]
            for case in explicit if len(case["expected_rows"]) > 1
        ))

    def test_column_aliases_are_scoped_to_the_case(self) -> None:
        cases = {case["case_id"]: case for case in load_cases(CASES_PATH, set(), False)}
        new_users = cases["GROWTH_OPS-001"]
        activated = cases["GROWTH_OPS-002"]
        expected_columns = ["month", "value"]
        expected_rows = [{"month": "2026-01", "value": 10}]
        self.assertTrue(compare_results_strict(
            ["month", "new_users"], [{"month": "2026-01", "new_users": 10}],
            expected_columns, expected_rows, True,
            order_by_column="month", column_aliases=new_users["column_aliases"],
        )[0])
        self.assertFalse(compare_results_strict(
            ["month", "new_users"], [{"month": "2026-01", "new_users": 10}],
            expected_columns, expected_rows, True,
            order_by_column="month", column_aliases=activated["column_aliases"],
        )[0])
        self.assertFalse(compare_results_strict(
            ["name"], [{"name": "B"}, {"name": "A"}],
            ["name"], [{"name": "A"}, {"name": "B"}], True,
        )[0])

    def test_phase83_aliases_do_not_allow_extra_columns_or_wrong_values(self) -> None:
        cases = {case["case_id"]: case for case in load_cases(CASES_PATH, set(), False)}
        growth = cases["GROWTH_OPS-100"]
        self.assertFalse(compare_results_strict(
            ["register_platform", "total_play_count", "distinct_user_count",
             "avg_play_per_user"],
            [{"register_platform": "iOS", "total_play_count": 248528,
              "distinct_user_count": 2002, "avg_play_per_user": 124.14}],
            ["platform", "plays_per_user"],
            [{"platform": "iOS", "plays_per_user": 124.14}], False,
            column_aliases=growth["column_aliases"],
        )[0])

        content = cases["CONTENT_OPS-052"]
        self.assertFalse(compare_results_strict(
            ["内容分类", "内容数量", "平均视频时长"],
            [{"内容分类": "生活", "内容数量": 1360, "平均视频时长": 92.20}],
            ["category_name", "contents", "avg_duration_seconds"],
            [{"category_name": "生活", "contents": 1383,
              "avg_duration_seconds": 92.41}], False,
            column_aliases=content["column_aliases"],
        )[0])

    def test_phase83_case_accepts_reviewed_names_from_both_runs(self) -> None:
        cases = {case["case_id"]: case for case in load_cases(CASES_PATH, set(), False)}
        aliases = cases["CHANNEL_OPS-026"]["column_aliases"]
        expected_columns = ["channel_name", "impressions", "clicks", "ctr"]
        expected_rows = [{"channel_name": "A", "impressions": 100,
                          "clicks": 5, "ctr": 0.05}]
        for columns, row in (
            (["channel_name", "impressions", "clicks", "click_through_rate"],
             {"channel_name": "A", "impressions": 100, "clicks": 5,
              "click_through_rate": 0.05}),
            (["channel_name", "total_impressions", "total_clicks", "click_through_rate"],
             {"channel_name": "A", "total_impressions": 100, "total_clicks": 5,
              "click_through_rate": 0.05}),
        ):
            self.assertTrue(compare_results_strict(
                columns, [row], expected_columns, expected_rows, False,
                column_aliases=aliases,
            )[0])

    def test_content_topn_tie_accepts_only_verified_cutoff_members(self) -> None:
        case = next(case for case in load_cases(CASES_PATH, set(), False)
                    if case["case_id"] == "CONTENT_OPS-025")
        expected = case["expected_rows"]
        policy = case["top_n_tie_policy"]
        alternate = expected[:7] + policy["boundary_candidates"][3:6]
        columns = case["expected_columns"]

        def check(rows, *, policy_enabled=True):
            kwargs = {"order_by_column": "plays"}
            if policy_enabled:
                kwargs["top_n_tie_policy"] = policy
            return compare_results_strict(
                columns, rows, columns, expected, True, **kwargs,
            )[0]

        self.assertTrue(check(alternate))
        self.assertFalse(check(alternate, policy_enabled=False))
        self.assertFalse(check(alternate[1:] + [expected[7]]))
        self.assertFalse(check(alternate[:7] +
                               [{"content_title": "invented", "plays": 8}] +
                               alternate[8:]))
        self.assertFalse(check(alternate[:9] + [alternate[7]]))
        self.assertFalse(check(alternate[:9] +
                               [{"content_title": alternate[9]["content_title"],
                                 "plays": 7}]))
        self.assertFalse(check(alternate[7:] + alternate[:7]))
        self.assertFalse(check(alternate[:-1]))

        aliased = [{"content_title": row["content_title"],
                    "play_count": row["plays"]} for row in alternate]
        self.assertTrue(compare_results_strict(
            ["content_title", "play_count"], aliased, columns, expected, True,
            order_by_column="plays", column_aliases=case["column_aliases"],
            top_n_tie_policy=policy,
        )[0])
        self.assertTrue(compare_results(
            ["content_title", "play_count"], aliased, columns, expected, True,
            order_by_column="plays", top_n_tie_policy=policy,
        )[0])
        self.assertFalse(compare_results_strict(
            ["content_title", "play_count", "extra"],
            [{**row, "extra": 1} for row in aliased], columns, expected, True,
            order_by_column="plays", column_aliases=case["column_aliases"],
            top_n_tie_policy=policy,
        )[0])


class RunManifestTest(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        for name in (*EVALUATOR_FILES, "app/query.py", "app/skills/database_query/SKILL.md",
                     "data/metrics/metric_catalog.json",
                     "evaluation/run_benchmark.py", "evaluation/run_e2e.py",
                     "evaluation/gold_result.py",
                     "evaluation/gold_sql.py",
                     "evaluation/models.py", "evaluation/cases/all_cases.jsonl",
                     "data/databases/short_video_ops/_schema.json",
                     "data/databases/short_video_ops/table.csv"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name, encoding="utf-8")
        self.cases = [{"case_id": "A", "query": "count users"}]

    def build(self):
        return build_run_manifest(
            self.cases, base_dir=self.root, mode="live", scope="classic",
            config={"user_roles": ["growth"], "evaluation_date": "2026-09-28"},
            case_source=self.root / "evaluation/cases/all_cases.jsonl",
        )

    def test_run_identity_is_stable_but_run_id_is_unique(self) -> None:
        first, second = self.build(), self.build()
        self.assertEqual(first["fingerprint"], second["fingerprint"])
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual(comparison_identity(first), comparison_identity(second))

    def test_case_content_data_and_evaluator_changes_invalidate_run(self) -> None:
        first = self.build()
        self.cases[0]["query"] = "count active users"
        case_changed = self.build()
        self.assertNotEqual(first["dataset"]["version"], case_changed["dataset"]["version"])
        (self.root / "data/databases/short_video_ops/table.csv").write_text("new", encoding="utf-8")
        data_changed = self.build()
        self.assertNotEqual(case_changed["versions"]["data"], data_changed["versions"]["data"])
        (self.root / "evaluation/run_benchmark.py").write_text("new", encoding="utf-8")
        evaluator_changed = self.build()
        self.assertNotEqual(
            data_changed["versions"]["evaluator"], evaluator_changed["versions"]["evaluator"]
        )

    def test_no_empty_or_duplicate_dataset(self) -> None:
        self.cases = []
        with self.assertRaises(ValueError):
            self.build()
        self.cases = [{"case_id": "A"}, {"case_id": "A"}]
        with self.assertRaises(ValueError):
            self.build()


if __name__ == "__main__":
    unittest.main()
