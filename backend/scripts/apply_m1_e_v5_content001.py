"""Apply three exact CONTENT_OPS-001 aliases after reviewed PostgreSQL replay."""

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
from scripts.rescore_m1_e_v5_content001 import (
    CASES, CASE_ID, FORMAL_SHA256, PROJECTIONS, RESULTS, REVIEW,
    SOURCE, SOURCE_RUN_ID, SOURCE_SHA256, SQL_SHA256, preflight,
)


FROZEN = RESULTS / "m1_e_all_cases_before_v5_content001_20261014.jsonl"
UPDATED_SHA256 = "08cf84a50f43eb2d176d96246e1210c398a13a89beec69a9d0db1b7361b7815a"


def apply(replay_path: Path, expected_replay_sha256: str, output: Path) -> dict:
    protected = {CASES.resolve(), SOURCE.resolve(), replay_path.resolve(), FROZEN.resolve()}
    require(not output.exists() and output.resolve() not in protected,
            "Choose a new application-report path")
    require(len(expected_replay_sha256) == 64 and
            sha256(replay_path) == expected_replay_sha256,
            "Reviewed replay SHA-256 differs")
    source_report, source_row, original, proposed, projection_review = preflight()
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    manifest = validate_report_identity(replay)
    require(
        replay.get("run_status") == "complete"
        and replay.get("formal_cases_modified") is False
        and replay.get("formal_cases_sha256") == FORMAL_SHA256
        and replay.get("source_report_sha256") == SOURCE_SHA256
        and replay.get("new_model_request_count") == 0
        and replay.get("summary") == {
            "case_count": 1,
            "original_strict_pass_count": 0,
            "candidate_strict_pass_count": 1,
            "loose_pass_count": 1,
            "alias_addition_count": 3,
            "failed_case_ids": [],
        }
        and manifest["mode"] == "offline_rescore"
        and manifest["scope"] == "m1_e_v5_content001"
        and manifest["source_identity"] == source_report["run_manifest"]["source_identity"]
        and manifest["versions"]["physical_schema"] ==
            source_report["run_manifest"]["versions"]["physical_schema"]
        and manifest["dataset"]["case_ids"] == [CASE_ID]
        and _digest([proposed]) == manifest["dataset"]["version"]
        and policy_identity([proposed]) == manifest["result_policy"]
        and gold_selection_identity([proposed], manifest["source_identity"])
            == manifest["gold_selection"],
        "Independent PostgreSQL replay is missing or incomplete",
    )
    require(len(replay.get("cases") or []) == 1, "Replay needs exactly one case")
    item = replay["cases"][0]
    require(
        item.get("case_id") == CASE_ID
        and item.get("source_run_id") == SOURCE_RUN_ID
        and item.get("generated_sql_sha256") == SQL_SHA256
        and item.get("generated_sql") == source_row["generated_sql"]
        and item.get("postgres_gold_sql") == source_row["result_metrics"]["gold_sql"]
        and item.get("projection_review") == projection_review
        and item.get("alias_additions") == REVIEW["aliases"]
        and item.get("allowed_auxiliary_columns_additions") == []
        and item.get("original_strict") is False
        and item.get("candidate_strict") is True
        and item.get("loose_correct") is True
        and item.get("actual_columns") == [PROJECTIONS[name][0]
                                            for name in original["expected_columns"]]
        and item.get("gold_columns") == original["expected_columns"],
        "Replay columns or pinned source evidence differ",
    )
    gold = {"columns": item["gold_columns"], "rows": item["gold_rows"]}
    frozen = {"columns": original["expected_columns"], "rows": original["expected_rows"]}
    actual_columns, actual_rows = item["actual_columns"], item["actual_rows"]
    require(
        strict(gold["columns"], gold["rows"], frozen, original)[0]
        and strict(actual_columns, actual_rows, gold, original)[0] is False
        and strict(actual_columns, actual_rows, gold, proposed)[0] is True
        and compare_results(
            actual_columns, actual_rows, gold["columns"], gold["rows"],
            bool(original.get("order_sensitive", True)),
            order_by_column=original.get("order_by_column"),
            top_n_tie_policy=original.get("top_n_tie_policy"),
        )[0] is True
        and len(actual_rows) == source_row["result_metrics"]["generated_result_rows"]
        and len(gold["rows"]) == source_row["result_metrics"]["gold_result_rows"],
        "Saved PostgreSQL rows do not reproduce reviewed scores",
    )
    require({key: value for key, value in original.items() if key != "column_aliases"} ==
            {key: value for key, value in proposed.items() if key != "column_aliases"},
            "Case content changed beyond explicit aliases")

    original_bytes = CASES.read_bytes()
    lines = original_bytes.decode("utf-8").splitlines()
    positions = [index for index, line in enumerate(lines)
                 if json.loads(line)["case_id"] == CASE_ID]
    require(len(lines) == 430 and len(positions) == 1 and sha256(CASES) == FORMAL_SHA256,
            "Formal cases changed during application")
    lines[positions[0]] = json.dumps(proposed, ensure_ascii=False, separators=(",", ":"))
    updated = ("\n".join(lines) + "\n").encode("utf-8")
    require(updated != original_bytes and
            hashlib.sha256(updated).hexdigest() == UPDATED_SHA256,
            "Unexpected formal case content after exact alias update")
    if FROZEN.exists():
        require(FROZEN.read_bytes() == original_bytes, "Frozen original differs")
    else:
        FROZEN.parent.mkdir(parents=True, exist_ok=True)
        with FROZEN.open("xb") as stream:
            stream.write(original_bytes)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=CASES.parent, prefix="m1_e_v5_content001_",
            suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(updated)
        temporary.replace(CASES)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    report = {
        "stage": "M1 E v5 CONTENT_OPS-001 exact strict policy applied",
        "run_status": "complete",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source_cases_sha256": FORMAL_SHA256,
        "updated_cases_sha256": sha256(CASES),
        "source_report_sha256": SOURCE_SHA256,
        "replay_report_sha256": expected_replay_sha256,
        "changed_case_ids": [CASE_ID],
        "changed_case_count": 1,
        "alias_addition_count": 3,
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
                        default=RESULTS / "m1_e_v5_content001_rescore_server.json")
    parser.add_argument("--replay-sha256", required=True)
    parser.add_argument("--output", type=Path,
                        default=RESULTS / "m1_e_v5_content001_apply_server.json")
    args = parser.parse_args()
    print(json.dumps(apply(args.replay.resolve(), args.replay_sha256,
                           args.output.resolve()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
