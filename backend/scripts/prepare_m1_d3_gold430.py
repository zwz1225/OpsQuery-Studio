"""One-time offline preparation; never used by runtime Gold selection.

Preserves first79 bytes and records each new SQL before publication. All output
names are exclusive except the formal case file, which is replaced atomically.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from scripts.audit_m1_d3_gold430 import (
    BEFORE_PATH, BEFORE_SHA256, FULL_LIST_PATH, REMAINING_LIST_PATH, FULL_REVIEW_PATH,
    FIRST_REVIEW_SHA256, frozen_inputs, review_record,
)
from scripts.audit_m1_d3_gold79 import (
    BASELINE_SHA256, CASE_PATH, EVIDENCE_SHA256, POSTGRES_SOURCE, check_variant,
    load_types, reviewed_shape, require, sha256,
)


def write_new(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def prepare():
    original_bytes = CASE_PATH.read_bytes()
    require(sha256(original_bytes) == BEFORE_SHA256, "Formal cases must match accepted pre430 snapshot")
    for path in (BEFORE_PATH, FULL_LIST_PATH, REMAINING_LIST_PATH, FULL_REVIEW_PATH):
        require(not path.exists(), "Preparation output exists: " + str(path))
    BEFORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with BEFORE_PATH.open("xb") as stream:
        stream.write(original_bytes)
    originals, before, first, _ = frozen_inputs()
    types = load_types()
    records, output_lines = [], []
    for old, case, line in zip(originals, before, original_bytes.splitlines(keepends=True)):
        if case["case_id"] in first:
            output_lines.append(line)
            continue
        require(case == old and "gold_sql_by_dialect" not in case, "Unexpected unreviewed baseline variant")
        sql, changes = reviewed_shape(case["gold_sql"], types)
        record = review_record(case, sql, changes)
        new = {**case, "gold_sql_by_dialect": {"postgres": sql}}
        check_variant(old, new, record, types)
        records.append(record)
        output_lines.append((json.dumps(new, ensure_ascii=False) + "\n").encode("utf-8"))
    require(len(records) == 351 and len(output_lines) == 430, "Unexpected preparation coverage")
    full_ids = [c["case_id"] for c in before]
    new_ids = [r["case_id"] for r in records]
    write_new(FULL_LIST_PATH, {"stage":"M1 D3 full explicit PostgreSQL Gold430", "case_count":430,
        "case_ids": full_ids, "scope":"Frozen formal430 order; first79 plus remaining351"})
    write_new(REMAINING_LIST_PATH, {"stage":"M1 D3 remaining explicit PostgreSQL Gold351", "case_count":351,
        "case_ids":new_ids,"scope":"Exact complement of the accepted first79"})
    write_new(FULL_REVIEW_PATH, {"stage":"M1 D3 remaining351 explicit PostgreSQL Gold case review",
        "review_kind":"Agent offline structure/type/semantic audit; real PostgreSQL execution pending",
        "review_date":"2026-10-12", "baseline_sha256":BASELINE_SHA256,"before_sha256":BEFORE_SHA256,
        "first79_review_sha256":FIRST_REVIEW_SHA256,"c3_evidence_sha256":EVIDENCE_SHA256,
        "source_identity":POSTGRES_SOURCE,"case_count":351,
        "sqlglot_version":"30.17.0","by_scenario":dict(Counter(r['scenario'] for r in records)),
        "cases":records})
    require(CASE_PATH.read_bytes() == original_bytes, "Formal cases changed during preparation")
    with NamedTemporaryFile(mode="wb", dir=CASE_PATH.parent, prefix="gold430_", delete=False) as stream:
        temp_path = Path(stream.name)
        stream.write(b"".join(output_lines))
        stream.flush()
        os.fsync(stream.fileno())
    temp_path.replace(CASE_PATH)
    print(json.dumps({"added_explicit_variants":len(records),"total_variants":430,
        "first79_unchanged":True,"formal_cases_sha256":sha256(CASE_PATH.read_bytes())},indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", required=True)
    parser.parse_args()
    prepare()


if __name__ == "__main__":
    main()
