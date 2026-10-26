"""Read-only SQL replay for M0 30-case column-contract review."""

from __future__ import annotations

from itertools import permutations
import hashlib
import json
from pathlib import Path

from app.config import BASE_DIR
from app.querying.duckdb_engine import DuckDbEngine
from app.security import AccessController
from evaluation.run_benchmark import compare_results, compare_results_strict, load_cases


ROOT = BASE_DIR / "evaluation"
RESULTS = ROOT / "results"
OFF = RESULTS / "m0_phase83_live_off_server.json"
ON = RESULTS / "m0_phase83_live_on_server.json"
OUTPUT = RESULTS / "m0_phase83_column_candidates.json"


def read_report(path: Path) -> dict:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("run_status") != "complete" or len(report.get("cases", [])) != 30:
        raise ValueError(f"Incomplete report: {path}")
    return report


def replay(engine: DuckDbEngine, sql: str, scope: object, case_id: str, label: str):
    result = engine.execute("short_video_ops", sql, scope, row_limit=10000)
    if not result.success or result.truncated:
        raise ValueError(f"{case_id} {label} SQL replay failed: {result.error}")
    return result


def mappings(actual: object, gold: object, case: dict) -> list[dict]:
    candidates = []
    for selected in permutations(actual.columns, len(gold.columns)):
        aliases = {
            expected: [observed]
            for expected, observed in zip(gold.columns, selected)
            if expected != observed
        }
        extras = [name for name in actual.columns if name not in selected]
        valid, _ = compare_results_strict(
            actual.columns, actual.rows, gold.columns, gold.rows,
            bool(case.get("order_sensitive", True)),
            order_by_column=case.get("order_by_column"),
            column_aliases=aliases,
            allowed_auxiliary_columns=extras,
        )
        if valid:
            candidate = {"column_aliases": aliases, "extra_columns": extras}
            if candidate not in candidates:
                candidates.append(candidate)
    return candidates


def main() -> None:
    off = read_report(OFF)
    on = read_report(ON)
    a = off["run_manifest"]
    b = on["run_manifest"]
    if a["dataset"] != b["dataset"] or a["versions"] != b["versions"]:
        raise ValueError("Off/on reports do not share dataset and source versions")
    ids = a["dataset"]["case_ids"]
    if [c["case_id"] for c in off["cases"]] != ids or [c["case_id"] for c in on["cases"]] != ids:
        raise ValueError("Report case order differs from manifest")
    source = ROOT / "cases" / "all_cases.jsonl"
    cases = {c["case_id"]: c for c in load_cases(source, set(), False)}
    engine = DuckDbEngine()
    controller = AccessController()
    records = []
    for index, case_id in enumerate(ids, 1):
        case = cases[case_id]
        scope = controller.resolve(f"demo_{case['scenario']}")
        gold = replay(engine, case["gold_sql"], scope, case_id, "Gold")
        record = {
            "case_id": case_id,
            "query": case["query"],
            "gold_sql": case["gold_sql"],
            "expected_columns": gold.columns,
            "runs": {},
        }
        for label, report in (("off", off), ("on", on)):
            saved = report["cases"][index - 1]
            actual = replay(engine, saved["generated_sql"], scope, case_id, label)
            correct, column_match, _ = compare_results(
                actual.columns, actual.rows, gold.columns, gold.rows,
                bool(case.get("order_sensitive", True)),
                order_by_column=case.get("order_by_column"),
            )
            if correct != saved["result_correct"] or column_match != saved["column_match"]:
                raise ValueError(f"{case_id} {label} original score did not replay")
            record["runs"][label] = {
                "result_correct": correct,
                "strict_result_correct": saved["strict_result_correct"],
                "generated_sql": saved["generated_sql"],
                "actual_columns": actual.columns,
                "expected_columns": gold.columns,
                "actual_row_count": len(actual.rows),
                "candidate_mappings": mappings(actual, gold, case) if correct else [],
            }
        records.append(record)
        print(f"[{index}/30] {case_id}", flush=True)
    payload = {
        "sources": {
            "off_run_id": a["run_id"],
            "on_run_id": b["run_id"],
            "off_sha256": hashlib.sha256(OFF.read_bytes()).hexdigest(),
            "on_sha256": hashlib.sha256(ON.read_bytes()).hexdigest(),
            "dataset_version": a["dataset"]["version"],
            "data_version": a["versions"]["data"],
        },
        "cases": records,
    }
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"audit: {OUTPUT}")


if __name__ == "__main__":
    main()
