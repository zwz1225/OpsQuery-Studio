"""Offline review of 430 explicit PG variants against frozen data/type evidence.

The 79-case acceptance remains a separate frozen record. This script validates
351 additions and all unchanged scoring fields; it opens no PostgreSQL connection.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlglot
from sqlglot import exp

from app.config import BASE_DIR
from evaluation.gold_sql import select_gold_sql
from scripts.audit_m1_d3_gold79 import (
    BASELINE_PATH, BASELINE_SHA256, CASE_PATH, EVIDENCE_SHA256, LIST_PATH,
    POSTGRES_SOURCE, REVIEW_PATH, check_variant, load_rows, load_types,
    reviewed_shape, require, sha256,
)

BEFORE_PATH = BASE_DIR / "evaluation/results/m1_all_cases_before_postgres_gold430_20261012.jsonl"
BEFORE_SHA256 = "16fe651be76e5eacde7eb30ac6b1880eb4fcb0d22eebb7b347142f26e488a34f"
FIRST_REVIEW_SHA256 = "fb0ba5949b9e0d68a124dc5d92c533372a423b031a613c9bc8026a153d2b8daf"
FULL_LIST_PATH = BASE_DIR / "evaluation/cases/m1_d3_postgres_gold430.json"
REMAINING_LIST_PATH = BASE_DIR / "evaluation/cases/m1_d3_postgres_gold351.json"
FULL_REVIEW_PATH = BASE_DIR / "evaluation/cases/m1_d3_postgres_gold351_review.json"
ACCEPTED_D3_CASES_PATH = BASE_DIR / "evaluation/results/m1_e_all_cases_before_aliases_20261012.jsonl"
ACCEPTED_D3_CASES_SHA256 = "e1cb760a8ffa4f89e45ca73403c439975c51d2be47cd36800ee4c7c0ee1925f1"


def frozen_inputs():
    require(sha256(BASELINE_PATH.read_bytes()) == BASELINE_SHA256, "Pre-D3 original bytes changed")
    require(sha256(BEFORE_PATH.read_bytes()) == BEFORE_SHA256, "Accepted first79 dataset bytes changed")
    require(sha256(REVIEW_PATH.read_bytes()) == FIRST_REVIEW_SHA256, "Frozen first79 review changed")
    originals, before = load_rows(BASELINE_PATH), load_rows(BEFORE_PATH)
    require(len(originals) == len(before) == 430, "Expected 430 original cases")
    first = json.loads(LIST_PATH.read_text(encoding="utf-8"))["case_ids"]
    require(len(first) == len(set(first)) == 79, "Invalid frozen first79 list")
    require([c["case_id"] for c in originals] == [c["case_id"] for c in before], "Frozen case order changed")
    first_records = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))["cases"]
    require([r["case_id"] for r in first_records] == first, "Frozen review order changed")
    for old, case in zip(originals, before):
        if case["case_id"] not in first:
            require(old == case, "Unreviewed baseline case changed: " + case["case_id"])
    return originals, before, first, first_records


def clauses(tree, kind):
    return [node.sql(dialect="postgres") for node in tree.find_all(kind)]


def review_record(case, sql, changes):
    tree = sqlglot.parse_one(sql, read="postgres")
    filters = clauses(tree, exp.Where)
    measures = [p.sql(dialect="postgres") for p in tree.selects]
    note = ("Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, "
            "window ordering, limits, aliases and frozen result/tie policy. "
            "Only explicit dialect/type adjustments are permitted. Outputs: " + ", ".join(case["expected_columns"]) +
            ". Filters: " + ("; ".join(filters) or "none") + ".")
    return {"case_id": case["case_id"], "scenario": case["scenario"], "query": case["query"],
        "semantic_note": note, "original_sql_sha256": sha256(case["gold_sql"]),
        "postgres_sql_sha256": sha256(sql), "changes": changes,
        "output_columns": tree.named_selects, "projection_expressions": measures,
        "physical_tables": sorted({t.name for t in tree.find_all(exp.Table)
            if t.name not in {c.alias for c in tree.find_all(exp.CTE)}}),
        "where_clauses": filters, "join_clauses": clauses(tree, exp.Join),
        "group_clauses": clauses(tree, exp.Group), "having_clauses": clauses(tree, exp.Having),
        "order_clauses": clauses(tree, exp.Order), "limit_clauses": clauses(tree, exp.Limit),
        "order_sensitive": case.get("order_sensitive"), "order_by_column": case.get("order_by_column"),
        "top_n_tie_policy": case.get("top_n_tie_policy"),
        "status": "offline_reviewed_pending_postgres_execution", "postgres_execution_verified": False}


def audit(*, cases_path: Path = ACCEPTED_D3_CASES_PATH, review_path: Path = FULL_REVIEW_PATH) -> dict:
    if cases_path == ACCEPTED_D3_CASES_PATH:
        require(sha256(cases_path.read_bytes()) == ACCEPTED_D3_CASES_SHA256,
                "Frozen D3 Gold430 cases changed after M1 E alias review")
    originals, before, first, first_records = frozen_inputs()
    current = load_rows(cases_path)
    require([c["case_id"] for c in current] == [c["case_id"] for c in before], "Full case order changed")
    review = json.loads(review_path.read_text(encoding="utf-8"))
    require(review["before_sha256"] == BEFORE_SHA256 and review["baseline_sha256"] == BASELINE_SHA256
            and review["first79_review_sha256"] == FIRST_REVIEW_SHA256
            and review["c3_evidence_sha256"] == EVIDENCE_SHA256
            and review["source_identity"] == POSTGRES_SOURCE, "Full review provenance mismatch")
    full_ids = json.loads(FULL_LIST_PATH.read_text(encoding="utf-8"))["case_ids"]
    remaining_ids = json.loads(REMAINING_LIST_PATH.read_text(encoding="utf-8"))["case_ids"]
    expected_ids = [c["case_id"] for c in originals]
    require(full_ids == expected_ids and len(set(full_ids)) == 430, "Invalid full430 manifest")
    require(remaining_ids == [i for i in expected_ids if i not in first] and len(remaining_ids) == 351,
            "Remaining scope must exactly complement frozen first79")
    records = {r["case_id"]: r for r in review["cases"]}
    require([r["case_id"] for r in review["cases"]] == remaining_ids and len(records) == 351,
            "Remaining review coverage/order changed")
    first_records = {r["case_id"]: r for r in first_records}
    types = load_types()
    original_by_id = {c["case_id"]: c for c in originals}
    old_lines, new_lines = BEFORE_PATH.read_bytes().splitlines(), cases_path.read_bytes().splitlines()
    checked = []
    preserved_first = 0
    for index, (old, case) in enumerate(zip(before, current)):
        cid = case["case_id"]
        require(select_gold_sql(old).public() == select_gold_sql(case).public(), cid + ": DuckDB selection changed")
        if cid in first_records:
            require(old_lines[index] == new_lines[index], cid + ": accepted first79 bytes changed")
            record = first_records[cid]
            preserved_first += 1
        else:
            record = records[cid]
            require(review_record(original_by_id[cid], case["gold_sql_by_dialect"]["postgres"], record["changes"])
                    == record, cid + ": semantic review detail changed")
        checked.append(check_variant(original_by_id[cid], case, record, types))
    return {"stage": "M1 D3 explicit PostgreSQL Gold430 offline audit", "run_status": "complete",
        "checked_at": datetime.now(timezone.utc).isoformat(), "reviewed_case_count": len(checked),
        "new_variant_count": len(records), "first79_byte_preserved_count": preserved_first,
        "unchanged_duckdb_sql_count": len(current), "unchanged_expected_and_scoring_case_count": len(current),
        "by_scenario": dict(Counter(c["scenario"] for c in current)),
        "new_variants_by_scenario": dict(Counter(c["scenario"] for c in current if c["case_id"] in records)),
        "dataset_sha256": sha256(cases_path.read_bytes()), "before_sha256": BEFORE_SHA256,
        "baseline_sha256": BASELINE_SHA256, "first79_review_sha256": FIRST_REVIEW_SHA256,
        "review_sha256": sha256(review_path.read_bytes()), "c3_evidence_sha256": EVIDENCE_SHA256,
        "new_model_request_count": 0, "postgresql_connected": False, "postgres_execution_verified": False,
        "live_target_verified": False, "source_identity_scope": "Recorded C3 snapshot; live execution pending",
        "recorded_source_identity": POSTGRES_SOURCE, "cases": checked, "errors": []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "Output exists; choose an independent filename")
    payload = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({k:v for k,v in payload.items() if k != "cases"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
