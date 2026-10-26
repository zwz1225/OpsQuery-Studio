"""Freeze E06 feedback-only candidate against the E05 advisory treatment."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
SOURCE = BACKEND / ".downloads/m3_e05_pair24_endpoint_scope_v1_20261024"
NAME = "m3_e06_pair24_endpoint_feedback_v2_20261024"
OUT = BACKEND / ".downloads" / NAME
ZIP = ROOT / "M3_E06_pair24_endpoint_feedback_v2_20261024.zip"
CONTROLS = ("m3_e06_pair24_common.py", "m3_e06_pair24_side.py",
            "prepare_m3_e06_pair24.py", "run_m3_e06_pair24.py")
CASE_LIST = "evaluation/cases/bird_mini_dev/m3_e06_endpoint_scope24.json"
WORKER = "evaluation/bird/case_worker.py"
VALIDATOR = "evaluation/bird/endpoint_validation.py"
AUDIT = BACKEND / "evaluation/results/m3_e06_endpoint_validation_offline_local_20261024_v2.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError("Frozen E05 worker anchor differs")
    return source.replace(before, after, 1)


def candidate_worker(source):
    source = replace_once(source,
        "            repair=RepairSession(runtime,recorder.secrets,public)\n",
        "            repair=RepairSession(runtime,recorder.secrets,public)\n"
        "            from .endpoint_validation import POLICY as ENDPOINT_VALIDATION_POLICY, inspect as inspect_endpoint\n"
        "            report['endpoint_validation_policy']=ENDPOINT_VALIDATION_POLICY\n"
        "            report['endpoint_validation_observations']=[]\n")
    source = replace_once(source,
        "                        result=runtime.execute_native(sql,budget,validate_only=True)\n"
        "                        if intent_enabled:\n",
        "                        result=runtime.execute_native(sql,budget,validate_only=True)\n"
        "                        if intent_enabled:\n"
        "                            endpoint_decision=inspect_endpoint(public,runtime.catalog.tables,sql)\n"
        "                            endpoint_decision['enforcement']='candidate_validation_feedback'\n"
        "                            report['endpoint_validation_observations'].append(recorder._safe(dict(\n"
        "                                sql_round=sql_round,decision=endpoint_decision)))\n"
        "                            if endpoint_decision['status']=='candidate_repair':\n"
        "                                failure=BirdFailure('intent_contract_violation')\n"
        "                                failure._intent_violations=[endpoint_decision['feedback']]\n"
        "                                raise failure\n")
    return source


def main():
    if OUT.exists() or ZIP.exists() or Path(str(ZIP) + ".sha256").exists():
        raise SystemExit("Preserve existing E06 delivery; choose a new version")
    from scripts.m3_e05_pair24_common import bundle as old_bundle
    from scripts.m3_e06_pair24_common import bundle as new_bundle, PRIMARY, OBSERVED, SUPPORT_FILES, DNS_READINESS_POLICY
    previous = old_bundle(SOURCE)
    old = previous["payload"]
    e05_candidate = old["sides"]["candidate"]
    selected = json.loads((BACKEND / CASE_LIST).read_bytes())["case_ids"]
    if selected != old["case_ids"] or len(selected) != 24:
        raise ValueError("E06 selection differs from frozen E05")
    audit = json.loads(AUDIT.read_bytes())
    if (audit.get("run_status") != "complete" or audit.get("new_model_request_count") != 0
            or audit.get("gold_loaded") is not False or audit.get("database_connected") is not False
            or audit["outcomes"]["baseline"]["candidate_repair_ids"] != PRIMARY
            or audit["outcomes"]["candidate"]["candidate_repair_ids"] != PRIMARY):
        raise ValueError("E06 offline feedback review differs")
    from evaluation.bird.endpoint_validation import POLICY as VALIDATION_POLICY
    if audit.get("policy") != VALIDATION_POLICY or audit["source_sha256"]["validation_module"] != sha(BACKEND / VALIDATOR):
        raise ValueError("Offline review is not bound to current validator")
    for side in ("baseline", "candidate"):
        case = next(v for v in audit["outcomes"][side]["cases"] if v["case_id"] == "BIRD-PG-0206")
        if case["decision"]["status"] != "abstain":
            raise ValueError("0206 boundary is no longer abstained")
    payload = dict(experiment="m3_e06_endpoint_feedback_development24", date="2026-10-24",
        source_bundle_id=previous["bundle_id"], offline_audit_sha256=sha(AUDIT),
        case_ids=selected, regression_ids=old["regression_ids"], primary_ids=PRIMARY,
        observed_ids=OBSERVED, index_database_ids=old["index_database_ids"],
        support_files=SUPPORT_FILES, source_binding=old["source_binding"],
        model_configuration=old["model_configuration"],
        schema_selection_policy=old["schema_selection_policy"],
        sql_repair_policy=old["sql_repair_policy"],
        intent_policies={"baseline": old["intent_policies"]["candidate"],
                         "candidate": old["intent_policies"]["candidate"]},
        endpoint_scope_policy=old["endpoint_scope_policy"],
        endpoint_validation_policy=VALIDATION_POLICY,
        maximum_generated_cases=48, automatic_holdout=False,
        side_generation_order=["baseline", "candidate"], scoring_after_both_captures=True,
        transport_policy=old["transport_policy"], dns_readiness_policy=DNS_READINESS_POLICY,
        common_adaptation=old["common_adaptation"],
        index_policy="Each side builds and verifies its own source-bound index.",
        controllers={}, files={}, sides={})
    OUT.mkdir(parents=True)
    for name in CONTROLS:
        dst = OUT / "control" / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(BACKEND / "scripts" / name, dst)
        payload["controllers"][name] = payload["files"]["control/" + name] = sha(dst)
    for label in ("baseline", "candidate"):
        assets = {}
        code = deepcopy(e05_candidate["code_files"])
        for name, entry in e05_candidate["assets"].items():
            src = SOURCE / entry["bundle_path"]
            dst = OUT / "payload" / label / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            if name == CASE_LIST:
                raise ValueError("E06 selection unexpectedly existed in E05")
            if label == "candidate" and name == WORKER:
                dst.write_bytes(candidate_worker(src.read_text(encoding="utf-8")).encode("utf-8"))
            else:
                shutil.copyfile(src, dst)
            assets[name] = {"bundle_path": dst.relative_to(OUT).as_posix(), "sha256": sha(dst)}
            payload["files"][assets[name]["bundle_path"]] = sha(dst)
            if name in code:
                code[name] = sha(dst)
        additions = [CASE_LIST] + ([VALIDATOR] if label == "candidate" else [])
        for name in additions:
            src = BACKEND / name
            dst = OUT / "payload" / label / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            assets[name] = {"bundle_path": dst.relative_to(OUT).as_posix(), "sha256": sha(dst)}
            payload["files"][assets[name]["bundle_path"]] = sha(dst)
            if name == VALIDATOR:
                code[name] = sha(dst)
        payload["sides"][label] = {"code_files": code, "assets": assets}
    readme = OUT / "README.md"
    readme.write_text("M3 E06 development24 pair. Both sides retain frozen E05 advisory treatment; candidate alone adds the public-only endpoint validator and case-worker feedback wiring. No credentials or database dumps.\n", encoding="utf-8")
    payload["files"]["README.md"] = sha(readme)
    manifest = {"schema": "m3_e06_pair24_bundle_v1", "bundle_id": digest(payload), "payload": payload}
    (OUT / "bundle_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    new_bundle(OUT)
    with zipfile.ZipFile(ZIP, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in ("bundle_manifest.json", *payload["files"]):
            archive.write(OUT / name, NAME + "/" + name)
    Path(str(ZIP) + ".sha256").write_text(f"{sha(ZIP)}  {ZIP.name}\n", encoding="ascii")
    print(json.dumps({"bundle_id": manifest["bundle_id"], "zip": str(ZIP), "sha256": sha(ZIP),
        "selected_cases": len(selected), "baseline_code_files": len(payload["sides"]["baseline"]["code_files"]),
        "candidate_code_files": len(payload["sides"]["candidate"]["code_files"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
