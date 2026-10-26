"""Independently verify committed M1 B data with the readonly database account."""
from __future__ import annotations

import argparse
import getpass
import hashlib
import json
from pathlib import Path

from scripts.m1_b_postgres_common import (
    APPROVED_SPEC, BASE, TARGET, begin_report, check_identity, check_readonly_acl, check_source_files,
    common_arguments, configure_transaction, connect_driver, finish_report, load_preparation,
    require, validate_arguments, verify_target, write_denial_probes,
)


def load_import_record(path: Path) -> dict:
    data = path.read_bytes()
    record = json.loads(data)
    require(record["mode"] == "import" and record["target"] == TARGET, "Not a matching PostgreSQL import record")
    require(record["source_preparation"]["canonical_import_spec_sha256"] == APPROVED_SPEC, "Import record uses a different specification")
    committed = record["run_status"] == "complete" and record["commit_state"] == "committed"
    # commit_in_progress can remain on disk after abrupt process termination.
    recovering = record["commit_state"] in {"unknown", "commit_in_progress"}
    require(committed or recovering, "Import was not committed or in an unknown-commit recovery state")
    expected_version = record.get("verified_target_data_version") or record.get("candidate_target_data_version")
    require(isinstance(expected_version, str) and len(expected_version) == 64, "Import record lacks verified candidate data version")
    return {"sha256": hashlib.sha256(data).hexdigest(), "commit_state": record["commit_state"],
            "expected_target_data_version": expected_version, "recovery_of_unknown_commit": recovering}


def execute_validation(connection, manifest: dict, report: dict, timeout_ms: int) -> None:
    report.update(phase="verify_readonly_snapshot", validation={}, write_denial_probes={})
    with connection.transaction():
        configure_transaction(connection, read_only=True, timeout_ms=timeout_ms)
        report["connection_identity"] = check_identity(connection, TARGET["query_role"])
        require(connection.execute("SHOW default_transaction_read_only").fetchone() == ("on",),
                "Readonly role default transaction setting differs")
        report["readonly_acl"] = check_readonly_acl(connection, manifest)
        version = verify_target(connection, manifest, report["validation"])
    # Actual denial probes run separately and always roll back. No table data is changed.
    report["phase"] = "verify_write_denial"
    write_denial_probes(connection, manifest["tables"][0], report["write_denial_probes"])
    check_source_files(manifest)
    if "import_record" in report:
        require(version == report["import_record"]["expected_target_data_version"], "Committed target data version differs from import verification")
    report.update(phase="completed", source_files_unchanged=True, target_data_verified=True,
        verified_target_data_version=version, summary={**report["validation"]["summary"],
            "readonly_table_select_count": len(report["readonly_acl"]["tables"]),
            "actual_write_denial_count": len(report["write_denial_probes"]["checks"]),
            "actual_write_denial_sqlstate": "42501"},
        validation_scope="One repeatable-read snapshot. Revalidate after any target/schema changes; not a live mutation monitor.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    common_arguments(parser)
    parser.add_argument("--import-report", type=Path)
    parser.add_argument("--output", type=Path, default=BASE / "evaluation/results/m1_b_postgres_validation_server.json")
    args = parser.parse_args()
    report = begin_report(args.output, args.preparation_dir, "validation_check_only" if args.check_only else "validation")
    error = None
    try:
        validate_arguments(args)
        report["phase"] = "verify_frozen_source"
        manifest, evidence = load_preparation(args.preparation_dir)
        report["source_preparation"] = evidence
        if args.import_report:
            report["import_record"] = load_import_record(args.import_report)
        if args.check_only:
            report.update(phase="source_plan_checked", source_files_unchanged=True,
                          summary={"planned_table_count": 41, "planned_field_count": 276, "planned_row_count": 722732})
        else:
            password = getpass.getpass("Password for askdata_readonly: ")
            report["phase"] = "connect"
            with connect_driver(args.host, args.port, TARGET["query_role"], password) as connection:
                password = None
                report["postgresql_connected"] = True
                execute_validation(connection, manifest, report, args.statement_timeout_ms)
    except (Exception, KeyboardInterrupt) as exc:
        error = exc
    finish_report(args.output, report, error)
    raise SystemExit(1 if error is not None else 0)


if __name__ == "__main__":
    main()
