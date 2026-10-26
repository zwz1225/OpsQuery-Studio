"""Apply 14 reviewed aliases only after independent PostgreSQL replay passes.

The accepted D3 dataset stays frozen in evaluation/results. This command edits
only column_aliases in the formal case file, with the original first-run
reports and the independent PostgreSQL replay as evidence.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from app.config import BASE_DIR
from scripts.rescore_m1_e_postgres_aliases import (
    CASE_PATH, CLASSIC_PATH, EXPECTED_CASES_SHA256, PHASE_PATH, REVIEW_PATH,
    digest, require, score,
)


FROZEN_CASES = BASE_DIR / "evaluation/results/m1_e_all_cases_before_aliases_20261012.jsonl"
DEFAULT_REPLAY = BASE_DIR / "evaluation/results/m1_e_postgres_alias_rescore_server_v2.json"
DEFAULT_OUTPUT = BASE_DIR / "evaluation/results/m1_e_postgres_alias_apply_server_v2.json"


def apply(replay_path: Path, output: Path) -> dict:
    require(output.resolve() not in {path.resolve() for path in (
        CASE_PATH, FROZEN_CASES, REVIEW_PATH, CLASSIC_PATH, PHASE_PATH,
        replay_path,
    )} and not output.exists(), "Choose a new alias-application report path")
    require(digest(CASE_PATH) == EXPECTED_CASES_SHA256
            and digest(FROZEN_CASES) == EXPECTED_CASES_SHA256
            and CASE_PATH.read_bytes() == FROZEN_CASES.read_bytes(),
            "Formal cases must still equal the frozen pre-alias dataset")
    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    require(replay.get("run_status") == "complete"
            and replay.get("formal_aliases_applied") is False
            and replay.get("source_cases_sha256") == EXPECTED_CASES_SHA256
            and replay.get("review_report_sha256") == digest(REVIEW_PATH)
            and replay.get("new_model_request_count") == 0,
            "Independent PostgreSQL replay is missing or has wrong provenance")
    require(replay.get("source_report_sha256") == {
        CLASSIC_PATH.name: digest(CLASSIC_PATH),
        PHASE_PATH.name: digest(PHASE_PATH),
    } and all(digest(path) == review["report_files"][path.name]["sha256"]
              for path in (CLASSIC_PATH, PHASE_PATH)),
            "First-run report bytes changed")
    identities = [json.loads(path.read_text(encoding="utf-8"))["run_manifest"]["source_identity"]
                  for path in (CLASSIC_PATH, PHASE_PATH)]
    require(replay["run_manifest"]["source_identity"] == identities[0] == identities[1]
            and identities[0]["backend"] == "postgresql", "Replay source identity changed")
    candidates, checked = review["candidate_aliases"], replay.get("cases") or []
    require(len(candidates) == len(checked) == 14
            and [item["case_id"] for item in candidates]
            == [item["case_id"] for item in checked]
            and replay.get("summary") == {
                "case_count": 14, "original_replayed_strict_pass_count": 0,
                "amended_strict_pass_count": 14, "amended_strict_accuracy": 1.0,
                "loose_pass_count": 14, "alias_addition_count": 23,
            }, "Replay must confirm all 14 cases and 23 explicit aliases")

    original_lines = FROZEN_CASES.read_text(encoding="utf-8").splitlines()
    cases = [json.loads(line) for line in original_lines]
    require(len(cases) == len({row["case_id"] for row in cases}) == 430,
            "Formal case set changed")
    positions = {row["case_id"]: index for index, row in enumerate(cases)}
    amended_lines = original_lines[:]
    for candidate, evidence in zip(candidates, checked):
        case_id = candidate["case_id"]
        require(case_id in positions
                and candidate["missing_explicit_aliases"] == evidence["alias_additions"]
                and evidence["source_strict_result_correct"] is False
                and evidence["original_replayed_strict_result_correct"] is False
                and evidence["amended_strict_result_correct"] is True
                and evidence["loose_result_correct"] is True,
                "Candidate was not confirmed by PostgreSQL replay: " + case_id)
        case = cases[positions[case_id]]
        amended = deepcopy(case)
        for pair in candidate["missing_explicit_aliases"]:
            expected, actual = pair["expected"], pair["actual"]
            require(expected in case["expected_columns"] and actual
                    and actual not in amended.get("column_aliases", {}).get(expected, []),
                    "Invalid per-case alias: " + case_id)
            amended.setdefault("column_aliases", {}).setdefault(expected, []).append(actual)
        gold = {"columns": evidence["gold_columns"], "rows": evidence["gold_rows"]}
        require(score(evidence["actual_columns"], evidence["actual_rows"], gold, case)[0] is False
                and score(evidence["actual_columns"], evidence["actual_rows"], gold, amended)[0] is True,
                "Evidence rows do not reproduce strict scoring: " + case_id)
        # Confirm aliases are the only changed field and all remaining bytes stay intact.
        original_without = {key: value for key, value in case.items() if key != "column_aliases"}
        amended_without = {key: value for key, value in amended.items() if key != "column_aliases"}
        require(original_without == amended_without, "Case content changed beyond aliases")
        amended_lines[positions[case_id]] = json.dumps(
            amended, ensure_ascii=False, separators=(",", ":"),
        )

    updated_bytes = ("\n".join(amended_lines) + "\n").encode("utf-8")
    require(updated_bytes != CASE_PATH.read_bytes() and
            sum(old != new for old, new in zip(original_lines, amended_lines)) == 14,
            "Expected exactly 14 changed case lines")
    require(digest(CASE_PATH) == EXPECTED_CASES_SHA256,
            "Formal cases changed during alias review")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=CASE_PATH.parent,
                                         prefix="m1_e_alias_", suffix=".tmp",
                                         delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(updated_bytes)
        temporary.replace(CASE_PATH)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    report = {
        "stage": "M1 E confirmed PostgreSQL aliases applied to formal cases",
        "run_status": "complete", "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source_cases_sha256": EXPECTED_CASES_SHA256,
        "updated_cases_sha256": digest(CASE_PATH),
        "replay_report_sha256": digest(replay_path),
        "changed_case_count": 14, "alias_addition_count": 23,
        "changed_case_ids": [item["case_id"] for item in candidates],
        "new_model_request_count": 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(apply(args.replay.resolve(), args.output.resolve()),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
