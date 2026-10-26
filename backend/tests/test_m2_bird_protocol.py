"""External subset selection, no-Gold inputs and the pinned native EX predicate."""
import ast
from collections import Counter
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from evaluation.bird_protocol import (
    BirdProtocolError, PUBLIC_KEYS, QUESTIONS_SHA256, RESULT_ROW_LIMIT,
    agent_input, case_id, compare_ex_rows, load_canonical_questions,
    make_bundle, select_splits, sha256, validate_agent_input,
)
from scripts.freeze_m2_bird_protocol import write_or_check_bundle

BUNDLE = Path(__file__).resolve().parents[1] / "evaluation/cases/bird_mini_dev/m2_pg_v1"


def synthetic_rows():
    rows = []
    for i in range(500):
        rows.append({"question_id": i, "db_id": f"domain_{i % 11}", "question": f"Question {i}",
                     "evidence": "allowed evidence", "SQL": f"SELECT {i}",
                     "difficulty": ("simple", "moderate", "challenging")[(i // 11) % 3]})
    return rows


class SplitContractTest(unittest.TestCase):
    def test_database_separation_counts_and_difficulty_quotas(self):
        splits = select_splits(synthetic_rows())
        dev, hold = splits["development80"], splits["holdout30"]
        self.assertEqual((len(dev), len(hold), len(splits["smoke8"])), (80, 30, 8))
        self.assertFalse({r["db_id"] for r in dev} & {r["db_id"] for r in hold})
        self.assertTrue({case_id(r) for r in splits["smoke8"]} <= {case_id(r) for r in dev})
        for db in {r["db_id"] for r in dev + hold}:
            self.assertEqual(Counter(r["difficulty"] for r in dev + hold if r["db_id"] == db),
                             {"simple": 3, "moderate": 5, "challenging": 2})

    def test_input_order_does_not_change_selection(self):
        rows = synthetic_rows()
        self.assertEqual(select_splits(rows), select_splits(list(reversed(rows))))

    def test_sql_question_and_evidence_content_do_not_choose_cases(self):
        rows = synthetic_rows(); changed = deepcopy(rows)
        for row in changed:
            row.update(SQL="SELECT dangerous_wrong_answer", question="changed", evidence="changed")
        before = {k: [case_id(r) for r in v] for k,v in select_splits(rows).items()}
        after = {k: [case_id(r) for r in v] for k,v in select_splits(changed).items()}
        self.assertEqual(before, after)

    def test_duplicate_ids_and_insufficient_strata_fail(self):
        rows = synthetic_rows(); rows[0]["question_id"] = rows[1]["question_id"]
        with self.assertRaises(BirdProtocolError): select_splits(rows)
        rows = synthetic_rows()
        for row in rows:
            if row["db_id"] == "domain_0": row["difficulty"] = "moderate"
        with self.assertRaises(BirdProtocolError): select_splits(rows)

    def test_canonical_bytes_and_changed_gold_cannot_be_refrozen(self):
        with self.assertRaisesRegex(BirdProtocolError, "hash"):
            load_canonical_questions(b"[]")
        with self.assertRaisesRegex(BirdProtocolError, "changed"):
            make_bundle(synthetic_rows(), {}, {}, {})

    def test_agent_allowlist_omits_gold_difficulty_and_future_fields(self):
        row = synthetic_rows()[0]
        row.update(expected_rows=[{"secret": 42}], retrieval_terms=["Gold field"], metadata={"gold_sql": "SELECT 42"})
        public = agent_input(row)
        self.assertEqual(set(public), PUBLIC_KEYS)
        self.assertEqual(public["evidence"], row["evidence"])
        self.assertNotIn("SQL", public)
        self.assertNotIn("difficulty", public)
        for forbidden in ("SQL", "gold_sql", "expected_rows", "retrieval_terms", "metadata"):
            bad = {**public, forbidden: "hidden"}
            with self.subTest(field=forbidden), self.assertRaises(BirdProtocolError):
                validate_agent_input(bad)


class ExPolicyTest(unittest.TestCase):
    def test_row_order_and_duplicate_multiplicity_are_ignored(self):
        self.assertTrue(compare_ex_rows([(1,), (2,), (1,)], [(2,), (1,)]))

    def test_column_positions_and_null_are_not_relaxed(self):
        self.assertFalse(compare_ex_rows([("EUR", 3)], [(3, "EUR")]))
        self.assertFalse(compare_ex_rows([(None,)], [("",)]))
        self.assertFalse(compare_ex_rows([(0.30000000001,)], [(0.3,)]))

    def test_native_numeric_values_are_not_lossily_serialized(self):
        self.assertTrue(compare_ex_rows([(3, Decimal("1.25"))], [(3.0, Decimal("1.250"))]))
        self.assertFalse(compare_ex_rows([(Decimal("9007199254740993"),)], [(float(9007199254740993),)]))

    def test_empty_results_match_upstream(self):
        self.assertTrue(compare_ex_rows([], []))
        self.assertFalse(compare_ex_rows([], [(None,)]))

    def test_incomplete_or_unhashable_values_cannot_pass(self):
        for flags in ({"predicted_complete": False}, {"gold_complete": False}):
            with self.assertRaises(BirdProtocolError): compare_ex_rows([(1,)], [(1,)], **flags)
        with self.assertRaises(BirdProtocolError): compare_ex_rows([([1],)], [([1],)])
        with self.assertRaises(BirdProtocolError): compare_ex_rows([{"a": 1}], [{"a": 1}])
        with self.assertRaises(BirdProtocolError): compare_ex_rows([(1,)] * (RESULT_ROW_LIMIT + 1), [(1,)])

    def test_comparator_matches_pinned_official_function(self):
        source = (BUNDLE / "reference/official_calculate_ex.py.txt").read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertEqual(len(tree.body), 1)
        self.assertIsInstance(tree.body[0], ast.FunctionDef)
        namespace = {"__builtins__": {"set": set}}
        exec(compile(tree, "pinned_official_calculate_ex", "exec"), namespace)
        for predicted, gold in [([], []), ([(1,), (1,)], [(1.0,)]), ([(1, 2)], [(2, 1)]),
                                ([(None,)], [(None,)]), ([(0.30000000001,)], [(0.3,)]),
                                ([(Decimal("1.25"),)], [(Decimal("1.250"),)])]:
            self.assertEqual(compare_ex_rows(predicted, gold), bool(namespace["calculate_ex"](predicted, gold)))


class FrozenBundleTest(unittest.TestCase):
    def test_all_frozen_artifacts_and_gold_boundary(self):
        protocol = json.loads((BUNDLE / "protocol.json").read_bytes())
        for name,digest in protocol["artifact_sha256"].items():
            self.assertEqual(sha256((BUNDLE/name).read_bytes()), digest, name)
        self.assertEqual(protocol["dataset"]["questions_sha256"], QUESTIONS_SHA256)
        self.assertEqual(protocol["scoring"]["primary_denominator"].split(",")[0], "all frozen cases")
        self.assertFalse(protocol["agent"]["retrieval"]["gold_retrieval_terms"])
        dev = json.loads((BUNDLE / "development80.json").read_bytes())
        hold = json.loads((BUNDLE / "holdout30.json").read_bytes())
        self.assertFalse(set(dev["database_ids"]) & set(hold["database_ids"]))
        self.assertEqual((dev["case_count"], hold["case_count"]), (80, 30))
        ids = set(dev["case_ids"] + hold["case_ids"])
        gold = [json.loads(line) for line in (BUNDLE / "scorer/gold110.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual({r["case_id"] for r in gold}, ids)
        for split in ("development80", "holdout30", "smoke8"):
            inputs = [json.loads(line) for line in (BUNDLE / f"inputs/{split}.jsonl").read_text(encoding="utf-8").splitlines()]
            for row in inputs: validate_agent_input(row)
            manifest = json.loads((BUNDLE / f"{split}.json").read_bytes())
            self.assertEqual([r["case_id"] for r in inputs], manifest["case_ids"])

    def test_bundle_mutation_extra_files_and_overwrite_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "bundle"; files = {"x.json": b"{}\n"}
            write_or_check_bundle(target, files, check=False)
            write_or_check_bundle(target, files, check=True)
            with self.assertRaises(BirdProtocolError): write_or_check_bundle(target, files, check=False)
            (target / "x.json").write_bytes(b"[]\n")
            with self.assertRaises(BirdProtocolError): write_or_check_bundle(target, files, check=True)
            (target / "x.json").write_bytes(files["x.json"])
            (target / "unexpected").write_text("extra")
            with self.assertRaises(BirdProtocolError): write_or_check_bundle(target, files, check=True)


if __name__ == "__main__":
    unittest.main()
