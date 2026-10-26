"""No-model checks for the isolated E05 endpoint-scope pair."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from types import SimpleNamespace

from scripts.m3_e05_pair24_common import PairError, bundle, compare_pair
from scripts.prepare_m3_e05_pair24 import prepare


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
DELIVERY = BACKEND / ".downloads/m3_e05_pair24_endpoint_scope_v1_20261024"


class E05Pair24Test(unittest.TestCase):
    def test_exact_candidate_delta_and_public_case_split(self):
        payload = bundle(DELIVERY)["payload"]
        old = payload["sides"]["baseline"]["code_files"]
        new = payload["sides"]["candidate"]["code_files"]
        self.assertEqual({n for n in old if old[n] != new[n]}, {"evaluation/bird/intent.py"})
        self.assertEqual(set(new) - set(old), {"evaluation/bird/endpoint_scope.py"})
        self.assertEqual(payload["case_ids"][:4],
                         ["BIRD-PG-0239", "BIRD-PG-0072", "BIRD-PG-0092", "BIRD-PG-0356"])
        self.assertEqual(len(payload["case_ids"]), 24)
        self.assertEqual(payload["maximum_generated_cases"], 48)
        self.assertFalse(payload["automatic_holdout"])
        self.assertEqual(payload["endpoint_scope_policy"],
                         "m3_public_explicit_endpoint_scope_candidate_v1")

    def test_zip_and_advisory_wiring(self):
        archive = ROOT / "M3_E05_pair24_endpoint_scope_v1_20261024.zip"
        with zipfile.ZipFile(archive) as zipped:
            self.assertIsNone(zipped.testzip())
            self.assertIn("m3_e05_pair24_endpoint_scope_v1_20261024/bundle_manifest.json",
                          zipped.namelist())
        base = (DELIVERY / "payload/baseline/evaluation/bird/intent.py").read_text(encoding="utf-8")
        candidate = (DELIVERY / "payload/candidate/evaluation/bird/intent.py").read_text(encoding="utf-8")
        self.assertNotIn("explicit_endpoint_scope", base)
        self.assertIn("'explicit_endpoint_scope':endpoint_scope_contract(public,tables.values())", candidate)
        self.assertIn("This is advisory; do not invent a mandatory SQL predicate", candidate)
        self.assertNotIn("observe_sql(", candidate)
        self.assertNotIn("shape_issues(", candidate)
        self.assertFalse(any(name.endswith(".env") for name in bundle(DELIVERY)["payload"]["files"]))

    def test_comparison_has_fixed_target_and_source_guards(self):
        payload = bundle(DELIVERY)["payload"]

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
                      "budget": {"model_events": [{"kind": "chat", "usage": {"total_tokens": 5}}],
                                 "model_http_attempts": 1}, "case_wall_seconds": 1.0}
                     for cid in payload["case_ids"]]
            return {"model_configuration": {}, "source_binding": {}, "schema_selection_policy": {},
                    "sql_repair_policy": {}, "case_list_sha256": "same", "transport_policy": {},
                    "transport_dependency_binding": {}, "condition_relation_policy": {},
                    "intent_candidate_policy": payload["intent_policies"][side],
                    "selected_case_ids": payload["case_ids"], "cases": cases, "index_builds": indexes}

        captures = {side: capture(side) for side in ("baseline", "candidate")}
        natives = {side: {"cases": [{"case_id": cid,
                    "native_comparison": {"matches_frozen_gold": cid != "BIRD-PG-0239" or side == "candidate"}}
                    for cid in payload["case_ids"]]} for side in ("baseline", "candidate")}
        result = compare_pair(payload, captures, natives)
        self.assertEqual(result["wrong_to_right"], ["BIRD-PG-0239"])
        self.assertTrue(result["screening"]["target_0239_native_correct"])
        self.assertEqual(result["regression20_retained_count"], 20)
        captures["candidate"]["source_binding"] = {"other": True}
        with self.assertRaises(PairError):
            compare_pair(payload, captures, natives)

    def test_prepare_isolates_sources_and_excludes_credentials(self):
        with tempfile.TemporaryDirectory(dir=BACKEND / "evaluation/results") as temporary:
            root = Path(temporary)
            source, data, private = (root / name for name in ("source", "data", "private"))
            for directory in (source, data, private):
                directory.mkdir()
            model, credentials = private / ".env", private / "credentials.json"
            model.write_text("placeholder-not-read", encoding="utf-8")
            credentials.write_text("placeholder-not-read", encoding="utf-8")
            work = root / "workspace"
            result = prepare(SimpleNamespace(bundle_root=DELIVERY, source_backend=source,
                workspace=work, data_root=data, model_config_file=model, credentials_file=credentials))
            self.assertEqual(result["run_status"], "complete")
            self.assertTrue((work / "candidate/backend/evaluation/bird/endpoint_scope.py").is_file())
            self.assertFalse((work / "baseline/backend/evaluation/bird/endpoint_scope.py").exists())
            self.assertFalse((work / "candidate/backend/.env").exists())


if __name__ == "__main__":
    unittest.main()
