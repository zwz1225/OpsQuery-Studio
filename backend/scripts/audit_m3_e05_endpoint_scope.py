"""Offline public endpoint probe; reads no scorer SQL or database rows."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from evaluation.bird.endpoint_scope import public_contract, observe_sql
from evaluation.bird_protocol import validate_agent_input
from scripts.m2_b_common import BASE


PUBLIC_PATH = BASE / "evaluation/cases/bird_mini_dev/m2_pg_v1/inputs/development80.jsonl"
MANIFEST_PATH = BASE / "evaluation/cases/bird_mini_dev/m2_b_import_spec_v1.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(capture_path: Path, expected_sha256: str) -> dict:
    if sha256(capture_path) != expected_sha256:
        raise ValueError("Capture SHA-256 differs from the selected evidence")
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    if capture.get("run_status") != "complete" or len(capture.get("cases", [])) != 24:
        raise ValueError("Expected one complete E04 development24 capture")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    public_rows = [json.loads(line) for line in PUBLIC_PATH.read_text(encoding="utf-8").splitlines()]
    if len(public_rows) != 80:
        raise ValueError("Frozen development80 input count differs")
    for row in public_rows:
        validate_agent_input(row)
    by_id = {row["case_id"]: row for row in public_rows}
    if len(by_id) != 80:
        raise ValueError("Repeated public case identity")
    captured = {case["case_id"]: case for case in capture["cases"]}
    if len(captured) != 24 or not set(captured) <= set(by_id):
        raise ValueError("Capture cases differ from frozen public development split")
    tables = manifest["dump"]["tables"]
    bound = []
    for row in public_rows:
        contract = public_contract(row, tables)
        if contract.get("basis") == "public_evidence_explicit_like_endpoint_and_metric":
            item = {"case_id": row["case_id"], "database_id": row["database_id"],
                    "contract": contract}
            if row["case_id"] in captured:
                sql = captured[row["case_id"]].get("generated_sql")
                item["saved_sql_observations"] = observe_sql(contract, sql) if isinstance(sql, str) else []
                item["saved_sql_available"] = isinstance(sql, str)
            bound.append(item)
    module_path = BASE / "evaluation/bird/endpoint_scope.py"
    return {
        "stage": "M3 E05 explicit public endpoint offline probe",
        "run_status": "complete",
        "formal_benchmark": False,
        "holdout_run": False,
        "database_connected": False,
        "new_model_request_count": 0,
        "development_public_case_count": len(public_rows),
        "captured_case_count": len(captured),
        "bound_case_count": len(bound),
        "bound_cases": bound,
        "source_sha256": {
            "public_development80": sha256(PUBLIC_PATH),
            "authorized_import_manifest": sha256(MANIFEST_PATH),
            "e04_candidate_capture": expected_sha256,
            "endpoint_scope_module": sha256(module_path),
        },
        "meaning": "Public-only applicability and saved SQL observations; no fresh generation, SQL execution or EX scoring.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-capture", type=Path, required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.source_capture.resolve(), args.source_sha256)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "run_status": report["run_status"],
                      "bound_case_count": report["bound_case_count"],
                      "bound_case_ids": [case["case_id"] for case in report["bound_cases"]],
                      "new_model_request_count": 0}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
