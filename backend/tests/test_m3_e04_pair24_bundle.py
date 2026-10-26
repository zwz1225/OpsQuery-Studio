"""No-model E04 bundle and comparison guard tests."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
import zipfile

from scripts.m3_e04_pair24_common import bundle, compare_pair, PairError
from scripts.prepare_m3_e04_pair24 import prepare


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
DELIVERY = BACKEND / ".downloads/m3_e04_pair24_scalar_count_v2_20261024"


class E04Pair24Test(unittest.TestCase):
    def test_frozen_bundle_is_exact_e02_plus_scalar_candidate(self):
        row = bundle(DELIVERY)
        p = row["payload"]
        old = p["sides"]["baseline"]["code_files"]
        new = p["sides"]["candidate"]["code_files"]
        self.assertEqual({n for n in old if old[n] != new[n]}, {"evaluation/bird/intent.py"})
        self.assertEqual(set(new) - set(old), {"evaluation/bird/scalar_count_shape.py"})
        self.assertEqual(p["maximum_generated_cases"], 48)
        self.assertFalse(p["automatic_holdout"])
        self.assertEqual(p["case_ids"][:4],
            ["BIRD-PG-0092", "BIRD-PG-0072", "BIRD-PG-0356", "BIRD-PG-0239"])
        self.assertEqual(len(p["case_ids"]), 24)
        self.assertNotEqual(p["intent_policies"]["baseline"], p["intent_policies"]["candidate"])
        self.assertEqual(p["source_binding"],
            json.loads((BACKEND / ".downloads/m3_e02_pair80_process_dns_v1_20261024_r3/bundle_manifest.json").read_bytes())["payload"]["source_binding"])
        names = set(p["files"])
        # Frozen protocol validation and native replay need these reference
        # artifacts on disk; the selected generator input remains development24.
        self.assertTrue(any("holdout30" in name for name in names))
        self.assertTrue(any("/scorer/" in name for name in names))
        self.assertFalse(any(name.endswith(".env") for name in names))

    def test_zip_and_side_policy_wiring_are_frozen(self):
        archive = ROOT / "M3_E04_pair24_scalar_count_v2_20261024.zip"
        with zipfile.ZipFile(archive) as zipped:
            self.assertIsNone(zipped.testzip())
            self.assertIn("m3_e04_pair24_scalar_count_v2_20261024/bundle_manifest.json", zipped.namelist())
        base = (DELIVERY / "payload/baseline/evaluation/bird/intent.py").read_text(encoding="utf-8")
        candidate = (DELIVERY / "payload/candidate/evaluation/bird/intent.py").read_text(encoding="utf-8")
        self.assertNotIn("scalar_count_output", base)
        self.assertIn("'scalar_count_output':scalar_count_contract(public)", candidate)
        self.assertIn("issues = shape_issues(contract['scalar_count_output'], sql)", candidate)
        self.assertIn("hard_for_simple_outer_select", candidate)
        driver = (DELIVERY / "control/run_m3_e04_pair24.py").read_text(encoding="utf-8")
        for name in ("e04_pair24_preflight_server.json", "e04_pair24_transport_model_probe_server.json",
                     "e04_pair24_server.json", "e04_pair24_comparison_server.json"):
            self.assertIn(name, driver)
        self.assertNotIn("e02_pair24", driver)

    def test_comparison_keeps_fixed_denominator_and_0092_gate(self):
        payload = bundle(DELIVERY)["payload"]
        def make(side):
            indexes = [{"identity": {"source_identity": {"logical_database_id": db}},
                        "path": f"/{side}/{db}/schema_index.json",
                        "model_usage": {"model_events": [{"usage": {"total_tokens": 10}}],
                                        "model_http_attempts": 1}}
                       for db in payload["index_database_ids"]]
            cases = [{"case_id": cid, "database_id": "financial", "status": "complete",
                      "source_identity": {"source_id": "same"}, "query_role": "readonly",
                      "development_diagnostics": {"retrieval": {"schema_graph": {"value": {"fields": [], "joins": []}}}},
                      "budget": {"model_events": [{"kind": "chat", "usage": {"total_tokens": 5}}],
                                 "model_http_attempts": 1},
                      "case_wall_seconds": 1.0}
                     for cid in payload["case_ids"]]
            return {"model_configuration": {}, "source_binding": {}, "schema_selection_policy": {},
                    "sql_repair_policy": {}, "case_list_sha256": "same", "transport_policy": {},
                    "transport_dependency_binding": {}, "condition_relation_policy": {},
                    "intent_candidate_policy": payload["intent_policies"][side],
                    "selected_case_ids": payload["case_ids"], "cases": cases, "index_builds": indexes}
        captures = {side: make(side) for side in ("baseline", "candidate")}
        natives = {side: {"cases": [{"case_id": cid,
                    "native_comparison": {"matches_frozen_gold": cid != "BIRD-PG-0092" or side == "candidate"}}
                    for cid in payload["case_ids"]]} for side in ("baseline", "candidate")}
        result = compare_pair(payload, captures, natives)
        self.assertEqual(result["case_count"], 24)
        self.assertEqual(result["wrong_to_right"], ["BIRD-PG-0092"])
        self.assertEqual(result["regression20_retained_count"], 20)
        self.assertTrue(result["screening"]["target_0092_native_correct"])
        captures["candidate"]["source_binding"] = {"other": True}
        with self.assertRaises(PairError):
            compare_pair(payload, captures, natives)

    def test_prepare_creates_two_isolated_exact_code_trees_without_secrets(self):
        with tempfile.TemporaryDirectory(dir=BACKEND / "evaluation/results") as temporary:
            root = Path(temporary).resolve()
            self.assertTrue(root.is_relative_to(BACKEND.resolve()))
            source, data, secret = (root / name for name in ("source", "data", "private"))
            for folder in (source, data, secret):
                folder.mkdir()
            model, credentials = secret / ".env", secret / "credentials.json"
            model.write_text("placeholder-not-read", encoding="utf-8")
            credentials.write_text("placeholder-not-read", encoding="utf-8")
            work = root / "workspace"
            result = prepare(SimpleNamespace(bundle_root=DELIVERY, source_backend=source,
                workspace=work, data_root=data, model_config_file=model, credentials_file=credentials))
            self.assertEqual(result["run_status"], "complete")
            self.assertEqual((result["baseline_code_files"], result["candidate_code_files"]), (99, 100))
            self.assertTrue((work / "baseline/backend/evaluation/bird/intent.py").is_file())
            self.assertTrue((work / "candidate/backend/evaluation/bird/scalar_count_shape.py").is_file())
            self.assertFalse((work / "candidate/backend/.env").exists())
            self.assertFalse((work / "candidate/backend/credentials.json").exists())


if __name__ == "__main__":
    unittest.main()
