"""Check the pinned v6 evidence and prevent unreviewed case-file changes."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import apply_m1_e_v6_strict2 as application
from scripts import rescore_m1_e_v6_strict2 as review


def frozen_input() -> Path:
    if hashlib.sha256(review.CASES.read_bytes()).hexdigest() == review.FORMAL_SHA256:
        return review.CASES
    return application.FROZEN


class M1EV6StrictReviewTest(unittest.TestCase):
    def test_pinned_v6_sql_and_exact_column_meaning(self) -> None:
        with patch.object(review, "CASES", frozen_input()):
            report, originals, rows, proposals, projections = review.preflight()
        self.assertEqual(report["run_manifest"]["run_id"], review.SOURCE_RUN_ID)
        self.assertEqual([row["case_id"] for row in rows.values()
                          if row["strict_result_correct"] is False],
                         list(review.REVIEWED))
        self.assertEqual(
            sum(len(names) for item in review.REVIEWED.values()
                for names in item["aliases"].values()), 4,
        )
        self.assertEqual(
            [(item["gold_column"], item["actual_column"])
             for item in projections["CHANNEL_OPS-066"]],
            [("conversion_type", "转化类型"), ("conversions", "转化数"),
             ("avg_value", "平均价值")],
        )
        self.assertEqual(
            [(item["gold_column"], item["actual_column"])
             for item in projections["CONTENT_OPS-138"]],
            [("category_name", "content_category"), ("reports", "report_count")],
        )
        for case_id in review.REVIEWED:
            with self.subTest(case_id=case_id):
                self.assertEqual(originals[case_id]["case_id"], case_id)
                self.assertEqual(proposals[case_id]["case_id"], case_id)
                self.assertFalse(rows[case_id]["strict_result_correct"])
                self.assertTrue(rows[case_id]["result_correct"])

    def test_only_two_formal_lines_change(self) -> None:
        original = frozen_input().read_bytes()
        updated, proposed_cases = application.proposed_case_bytes(original)
        self.assertEqual(hashlib.sha256(updated).hexdigest(),
                         application.UPDATED_SHA256)
        old_lines = original.decode("utf-8").splitlines()
        new_lines = updated.decode("utf-8").splitlines()
        changed = [(json.loads(old)["case_id"], json.loads(new)["case_id"])
                   for old, new in zip(old_lines, new_lines) if old != new]
        self.assertEqual(changed, [(case_id, case_id) for case_id in review.REVIEWED])
        self.assertEqual([case["case_id"] for case in proposed_cases],
                         list(review.REVIEWED))

    def test_unreviewed_replay_cannot_update_formal_cases(self) -> None:
        before = hashlib.sha256(review.CASES.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            replay = Path(temporary) / "unreviewed.json"
            replay.write_text("{}", encoding="utf-8")
            output = Path(temporary) / "apply.json"
            with self.assertRaisesRegex(ValueError, "Reviewed replay SHA-256 differs"):
                application.apply(replay, "0" * 64, output)
            self.assertFalse(output.exists())
        self.assertEqual(hashlib.sha256(review.CASES.read_bytes()).hexdigest(), before)

    def test_replay_never_overwrites_source_report(self) -> None:
        with self.assertRaisesRegex(ValueError, "Choose a new output path"):
            review.replay(review.SOURCE)


if __name__ == "__main__":
    unittest.main()
