"""Audit stored, explicit D3 variants. Never used to select or execute Gold SQL.

This is an offline provenance/type audit against the accepted C3 snapshot.
It neither opens PostgreSQL nor certifies the current server's data.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import traverse_scope

from app.config import BASE_DIR
from app.database import SCHEMA, physical_table_name
from app.datasources.sql_policy import validate_readonly_sql
from app.security import AccessController
from evaluation.gold_sql import GoldSqlSelectionError, select_gold_sql

CASE_PATH = BASE_DIR / "evaluation/cases/all_cases.jsonl"
BASELINE_PATH = BASE_DIR / "evaluation/results/m1_all_cases_before_postgres_gold79_20261010.jsonl"
LIST_PATH = BASE_DIR / "evaluation/cases/m1_d3_postgres_gold79.json"
REVIEW_PATH = BASE_DIR / "evaluation/cases/m1_d3_postgres_gold79_review.json"
EVIDENCE_PATH = BASE_DIR / "evaluation/results/m1_c3_postgres_runtime_server_v2.json"
BASELINE_SHA256 = "0eb11d55d07cbcc8926b4c5de6657c1f897e7559387cfb5f5c884ef20ec9e6ec"
EVIDENCE_SHA256 = "2cd9a7b9ad94300b36a9494b22a76e28db2d64a91c8d23835c96e982e6ea7166"
POSTGRES_SOURCE = {
    "logical_database_id": "short_video_ops", "source_id": "short_video_ops_postgres",
    "backend": "postgresql", "dialect": "postgres", "prompt_dialect": "PostgreSQL",
    "physical_schema": "askdata_ops",
    "catalog_version": "94a801805965a90aa6ae015f28af196f88f72c1d887319dd1896a2973eaaa288",
    "data_version": "882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(value: bytes | str) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def load_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_types(path: Path = EVIDENCE_PATH) -> dict[str, dict[str, str]]:
    require(sha256(path.read_bytes()) == EVIDENCE_SHA256, "Accepted C3 evidence bytes changed")
    evidence = json.loads(path.read_text(encoding="utf-8"))
    require(evidence["run_status"] == "complete" and evidence["live_target_verified"]
            and evidence["check_pass_count"] == 24 and not evidence["errors"], "C3 evidence not accepted")
    require(evidence["source_identity"] == POSTGRES_SOURCE, "Recorded PostgreSQL identity changed")
    types = {table["name"]: {c["name"]: c["postgresql_type"] for c in table["columns"]}
             for table in evidence["live_verification"]["tables"]}
    require(len(types) == 41 and sum(map(len, types.values())) == 276, "Incomplete physical type snapshot")
    return types


def _condition_leaves(condition):
    if isinstance(condition, (exp.And, exp.Or)):
        yield from _condition_leaves(condition.this)
        yield from _condition_leaves(condition.expression)
    elif isinstance(condition, (exp.Not, exp.Paren)):
        yield from _condition_leaves(condition.this)
    elif isinstance(condition, exp.Column):
        yield condition


def condition_columns(tree):
    for node in tree.walk():
        if isinstance(node, (exp.Where, exp.Having, exp.If)):
            yield from _condition_leaves(node.this)


def reviewed_shape(original_sql: str, types: dict[str, dict[str, str]]) -> tuple[str, dict[str, Any]]:
    """Model the only permitted changes for this frozen 79-case review.

    Rendering produces an audit reference, not a runtime fallback. Every
    persisted SQL is separately hashed, reviewed and executed on the server.
    """
    tree = sqlglot.parse_one(original_sql, read="duckdb")
    resolved = {}
    for scope in traverse_scope(tree):
        for column in scope.columns:
            candidates = [(source.name, types[source.name][column.name])
                          for alias, source in scope.sources.items()
                          if isinstance(source, exp.Table) and source.name in types
                          and column.name in types[source.name]
                          and (not column.table or column.table == alias)]
            if len(candidates) == 1:
                resolved[id(column)] = candidates[0]
    changes: dict[str, Any] = {
        "integer_truth_tests": [], "round_numeric_cast_count": 0,
        "floating_division_count": 0,
        "month_format_count": len(list(tree.find_all(exp.TimeToStr))),
        "substring_count": len(list(tree.find_all(exp.Substring))),
        "nullif_count": len(list(tree.find_all(exp.Nullif))),
        "nulls_last_order_count": len(list(tree.find_all(exp.Ordered))),
    }
    for column in list(condition_columns(tree)):
        require(id(column) in resolved, "Unresolved truth test: " + column.sql())
        table, data_type = resolved[id(column)]
        require(data_type == "bigint", "Unexpected truth-test physical type: " + data_type)
        changes["integer_truth_tests"].append({"expression": column.sql(), "table": table,
                                              "column": column.name, "physical_type": data_type})
        column.replace(exp.NEQ(this=column.copy(), expression=exp.Literal.number(0)))
    for division in list(tree.find_all(exp.Div)):
        division.set("this", exp.Cast(this=division.this.copy(),
                     to=exp.DataType.build("DOUBLE PRECISION", dialect="postgres")))
        changes["floating_division_count"] += 1
    for rounding in list(tree.find_all(exp.Round)):
        require(rounding.args.get("decimals") is not None, "Unreviewed one-argument ROUND")
        rounding.set("this", exp.Cast(this=rounding.this.copy(),
                     to=exp.DataType.build("NUMERIC", dialect="postgres")))
        changes["round_numeric_cast_count"] += 1
    require(all(not node.args.get("nulls_first") for node in tree.find_all(exp.Ordered)),
            "Unexpected original NULL ordering")
    return tree.sql(dialect="postgres", pretty=True), changes


def check_variant(original: dict, current: dict, review: dict, types: dict) -> dict:
    case_id = original["case_id"]
    require({k: v for k, v in current.items() if k != "gold_sql_by_dialect"} == original,
            case_id + ": original SQL/expectations/scoring fields changed")
    require(set(current["gold_sql_by_dialect"]) == {"postgres"}, case_id + ": unexpected variants")
    selected = select_gold_sql(current, POSTGRES_SOURCE)
    require(selected.selection_key == "gold_sql_by_dialect.postgres", "Wrong SQL selection")
    reference, changes = reviewed_shape(original["gold_sql"], types)
    tree = sqlglot.parse_one(selected.sql, read="postgres")
    require(tree.sql(dialect="postgres") == sqlglot.parse_one(reference, read="postgres").sql(dialect="postgres"),
            case_id + ": SQL differs from reviewed dialect-only changes")
    require(review["case_id"] == case_id and review["original_sql_sha256"] == sha256(original["gold_sql"])
            and review["postgres_sql_sha256"] == sha256(selected.sql)
            and review["changes"] == changes, case_id + ": review provenance mismatch")
    require(review["status"] == "offline_reviewed_pending_postgres_execution"
            and review["semantic_note"] and review["postgres_execution_verified"] is False,
            case_id + ": invalid offline review status")
    require(tree.named_selects == original["expected_columns"], case_id + ": output names changed")
    require(not list(condition_columns(tree)), case_id + ": non-boolean physical column used as predicate")
    for node in tree.find_all(exp.Round):
        require(isinstance(node.this, exp.Cast) and node.this.args["to"].this == exp.DataType.Type.DECIMAL,
                case_id + ": two-argument ROUND without numeric input")
    for node in tree.find_all(exp.Div):
        require(isinstance(node.this, exp.Cast) and node.this.args["to"].this == exp.DataType.Type.DOUBLE,
                case_id + ": division is not explicitly floating point")
    require(all(not node.args.get("nulls_first") for node in tree.find_all(exp.Ordered)),
            case_id + ": NULL ordering changed")
    scope = AccessController().resolve(f"demo_{original['scenario']}")
    validate_readonly_sql("short_video_ops", selected.sql, SCHEMA, scope, dialect="postgres",
                          physical_schema="askdata_ops")
    # Independent scope/column resolution against all 276 recorded columns.
    qualify(tree.copy(), dialect="postgres", schema=types, identify=False,
            validate_qualify_columns=True)
    return {"case_id": case_id, "status": "passed", "changes": changes,
            "application_role": f"demo_{original['scenario']}",
            "postgres_sql_sha256": sha256(selected.sql)}


def first79_cases_path() -> Path:
    """Keep the original 79-case audit reproducible after the 351 additions."""
    historical = BASE_DIR / "evaluation/results/m1_all_cases_before_postgres_gold430_20261012.jsonl"
    if historical.exists():
        require(sha256(historical.read_bytes()) ==
                "16fe651be76e5eacde7eb30ac6b1880eb4fcb0d22eebb7b347142f26e488a34f",
                "Frozen first79 dataset bytes changed")
        return historical
    return CASE_PATH


def audit(*, cases_path: Path | None = None) -> dict:
    cases_path = cases_path or first79_cases_path()
    require(sha256(BASELINE_PATH.read_bytes()) == BASELINE_SHA256, "Pre-D3 original bytes changed")
    originals, current = load_rows(BASELINE_PATH), load_rows(cases_path)
    require(len(originals) == len(current) == 430, "Expected 430 cases")
    require([r["case_id"] for r in originals] == [r["case_id"] for r in current], "Case order changed")
    selected_ids = json.loads(LIST_PATH.read_text(encoding="utf-8"))["case_ids"]
    expected_ids = json.loads((BASE_DIR / "evaluation/cases/m1_a_duckdb_regression.json").read_text(encoding="utf-8"))["case_ids"]
    classic = [r["case_id"] for r in originals if r["classic"]]
    extension = json.loads((BASE_DIR / "evaluation/cases/phase83_validation.json").read_text(encoding="utf-8"))["case_ids"]
    require(selected_ids == expected_ids == classic + extension and len(set(selected_ids)) == 79,
            "Scope must be the frozen classic49 + extension30")
    types = load_types()
    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    require(review["baseline_sha256"] == BASELINE_SHA256 and review["c3_evidence_sha256"] == EVIDENCE_SHA256
            and review["source_identity"] == POSTGRES_SOURCE, "Review source provenance changed")
    records = {r["case_id"]: r for r in review["cases"]}
    require(len(records) == len(review["cases"]) == 79 and set(records) == set(selected_ids), "Review coverage mismatch")
    checked = {}
    untouched = 0
    old_lines = BASELINE_PATH.read_bytes().splitlines()
    new_lines = cases_path.read_bytes().splitlines()
    for index, (original, case) in enumerate(zip(originals, current)):
        case_id = case["case_id"]
        require(select_gold_sql(original).public() == select_gold_sql(case).public(),
                case_id + ": DuckDB SQL selection changed")
        if case_id in records:
            checked[case_id] = check_variant(original, case, records[case_id], types)
        else:
            require(old_lines[index] == new_lines[index], case_id + ": unselected case bytes changed")
            try:
                select_gold_sql(case, POSTGRES_SOURCE)
            except GoldSqlSelectionError:
                untouched += 1
            else:
                raise ValueError(case_id + ": unreviewed PostgreSQL fallback/variant found")
    return {"stage": "M1 D3 stored PostgreSQL Gold79 offline audit", "run_status": "complete",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "reviewed_case_count": len(checked), "classic_count": 49, "extension_count": 30,
            "unchanged_duckdb_sql_count": 430, "untouched_unreviewed_case_count": untouched,
            "new_model_request_count": 0, "postgresql_connected": False,
            "live_target_verified": False, "postgres_execution_verified": False,
            "source_identity_scope": "Recorded C3 snapshot; not a current live verification",
            "recorded_source_identity": POSTGRES_SOURCE,
            "dataset_path": cases_path.relative_to(BASE_DIR).as_posix(),
            "dataset_scope": "Frozen first79 preparation snapshot" if cases_path != CASE_PATH else "Formal cases",
            "dataset_sha256": sha256(cases_path.read_bytes()),
            "baseline_sha256": BASELINE_SHA256, "c3_evidence_sha256": EVIDENCE_SHA256,
            "review_sha256": sha256(REVIEW_PATH.read_bytes()),
            "cases": [checked[case_id] for case_id in selected_ids], "errors": []}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, help="Explicit dataset; default preserves the frozen first79 snapshot")
    parser.add_argument("--output", type=Path, default=BASE_DIR / "evaluation/results/m1_d3_gold79_audit.json")
    args = parser.parse_args()
    # Exclusive creation preserves earlier evidence and catches accidental reruns.
    require(not args.output.exists(), "Output already exists; choose an independent report filename")
    report = audit(cases_path=args.cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in report.items() if k != "cases"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
