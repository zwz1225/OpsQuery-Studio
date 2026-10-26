"""Apply four explicit M1 E v3 policy changes after PostgreSQL replay.

This command changes only the reviewed cases' explicit aliases and, for
GROWTH_OPS-100, two exact auxiliary column allowances. Run it only after the
independent PostgreSQL report has been checked.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from app.config import BASE_DIR
from evaluation.report_identity import validate_report_identity
from scripts.rescore_m1_e_v3_strict import (
    CASES, FORMAL_SHA256, RESULTS, REVIEWED, SOURCES, amended_case,
    require, sha256, strict,
)


FROZEN = RESULTS / "m1_e_all_cases_before_v3_strict4_20261013.jsonl"


def apply(replay_path: Path, output: Path) -> dict:
    protected = {CASES.resolve(), replay_path.resolve(), FROZEN.resolve(), *(
        (RESULTS / name).resolve() for name in SOURCES
    )}
    require(not output.exists() and output.resolve() not in protected,
            "Choose a fresh application-report path")
    require(sha256(CASES) == FORMAL_SHA256, "Formal cases differ from v3 source")
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    manifest = validate_report_identity(replay)
    require(replay.get("run_status") == "complete" and
            replay.get("formal_cases_modified") is False and
            replay.get("formal_cases_sha256") == FORMAL_SHA256 and
            replay.get("new_model_request_count") == 0 and
            replay.get("summary") == {
                "case_count": 4, "original_strict_pass_count": 0,
                "candidate_strict_pass_count": 4, "loose_pass_count": 4,
                "alias_addition_count": 7, "auxiliary_allow_count": 2,
            }, "Independent PostgreSQL replay is missing or incomplete")
    require(manifest["source_identity"]["backend"] == "postgresql" and
            manifest["scope"] == "m1_e_v3_strict4" and
            replay.get("source_report_sha256") == {
                name: SOURCES[name]["sha256"] for name in SOURCES
            } and all(
                sha256(RESULTS / name) == identity["sha256"]
                for name, identity in SOURCES.items()
            ), "Source reports or source identity changed")
    evidence = replay.get("cases") or []
    require([item.get("case_id") for item in evidence] == list(REVIEWED),
            "Replay case order differs from reviewed cases")

    original_bytes = CASES.read_bytes()
    lines = original_bytes.decode("utf-8").splitlines()
    parsed = [json.loads(line) for line in lines]
    positions = {row["case_id"]: index for index, row in enumerate(parsed)}
    require(len(lines) == len(positions) == 430, "Formal case list changed")
    amended_lines = lines[:]
    for item in evidence:
        case_id = item["case_id"]
        original = parsed[positions[case_id]]
        proposal = REVIEWED[case_id]
        amended = amended_case(original, proposal)
        require(item["generated_sql_sha256"] == proposal["sql_sha256"] and
                item["alias_additions"] == proposal["aliases"] and
                item["allowed_auxiliary_columns_additions"] == proposal["auxiliary_columns"] and
                item["original_strict"] is False and
                item["candidate_strict"] is True and
                item["loose_correct"] is True,
                "Replay evidence differs from reviewed policy: " + case_id)
        gold = {"columns": item["gold_columns"], "rows": item["gold_rows"]}
        require(strict(item["actual_columns"], item["actual_rows"], gold, original)[0] is False
                and strict(item["actual_columns"], item["actual_rows"], gold, amended)[0] is True,
                "Saved PostgreSQL rows do not reproduce strict scoring: " + case_id)
        unchanged = {key: value for key, value in original.items()
                     if key not in {"column_aliases", "allowed_auxiliary_columns"}}
        amended_unchanged = {key: value for key, value in amended.items()
                             if key not in {"column_aliases", "allowed_auxiliary_columns"}}
        require(unchanged == amended_unchanged,
                "Case content changed beyond the reviewed policy: " + case_id)
        amended_lines[positions[case_id]] = json.dumps(
            amended, ensure_ascii=False, separators=(",", ":"),
        )

    updated = ("\n".join(amended_lines) + "\n").encode("utf-8")
    require(sum(old != new for old, new in zip(lines, amended_lines)) == 4 and
            updated != original_bytes and sha256(CASES) == FORMAL_SHA256,
            "Expected exactly four changed formal case lines")
    if FROZEN.exists():
        require(FROZEN.read_bytes() == original_bytes,
                "Existing frozen case file differs from v3 source")
    else:
        FROZEN.parent.mkdir(parents=True, exist_ok=True)
        with FROZEN.open("xb") as stream:
            stream.write(original_bytes)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=CASES.parent, prefix="m1_e_v3_strict_",
            suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(updated)
        temporary.replace(CASES)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    report = {
        "stage": "M1 E v3 four-case exact strict policy applied",
        "run_status": "complete", "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source_cases_sha256": FORMAL_SHA256,
        "updated_cases_sha256": sha256(CASES),
        "replay_report_sha256": sha256(replay_path),
        "changed_case_ids": list(REVIEWED),
        "changed_case_count": 4,
        "alias_addition_count": 7,
        "auxiliary_allow_count": 2,
        "new_model_request_count": 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path,
                        default=RESULTS / "m1_e_v3_strict4_rescore_server.json")
    parser.add_argument("--output", type=Path,
                        default=RESULTS / "m1_e_v3_strict4_apply_server.json")
    args = parser.parse_args()
    print(json.dumps(apply(args.replay.resolve(), args.output.resolve()),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
