"""Local DuckDB diagnostics only; this cannot prove PostgreSQL execution.

Run the unchanged originals and a DuckDB rendering of each stored PG variant
on the CSV snapshot. Use DECIMAL(38,15) for the diagnostic numeric casts,
because DuckDB's unparameterized DECIMAL defaults to (18,3). PostgreSQL's
unparameterized NUMERIC is not subject to that default. The stored PG SQL is
never edited and these diagnostic statements are never selected as PG Gold.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import sqlglot
from sqlglot import exp

from app.config import BASE_DIR
from app.querying.duckdb_engine import DuckDbEngine
from evaluation.run_benchmark import compare_results_strict
from scripts.audit_m1_d3_gold79 import (
    BASELINE_PATH, CASE_PATH, LIST_PATH, POSTGRES_SOURCE, audit, first79_cases_path, load_rows, require, sha256,
)
from evaluation.gold_sql import select_gold_sql


def diagnostic_sql(postgres_sql: str) -> str:
    tree = sqlglot.parse_one(postgres_sql, read="postgres")
    for cast in tree.find_all(exp.Cast):
        target = cast.args["to"]
        if target.this == exp.DataType.Type.DECIMAL and not target.expressions:
            cast.set("to", exp.DataType.build("DECIMAL(38,15)", dialect="duckdb"))
    return tree.sql(dialect="duckdb")


def compare(columns, rows, case):
    return compare_results_strict(columns, rows, case["expected_columns"], case["expected_rows"],
        case.get("order_sensitive", False), order_by_column=case.get("order_by_column"),
        column_aliases=case.get("column_aliases"), allowed_auxiliary_columns=case.get("allowed_auxiliary_columns"),
        top_n_tie_policy=case.get("top_n_tie_policy"))


def check() -> dict:
    provenance = audit()
    ids = json.loads(LIST_PATH.read_text(encoding="utf-8"))["case_ids"]
    originals = {c["case_id"]: c for c in load_rows(BASELINE_PATH)}
    current = {c["case_id"]: c for c in load_rows(first79_cases_path())}
    engine = DuckDbEngine()
    results = []
    started = time.perf_counter()
    try:
        with engine.connect("short_video_ops") as connection:
            def execute(sql):
                cursor = connection.execute(engine._validate_sql("short_video_ops", sql, None))
                raw_rows = cursor.fetchmany(10001)
                require(len(raw_rows) <= 10000, "Unexpected truncation in Gold diagnostic")
                columns = [d[0] for d in cursor.description]
                return columns, [{c: engine._json_value(v) for c, v in zip(columns, row)} for row in raw_rows]

            # Edge cases deliberately include non-binary numeric truthiness and NULL.
            prefix = "WITH flags AS (SELECT flag FROM (VALUES (0), (1), (-1), (2), (NULL)) AS t(flag)) "
            _, before = execute(prefix + "SELECT flag, CASE WHEN flag THEN 1 ELSE 0 END AS value FROM flags ORDER BY flag")
            _, after = execute(prefix + "SELECT flag, CASE WHEN flag <> 0 THEN 1 ELSE 0 END AS value FROM flags ORDER BY flag")
            require(before == after, "Nonzero/NULL truth semantics changed")
            for index, case_id in enumerate(ids, 1):
                original = originals[case_id]
                pg_sql = select_gold_sql(current[case_id], POSTGRES_SOURCE).sql
                duck_sql = diagnostic_sql(pg_sql)
                original_columns, original_rows = execute(original["gold_sql"])
                variant_columns, variant_rows = execute(duck_sql)
                original_ok, original_reason = compare(original_columns, original_rows, original)
                variant_ok, variant_reason = compare(variant_columns, variant_rows, original)
                pair_case = {**original, "expected_columns": original_columns, "expected_rows": original_rows}
                pair_ok, pair_reason = compare(variant_columns, variant_rows, pair_case)
                result = {"case_id": case_id, "original_strict_correct": original_ok,
                    "rendered_variant_strict_correct": variant_ok, "pair_strict_correct": pair_ok,
                    "original_reason": original_reason, "variant_reason": variant_reason, "pair_reason": pair_reason,
                    "original_row_count": len(original_rows), "variant_row_count": len(variant_rows),
                    "postgres_sql_sha256": sha256(pg_sql), "diagnostic_duckdb_sql": duck_sql}
                if not all((original_ok, variant_ok, pair_ok)):
                    result.update(original_rows=original_rows, variant_rows=variant_rows)
                results.append(result)
                print(f"[{index}/79] {case_id}: original={original_ok} rendered={variant_ok} pair={pair_ok}", flush=True)
    finally:
        engine.close()
    passed = sum(all((r["original_strict_correct"], r["rendered_variant_strict_correct"],
                      r["pair_strict_correct"])) for r in results)
    return {"stage": "M1 D3 local DuckDB compatibility diagnostics", "run_status": "complete" if passed == 79 else "failed",
        "recorded_at": datetime.now(timezone.utc).isoformat(), "case_count": 79, "pass_count": passed,
        "original_strict_pass_count": sum(r["original_strict_correct"] for r in results),
        "rendered_variant_strict_pass_count": sum(r["rendered_variant_strict_correct"] for r in results),
        "pair_strict_pass_count": sum(r["pair_strict_correct"] for r in results),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "actual_execution_backend": "duckdb", "postgresql_connected": False,
        "postgres_execution_verified": False, "new_model_request_count": 0,
        "numeric_emulation": "Diagnostic DECIMAL(38,15); does not emulate all PostgreSQL numeric rounding rules",
        "dataset_sha256": provenance["dataset_sha256"], "cases": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "Output already exists; choose an independent filename")
    report = check()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}, ensure_ascii=False, indent=2))
    if report["run_status"] != "complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
