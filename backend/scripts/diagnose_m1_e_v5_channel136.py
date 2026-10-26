"""Replay CHANNEL_OPS-136's v5 PostgreSQL failure and verified repair."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from app.config import BASE_DIR, settings
from app.datasources import create_datasource_runtime
from app.querying.sql_validator import SQLValidator
from app.security import AccessController
from evaluation.gold_result import resolve_gold_result
from evaluation.report_identity import validate_report_identity
from evaluation.run_benchmark import compare_results, load_cases, summarize
from evaluation.run_manifest import _digest, build_run_manifest
from scripts.rescore_m1_e_v3_strict import require, sha256, strict


RESULTS = BASE_DIR / "evaluation/results"
CASES = BASE_DIR / "evaluation/cases/all_cases.jsonl"
SOURCE = RESULTS / "m1_e_postgres_live_phase83_server_v5.json"
FORMAL_SHA256 = "ff5956e9f4aca878ee63e232bdea1fef3416a28eda72669f91a33546c70f3adc"
SOURCE_SHA256 = "41a2670f7dc5fd6cc490149d36d4fe9cd2f2b2c9239f278446b6c9560cf18af6"
SOURCE_RUN_ID = "9102289c2003472dbbe2e39a2ef9996f"
SQL_SHA256 = "e8c07dd1a966eb9181d576f03b8b377ad6a5be11b1a2dcd0439a6289614becbd"
CASE_ID = "CHANNEL_OPS-136"


def preflight() -> tuple[dict, dict, dict]:
    require(sha256(CASES) == FORMAL_SHA256, "Formal cases differ from v5")
    require(sha256(SOURCE) == SOURCE_SHA256, "v5 phase83 report differs")
    report = json.loads(SOURCE.read_text(encoding="utf-8"))
    manifest = validate_report_identity(report)
    require(
        report["run_status"] == "complete"
        and manifest["run_id"] == SOURCE_RUN_ID
        and manifest["mode"] == "live"
        and manifest["scope"] == "all"
        and len(report["cases"]) == 30
        and report["summary"] == summarize(report["cases"], "live")
        and manifest["source_identity"]["source_id"] == "short_video_ops_postgres"
        and manifest["source_identity"]["backend"] == "postgresql",
        "v5 phase83 source or summary differs",
    )
    cases = load_cases(CASES, set(), False)
    by_id = {case["case_id"]: case for case in cases}
    require(len(cases) == len(by_id) == 430, "Formal case count differs")
    selected = [by_id[case_id] for case_id in manifest["dataset"]["case_ids"]]
    require(_digest(selected) == manifest["dataset"]["version"],
            "v5 phase83 dataset differs from formal cases")
    row = next(item for item in report["cases"] if item["case_id"] == CASE_ID)
    require(
        hashlib.sha256(row["generated_sql"].encode("utf-8")).hexdigest() == SQL_SHA256
        and row["sql_execution_success"] is False
        and row["result_correct"] is False
        and row["strict_result_correct"] is False
        and "42703" in row["comparison_reason"]
        and row["query_contract"]["constraint_validation"]["status"] == "PASS"
        and not row["query_contract"]["constraint_validation"]["warnings"],
        "Reviewed CHANNEL_OPS-136 v5 failure differs",
    )
    return report, row, by_id[CASE_ID]


def diagnose(output: Path) -> dict:
    require(not output.exists() and output.resolve() not in {CASES.resolve(), SOURCE.resolve()},
            "Choose a new output path and preserve source evidence")
    report, row, case = preflight()
    identity = report["run_manifest"]["source_identity"]
    with create_datasource_runtime(settings) as runtime:
        require(runtime.identity.public() == identity
                and runtime.metadata.verification["physical_schema_version"] ==
                    report["run_manifest"]["versions"]["physical_schema"],
                "Live PostgreSQL source differs from v5")
        manifest = build_run_manifest(
            [case], base_dir=BASE_DIR, mode="diagnostic",
            scope="m1_e_v5_channel136", case_source=CASES, runtime=runtime,
            config={"operation": "saved_sql_postgres_replay", "new_model_request_count": 0,
                    "source_run_id": SOURCE_RUN_ID},
        )
        validator = SQLValidator(runtime=runtime)
        graph = {"source_identity": identity}
        before = validator.validate(row["generated_sql"], identity["logical_database_id"], graph)
        require(before.status == "BLOCK" and len(before.errors) == 1 and
                "PostgreSQL ORDER BY expression cannot use SELECT alias target_gap"
                in before.errors[0], "Expected nested ORDER BY alias was not identified")
        repaired_sql = validator.repair_postgres_nested_order_aliases(
            row["generated_sql"], identity["logical_database_id"], graph,
        )
        after = validator.validate(repaired_sql, identity["logical_database_id"], graph)
        require(repaired_sql != row["generated_sql"] and after.status == "PASS",
                "Deterministic PostgreSQL repair did not validate")
        scope = AccessController().resolve("demo_channel_ops")
        failed = runtime.executor.execute(identity["logical_database_id"],
                                          row["generated_sql"], scope, row_limit=10000)
        require(not failed.success and "42703" in str(failed.error),
                "Original SQL no longer reproduces SQLSTATE 42703")
        actual = runtime.executor.execute(identity["logical_database_id"],
                                          repaired_sql, scope, row_limit=10000)
        require(actual.success and not actual.truncated,
                "Repaired PostgreSQL SQL failed: " + str(actual.error))
        with tempfile.TemporaryDirectory(prefix="askdata_m1_e_v5_gold_") as temporary:
            gold = resolve_gold_result(
                case, runtime.executor, scope, cache_dir=Path(temporary),
                use_cached_gold=False, data_version=identity["data_version"],
            )
        require(gold["source"] == "execution", "Gold was not freshly executed")
        frozen = {"columns": case["expected_columns"], "rows": case["expected_rows"]}
        require(strict(gold["columns"], gold["rows"], frozen, case)[0],
                "Fresh PostgreSQL Gold differs from frozen expectation")
        strict_score = strict(actual.columns, actual.rows, gold, case)
        loose = compare_results(
            actual.columns, actual.rows, gold["columns"], gold["rows"],
            bool(case.get("order_sensitive", True)),
            order_by_column=case.get("order_by_column"),
            top_n_tie_policy=case.get("top_n_tie_policy"),
        )
    require(sha256(CASES) == FORMAL_SHA256 and sha256(SOURCE) == SOURCE_SHA256,
            "Source evidence changed during diagnosis")
    passed = strict_score[0] is True and loose[0] is True
    result = {
        "stage": "M1 E v5 CHANNEL_OPS-136 PostgreSQL ORDER BY diagnosis",
        "run_status": "complete" if passed else "failed",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "run_manifest": manifest,
        "source_report_sha256": SOURCE_SHA256,
        "formal_cases_sha256": FORMAL_SHA256,
        "formal_cases_modified": False,
        "new_model_request_count": 0,
        "case": {
            "case_id": CASE_ID,
            "source_run_id": SOURCE_RUN_ID,
            "original_sql_sha256": SQL_SHA256,
            "original_sql": row["generated_sql"],
            "original_validation": before.to_dict(),
            "original_sql_error": str(failed.error),
            "repaired_sql": repaired_sql,
            "repaired_sql_sha256": hashlib.sha256(repaired_sql.encode("utf-8")).hexdigest(),
            "repaired_validation": after.to_dict(),
            "postgres_gold_sql": gold["gold_sql"],
            "actual_columns": actual.columns, "actual_rows": actual.rows,
            "gold_columns": gold["columns"], "gold_rows": gold["rows"],
            "loose_correct": loose[0], "loose_reason": loose[2],
            "strict_correct": strict_score[0], "strict_reason": strict_score[1],
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=RESULTS / "m1_e_v5_channel136_diagnostic_server.json")
    args = parser.parse_args()
    report = diagnose(args.output.resolve())
    print(json.dumps({"output": str(args.output), "run_status": report["run_status"],
                      "case": {k: report["case"][k] for k in (
                          "case_id", "original_sql_error", "loose_correct", "strict_correct",
                      )}}, ensure_ascii=False, indent=2))
    if report["run_status"] != "complete":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
