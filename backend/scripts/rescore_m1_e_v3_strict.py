"""Independently replay four reviewed M1 E v3 strict-scoring cases on PostgreSQL.

The command saves new evidence only. It does not edit formal cases or source
reports and sends no model requests.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from app.config import BASE_DIR, settings
from app.datasources import create_datasource_runtime
from app.security import AccessController
from evaluation.gold_result import resolve_gold_result
from evaluation.report_identity import validate_report_identity
from evaluation.run_benchmark import (
    compare_results, compare_results_strict, load_cases, summarize,
)
from evaluation.run_manifest import _digest, build_run_manifest


RESULTS = BASE_DIR / "evaluation/results"
CASES = BASE_DIR / "evaluation/cases/all_cases.jsonl"
FORMAL_SHA256 = "2c72c23c00685ea2dca5247e50a9395ba8e3d885f64710059f86004d1f705c15"
SOURCES = {
    "m1_e_postgres_live_classic_server_v3.json": {
        "sha256": "ad6eaf3b8b4647a38ea70aa3c3cb11278231746dd12de7370e0aa97254cf7ca2",
        "run_id": "41347c0a292942d1b4b0f45c7b9ff0d7",
    },
    "m1_e_postgres_live_phase83_server_v3.json": {
        "sha256": "408e7052fe3c4251832526087cf1c254004788b34a18adf95e9ddd3fa4a20a43",
        "run_id": "853f3db4df48422c9d25eb605b0bebc2",
    },
}
REVIEWED = {
    "CHANNEL_OPS-004": {
        "sql_sha256": "5b5609829546231531cb3295669051feaabad5f1be21518605d4cfdff69a8b43",
        "aliases": {"stat_date": ["统计日期"], "spend": ["广告消耗"]},
        "auxiliary_columns": [],
    },
    "CHANNEL_OPS-005": {
        "sql_sha256": "f7d13e275e31de0eb81900c37be20d0e64c83d18e7551f893d0ee2631df97ab3",
        "aliases": {"stat_date": ["统计日期"], "spend": ["广告消耗"]},
        "auxiliary_columns": [],
    },
    "GROWTH_OPS-100": {
        "sql_sha256": "df89015a67415f248e7d6af08595f2bcae283e501a582fd7511742f284e39205",
        "aliases": {"plays_per_user": ["avg_plays_per_user"]},
        "auxiliary_columns": ["total_play_count", "distinct_user_count"],
    },
    "CHANNEL_OPS-102": {
        "sql_sha256": "abde6d2c9849e139c22a27ac0d62c72e7fc21e8a16ad707a959770cf704ae2b0",
        "aliases": {"creative_status": ["创意状态"], "creatives": ["创意数量"]},
        "auxiliary_columns": [],
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict(columns: list[str], rows: list[dict], gold: dict, case: dict) -> tuple[bool, str]:
    return compare_results_strict(
        columns, rows, gold["columns"], gold["rows"],
        bool(case.get("order_sensitive", True)),
        order_by_column=case.get("order_by_column"),
        column_aliases=case.get("column_aliases"),
        allowed_auxiliary_columns=case.get("allowed_auxiliary_columns"),
        top_n_tie_policy=case.get("top_n_tie_policy"),
    )


def amended_case(original: dict, review: dict) -> dict:
    amended = deepcopy(original)
    for expected, names in review["aliases"].items():
        require(expected in original["expected_columns"] and names and all(names),
                "Invalid expected column mapping: " + original["case_id"])
        aliases = amended.setdefault("column_aliases", {}).setdefault(expected, [])
        require(not set(names) & set(aliases),
                "Alias is already declared: " + original["case_id"])
        aliases.extend(names)
    if review["auxiliary_columns"]:
        extras = amended.setdefault("allowed_auxiliary_columns", [])
        require(not set(review["auxiliary_columns"]) & set(extras),
                "Auxiliary column is already declared: " + original["case_id"])
        extras.extend(review["auxiliary_columns"])
    return amended


def replay(output: Path) -> dict:
    source_paths = [RESULTS / name for name in SOURCES]
    require(not output.exists() and output.resolve() not in {
        CASES.resolve(), *(path.resolve() for path in source_paths),
    }, "Choose a new output path and preserve source evidence")
    require(sha256(CASES) == FORMAL_SHA256, "Formal case dataset differs from v3")

    reports = []
    for path in source_paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        manifest = validate_report_identity(report)
        expected = SOURCES[path.name]
        require(sha256(path) == expected["sha256"] and
                manifest["run_id"] == expected["run_id"] and
                report["run_status"] == "complete" and
                report["summary"] == summarize(report["cases"], "live"),
                "v3 source report changed: " + path.name)
        reports.append(report)
    identity = reports[0]["run_manifest"]["source_identity"]
    require(identity == reports[1]["run_manifest"]["source_identity"] and
            identity["backend"] == "postgresql", "Source identities differ")
    require(reports[0]["run_manifest"]["versions"]["physical_schema"] ==
            reports[1]["run_manifest"]["versions"]["physical_schema"],
            "Physical schema versions differ")

    cases = load_cases(CASES, set(), False)
    by_id = {case["case_id"]: case for case in cases}
    require(len(cases) == len(by_id) == 430, "Formal case count changed")
    for report in reports:
        selected = [by_id[case_id] for case_id in report["run_manifest"]["dataset"]["case_ids"]]
        require(_digest(selected) == report["run_manifest"]["dataset"]["version"],
                "v3 report case dataset differs from formal cases")
    source_rows = {case["case_id"]: case for report in reports for case in report["cases"]}
    amended = [amended_case(by_id[case_id], review) for case_id, review in REVIEWED.items()]
    for case_id, review in REVIEWED.items():
        row = source_rows[case_id]
        require(row["sql_execution_success"] is True and
                row["result_correct"] is True and
                row["strict_result_correct"] is False and
                hashlib.sha256(row["generated_sql"].encode("utf-8")).hexdigest() ==
                review["sql_sha256"], "Reviewed SQL or outcome changed: " + case_id)

    evidence = []
    with create_datasource_runtime(settings) as runtime:
        require(runtime.identity.public() == identity and
                runtime.metadata.verification["physical_schema_version"] ==
                reports[0]["run_manifest"]["versions"]["physical_schema"],
                "Current verified PostgreSQL source differs from v3")
        manifest = build_run_manifest(
            amended, base_dir=BASE_DIR, mode="offline_rescore", scope="m1_e_v3_strict4",
            case_source=CASES, runtime=runtime,
            config={"operation": "saved_sql_postgres_replay", "new_model_request_count": 0,
                    "source_run_ids": [report["run_manifest"]["run_id"] for report in reports]},
        )
        controller = AccessController()
        with tempfile.TemporaryDirectory(prefix="askdata_m1_e_v3_gold_") as temporary:
            for index, (case_id, candidate) in enumerate(REVIEWED.items(), 1):
                original, proposed, row = by_id[case_id], amended[index - 1], source_rows[case_id]
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
                old_score = strict(actual.columns, actual.rows, gold, original)
                proposed_score = strict(actual.columns, actual.rows, gold, proposed)
                loose = compare_results(
                    actual.columns, actual.rows, gold["columns"], gold["rows"],
                    bool(original.get("order_sensitive", True)),
                    order_by_column=original.get("order_by_column"),
                    top_n_tie_policy=original.get("top_n_tie_policy"),
                )
                require(old_score[0] is False and proposed_score[0] is True and
                        loose[0] is True and
                        len(actual.rows) == row["result_metrics"]["generated_result_rows"] and
                        len(gold["rows"]) == row["result_metrics"]["gold_result_rows"],
                        "Independent PostgreSQL replay did not confirm case: " + case_id)
                evidence.append({
                    "case_id": case_id, "source_run_id": row["run_id"],
                    "generated_sql_sha256": candidate["sql_sha256"],
                    "generated_sql": row["generated_sql"],
                    "postgres_gold_sql": gold["gold_sql"],
                    "actual_columns": actual.columns, "actual_rows": actual.rows,
                    "gold_columns": gold["columns"], "gold_rows": gold["rows"],
                    "original_strict": old_score[0], "original_reason": old_score[1],
                    "candidate_strict": proposed_score[0], "candidate_reason": proposed_score[1],
                    "loose_correct": loose[0], "alias_additions": candidate["aliases"],
                    "allowed_auxiliary_columns_additions": candidate["auxiliary_columns"],
                })
                print(f"[{index}/4] {case_id}: {old_score[0]} -> {proposed_score[0]}",
                      flush=True)
    require(sha256(CASES) == FORMAL_SHA256 and all(
        sha256(path) == SOURCES[path.name]["sha256"] for path in source_paths
    ), "Source evidence changed during replay")
    report = {
        "stage": "M1 E v3 four-case PostgreSQL strict-policy review",
        "run_status": "complete", "recorded_at": datetime.now(timezone.utc).isoformat(),
        "run_manifest": manifest,
        "source_report_sha256": {path.name: sha256(path) for path in source_paths},
        "formal_cases_sha256": FORMAL_SHA256,
        "formal_cases_modified": False, "new_model_request_count": 0,
        "summary": {
            "case_count": 4, "original_strict_pass_count": 0,
            "candidate_strict_pass_count": 4, "loose_pass_count": 4,
            "alias_addition_count": 7, "auxiliary_allow_count": 2,
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
                        default=RESULTS / "m1_e_v3_strict4_rescore_server.json")
    args = parser.parse_args()
    report = replay(args.output.resolve())
    print(json.dumps({"output": str(args.output), "summary": report["summary"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
