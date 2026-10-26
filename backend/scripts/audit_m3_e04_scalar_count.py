"""Offline, public-input-only scan of saved E02 SQL for E04 boundaries."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from evaluation.bird.scalar_count_shape import public_contract, shape_issues


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scan(public_path: Path, captures: dict[str, Path]) -> dict:
    public = [json.loads(line) for line in public_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [row["case_id"] for row in public]
    if len(ids) != 80 or len(set(ids)) != 80:
        raise ValueError("Expected the fixed development80 public split")
    contracts = {row["case_id"]: public_contract(row) for row in public}
    result = {
        "stage": "M3 E04 saved-SQL public-boundary audit",
        "run_status": "complete",
        "formal_benchmark": False,
        "new_model_request_count": 0,
        "postgresql_connected": False,
        "public_input_sha256": sha(public_path),
        "contract_counts": {kind: sum(c["enforcement"] == kind for c in contracts.values()) for kind in
                            ("none", "advisory", "hard_for_simple_outer_select")},
        "hard_case_ids": [cid for cid in ids if contracts[cid]["enforcement"] == "hard_for_simple_outer_select"],
        "captures": {},
    }
    for side, path in captures.items():
        report = json.loads(path.read_bytes())
        cases = report.get("cases", [])
        if report.get("run_status") != "complete" or [c["case_id"] for c in cases] != ids:
            raise ValueError("Saved capture is not the complete ordered development80 split")
        flagged = []
        for case in cases:
            sql = case.get("generated_sql")
            if not isinstance(sql, str) or not sql.strip():
                continue
            issues = shape_issues(contracts[case["case_id"]], sql)
            if issues:
                flagged.append({"case_id": case["case_id"], "issue_codes": [i["code"] for i in issues]})
        result["captures"][side] = {"source_sha256": sha(path), "saved_case_count": len(cases),
                                    "flagged": flagged}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-input", type=Path, required=True)
    parser.add_argument("--baseline-capture", type=Path, required=True)
    parser.add_argument("--candidate-capture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = scan(args.public_input, {"baseline": args.baseline_capture, "candidate": args.candidate_capture})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "contract_counts": report["contract_counts"],
                      "captures": {s: r["flagged"] for s, r in report["captures"].items()}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
