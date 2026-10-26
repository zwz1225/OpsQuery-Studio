"""Offline rescore of both saved M0 phase83 live runs with reviewed Case aliases."""

from __future__ import annotations

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


ROOT = BASE_DIR / "evaluation"
RESULTS = ROOT / "results"
SOURCE = ROOT / "cases" / "all_cases.jsonl"
BACKUP = RESULTS / "m0_all_cases_before_phase83_aliases_20260929.jsonl"
COHORT = ROOT / "cases" / "phase83_validation.json"
INPUTS = {
    "off": RESULTS / "m0_phase83_live_off_server.json",
    "on": RESULTS / "m0_phase83_live_on_server.json",
}
OUTPUTS = {
    "off": RESULTS / "m0_phase83_live_off_alias_rescore.json",
    "on": RESULTS / "m0_phase83_live_on_alias_rescore.json",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replay(engine: DuckDbEngine, sql: str, scope: object, case_id: str, kind: str):
    result = engine.execute("short_video_ops", sql, scope, row_limit=10000)
    require(result.success and not result.truncated,
            f"{case_id} {kind} SQL replay failed: {result.error}")
    return result


def main() -> None:
    require(BACKUP.is_file(), f"Missing pre-alias Case backup: {BACKUP}")
    require(all(not path.exists() for path in OUTPUTS.values()),
            "An offline rescore output already exists; original results will not be overwritten")
    ids = json.loads(COHORT.read_text(encoding="utf-8"))["case_ids"]
    old_all = load_cases(BACKUP, set(), False)
    new_all = load_cases(SOURCE, set(), False)
    require(len(old_all) == len(new_all) == 430, "Expected 430 source cases")
    require([c["case_id"] for c in old_all] == [c["case_id"] for c in new_all],
            "Case order changed")
    changed = []
    for old, new in zip(old_all, new_all):
        if old == new:
            continue
        require("column_aliases" not in old and
                {k: v for k, v in new.items() if k != "column_aliases"} == old,
                f"Change beyond new aliases in {old['case_id']}")
        require(old["case_id"] in ids and "allowed_auxiliary_columns" not in new,
                f"Unexpected Case annotation in {old['case_id']}")
        changed.append(old["case_id"])
    require(len(changed) == 27, f"Expected 27 annotated cases, got {len(changed)}")
    old_cases = {c["case_id"]: c for c in old_all}
    new_cases = {c["case_id"]: c for c in new_all}
    require(len(ids) == len(set(ids)) == 30 and all(not old_cases[i]["classic"] for i in ids),
            "Invalid 30-case cohort")

    saved = {label: json.loads(path.read_text(encoding="utf-8"))
             for label, path in INPUTS.items()}
    manifests = {label: report["run_manifest"] for label, report in saved.items()}
    for label, report in saved.items():
        manifest = manifests[label]
        require(report.get("run_status") == "complete" and manifest["mode"] == "live"
                and manifest["scope"] == "all" and
                [c["case_id"] for c in report["cases"]] == ids == manifest["dataset"]["case_ids"],
                f"Incomplete or different {label} report")
        old_manifest = build_run_manifest(
            [old_cases[i] for i in ids], base_dir=BASE_DIR, mode="live", scope="all",
            config=manifest["config"], case_source=BACKUP, case_list=COHORT,
        )
        new_manifest = build_run_manifest(
            [new_cases[i] for i in ids], base_dir=BASE_DIR, mode="live", scope="all",
            config=manifest["config"], case_source=SOURCE, case_list=COHORT,
        )
        require(old_manifest["dataset"]["version"] == manifest["dataset"]["version"],
                f"Original {label} dataset version differs")
        require(new_manifest["versions"] == manifest["versions"],
                f"Current source versions differ from {label} run")
        manifests[label] = {"source": manifest, "current": new_manifest}
    require(manifests["off"]["source"]["versions"] ==
            manifests["on"]["source"]["versions"], "Source versions differ")

    engine = DuckDbEngine()
    controller = AccessController()
    rows: dict[str, list[dict]] = {"off": [], "on": []}
    for index, case_id in enumerate(ids, 1):
        old = old_cases[case_id]
        new = new_cases[case_id]
        scope = controller.resolve(f"demo_{old['scenario']}")
        gold = replay(engine, old["gold_sql"], scope, case_id, "Gold")
        for label, report in saved.items():
            prior = report["cases"][index - 1]
            require(prior["query"] == old["query"] and
                    prior["sql_execution_success"] is True,
                    f"Saved question or SQL state changed: {case_id} {label}")
            actual = replay(engine, prior["generated_sql"], scope, case_id, label)
            args = (actual.columns, actual.rows, gold.columns, gold.rows,
                    bool(old.get("order_sensitive", True)))
            options = {"order_by_column": old.get("order_by_column")}
            loose, column_match, _ = compare_results(*args, **options)
            old_strict, _ = compare_results_strict(
                *args, **options, column_aliases=old.get("column_aliases"),
                allowed_auxiliary_columns=old.get("allowed_auxiliary_columns"),
            )
            new_strict, reason = compare_results_strict(
                *args, **options, column_aliases=new.get("column_aliases"),
                allowed_auxiliary_columns=new.get("allowed_auxiliary_columns"),
            )
            require(loose == prior["result_correct"] and
                    column_match == prior["column_match"] and
                    old_strict == prior["strict_result_correct"],
                    f"Original score did not replay: {case_id} {label}")
            row = deepcopy(prior)
            row["strict_result_correct"] = new_strict
            row["strict_comparison_reason"] = reason
            row["result_metrics"]["strict_correct"] = new_strict
            row["result_metrics"]["strict_reason"] = reason
            row["offline_rescore"] = {
                "old_strict_correct": old_strict,
                "new_strict_correct": new_strict,
                "expected_columns": gold.columns,
                "actual_columns": actual.columns,
                "column_aliases": new.get("column_aliases", {}),
                "extra_columns_allowed": new.get("allowed_auxiliary_columns", []),
                "generated_row_count": len(actual.rows),
                "gold_row_count": len(gold.rows),
            }
            rows[label].append(row)
        print(f"[{index}/30] {case_id}", flush=True)

    for label, path in OUTPUTS.items():
        report = saved[label]
        summary = summarize(rows[label], "live")
        for key, value in report["summary"].items():
            if key not in ("strict_result_accuracy", "strict_scored_count"):
                require(summary[key] == value, f"Unrelated summary changed: {label} {key}")
        payload = {
            "rescore_status": "complete",
            "summary": summary,
            "cases": rows[label],
            "source_run_manifest": manifests[label]["source"],
            "rescore_manifest": {
                "type": "offline_sql_replay_with_explicit_case_aliases",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source_report": INPUTS[label].relative_to(BASE_DIR).as_posix(),
                "source_report_sha256": sha(INPUTS[label]),
                "source_run_id": manifests[label]["source"]["run_id"],
                "original_cases_sha256": sha(BACKUP),
                "current_cases_sha256": sha(SOURCE),
                "original_dataset_version": manifests[label]["source"]["dataset"]["version"],
                "rescored_dataset_version": manifests[label]["current"]["dataset"]["version"],
                "alias_case_ids": changed,
                "model_requests": 0,
            },
        }
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
        print(f"{label}: original_strict={sum(c['offline_rescore']['old_strict_correct'] for c in rows[label])}/30"
              f" rescored_strict={sum(c['strict_result_correct'] for c in rows[label])}/30"
              f" output={path}")


if __name__ == "__main__":
    main()
