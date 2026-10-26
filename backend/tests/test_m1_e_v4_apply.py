"""Verify seven-case application on a copied formal dataset."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import apply_m1_e_v4_strict7 as application
from scripts.rescore_m1_e_v3_strict import amended_case, sha256
from scripts.rescore_m1_e_v4_strict7 import FORMAL_SHA256, RESULTS, REVIEWED


REPLAY = RESULTS / "m1_e_v4_strict7_rescore_server.json"
FROZEN = RESULTS / "m1_e_all_cases_before_v4_strict7_20261014.jsonl"


class M1EV4ApplyTest(unittest.TestCase):
    def source_cases(self) -> Path:
        source = FROZEN if FROZEN.exists() else application.CASES
        self.assertEqual(sha256(source), FORMAL_SHA256)
        return source

    def test_copy_changes_exactly_seven_reviewed_cases(self) -> None:
        original = self.source_cases().read_bytes()
        with tempfile.TemporaryDirectory(prefix="askdata_m1_e_v4_apply_test_") as folder:
            root = Path(folder)
            cases = root / "all_cases.jsonl"
            frozen = root / "before.jsonl"
            output = root / "apply.json"
            cases.write_bytes(original)
            with (patch.object(application, "CASES", cases),
                  patch.object(application, "FROZEN", frozen)):
                result = application.apply(REPLAY, output)
            self.assertEqual(result["run_status"], "complete")
            self.assertEqual(result["changed_case_ids"], list(REVIEWED))
            self.assertEqual(result["alias_addition_count"], 16)
            self.assertEqual(frozen.read_bytes(), original)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), result)
            before = [json.loads(line) for line in original.decode("utf-8").splitlines()]
            after = [json.loads(line) for line in cases.read_text(encoding="utf-8").splitlines()]
            changed = [old["case_id"] for old, new in zip(before, after) if old != new]
            self.assertEqual(len(changed), 7)
            self.assertEqual(set(changed), set(REVIEWED))
            for old, new in zip(before, after):
                if old["case_id"] in REVIEWED:
                    self.assertEqual(new, amended_case(old, REVIEWED[old["case_id"]]))
                else:
                    self.assertEqual(new, old)

    def test_tampered_replay_cannot_change_cases(self) -> None:
        original = self.source_cases().read_bytes()
        with tempfile.TemporaryDirectory(prefix="askdata_m1_e_v4_tamper_test_") as folder:
            root = Path(folder)
            cases = root / "all_cases.jsonl"
            replay = root / "tampered.json"
            cases.write_bytes(original)
            replay.write_bytes(REPLAY.read_bytes() + b" ")
            with patch.object(application, "CASES", cases):
                with self.assertRaisesRegex(ValueError, "replay report differs"):
                    application.apply(replay, root / "apply.json")
            self.assertEqual(cases.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
