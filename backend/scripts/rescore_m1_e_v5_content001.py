"""Independently replay the reviewed CONTENT_OPS-001 v5 SQL on PostgreSQL."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

import sqlglot
from sqlglot import exp

from app.config import BASE_DIR, settings
from app.datasources import create_datasource_runtime
from app.security import AccessController
from evaluation.gold_result import resolve_gold_result
from evaluation.report_identity import validate_report_identity
from evaluation.run_benchmark import compare_results, load_cases, summarize
from evaluation.run_manifest import _digest, build_run_manifest
from scripts.rescore_m1_e_v3_strict import amended_case, require, sha256, strict


RESULTS = BASE_DIR / "evaluation/results"
CASES = BASE_DIR / "evaluation/cases/all_cases.jsonl"
SOURCE = RESULTS / "m1_e_postgres_live_classic_server_v5.json"
FORMAL_SHA256 = "ff5956e9f4aca878ee63e232bdea1fef3416a28eda72669f91a33546c70f3adc"
SOURCE_SHA256 = "bd8d2a5fb01d0a87c34f43656ae228183b7f7e8efa3143519e862060fd8ef37e"
SOURCE_RUN_ID = "4d173d09c42b468b992942c4e2a6cfb2"
SQL_SHA256 = "2da9406a2084936de17c7f397766ca9712049f3a476c7fb722252f36fdb76174"
CASE_ID = "CONTENT_OPS-001"
REVIEW = {
    "aliases": {
        "metric_date": ["指标日期"],
        "impressions": ["曝光量"],
        "plays": ["播放量"],
    },
    "auxiliary_columns": [],
}
PROJECTIONS = {
    "metric_date": ("指标日期", "cdm.metric_date"),
    "impressions": ("曝光量", "SUM(cdm.impressions)"),
    "plays": ("播放量", "SUM(cdm.play_count)"),
}


def preflight() -> tuple[dict, dict, dict, dict, list[dict]]:
    require(sha256(CASES) == FORMAL_SHA256, "Formal cases differ from v5")
    require(sha256(SOURCE) == SOURCE_SHA256, "v5 source report differs")
    report = json.loads(SOURCE.read_text(encoding="utf-8"))
    manifest = validate_report_identity(report)
    require(
        report.get("run_status") == "complete"
        and manifest["run_id"] == SOURCE_RUN_ID
        and manifest["mode"] == "live"
        and manifest["scope"] == "classic"
        and len(report["cases"]) == 49
        and report["summary"] == summarize(report["cases"], "live")
        and manifest["source_identity"]["source_id"] == "short_video_ops_postgres"
        and manifest["source_identity"]["backend"] == "postgresql",
        "v5 report status, summary, or PostgreSQL identity differs",
    )
    cases = load_cases(CASES, set(), False)
    by_id = {case["case_id"]: case for case in cases}
    require(len(cases) == len(by_id) == 430, "Formal case count differs")
    selected = [by_id[case_id] for case_id in manifest["dataset"]["case_ids"]]
    require(_digest(selected) == manifest["dataset"]["version"],
            "v5 case dataset differs from formal cases")
    original = by_id[CASE_ID]
    row = next(item for item in report["cases"] if item["case_id"] == CASE_ID)
    require(
        hashlib.sha256(row["generated_sql"].encode("utf-8")).hexdigest() == SQL_SHA256
        and row["sql_execution_success"] is True
        and row["result_correct"] is True
        and row["strict_result_correct"] is False
        and row["result_metrics"]["gold_result_source"] == "execution"
        and row["result_metrics"]["gold_dialect"] == "postgres"
        and row["query_contract"]["constraint_validation"]["status"] == "PASS"
        and not row["query_contract"]["constraint_validation"]["warnings"],
        "CONTENT_OPS-001 v5 SQL or scores differ from reviewed evidence",
    )
    statement = sqlglot.parse_one(row["generated_sql"], read="postgres")
    require(isinstance(statement, exp.Select) and len(statement.expressions) == 3,
            "Reviewed SELECT projection count differs")
    projection_review = []
    for expected, projection in zip(original["expected_columns"], statement.expressions):
        require(isinstance(projection, exp.Alias) and expected in PROJECTIONS,
                "Unexpected SELECT projection")
        actual_alias, expression = PROJECTIONS[expected]
        require(projection.alias_or_name == actual_alias
                and projection.this.sql(dialect="postgres") == expression,
                "Column expression differs from semantic review: " + expected)
        projection_review.append({"gold_column": expected, "actual_column": actual_alias,
                                  "expression": expression})
    proposed = amended_case(original, REVIEW)
    require(set(REVIEW["aliases"]) == set(original["expected_columns"])
            and not REVIEW["auxiliary_columns"] and proposed != original,
            "Expected exactly three explicit aliases")
    return report, row, original, proposed, projection_review


def replay(output: Path) -> dict:
    require(not output.exists() and output.resolve() not in {CASES.resolve(), SOURCE.resolve()},
            "Choose a new output path and preserve source evidence")
    report, row, original, proposed, projection_review = preflight()
    identity = report["run_manifest"]["source_identity"]
    with create_datasource_runtime(settings) as runtime:
        require(runtime.identity.public() == identity
                and runtime.metadata.verification["physical_schema_version"] ==
                    report["run_manifest"]["versions"]["physical_schema"],
                "Live PostgreSQL source differs from v5")
        manifest = build_run_manifest(
            [proposed], base_dir=BASE_DIR, mode="offline_rescore",
            scope="m1_e_v5_content001", case_source=CASES, runtime=runtime,
            config={"operation": "saved_sql_postgres_replay", "new_model_request_count": 0,
                    "source_run_id": SOURCE_RUN_ID},
        )
        scope = AccessController().resolve("demo_content_ops")
        actual = runtime.executor.execute(identity["logical_database_id"],
                                          row["generated_sql"], scope, row_limit=10000)
        require(actual.success and not actual.truncated,
                "Saved PostgreSQL SQL failed: " + str(actual.error))
        with tempfile.TemporaryDirectory(prefix="askdata_m1_e_v5_gold_") as temporary:
            gold = resolve_gold_result(
                original, runtime.executor, scope, cache_dir=Path(temporary),
                use_cached_gold=False, data_version=identity["data_version"],
            )
        require(gold["source"] == "execution"
                and gold["gold_sql"] == row["result_metrics"]["gold_sql"],
                "Gold was not freshly executed with the selected PostgreSQL SQL")
        frozen = {"columns": original["expected_columns"], "rows": original["expected_rows"]}
        require(strict(gold["columns"], gold["rows"], frozen, original)[0],
                "Fresh PostgreSQL Gold differs from frozen expectation")
        original_score = strict(actual.columns, actual.rows, gold, original)
        candidate_score = strict(actual.columns, actual.rows, gold, proposed)
        loose = compare_results(
            actual.columns, actual.rows, gold["columns"], gold["rows"],
            bool(original.get("order_sensitive", True)),
            order_by_column=original.get("order_by_column"),
            top_n_tie_policy=original.get("top_n_tie_policy"),
        )
        require(len(actual.rows) == row["result_metrics"]["generated_result_rows"]
                and len(gold["rows"]) == row["result_metrics"]["gold_result_rows"],
                "Fresh row counts differ from v5")

    require(sha256(CASES) == FORMAL_SHA256 and sha256(SOURCE) == SOURCE_SHA256,
            "Source evidence changed during replay")
    passed = original_score[0] is False and candidate_score[0] is True and loose[0] is True
    result = {
        "stage": "M1 E v5 CONTENT_OPS-001 exact column review",
        "run_status": "complete" if passed else "failed",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "run_manifest": manifest,
        "source_report_sha256": SOURCE_SHA256,
        "formal_cases_sha256": FORMAL_SHA256,
        "formal_cases_modified": False,
        "new_model_request_count": 0,
        "summary": {
            "case_count": 1,
            "original_strict_pass_count": int(original_score[0]),
            "candidate_strict_pass_count": int(candidate_score[0]),
            "loose_pass_count": int(loose[0]),
            "alias_addition_count": 3,
            "failed_case_ids": [] if passed else [CASE_ID],
        },
        "cases": [{
            "case_id": CASE_ID, "source_run_id": SOURCE_RUN_ID,
            "generated_sql_sha256": SQL_SHA256,
            "generated_sql": row["generated_sql"],
            "postgres_gold_sql": gold["gold_sql"],
            "projection_review": projection_review,
            "actual_columns": actual.columns, "actual_rows": actual.rows,
            "gold_columns": gold["columns"], "gold_rows": gold["rows"],
            "original_strict": original_score[0], "original_reason": original_score[1],
            "candidate_strict": candidate_score[0], "candidate_reason": candidate_score[1],
            "loose_correct": loose[0], "loose_reason": loose[2],
            "alias_additions": REVIEW["aliases"],
            "allowed_auxiliary_columns_additions": [],
        }],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=RESULTS / "m1_e_v5_content001_rescore_server.json")
    args = parser.parse_args()
    report = replay(args.output.resolve())
    print(json.dumps({"output": str(args.output), "run_status": report["run_status"],
                      "summary": report["summary"]}, ensure_ascii=False, indent=2))
    if report["run_status"] != "complete":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
