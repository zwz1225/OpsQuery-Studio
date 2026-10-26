"""Apply the reviewed M1 A case aliases and save an independent offline rescore.

From backend: python -m scripts.rescore_m1_a_classic --apply-aliases
Subsequent runs omit --apply-aliases; the original report is never rewritten.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from app.config import BASE_DIR
from app.datasources import create_datasource_runtime
from app.security import AccessController
from evaluation.gold_result import resolve_gold_result
from evaluation.run_benchmark import compare_results, summarize
from evaluation.run_manifest import build_run_manifest, data_digest, _digest
from scripts.audit_m1_a_classic import ALIASES, require, strict


RESULTS = BASE_DIR / "evaluation/results"
CASE_PATH = BASE_DIR / "evaluation/cases/all_cases.jsonl"
BACKUP = RESULTS / "m1_all_cases_before_classic_aliases_20261007.jsonl"
SOURCE = RESULTS / "m1_a_live_classic_server.json"
REVIEW = RESULTS / "m1_a_classic_alias_review_local.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_cases(data: bytes) -> list[dict]:
    return [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run(source: Path, output: Path, apply_aliases: bool) -> dict:
    protected = {CASE_PATH.resolve(), BACKUP.resolve(), SOURCE.resolve(), REVIEW.resolve(), source.resolve()}
    require(output.resolve() not in protected, "Output would overwrite an input or original backup")
    require(not output.exists(), "Output already exists; choose a new --output filename")
    source_bytes = source.read_bytes()
    saved = json.loads(source_bytes)
    review_bytes = REVIEW.read_bytes()
    review = json.loads(review_bytes)
    manifest = saved["run_manifest"]
    require(saved.get("run_status") == "complete", "Source run is incomplete")
    require(manifest["mode"] == "live" and manifest["scope"] == "classic", "Expected live classic source")
    require(sha(source_bytes) == review["source_report_sha256"], "Source differs from reviewed report")
    require(review["run_status"] == "complete" and review["alias_additions"] == ALIASES,
            "Reviewed alias additions differ")
    require(review["summary"]["candidate_strict_pass_count"] == 49, "Review did not pass all cases")
    current_bytes = CASE_PATH.read_bytes()
    original_bytes = BACKUP.read_bytes() if BACKUP.exists() else current_bytes
    original = read_cases(original_bytes)
    require(len(original) == 430 and len({c["case_id"] for c in original}) == 430,
            "Expected 430 unique source cases")
    old_classic = [c for c in original if c["classic"]]
    require(_digest(old_classic) == manifest["dataset"]["version"], "Pre-alias backup differs from source dataset")
    expected = deepcopy(original)
    changed = []
    additions_count = 0
    for before, after in zip(original, expected):
        for column, additions in ALIASES.get(after["case_id"], {}).items():
            require(after["classic"] and column in after["expected_columns"], "Unknown canonical column")
            existing = after.setdefault("column_aliases", {}).setdefault(column, [])
            for alias in additions:
                require(isinstance(alias, str) and alias != "*" and alias not in existing,
                        "Alias is not a new explicit name")
                existing.append(alias)
                additions_count += 1
        if before != after:
            require({k: v for k, v in before.items() if k != "column_aliases"} ==
                    {k: v for k, v in after.items() if k != "column_aliases"}, "Non-alias case mutation")
            changed.append(after["case_id"])
    require(set(changed) == set(ALIASES) and len(changed) == 8 and additions_count == 13,
            "Expected exactly 8 cases and 13 alias additions")
    new_classic = [c for c in expected if c["classic"]]
    require(_digest(new_classic) == review["candidate_dataset_version"], "New dataset differs from reviewed candidate")
    current = read_cases(current_bytes)
    require(current == original or current == expected, "Current cases contain unreviewed changes")
    require(apply_aliases or current == expected, "Run with --apply-aliases to update the formal cases first")
    ids = [c["case_id"] for c in old_classic]
    require(len(ids) == len(set(ids)) == 49 and ids == manifest["dataset"]["case_ids"] ==
            [c["case_id"] for c in saved["cases"]], "Classic IDs/order differ")
    require(summarize(saved["cases"], "live") == saved["summary"], "Original summary differs")
    results = []
    with create_datasource_runtime() as runtime:
        identity = runtime.identity.public()
        require(identity == manifest["source_identity"], "Datasource identity differs")
        local_old = build_run_manifest(old_classic, base_dir=BASE_DIR, mode="live", scope="classic",
            config=manifest["config"], case_source=CASE_PATH, source_identity=identity)
        require(local_old["versions"] == manifest["versions"], "Application/evaluator/data versions differ")
        # Back up exact bytes before publishing the reviewed additions. Unchanged
        # lines and newline style are retained; only eight JSONL lines are edited.
        if not BACKUP.exists():
            with BACKUP.open("xb") as stream:
                stream.write(original_bytes)
        require(BACKUP.read_bytes() == original_bytes, "Original backup changed")
        if current != expected:
            require(CASE_PATH.read_bytes() == current_bytes, "Cases changed before write")
            by_id = {c["case_id"]: c for c in expected}
            lines = []
            for line in current_bytes.decode("utf-8").splitlines(keepends=True):
                if line.strip() and json.loads(line)["case_id"] in ALIASES:
                    case_id = json.loads(line)["case_id"]
                    ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
                    lines.append(json.dumps(by_id[case_id], ensure_ascii=False) + ending)
                else:
                    lines.append(line)
            atomic_write(CASE_PATH, "".join(lines).encode("utf-8"))
        formal_bytes = CASE_PATH.read_bytes()
        require(read_cases(formal_bytes) == expected, "Published formal cases differ from reviewed candidate")
        formal_manifest = build_run_manifest(new_classic, base_dir=BASE_DIR,
            mode="offline_rescore", scope="classic", config={"new_model_request_count": 0,
                "operation": "saved_sql_replay", "source_run_id": manifest["run_id"]},
            case_source=CASE_PATH, source_identity=identity)
        require(formal_manifest["versions"] == manifest["versions"], "Scoring code changed")
        access = AccessController()
        for index, (old, new, row) in enumerate(zip(old_classic, new_classic, saved["cases"]), 1):
            scope = access.resolve("demo_" + new["scenario"])
            require(scope.user_id == row["trace"]["permission"]["user_id"] and
                    list(scope.roles) == row["trace"]["permission"]["roles"], "Role mismatch")
            actual = runtime.executor.execute("short_video_ops", row["generated_sql"], scope, row_limit=10000)
            require(actual.success and not actual.truncated, "SQL replay failed: " + str(actual.error))
            gold = resolve_gold_result(new, runtime.executor, scope, data_version=identity["data_version"])
            old_ok, old_reason = strict(actual, gold, old)
            new_ok, new_reason = strict(actual, gold, new)
            loose, column_match, loose_reason = compare_results(actual.columns, actual.rows,
                gold["columns"], gold["rows"], new.get("order_sensitive", False),
                order_by_column=new.get("order_by_column"), top_n_tie_policy=new.get("top_n_tie_policy"))
            require(old_ok == row["strict_result_correct"] and loose == row["result_correct"],
                    "Original scoring did not reproduce: " + new["case_id"])
            require(new_ok and loose, "Formal case rescore failed: " + new["case_id"])
            require(len(actual.rows) == row["result_metrics"]["generated_result_rows"] and
                    len(gold["rows"]) == row["result_metrics"]["gold_result_rows"], "Row count changed")
            results.append({"case_id": new["case_id"], "source_strict_result_correct": row["strict_result_correct"],
                "original_replayed_strict_result_correct": old_ok, "original_strict_reason": old_reason,
                "strict_result_correct": new_ok, "strict_comparison_reason": new_reason,
                "result_correct": loose, "comparison_reason": loose_reason, "column_match": column_match,
                "generated_sql": row["generated_sql"], "gold_sql": new["gold_sql"],
                "actual_columns": actual.columns, "actual_rows": actual.rows,
                "gold_columns": gold["columns"], "gold_rows": gold["rows"],
                "gold_result_source": gold["source"], "column_aliases": new.get("column_aliases", {}),
                "alias_additions": ALIASES.get(new["case_id"], {}),
                "order_sensitive": new.get("order_sensitive", False),
                "replay_execution_ms": actual.execution_ms})
            print(f"[{index}/49] {new['case_id']}: {old_ok} -> {new_ok}", flush=True)
        require(data_digest(BASE_DIR) == identity["data_version"], "Data changed during replay")
    require(source.read_bytes() == source_bytes and REVIEW.read_bytes() == review_bytes,
            "Original report/review changed")
    require(CASE_PATH.read_bytes() == formal_bytes and BACKUP.read_bytes() == original_bytes,
            "Case definitions changed during replay")
    payload = {"run_status": "complete", "run_manifest": formal_manifest,
        "mode": "offline_rescore", "source_run_id": manifest["run_id"],
        "source_report": source.name, "source_report_sha256": sha(source_bytes),
        "source_manifest": manifest, "source_summary": saved["summary"],
        "review_report_sha256": sha(review_bytes), "formal_aliases_applied": True,
        "original_case_backup": BACKUP.relative_to(BASE_DIR).as_posix(),
        "original_cases_sha256": sha(original_bytes), "formal_cases_sha256": sha(formal_bytes),
        "original_dataset_version": _digest(old_classic), "formal_dataset_version": _digest(new_classic),
        "changed_case_ids": changed, "alias_additions": ALIASES,
        "summary": {"mode": "offline_rescore", "case_count": len(results),
            "original_strict_pass_count": sum(c["source_strict_result_correct"] for c in results),
            "original_replayed_strict_pass_count": sum(c["original_replayed_strict_result_correct"] for c in results),
            "strict_pass_count": sum(c["strict_result_correct"] for c in results),
            "strict_result_accuracy": 1.0, "result_accuracy": 1.0,
            "result_scored_count": 49, "strict_scored_count": 49, "unscored_count": 0,
            "raw_column_name_match_count": sum(c["column_match"] for c in results),
            "changed_case_count": 8, "alias_addition_count": 13, "new_model_request_count": 0},
        "limits": ["Saved final SQL replay on matching local data; not a new server live run.",
            "Original server result rows are absent; local rows cannot be directly compared to them.",
            "Only per-case aliases changed; SQL, questions, ordering, precision and comparator are unchanged."],
        "cases": results}
    atomic_write(output, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=RESULTS / "m1_a_live_classic_alias_rescore_local.json")
    parser.add_argument("--apply-aliases", action="store_true")
    args = parser.parse_args()
    payload = run(args.source.resolve(), args.output.resolve(), args.apply_aliases)
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
