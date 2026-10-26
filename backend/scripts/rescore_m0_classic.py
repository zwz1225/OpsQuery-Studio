"""Offline rescore of the saved M0 classic live run after per-case alias review.

Run from backend: python -m scripts.rescore_m0_classic
This replays saved SQL against the version-matched local data; it never calls a model.
If the pre-alias Case backup is absent, the script reconstructs it from the current
Cases and verifies the reconstructed dataset digest against the original report.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from app.config import BASE_DIR
from app.querying.duckdb_engine import DuckDbEngine
from app.security import AccessController
from evaluation.run_benchmark import compare_results, compare_results_strict, load_cases, summarize
from evaluation.run_manifest import build_run_manifest


RESULTS = BASE_DIR / "evaluation" / "results"
CURRENT_CASES = BASE_DIR / "evaluation" / "cases" / "all_cases.jsonl"
ORIGINAL_CASES = RESULTS / "m0_all_cases_before_aliases_20260929.jsonl"
SOURCE = RESULTS / "m0_live_classic_server.json"
OUTPUT = RESULTS / "m0_live_classic_alias_rescore.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows_digest(rows: list[dict]) -> str:
    encoded = json.dumps(rows, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def replay(engine: DuckDbEngine, sql: str, scope: object, case_id: str, kind: str):
    result = engine.execute("short_video_ops", sql, scope, row_limit=10000)
    require(result.success, f"{case_id}: {kind} SQL replay failed: {result.error}")
    require(not result.truncated, f"{case_id}: {kind} SQL replay exceeded 10000 rows")
    return result


def rescore(source: Path, original_cases_path: Path, current_cases_path: Path) -> dict:
    saved = json.loads(source.read_text(encoding="utf-8"))
    source_manifest = saved.get("run_manifest") or {}
    require(saved.get("run_status") == "complete", "Source report is not complete")
    require(source_manifest.get("mode") == "live" and source_manifest.get("scope") == "classic",
            "Source report must be a live classic run")
    require(source_manifest.get("dataset", {}).get("case_list") is None,
            "Source report used an unexpected case list")
    saved_rows = saved.get("cases") or []
    case_ids = source_manifest["dataset"]["case_ids"]
    require(len(case_ids) == 49 and len(set(case_ids)) == 49,
            "Expected the complete 49-case classic scope")
    require([row.get("case_id") for row in saved_rows] == case_ids,
            "Saved rows and source manifest have different case IDs or order")

    new_all = load_cases(current_cases_path, set(), False)
    if original_cases_path.is_file():
        old_all = load_cases(original_cases_path, set(), False)
        original_cases_source = original_cases_path.relative_to(BASE_DIR).as_posix()
        original_cases_sha256 = digest(original_cases_path)
    else:
        # The original run had no aliases. Reconstruct its Case definitions and
        # require their dataset digest to match the saved run before replaying SQL.
        old_all = [{key: value for key, value in case.items() if key != "column_aliases"}
                   for case in new_all]
        original_cases_source = "reconstructed_from_current_cases_without_column_aliases"
        original_cases_sha256 = None
    require(len(old_all) == len(new_all) == 430, "Expected 430 source cases")
    require([case["case_id"] for case in old_all] == [case["case_id"] for case in new_all],
            "Case order changed")
    changed = []
    for old, new in zip(old_all, new_all):
        require("column_aliases" not in old, f"Original case already had aliases: {old['case_id']}")
        without_aliases = {key: value for key, value in new.items() if key != "column_aliases"}
        require(without_aliases == old, f"Change beyond aliases in {old['case_id']}")
        if "column_aliases" in new:
            aliases = new["column_aliases"]
            require(new["classic"] and aliases and isinstance(aliases, dict),
                    f"Invalid alias case: {new['case_id']}")
            require(all(key in new["expected_columns"] and isinstance(values, list)
                        and len(values) == 1 and isinstance(values[0], str)
                        and values[0] != "*" for key, values in aliases.items()),
                    f"Invalid explicit aliases: {new['case_id']}")
            changed.append(new["case_id"])
    require(len(changed) == 42, f"Expected 42 alias cases, got {len(changed)}")

    old_classic = [case for case in old_all if case["classic"]]
    new_classic = [case for case in new_all if case["classic"]]
    require([case["case_id"] for case in old_classic] == case_ids, "Classic cases differ")
    manifest_args = dict(base_dir=BASE_DIR, mode="live", scope="classic",
                         config=source_manifest["config"])
    old_manifest = build_run_manifest(old_classic, case_source=(
        original_cases_path if original_cases_path.is_file() else current_cases_path),
                                      **manifest_args)
    new_manifest = build_run_manifest(new_classic, case_source=current_cases_path,
                                      **manifest_args)
    require(old_manifest["dataset"]["version"] == source_manifest["dataset"]["version"],
            "Original case source does not match the saved run")
    for name in ("data", "schema", "application", "evaluator", "evaluation_code"):
        require(new_manifest["versions"][name] == source_manifest["versions"][name],
                f"Source version mismatch: {name}")

    engine = DuckDbEngine()
    controller = AccessController()
    rescored_rows = []
    for old, new, saved_row in zip(old_classic, new_classic, saved_rows):
        case_id = old["case_id"]
        require(saved_row["query"] == old["query"], f"Question mismatch: {case_id}")
        require(saved_row["sql_execution_success"] is True,
                f"Original generated SQL failed: {case_id}")
        scope = controller.resolve(f"demo_{old['scenario']}")
        generated = replay(engine, saved_row["generated_sql"], scope, case_id, "generated")
        gold = replay(engine, old["gold_sql"], scope, case_id, "Gold")
        args = (generated.columns, generated.rows, gold.columns, gold.rows,
                bool(old.get("order_sensitive", True)))
        options = {"order_by_column": old.get("order_by_column")}
        loose, column_match, _ = compare_results(*args, **options)
        old_strict, _ = compare_results_strict(*args, **options)
        new_strict, reason = compare_results_strict(
            *args, **options, column_aliases=new.get("column_aliases"),
            allowed_auxiliary_columns=new.get("allowed_auxiliary_columns"),
        )
        require(loose == saved_row["result_correct"] and
                old_strict == saved_row["strict_result_correct"] and
                column_match == saved_row["column_match"],
                f"Original score could not be reproduced: {case_id}")
        require(len(generated.rows) == saved_row["result_metrics"]["generated_result_rows"]
                and len(gold.rows) == saved_row["result_metrics"]["gold_result_rows"],
                f"Original row counts could not be reproduced: {case_id}")
        row = deepcopy(saved_row)
        row["strict_result_correct"] = new_strict
        row["strict_comparison_reason"] = reason
        row["result_metrics"]["strict_correct"] = new_strict
        row["result_metrics"]["strict_reason"] = reason
        row["offline_rescore"] = {
            "old_strict_correct": old_strict,
            "new_strict_correct": new_strict,
            "expected_columns": gold.columns,
            "actual_columns": generated.columns,
            "generated_row_count": len(generated.rows),
            "gold_row_count": len(gold.rows),
            "generated_rows_sha256": rows_digest(generated.rows),
            "gold_rows_sha256": rows_digest(gold.rows),
            "column_aliases": new.get("column_aliases", {}),
        }
        rescored_rows.append(row)
        print(f"[{len(rescored_rows)}/49] {case_id}: {old_strict} -> {new_strict}", flush=True)

    summary = summarize(rescored_rows, "live")
    require(saved["summary"]["strict_result_accuracy"] ==
            round(sum(row["offline_rescore"]["old_strict_correct"] for row in rescored_rows) / 49, 6),
            "Original strict summary is inconsistent")
    for key, value in saved["summary"].items():
        if key not in ("strict_result_accuracy", "strict_scored_count"):
            require(summary[key] == value, f"Unrelated summary changed: {key}")
    return {
        "rescore_status": "complete",
        "summary": summary,
        "cases": rescored_rows,
        "source_run_manifest": source_manifest,
        "rescore_manifest": {
            "type": "offline_sql_replay_with_explicit_case_aliases",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_report": source.relative_to(BASE_DIR).as_posix(),
            "source_report_sha256": digest(source),
            "source_run_id": source_manifest["run_id"],
            "original_cases_source": original_cases_source,
            "original_cases_sha256": original_cases_sha256,
            "current_cases_sha256": digest(current_cases_path),
            "original_dataset_version": old_manifest["dataset"]["version"],
            "rescored_dataset_version": new_manifest["dataset"]["version"],
            "data_version": new_manifest["versions"]["data"],
            "evaluator_version": new_manifest["versions"]["evaluator"],
            "alias_case_ids": changed,
            "model_requests": 0,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--original-cases", type=Path, default=ORIGINAL_CASES)
    parser.add_argument("--current-cases", type=Path, default=CURRENT_CASES)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output not in {args.source.resolve(), args.original_cases.resolve(),
                           args.current_cases.resolve()}, "Output would overwrite an input")
    require(not output.exists(), f"Output already exists: {output}")
    payload = rescore(args.source.resolve(), args.original_cases.resolve(),
                      args.current_cases.resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(output)
    print(json.dumps({"output": str(output), "source_run_id":
                      payload["rescore_manifest"]["source_run_id"],
                      "original_strict": sum(row["offline_rescore"]["old_strict_correct"]
                                             for row in payload["cases"]),
                      "rescored_strict": sum(row["strict_result_correct"]
                                             for row in payload["cases"]),
                      "summary": payload["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
