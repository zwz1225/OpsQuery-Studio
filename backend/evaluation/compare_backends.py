"""Compare actual Gold rows across DuckDB/PostgreSQL; never a regression score.

Requires current manifests, embedded result evidence and accepted M1 B data
equivalence. Different native data/catalog/SQL identities are recorded, not
silently treated as identical. No model or database connection is opened.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from app.datasources.postgres_config import PostgresConfig, load_recorded_source, read_record
from app.security import AccessController
from evaluation.gold_sql import gold_selection_identity, select_gold_sql
from evaluation.gold_result import GOLD_CACHE_VERSION
from evaluation.report_identity import validate_report_identity
from evaluation.result_policy import evidence_digest, policy_identity, result_policy, valid_result
from evaluation.run_manifest import _digest


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_data_equivalence(import_path: Path, validation_path: Path) -> dict:
    report, _ = read_record(validation_path, "M1 B validation evidence")
    version = report.get("verified_target_data_version")
    config = PostgresConfig(host="offline-evidence", port=55432, database="askdata_m1_test",
        schema="askdata_ops", user="askdata_readonly", password="", source_id="short_video_ops_postgres",
        connect_timeout_seconds=10, statement_timeout_ms=120000, lock_timeout_ms=5000,
        pool_min_size=1, pool_max_size=4, pool_wait_timeout_seconds=10, pool_max_waiting=16,
        verified_data_version=version, import_report_path=import_path.resolve(),
        validation_report_path=validation_path.resolve())
    # This recomputes/validates the full recorded import + target table digests,
    # structure, ACL and canonical import spec. It opens no database connection.
    recorded = load_recorded_source(config)
    return {"kind": "accepted_M1_B_import_and_validation", "validation_evidence_verified": True,
        "logical_database_id": config.source_id.removesuffix("_postgres"),
        "postgres_source_id": config.source_id, "postgres_physical_schema": config.schema,
        "duckdb_data_version": report["source_preparation"]["source_data_version"],
        "postgres_data_version": config.verified_data_version,
        "postgres_physical_schema_version": recorded.physical_schema_version,
        "import_report_sha256": recorded.import_report_sha256,
        "validation_report_sha256": recorded.validation_report_sha256}


def _read(value):
    return json.loads(Path(value).read_text(encoding="utf-8")) if isinstance(value, (str, Path)) else value


def _raw_evidence(row: dict, manifest: dict, case: dict) -> dict:
    evidence = (row.get("result_metrics") or {}).get("gold_result_evidence")
    require(isinstance(evidence, dict), "Missing embedded Gold result evidence; use fresh D4 Gold reports")
    require(evidence.get("sha256") == evidence_digest({k: v for k, v in evidence.items() if k != "sha256"}),
            "Gold result evidence checksum differs")
    require(evidence.get("gold_cache_version") == GOLD_CACHE_VERSION, "Gold evidence cache format differs")
    source = manifest["source_identity"]
    selection = select_gold_sql(case, source).public()
    require(evidence.get("source_identity") == source and evidence.get("data_version") == source["data_version"],
            "Gold result evidence datasource differs")
    require(evidence.get("case_id") == case["case_id"] and evidence.get("question") == case["query"]
            and evidence.get("scenario") == case["scenario"] and evidence.get("database") == source["logical_database_id"],
            "Gold evidence case identity differs")
    require(evidence.get("gold_selection") == selection and evidence.get("gold_sql") == selection["sql"]
            and row.get("generated_sql") == selection["sql"], "Gold evidence selected SQL differs")
    require(evidence.get("scope") == AccessController().resolve(f"demo_{case['scenario']}").public(),
            "Gold evidence permissions differ")
    require(evidence.get("result_policy") == result_policy(case) and evidence.get("max_result_rows") == 10000,
            "Gold evidence result policy differs")
    require(evidence.get("result_source") in ("execution", "cache")
            and row.get("gold_result_source") == evidence["result_source"] and row.get("sql_execution_success") is True,
            "Cross-backend comparison requires actual successful Gold results")
    require(valid_result(evidence.get("columns"), evidence.get("rows"), 10000), "Gold result rows/columns invalid")
    require((row.get("result_metrics") or {}).get("gold_result_rows") == len(evidence["rows"]),
            "Gold evidence row count differs from report")
    return evidence


def _strict(columns, rows, expected_columns, expected_rows, case):
    # Import only for comparison; this never invokes a runner/model/executor.
    from evaluation.run_benchmark import compare_results_strict
    return compare_results_strict(columns, rows, expected_columns, expected_rows,
        bool(case.get("order_sensitive", True)), order_by_column=case.get("order_by_column"),
        column_aliases=case.get("column_aliases"), allowed_auxiliary_columns=case.get("allowed_auxiliary_columns"),
        top_n_tie_policy=case.get("top_n_tie_policy"))


class BackendResultComparator:
    @staticmethod
    def compare(duckdb_report, postgres_report, cases: list[dict[str, Any]], data_equivalence: dict) -> dict:
        left, right = _read(duckdb_report), _read(postgres_report)
        manifests = [validate_report_identity(r) for r in (left, right)]
        require(data_equivalence.get("validation_evidence_verified") is True, "Data equivalence evidence is required")
        expected_ids = [c["case_id"] for c in cases]
        require(len(set(expected_ids)) == len(expected_ids) and expected_ids, "Duplicate/empty comparison cases")
        for report, manifest, backend in zip((left, right), manifests, ("duckdb", "postgresql")):
            source = manifest["source_identity"]
            require(report.get("run_status") == "complete" and manifest["manifest_version"] == 4
                    and manifest["mode"] == "gold", "Use complete D4 Gold reports")
            require(source["backend"] == backend and source["logical_database_id"] == data_equivalence["logical_database_id"],
                    "Wrong backend or logical database for comparison")
            require(source["data_version"] == data_equivalence["duckdb_data_version" if backend == "duckdb" else "postgres_data_version"],
                    "Report data version differs from verified equivalent data")
            require(manifest["dataset"]["case_ids"] == expected_ids and manifest["dataset"]["version"] == _digest(cases),
                    "Cross-backend reports need the same frozen cases")
            require(manifest.get("gold_selection") == gold_selection_identity(cases, source), "Wrong explicit Gold selection")
            require(manifest.get("result_policy") == policy_identity(cases), "Cross-backend result policy differs")
        postgres_source = manifests[1]["source_identity"]
        require(postgres_source["source_id"] == data_equivalence["postgres_source_id"]
                and postgres_source["physical_schema"] == data_equivalence["postgres_physical_schema"]
                and manifests[1]["versions"].get("physical_schema") == data_equivalence["postgres_physical_schema_version"],
                "PostgreSQL report differs from accepted physical target")
        for key in ("application", "evaluator", "evaluation_code", "result_policy"):
            require(manifests[0]["versions"].get(key) and manifests[0]["versions"][key] == manifests[1]["versions"].get(key),
                    "Cross-backend code/result policy versions differ: " + key)
        require(manifests[0]["config"].get("user_roles") == manifests[1]["config"].get("user_roles"),
                "Cross-backend report roles differ")
        rows = []
        for case, old, new in zip(cases, left["cases"], right["cases"]):
            before, after = _raw_evidence(old, manifests[0], case), _raw_evidence(new, manifests[1], case)
            pair_ok, pair_reason = _strict(after["columns"], after["rows"], before["columns"], before["rows"], case)
            old_ok, old_reason = _strict(before["columns"], before["rows"], case["expected_columns"], case["expected_rows"], case)
            new_ok, new_reason = _strict(after["columns"], after["rows"], case["expected_columns"], case["expected_rows"], case)
            row = {"case_id": case["case_id"], "pair_correct": pair_ok, "pair_reason": pair_reason,
                "duckdb_expected_correct": old_ok, "postgres_expected_correct": new_ok,
                "duckdb_expected_reason": old_reason, "postgres_expected_reason": new_reason,
                "duckdb_row_count": len(before["rows"]), "postgres_row_count": len(after["rows"]),
                "raw_rows_identical": before["columns"] == after["columns"] and before["rows"] == after["rows"],
                "reported_scores_match_replay": old.get("strict_result_correct") == old_ok and new.get("strict_result_correct") == new_ok,
                "duckdb_evidence_sha256": before["sha256"], "postgres_evidence_sha256": after["sha256"]}
            if not all((pair_ok, old_ok, new_ok)):
                row.update(duckdb_columns=before["columns"], postgres_columns=after["columns"],
                           duckdb_rows=before["rows"], postgres_rows=after["rows"])
            rows.append(row)
        passed = all(r["pair_correct"] and r["duckdb_expected_correct"] and r["postgres_expected_correct"]
                     and r["reported_scores_match_replay"] for r in rows)
        return {"report_type": "cross_backend_gold_result_consistency", "comparison_version": 1,
            "run_status": "complete", "comparison_status": "passed" if passed else "failed",
            "created_at": datetime.now(timezone.utc).isoformat(), "case_count": len(rows),
            "pair_pass_count": sum(r["pair_correct"] for r in rows),
            "duckdb_expected_pass_count": sum(r["duckdb_expected_correct"] for r in rows),
            "postgres_expected_pass_count": sum(r["postgres_expected_correct"] for r in rows),
            "raw_rows_identical_count": sum(r["raw_rows_identical"] for r in rows),
            "reported_scores_match_replay_count": sum(r["reported_scores_match_replay"] for r in rows),
            "sources": [m["source_identity"] for m in manifests], "run_ids": [m["run_id"] for m in manifests],
            "input_report_content_sha256": [evidence_digest(r) for r in (left, right)],
            "data_equivalence": data_equivalence, "new_model_request_count": 0,
            "database_connections_opened_by_comparator": 0, "is_same_source_regression": False,
            "comparison_rules": "Existing explicit aliases, business tolerance, order and approved Top-N ties",
            "cases": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duckdb-report", type=Path, required=True)
    parser.add_argument("--postgres-report", type=Path, required=True)
    parser.add_argument("--cases", type=Path, default=Path(__file__).parent / "cases/all_cases.jsonl")
    parser.add_argument("--case-list", type=Path, required=True)
    parser.add_argument("--import-evidence", type=Path, required=True)
    parser.add_argument("--validation-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "Output exists; choose an independent comparison report filename")
    from evaluation.case_selection import select_cases, load_case_ids
    cases = select_cases([json.loads(l) for l in args.cases.read_text(encoding="utf-8").splitlines() if l.strip()],
                         load_case_ids(args.case_list))
    pair = load_data_equivalence(args.import_evidence, args.validation_evidence)
    report = BackendResultComparator.compare(args.duckdb_report, args.postgres_report, cases, pair)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("cases", "data_equivalence", "sources")}, indent=2))
    if report["comparison_status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
