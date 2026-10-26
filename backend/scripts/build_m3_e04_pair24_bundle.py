"""Freeze E04 scalar-count candidate against the identical accepted E02 treatment."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
SOURCE = BACKEND / ".downloads/m3_e02_pair80_process_dns_v1_20261024_r3"
NAME = "m3_e04_pair24_scalar_count_v2_20261024"
OUT = BACKEND / ".downloads" / NAME
ZIP = ROOT / ("M3_E04_pair24_scalar_count_v2_20261024.zip")
CONTROLS = ("m3_e04_pair24_common.py", "m3_e04_pair24_side.py",
            "prepare_m3_e04_pair24.py", "run_m3_e04_pair24.py")
CASE_LIST = "evaluation/cases/bird_mini_dev/m3_e04_scalar_count24.json"
SCALAR = "evaluation/bird/scalar_count_shape.py"
INTENT = "evaluation/bird/intent.py"
AUDIT = BACKEND / "evaluation/results/m3_e04_scalar_count_offline_audit_20261024.json"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError("Frozen E02 intent anchor differs")
    return source.replace(before, after, 1)


def candidate_intent(source):
    source = replace_once(source, "POLICY = 'bird_public_intent_candidate_v4'",
        "POLICY = 'bird_public_intent_candidate_v4_scalar_count_e04'")
    source = replace_once(source,
        "    from .units_output import unit_contract,participant_output_contract\n",
        "    from .units_output import unit_contract,participant_output_contract\n"
        "    from .scalar_count_shape import public_contract as scalar_count_contract\n")
    source = replace_once(source,
        "            'entity_grain':grain_contract(runtime,public),\n",
        "            'entity_grain':grain_contract(runtime,public),\n"
        "            'scalar_count_output':scalar_count_contract(public),\n")
    source = replace_once(source,
        "                'Missing schema is a reason to clarify only after checking the supplied authorized field groups and declared FK paths. Explain the specific missing field or ambiguity.'\n",
        "                'Missing schema is a reason to clarify only after checking the supplied authorized field groups and declared FK paths. Explain the specific missing field or ambiguity.',\n"
        "                'When scalar_count_output.enforcement is hard_for_simple_outer_select, return one overall count value. An inner grouped eligibility subquery is allowed, but the final SELECT should not group or project extra fields. Advisory and none do not impose this shape.'\n")
    source = replace_once(source,
        "    tables = checked_tables(runtime); refs = bindings(tree, tables); issues = []\n",
        "    from .scalar_count_shape import shape_issues\n"
        "    tables = checked_tables(runtime); refs = bindings(tree, tables)\n"
        "    issues = shape_issues(contract['scalar_count_output'], sql)\n")
    return source


def main():
    if OUT.exists() or ZIP.exists() or Path(str(ZIP) + ".sha256").exists():
        raise SystemExit("Preserve existing E04 delivery; choose a new version")
    from scripts.m3_e02_pair80_common import bundle as old_bundle
    from scripts.m3_e04_pair24_common import bundle as new_bundle, PRIMARY, OBSERVED, SUPPORT_FILES, DNS_READINESS_POLICY
    original = old_bundle(SOURCE)
    old = original["payload"]
    side = old["sides"]["candidate"]
    selected = json.loads((BACKEND / CASE_LIST).read_bytes())["case_ids"]
    regression = json.loads((BACKEND / "evaluation/cases/bird_mini_dev/m3_a_success_regression20.json").read_bytes())["case_ids"]
    development = json.loads((SOURCE / side["assets"]["evaluation/cases/bird_mini_dev/m2_pg_v1/development80.json"]["bundle_path"]).read_bytes())["case_ids"]
    if (len(selected) != len(set(selected)) or len(selected) != 24 or
        selected != PRIMARY + OBSERVED + regression or not set(selected) <= set(development)):
        raise ValueError("E04 selected split or controls differ")
    audit = json.loads(AUDIT.read_bytes())
    if (audit.get("run_status") != "complete" or audit.get("contract_counts") !=
        {"none": 67, "advisory": 6, "hard_for_simple_outer_select": 7} or
        audit["captures"]["baseline"]["flagged"] or
        audit["captures"]["candidate"]["flagged"] !=
        [{"case_id": "BIRD-PG-0092", "issue_codes": ["scalar_count_outer_group"]}]):
        raise ValueError("E04 offline boundary audit differs")
    public = [json.loads(line) for line in
              (SOURCE / side["assets"]["evaluation/cases/bird_mini_dev/m2_pg_v1/inputs/development80.jsonl"]["bundle_path"]).read_text(encoding="utf-8").splitlines()]
    index_db = sorted({row["database_id"] for row in public if row["case_id"] in selected})
    if len(index_db) != 8:
        raise ValueError("E04 selected index domains differ")
    baseline_policy = deepcopy(old["intent_candidate_policy"])
    candidate_policy = deepcopy(baseline_policy)
    candidate_policy["policy_id"] = "bird_public_intent_candidate_v4_scalar_count_e04"
    from evaluation.bird.scalar_count_shape import POLICY as SCALAR_POLICY
    payload = dict(experiment="m3_e04_scalar_count_development24", date="2026-10-24",
        source_bundle_id=original["bundle_id"], offline_audit_sha256=sha(AUDIT),
        case_ids=selected, regression_ids=regression, primary_ids=PRIMARY, observed_ids=OBSERVED,
        index_database_ids=index_db, support_files=SUPPORT_FILES, source_binding=old["source_binding"],
        model_configuration=old["model_configuration"], schema_selection_policy=old["schema_selection_policy"],
        sql_repair_policy=old["sql_repair_policy"], intent_policies={"baseline": baseline_policy,
            "candidate": candidate_policy}, scalar_count_policy=SCALAR_POLICY,
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
        assets = {}; code = deepcopy(side["code_files"])
        for name, entry in side["assets"].items():
            dst = OUT / "payload" / label / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            src = SOURCE / entry["bundle_path"]
            if label == "candidate" and name == INTENT:
                dst.write_bytes(candidate_intent(src.read_text(encoding="utf-8")).encode("utf-8"))
            else:
                shutil.copyfile(src, dst)
            assets[name] = {"bundle_path": dst.relative_to(OUT).as_posix(), "sha256": sha(dst)}
            if name in code:
                code[name] = sha(dst)
            payload["files"][assets[name]["bundle_path"]] = sha(dst)
        additions = [CASE_LIST] + ([SCALAR] if label == "candidate" else [])
        for name in additions:
            src = BACKEND / name; dst = OUT / "payload" / label / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            assets[name] = {"bundle_path": dst.relative_to(OUT).as_posix(), "sha256": sha(dst)}
            payload["files"][assets[name]["bundle_path"]] = sha(dst)
            if name == SCALAR:
                code[name] = sha(dst)
        payload["sides"][label] = {"code_files": code, "assets": assets}
    readme = OUT / "README.md"
    readme.write_text("M3 E04 scalar-count development24 pair. Baseline is accepted E02 semantics; candidate differs only in intent.py and scalar_count_shape.py. No credentials or database dumps.\n", encoding="utf-8")
    payload["files"]["README.md"] = sha(readme)
    manifest = {"schema": "m3_e04_pair24_bundle_v1", "bundle_id": digest(payload), "payload": payload}
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
