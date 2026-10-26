"""Apply seven reviewed exact column mappings after PostgreSQL replay."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from app.config import BASE_DIR
from evaluation.gold_sql import gold_selection_identity
from evaluation.report_identity import validate_report_identity
from evaluation.result_policy import policy_identity
from evaluation.run_manifest import _digest
from scripts.rescore_m1_e_v3_strict import amended_case, require, sha256, strict
from scripts.rescore_m1_e_v4_strict7 import (
    CASES, FORMAL_SHA256, RESULTS, REVIEWED, SOURCES,
)


REPLAY_SHA256 = "7a400f6ce7835672a80e2f30fd8ac6147366b8f96c3a7983c05a771fd96fed92"
FROZEN = RESULTS / "m1_e_all_cases_before_v4_strict7_20261014.jsonl"


def apply(replay_path: Path, output: Path) -> dict:
    protected = {CASES.resolve(), replay_path.resolve(), FROZEN.resolve(), *(
        (RESULTS / name).resolve() for name in SOURCES
    )}
    require(not output.exists() and output.resolve() not in protected,
            "Choose a fresh application-report path")
    require(sha256(CASES) == FORMAL_SHA256, "Formal cases differ from v4 source")
    require(sha256(replay_path) == REPLAY_SHA256,
            "Reviewed PostgreSQL replay report differs")

    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    manifest = validate_report_identity(replay)
    require(
        replay.get("run_status") == "complete"
        and replay.get("formal_cases_modified") is False
        and replay.get("formal_cases_sha256") == FORMAL_SHA256
        and replay.get("new_model_request_count") == 0
        and replay.get("summary") == {
            "case_count": 7,
            "original_strict_pass_count": 0,
            "candidate_strict_pass_count": 7,
            "loose_pass_count": 7,
            "alias_addition_count": 16,
            "auxiliary_allow_count": 0,
            "failed_case_ids": [],
        }
        and manifest["mode"] == "offline_rescore"
        and manifest["scope"] == "m1_e_v4_strict7"
        and manifest["source_identity"]["source_id"] == "short_video_ops_postgres"
        and manifest["source_identity"]["backend"] == "postgresql"
        and manifest["dataset"]["case_ids"] == list(REVIEWED),
        "Independent PostgreSQL replay is missing or incomplete",
    )
    source_paths = [RESULTS / name for name in SOURCES]
    require(
        replay.get("source_report_sha256") == {
            name: item["sha256"] for name, item in SOURCES.items()
        }
        and all(sha256(path) == SOURCES[path.name]["sha256"]
                for path in source_paths),
        "v4 source reports differ from reviewed evidence",
    )
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in source_paths]
    require(all(validate_report_identity(report)["source_identity"] ==
                manifest["source_identity"] for report in reports)
            and all(report["run_manifest"]["versions"]["physical_schema"] ==
                    manifest["versions"]["physical_schema"] for report in reports),
            "PostgreSQL source identity or physical schema changed")
    source_rows = {case["case_id"]: case for report in reports
                   for case in report["cases"]}

    original_bytes = CASES.read_bytes()
    lines = original_bytes.decode("utf-8").splitlines()
    parsed = [json.loads(line) for line in lines]
    positions = {row["case_id"]: index for index, row in enumerate(parsed)}
    require(len(lines) == len(positions) == 430, "Formal case list changed")
    amended_lines = lines[:]
    evidence = replay.get("cases") or []
    require([item.get("case_id") for item in evidence] == list(REVIEWED),
            "Replay case order differs from reviewed cases")
    proposed_cases = []
    for item in evidence:
        case_id = item["case_id"]
        original = parsed[positions[case_id]]
        proposal = REVIEWED[case_id]
        amended = amended_case(original, proposal)
        source = source_rows[case_id]
        require(
            item["source_run_id"] == source["run_id"]
            and item["generated_sql"] == source["generated_sql"]
            and item["postgres_gold_sql"] == source["result_metrics"]["gold_sql"]
            and item["generated_sql_sha256"] == proposal["sql_sha256"]
            and item["alias_additions"] == proposal["aliases"]
            and item["allowed_auxiliary_columns_additions"] == []
            and item["original_strict"] is False
            and item["candidate_strict"] is True
            and item["loose_correct"] is True,
            "Replay evidence differs from reviewed SQL or policy: " + case_id,
        )
        gold = {"columns": item["gold_columns"], "rows": item["gold_rows"]}
        frozen = {"columns": original["expected_columns"],
                  "rows": original["expected_rows"]}
        require(
            strict(item["gold_columns"], item["gold_rows"], frozen, original)[0]
            and strict(item["actual_columns"], item["actual_rows"], gold,
                       original)[0] is False
            and strict(item["actual_columns"], item["actual_rows"], gold,
                       amended)[0] is True,
            "Saved PostgreSQL rows do not reproduce strict scoring: " + case_id,
        )
        unchanged = {key: value for key, value in original.items()
                     if key not in {"column_aliases", "allowed_auxiliary_columns"}}
        amended_unchanged = {key: value for key, value in amended.items()
                             if key not in {"column_aliases", "allowed_auxiliary_columns"}}
        require(unchanged == amended_unchanged,
                "Case content changed beyond exact aliases: " + case_id)
        proposed_cases.append(amended)
        amended_lines[positions[case_id]] = json.dumps(
            amended, ensure_ascii=False, separators=(",", ":"),
        )

    require(
        _digest(proposed_cases) == manifest["dataset"]["version"]
        and policy_identity(proposed_cases) == manifest["result_policy"]
        and gold_selection_identity(proposed_cases, manifest["source_identity"])
            == manifest["gold_selection"],
        "Replay manifest does not represent the proposed seven cases",
    )
    updated = ("\n".join(amended_lines) + "\n").encode("utf-8")
    require(sum(old != new for old, new in zip(lines, amended_lines)) == 7
            and updated != original_bytes and sha256(CASES) == FORMAL_SHA256,
            "Expected exactly seven changed formal case lines")
    if FROZEN.exists():
        require(FROZEN.read_bytes() == original_bytes,
                "Existing frozen case file differs from v4 source")
    else:
        FROZEN.parent.mkdir(parents=True, exist_ok=True)
        with FROZEN.open("xb") as stream:
            stream.write(original_bytes)

    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=CASES.parent, prefix="m1_e_v4_strict_",
            suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(updated)
        temporary.replace(CASES)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    report = {
        "stage": "M1 E v4 seven-case exact strict policy applied",
        "run_status": "complete",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source_cases_sha256": FORMAL_SHA256,
        "updated_cases_sha256": sha256(CASES),
        "replay_report_sha256": REPLAY_SHA256,
        "source_report_sha256": replay["source_report_sha256"],
        "changed_case_ids": list(REVIEWED),
        "changed_case_count": 7,
        "alias_addition_count": 16,
        "auxiliary_allow_count": 0,
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
                        default=RESULTS / "m1_e_v4_strict7_rescore_server.json")
    parser.add_argument("--output", type=Path,
                        default=RESULTS / "m1_e_v4_strict7_apply_server.json")
    args = parser.parse_args()
    print(json.dumps(apply(args.replay.resolve(), args.output.resolve()),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
