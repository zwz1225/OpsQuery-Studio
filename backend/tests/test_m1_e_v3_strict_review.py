"""Check saved v3 SQL projections and proposed exact per-case policies."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

import sqlglot

from app.querying.duckdb_engine import DuckDbEngine
from evaluation.run_benchmark import compare_results_strict
from scripts.rescore_m1_e_v3_strict import REVIEWED, amended_case, sha256, SOURCES


BASE = Path(__file__).resolve().parents[1]


class M1EV3StrictReviewTest(unittest.TestCase):
    def test_saved_sql_and_current_data_support_only_reviewed_columns(self) -> None:
        frozen_path = BASE / "evaluation/results/m1_e_all_cases_before_v3_strict4_20261013.jsonl"
        original_path = frozen_path if frozen_path.exists() else BASE / "evaluation/cases/all_cases.jsonl"
        formal = {
            case["case_id"]: case
            for line in original_path.read_text(
                encoding="utf-8").splitlines() if line.strip()
            for case in [json.loads(line)]
        }
        source_rows = {}
        for name, identity in SOURCES.items():
            path = BASE / "evaluation/results" / name
            self.assertEqual(sha256(path), identity["sha256"])
            source_rows.update({row["case_id"]: row for row in json.loads(
                path.read_text(encoding="utf-8"))["cases"]})

        engine = DuckDbEngine()
        with engine.connect("short_video_ops") as connection:
            connection.execute("CREATE SCHEMA askdata_ops")
            for table in (
                "ad_daily_stats", "ad_creatives", "user_daily_activity",
                "user_registrations",
            ):
                connection.execute(
                    f"CREATE VIEW askdata_ops.{table} AS SELECT * FROM main.{table}"
                )
            for case_id, review in REVIEWED.items():
                with self.subTest(case_id=case_id):
                    original, source = formal[case_id], source_rows[case_id]
                    amended = amended_case(original, review)
                    projections = sqlglot.parse_one(
                        source["generated_sql"], read="postgres"
                    ).expressions
                    labels = {item.alias_or_name for item in projections}
                    self.assertTrue(all(
                        actual in labels
                        for aliases in review["aliases"].values() for actual in aliases
                    ))
                    self.assertTrue(set(review["auxiliary_columns"]) <= labels)
                    result = connection.execute(source["generated_sql"])
                    columns = [item[0] for item in result.description]
                    rows = [
                        {name: engine._json_value(value)
                         for name, value in zip(columns, record)}
                        for record in result.fetchall()
                    ]
                    arguments = (
                        columns, rows, original["expected_columns"],
                        original["expected_rows"],
                        bool(original.get("order_sensitive", True)),
                    )
                    options = {
                        "order_by_column": original.get("order_by_column"),
                        "top_n_tie_policy": original.get("top_n_tie_policy"),
                    }
                    self.assertFalse(compare_results_strict(
                        *arguments, column_aliases=original.get("column_aliases"),
                        allowed_auxiliary_columns=original.get("allowed_auxiliary_columns"),
                        **options,
                    )[0])
                    self.assertTrue(compare_results_strict(
                        *arguments, column_aliases=amended.get("column_aliases"),
                        allowed_auxiliary_columns=amended.get("allowed_auxiliary_columns"),
                        **options,
                    )[0])


if __name__ == "__main__":
    unittest.main()
