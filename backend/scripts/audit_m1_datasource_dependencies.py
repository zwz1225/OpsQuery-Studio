"""Read-only M1 dependency inventory; never loads app settings or a database.

Run from backend: python -m scripts.audit_m1_datasource_dependencies
The output describes inspected source, not PostgreSQL execution or migration.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


BASE_DIR = Path(__file__).resolve().parents[1]
PATTERNS = {
    "concrete_executor": r"DuckDbEngine|duckdb\.connect",
    "csv_execution": r"read_csv_auto|glob\([\"']\*\.csv",
    "static_catalog": r"from .*database import .*\b(?:SCHEMA|RELATIONS)\b",
    "dialect_parser": r"(?:read|dialect)=[\"']duckdb[\"']",
    "duckdb_prompt": r"DuckDB",
    "static_index_version": r"csv_duckdb_v1|schema_store\.json",
    "logical_database_literal": r"[\"']short_video_ops[\"']",
}
GOLD_FEATURES = {
    "strftime": r"\bstrftime\s*\(",
    "date_trunc": r"\bdate_trunc\s*\(",
    "interval": r"\bINTERVAL\b",
    "division_operator": r"/",
    "cast": r"\bCAST\s*\(",
    "order_by": r"\bORDER\s+BY\b",
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def file_identity(path: Path) -> dict:
    return {
        "path": path.relative_to(BASE_DIR).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def build_inventory() -> dict:
    folder = BASE_DIR / "data" / "databases" / "short_video_ops"
    schema_path = folder / "_schema.json"
    manifest_path = folder / "_database_manifest.json"
    cases_path = BASE_DIR / "evaluation" / "cases" / "all_cases.jsonl"
    schema = read_json(schema_path)
    manifest = read_json(manifest_path)
    cases = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    tables = schema["tables"]
    fields = [field for table in tables for field in table["fields"]]
    source_files = sorted([
        *(BASE_DIR / "app").rglob("*.py"),
        *(BASE_DIR / "app" / "skills").rglob("SKILL.md"),
        *(BASE_DIR / "app" / "skills").rglob("config.json"),
        *(BASE_DIR / "evaluation").glob("*.py"),
        *(BASE_DIR / "scripts").glob("*.py"),
        BASE_DIR / "requirements.txt",
    ])
    source_files = [p for p in source_files if p.resolve() != Path(__file__).resolve()]
    matches = []
    for path in source_files:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            categories = [name for name, pattern in PATTERNS.items() if re.search(pattern, line)]
            if categories:
                matches.append({"path": path.relative_to(BASE_DIR).as_posix(),
                                "line": line_number, "categories": categories,
                                "source": line.strip()})
    features = {}
    for name, pattern in GOLD_FEATURES.items():
        ids = [case["case_id"] for case in cases
               if re.search(pattern, case.get("gold_sql") or "", re.I)]
        features[name] = {"case_count": len(ids), "case_ids": ids}
    table_ids = {table["id"] for table in tables}
    relation_issues = []
    for relation in schema["relations"]:
        for side in ("left", "right"):
            table_id = relation[f"{side}_table"]
            field_name = relation[f"{side}_field"]
            table = next((item for item in tables if item["id"] == table_id), None)
            if table is None or field_name not in {f["name"] for f in table["fields"]}:
                relation_issues.append({"table_id": table_id, "field": field_name})
    csv_files = sorted(folder.glob("*.csv"))
    data_files = sorted([schema_path, *csv_files])
    return {
        "audit_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "M1 step 1: static dependency audit and adaptation design",
        "database_connected": False,
        "runtime_behavior_changed": False,
        "summary": {
            "table_count": len(tables), "field_count": len(fields),
            "relation_count": len(schema["relations"]),
            "csv_file_count": len(csv_files),
            "declared_total_rows": manifest["total_rows"],
            "schema_declared_total_rows": sum(t.get("row_count", 0) for t in tables),
            "case_count": len(cases), "classic_case_count": sum(bool(c.get("classic")) for c in cases),
            "source_types": dict(sorted(Counter(f.get("source_type", "") for f in fields).items())),
            "business_types": dict(sorted(Counter(f.get("type", "") for f in fields).items())),
            "fields_with_stored_profile": sum(isinstance(f.get("data_profile"), dict) for f in fields),
            "fields_with_index_content": sum(bool(f.get("index_content")) for f in fields),
            "fields_with_declared_nulls": sum(
                float((f.get("data_profile") or {}).get("null_ratio", 0)) > 0 for f in fields),
            "prebuilt_only_tables": sum(all(f.get("data_profile") and f.get("index_content")
                                            for f in t["fields"]) for t in tables),
            "dependency_hit_count": len(matches),
            "dependency_file_count": len({m["path"] for m in matches}),
        },
        "checks": {
            "unique_logical_table_ids": len(table_ids) == len(tables),
            "manifest_table_count_matches": manifest["table_count"] == len(tables),
            "manifest_rows_match_schema": manifest["total_rows"] == sum(t.get("row_count", 0) for t in tables),
            "csv_names_match_catalog": {p.stem for p in csv_files} == {t.get("name") for t in tables},
            "relation_fields_exist": not relation_issues,
        },
        "limitations": [
            "Counts and null information come from stored metadata, not a recount of all CSV records.",
            "Pattern matches are navigation evidence, not an exhaustive semantic dependency analysis.",
            "No PostgreSQL connection, type conversion, SQL execution, or migration has been verified.",
        ],
        "gold_sql_features": features,
        "source_files": [file_identity(p) for p in source_files],
        "data_files": [file_identity(p) for p in data_files],
        "input_files": [file_identity(p) for p in (manifest_path, cases_path)],
        "dependency_matches": matches,
        "relation_issues": relation_issues,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=BASE_DIR / "evaluation" / "results" / "m1_datasource_dependency_audit.json")
    args = parser.parse_args()
    payload = build_inventory()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "summary": payload["summary"],
                      "checks": payload["checks"]}, ensure_ascii=False, indent=2))
    if not all(payload["checks"].values()):
        raise SystemExit("Static catalog consistency check failed; inspect the audit report")


if __name__ == "__main__":
    main()
