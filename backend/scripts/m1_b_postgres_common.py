"""M1 B shared helpers. No application runtime or model configuration imports."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import re
from typing import Any

from scripts.preflight_m1_b_source import (
    BASE, BASELINE_DATA_VERSION, PG_TYPES, TARGET, digest_file, json_value,
    multiset_hash, quote, typed_row_hash,
)

APPROVED_SPEC = "8f936c3089614a38b17194b76e0c073c20cfe5b194ecb8f9f1e27b8f4d2ca7fd"
DEFAULT_PREPARATION = BASE / "evaluation/results/m1_b_source_server_20261008"


class CheckFailed(ValueError):
    """Controlled messages exclude passwords and database connection text."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailed(message)


def digest_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def scalar(value: Any) -> Any:
    return str(value) if isinstance(value, Decimal) else json_value(value)


def table_sql(table: dict) -> str:
    return quote(TARGET["physical_schema"]) + "." + quote(table["name"])


def statements(table: dict) -> tuple[str, str]:
    names = ", ".join(quote(field["name"]) for field in table["columns"])
    definitions = [quote(field["name"]) + " " + PG_TYPES[field["source_type"]] for field in table["columns"]]
    definitions.append("PRIMARY KEY (" + ", ".join(quote(key) for key in table["primary_key"]) + ")")
    ddl = f"CREATE TABLE {table_sql(table)} (\n  " + ",\n  ".join(definitions) + "\n);"
    copy = (f"COPY {table_sql(table)} ({names}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8', "
            f"NULL '', FORCE_NULL ({names}));")
    return ddl, copy


def check_source_files(manifest: dict) -> None:
    for name, expected in manifest["source"]["files_sha256"].items():
        require(Path(name).name == name, "Invalid source file name")
        require(digest_file(BASE / "data/databases/short_video_ops" / name) == expected,
                "Frozen source file changed: " + name)


def load_preparation(directory: Path) -> tuple[dict, dict]:
    raw = {name: (directory / name).read_bytes() for name in
           ["source_preflight.json", "import_manifest.json", "preparation_review.json"]}
    source, manifest, review = [json.loads(raw[name]) for name in raw]
    require(source["status"] == review["status"] == "passed", "Source preparation did not pass")
    require(source["errors"] == source["warnings"] == [], "Source preparation has errors/warnings")
    require(source["source_files_unchanged"] and review["all_typed_row_digests_match"] and
            review["format_precision_probe_passed"], "Source preparation evidence is incomplete")
    require(source["source"]["data_version"] == BASELINE_DATA_VERSION, "Source differs from accepted M1 A data")
    require(source["source"] == manifest["source"] and review["summary"] == source["summary"], "Source evidence disagrees")
    require(manifest["target"] == TARGET, "Target/roles differ from approved plan")
    require(digest_json(manifest) == source["import_spec_sha256"] == APPROVED_SPEC, "Specification differs from approved manifest")
    for name in ["source_preflight.json", "import_manifest.json"]:
        require(hashlib.sha256(raw[name]).hexdigest() == review["input_artifact_sha256"][name],
                "Preparation artifact bytes changed: " + name)
    require(len(manifest["tables"]) == 41 and sum(t["row_count"] for t in manifest["tables"]) == 722732, "Unexpected source counts")
    for table in manifest["tables"]:
        require(re.fullmatch(r"[a-z][a-z0-9_]*", table["name"]) is not None, "Invalid table name")
        require(table["csv_relative_path"] == f"data/databases/short_video_ops/{table['name']}.csv", "Unexpected CSV path")
        require(statements(table) == (table["create_table_sql"], table["copy_from_stdin_sql"]), "SQL differs from approved definitions")
    check_source_files(manifest)
    return manifest, {"canonical_import_spec_sha256": APPROVED_SPEC, "source_data_version": BASELINE_DATA_VERSION,
        "preparation_artifact_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in raw.items()},
        "source_file_count": len(manifest["source"]["files_sha256"])}


def begin_report(path: Path, preparation: Path, mode: str) -> dict:
    output = path.resolve()
    for protected in [(BASE / "data/databases/short_video_ops").resolve(), preparation.resolve()]:
        require(output != protected and protected not in output.parents, "Report must be outside source/preparation directories")
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"stage": "M1 B PostgreSQL " + mode, "run_status": "running", "mode": mode,
        "started_at": datetime.now(timezone.utc).isoformat(), "target": dict(TARGET), "commit_state": "not_started",
        "postgresql_connected": False, "target_data_verified": False, "verified_target_data_version": None,
        "new_model_request_count": 0, "errors": []}
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return report


def save_report(path: Path, report: dict) -> None:
    # A process interruption must not leave a truncated commit/recovery record.
    from uuid import uuid4
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def safe_error(error: BaseException) -> dict:
    return {"type": type(error).__name__, "sqlstate": getattr(error, "sqlstate", None),
            "message": str(error) if isinstance(error, CheckFailed) else
            "Operation failed; raw connection/database text omitted. Inspect phase and SQLSTATE."}


def connect_driver(host: str, port: int, role: str, password: str):
    import psycopg
    require(psycopg.__version__ == "3.2.13", "Install the pinned requirements-postgres.txt driver")
    return psycopg.connect(host=host, port=port, dbname=TARGET["physical_database"], user=role,
        password=password, connect_timeout=10, autocommit=True, client_encoding="UTF8",
        application_name="askdata_m1_b_" + role)


def configure_transaction(connection, *, read_only: bool, timeout_ms: int) -> None:
    connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, " + ("READ ONLY" if read_only else "READ WRITE"))
    connection.execute("SET LOCAL search_path TO pg_catalog, askdata_ops")
    connection.execute("SET LOCAL TimeZone TO 'UTC'")
    connection.execute("SET LOCAL DateStyle TO 'ISO, YMD'")
    connection.execute("SET LOCAL extra_float_digits TO 3")
    connection.execute("SELECT set_config('statement_timeout', %s, true)", (str(timeout_ms),))
    connection.execute("SET LOCAL lock_timeout TO '5s'")


def check_identity(connection, role: str) -> dict:
    row = connection.execute("SELECT current_database(), current_user, current_setting('server_version'), "
        "current_setting('server_version_num')::integer, current_setting('server_encoding'), "
        "current_setting('TimeZone'), datcollate, datctype, datlocprovider::text "
        "FROM pg_database WHERE datname=current_database()").fetchone()
    require(row[0] == TARGET["physical_database"] and row[1] == role, "Connected database/user differs from target")
    require(row[3] // 10000 == 16 and row[4:] == ("UTF8", "UTC", "C", "C", "c"), "Target version/encoding/timezone/locale differs")
    flags = connection.execute("SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
        "FROM pg_roles WHERE rolname=current_user").fetchone()
    require(flags == (True, False, False, False, False, False), "Execution role has unexpected administrative privileges")
    owner = connection.execute("SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname=%s",
        (TARGET["physical_schema"],)).fetchone()
    require(owner == (TARGET["import_role"],), "Business schema missing or owned by a different role")
    require(connection.execute("SELECT pg_has_role(%s,%s,'USAGE')",
        (TARGET["query_role"], TARGET["import_role"])).fetchone() == (False,), "Readonly role inherits import permissions")
    return {"physical_database": row[0], "execution_role": row[1], "server_version": row[2],
        "encoding": row[4], "timezone": row[5], "collation": row[6], "ctype": row[7], "locale_provider": row[8]}


def relation_objects(connection) -> list[tuple]:
    return connection.execute("SELECT c.relname,c.relkind::text FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname=%s AND c.relkind IN ('r','p','v','m','f','S') ORDER BY c.relname",
        (TARGET["physical_schema"],)).fetchall()


def column_metadata(connection, name: str) -> list[dict]:
    rows = connection.execute("SELECT a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull, "
        "a.attidentity::text,a.attgenerated::text,a.atthasdef FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid "
        "JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname=%s AND c.relname=%s AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum",
        (TARGET["physical_schema"], name)).fetchall()
    return [dict(zip(["name", "postgresql_type", "not_null", "identity", "generated", "has_default"], row)) for row in rows]


def primary_key(connection, name: str) -> list[str]:
    rows = connection.execute("SELECT a.attname FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid "
        "JOIN pg_namespace n ON n.oid=c.relnamespace "
        "CROSS JOIN LATERAL unnest(k.conkey) WITH ORDINALITY AS key_columns(attnum,ordinal_index) "
        "JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=key_columns.attnum "
        "WHERE n.nspname=%s AND c.relname=%s AND k.contype='p' ORDER BY key_columns.ordinal_index",
        (TARGET["physical_schema"], name)).fetchall()
    return [row[0] for row in rows]


def stat_equal(actual: Any, expected: Any, kind: str, key: str, policy: dict) -> bool:
    if actual is None or expected is None:
        return actual is expected
    if key == "average" or (kind == "DOUBLE" and key == "sum"):
        return math.isclose(float(actual), float(expected), rel_tol=policy["relative_tolerance"],
                            abs_tol=policy["absolute_tolerance"])
    if key in {"minimum", "maximum"} and kind in {"DATE", "TIMESTAMP"}:
        return json_value(actual) == expected
    return actual == expected


def verify_target(connection, manifest: dict, output: dict) -> str:
    output.update(status="running", tables=[], relations=[], errors=[])
    require(relation_objects(connection) == sorted((t["name"], "r") for t in manifest["tables"]),
            "Target must contain exactly 41 ordinary business tables")
    output["snapshot"] = str(connection.execute("SELECT pg_current_snapshot()").fetchone()[0])
    # Prevent concurrent DDL. Repeatable read ensures a consistent data snapshot.
    connection.execute("LOCK TABLE " + ", ".join(table_sql(t) for t in manifest["tables"]) + " IN ACCESS SHARE MODE")
    for index, table in enumerate(manifest["tables"], start=1):
        columns = column_metadata(connection, table["name"])
        expected_columns = [{"name": f["name"], "postgresql_type": f["postgresql_type"],
            "not_null": f["name"] in table["primary_key"], "identity": "", "generated": "", "has_default": False}
            for f in table["columns"]]
        require(columns == expected_columns, "Target columns/order/nullability differ: " + table["name"])
        keys = primary_key(connection, table["name"])
        require(keys == table["primary_key"], "Target primary key differs: " + table["name"])
        structure = connection.execute("SELECT pg_get_userbyid(c.relowner),c.relrowsecurity,c.relforcerowsecurity "
            "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relname=%s",
            (TARGET["physical_schema"], table["name"])).fetchone()
        require(structure == (TARGET["import_role"], False, False), "Target owner/RLS differs: " + table["name"])
        access = connection.execute("SELECT has_table_privilege(%s,%s,'SELECT')",
            (TARGET["query_role"], table_sql(table))).fetchone()[0]
        require(access is True, "Readonly SELECT grant missing: " + table["name"])
        expressions = ["COUNT(*)"]
        for field in table["columns"]:
            col = quote(field["name"])
            expressions.extend([f"COUNT(*)-COUNT({col})", f"COUNT(DISTINCT {col})", f"MIN({col})", f"MAX({col})"])
            if field["source_type"] in {"BIGINT", "DOUBLE"}:
                expressions.extend([f"SUM({col})", f"AVG({col})"])
        stats = iter(connection.execute(f"SELECT {', '.join(expressions)} FROM {table_sql(table)}").fetchone())
        count = next(stats)
        observed = {"name": table["name"], "row_count": count, "columns": columns, "primary_key": keys,
                    "owner": structure[0], "readonly_select_granted": access, "statistics": []}
        output["tables"].append(observed)
        if count != table["row_count"]:
            output["errors"].append({"table": table["name"], "check": "row_count", "actual": count, "expected": table["row_count"]})
        for field in table["columns"]:
            stat_keys = ["null_count", "non_null_distinct_count", "minimum", "maximum"]
            if field["source_type"] in {"BIGINT", "DOUBLE"}:
                stat_keys += ["sum", "average"]
            record = {"name": field["name"]}
            for key in stat_keys:
                actual = next(stats)
                record[key] = scalar(actual)
                if not stat_equal(actual, field[key], field["source_type"], key, manifest["floating_aggregate_comparison"]):
                    output["errors"].append({"table": table["name"], "column": field["name"], "check": key,
                                            "actual": scalar(actual), "expected": field[key]})
            observed["statistics"].append(record)
        hashes, actual_count = [], 0
        timestamp_precision = {f["name"]: {"nonzero_microsecond_count": 0, "max_significant_fractional_digits": 0}
                               for f in table["columns"] if f["source_type"] == "TIMESTAMP"}
        names = ", ".join(quote(f["name"]) for f in table["columns"])
        with connection.cursor(name=f"m1_b_rows_{index}") as cursor:
            cursor.execute(f"SELECT {names} FROM {table_sql(table)}")
            while batch := cursor.fetchmany(4096):
                actual_count += len(batch)
                hashes.extend(typed_row_hash(row, table["columns"]) for row in batch)
                for row in batch:
                    for field, value in zip(table["columns"], row):
                        if field["source_type"] == "TIMESTAMP" and value is not None:
                            require(value.tzinfo is None, "Unexpected timezone-bearing timestamp")
                            if value.microsecond:
                                item = timestamp_precision[field["name"]]
                                item["nonzero_microsecond_count"] += 1
                                item["max_significant_fractional_digits"] = max(item["max_significant_fractional_digits"],
                                    len(str(value.microsecond).zfill(6).rstrip("0")))
        observed.update(timestamp_value_precision=timestamp_precision, full_row_count=actual_count,
                        typed_row_multiset_sha256=multiset_hash(hashes))
        if observed["typed_row_multiset_sha256"] != table["typed_row_multiset_sha256"] or actual_count != count:
            output["errors"].append({"table": table["name"], "check": "full_typed_row_content"})
        key_sql = ", ".join(quote(key) for key in keys)
        observed["primary_key_duplicate_groups"] = connection.execute(
            f"SELECT COUNT(*) FROM (SELECT {key_sql} FROM {table_sql(table)} GROUP BY {key_sql} HAVING COUNT(*)>1) x").fetchone()[0]
        observed["primary_key_null_rows"] = connection.execute(f"SELECT COUNT(*) FROM {table_sql(table)} WHERE " +
            " OR ".join(quote(key) + " IS NULL" for key in keys)).fetchone()[0]
        if observed["primary_key_duplicate_groups"] or observed["primary_key_null_rows"]:
            output["errors"].append({"table": table["name"], "check": "primary_key_values"})
        print(f"verify [{index}/{len(manifest['tables'])}] {table['name']}: rows={count}", flush=True)
    for relation in manifest["business_relations"]:
        parent, child, pk, fk = [relation[k] for k in ["left_table_name", "right_table_name", "left_field", "right_field"]]
        schema = quote(TARGET["physical_schema"])
        unmatched = connection.execute(f"SELECT COUNT(*) FROM {schema}.{quote(child)} c WHERE c.{quote(fk)} IS NOT NULL "
            f"AND NOT EXISTS (SELECT 1 FROM {schema}.{quote(parent)} p WHERE p.{quote(pk)}=c.{quote(fk)})").fetchone()[0]
        output["relations"].append({"parent": parent, "child": child, "child_column": fk, "unmatched_non_null_child_rows": unmatched})
        if unmatched != relation["unmatched_non_null_child_rows"]:
            output["errors"].append({"check": "business_relation_values", "parent": parent, "child": child})
    require(not output["errors"], "Target data differs; inspect validation errors")
    version = digest_json({"target": TARGET, "tables": [{key: t[key] for key in
        ["name", "columns", "primary_key", "row_count", "typed_row_multiset_sha256"]} for t in output["tables"]]})
    output.update(status="passed", verified_snapshot_data_version=version,
        summary={"table_count": len(output["tables"]), "field_count": sum(len(t["columns"]) for t in output["tables"]),
                 "row_count": sum(t["row_count"] for t in output["tables"]), "relation_count": len(output["relations"]),
                 "error_count": 0, "full_typed_row_match_count": len(output["tables"])})
    return version


def check_readonly_acl(connection, manifest: dict) -> dict:
    grants = connection.execute("SELECT has_database_privilege(current_user,current_database(),'CONNECT'), "
        "has_database_privilege(current_user,current_database(),'CREATE'),has_database_privilege(current_user,current_database(),'TEMP'), "
        "has_schema_privilege(current_user,%s,'USAGE'),has_schema_privilege(current_user,%s,'CREATE'), "
        "has_schema_privilege(current_user,'public','CREATE')", (TARGET["physical_schema"], TARGET["physical_schema"])).fetchone()
    require(grants == (True, False, False, True, False, False), "Readonly database/schema grants are wider than expected")
    checks = []
    for table in manifest["tables"]:
        privileges = ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]
        values = connection.execute("SELECT " + ", ".join("has_table_privilege(current_user,%s,%s)" for _ in privileges),
            tuple(value for privilege in privileges for value in [table_sql(table), privilege])).fetchone()
        require(values == (True, False, False, False, False, False, False), "Readonly table grants wider than expected: " + table["name"])
        checks.append({"name": table["name"], "grants": dict(zip(privileges, values))})
    return {"status": "passed", "database_schema_grants": list(grants), "tables": checks}


def write_denial_probes(connection, table: dict, output: dict) -> None:
    from uuid import uuid4
    output.update(status="running", checks=[], read_write_transaction_used=True)
    qualified, key = table_sql(table), quote(table["primary_key"][0])
    names = ", ".join(quote(field["name"]) for field in table["columns"])
    probes = [
        ("insert", f"INSERT INTO {qualified} ({names}) SELECT {names} FROM {qualified} WHERE FALSE"),
        ("update", f"UPDATE {qualified} SET {key}={key} WHERE FALSE"),
        ("delete", f"DELETE FROM {qualified} WHERE FALSE"),
        ("create_table", f"CREATE TABLE {quote(TARGET['physical_schema'])}.{quote('_m1_acl_probe_' + uuid4().hex)} (probe bigint)"),
    ]
    # READ WRITE checks grants themselves, not only default_transaction_read_only.
    # Unexpected success cannot modify business rows; CREATE is rolled back too.
    with connection.transaction(force_rollback=True):
        connection.execute("SET TRANSACTION READ WRITE")
        connection.execute("SET LOCAL lock_timeout TO '5s'")
        connection.execute("SET LOCAL statement_timeout TO '15s'")
        for name, sql in probes:
            state = None
            try:
                with connection.transaction():
                    connection.execute(sql)
            except Exception as error:
                state = getattr(error, "sqlstate", None)
            output["checks"].append({"operation": name, "sqlstate": state, "permission_denied": state == "42501"})
    output["all_probe_changes_rolled_back"] = True
    require(all(item["permission_denied"] for item in output["checks"]), "Write-denial probes must all return SQLSTATE 42501")
    require(connection.execute("SELECT 1").fetchone() == (1,), "Connection did not recover after denial probes")
    output.update(status="passed", connection_recovered=True)


def common_arguments(parser) -> None:
    parser.add_argument("--preparation-dir", type=Path, default=DEFAULT_PREPARATION)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=55432)
    parser.add_argument("--statement-timeout-ms", type=int, default=120000)
    parser.add_argument("--check-only", action="store_true", help="Validate frozen inputs only; no connection/password prompt")


def validate_arguments(args) -> None:
    require(1 <= args.port <= 65535, "Invalid PostgreSQL port")
    require(1000 <= args.statement_timeout_ms <= 1800000, "Statement timeout must be 1000..1800000 ms")


def finish_report(path: Path, report: dict, error: BaseException | None = None) -> None:
    if error is not None:
        report["errors"].append(safe_error(error))
        report["run_status"] = "failed"
        report["target_data_verified"] = False
        report["verified_target_data_version"] = None
    else:
        report["run_status"] = "complete"
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    save_report(path, report)
    print(json.dumps({key: report.get(key) for key in ["run_status", "mode", "phase", "commit_state", "summary",
        "target_data_verified", "verified_target_data_version", "errors"]}, ensure_ascii=False, indent=2))
