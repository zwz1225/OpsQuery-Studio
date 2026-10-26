"""Replay two saved v6 PostgreSQL queries against fresh Gold without model calls.

This command writes independent evidence only. It never edits formal cases or
the original live report. Run it before applying any proposed column aliases.
"""

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
SOURCE = RESULTS / "m1_e_postgres_live_classic_server_v6.json"
FORMAL_SHA256 = "08cf84a50f43eb2d176d96246e1210c398a13a89beec69a9d0db1b7361b7815a"
SOURCE_SHA256 = "7a8c204f2ea28b87917ff3bb93835fe3c72287aef01b20bbc32a49b838939f9e"
SOURCE_RUN_ID = "983ed2ffb4d044549db1f077b3d9519c"
REVIEWED = {
    "CHANNEL_OPS-066": {
        "sql_sha256": "e8b79d41391a3a4e72d22ba2a36a29565cc473716fed26e29a0a8496faa48c9a",
        "aliases": {
            "conversion_type": ["转化类型"],
            "conversions": ["转化数"],
            "avg_value": ["平均价值"],
        },
        "projections": {
            "conversion_type": ("转化类型", "cce.conversion_type"),
            "conversions": ("转化数", "COUNT(*)"),
            "avg_value": ("平均价值", "ROUND(AVG(cce.conversion_value::numeric), 2)"),
        },
    },
    "CONTENT_OPS-138": {
        "sql_sha256": "5d16ed905549846295520691acdc6963fea8385596ebc2d6f6c46c079096b708",
        "aliases": {"category_name": ["content_category"]},
        "projections": {
            "category_name": ("content_category", "cc.category_name"),
            "reports": ("report_count", "COUNT(cr.report_id)"),
        },
    },
}


def preflight() -> tuple[dict, dict[str, dict], dict[str, dict], dict[str, dict], dict]:
    require(sha256(CASES) == FORMAL_SHA256, "Formal cases differ from reviewed v6")
    require(sha256(SOURCE) == SOURCE_SHA256, "v6 source report differs")
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
        and manifest["source_identity"]["backend"] == "postgresql"
        and manifest["source_identity"]["dialect"] == "postgres"
        and manifest["source_verification"].get("live_target_verified") is True,
        "v6 status, summary, or verified PostgreSQL identity differs",
    )
    cases = load_cases(CASES, set(), False)
    by_id = {case["case_id"]: case for case in cases}
    require(len(cases) == len(by_id) == 430, "Formal case count differs")
    selected = [by_id[case_id] for case_id in manifest["dataset"]["case_ids"]]
    require(_digest(selected) == manifest["dataset"]["version"],
            "v6 report dataset differs from formal cases")
    source_rows = {item["case_id"]: item for item in report["cases"]}
    require(len(source_rows) == 49 and set(REVIEWED) <= set(source_rows),
            "Reviewed cases missing from v6 report")

    proposed = {}
    projections = {}
    for case_id, review in REVIEWED.items():
        original = by_id[case_id]
        row = source_rows[case_id]
        require(
            hashlib.sha256(row["generated_sql"].encode("utf-8")).hexdigest()
                == review["sql_sha256"]
            and row["sql_execution_success"] is True
            and row["result_correct"] is True
            and row["strict_result_correct"] is False
            and row["result_metrics"]["gold_result_source"] == "execution"
            and row["result_metrics"]["gold_dialect"] == "postgres"
            and row["query_contract"]["constraint_validation"]["status"] == "PASS"
            and not row["query_contract"]["constraint_validation"]["warnings"],
            "Reviewed SQL, score, or validation changed: " + case_id,
        )
        statement = sqlglot.parse_one(row["generated_sql"], read="postgres")
        require(isinstance(statement, exp.Select) and
                len(statement.expressions) == len(original["expected_columns"]),
                "Reviewed projection count differs: " + case_id)
        case_projections = []
        for expected, projection in zip(original["expected_columns"], statement.expressions):
            require(isinstance(projection, exp.Alias) and
                    expected in review["projections"],
                    "Unexpected projection: " + case_id + ": " + expected)
            actual, expression = review["projections"][expected]
            reference = sqlglot.parse_one("SELECT " + expression, read="postgres")
            require(projection.alias_or_name == actual and
                    projection.this == reference.expressions[0],
                    "Projection meaning differs: " + case_id + ": " + expected)
            case_projections.append({"gold_column": expected,
                                     "actual_column": actual, "expression": expression})
        require(set(review["aliases"]) <= set(original["expected_columns"])
                and sum(map(len, review["aliases"].values())) in (1, 3),
                "Unexpected alias proposal: " + case_id)
        proposed[case_id] = amended_case(original, {
            "aliases": review["aliases"], "auxiliary_columns": [],
        })
        projections[case_id] = case_projections
    require(sum(len(names) for review in REVIEWED.values()
                for names in review["aliases"].values()) == 4,
            "Expected exactly four explicit aliases")
    return report, by_id, source_rows, proposed, projections


def replay(output: Path) -> dict:
    require(not output.exists() and output.resolve() not in
            {CASES.resolve(), SOURCE.resolve()},
            "Choose a new output path and preserve source evidence")
    report, by_id, source_rows, proposed, projections = preflight()
    identity = report["run_manifest"]["source_identity"]
    evidence = []
    with create_datasource_runtime(settings) as runtime:
        require(runtime.identity.public() == identity and
                runtime.metadata.verification["physical_schema_version"] ==
                report["run_manifest"]["versions"]["physical_schema"],
                "Live PostgreSQL source differs from v6")
        manifest = build_run_manifest(
            [proposed[case_id] for case_id in REVIEWED], base_dir=BASE_DIR,
            mode="offline_rescore", scope="m1_e_v6_strict2", case_source=CASES,
            runtime=runtime,
            config={"operation": "saved_sql_postgres_replay",
                    "new_model_request_count": 0, "source_run_id": SOURCE_RUN_ID},
        )
        controller = AccessController()
        with tempfile.TemporaryDirectory(prefix="askdata_m1_e_v6_gold_") as temporary:
            for index, case_id in enumerate(REVIEWED, 1):
                original, row = by_id[case_id], source_rows[case_id]
                scope = controller.resolve("demo_" + original["scenario"])
                actual = runtime.executor.execute(
                    identity["logical_database_id"], row["generated_sql"],
                    scope, row_limit=10000,
                )
                require(actual.success and not actual.truncated,
                        "Saved PostgreSQL SQL failed: " + case_id + " " + str(actual.error))
                gold = resolve_gold_result(
                    original, runtime.executor, scope, cache_dir=Path(temporary),
                    use_cached_gold=False, data_version=identity["data_version"],
                )
                require(gold["source"] == "execution" and
                        gold["gold_sql"] == row["result_metrics"]["gold_sql"],
                        "Fresh PostgreSQL Gold differs from v6: " + case_id)
                frozen = {"columns": original["expected_columns"],
                          "rows": original["expected_rows"]}
                require(strict(gold["columns"], gold["rows"], frozen, original)[0],
                        "Fresh PostgreSQL Gold differs from frozen expectation: " + case_id)
                original_score = strict(actual.columns, actual.rows, gold, original)
                candidate_score = strict(actual.columns, actual.rows, gold, proposed[case_id])
                loose = compare_results(
                    actual.columns, actual.rows, gold["columns"], gold["rows"],
                    bool(original.get("order_sensitive", True)),
                    order_by_column=original.get("order_by_column"),
                    top_n_tie_policy=original.get("top_n_tie_policy"),
                )
                require(len(actual.rows) == row["result_metrics"]["generated_result_rows"]
                        and len(gold["rows"]) == row["result_metrics"]["gold_result_rows"],
                        "Fresh row counts differ from v6: " + case_id)
                require(original_score[0] is False and candidate_score[0] is True
                        and loose[0] is True,
                        "Independent PostgreSQL replay did not confirm aliases: " + case_id)
                evidence.append({
                    "case_id": case_id, "source_run_id": row["run_id"],
                    "generated_sql_sha256": REVIEWED[case_id]["sql_sha256"],
                    "generated_sql": row["generated_sql"],
                    "postgres_gold_sql": gold["gold_sql"],
                    "projection_review": projections[case_id],
                    "actual_columns": actual.columns, "actual_rows": actual.rows,
                    "gold_columns": gold["columns"], "gold_rows": gold["rows"],
                    "original_strict": original_score[0],
                    "original_reason": original_score[1],
                    "candidate_strict": candidate_score[0],
                    "candidate_reason": candidate_score[1],
                    "loose_correct": loose[0], "loose_reason": loose[2],
                    "alias_additions": REVIEWED[case_id]["aliases"],
                    "allowed_auxiliary_columns_additions": [],
                })
                print(f"[{index}/{len(REVIEWED)}] {case_id}: "
                      f"{original_score[0]} -> {candidate_score[0]}", flush=True)
    require(sha256(CASES) == FORMAL_SHA256 and sha256(SOURCE) == SOURCE_SHA256,
            "Source evidence changed during replay")
    result = {
        "stage": "M1 E v6 two-case PostgreSQL strict-policy review",
        "run_status": "complete", "recorded_at": datetime.now(timezone.utc).isoformat(),
        "run_manifest": manifest,
        "source_report_sha256": SOURCE_SHA256,
        "formal_cases_sha256": FORMAL_SHA256,
        "formal_cases_modified": False, "new_model_request_count": 0,
        "summary": {
            "case_count": 2, "original_strict_pass_count": 0,
            "candidate_strict_pass_count": 2, "loose_pass_count": 2,
            "alias_addition_count": 4, "failed_case_ids": [],
        },
        "cases": evidence,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=RESULTS / "m1_e_v6_strict2_rescore_server.json")
    args = parser.parse_args()
    result = replay(args.output.resolve())
    print(json.dumps({"output": str(args.output), "run_status": result["run_status"],
                      "summary": result["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
