"""No-model checks for the isolated E06 feedback pair."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from types import SimpleNamespace

from scripts.m3_e06_pair24_common import PairError, bundle, compare_pair
from scripts.m3_e05_pair24_common import bundle as e05_bundle
from scripts.prepare_m3_e06_pair24 import prepare


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
DELIVERY = BACKEND / ".downloads/m3_e06_pair24_endpoint_feedback_v2_20261024"


class E06Pair24Test(unittest.TestCase):
    def test_frozen_candidate_delta_and_archive(self):
        payload = bundle(DELIVERY)["payload"]
        old = payload["sides"]["baseline"]["code_files"]
        new = payload["sides"]["candidate"]["code_files"]
        frozen_e05 = e05_bundle(BACKEND / ".downloads/m3_e05_pair24_endpoint_scope_v1_20261024")
        self.assertEqual(old, frozen_e05["payload"]["sides"]["candidate"]["code_files"])
        self.assertEqual({n for n in old if old[n] != new[n]},
                         {"evaluation/bird/case_worker.py"})
        self.assertEqual(set(new) - set(old),
                         {"evaluation/bird/endpoint_validation.py"})
        self.assertEqual(payload["intent_policies"]["baseline"],
                         payload["intent_policies"]["candidate"])
        self.assertEqual(payload["case_ids"],
                         json.loads((BACKEND / "evaluation/cases/bird_mini_dev/m3_e06_endpoint_scope24.json").read_bytes())["case_ids"])
        self.assertEqual(len(payload["case_ids"]), 24)
        self.assertEqual(payload["maximum_generated_cases"], 48)
        self.assertFalse(payload["automatic_holdout"])
        archive = ROOT / "M3_E06_pair24_endpoint_feedback_v2_20261024.zip"
        with zipfile.ZipFile(archive) as zipped:
            self.assertIsNone(zipped.testzip())
        self.assertFalse(any(name.endswith(".env") for name in payload["files"]))

    def test_feedback_wiring_is_only_on_candidate(self):
        relative = "evaluation/bird/case_worker.py"
        baseline = (DELIVERY / "payload/baseline" / relative).read_text(encoding="utf-8")
        candidate = (DELIVERY / "payload/candidate" / relative).read_text(encoding="utf-8")
        self.assertNotIn("inspect_endpoint", baseline)
        self.assertIn("inspect_endpoint(public,runtime.catalog.tables,sql)", candidate)
        self.assertIn("endpoint_decision['enforcement']='candidate_validation_feedback'", candidate)
        self.assertLess(candidate.index("runtime.execute_native(sql,budget,validate_only=True)"),
                        candidate.index("inspect_endpoint(public,runtime.catalog.tables,sql)"))
        self.assertLess(candidate.index("inspect_endpoint(public,runtime.catalog.tables,sql)"),
                        candidate.index("issues=violations(runtime,public,intent_contract,sql)"))
        self.assertIn("failure._intent_violations=[endpoint_decision['feedback']]", candidate)
        compile(candidate, str(DELIVERY / "payload/candidate" / relative), "exec")

    def test_comparison_screens_0206_boundary(self):
        payload = bundle(DELIVERY)["payload"]

        def capture(side, rejected=False):
            indexes = [{"identity": {"source_identity": {"logical_database_id": db}},
                        "path": f"/{side}/{db}/schema_index.json",
                        "model_usage": {"model_events": [{"usage": {"total_tokens": 10}}],
                                        "model_http_attempts": 1}}
                       for db in payload["index_database_ids"]]
            cases = [{"case_id": cid, "database_id": "toxicology", "status": "complete",
                      "source_identity": {"source_id": "same"}, "query_role": "readonly",
                      "development_diagnostics": {"retrieval": {"schema_graph": {
                          "value": {"fields": [], "joins": []}}}},
                      "endpoint_validation_observations": ([{"decision": {"status": "candidate_repair"}}]
                          if rejected and cid == "BIRD-PG-0206" else []),
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
            "matches_frozen_gold": cid not in ("BIRD-PG-0239", "BIRD-PG-0072")
            or side == "candidate" and cid == "BIRD-PG-0239"}}
            for cid in payload["case_ids"]]} for side in ("baseline", "candidate")}
        result = compare_pair(payload, captures, natives)
        self.assertEqual(result["wrong_to_right"], ["BIRD-PG-0239"])
        self.assertTrue(result["screening"]["boundary_0206_native_correct"])
        self.assertTrue(result["screening"]["boundary_0206_not_rejected"])
        captures["candidate"] = capture("candidate", rejected=True)
        result = compare_pair(payload, captures, natives)
        self.assertFalse(result["screening"]["boundary_0206_not_rejected"])

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
            self.assertTrue((work / "candidate/backend/evaluation/bird/endpoint_validation.py").is_file())
            self.assertFalse((work / "baseline/backend/evaluation/bird/endpoint_validation.py").exists())
            self.assertFalse((work / "candidate/backend/.env").exists())


if __name__ == "__main__":
    unittest.main()
