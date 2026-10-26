"""Offline controls for frozen E06 development80 extension."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from types import SimpleNamespace

from scripts.m3_e06_pair24_common import bundle as pair24_bundle
from scripts.m3_e06_pair80_common import bundle, compare_pair
from scripts.prepare_m3_e06_pair80 import prepare


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
PAIR24 = BACKEND / ".downloads/m3_e06_pair24_endpoint_feedback_v2_20261024"
PAIR80 = BACKEND / ".downloads/m3_e06_pair80_endpoint_feedback_v2_20261024_r2"


class E06Pair80Test(unittest.TestCase):
    def test_frozen_producers_and_full_development_selection(self):
        old = pair24_bundle(PAIR24)
        current = bundle(PAIR80)
        payload = current["payload"]
        self.assertEqual(payload["source_bundle_id"], old["bundle_id"])
        self.assertEqual(payload["pair24_comparison_sha256"],
                         "a66d55d54dc22d5bd0cfbec4ba8415a3f507d8c46a9f589aa1c1e7292a8e0d37")
        for side in ("baseline", "candidate"):
            self.assertEqual(payload["sides"][side]["code_files"],
                             old["payload"]["sides"][side]["code_files"])
            for name, entry in old["payload"]["sides"][side]["assets"].items():
                self.assertEqual(payload["sides"][side]["assets"][name]["sha256"], entry["sha256"])
        selected = json.loads((BACKEND / "evaluation/cases/bird_mini_dev/m2_pg_v1/development80.json").read_bytes())
        self.assertEqual(payload["case_ids"], selected["case_ids"])
        self.assertEqual(payload["maximum_generated_cases"], 160)
        self.assertEqual(len(payload["historical_success50_ids"]), 50)
        self.assertFalse(payload["automatic_holdout"])
        self.assertFalse(any(name.endswith(".env") or "credentials" in name.lower()
                             for name in payload["files"]))
        with zipfile.ZipFile(ROOT / "M3_E06_pair80_endpoint_feedback_v2_20261024_r2.zip") as archive:
            self.assertIsNone(archive.testzip())

    def test_comparison_detects_boundary_rejection_and_regression(self):
        payload = bundle(PAIR80)["payload"]

        def capture(side):
            indexes = [{"identity": {"source_identity": {"logical_database_id": db}},
                        "path": f"/{side}/{db}/schema_index.json",
                        "model_usage": {"model_events": [{"usage": {"total_tokens": 10}}],
                                        "model_http_attempts": 1}}
                       for db in payload["index_database_ids"]]
            cases = [{"case_id": cid, "database_id": "toxicology", "status": "complete",
                      "source_identity": {"source_id": "same"}, "query_role": "readonly",
                      "development_diagnostics": {"retrieval": {"schema_graph": {
                          "value": {"fields": [], "joins": []}}}},
                      "endpoint_validation_observations": [],
                      "budget": {"model_events": [{"kind": "chat", "usage": {"total_tokens": 5}}],
                                 "model_http_attempts": 1}, "case_wall_seconds": 1.0}
                     for cid in payload["case_ids"]]
            return {"model_configuration": {}, "source_binding": {}, "schema_selection_policy": {},
                    "sql_repair_policy": {}, "case_list_sha256": "same", "transport_policy": {},
                    "transport_dependency_binding": {}, "condition_relation_policy": {},
                    "intent_candidate_policy": payload["intent_policies"][side],
                    "selected_case_ids": payload["case_ids"], "cases": cases, "index_builds": indexes}

        captures = {side: capture(side) for side in ("baseline", "candidate")}
        natives = {side: {"cases": [{"case_id": cid, "native_comparison": {
            "matches_frozen_gold": side == "candidate" or cid != "BIRD-PG-0239"}}
            for cid in payload["case_ids"]]} for side in ("baseline", "candidate")}
        result = compare_pair(payload, captures, natives)
        self.assertEqual((result["case_count"], result["baseline_match_count"],
                          result["candidate_match_count"]), (80, 79, 80))
        self.assertTrue(result["automatic_screen_pass"])
        self.assertEqual(result["wrong_to_right"], ["BIRD-PG-0239"])

        broken = deepcopy(captures)
        boundary = next(row for row in broken["candidate"]["cases"] if row["case_id"] == "BIRD-PG-0206")
        boundary["endpoint_validation_observations"] = [{"decision": {"status": "candidate_repair"}}]
        self.assertFalse(compare_pair(payload, broken, natives)["screening"]["boundary_0206_not_rejected"])

        broken = deepcopy(natives)
        regression_id = payload["regression_ids"][0]
        next(row for row in broken["candidate"]["cases"] if row["case_id"] == regression_id)[
            "native_comparison"]["matches_frozen_gold"] = False
        result = compare_pair(payload, captures, broken)
        self.assertIn(regression_id, result["right_to_wrong"])
        self.assertFalse(result["screening"]["regression20_retained"])

    def test_prepare_uses_independent_sources_without_secrets(self):
        with tempfile.TemporaryDirectory(dir=BACKEND / "evaluation/results") as temporary:
            root = Path(temporary)
            source, data, private = (root / name for name in ("source", "data", "private"))
            for directory in (source, data, private):
                directory.mkdir()
            model, credentials = private / ".env", private / "credentials.json"
            model.write_text("placeholder-not-read", encoding="utf-8")
            credentials.write_text("placeholder-not-read", encoding="utf-8")
            work = root / "workspace"
            result = prepare(SimpleNamespace(bundle_root=PAIR80, source_backend=source,
                workspace=work, data_root=data, model_config_file=model, credentials_file=credentials))
            self.assertEqual(result["run_status"], "complete")
            self.assertTrue((work / "candidate/backend/evaluation/bird/endpoint_validation.py").is_file())
            self.assertFalse((work / "baseline/backend/evaluation/bird/endpoint_validation.py").exists())
            self.assertFalse((work / "candidate/backend/.env").exists())
            self.assertTrue((work / "candidate/backend" / "evaluation/cases/bird_mini_dev/m2_pg_v1/development80.json").is_file())


if __name__ == "__main__":
    unittest.main()
