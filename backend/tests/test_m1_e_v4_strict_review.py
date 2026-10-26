"""Check saved v4 SQL against the seven explicit proposed column mappings."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import sqlglot
from sqlglot import exp

from app.querying.duckdb_engine import DuckDbEngine
from scripts.rescore_m1_e_v3_strict import amended_case, strict
from scripts import rescore_m1_e_v4_strict7 as review


REVIEWED = review.REVIEWED


def reviewed_inputs() -> tuple:
    frozen = review.RESULTS / "m1_e_all_cases_before_v4_strict7_20261014.jsonl"
    source = frozen if frozen.exists() else review.CASES
    with patch.object(review, "CASES", source):
        return review.preflight()


class M1EV4StrictReviewTest(unittest.TestCase):
    def test_pinned_inputs_and_exact_projection_meaning(self) -> None:
        reports, cases, rows, identity = reviewed_inputs()
        self.assertEqual([len(report["cases"]) for report in reports], [49, 30])
        self.assertEqual(identity["source_id"], "short_video_ops_postgres")
        self.assertEqual(sum(len(names) for item in REVIEWED.values()
                             for names in item["aliases"].values()), 16)
        for case_id, candidate in REVIEWED.items():
            with self.subTest(case_id=case_id):
                self.assertIn(case_id, cases)
                projections = sqlglot.parse_one(
                    rows[case_id]["generated_sql"], read="postgres"
                ).expressions
                output_names = [projection.alias_or_name for projection in projections]
                self.assertEqual(len(output_names), len(set(output_names)))
                self.assertTrue(all(
                    label in output_names
                    for names in candidate["aliases"].values() for label in names
                ))
                self.assertEqual(candidate["auxiliary_columns"], [])

        # For the CPA gap, the output really is actual CPA less target CPA.
        gap_sql = rows["CHANNEL_OPS-136"]["generated_sql"]
        projection = next(item for item in sqlglot.parse_one(gap_sql, read="postgres").expressions
                          if item.alias_or_name == "target_gap")
        self.assertIsNotNone(projection.find(exp.Sub))
        self.assertIn("target_cpa", {column.name for column in projection.find_all(exp.Column)})
        self.assertIn("spend", {column.name for column in projection.find_all(exp.Column)})
        self.assertIn("conversions", {column.name for column in projection.find_all(exp.Column)})

    def test_six_saved_queries_replay_on_local_data_with_only_exact_aliases(self) -> None:
        _, cases, rows, _ = reviewed_inputs()
        engine = DuckDbEngine()
        with engine.connect("short_video_ops") as connection:
            connection.execute("CREATE SCHEMA askdata_ops")
            for table in (
                "ad_daily_stats", "ad_campaigns", "acquisition_channels",
                "channel_targets", "channel_conversion_events",
            ):
                connection.execute(
                    f"CREATE VIEW askdata_ops.{table} AS SELECT * FROM main.{table}"
                )
            for case_id, candidate in REVIEWED.items():
                if case_id == "CHANNEL_OPS-136":
                    # DuckDB and PostgreSQL differ on this query's decimal
                    # division for one frozen row; the PG replay is decisive.
                    continue
                with self.subTest(case_id=case_id):
                    original = cases[case_id]
                    result = connection.execute(rows[case_id]["generated_sql"])
                    columns = [description[0] for description in result.description]
                    actual_rows = [
                        {name: engine._json_value(value)
                         for name, value in zip(columns, record)}
                        for record in result.fetchall()
                    ]
                    gold = {"columns": original["expected_columns"],
                            "rows": original["expected_rows"]}
                    self.assertEqual(len(actual_rows),
                                     rows[case_id]["result_metrics"]["generated_result_rows"])
                    self.assertFalse(strict(columns, actual_rows, gold, original)[0])
                    proposed = amended_case(original, candidate)
                    self.assertTrue(strict(columns, actual_rows, gold, proposed)[0])


if __name__ == "__main__":
    unittest.main()
