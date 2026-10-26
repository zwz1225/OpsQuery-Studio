"""Freeze the accepted E06 pair24 producer bytes for one development80 pair."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
SOURCE = BACKEND / ".downloads/m3_e06_pair24_endpoint_feedback_v2_20261024"
EVIDENCE = ROOT.parent / "m3_e06_pair24_endpoint_feedback_v2_20261024_r1"
HISTORICAL = BACKEND / "evaluation/results/m2_public_intent_v4_development80_native_server.json"
NAME = "m3_e06_pair80_endpoint_feedback_v2_20261024_r2"
OUT = BACKEND / ".downloads" / NAME
ZIP = ROOT / "M3_E06_pair80_endpoint_feedback_v2_20261024_r2.zip"
CONTROLS = ("m3_e06_pair80_common.py", "m3_e06_pair80_side.py",
            "prepare_m3_e06_pair80.py", "run_m3_e06_pair80.py")
CASE_LIST = "evaluation/cases/bird_mini_dev/m2_pg_v1/development80.json"
COMPARISON_SHA = "a66d55d54dc22d5bd0cfbec4ba8415a3f507d8c46a9f589aa1c1e7292a8e0d37"
HISTORICAL_SHA = "1bbb278d0a5ffb99b3049faff6e1da2c482230284188e71e8d4fb44504c38774"
REPORT_SHA = {
    "baseline_capture": "cfa82d667eb05462c03b95179eb3121e0c8e81084e6175e9724a769600c15d27",
    "baseline_native": "da1f3dd1d843d85f0d30f44b89cce6d0434f02efd22dcf121aed2756fee8e45c",
    "candidate_capture": "7daa312a5291eb0e3c76460f5a0c8b528d582c0179c379bbe275c2b004d9131a",
    "candidate_native": "eddbf786b8de05985c9760f75d75ecb7d6ab219a2c898ce3e742f691a245d282",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def accepted_evidence():
    path = EVIDENCE / "reports/e06_pair24_comparison_server.json"
    if sha(path) != COMPARISON_SHA:
        raise ValueError("Accepted pair24 comparison bytes differ")
    report = json.loads(path.read_bytes())
    if (report["run_status"] != "complete" or report["automatic_screen_pass"] is not True
            or report["case_count"] != 24 or report["baseline_match_count"] != 22
            or report["candidate_match_count"] != 23
            or report["wrong_to_right"] != ["BIRD-PG-0239"] or report["right_to_wrong"]):
        raise ValueError("Accepted pair24 outcomes differ")
    for key, expected in REPORT_SHA.items():
        rel = ("baseline" if key.startswith("baseline") else "candidate")
        rel += "/backend/evaluation/results/m3_e06_pair24_"
        rel += key + "_server.json"
        if report["source_reports"][key]["sha256"] != expected or sha(EVIDENCE / rel) != expected:
            raise ValueError("Accepted pair24 source report differs: " + key)
    return report


def historical_successes():
    if sha(HISTORICAL) != HISTORICAL_SHA:
        raise ValueError("Historical V4 native report changed")
    report = json.loads(HISTORICAL.read_bytes())
    if report.get("run_status") != "complete" or report.get("summary", {}).get("native_match_count") != 50:
        raise ValueError("Historical 50-success reference differs")
    return [row["case_id"] for row in report["cases"]
            if row["native_comparison"]["matches_frozen_gold"]]


def main():
    if OUT.exists() or ZIP.exists() or Path(str(ZIP) + ".sha256").exists():
        raise SystemExit("Preserve existing E06 development80 delivery; choose a new version")
    from scripts.m3_e06_pair24_common import bundle as frozen_bundle
    from scripts.m3_e06_pair80_common import bundle as new_bundle, PRIMARY, OBSERVED, SUPPORT_FILES, DNS_READINESS_POLICY

    frozen = frozen_bundle(SOURCE)
    report = accepted_evidence()
    if report["bundle_id"] != frozen["bundle_id"]:
        raise ValueError("Accepted pair24 report belongs to another producer bundle")
    old = frozen["payload"]
    selected = json.loads((BACKEND / CASE_LIST).read_bytes())["case_ids"]
    historical = historical_successes()
    if (len(selected) != 80 or len(historical) != 50 or not set(historical) <= set(selected)
            or not set(old["case_ids"]) <= set(selected)):
        raise ValueError("Frozen development80 or historical subset differs")
    payload = dict(experiment="m3_e06_endpoint_feedback_development80", date="2026-10-24",
        source_bundle_id=frozen["bundle_id"], pair24_comparison_sha256=COMPARISON_SHA,
        pair24_source_report_sha256=REPORT_SHA, historical_success50_report_sha256=HISTORICAL_SHA,
        case_ids=selected, regression_ids=old["regression_ids"],
        historical_success50_ids=historical, primary_ids=PRIMARY, observed_ids=OBSERVED,
        index_database_ids=old["index_database_ids"], support_files=SUPPORT_FILES,
        source_binding=old["source_binding"], model_configuration=old["model_configuration"],
        schema_selection_policy=old["schema_selection_policy"],
        sql_repair_policy=old["sql_repair_policy"], intent_policies=old["intent_policies"],
        endpoint_scope_policy=old["endpoint_scope_policy"],
        endpoint_validation_policy=old["endpoint_validation_policy"],
        maximum_generated_cases=160, automatic_holdout=False,
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
    for side in ("baseline", "candidate"):
        frozen_side = old["sides"][side]
        assets = {}
        for name, entry in frozen_side["assets"].items():
            src = SOURCE / entry["bundle_path"]
            dst = OUT / "payload" / side / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            if sha(dst) != entry["sha256"]:
                raise ValueError("Frozen producer asset changed: " + name)
            assets[name] = {"bundle_path": dst.relative_to(OUT).as_posix(), "sha256": sha(dst)}
            payload["files"][assets[name]["bundle_path"]] = sha(dst)
        payload["sides"][side] = {"code_files": deepcopy(frozen_side["code_files"]), "assets": assets}
    readme = OUT / "README.md"
    readme.write_text("M3 E06 development80 same-round pair. Both producer code inventories are byte-identical to the accepted E06 development24 bundle. Only the selected public development list and isolated controller change. No credentials or database dumps.\n", encoding="utf-8")
    payload["files"]["README.md"] = sha(readme)
    manifest = {"schema": "m3_e06_pair80_bundle_v1", "bundle_id": digest(payload), "payload": payload}
    (OUT / "bundle_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    new_bundle(OUT)
    with zipfile.ZipFile(ZIP, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in ("bundle_manifest.json", *payload["files"]):
            archive.write(OUT / name, NAME + "/" + name)
    Path(str(ZIP) + ".sha256").write_bytes(f"{sha(ZIP)}  {ZIP.name}\n".encode("ascii"))
    print(json.dumps({"bundle_id": manifest["bundle_id"], "zip": str(ZIP), "sha256": sha(ZIP),
        "selected_cases": len(selected), "historical_successes": len(historical),
        "baseline_code_files": len(payload["sides"]["baseline"]["code_files"]),
        "candidate_code_files": len(payload["sides"]["candidate"]["code_files"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
