"""Import approved M1 B CSVs atomically; verify every target row before commit."""
from __future__ import annotations

import argparse
import getpass
import hashlib
from pathlib import Path

from scripts.m1_b_postgres_common import (
    BASE, TARGET, begin_report, check_identity, check_source_files, common_arguments,
    configure_transaction, connect_driver, finish_report, load_preparation,
    relation_objects, require, save_report, validate_arguments, verify_target,
)


def copy_tables(connection, manifest: dict, records: list) -> None:
    for index, table in enumerate(manifest["tables"], start=1):
        connection.execute(table["create_table_sql"])
        digest, byte_count = hashlib.sha256(), 0
        with (BASE / table["csv_relative_path"]).open("rb") as stream:
            with connection.cursor() as cursor:
                with cursor.copy(table["copy_from_stdin_sql"]) as copy:
                    while block := stream.read(1024 * 1024):
                        digest.update(block)
                        byte_count += len(block)
                        copy.write(block)
                copied_rows = cursor.rowcount
        require(digest.hexdigest() == table["csv_sha256"], "CSV changed during COPY: " + table["name"])
        require(copied_rows == table["row_count"], "COPY row count differs: " + table["name"])
        records.append({"name": table["name"], "copy_row_count": copied_rows, "csv_bytes_sent": byte_count,
                        "sent_csv_sha256": digest.hexdigest()})
        print(f"copy [{index}/{len(manifest['tables'])}] {table['name']}: rows={copied_rows}", flush=True)


def execute_import(connection, manifest: dict, report: dict, output: Path, timeout_ms: int) -> None:
    report.update(phase="begin_import", copied_tables=[], validation={})
    attempting_commit = False
    try:
        with connection.transaction():
            configure_transaction(connection, read_only=False, timeout_ms=timeout_ms)
            report["connection_identity"] = check_identity(connection, TARGET["import_role"])
            require(connection.execute("SELECT pg_try_advisory_xact_lock(720260108,1)").fetchone() == (True,),
                    "Another M1 B import owns the transaction lock")
            require(not relation_objects(connection), "Business schema is nonempty; existing objects will not be overwritten")
            report["phase"] = "copy"
            report["commit_state"] = "uncommitted"
            copy_tables(connection, manifest, report["copied_tables"])
            report["phase"] = "verify_before_commit"
            candidate = verify_target(connection, manifest, report["validation"])
            check_source_files(manifest)
            report["source_files_unchanged"] = True
            report["candidate_target_data_version"] = candidate
            report["phase"] = "commit"
            report["commit_state"] = "commit_in_progress"
            save_report(output, report)
            attempting_commit = True
        report["commit_state"] = "committed"
        report["target_data_verified"] = True
        report["verified_target_data_version"] = candidate
        report["summary"] = report["validation"]["summary"]
        report["phase"] = "completed"
        report["readonly_independent_validation_pending"] = True
    except BaseException:
        if attempting_commit:
            report["commit_state"] = "unknown"
            report["recovery"] = "Do not rerun import. Run independent validation to establish whether all tables committed."
        else:
            # Psycopg transaction context has attempted rollback at this point.
            from psycopg.pq import TransactionStatus
            idle = not connection.closed and connection.info.transaction_status == TransactionStatus.IDLE
            report["commit_state"] = "rolled_back" if idle else "rollback_not_confirmed"
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    common_arguments(parser)
    parser.add_argument("--output", type=Path, default=BASE / "evaluation/results/m1_b_postgres_import_server.json")
    args = parser.parse_args()
    mode = "import_check_only" if args.check_only else "import"
    report = begin_report(args.output, args.preparation_dir, mode)
    error = None
    try:
        validate_arguments(args)
        report["phase"] = "verify_frozen_source"
        manifest, evidence = load_preparation(args.preparation_dir)
        report["source_preparation"] = evidence
        if args.check_only:
            report.update(phase="source_plan_checked", source_files_unchanged=True,
                          summary={"planned_table_count": 41, "planned_field_count": 276, "planned_row_count": 722732})
        else:
            password = getpass.getpass("Password for askdata_import: ")
            report["phase"] = "connect"
            with connect_driver(args.host, args.port, TARGET["import_role"], password) as connection:
                password = None
                report["postgresql_connected"] = True
                execute_import(connection, manifest, report, args.output, args.statement_timeout_ms)
    except (Exception, KeyboardInterrupt) as exc:
        error = exc
    finish_report(args.output, report, error)
    raise SystemExit(1 if error is not None else 0)


if __name__ == "__main__":
    main()
