"""Verify independent M1 B source artifacts; does not connect to PostgreSQL."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

import duckdb
import sqlglot
from sqlglot import exp

from scripts.preflight_m1_b_source import (
    BASE, BASELINE_DATA_VERSION, PG_TYPES, TARGET, digest_file,
    multiset_hash, scan_csv, typed_row_hash,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def review(directory: Path) -> dict:
    report = json.loads((directory / "source_preflight.json").read_text(encoding="utf-8"))
    manifest = json.loads((directory / "import_manifest.json").read_text(encoding="utf-8"))
    ddl = (directory / "create_tables.sql").read_text(encoding="utf-8")
    require(report["status"] == "passed" and not report["errors"] and not report["warnings"], "Source check did not fully pass")
    require(report["source_files_unchanged"] and report["source"]["data_version"] == BASELINE_DATA_VERSION,
            "Source baseline changed")
    require(not report["postgresql_connected"] and report["new_model_request_count"] == 0, "Unexpected external execution")
    require(manifest["source"] == report["source"] and manifest["target"] == TARGET,
            "Manifest source/target differs from reviewed preflight")
    require(not manifest["target_data_verified"] and manifest["verified_target_data_version"] is None,
            "Source preparation incorrectly claims target verification")
    expected_digest = hashlib.sha256(json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                                               separators=(",", ":")).encode("utf-8")).hexdigest()
    require(expected_digest == report["import_spec_sha256"], "Manifest fingerprint differs")
    for name, expected in report["source"]["files_sha256"].items():
        require(digest_file(BASE / "data/databases/short_video_ops" / name) == expected,
                "Current source file differs: " + name)
    trees = sqlglot.parse(ddl, read="postgres")
    creates = [tree for tree in trees if isinstance(tree, exp.Create)]
    require(len(creates) == 41 and len(trees) == 43, "DDL must contain 41 CREATE TABLE and BEGIN/COMMIT")
    require(all(tree.kind == "TABLE" for tree in creates), "Unexpected DDL object")
    require([tree.this.this.name for tree in creates] == [table["name"] for table in manifest["tables"]], "DDL table order differs")
    require(all(tree.this.this.db == TARGET["physical_schema"] for tree in creates), "DDL schema differs")
    require(len(manifest["tables"]) == 41 and sum(t["row_count"] for t in manifest["tables"]) == 722732,
            "Wrong table/row totals")
    for table, specification in zip(report["tables"], manifest["tables"]):
        require(table["name"] == specification["name"] and table["columns"] == specification["columns"], "Column mapping differs")
        require(table["typed_row_multiset_sha256"] == table["raw_typed_row_multiset_sha256"], "CSV/DuckDB row content differs")
        require(not table["primary_key_duplicate_groups"] and not table["primary_key_null_rows"], "Invalid source primary key")
        require(all(f["postgresql_type"] == PG_TYPES[f["source_type"]] for f in table["columns"]), "Unsupported type mapping")
        require("FROM STDIN" in specification["copy_from_stdin_sql"] and "FORCE_NULL" in specification["copy_from_stdin_sql"],
                "Wrong COPY input/NULL contract")
    require(len(report["relations"]) == 53 and all(r["endpoint_valid"] and not r["unmatched_non_null_child_rows"]
                                                and not r["create_fk_constraint"] for r in report["relations"]),
            "Business relationship validation differs")
    # Focused format probe covers source BOM, quoted CSV delimiters/newlines,
    # literal NULL versus empty cells, and subsecond timestamp preservation.
    fields = [{"name": "key", "source_type": "VARCHAR"}, {"name": "text_value", "source_type": "VARCHAR"},
              {"name": "event_at", "source_type": "TIMESTAMP"}, {"name": "count_value", "source_type": "BIGINT"}]
    with tempfile.TemporaryDirectory(prefix="askdata_m1_b_format_") as tmp:
        path = Path(tmp) / "format.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            stream.write('key,text_value,event_at,count_value\nK001,"a,b\nsecond line",2026-01-01 12:00:00.123456,9223372036854775807\n'
                         'K002,NULL,,\nK003,"",2026-01-02 00:00:00,0\n')
        raw = scan_csv(path, fields)
        with duckdb.connect(config={"threads": 1}) as connection:
            rows = connection.execute("SELECT * FROM read_csv_auto(?, header=true, sample_size=-1)", [str(path)]).fetchall()
        require(raw["typed_row_multiset_sha256"] == multiset_hash([typed_row_hash(row, fields) for row in rows]),
                "CSV format/precision probe differs from DuckDB")
        require(raw["utf8_bom"] and raw["max_fractional_digits"][2] == 6 and rows[0][1] == "a,b\nsecond line",
                "BOM/quoted multiline/subsecond preservation failed")
        require(rows[1][1] == "NULL" and rows[2][1] is None, "Literal NULL/quoted empty semantics failed")
    return {"status": "passed", "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "input_artifact_sha256": {name: digest_file(directory / name)
                                      for name in ["source_preflight.json", "import_manifest.json", "create_tables.sql"]},
            "summary": report["summary"], "csv_with_utf8_bom": sum(t["utf8_bom"] for t in report["tables"]),
            "all_typed_row_digests_match": True, "format_precision_probe_passed": True,
            "postgresql_ddl_parsed_table_count": len(creates), "source_files_unchanged": True,
            "limits": ["SQLGlot parse checks preparation syntax, not PostgreSQL execution.",
                       "No target database data, table permissions or import transaction has been verified."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=BASE / "evaluation/results/m1_b_source_local_v2")
    args = parser.parse_args()
    directory = args.input_dir.resolve()
    output = directory / "preparation_review.json"
    require(not output.exists(), "Review already exists; preserve the original record")
    result = review(directory)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
