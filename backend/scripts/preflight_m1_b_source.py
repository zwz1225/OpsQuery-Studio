"""Read-only CSV preflight and PostgreSQL import specification; no DB/network writes."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import tempfile
from typing import Any

from app.datasources.row_digest import json_value, typed_row_hash, multiset_hash

import duckdb

BASE = Path(__file__).resolve().parents[1]
DATABASE = "short_video_ops"
BASELINE_DATA_VERSION = "d23481ffef242c04bc2adcf1f5a7082ec65ce392d30a48b16e7ccb0b3a3809b8"
PG_TYPES = {"VARCHAR": "text", "BIGINT": "bigint", "DATE": "date",
            "TIMESTAMP": "timestamp without time zone", "DOUBLE": "double precision"}
TARGET = {"source_id": "short_video_ops_postgres", "logical_database_id": DATABASE,
          "backend": "postgresql", "dialect": "postgres", "physical_database": "askdata_m1_test",
          "physical_schema": "askdata_ops", "import_role": "askdata_import",
          "query_role": "askdata_readonly"}


def quote(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def digest_file(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def parse_cell(value: str, kind: str) -> Any:
    if "\x00" in value:
        raise ValueError("NUL byte is not supported by PostgreSQL text input")
    if value == "":
        return None  # Verified against the existing read_csv_auto baseline below.
    if kind == "VARCHAR":
        return value
    if kind == "BIGINT":
        if not re.fullmatch(r"[+-]?[0-9]+", value):
            raise ValueError("Not a decimal integer")
        result = int(value)
        if not -(2 ** 63) <= result < 2 ** 63:
            raise ValueError("Outside signed 64-bit integer range")
        return result
    if kind == "DOUBLE":
        result = float(value)
        if not math.isfinite(result):
            raise ValueError("Non-finite floating point value")
        return result
    if kind == "DATE":
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("Expected ISO date")
        return date.fromisoformat(value)
    if kind == "TIMESTAMP":
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?", value):
            raise ValueError("Expected timezone-free ISO timestamp with at most six fractional digits")
        return datetime.fromisoformat(value)
    raise ValueError("Unsupported physical type: " + kind)


def scan_csv(path: Path, fields: list[dict]) -> dict:
    headers = [field["name"] for field in fields]
    nulls = [0] * len(fields)
    fractional = [0] * len(fields)
    max_digits = [0] * len(fields)
    count = 0
    hashes = []
    with path.open("rb") as stream:
        utf8_bom = stream.read(3) == b"\xef\xbb\xbf"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        if next(reader, None) != headers:
            raise ValueError("CSV header/order does not match schema: " + path.name)
        for record_number, row in enumerate(reader, start=2):
            if len(row) != len(fields):
                raise ValueError(f"{path.name}: record {record_number} has wrong column count")
            typed = []
            for index, (value, field) in enumerate(zip(row, fields)):
                try:
                    typed.append(parse_cell(value, field["source_type"]))
                except (ValueError, OverflowError) as exc:
                    # No raw field value in errors or reports.
                    raise ValueError(f"{path.name}: record {record_number}, {field['name']}: {exc}") from exc
                nulls[index] += int(value == "")
                if field["source_type"] == "TIMESTAMP" and "." in value:
                    fractional[index] += 1
                    max_digits[index] = max(max_digits[index], len(value.rsplit(".", 1)[1]))
            hashes.append(typed_row_hash(typed, fields))
            count += 1
    return {"row_count": count, "utf8_bom": utf8_bom, "empty_cell_counts": nulls,
            "fractional_timestamp_counts": fractional, "max_fractional_digits": max_digits,
            "typed_row_multiset_sha256": multiset_hash(hashes)}


def null_probe() -> dict:
    with tempfile.TemporaryDirectory(prefix="askdata_m1_b_null_") as tmp:
        path = Path(tmp) / "probe.csv"
        path.write_text('id,value\n1,\n2,""\n3,NULL\n4,"a,b"\n', encoding="utf-8")
        with duckdb.connect() as connection:
            actual = connection.execute("SELECT * FROM read_csv_auto(?, header=true, sample_size=-1) ORDER BY id",
                                        [str(path)]).fetchall()
    expected = [(1, None), (2, None), (3, "NULL"), (4, "a,b")]
    if actual != expected:
        raise ValueError("DuckDB CSV NULL behavior differs from the proposed COPY contract")
    return {"passed": True, "unquoted_empty_is_null": True, "quoted_empty_is_null": True,
            "literal_NULL_is_text": True, "quoted_comma_preserved": True}


def preflight(folder: Path, expected_version: str) -> tuple[dict, dict | None, str | None]:
    report = {"stage": "M1 B source preparation", "status": "failed",
              "created_at": datetime.now(timezone.utc).isoformat(),
              "duckdb_version": duckdb.__version__, "target_plan": TARGET,
              "postgresql_connected": False, "new_model_request_count": 0,
              "errors": [], "warnings": [], "tables": [], "relations": []}
    errors, warnings = report["errors"], report["warnings"]
    try:
        schema = json.loads((folder / "_schema.json").read_text(encoding="utf-8"))
        source_manifest = json.loads((folder / "_database_manifest.json").read_text(encoding="utf-8"))
        if folder.name != DATABASE or schema["database"] != DATABASE or source_manifest["database"] != DATABASE:
            raise ValueError("Wrong logical database/source directory")
        tables = schema["tables"]
        table_names = [table["name"] for table in tables]
        if len(table_names) != len(set(table_names)):
            raise ValueError("Duplicate physical table names")
        if set(table_names) != {path.stem for path in folder.glob("*.csv")}:
            raise ValueError("CSV file set differs from schema table set")
        if set(table_names) != set(source_manifest["tables"]):
            raise ValueError("Manifest table set differs from schema")
        paths = sorted(folder.glob("*.csv")) + [folder / "_schema.json", folder / "_database_manifest.json"]
        before = {path.name: digest_file(path) for path in paths}
        # Same canonical algorithms as csv_metadata, without importing runtime/config.
        entries = [{"path": f"data/databases/{DATABASE}/{path.name}", "sha256": before[path.name]}
                   for path in sorted(folder.iterdir()) if path.is_file() and
                   (path.suffix == ".csv" or path.name == "_schema.json")]
        data_version = hashlib.sha256(json.dumps(entries, ensure_ascii=False, sort_keys=True,
                                                separators=(",", ":")).encode("utf-8")).hexdigest()
        catalog_content = json.dumps({"tables": tables, "relations": schema["relations"]},
                                     ensure_ascii=False, sort_keys=True)
        report["source"] = {"logical_database_id": DATABASE, "source_id": "short_video_ops_duckdb",
                            "data_version": data_version, "expected_data_version": expected_version,
                            "catalog_version": hashlib.sha256(catalog_content.encode("utf-8")).hexdigest(),
                            "files_sha256": before,
                            "csv_bytes": sum(path.stat().st_size for path in folder.glob("*.csv"))}
        if data_version != expected_version:
            raise ValueError("Source data version differs from the accepted M1 A baseline")
        report["csv_null_probe"] = null_probe()
        type_counts = Counter()
        with duckdb.connect(config={"threads": 1}) as connection:
            for number, table in enumerate(tables, start=1):
                name, fields = table["name"], table["fields"]
                if table["id"] != f"{DATABASE}.{name}" or table["database"] != DATABASE:
                    raise ValueError("Invalid logical table identity: " + name)
                field_names = [field["name"] for field in fields]
                if len(field_names) != len(set(field_names)) or not fields:
                    raise ValueError("Duplicate/empty field definition: " + name)
                for field in fields:
                    if field["source_type"] not in PG_TYPES:
                        raise ValueError("Unsupported physical source type")
                    type_counts[field["source_type"]] += 1
                raw = scan_csv(folder / f"{name}.csv", fields)
                table_sql = quote(name)
                connection.execute(f"CREATE TABLE {table_sql} AS SELECT * FROM read_csv_auto("
                                   f"{literal((folder / (name + '.csv')).resolve().as_posix())},"
                                   " header=true, sample_size=-1)")
                actual_types = [(row[0], row[1]) for row in connection.execute(f"DESCRIBE {table_sql}").fetchall()]
                if actual_types != [(field["name"], field["source_type"]) for field in fields]:
                    errors.append({"table": name, "check": "inferred_types", "actual": actual_types})
                count = connection.execute(f"SELECT COUNT(*) FROM {table_sql}").fetchone()[0]
                declared = source_manifest["tables"][name]
                if not count == raw["row_count"] == table["row_count"] == declared["row_count"]:
                    errors.append({"table": name, "check": "row_count", "actual": count,
                                   "raw": raw["row_count"], "schema": table["row_count"], "manifest": declared["row_count"]})
                if declared["columns"] != field_names:
                    errors.append({"table": name, "check": "manifest_columns"})
                expressions = []
                for field in fields:
                    column = quote(field["name"])
                    expressions.extend([f"COUNT(*)-COUNT({column})", f"COUNT(DISTINCT {column})",
                                        f"MIN({column})", f"MAX({column})"])
                    if field["source_type"] in {"BIGINT", "DOUBLE"}:
                        expressions.extend([f"SUM({column})", f"AVG({column})"])
                stats = iter(connection.execute(f"SELECT {', '.join(expressions)} FROM {table_sql}").fetchone())
                columns = []
                for index, field in enumerate(fields):
                    kind = field["source_type"]
                    null_count, distinct, minimum, maximum = [next(stats) for _ in range(4)]
                    item = {"name": field["name"], "source_type": kind, "postgresql_type": PG_TYPES[kind],
                            "null_count": null_count, "non_null_distinct_count": distinct,
                            "minimum": json_value(minimum), "maximum": json_value(maximum),
                            "raw_empty_cell_count": raw["empty_cell_counts"][index]}
                    if kind in {"BIGINT", "DOUBLE"}:
                        item.update(sum=next(stats), average=next(stats))
                    if kind == "TIMESTAMP":
                        item.update(fractional_value_count=raw["fractional_timestamp_counts"][index],
                                    max_fractional_digits=raw["max_fractional_digits"][index])
                    if null_count != raw["empty_cell_counts"][index]:
                        errors.append({"table": name, "column": field["name"], "check": "NULL_parse"})
                    profile = field.get("data_profile", {})
                    null_ratio = round(null_count / count, 6) if count else 0.0
                    if "null_ratio" in profile and null_ratio != profile["null_ratio"]:
                        warnings.append({"table": name, "column": field["name"], "check": "profile_null_ratio",
                                         "actual": null_ratio, "declared": profile["null_ratio"]})
                    columns.append(item)
                keys = table.get("primary_key") or []
                if not keys or any(key not in field_names for key in keys):
                    raise ValueError("Invalid/missing declared primary key: " + name)
                key_sql = ", ".join(quote(key) for key in keys)
                duplicates = connection.execute(f"SELECT COUNT(*) FROM (SELECT {key_sql} FROM {table_sql} "
                                                f"GROUP BY {key_sql} HAVING COUNT(*) > 1)").fetchone()[0]
                key_nulls = connection.execute(f"SELECT COUNT(*) FROM {table_sql} WHERE " +
                                              " OR ".join(quote(key) + " IS NULL" for key in keys)).fetchone()[0]
                if duplicates or key_nulls:
                    errors.append({"table": name, "check": "primary_key", "duplicate_groups": duplicates,
                                   "null_rows": key_nulls})
                cursor = connection.execute(f"SELECT {', '.join(quote(f) for f in field_names)} FROM {table_sql}")
                hashes = []
                while batch := cursor.fetchmany(4096):
                    hashes.extend(typed_row_hash(row, fields) for row in batch)
                typed_hash = multiset_hash(hashes)
                if typed_hash != raw["typed_row_multiset_sha256"]:
                    errors.append({"table": name, "check": "raw_vs_DuckDB_typed_row_multiset"})
                report["tables"].append({"name": name, "logical_table_id": table["id"],
                    "csv_sha256": before[name + ".csv"], "utf8_bom": raw["utf8_bom"],
                    "row_count": count, "columns": columns,
                    "primary_key": keys, "primary_key_duplicate_groups": duplicates,
                    "primary_key_null_rows": key_nulls, "typed_row_multiset_sha256": typed_hash,
                    "raw_typed_row_multiset_sha256": raw["typed_row_multiset_sha256"]})
                print(f"[{number}/{len(tables)}] {name}: rows={count} fields={len(fields)}", flush=True)
            definitions = {table["name"]: {field["name"] for field in table["fields"]} for table in tables}
            for relation in schema["relations"]:
                parent, child = relation["left_table_name"], relation["right_table_name"]
                pk, fk = relation["left_field"], relation["right_field"]
                if (parent not in definitions or child not in definitions or
                    pk not in definitions[parent] or fk not in definitions[child] or
                    relation["left_table"] != f"{DATABASE}.{parent}" or
                    relation["right_table"] != f"{DATABASE}.{child}"):
                    raise ValueError("Invalid business relationship endpoint")
                orphans = connection.execute(f"SELECT COUNT(*) FROM {quote(child)} c WHERE c.{quote(fk)} IS NOT NULL "
                    f"AND NOT EXISTS (SELECT 1 FROM {quote(parent)} p WHERE p.{quote(pk)}=c.{quote(fk)})").fetchone()[0]
                report["relations"].append({**relation, "endpoint_valid": True,
                                            "unmatched_non_null_child_rows": orphans, "create_fk_constraint": False})
                if orphans:
                    warnings.append({"check": "business_relation_unmatched_rows", "parent": parent,
                                     "child": child, "child_column": fk, "count": orphans})
        for role, allowed in schema["role_tables"].items():
            if set(allowed) - set(table_names) or source_manifest["roles"].get(role) != allowed:
                errors.append({"check": "business_role_table_scope", "role": role})
        total = sum(table["row_count"] for table in report["tables"])
        if total != source_manifest["total_rows"] or len(tables) != source_manifest["table_count"]:
            errors.append({"check": "manifest_totals"})
        after = {path.name: digest_file(path) for path in paths}
        report["source_files_unchanged"] = before == after
        if before != after:
            errors.append({"check": "source_mutated_during_scan"})
        report["summary"] = {"table_count": len(tables), "field_count": sum(type_counts.values()),
                             "row_count": total, "relation_count": len(report["relations"]),
                             "type_counts": dict(type_counts), "error_count": len(errors),
                             "warning_count": len(warnings),
                             "columns_with_null": [{"table": table["name"], "column": field["name"],
                                 "null_count": field["null_count"]} for table in report["tables"]
                                 for field in table["columns"] if field["null_count"]]}
        report["status"] = "passed" if not errors else "failed"
    except (ValueError, KeyError, OSError, csv.Error, duckdb.Error) as exc:
        errors.append({"check": "preflight_failed", "message": str(exc)})
    if errors:
        return report, None, None
    copy_policy = {"format": "csv", "header": True, "encoding": "UTF8", "delimiter": ",",
                   "quote": '"', "escape": '"', "null": "", "force_null": "all_explicit_columns",
                   "note": "Both quoted and unquoted empty cells are NULL, matching verified DuckDB baseline."}
    manifest_tables, statements = [], ["-- Generated preparation artifact; not executed by preflight.",
                                       "-- Connect as askdata_import to askdata_m1_test. Schema must already exist.",
                                       "BEGIN;"]
    for table in report["tables"]:
        qualified = quote(TARGET["physical_schema"]) + "." + quote(table["name"])
        names = ", ".join(quote(field["name"]) for field in table["columns"])
        declarations = [quote(field["name"]) + " " + field["postgresql_type"] for field in table["columns"]]
        declarations.append("PRIMARY KEY (" + ", ".join(quote(key) for key in table["primary_key"]) + ")")
        ddl = "CREATE TABLE " + qualified + " (\n  " + ",\n  ".join(declarations) + "\n);"
        statements.append(ddl)
        copy = (f"COPY {qualified} ({names}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8', "
                f"NULL '', FORCE_NULL ({names}));")
        manifest_tables.append({**table, "csv_relative_path": f"data/databases/{DATABASE}/{table['name']}.csv",
                                "create_table_sql": ddl, "copy_from_stdin_sql": copy,
                                "nullable_columns": [field["name"] for field in table["columns"]
                                                     if field["name"] not in table["primary_key"]]})
    statements.append("COMMIT;")
    manifest = {"format_version": 1, "stage": "M1 B source preparation", "target": TARGET,
                "source": report["source"], "copy_policy": copy_policy,
                "typed_row_digest_algorithm": "SHA256 of sorted binary SHA256 hashes of compact UTF8 JSON rows; each cell is [source_type,value]; DOUBLE uses float.hex; TIMESTAMP uses naive ISO microseconds; NULL stays null. Duplicates retained.",
                "floating_aggregate_comparison": {"relative_tolerance": 1e-9, "absolute_tolerance": 1e-6,
                                                  "note": "Future aggregate check only; full typed-row hashes still must match."},
                "tables": manifest_tables, "business_relations": report["relations"],
                "target_data_verified": False, "verified_target_data_version": None,
                "write_policy": "Fresh tables only; no DROP, TRUNCATE, overwrite or ON_ERROR ignore.",
                "default_privileges_require_table_creator": TARGET["import_role"]}
    report["import_spec_sha256"] = hashlib.sha256(json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                                                            separators=(",", ":")).encode("utf-8")).hexdigest()
    return report, manifest, "\n\n".join(statements) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=BASE / "data/databases" / DATABASE)
    parser.add_argument("--expected-data-version", default=BASELINE_DATA_VERSION)
    parser.add_argument("--output-dir", type=Path, default=BASE / "evaluation/results/m1_b_source_local")
    args = parser.parse_args()
    source, output = args.source_dir.resolve(), args.output_dir.resolve()
    if output == source or source in output.parents:
        parser.error("Output directory must be outside the frozen source directory")
    if output.exists() and any(output.iterdir()):
        parser.error("Output directory is nonempty; choose a new directory to preserve prior reports")
    report, manifest, ddl = preflight(source, args.expected_data_version)
    output.mkdir(parents=True, exist_ok=True)
    (output / "source_preflight.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    if manifest is not None:
        (output / "import_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        (output / "create_tables.sql").write_text(ddl, encoding="utf-8")
    print(json.dumps({"status": report["status"], "summary": report.get("summary"),
                      "errors": report["errors"], "output_dir": str(output)}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
