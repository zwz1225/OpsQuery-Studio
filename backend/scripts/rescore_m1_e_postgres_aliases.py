"""Replay 14 reviewed M1 E SQLs on verified PostgreSQL without model requests.

This command only writes a new review report. It leaves the formal cases and
the three first-run server reports unchanged. Run it with DATA_BACKEND and
DATA_SOURCE_ID selecting the accepted PostgreSQL source.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from app.config import BASE_DIR, settings
from app.datasources import create_datasource_runtime
from app.security import AccessController
from evaluation.gold_result import resolve_gold_result
from evaluation.report_identity import validate_report_identity
from evaluation.run_benchmark import (
    compare_results, compare_results_strict, load_cases, summarize,
)
from evaluation.run_manifest import _digest, build_run_manifest


RESULTS = BASE_DIR / "evaluation/results"
CASE_PATH = BASE_DIR / "evaluation/cases/all_cases.jsonl"
REVIEW_PATH = RESULTS / "m1_e_postgres_server_review_local.json"
CLASSIC_PATH = RESULTS / "m1_e_postgres_live_classic_server.json"
PHASE_PATH = RESULTS / "m1_e_postgres_live_phase83_server.json"
EXPECTED_CASES_SHA256 = "e1cb760a8ffa4f89e45ca73403c439975c51d2be47cd36800ee4c7c0ee1925f1"


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def score(columns: list[str], rows: list[dict], gold: dict, case: dict) -> tuple[bool, str]:
    return compare_results_strict(
        columns, rows, gold["columns"], gold["rows"],
        bool(case.get("order_sensitive", True)),
        order_by_column=case.get("order_by_column"),
        column_aliases=case.get("column_aliases"),
        allowed_auxiliary_columns=case.get("allowed_auxiliary_columns"),
        top_n_tie_policy=case.get("top_n_tie_policy"),
    )


def replay(output: Path, *, review_path: Path = REVIEW_PATH,
           classic_path: Path = CLASSIC_PATH, phase_path: Path = PHASE_PATH,
           case_path: Path = CASE_PATH) -> dict:
    protected = {path.resolve() for path in (
        review_path, classic_path, phase_path, case_path,
    )}
    require(output.resolve() not in protected and not output.exists(),
            "Choose a fresh output path without overwriting source evidence")
    require(digest(case_path) == EXPECTED_CASES_SHA256,
            "Formal cases differ from the reviewed M1 E first-run dataset")
    review = json.loads(review_path.read_text(encoding="utf-8"))
    require(review.get("review_status") == "complete"
            and review.get("acceptance_status") == "needs_fixes", "Invalid M1 E review")
    source_reports = {}
    for path in (classic_path, phase_path):
        report = json.loads(path.read_text(encoding="utf-8"))
        manifest = validate_report_identity(report)
        expected = review["report_files"][path.name]
        require(digest(path) == expected["sha256"]
                and manifest["run_id"] == expected["run_id"]
                and report["run_status"] == "complete"
                and report["summary"] == summarize(report["cases"], "live"),
                "Original live report differs from reviewed evidence: " + path.name)
        source_reports[path.name] = report
    classic, phase = source_reports[classic_path.name], source_reports[phase_path.name]
    require(classic["run_manifest"]["scope"] == "classic"
            and phase["run_manifest"]["scope"] == "all"
            and classic["run_manifest"]["source_identity"] == phase["run_manifest"]["source_identity"],
            "Live reports have different scopes or sources")
    cases = load_cases(case_path, set(), False)
    by_id = {case["case_id"]: case for case in cases}
    require(len(cases) == len(by_id) == 430, "Formal case list changed")
    old_classic = [case for case in cases if case["classic"]]
    old_phase = [by_id[cid] for cid in phase["run_manifest"]["dataset"]["case_ids"]]
    require(_digest(old_classic) == classic["run_manifest"]["dataset"]["version"]
            and _digest(old_phase) == phase["run_manifest"]["dataset"]["version"],
            "Original dataset versions do not match server live reports")
    source_rows = {row["case_id"]: row for report in (classic, phase)
                   for row in report["cases"]}
    candidates = review["candidate_aliases"]
    require(len(candidates) == 14 and len({item["case_id"] for item in candidates}) == 14
            and sum(len(item["missing_explicit_aliases"]) for item in candidates) == 23,
            "Expected exactly 14 cases and 23 explicit alias additions")
    amended_cases = []
    for item in candidates:
        case_id = item["case_id"]
        require(case_id in by_id and case_id in source_rows,
                "Unknown candidate case " + case_id)
        row = source_rows[case_id]
        require(row["sql_execution_success"] is True
                and row["result_correct"] is True
                and row["strict_result_correct"] is False
                and row["generated_sql"], "Candidate status changed: " + case_id)
        amended = deepcopy(by_id[case_id])
        for pair in item["missing_explicit_aliases"]:
            expected, actual = pair["expected"], pair["actual"]
            require(expected in amended["expected_columns"] and actual and actual != "*",
                    "Invalid explicit alias for " + case_id)
            aliases = amended.setdefault("column_aliases", {}).setdefault(expected, [])
            require(actual not in aliases, "Alias already present for " + case_id)
            aliases.append(actual)
        amended_cases.append(amended)

    results = []
    with create_datasource_runtime(settings) as runtime:
        identity = runtime.identity.public()
        require(identity == classic["run_manifest"]["source_identity"]
                and identity == phase["run_manifest"]["source_identity"]
                and identity["backend"] == "postgresql",
                "Verified PostgreSQL runtime differs from first-run source")
        manifest = build_run_manifest(
            amended_cases, base_dir=BASE_DIR, mode="offline_rescore",
            scope="m1_e_alias14", case_source=case_path, runtime=runtime,
            config={"operation": "saved_sql_postgres_replay",
                    "source_run_ids": [classic["run_manifest"]["run_id"],
                                       phase["run_manifest"]["run_id"]],
                    "new_model_request_count": 0},
        )
        controller = AccessController()
        with tempfile.TemporaryDirectory(prefix="askdata_m1_e_gold_") as temporary:
            for index, (item, amended) in enumerate(zip(candidates, amended_cases), 1):
                replay_case(item, amended, index, by_id, source_rows, runtime,
                            identity, controller, Path(temporary), results)
    require(digest(case_path) == EXPECTED_CASES_SHA256
            and all(digest(path) == review["report_files"][path.name]["sha256"]
                    for path in (classic_path, phase_path)),
            "Source files changed during independent replay")
    report = {
        "stage": "M1 E PostgreSQL saved-SQL alias14 independent rescore",
        "run_status": "complete", "recorded_at": datetime.now(timezone.utc).isoformat(),
        "run_manifest": manifest, "source_report_sha256": {
            path.name: digest(path) for path in (classic_path, phase_path)
        },
        "review_report_sha256": digest(review_path),
        "source_cases_sha256": EXPECTED_CASES_SHA256,
        "formal_aliases_applied": False,
        "new_model_request_count": 0,
        "summary": {
            "case_count": 14, "original_replayed_strict_pass_count": 0,
            "amended_strict_pass_count": 14, "amended_strict_accuracy": 1.0,
            "loose_pass_count": 14, "alias_addition_count": 23,
        },
        "cases": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return report


def replay_case(item: dict, amended: dict, index: int, by_id: dict,
                source_rows: dict, runtime, identity: dict, controller,
                temporary: Path, results: list[dict]) -> None:
    """Keep per-case replay small enough to audit without mutating inputs."""
    case_id = item["case_id"]
    original, row = by_id[case_id], source_rows[case_id]
    scope = controller.resolve("demo_" + original["scenario"])
    actual = runtime.executor.execute(
        identity["logical_database_id"], row["generated_sql"],
        scope, row_limit=10000,
    )
    require(actual.success and not actual.truncated,
            "Saved SQL PostgreSQL replay failed: " + case_id + " " + str(actual.error))
    gold = resolve_gold_result(
        original, runtime.executor, scope, cache_dir=temporary,
        use_cached_gold=False, data_version=identity["data_version"],
    )
    require(gold["source"] == "execution", "Expected fresh Gold execution")
    expected_gold = {"columns": original["expected_columns"],
                     "rows": original["expected_rows"]}
    require(score(gold["columns"], gold["rows"], expected_gold, original)[0],
            "Fresh PostgreSQL Gold differs from frozen expected rows: " + case_id)
    original_score = score(actual.columns, actual.rows, gold, original)
    amended_score = score(actual.columns, actual.rows, gold, amended)
    loose_score = compare_results(
        actual.columns, actual.rows, gold["columns"], gold["rows"],
        bool(original.get("order_sensitive", True)),
        order_by_column=original.get("order_by_column"),
        top_n_tie_policy=original.get("top_n_tie_policy"),
    )
    require(original_score[0] is False and amended_score[0] is True
            and loose_score[0] is True,
            "PG replay did not confirm candidate alias: " + case_id)
    require(len(actual.rows) == row["result_metrics"]["generated_result_rows"]
            and len(gold["rows"]) == row["result_metrics"]["gold_result_rows"],
            "Result row count changed since first run: " + case_id)
    results.append({
        "case_id": case_id, "source_run_id": row["run_id"],
        "source_strict_result_correct": row["strict_result_correct"],
        "original_replayed_strict_result_correct": original_score[0],
        "original_strict_reason": original_score[1],
        "amended_strict_result_correct": amended_score[0],
        "amended_strict_reason": amended_score[1],
        "loose_result_correct": loose_score[0],
        "actual_columns": actual.columns, "actual_rows": actual.rows,
        "gold_columns": gold["columns"], "gold_rows": gold["rows"],
        "generated_sql": row["generated_sql"],
        "selected_postgres_gold_sql": gold["gold_sql"],
        "alias_additions": item["missing_explicit_aliases"],
        "order_sensitive": original.get("order_sensitive", True),
    })
    print(f"[{index}/14] {case_id}: original={original_score[0]} "
          f"amended={amended_score[0]}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=RESULTS / "m1_e_postgres_alias_rescore_server.json")
    parser.add_argument("--review", type=Path, default=REVIEW_PATH)
    parser.add_argument("--source-classic", type=Path, default=CLASSIC_PATH)
    parser.add_argument("--source-phase", type=Path, default=PHASE_PATH)
    args = parser.parse_args()
    report = replay(args.output.resolve(), review_path=args.review.resolve(),
                    classic_path=args.source_classic.resolve(),
                    phase_path=args.source_phase.resolve())
    print(json.dumps({"output": str(args.output), "summary": report["summary"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
