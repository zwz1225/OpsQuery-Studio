"""Live C2 lifecycle probes against the isolated M1 B database; no model calls."""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Thread
from time import monotonic, sleep

from app.config import BASE_DIR, settings
from app.datasources.postgres_config import PostgresConfig, PostgresConfigError, load_recorded_source
from app.datasources.postgres_connections import PostgresConnectionManager, PostgresConnectionError, safe_error


def require(value, name):
    if not value:
        raise PostgresConnectionError("probe_failed_" + name)


def scalar(manager, query="SELECT 1"):
    with manager.transaction() as conn:
        return conn.execute(query).fetchone()[0]


def expected_failure(manager, query, states):
    try:
        with manager.transaction() as conn:
            conn.execute(query).fetchone()
            # In particular, if CREATE unexpectedly works, roll it back.
            raise PostgresConnectionError("probe_unexpected_success")
    except PostgresConnectionError as error:
        require(error.sqlstate in states, "expected_sqlstate")
        return error.public()


def queue_probes(manager):
    """Real psycopg_pool: one holder, one waiting slot, third borrower denied."""
    outcome = []

    def waiter():
        try:
            with manager.transaction():
                outcome.append("unexpected_success")
        except Exception as error:
            outcome.append(safe_error(error).category)

    worker = Thread(target=waiter, name="askdata-c2-pool-probe", daemon=True)
    with manager.transaction():
        worker.start()
        try:
            deadline = monotonic() + 1.5
            while manager.public_status()["pool"].get("requests_waiting", 0) != 1:
                require(monotonic() < deadline, "waiting_slot_observed")
                sleep(0.01)
            try:
                with manager.transaction():
                    raise PostgresConnectionError("probe_unexpected_checkout")
            except PostgresConnectionError as error:
                require(error.category == "pool_queue_full", "queue_capacity")
                queue_error = error.public()
            worker.join(timeout=4)
            require(not worker.is_alive() and outcome == ["pool_wait_timeout"], "waiting_deadline")
        finally:
            # Closing also releases the waiter if a failed assertion interrupted
            # the normal timeout path. No dangling thread owns a live operation.
            if worker.is_alive():
                manager.close()
                worker.join(timeout=4)
    require(scalar(manager) == 1, "pool_recovery")
    stats = manager.public_status()["pool"]
    require(stats["pool_min"] == stats["pool_max"] == stats["pool_size"] == 1, "pool_size")
    return {"queue_full": queue_error, "waiting_timeout": outcome[0],
            "recovered": True, "max_connections": 1, "max_waiting": 1}


def run_checks(config, report):
    checks = report["checks"]
    manager = PostgresConnectionManager(config)
    try:
        with manager:
            report["postgresql_connected"] = True
            report["connection_identity"] = manager.public_status()["connection_identity"]
            with manager.transaction() as conn:
                row = conn.execute("""SELECT current_database(), current_user,
                    current_setting('transaction_read_only'), current_schemas(false),
                    current_setting('TimeZone'), current_setting('transaction_isolation'),
                    (SELECT setting::int FROM pg_settings WHERE name='statement_timeout'),
                    (SELECT setting::int FROM pg_settings WHERE name='lock_timeout')""").fetchone()
            require(row == (config.database, config.user, "on", ["pg_catalog", config.schema], "UTC",
                "repeatable read", config.statement_timeout_ms, config.lock_timeout_ms), "transaction_settings")
            checks.append({"name": "login_and_transaction_settings", "passed": True,
                "readonly": row[2], "search_path": row[3], "timezone": row[4], "isolation": row[5],
                "statement_timeout_ms": row[6], "lock_timeout_ms": row[7]})
            require(scalar(manager) == 1, "normal_query")
            checks.append({"name": "normal_query", "passed": True})
            error = expected_failure(manager, "SELECT 1/0", {"22012"})
            require(scalar(manager) == 1, "query_failure_recovery")
            checks.append({"name": "query_failure_rollback_and_recovery", "passed": True, "expected_error": error})
            error = expected_failure(manager,
                "CREATE TABLE askdata_ops.__askdata_c2_readonly_probe (id integer)", {"25006", "42501"})
            require(scalar(manager) == 1, "readonly_recovery")
            checks.append({"name": "write_denied_and_recovery", "passed": True,
                "expected_error": error, "probe_changes_committed": False})
            with manager.transaction() as conn:
                conn.execute("SELECT set_config('TimeZone', 'Asia/Shanghai', true)")
                require(conn.execute("SHOW TimeZone").fetchone()[0] == "Asia/Shanghai", "local_timezone_set")
            require(scalar(manager, "SHOW TimeZone") == "UTC", "timezone_reset")
            checks.append({"name": "transaction_settings_do_not_leak", "passed": True})
    finally:
        manager.close()
        report["main_manager_final"] = manager.public_status()
    manager.close()
    try:
        with manager.transaction():
            raise PostgresConnectionError("probe_unexpected_checkout")
    except PostgresConnectionError as error:
        require(error.category == "manager_closed", "closed_admission")
    checks.append({"name": "idempotent_close_and_closed_admission", "passed": True})

    # Separate diagnostic pool; does not change application or .env settings.
    probe_config = replace(config, pool_min_size=1, pool_max_size=1, pool_max_waiting=1,
        pool_wait_timeout_seconds=2, statement_timeout_ms=1000, lock_timeout_ms=1000)
    probe = PostgresConnectionManager(probe_config)
    try:
        with probe:
            error = expected_failure(probe, "SELECT pg_sleep(2)", {"57014"})
            require(scalar(probe) == 1, "timeout_recovery")
            checks.append({"name": "statement_timeout_and_recovery", "passed": True, "expected_error": error})
            checks.append({"name": "pool_capacity_waiting_limit_and_recovery", "passed": True,
                **queue_probes(probe)})
            with probe.transaction() as conn:
                probe.close()
                require(not conn.closed, "active_connection_graceful_return")
            require(conn.closed, "active_connection_closed_on_return")
            checks.append({"name": "close_during_operation_and_return", "passed": True})
    finally:
        probe.close()
        report["probe_manager_final"] = probe.public_status()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BASE_DIR/"evaluation/results/m1_c2_postgres_connections_server.json")
    args = parser.parse_args()
    output = args.output.resolve()
    protected = [(BASE_DIR/"data").resolve(), (BASE_DIR.parent/"data").resolve()]
    if any(path == output or path in output.parents for path in protected):
        raise PostgresConfigError("Output must be outside frozen data directories")
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"stage": "M1 C2 PostgreSQL connection lifecycle", "run_status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(), "application_backend": settings.data_backend,
        "application_source_id": settings.data_source_id, "postgresql_connected": False,
        "live_target_verified": False, "catalog_version": None, "runtime_available": False,
        "new_model_request_count": 0, "checks": [], "errors": []}
    with output.open("x", encoding="utf-8") as stream:
        try:
            require(settings.data_backend == "duckdb" and settings.data_source_id == "short_video_ops_duckdb",
                    "application_stays_duckdb")
            config = PostgresConfig.from_settings(settings)
            report["configuration"] = config.public()
            report["recorded_source"] = load_recorded_source(config).public()
            run_checks(config, report)
            report.update(run_status="complete", connection_lifecycle_verified=True)
        except Exception as error:
            report["run_status"] = "failed"
            report["errors"].append({"type": type(error).__name__, **(
                {"message": str(error)} if isinstance(error, PostgresConfigError) else safe_error(error).public())})
        finally:
            report["finished_at"] = datetime.now(timezone.utc).isoformat()
            report["check_pass_count"] = sum(c["passed"] for c in report["checks"])
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["run_status"] == "complete" else 1)


if __name__ == "__main__":
    main()
