"""Replay seven saved M1 E v4 SQL queries and their Gold on PostgreSQL.

This writes independent evidence. It never edits the formal cases or calls a model.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

import sqlglot

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
FORMAL_SHA256 = "22a7ee6f9d8d2309e79ceb5d831468b30f609c485a0a31ba5d1a0cbde3d9ba6b"
SOURCES = {
    "m1_e_postgres_live_classic_server_v4.json": {
        "sha256": "71069c4ab43ef935c9e7ea16481c33a688684b952e3b0abdbe42248a9bc56735",
        "run_id": "c8659a8ae7d54366b324c47d35214111",
        "scope": "classic",
        "case_count": 49,
    },
    "m1_e_postgres_live_phase83_server_v4.json": {
        "sha256": "e001bfffb11b9037720e759efdb5f959b4ed42e04121c7d0f5d067736fd55025",
        "run_id": "ece685dafeaa456c87397e62d09b2932",
        "scope": "all",
        "case_count": 30,
    },
}

# Each mapping is attached to one reviewed case and one pinned generated SQL.
REVIEWED = {
    "CHANNEL_OPS-001": {
        "sql_sha256": "c6c302ce3094e7d3143fb00582cc92b8e4405c04cc017b83e182cb1bcc55e436",
        "aliases": {"stat_date": ["\u7edf\u8ba1\u65e5\u671f"], "spend": ["\u5e7f\u544a\u6d88\u8017"]},
        "auxiliary_columns": [],
    },
    "CHANNEL_OPS-002": {
        "sql_sha256": "de99c0ded2ca09f3f8e22decf4ba2ef6b954435ace2fec15cbf2e8639bd07d77",
        "aliases": {"stat_date": ["\u7edf\u8ba1\u65e5\u671f"], "spend": ["\u5e7f\u544a\u6d88\u8017"]},
        "auxiliary_columns": [],
    },
    "CHANNEL_OPS-067": {
        "sql_sha256": "db9609dd4b4d98f21d9fc2503433431aeb3f0fd3c7d01086313e9f970a08ce66",
        "aliases": {"conversion_type": ["\u8f6c\u5316\u7c7b\u578b"], "conversions": ["\u8f6c\u5316\u6570"], "avg_value": ["\u5e73\u5747\u4ef7\u503c"]},
        "auxiliary_columns": [],
    },
    "CHANNEL_OPS-069": {
        "sql_sha256": "db9609dd4b4d98f21d9fc2503433431aeb3f0fd3c7d01086313e9f970a08ce66",
        "aliases": {"conversion_type": ["\u8f6c\u5316\u7c7b\u578b"], "conversions": ["\u8f6c\u5316\u6570"], "avg_value": ["\u5e73\u5747\u4ef7\u503c"]},
        "auxiliary_columns": [],
    },
    "CHANNEL_OPS-070": {
        "sql_sha256": "eefdc08d30eb7348ecb4111f42c6fe49261b788ebab0807637eaa1f33199fc9d",
        "aliases": {"conversion_type": ["\u8f6c\u5316\u7c7b\u578b"], "conversions": ["\u8f6c\u5316\u6570"], "avg_value": ["\u5e73\u5747\u4ef7\u503c"]},
        "auxiliary_columns": [],
    },
    "CHANNEL_OPS-026": {
        "sql_sha256": "6d44cba4461e630d5a34012ac2a92d2ac4196d5de0af6e38a4f60815b503c0a6",
        "aliases": {"impressions": ["exposure_count"], "clicks": ["click_count"]},
        "auxiliary_columns": [],
    },
    "CHANNEL_OPS-136": {
        "sql_sha256": "5780328cce2d0e9c94cacec7b0ab4b42d46e0a49efb0212bec32e0bc446b5e01",
        "aliases": {"gap": ["target_gap"]},
        "auxiliary_columns": [],
    },
}


def preflight() -> tuple[list[dict], dict[str, dict], dict[str, dict], dict]:
    """Pin the unchanged formal dataset, source reports, SQL and proposals."""
    require(sha256(CASES) == FORMAL_SHA256, "Formal case dataset differs from v4")
    cases = load_cases(CASES, set(), False)
    by_id = {case["case_id"]: case for case in cases}
    require(len(cases) == len(by_id) == 430, "Formal case count changed")

    reports = []
    source_rows = {}
    for name, expected in SOURCES.items():
        path = RESULTS / name
        report = json.loads(path.read_text(encoding="utf-8"))
        manifest = validate_report_identity(report)
        require(
            sha256(path) == expected["sha256"]
            and manifest["run_id"] == expected["run_id"]
            and manifest["mode"] == "live"
            and manifest["scope"] == expected["scope"]
            and report["run_status"] == "complete"
            and len(report["cases"]) == expected["case_count"]
            and report["summary"] == summarize(report["cases"], "live"),
            "v4 source report changed: " + name,
        )
        selected = [by_id[case_id] for case_id in manifest["dataset"]["case_ids"]]
        require(_digest(selected) == manifest["dataset"]["version"],
                "v4 report case dataset differs from formal cases: " + name)
        require([row["case_id"] for row in report["cases"]] ==
                manifest["dataset"]["case_ids"], "v4 case order differs: " + name)
        for row in report["cases"]:
            require(row["case_id"] not in source_rows,
                    "Case is present in both source reports: " + row["case_id"])
            source_rows[row["case_id"]] = row
        reports.append(report)

    identity = reports[0]["run_manifest"]["source_identity"]
    physical = reports[0]["run_manifest"]["versions"]["physical_schema"]
    require(
        identity == reports[1]["run_manifest"]["source_identity"]
        and identity["backend"] == "postgresql"
        and identity["source_id"] == "short_video_ops_postgres"
        and physical == reports[1]["run_manifest"]["versions"]["physical_schema"]
        and all(report["run_manifest"]["source_verification"].get("live_target_verified")
                is True for report in reports),
        "v4 PostgreSQL source identities or verification differ",
    )

    require(set(REVIEWED) <= set(source_rows), "Reviewed cases absent from v4 reports")
    for case_id, candidate in REVIEWED.items():
        row = source_rows[case_id]
        proposed = amended_case(by_id[case_id], candidate)
        projection_names = [expression.alias_or_name for expression in
                            sqlglot.parse_one(row["generated_sql"], read="postgres").expressions]
        requested_names = [name for names in candidate["aliases"].values() for name in names]
        require(
            row["sql_execution_success"] is True
            and row["result_correct"] is True
            and row["strict_result_correct"] is False
            and row["result_metrics"]["gold_result_source"] == "execution"
            and row["result_metrics"]["gold_dialect"] == "postgres"
            and row["query_contract"]["constraint_validation"]["status"] == "PASS"
            and not row["query_contract"]["constraint_validation"]["warnings"]
            and hashlib.sha256(row["generated_sql"].encode("utf-8")).hexdigest()
                == candidate["sql_sha256"]
            and len(requested_names) == len(set(requested_names))
            and set(requested_names) <= set(projection_names)
            and not candidate["auxiliary_columns"]
            and proposed != by_id[case_id],
            "Reviewed SQL, result or exact mapping changed: " + case_id,
        )
    return reports, by_id, source_rows, identity


def replay(output: Path) -> dict:
    source_paths = [RESULTS / name for name in SOURCES]
    require(not output.exists() and output.resolve() not in {
        CASES.resolve(), *(path.resolve() for path in source_paths),
    }, "Choose a new output path and preserve source evidence")
    reports, by_id, source_rows, identity = preflight()
    proposed_cases = [amended_case(by_id[case_id], candidate)
                      for case_id, candidate in REVIEWED.items()]
    evidence = []
    with create_datasource_runtime(settings) as runtime:
        require(
            runtime.identity.public() == identity
            and runtime.metadata.verification["physical_schema_version"] ==
                reports[0]["run_manifest"]["versions"]["physical_schema"],
            "Current verified PostgreSQL source differs from v4",
        )
        manifest = build_run_manifest(
            proposed_cases, base_dir=BASE_DIR, mode="offline_rescore",
            scope="m1_e_v4_strict7", case_source=CASES, runtime=runtime,
            config={"operation": "saved_sql_postgres_replay", "new_model_request_count": 0,
                    "source_run_ids": [report["run_manifest"]["run_id"]
                                       for report in reports]},
        )
        controller = AccessController()
        with tempfile.TemporaryDirectory(prefix="askdata_m1_e_v4_gold_") as temporary:
            for index, (case_id, candidate) in enumerate(REVIEWED.items(), 1):
                original = by_id[case_id]
                proposed = proposed_cases[index - 1]
                row = source_rows[case_id]
                scope = controller.resolve("demo_" + original["scenario"])
                actual = runtime.executor.execute(
                    identity["logical_database_id"], row["generated_sql"], scope,
                    row_limit=10000,
                )
                require(actual.success and not actual.truncated,
                        "Saved PostgreSQL SQL failed: " + case_id + " " + str(actual.error))
                gold = resolve_gold_result(
                    original, runtime.executor, scope, cache_dir=Path(temporary),
                    use_cached_gold=False, data_version=identity["data_version"],
                )
                require(gold["source"] == "execution", "Gold was not freshly executed")
                frozen = {"columns": original["expected_columns"],
                          "rows": original["expected_rows"]}
                require(strict(gold["columns"], gold["rows"], frozen, original)[0],
                        "PostgreSQL Gold differs from frozen expectation: " + case_id)
                original_score = strict(actual.columns, actual.rows, gold, original)
                candidate_score = strict(actual.columns, actual.rows, gold, proposed)
                loose = compare_results(
                    actual.columns, actual.rows, gold["columns"], gold["rows"],
                    bool(original.get("order_sensitive", True)),
                    order_by_column=original.get("order_by_column"),
                    top_n_tie_policy=original.get("top_n_tie_policy"),
                )
                require(
                    len(actual.rows) == row["result_metrics"]["generated_result_rows"]
                    and len(gold["rows"]) == row["result_metrics"]["gold_result_rows"],
                    "Row count differs from v4 report: " + case_id,
                )
                evidence.append({
                    "case_id": case_id, "source_run_id": row["run_id"],
                    "generated_sql_sha256": candidate["sql_sha256"],
                    "generated_sql": row["generated_sql"],
                    "postgres_gold_sql": gold["gold_sql"],
                    "actual_columns": actual.columns, "actual_rows": actual.rows,
                    "gold_columns": gold["columns"], "gold_rows": gold["rows"],
                    "original_strict": original_score[0],
                    "original_reason": original_score[1],
                    "candidate_strict": candidate_score[0],
                    "candidate_reason": candidate_score[1],
                    "loose_correct": loose[0], "loose_reason": loose[2],
                    "alias_additions": candidate["aliases"],
                    "allowed_auxiliary_columns_additions": candidate["auxiliary_columns"],
                })
                print(f"[{index}/{len(REVIEWED)}] {case_id}: "
                      f"{original_score[0]} -> {candidate_score[0]}, loose={loose[0]}",
                      flush=True)

    require(sha256(CASES) == FORMAL_SHA256 and all(
        sha256(path) == SOURCES[path.name]["sha256"] for path in source_paths
    ), "Source evidence changed during replay")
    failed = [row["case_id"] for row in evidence if
              row["original_strict"] is not False or
              row["candidate_strict"] is not True or
              row["loose_correct"] is not True]
    report = {
        "stage": "M1 E v4 seven-case PostgreSQL strict-policy review",
        "run_status": "failed" if failed else "complete",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "run_manifest": manifest,
        "source_report_sha256": {path.name: sha256(path) for path in source_paths},
        "formal_cases_sha256": FORMAL_SHA256,
        "formal_cases_modified": False,
        "new_model_request_count": 0,
        "summary": {
            "case_count": len(REVIEWED),
            "original_strict_pass_count": sum(row["original_strict"] is True for row in evidence),
            "candidate_strict_pass_count": sum(row["candidate_strict"] is True for row in evidence),
            "loose_pass_count": sum(row["loose_correct"] is True for row in evidence),
            "alias_addition_count": sum(len(names) for candidate in REVIEWED.values()
                                        for names in candidate["aliases"].values()),
            "auxiliary_allow_count": 0,
            "failed_case_ids": failed,
        },
        "cases": evidence,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=RESULTS / "m1_e_v4_strict7_rescore_server.json")
    args = parser.parse_args()
    report = replay(args.output.resolve())
    print(json.dumps({"output": str(args.output), "run_status": report["run_status"],
                      "summary": report["summary"]}, ensure_ascii=False, indent=2))
    if report["run_status"] != "complete":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
