"""Review saved M1 A SQL offline; leaves source report and case definitions untouched.

Run from backend: python -m scripts.audit_m1_a_classic
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from app.config import BASE_DIR
from app.datasources import create_datasource_runtime
from app.security import AccessController
from evaluation.gold_result import resolve_gold_result
from evaluation.run_benchmark import load_cases, compare_results, compare_results_strict, summarize
from evaluation.run_manifest import build_run_manifest, data_digest, _digest

ALIASES = {
    "CHANNEL_OPS-069": {"avg_value": ["avg_conversion_value"]},
    "CHANNEL_OPS-101": {"creatives": ["creative_count"]},
    "CONTENT_OPS-029": {"category_name": ["content_category"]},
    "CONTENT_OPS-035": {"category_name": ["内容分类"], "interactions": ["互动数"]},
    "CONTENT_OPS-036": {"interaction_date": ["interacted_date"]},
    "CONTENT_OPS-051": {"category_name": ["content_category"], "contents": ["content_count"],
                        "avg_duration_seconds": ["avg_video_duration"]},
    "CONTENT_OPS-136": {"category_name": ["内容分类"], "reports": ["举报数量"]},
    "CONTENT_OPS-137": {"category_name": ["内容分类"], "reports": ["举报数量"]},
}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def strict(actual, gold, case):
    return compare_results_strict(actual.columns, actual.rows, gold["columns"], gold["rows"],
        case.get("order_sensitive", False), order_by_column=case.get("order_by_column"),
        column_aliases=case.get("column_aliases"),
        allowed_auxiliary_columns=case.get("allowed_auxiliary_columns"),
        top_n_tie_policy=case.get("top_n_tie_policy"))

def audit(source: Path):
    source_bytes = source.read_bytes()
    saved = json.loads(source_bytes)
    manifest = saved["run_manifest"]
    require(saved.get("run_status") == "complete", "Incomplete source run")
    require(manifest["mode"] == "live" and manifest["scope"] == "classic", "Expected live classic")
    require(manifest["dataset"]["case_list"] is None, "Unexpected source case list")
    case_path = BASE_DIR / "evaluation/cases/all_cases.jsonl"
    cases_bytes = case_path.read_bytes()
    cases = load_cases(case_path, set(), True)
    ids = [c["case_id"] for c in cases]
    require(len(ids) == len(set(ids)) == 49, "Expected 49 unique classic cases")
    require(ids == manifest["dataset"]["case_ids"] == [c["case_id"] for c in saved["cases"]],
            "Case IDs/order mismatch")
    require(_digest(cases) == manifest["dataset"]["version"], "Source dataset version mismatch")
    require(summarize(saved["cases"], "live") == saved["summary"], "Source summary mismatch")
    failed = {c["case_id"] for c in saved["cases"] if c["strict_result_correct"] is False}
    require(failed == set(ALIASES), "Unexpected strict failures")
    proposed = deepcopy(cases)
    for case in proposed:
        for canonical, added in ALIASES.get(case["case_id"], {}).items():
            require(canonical in case["expected_columns"], "Unknown canonical column")
            existing = case.setdefault("column_aliases", {}).setdefault(canonical, [])
            for alias in added:
                require(alias != "*" and alias not in existing, "Invalid/duplicate alias addition")
                existing.append(alias)
    evidence = []
    with create_datasource_runtime() as runtime:
        identity = runtime.identity.public()
        require(identity == manifest["source_identity"], "Source identity mismatch")
        local = build_run_manifest(cases, base_dir=BASE_DIR, mode="live", scope="classic",
            config=manifest["config"], case_source=case_path, source_identity=identity)
        require(local["versions"] == manifest["versions"], "Application/evaluator/data version mismatch")
        access = AccessController()
        for index, (case, revised, row) in enumerate(zip(cases, proposed, saved["cases"]), 1):
            scope = access.resolve("demo_" + case["scenario"])
            require(scope.user_id == row["trace"]["permission"]["user_id"] and
                    list(scope.roles) == row["trace"]["permission"]["roles"], "Role mismatch")
            actual = runtime.executor.execute("short_video_ops", row["generated_sql"], scope, row_limit=10000)
            require(actual.success and not actual.truncated, "Replay failed: " + str(actual.error))
            gold = resolve_gold_result(case, runtime.executor, scope, data_version=identity["data_version"])
            old_ok, old_reason = strict(actual, gold, case)
            new_ok, new_reason = strict(actual, gold, revised)
            loose_ok, column_match, loose_reason = compare_results(actual.columns, actual.rows, gold["columns"],
                gold["rows"], case.get("order_sensitive", False),
                order_by_column=case.get("order_by_column"), top_n_tie_policy=case.get("top_n_tie_policy"))
            require(old_ok == row["strict_result_correct"], "Original strict replay differs: " + case["case_id"])
            require(loose_ok == row["result_correct"], "Original loose replay differs: " + case["case_id"])
            require(len(actual.rows) == row["result_metrics"]["generated_result_rows"] and
                    len(gold["rows"]) == row["result_metrics"]["gold_result_rows"], "Row count differs")
            evidence.append({"case_id": case["case_id"], "source_strict_correct": row["strict_result_correct"],
                "replayed_original_strict_correct": old_ok, "original_reason": old_reason,
                "candidate_strict_correct": new_ok, "candidate_reason": new_reason,
                "loose_correct": loose_ok, "loose_reason": loose_reason,
                "source_sql": row["generated_sql"], "gold_sql": case["gold_sql"],
                "actual_columns": actual.columns, "actual_rows": actual.rows,
                "gold_columns": gold["columns"], "gold_rows": gold["rows"],
                "gold_result_source": gold["source"], "order_sensitive": case.get("order_sensitive", False),
                "original_aliases": case.get("column_aliases", {}),
                "candidate_aliases": revised.get("column_aliases", {}),
                "alias_additions": ALIASES.get(case["case_id"], {})})
            print(f"[{index}/49] {case['case_id']} original={old_ok} candidate={new_ok}", flush=True)
        with runtime.executor.connect("short_video_ops") as conn:
            counts = conn.execute("SELECT COUNT(*) AS total_rows, COUNT(interaction_id) AS nonnull_ids, "
                "COUNT(*) FILTER (WHERE valid_interaction IS NULL OR valid_interaction NOT IN (0, 1)) "
                "AS invalid_flag_rows FROM video_interactions").fetchone()
            timestamp_type = conn.execute("SELECT typeof(interacted_at) FROM video_interactions LIMIT 1").fetchone()[0]
        require(data_digest(BASE_DIR) == identity["data_version"], "Data changed during replay")
    require(source.read_bytes() == source_bytes and case_path.read_bytes() == cases_bytes,
            "Source/case file changed during audit")
    require(all(c["candidate_strict_correct"] for c in evidence), "Candidate review still has failures")
    return {
        "run_status": "complete", "mode": "offline_sql_replay_alias_review",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_report": source.name, "source_report_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_run_id": manifest["run_id"], "source_manifest": manifest,
        "source_summary": saved["summary"], "source_identity": identity,
        "candidate_aliases_applied_to_case_file": False,
        "alias_additions": ALIASES, "candidate_dataset_version": _digest(proposed),
        "summary": {"case_count": 49, "replayed_original_strict_pass_count": sum(c["replayed_original_strict_correct"] for c in evidence),
            "candidate_strict_pass_count": sum(c["candidate_strict_correct"] for c in evidence),
            "candidate_strict_result_accuracy": 1.0, "loose_pass_count": sum(c["loose_correct"] for c in evidence),
            "changed_case_count": len(ALIASES), "alias_addition_count": sum(len(a) for columns in ALIASES.values() for a in columns.values()),
            "new_model_request_count": 0},
        "count_star_equivalence_check": {"table": "video_interactions", "total_rows": counts[0],
            "nonnull_interaction_ids": counts[1], "invalid_flag_rows": counts[2], "interacted_at_type": timestamp_type},
        "limitations": ["Local final-SQL replay using matching data/code versions; not a new server live run.",
            "Source report has no result rows; row values cannot be compared to original server rows directly.",
            "Proposed aliases are stored here only; source report and case definitions are unchanged.",
            "No prompt, comparator, precision, ordering, permission, or model changes."],
        "cases": evidence,
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=BASE_DIR / "evaluation/results/m1_a_live_classic_server.json")
    parser.add_argument("--output", type=Path, default=BASE_DIR / "evaluation/results/m1_a_classic_alias_review_local.json")
    args = parser.parse_args()
    require(args.source.resolve() != args.output.resolve(), "Output cannot overwrite source")
    payload = audit(args.source.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=True, indent=2))

if __name__ == "__main__":
    main()
