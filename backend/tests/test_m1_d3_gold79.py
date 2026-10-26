"""Frozen dataset provenance, PostgreSQL type traps and boolean policy regression."""
from copy import deepcopy
import json
import unittest

import sqlglot
from sqlglot import exp

from app.datasources.sql_policy import validate_readonly_sql
from evaluation.gold_sql import GoldSqlSelectionError, select_gold_sql
from scripts.audit_m1_d3_gold79 import (
    BASELINE_PATH, CASE_PATH, LIST_PATH, REVIEW_PATH, POSTGRES_SOURCE,
    audit, check_variant, first79_cases_path, load_rows, load_types, sha256,
)


class D3Gold79Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.originals = {c["case_id"]: c for c in load_rows(BASELINE_PATH)}
        cls.current = {c["case_id"]: c for c in load_rows(first79_cases_path())}
        cls.records = {r["case_id"]: r for r in json.loads(REVIEW_PATH.read_text(encoding="utf-8"))["cases"]}
        cls.types = load_types()

    def check_changed(self, case_id, change, *, refresh_review=False):
        case = deepcopy(self.current[case_id])
        record = deepcopy(self.records[case_id])
        change(case)
        if refresh_review:
            record["postgres_sql_sha256"] = sha256(case["gold_sql_by_dialect"]["postgres"])
        with self.assertRaises(ValueError):
            check_variant(self.originals[case_id], case, record, self.types)

    def test_full_offline_audit_79_and_original_430_preserved(self):
        result = audit()
        self.assertEqual((result["reviewed_case_count"], result["unchanged_duckdb_sql_count"],
                          result["untouched_unreviewed_case_count"]), (79, 430, 351))
        self.assertFalse(result["postgres_execution_verified"])
        self.assertFalse(result["live_target_verified"])

    def test_exact_scope_and_missing_variants_fail_closed(self):
        ids = json.loads(LIST_PATH.read_text(encoding="utf-8"))["case_ids"]
        self.assertEqual(set(ids), set(self.records))
        for case_id, case in self.current.items():
            with self.subTest(case_id=case_id):
                if case_id in ids:
                    self.assertEqual(select_gold_sql(case, POSTGRES_SOURCE).selection_key,
                                     "gold_sql_by_dialect.postgres")
                else:
                    with self.assertRaises(GoldSqlSelectionError):
                        select_gold_sql(case, POSTGRES_SOURCE)

    def test_expected_rows_cannot_be_changed_to_make_a_variant_pass(self):
        self.check_changed("GROWTH_OPS-001", lambda c: c["expected_rows"][0].update(value=-1))

    def test_original_duckdb_sql_cannot_be_modified(self):
        self.check_changed("GROWTH_OPS-001", lambda c: c.update(gold_sql="SELECT 1 AS value"))

    def test_aliases_cannot_be_broadened(self):
        self.check_changed("CHANNEL_OPS-069", lambda c: c["column_aliases"].update(avg_value=["anything"]))

    def test_existing_top10_tie_candidates_are_frozen(self):
        self.check_changed("CONTENT_OPS-025", lambda c: c["top_n_tie_policy"].update(boundary_value=0))

    def test_changed_month_filter_is_rejected_even_with_refreshed_sql_hash(self):
        self.check_changed("GROWTH_OPS-149", lambda c: c["gold_sql_by_dialect"].update(
            postgres=c["gold_sql_by_dialect"]["postgres"].replace("2026-04", "2026-05")), refresh_review=True)

    def test_bigint_truth_test_cannot_be_restored_or_narrowed_to_one(self):
        for replacement in ("a.is_activated", "a.is_activated = 1"):
            self.check_changed("GROWTH_OPS-061", lambda c: c["gold_sql_by_dialect"].update(
                postgres=c["gold_sql_by_dialect"]["postgres"].replace("a.is_activated <> 0", replacement)),
                refresh_review=True)

    def test_truth_tests_use_accepted_bigint_columns(self):
        tests = [t for r in self.records.values() for t in r["changes"]["integer_truth_tests"]]
        self.assertEqual(len(tests), 17)
        self.assertEqual({t["column"] for t in tests},
                         {"is_activated", "is_retained", "recalled", "delivered", "clicked", "valid_interaction"})
        self.assertTrue(all(self.types[t["table"]][t["column"]] == "bigint" for t in tests))

    def test_round_inputs_and_division_are_explicit(self):
        round_count = division_count = 0
        for case_id in self.records:
            tree = sqlglot.parse_one(select_gold_sql(self.current[case_id], POSTGRES_SOURCE).sql, read="postgres")
            for node in tree.find_all(exp.Round):
                self.assertEqual(node.this.args["to"].this, exp.DataType.Type.DECIMAL)
                round_count += 1
            for node in tree.find_all(exp.Div):
                self.assertEqual(node.this.args["to"].this, exp.DataType.Type.DOUBLE)
                division_count += 1
        self.assertEqual((round_count, division_count), (60, 19))

    def test_cte_gap_rounding_does_not_round_inputs_before_subtraction(self):
        tree = sqlglot.parse_one(self.current["GROWTH_OPS-149"]["gold_sql_by_dialect"]["postgres"], read="postgres")
        gap = next(n for n in tree.find_all(exp.Alias) if n.alias == "gap")
        self.assertIsInstance(gap.this.this.this, exp.Sub)
        self.assertFalse(list(gap.this.this.this.find_all(exp.Round)))

    def test_mom_keeps_lag_and_zero_guard_and_top10_null_order(self):
        mom = sqlglot.parse_one(self.current["CHANNEL_OPS-025"]["gold_sql_by_dialect"]["postgres"], read="postgres")
        self.assertEqual(len(list(mom.find_all(exp.Lag))), 2)
        self.assertEqual(len(list(mom.find_all(exp.Nullif))), 1)
        self.assertIn("<= '2026-05'", mom.sql(dialect="postgres"))
        for case_id in ("GROWTH_OPS-125", "CONTENT_OPS-025", "CONTENT_OPS-050", "CONTENT_OPS-100"):
            tree = sqlglot.parse_one(self.current[case_id]["gold_sql_by_dialect"]["postgres"], read="postgres")
            self.assertEqual(tree.args["limit"].expression.this, "10")
            self.assertTrue(all(n.args["nulls_first"] is False for n in tree.find_all(exp.Ordered)))

    def test_boolean_operators_are_syntax_and_allowed(self):
        tables = [{"id": "users", "name": "users", "database": "short_video_ops"}]
        for predicate in ("1 = 1 AND 2 = 2", "1 = 1 OR 2 = 2", "NOT (1 = 2)",
                          "1 = 1 AND (2 = 2 OR NOT (3 = 4))"):
            sql = "SELECT user_id FROM users WHERE " + predicate
            with self.subTest(predicate=predicate):
                self.assertEqual(validate_readonly_sql("short_video_ops", sql, tables,
                    dialect="postgres", physical_schema="askdata_ops"), sql)

    def test_boolean_operators_do_not_hide_unsafe_nested_functions(self):
        tables = [{"id": "users", "name": "users", "database": "short_video_ops"}]
        for predicate in ("1 = 1 AND pg_advisory_lock(1) IS NULL",
                          "1 = 1 OR pg_read_file('/tmp/example') IS NULL",
                          "NOT (set_config('TimeZone', 'UTC', false) = 'UTC')"):
            with self.subTest(predicate=predicate), self.assertRaises(ValueError):
                validate_readonly_sql("short_video_ops", "SELECT user_id FROM users WHERE " + predicate,
                                      tables, dialect="postgres", physical_schema="askdata_ops")


if __name__ == "__main__":
    unittest.main()
