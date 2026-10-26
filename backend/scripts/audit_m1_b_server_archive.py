"""Compare downloaded server source-preparation evidence with local verified artifacts."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from scripts.preflight_m1_b_source import BASE, BASELINE_DATA_VERSION, TARGET, digest_file


NAMES = ["source_preflight.json", "import_manifest.json", "preparation_review.json"]


def digest_json(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def compare(server_dir: Path, local_dir: Path) -> dict:
    originals = {(side, name): (directory / name).read_bytes()
                 for side, directory in [("server", server_dir), ("local", local_dir)] for name in NAMES}
    loaded = {side: {name: json.loads(originals[side, name]) for name in NAMES} for side in ["server", "local"]}
    errors = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    server, local = loaded["server"], loaded["local"]
    preflight, manifest, review = [server[name] for name in NAMES]
    for side, evidence in loaded.items():
        report, specification, audit = [evidence[name] for name in NAMES]
        check(report["status"] == audit["status"] == "passed", side + ": unsuccessful preparation")
        check(report["errors"] == report["warnings"] == [], side + ": source errors/warnings")
        check(report["source_files_unchanged"] and not report["postgresql_connected"] and
              report["new_model_request_count"] == 0, side + ": unexpected source/external activity")
        check(report["source"]["data_version"] == report["source"]["expected_data_version"] == BASELINE_DATA_VERSION,
              side + ": data version differs from M1 A")
        check(specification["source"] == report["source"] and specification["target"] == TARGET,
              side + ": manifest source/target identity differs")
        check(digest_json(specification) == report["import_spec_sha256"], side + ": manifest fingerprint invalid")
        check(not specification["target_data_verified"] and specification["verified_target_data_version"] is None,
              side + ": preparation incorrectly claims target verification")
        for name in NAMES[:2]:
            check(hashlib.sha256(originals[side, name]).hexdigest() == audit["input_artifact_sha256"][name],
                  side + ": downloaded artifact hash differs from recorded hash: " + name)
        check(audit["summary"] == report["summary"], side + ": review summary differs from source scan")
        check(audit["all_typed_row_digests_match"] and audit["format_precision_probe_passed"] and
              audit["source_files_unchanged"] and audit["postgresql_ddl_parsed_table_count"] == 41,
              side + ": preparation review checks did not pass")
    check(manifest == local["import_manifest.json"], "Local/server canonical import manifest differs")
    check({key: value for key, value in preflight.items() if key != "created_at"} ==
          {key: value for key, value in local["source_preflight.json"].items() if key != "created_at"},
          "Local/server full source scan differs beyond run timestamp")
    check({key: value for key, value in review.items() if key not in {"reviewed_at", "input_artifact_sha256"}} ==
          {key: value for key, value in local["preparation_review.json"].items()
           if key not in {"reviewed_at", "input_artifact_sha256"}}, "Local/server review checks differ")
    file_checks = []
    for name, expected in preflight["source"]["files_sha256"].items():
        actual = digest_file(BASE / "data/databases/short_video_ops" / name)
        matches = actual == expected == local["source_preflight.json"]["source"]["files_sha256"].get(name)
        check(matches, "Current local/server source file differs: " + name)
        file_checks.append({"name": name, "sha256": expected, "current_local_server_equal": matches})
    table_checks = []
    local_tables = {table["name"]: table for table in local["source_preflight.json"]["tables"]}
    check(len(preflight["tables"]) == len(local_tables) == 41, "Wrong table count")
    for table in preflight["tables"]:
        counterpart = local_tables[table["name"]]
        equal = table == counterpart
        row_equal = table["typed_row_multiset_sha256"] == table["raw_typed_row_multiset_sha256"] == counterpart["typed_row_multiset_sha256"]
        check(equal and row_equal, "Local/server table content/statistics differ: " + table["name"])
        table_checks.append({"name": table["name"], "row_count": table["row_count"],
                             "field_count": len(table["columns"]), "all_column_statistics_equal": equal,
                             "typed_row_multiset_equal": row_equal, "csv_sha256_equal": table["csv_sha256"] == counterpart["csv_sha256"]})
    # The server SQL file was not downloaded. Its recorded hash can still be
    # checked against the local generated DDL with Linux line endings.
    local_ddl = (local_dir / "create_tables.sql").read_bytes()
    check(hashlib.sha256(local_ddl).hexdigest() == local["preparation_review.json"]["input_artifact_sha256"]["create_tables.sql"],
          "Local DDL bytes differ from reviewed artifact")
    server_ddl_expected = hashlib.sha256(local_ddl.replace(b"\r\n", b"\n")).hexdigest()
    check(server_ddl_expected == review["input_artifact_sha256"]["create_tables.sql"],
          "Server recorded DDL hash differs from equivalent local Linux-newline DDL")
    import_bytes_equal_after_newlines = (originals["server", "import_manifest.json"] ==
                                        originals["local", "import_manifest.json"].replace(b"\r\n", b"\n"))
    check(import_bytes_equal_after_newlines, "Import manifest byte differences exceed line endings")
    for (side, name), before in originals.items():
        directory = server_dir if side == "server" else local_dir
        check((directory / name).read_bytes() == before, "Review input changed: " + side + "/" + name)
    return {"stage": "M1 B server source preparation archive review", "status": "passed" if not errors else "failed",
            "reviewed_at": datetime.now(timezone.utc).isoformat(), "errors": errors,
            "source_data_version": preflight["source"]["data_version"],
            "source_catalog_version": preflight["source"]["catalog_version"],
            "canonical_import_spec_sha256": preflight["import_spec_sha256"],
            "server_input_sha256": {name: hashlib.sha256(originals["server", name]).hexdigest() for name in NAMES},
            "local_input_sha256": {name: hashlib.sha256(originals["local", name]).hexdigest() for name in NAMES},
            "summary": {"source_file_count": len(file_checks), "table_count": len(table_checks),
                        "field_count": sum(row["field_count"] for row in table_checks),
                        "row_count": sum(row["row_count"] for row in table_checks),
                        "relation_count": len(preflight["relations"]), "error_count": len(errors),
                        "columns_with_null": preflight["summary"]["columns_with_null"]},
            "canonical_manifests_identical": manifest == local["import_manifest.json"],
            "manifest_bytes_identical_after_newline_normalization": import_bytes_equal_after_newlines,
            "server_recorded_ddl_hash_matches_local_linux_newlines": server_ddl_expected == review["input_artifact_sha256"]["create_tables.sql"],
            "source_file_checks": file_checks, "table_checks": table_checks,
            "downloaded_reports_unchanged": True, "postgresql_connected": False,
            "limits": ["Server create_tables.sql was not downloaded; checked its recorded hash against equivalent local DDL.",
                       "Source preparation is verified. PostgreSQL import, target values and table read/write permissions remain unverified."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-dir", type=Path, default=BASE / "evaluation/results/m1_b_source_server_20261008")
    parser.add_argument("--local-dir", type=Path, default=BASE / "evaluation/results/m1_b_source_local_v2")
    parser.add_argument("--output", type=Path, default=BASE / "evaluation/results/m1_b_server_source_archive_review.json")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Archive review exists; choose a new output path to preserve it")
    result = compare(args.server_dir.resolve(), args.local_dir.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ["status", "summary", "canonical_import_spec_sha256",
          "canonical_manifests_identical", "manifest_bytes_identical_after_newline_normalization",
          "server_recorded_ddl_hash_matches_local_linux_newlines", "errors"]}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
