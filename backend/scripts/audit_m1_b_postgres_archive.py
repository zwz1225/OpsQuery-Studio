"""Review downloaded M1 B import/validation evidence without a database connection."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from scripts.m1_b_postgres_common import BASE, TARGET, digest_json, load_preparation, stat_equal


def audit(directory: Path) -> dict:
    manifest, preparation = load_preparation(directory/"m1_b_source_server_20261008")
    paths = {mode: directory/f"m1_b_postgres_{mode}_server.json" for mode in ["import", "validation"]}
    raw = {mode: path.read_bytes() for mode, path in paths.items()}
    reports = {mode: json.loads(data) for mode, data in raw.items()}
    hashes = {mode: hashlib.sha256(data).hexdigest() for mode, data in raw.items()}
    errors, tables, nullable, times = [], [], [], []

    def check(value: bool, reason: str) -> None:
        if not value:
            errors.append(reason)

    summary = {"table_count": 41, "field_count": 276, "row_count": 722732, "relation_count": 53,
               "error_count": 0, "full_typed_row_match_count": 41}
    versions = []
    for mode, report in reports.items():
        check(report["mode"] == mode and report["run_status"] == "complete" and report["phase"] == "completed", mode+": incomplete run")
        check(report["target"] == TARGET and report["postgresql_connected"] and report["target_data_verified"], mode+": target identity/verification")
        check(report["source_preparation"] == preparation and report["source_files_unchanged"], mode+": source evidence differs")
        check(not report["errors"] and report["new_model_request_count"] == 0, mode+": errors/model requests")
        identity = report["connection_identity"]
        expected_identity = {"physical_database": TARGET["physical_database"], "execution_role": TARGET["import_role" if mode == "import" else "query_role"],
                             "server_version": "16.15", "encoding": "UTF8", "timezone": "UTC", "collation": "C", "ctype": "C", "locale_provider": "c"}
        check(identity == expected_identity, mode+": environment/role differs")
        validation = report["validation"]
        check(validation["status"] == "passed" and not validation["errors"] and validation["summary"] == summary, mode+": validation status/summary")
        check({key: report["summary"][key] for key in summary} == summary, mode+": top-level summary differs")
        observed = validation["tables"]
        check([t["name"] for t in observed] == [t["name"] for t in manifest["tables"]], mode+": table list/order differs")
        for table, actual in zip(manifest["tables"], observed):
            prefix = mode+":"+table["name"]
            expected_columns = [{"name": f["name"], "postgresql_type": f["postgresql_type"],
                                 "not_null": f["name"] in table["primary_key"], "identity": "", "generated": "", "has_default": False}
                                for f in table["columns"]]
            check(actual["columns"] == expected_columns and actual["primary_key"] == table["primary_key"], prefix+": physical columns/PK")
            check(actual["owner"] == TARGET["import_role"] and actual["readonly_select_granted"], prefix+": owner/SELECT")
            check(actual["row_count"] == actual["full_row_count"] == table["row_count"], prefix+": row count")
            check(actual["typed_row_multiset_sha256"] == table["typed_row_multiset_sha256"], prefix+": full typed rows")
            check(actual["primary_key_duplicate_groups"] == actual["primary_key_null_rows"] == 0, prefix+": PK values")
            check([f["name"] for f in actual["statistics"]] == [f["name"] for f in table["columns"]], prefix+": statistic columns")
            for field, stats in zip(table["columns"], actual["statistics"]):
                keys = ["null_count", "non_null_distinct_count", "minimum", "maximum"]
                if field["source_type"] in {"BIGINT", "DOUBLE"}: keys += ["sum", "average"]
                for key in keys:
                    value = stats[key]
                    if isinstance(value, str) and key in {"sum", "average"}: value = Decimal(value)
                    check(stat_equal(value, field[key], field["source_type"], key, manifest["floating_aggregate_comparison"]),
                          prefix+":"+field["name"]+":"+key)
                if mode == "validation" and field["null_count"]:
                    nullable.append({"table": table["name"], "column": field["name"], "null_count": stats["null_count"]})
                if field["source_type"] == "TIMESTAMP":
                    precision = actual["timestamp_value_precision"][field["name"]]
                    # This frozen dataset has whole-second values. Microsecond loss is
                    # additionally covered by a separate synthetic implementation test.
                    check(field["fractional_value_count"] == field["max_fractional_digits"] == 0 and
                          precision["nonzero_microsecond_count"] == precision["max_significant_fractional_digits"] == 0,
                          prefix+":"+field["name"]+": timestamp precision")
                    if mode == "validation": times.append({"table": table["name"], "column": field["name"], **precision})
            if mode == "validation":
                tables.append({"name": table["name"], "rows": table["row_count"], "fields": len(table["columns"]),
                               "typed_row_multiset_sha256": actual["typed_row_multiset_sha256"]})
        relations = [{"parent": r["left_table_name"], "child": r["right_table_name"], "child_column": r["right_field"],
                      "unmatched_non_null_child_rows": r["unmatched_non_null_child_rows"]} for r in manifest["business_relations"]]
        check(validation["relations"] == relations, mode+": business relations differ")
        version = digest_json({"target": TARGET, "tables": [{key: t[key] for key in
            ["name", "columns", "primary_key", "row_count", "typed_row_multiset_sha256"]} for t in observed]})
        check(version == report["verified_target_data_version"] == validation["verified_snapshot_data_version"], mode+": recomputed target version differs")
        versions.append(version)
    imported, validated = reports["import"], reports["validation"]
    check(imported["commit_state"] == "committed" and imported["candidate_target_data_version"] == versions[0], "Import commit/candidate")
    check(validated["commit_state"] == "not_started", "Validation unexpectedly committed writes")
    check(versions[0] == versions[1], "Pre/post commit target versions differ")
    expected_copy = [{"name": t["name"], "copy_row_count": t["row_count"], "csv_bytes_sent": (BASE/t["csv_relative_path"]).stat().st_size,
                      "sent_csv_sha256": t["csv_sha256"]} for t in manifest["tables"]]
    check(imported["copied_tables"] == expected_copy, "COPY counts/bytes/hashes differ")
    expected_import_record = {"sha256": hashes["import"], "commit_state": "committed", "expected_target_data_version": versions[0], "recovery_of_unknown_commit": False}
    check(validated["import_record"] == expected_import_record, "Independent validation import-reference hash/version differs")
    check(datetime.fromisoformat(imported["finished_at"]) <= datetime.fromisoformat(validated["started_at"]), "Independent validation did not start after import completion")
    acl = validated["readonly_acl"]
    check(acl["status"] == "passed" and acl["database_schema_grants"] == [True, False, False, True, False, False], "Readonly database/schema ACL differs")
    expected_grants = {key: key == "SELECT" for key in ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]}
    check(acl["tables"] == [{"name": t["name"], "grants": expected_grants} for t in manifest["tables"]], "Readonly table ACL differs")
    probes = validated["write_denial_probes"]
    check(probes == {"status": "passed", "read_write_transaction_used": True, "all_probe_changes_rolled_back": True,
                     "connection_recovered": True, "checks": [{"operation": op, "sqlstate": "42501", "permission_denied": True}
                     for op in ["insert", "update", "delete", "create_table"]]}, "Actual write-denial probes differ")
    check(validated["summary"] == {**summary, "readonly_table_select_count": 41, "actual_write_denial_count": 4,
                                  "actual_write_denial_sqlstate": "42501"}, "Readonly summary differs")
    for mode, path in paths.items(): check(path.read_bytes() == raw[mode], mode+": report changed during review")
    return {"stage": "M1 B downloaded PostgreSQL import/validation review", "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not errors else "failed", "errors": errors, "summary": validated["summary"],
        "source_preparation": preparation, "server_report_sha256": hashes,
        "verified_target_data_version": versions[1], "import_reference_bytes_match": validated["import_record"]["sha256"] == hashes["import"],
        "raw_reports_preserved": True, "import_pending_flag_superseded_by_independent_validation": imported.get("readonly_independent_validation_pending") is True,
        "tables": tables, "nullable_columns": nullable, "timestamp_columns": times,
        "csv_bytes": sum(t["csv_bytes_sent"] for t in expected_copy),
        "run_windows": {mode: {"started_at": r["started_at"], "finished_at": r["finished_at"],
            "elapsed_seconds": round((datetime.fromisoformat(r["finished_at"])-datetime.fromisoformat(r["started_at"])).total_seconds(), 6)} for mode, r in reports.items()},
        "review_connected_to_postgresql": False, "review_executed_sql": False, "new_model_request_count": 0,
        "scope": "Offline review of server snapshot evidence; not a live PostgreSQL state check or application-adapter acceptance."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=BASE/"evaluation/results")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError("Use a new archive-review output")
    record = audit(args.results_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: record[key] for key in ["status", "errors", "summary", "verified_target_data_version", "run_windows"]}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if record["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
