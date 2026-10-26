"""Replay saved E05 SQL through the public-only endpoint feedback proposal."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from evaluation.bird.endpoint_validation import POLICY, inspect
from evaluation.bird_protocol import validate_agent_input
from scripts.m2_b_common import BASE


PUBLIC = BASE / "evaluation/cases/bird_mini_dev/m2_pg_v1/inputs/development80.jsonl"
MANIFEST = BASE / "evaluation/cases/bird_mini_dev/m2_b_import_spec_v1.json"
MODULE = BASE / "evaluation/bird/endpoint_validation.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_capture(path: Path, expected_sha: str) -> dict:
    if sha(path) != expected_sha:
        raise ValueError("Capture SHA-256 differs from frozen input")
    report = json.loads(path.read_bytes())
    if (report.get("run_status") != "complete" or len(report.get("cases", [])) != 24
            or len(set(report.get("selected_case_ids", []))) != 24):
        raise ValueError("Expected one complete E05 development24 capture")
    if [case["case_id"] for case in report["cases"]] != report["selected_case_ids"]:
        raise ValueError("Capture case order differs")
    return report


def audit(captures: dict[str, tuple[Path, str]]) -> dict:
    rows = [json.loads(line) for line in PUBLIC.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 80:
        raise ValueError("Expected frozen public development80 input")
    for row in rows:
        validate_agent_input(row)
    public = {row["case_id"]: row for row in rows}
    if len(public) != 80:
        raise ValueError("Duplicate public case ID")
    tables = json.loads(MANIFEST.read_bytes())["dump"]["tables"]
    reports = {side: load_capture(*entry) for side, entry in captures.items()}
    if set(reports) != {"baseline", "candidate"}:
        raise ValueError("Expected both E05 sides")
    if (reports["baseline"]["selected_case_ids"] != reports["candidate"]["selected_case_ids"]
            or reports["baseline"]["source_binding"] != reports["candidate"]["source_binding"]):
        raise ValueError("Paired source/case identity differs")
    selected = reports["baseline"]["selected_case_ids"]
    if not set(selected) <= set(public):
        raise ValueError("Captured input outside frozen public development split")
    outcomes = {}
    for side, report in reports.items():
        items = []
        for case in report["cases"]:
            sql = case.get("generated_sql")
            decision = inspect(public[case["case_id"]], tables, sql)
            items.append({"case_id": case["case_id"], "database_id": case["database_id"],
                          "sql_sha256": hashlib.sha256(sql.encode("utf-8")).hexdigest() if isinstance(sql, str) else None,
                          "decision": decision})
        outcomes[side] = {"case_count": len(items),
                          "candidate_repair_ids": [v["case_id"] for v in items
                                                   if v["decision"]["status"] == "candidate_repair"],
                          "pass_ids": [v["case_id"] for v in items if v["decision"]["status"] == "pass"],
                          "abstain_count": sum(v["decision"]["status"] == "abstain" for v in items),
                          "cases": items}
    return {"stage": "M3 E06 endpoint validation feedback offline replay",
            "run_status": "complete", "policy": POLICY, "formal_benchmark": False,
            "holdout_run": False, "database_connected": False, "gold_loaded": False,
            "new_model_request_count": 0, "source_sha256": {
                "public_development80": sha(PUBLIC), "authorized_import_manifest": sha(MANIFEST),
                "validation_module": sha(MODULE),
                **{side + "_capture": expected for side, (_, expected) in captures.items()}},
            "public_case_count": len(rows), "selected_case_ids": selected,
            "outcomes": outcomes,
            "meaning": "Static analysis of saved SQL; proposed feedback only, no validator change or new model generation."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for side in ("baseline", "candidate"):
        parser.add_argument("--" + side + "-capture", type=Path, required=True)
        parser.add_argument("--" + side + "-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    captures = {side: (getattr(args, side + "_capture").resolve(),
                       getattr(args, side + "_sha256")) for side in ("baseline", "candidate")}
    report = audit(captures)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "run_status": report["run_status"],
                      "candidate_repair_ids": {s: v["candidate_repair_ids"]
                                               for s, v in report["outcomes"].items()},
                      "new_model_request_count": 0}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
