from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.apply_m1_e_v5_content001 import FROZEN, UPDATED_SHA256, apply
from scripts.apply_m1_e_v6_strict2 import (
    FROZEN as V6_FROZEN, UPDATED_SHA256 as V6_UPDATED_SHA256,
)
from scripts.diagnose_m1_e_v5_channel136 import SOURCE as CHANNEL_SOURCE, preflight as channel_preflight
from scripts.rescore_m1_e_v5_content001 import (
    CASES, FORMAL_SHA256, SOURCE as CONTENT_SOURCE, preflight as content_preflight,
)


class V5RemediationTest(unittest.TestCase):
    def assert_v5_or_later_formal_cases(self):
        current_sha256 = hashlib.sha256(CASES.read_bytes()).hexdigest()
        if current_sha256 == V6_UPDATED_SHA256:
            self.assertEqual(hashlib.sha256(V6_FROZEN.read_bytes()).hexdigest(),
                             UPDATED_SHA256)
        else:
            self.assertEqual(current_sha256, UPDATED_SHA256)
        self.assertEqual(hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
                         FORMAL_SHA256)

    def test_saved_report_and_each_content_column_are_reviewed(self):
        if hashlib.sha256(CASES.read_bytes()).hexdigest() == FORMAL_SHA256:
            _, row, original, proposed, projections = content_preflight()
        else:
            self.assert_v5_or_later_formal_cases()
            original = next(json.loads(line) for line in FROZEN.read_text(encoding="utf-8").splitlines()
                            if json.loads(line)["case_id"] == "CONTENT_OPS-001")
            proposed = next(json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines()
                            if json.loads(line)["case_id"] == "CONTENT_OPS-001")
            row = next(item for item in json.loads(CONTENT_SOURCE.read_text(encoding="utf-8"))["cases"]
                       if item["case_id"] == "CONTENT_OPS-001")
            projections = [
                {"gold_column": gold, "actual_column": actual, "expression": expression}
                for gold, actual, expression in (
                    ("metric_date", "指标日期", "cdm.metric_date"),
                    ("impressions", "曝光量", "SUM(cdm.impressions)"),
                    ("plays", "播放量", "SUM(cdm.play_count)"),
                )
            ]
        self.assertEqual(row["case_id"], "CONTENT_OPS-001")
        self.assertEqual([(item["gold_column"], item["actual_column"], item["expression"])
                          for item in projections], [
            ("metric_date", "指标日期", "cdm.metric_date"),
            ("impressions", "曝光量", "SUM(cdm.impressions)"),
            ("plays", "播放量", "SUM(cdm.play_count)"),
        ])
        self.assertEqual(original["column_aliases"], {"plays": ["play_count"]})
        self.assertEqual(proposed["column_aliases"]["plays"], ["play_count", "播放量"])

    def test_channel_failure_is_pinned_before_diagnosis(self):
        if hashlib.sha256(CASES.read_bytes()).hexdigest() == FORMAL_SHA256:
            _, row, case = channel_preflight()
        else:
            self.assert_v5_or_later_formal_cases()
            row = next(item for item in json.loads(CHANNEL_SOURCE.read_text(encoding="utf-8"))["cases"]
                       if item["case_id"] == "CHANNEL_OPS-136")
            case = next(json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines()
                        if json.loads(line)["case_id"] == "CHANNEL_OPS-136")
        self.assertEqual(row["case_id"], case["case_id"])
        self.assertIn("ORDER BY ABS(target_gap)", row["generated_sql"])
        self.assertIn("42703", row["comparison_reason"])

    def test_unreviewed_replay_cannot_change_formal_cases(self):
        before = hashlib.sha256(CASES.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            replay = Path(temporary) / "unreviewed.json"
            replay.write_text("{}", encoding="utf-8")
            output = Path(temporary) / "apply.json"
            with self.assertRaisesRegex(ValueError, "Reviewed replay SHA-256 differs"):
                apply(replay, "0" * 64, output)
            self.assertFalse(output.exists())
        self.assertEqual(hashlib.sha256(CASES.read_bytes()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main()
