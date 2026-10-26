"""Record local unit/input gates and build a whitelisted server sync package."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import platform
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

import psycopg
from scripts.m1_b_postgres_common import BASE, digest_file, load_preparation, require

FILES = [
    "backend/requirements-postgres.txt",
    "backend/scripts/preflight_m1_b_source.py",
    "backend/scripts/m1_b_postgres_common.py",
    "backend/scripts/import_m1_b_postgres.py",
    "backend/scripts/validate_m1_b_postgres.py",
    "backend/scripts/audit_m1_b_import_implementation.py",
    "backend/tests/test_m1_b_postgres.py",
    "backend/evaluation/M1_B_IMPORT_ACCEPTANCE.md",
    "backend/evaluation/M1_B_PREPARATION.md",
    "M1_数据源依赖梳理与最小适配方案.md",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--package", type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), "Audit output already exists")
    require(not args.package or not args.package.exists(), "Sync package already exists")
    require(psycopg.__version__ == "3.2.13", "Install requirements-postgres.txt")
    manifest, source = load_preparation(BASE/"evaluation/results/m1_b_source_server_20261008")
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(BASE/"tests"), pattern="test_m1_b_postgres.py")
    with redirect_stdout(stream):
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    require(result.wasSuccessful() and result.testsRun == 25 and not result.skipped, "Focused tests did not all pass")
    checks = {}
    for mode, filename in [("import_check_only", "m1_b_import_check_local_final.json"),
                           ("validation_check_only", "m1_b_validation_check_local_final.json")]:
        path = BASE/"evaluation/results"/filename
        record = json.loads(path.read_bytes())
        require(record["mode"] == mode and record["run_status"] == "complete" and
                not record["postgresql_connected"] and not record["target_data_verified"], "Invalid input-only evidence")
        checks[mode] = {"file": "evaluation/results/"+filename, "sha256": digest_file(path), "status": "passed"}
    artifacts = {name: digest_file(BASE.parent/name) for name in FILES}
    record = {"stage": "M1 B local import implementation", "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed", "python_version": platform.python_version(), "psycopg_version": psycopg.__version__,
        "source_preparation": source, "source_files_unchanged": True,
        "source_summary": {"table_count": len(manifest["tables"]), "row_count": sum(t["row_count"] for t in manifest["tables"])},
        "unit_tests": {"executed": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
            "scope": "Injected transactions/permissions; actual DuckDB row/statistic oracle with PostgreSQL catalog stubs."},
        "input_only_entry_checks": checks, "implementation_artifact_sha256": artifacts,
        "postgresql_integration_executed": False, "target_data_verified": False,
        "verified_target_data_version": None, "new_model_request_count": 0,
        "pending_gates": ["Server atomic import and commit", "Committed data verification with readonly role", "Actual ACL write denial"]}
    if args.package:
        args.package.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(args.package, "x", compression=ZIP_DEFLATED) as archive:
            for name in FILES:
                archive.write(BASE.parent/name, arcname=name)
        with ZipFile(args.package) as archive:
            require(archive.namelist() == FILES and archive.testzip() is None, "Invalid sync package")
        record["sync_package"] = {"filename": args.package.name, "sha256": digest_file(args.package), "file_count": len(FILES)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(record, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps({"status": record["status"], "test_count": result.testsRun,
        "postgresql_integration_executed": False, "output": str(args.output), "sync_package": record.get("sync_package")},
        ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
