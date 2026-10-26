"""Independent live metadata/data/runtime acceptance; default app stays DuckDB."""
from __future__ import annotations

import argparse
import errno
from copy import deepcopy
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from uuid import uuid4

from app.config import BASE_DIR, settings
from app.datasources.postgres_config import PostgresConfig, PostgresConfigError, load_recorded_source
from app.datasources.postgres_connections import PostgresConnectionError, safe_error
from app.datasources.runtime import create_datasource_runtime
from app.security import AccessController


def require(condition, name):
    if not condition:
        raise PostgresConnectionError("acceptance_failed_" + name)


@contextmanager
def owned_runtime(config, report):
    runtime = create_datasource_runtime(config)
    try:
        yield runtime
    finally:
        runtime.close()
        report["manager_final"] = runtime.executor.connections.public_status()


def run_checks(report):
    pg_settings = replace(settings, data_backend="postgresql", data_source_id="short_video_ops_postgres")
    config = PostgresConfig.from_settings(pg_settings)
    report["configuration"] = config.public()
    report["recorded_source"] = load_recorded_source(config).public()
    print("Verifying all 41 PostgreSQL tables, ACL and full typed row digests...", flush=True)
    with owned_runtime(pg_settings, report) as runtime:
        report["postgresql_connected"] = True
        report["live_verification"] = runtime.metadata.verification
        report["source_identity"] = runtime.identity.public()
        require(runtime.identity.backend == "postgresql" and runtime.identity.data_version == config.verified_data_version,
                "runtime_identity")
        require(len(runtime.catalog.tables) == 41 and sum(len(t["fields"]) for t in runtime.catalog.tables) == 276
            and len(runtime.catalog.relations) == 53, "catalog_counts")
        tables = {t["name"]: t for t in runtime.catalog.tables}
        access = AccessController()
        scope = access.resolve("demo_admin")

        def execute(name, sql, *, limit=200, success=True, validate=None, role=scope):
            result = runtime.executor.execute("short_video_ops", sql, role, row_limit=limit)
            require(result.success is success, name)
            if validate:
                require(validate(result), name + "_result")
            item = {"name": name, "passed": True, "sql": sql, "expected_success": success,
                "actual_success": result.success, "columns": result.columns, "returned_row_count": len(result.rows),
                "truncated": result.truncated, "execution_ms": result.execution_ms, "error": result.error}
            report["checks"].append(item)
            print(f"[{len(report['checks'])}] {name}: passed", flush=True)
            return result

        execute("qualified_table_count", "SELECT COUNT(*) AS users FROM askdata_ops.users",
            validate=lambda r: r.rows == [{"users": tables["users"]["row_count"]}])
        execute("cte_query", "WITH u AS (SELECT user_id FROM users ORDER BY user_id LIMIT 1) SELECT user_id FROM u",
            validate=lambda r: len(r.rows) == 1)
        execute("postgres_month_format", "SELECT to_char(registered_at,'YYYY-MM') AS month,COUNT(*) AS registrations "
            "FROM user_registrations GROUP BY 1 ORDER BY 1",
            validate=lambda r: not r.truncated and bool(r.rows) and sum(x["registrations"] for x in r.rows) == tables["user_registrations"]["row_count"])
        execute("date_and_null_normalization", "SELECT DATE '2026-01-01' AS day,NULL::text AS empty_value,"
            "CAST(1.25 AS NUMERIC) AS amount",
            validate=lambda r: r.rows == [{"day": "2026-01-01", "empty_value": None, "amount": 1.25}])
        execute("empty_result", "SELECT user_id FROM user_registrations WHERE registered_at < '1900-01-01'",
            validate=lambda r: r.rows == [] and r.columns == ["user_id"] and not r.truncated)
        require(tables["users"]["row_count"] > 10000, "limit_probe_source_rows")
        execute("preview_200_limit", "SELECT user_id FROM users ORDER BY user_id LIMIT 201",
            validate=lambda r: len(r.rows) == 200 and r.truncated)
        execute("scoring_10000_limit", "SELECT user_id FROM users ORDER BY user_id LIMIT 10001", limit=10000,
            validate=lambda r: len(r.rows) == 10000 and r.truncated)
        execute("sql_failure_redaction", "SELECT 1/0 AS invalid_value", success=False,
            validate=lambda r: "22012" in (r.error or ""))
        execute("query_recovery", "SELECT COUNT(*) AS users FROM users",
            validate=lambda r: r.rows == [{"users": tables["users"]["row_count"]}])
        rejected = {
            "wrong_schema": "SELECT user_id FROM public.users LIMIT 1",
            "unknown_table": "SELECT id FROM missing_table",
            "projection_star": "SELECT * FROM users",
            "multiple_statements": "SELECT 1;SELECT 2",
            "write_statement": "DELETE FROM users WHERE FALSE",
            "write_cte": "WITH d AS (DELETE FROM users WHERE FALSE RETURNING user_id) SELECT user_id FROM d",
            "select_into": "SELECT user_id INTO forbidden_table FROM users",
            "locking_select": "SELECT user_id FROM users FOR UPDATE",
            "side_effect_function": "SELECT set_config('TimeZone','UTC',false)",
            "server_file_function": "SELECT pg_read_file('private')",
        }
        for name, sql in rejected.items():
            execute(name, sql, success=False)
        execute("application_role_denied", "SELECT content_id FROM contents LIMIT 1", success=False,
            role=access.resolve("demo_growth_ops"), validate=lambda r: "无权" in (r.error or ""))

        # Test the guard failure path without changing any target data. These
        # are explicitly baseline-corruption probes, not a claimed DB mutation.
        metadata = runtime.metadata
        original_guards = metadata._guards
        try:
            metadata._guards = deepcopy(original_guards)
            metadata._guards["users"][1] = "0" * 64
            execute("injected_content_guard_mismatch", "SELECT user_id FROM users LIMIT 1", success=False,
                validate=lambda r: "source_content_changed" in (r.error or ""))
        finally:
            metadata._guards = original_guards
        execute("guard_restore_recovery", "SELECT COUNT(*) AS users FROM users",
            validate=lambda r: r.rows == [{"users": tables["users"]["row_count"]}])
        report["negative_guard_probe"] = {"injected_expected_guard_mismatch": True, "target_data_modified": False}
        profile = metadata.profile_table("short_video_ops.user_registrations", ["registered_at", "user_id"])
        require(set(profile) == {"registered_at", "user_id"} and all(profile[f]["sample_values"] for f in profile), "live_profile")
        require(all(isinstance(x, str) and "T" in x for x in profile["registered_at"]["sample_values"]), "timestamp_profile")
        report["profile"] = profile
        numeric_profile = metadata.profile_table("short_video_ops.contents", ["duration_seconds"])
        require(bool(numeric_profile["duration_seconds"]["sample_values"]) and
            all(isinstance(x, (int, float)) for x in numeric_profile["duration_seconds"]["sample_values"]), "numeric_profile")
        report["numeric_profile"] = numeric_profile
        report["checks"].append({"name": "verified_live_profile", "passed": True})
        report["live_target_verified"] = True
        report["runtime_available"] = True
        report["catalog_version"] = runtime.catalog.version
    report["manager_final"] = runtime.executor.connections.public_status()
    require(report["manager_final"]["state"] == "closed" and report["manager_final"]["active_operation_count"] == 0,
            "runtime_owner_closed_pool")
    report["checks"].append({"name": "runtime_owner_closes_shared_pool", "passed": True})


def public_failure(error):
    """Retain useful storage codes without driver text or filesystem paths."""
    if isinstance(error, OSError):
        category = {errno.ENOSPC: "disk_full", errno.EDQUOT: "quota_exceeded",
                    errno.EEXIST: "output_exists"}.get(error.errno, "filesystem_error")
        return {"type": type(error).__name__, "category": category, "errno": error.errno}
    return {"type": type(error).__name__, **(
        {"message": str(error)} if isinstance(error, PostgresConfigError) else safe_error(error).public())}


def write_json_file(path, report):
    # Exclusive creation protects historical reports; fsync detects buffered
    # write failures before database work starts or a final file is published.
    payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    with path.open("x", encoding="utf-8") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def persist_final_report(output, report):
    # Keep the valid running marker if writing/flushing the final report fails.
    # Only replace the output reserved by this invocation; never call directly
    # on historical files. Temporary file uses the same filesystem for rename.
    temporary = output.with_name(output.name + "." + uuid4().hex + ".tmp")
    try:
        write_json_file(temporary, report)
        os.replace(temporary, output)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass  # Cleanup must not obscure the original storage failure.


def execute_report(output, report, checks):
    report["report_write_status"] = "pending"
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        write_json_file(output, report)
    except Exception as error:
        report.update(run_status="failed", report_write_status="failed",
                      finished_at=datetime.now(timezone.utc).isoformat(), check_pass_count=0)
        report["report_write_error"] = {"phase": "initial", **public_failure(error)}
        return False

    try:
        require(settings.data_backend == "duckdb" and settings.data_source_id == "short_video_ops_duckdb", "default_app_backend")
        checks(report)
        report["run_status"] = "complete"
    except Exception as error:
        report.update(run_status="failed", live_target_verified=False, runtime_available=False)
        report["errors"].append(public_failure(error))
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["check_pass_count"] = sum(c["passed"] for c in report["checks"])
    report["report_write_status"] = "complete"
    try:
        persist_final_report(output, report)
    except Exception as error:
        # Preserve the checks' status separately and always print their original
        # errors. A successful validation without a saved report is not accepted.
        report["validation_run_status"] = report["run_status"]
        report.update(run_status="failed", report_write_status="failed")
        report["report_write_error"] = {"phase": "final", **public_failure(error)}
        return False
    return report["run_status"] == "complete"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BASE_DIR/"evaluation/results/m1_c3_postgres_runtime_server.json")
    args = parser.parse_args()
    output = args.output.resolve()
    if any(p in output.parents for p in [(BASE_DIR/"data").resolve(), (BASE_DIR.parent/"data").resolve()]):
        raise PostgresConfigError("Output must be outside frozen data directories")
    report = {"stage": "M1 C3 live PostgreSQL metadata, source verification and runtime", "run_status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(), "application_backend": settings.data_backend,
        "application_source_id": settings.data_source_id, "postgresql_connected": False,
        "live_target_verified": False, "runtime_available": False, "catalog_version": None,
        "new_model_request_count": 0, "checks": [], "errors": []}
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    success = execute_report(output, report, run_checks)
    print(json.dumps({k: report[k] for k in ['run_status', 'check_pass_count', 'live_target_verified', 'runtime_available',
        'catalog_version', 'new_model_request_count', 'errors', 'report_write_status',
        'report_write_error', 'validation_run_status'] if k in report}, ensure_ascii=False, indent=2), flush=True)
    raise SystemExit(0 if success else 1)


if __name__ == '__main__': main()
