"""Replay the saved phase83 SQL and rescore only the reviewed Top N tie case."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json

from app.config import BASE_DIR
from app.querying.duckdb_engine import DuckDbEngine
from app.security import AccessController
from evaluation.run_benchmark import (
    compare_results, compare_results_strict, load_cases, summarize,
)
from evaluation.run_manifest import build_run_manifest


ROOT = BASE_DIR / "evaluation"
RESULTS = ROOT / "results"
SOURCE = ROOT / "cases" / "all_cases.jsonl"
BACKUP = RESULTS / "m0_all_cases_before_topn_tie_20260929.jsonl"
COHORT = ROOT / "cases" / "phase83_validation.json"
INPUTS = {
    label: RESULTS / f"m0_phase83_live_{label}_alias_rescore.json"
    for label in ("off", "on")
}
OUTPUTS = {
    label: RESULTS / f"m0_phase83_live_{label}_tie_rescore.json"
    for label in ("off", "on")
}
CASE_ID = "CONTENT_OPS-025"


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(engine, sql, scope, label):
    result = engine.execute("short_video_ops", sql, scope, row_limit=10000)
    require(result.success and not result.truncated,
            f"{label} SQL replay failed: {result.error}")
    return result


def main() -> None:
    require(BACKUP.is_file() and SOURCE.is_file(), "Case source or backup missing")
    require(sha(BACKUP) ==
            "36e65b72415c78199d6069559700a3abcc177dba860c92e49f9cafc6dfc31f5d",
            "Pre-tie Case backup differs from review")
    require(all(path.is_file() for path in INPUTS.values()), "Alias rescore input missing")
    require(all(not path.exists() for path in OUTPUTS.values()),
            "Tie rescore output exists; reports will not be overwritten")
    ids = json.loads(COHORT.read_text(encoding="utf-8"))["case_ids"]
    old_all = load_cases(BACKUP, set(), False)
    new_all = load_cases(SOURCE, set(), False)
    require(len(old_all) == len(new_all) == 430 and len(ids) == 30,
            "Unexpected Case count")
    old = {case["case_id"]: case for case in old_all}
    new = {case["case_id"]: case for case in new_all}
    require(list(old) == list(new), "Case IDs or order changed")
    changed = [case_id for case_id in old if old[case_id] != new[case_id]]
    require(changed == [CASE_ID] and
            {key: value for key, value in new[CASE_ID].items()
             if key != "top_n_tie_policy"} == old[CASE_ID],
            "Changes exceed the reviewed tie policy")
    policy = new[CASE_ID]["top_n_tie_policy"]
    require(policy["limit"] == 10 and policy["boundary_value"] == 8 and
            len(policy["boundary_candidates"]) == 12,
            "Reviewed tie policy differs")

    engine = DuckDbEngine()
    scope = AccessController().resolve("demo_content_ops")
    gold = replay(engine, old[CASE_ID]["gold_sql"], scope, "Gold")

    for label, source in INPUTS.items():
        report = json.loads(source.read_text(encoding="utf-8"))
        require(report.get("rescore_status") == "complete" and
                [row["case_id"] for row in report["cases"]] == ids,
                f"{label} alias report incomplete or different")
        prior_manifest = report["rescore_manifest"]
        require(prior_manifest["rescored_dataset_version"] ==
                build_run_manifest(
                    [old[case_id] for case_id in ids], base_dir=BASE_DIR,
                    mode="live", scope="all",
                    config=report["source_run_manifest"]["config"],
                    case_source=BACKUP, case_list=COHORT,
                )["dataset"]["version"],
                f"{label} alias dataset version differs")
        rows = deepcopy(report["cases"])
        require(summarize(rows, "live") == report["summary"],
                f"{label} alias report summary differs")
        row = rows[ids.index(CASE_ID)]
        actual = replay(engine, row["generated_sql"], scope, label)
        args = (actual.columns, actual.rows, gold.columns, gold.rows, True)
        options = {"order_by_column": "plays"}
        old_loose, old_column_match, _ = compare_results(*args, **options)
        old_strict, _ = compare_results_strict(
            *args, **options, column_aliases=old[CASE_ID]["column_aliases"],
        )
        require(old_loose == row["result_correct"] and
                old_strict == row["strict_result_correct"] and
                old_column_match == row["column_match"] and
                not old_loose and not old_strict,
                f"{label} previous CONTENT_OPS-025 score did not replay")
        new_options = {**options, "top_n_tie_policy": policy}
        loose, column_match, reason = compare_results(*args, **new_options)
        strict, strict_reason = compare_results_strict(
            *args, **new_options, column_aliases=new[CASE_ID]["column_aliases"],
        )
        require(loose and strict and column_match is False,
                f"{label} reviewed cutoff members did not pass")
        row["result_correct"] = loose
        row["strict_result_correct"] = strict
        row["comparison_reason"] = reason
        row["strict_comparison_reason"] = strict_reason
        row["result_metrics"].update({"correct": loose, "reason": reason,
                                      "strict_correct": strict,
                                      "strict_reason": strict_reason})
        row["offline_top_n_tie_rescore"] = {
            "old_loose_correct": old_loose,
            "old_strict_correct": old_strict,
            "new_loose_correct": loose,
            "new_strict_correct": strict,
            "gold_row_count": len(gold.rows),
            "generated_row_count": len(actual.rows),
            "boundary_candidate_count": len(policy["boundary_candidates"]),
        }
        summary = summarize(rows, "live")
        for key, value in report["summary"].items():
            if key not in ("result_accuracy", "strict_result_accuracy",
                           "result_accuracy_given_executed_sql"):
                require(summary[key] == value,
                        f"Unrelated {label} summary changed: {key}")
        current_manifest = build_run_manifest(
            [new[case_id] for case_id in ids], base_dir=BASE_DIR,
            mode="live", scope="all",
            config=report["source_run_manifest"]["config"],
            case_source=SOURCE, case_list=COHORT,
        )
        payload = {
            "rescore_status": "complete",
            "summary": summary,
            "cases": rows,
            "source_run_manifest": report["source_run_manifest"],
            "rescore_manifest": {
                "type": "offline_sql_replay_with_case_scoped_top_n_tie_policy",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source_report": source.relative_to(BASE_DIR).as_posix(),
                "source_report_sha256": sha(source),
                "source_run_id": report["source_run_manifest"]["run_id"],
                "original_cases_sha256": sha(BACKUP),
                "current_cases_sha256": sha(SOURCE),
                "original_dataset_version": prior_manifest["rescored_dataset_version"],
                "rescored_dataset_version": current_manifest["dataset"]["version"],
                "tie_case_id": CASE_ID,
                "model_requests": 0,
            },
        }
        target = OUTPUTS[label]
        temp = target.with_suffix(target.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        temp.replace(target)
        print(f"{label}: loose={summary['result_accuracy']}"
              f" strict={summary['strict_result_accuracy']} output={target}")


if __name__ == "__main__":
    main()
