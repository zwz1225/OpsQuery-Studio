"""Apply four exact v6 aliases after reviewing the PostgreSQL replay report."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from app.config import BASE_DIR
from evaluation.gold_sql import gold_selection_identity
from evaluation.report_identity import validate_report_identity
from evaluation.result_policy import policy_identity
from evaluation.run_benchmark import compare_results
from evaluation.run_manifest import _digest
from scripts.rescore_m1_e_v3_strict import amended_case, require, sha256, strict
from scripts.rescore_m1_e_v6_strict2 import (
    CASES, FORMAL_SHA256, RESULTS, REVIEWED, SOURCE, SOURCE_RUN_ID,
    SOURCE_SHA256, preflight,
)


FROZEN = RESULTS / "m1_e_all_cases_before_v6_strict2_20261014.jsonl"
UPDATED_SHA256 = "82761737b873c9d4e9daac852bb3bf30867adc01919d088289dc9ba03972ed33"


def proposed_case_bytes(original_bytes: bytes) -> tuple[bytes, list[dict]]:
    lines = original_bytes.decode("utf-8").splitlines()
    parsed = [json.loads(line) for line in lines]
    positions = {case["case_id"]: index for index, case in enumerate(parsed)}
    require(len(lines) == len(positions) == 430, "Formal case list changed")
    updated_lines = lines[:]
    proposed_cases = []
    for case_id, review in REVIEWED.items():
        original = parsed[positions[case_id]]
        proposed = amended_case(original, {
            "aliases": review["aliases"], "auxiliary_columns": [],
        })
        require({key: value for key, value in original.items()
                 if key != "column_aliases"} ==
                {key: value for key, value in proposed.items()
                 if key != "column_aliases"},
                "Case content changed beyond exact aliases: " + case_id)
        proposed_cases.append(proposed)
        updated_lines[positions[case_id]] = json.dumps(
            proposed, ensure_ascii=False, separators=(",", ":"),
        )
    require(sum(old != new for old, new in zip(lines, updated_lines)) == 2,
            "Expected exactly two changed formal case lines")
    return ("\n".join(updated_lines) + "\n").encode("utf-8"), proposed_cases


def apply(replay_path: Path, expected_replay_sha256: str, output: Path) -> dict:
    protected = {CASES.resolve(), SOURCE.resolve(), replay_path.resolve(), FROZEN.resolve()}
    require(not output.exists() and output.resolve() not in protected,
            "Choose a fresh application-report path")
    require(len(expected_replay_sha256) == 64 and
            sha256(replay_path) == expected_replay_sha256,
            "Reviewed replay SHA-256 differs")
    source_report, by_id, source_rows, proposed, projections = preflight()
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    manifest = validate_report_identity(replay)
    proposed_cases = [proposed[case_id] for case_id in REVIEWED]
    require(
        replay.get("run_status") == "complete"
        and replay.get("formal_cases_modified") is False
        and replay.get("formal_cases_sha256") == FORMAL_SHA256
        and replay.get("source_report_sha256") == SOURCE_SHA256
        and replay.get("new_model_request_count") == 0
        and replay.get("summary") == {
            "case_count": 2, "original_strict_pass_count": 0,
            "candidate_strict_pass_count": 2, "loose_pass_count": 2,
            "alias_addition_count": 4, "failed_case_ids": [],
        }
        and manifest["mode"] == "offline_rescore"
        and manifest["scope"] == "m1_e_v6_strict2"
        and manifest["source_identity"] ==
            source_report["run_manifest"]["source_identity"]
        and manifest["versions"]["physical_schema"] ==
            source_report["run_manifest"]["versions"]["physical_schema"]
        and manifest["dataset"]["case_ids"] == list(REVIEWED)
        and _digest(proposed_cases) == manifest["dataset"]["version"]
        and policy_identity(proposed_cases) == manifest["result_policy"]
        and gold_selection_identity(proposed_cases, manifest["source_identity"])
            == manifest["gold_selection"],
        "Independent PostgreSQL replay is missing or incomplete",
    )
    evidence = replay.get("cases") or []
    require([item.get("case_id") for item in evidence] == list(REVIEWED),
            "Replay case order differs")
    for item in evidence:
        case_id = item["case_id"]
        original, row = by_id[case_id], source_rows[case_id]
        require(
            item["source_run_id"] == SOURCE_RUN_ID == row["run_id"]
            and item["generated_sql"] == row["generated_sql"]
            and item["generated_sql_sha256"] == REVIEWED[case_id]["sql_sha256"]
            and item["postgres_gold_sql"] == row["result_metrics"]["gold_sql"]
            and item["projection_review"] == projections[case_id]
            and item["alias_additions"] == REVIEWED[case_id]["aliases"]
            and item["allowed_auxiliary_columns_additions"] == []
            and item["actual_columns"] == [projection["actual_column"]
                                           for projection in projections[case_id]]
            and item["gold_columns"] == original["expected_columns"]
            and item["original_strict"] is False
            and item["candidate_strict"] is True
            and item["loose_correct"] is True
            and len(item["actual_rows"]) ==
                row["result_metrics"]["generated_result_rows"]
            and len(item["gold_rows"]) == row["result_metrics"]["gold_result_rows"],
            "Replay columns, rows, or pinned SQL differ: " + case_id,
        )
        gold = {"columns": item["gold_columns"], "rows": item["gold_rows"]}
        frozen = {"columns": original["expected_columns"],
                  "rows": original["expected_rows"]}
        actual_columns, actual_rows = item["actual_columns"], item["actual_rows"]
        require(
            strict(gold["columns"], gold["rows"], frozen, original)[0]
            and strict(actual_columns, actual_rows, gold, original)[0] is False
            and strict(actual_columns, actual_rows, gold, proposed[case_id])[0] is True
            and compare_results(
                actual_columns, actual_rows, gold["columns"], gold["rows"],
                bool(original.get("order_sensitive", True)),
                order_by_column=original.get("order_by_column"),
                top_n_tie_policy=original.get("top_n_tie_policy"),
            )[0] is True,
            "Saved PostgreSQL rows do not reproduce reviewed scores: " + case_id,
        )

    original_bytes = CASES.read_bytes()
    require(hashlib.sha256(original_bytes).hexdigest() == FORMAL_SHA256,
            "Formal cases changed during application")
    updated, recalculated_cases = proposed_case_bytes(original_bytes)
    require(recalculated_cases == proposed_cases and
            hashlib.sha256(updated).hexdigest() == UPDATED_SHA256,
            "Unexpected formal case content after exact aliases")
    if FROZEN.exists():
        require(FROZEN.read_bytes() == original_bytes,
                "Existing frozen case file differs from v6 source")
    else:
        FROZEN.parent.mkdir(parents=True, exist_ok=True)
        with FROZEN.open("xb") as stream:
            stream.write(original_bytes)

    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=CASES.parent, prefix="m1_e_v6_strict2_",
            suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(updated)
        temporary.replace(CASES)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    result = {
        "stage": "M1 E v6 two-case exact strict policy applied",
        "run_status": "complete", "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source_cases_sha256": FORMAL_SHA256,
        "updated_cases_sha256": sha256(CASES),
        "source_report_sha256": SOURCE_SHA256,
        "replay_report_sha256": expected_replay_sha256,
        "changed_case_ids": list(REVIEWED),
        "changed_case_count": 2, "alias_addition_count": 4,
        "new_model_request_count": 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path,
                        default=RESULTS / "m1_e_v6_strict2_rescore_server.json")
    parser.add_argument("--replay-sha256", required=True)
    parser.add_argument("--output", type=Path,
                        default=RESULTS / "m1_e_v6_strict2_apply_server.json")
    args = parser.parse_args()
    print(json.dumps(apply(args.replay.resolve(), args.replay_sha256,
                           args.output.resolve()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
