"""Independently audit the three M1 E PostgreSQL diagnostic downloads."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from app.config import BASE_DIR
from evaluation.gold_sql import select_gold_sql
from evaluation.report_identity import validate_report_identity
from evaluation.run_benchmark import compare_results, load_cases, summarize
from evaluation.run_manifest import _digest
from scripts.rescore_m1_e_postgres_aliases import score, digest


RESULTS = BASE_DIR / "evaluation/results"
CASES = RESULTS / "m1_e_all_cases_before_aliases_20261012.jsonl"
ROUND = RESULTS / "m1_e_round3_diagnostic_server_v2.json"
GROWTH = RESULTS / "m1_e_growth051_diagnostic_server_v2.json"
ALIASES = RESULTS / "m1_e_postgres_alias_rescore_server_v2.json"
CLASSIC = RESULTS / "m1_e_postgres_live_classic_server.json"
PHASE = RESULTS / "m1_e_postgres_live_phase83_server.json"
REVIEW = RESULTS / "m1_e_postgres_server_review_local.json"
EXPECTED_SOURCE = {
    "source_id": "short_video_ops_postgres", "backend": "postgresql",
    "dialect": "postgres", "physical_schema": "askdata_ops",
    "data_version": "882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1",
    "catalog_version": "94a801805965a90aa6ae015f28af196f88f72c1d887319dd1896a2973eaaa288",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def audit() -> dict:
    cases = load_cases(CASES, set(), False)
    by_id = {case["case_id"]: case for case in cases}
    require(len(cases) == len(by_id) == 430, "Formal case list changed")
    original_report = {
        row["case_id"]: row
        for path in (CLASSIC, PHASE)
        for row in json.loads(path.read_text(encoding="utf-8"))["cases"]
    }
    live_reports = []
    for path, case_ids in (
        (ROUND, ["GROWTH_OPS-150", "GROWTH_OPS-148", "CHANNEL_OPS-136"]),
        (GROWTH, ["GROWTH_OPS-051"]),
    ):
        report = json.loads(path.read_text(encoding="utf-8"))
        manifest = validate_report_identity(report)
        require(report.get("run_status") == "complete"
                and report["summary"] == summarize(report["cases"], "live")
                and manifest["mode"] == "live"
                and manifest["dataset"]["case_ids"] == case_ids
                and manifest["dataset"]["version"] == _digest([by_id[cid] for cid in case_ids])
                and manifest["source_verification"]["table_count"] == 41
                and manifest["source_verification"]["full_typed_row_match_count"] == 41
                and manifest["source_verification"]["readonly_table_acl_match_count"] == 41
                and all(manifest["source_identity"].get(key) == value
                        for key, value in EXPECTED_SOURCE.items()),
                "Invalid live report or source: " + path.name)
        live_reports.append((path, report, manifest))
    round_report = live_reports[0][1]
    require(all(row["sql_execution_success"] is True
                and row["result_correct"] is True
                and row["strict_result_correct"] is True
                and row["result_metrics"]["gold_result_source"] == "execution"
                and row["gold_sql"] == select_gold_sql(
                    by_id[row["case_id"]], live_reports[0][2]["source_identity"],
                ).sql
                for row in round_report["cases"]),
            "Three failed SQL cases are not fully recovered")
    growth = live_reports[1][1]["cases"][0]
    require(growth["sql_execution_success"] is False
            and growth["result_correct"] is False
            and growth["strict_result_correct"] is False
            and len(growth["trace"]["tool_calls"]) == 3
            and all(call["success"] is False for call in growth["trace"]["tool_calls"])
            and "SQLSTATE 42883" in growth["result_metrics"]["reason"]
            and "ua.is_activated = true" in growth["generated_sql"],
            "GROWTH_OPS-051 failure evidence changed")

    alias_report = json.loads(ALIASES.read_text(encoding="utf-8"))
    manifest = alias_report["run_manifest"]
    comparable = {key: value for key, value in manifest.items()
                  if key not in ("run_id", "created_at", "fingerprint")}
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    candidates = review["candidate_aliases"]
    require(alias_report["run_status"] == "complete"
            and alias_report["formal_aliases_applied"] is False
            and alias_report["new_model_request_count"] == 0
            and alias_report["source_cases_sha256"] == digest(CASES)
            and alias_report["review_report_sha256"] == digest(REVIEW)
            and alias_report["source_report_sha256"] == {
                CLASSIC.name: digest(CLASSIC), PHASE.name: digest(PHASE),
            }
            and manifest["fingerprint"] == _digest(comparable)
            and manifest["source_identity"] == live_reports[0][2]["source_identity"]
            and manifest["source_identity"] == live_reports[1][2]["source_identity"]
            and len(candidates) == len(alias_report["cases"]) == 14
            and alias_report["summary"]["alias_addition_count"] == 23,
            "Independent alias report provenance changed")
    amended_cases = []
    for item, evidence in zip(candidates, alias_report["cases"]):
        case_id = item["case_id"]
        original = by_id[case_id]
        amended = deepcopy(original)
        require(evidence["case_id"] == case_id
                and evidence["generated_sql"] == original_report[case_id]["generated_sql"]
                and evidence["source_run_id"] == original_report[case_id]["run_id"]
                and evidence["selected_postgres_gold_sql"] == select_gold_sql(
                    original, manifest["source_identity"],
                ).sql
                and evidence["alias_additions"] == item["missing_explicit_aliases"],
                "Alias case source or selected SQL mismatch: " + case_id)
        for pair in item["missing_explicit_aliases"]:
            amended.setdefault("column_aliases", {}).setdefault(pair["expected"], []).append(pair["actual"])
        actual_columns, actual_rows = evidence["actual_columns"], evidence["actual_rows"]
        gold = {"columns": evidence["gold_columns"], "rows": evidence["gold_rows"]}
        require(score(actual_columns, actual_rows, gold, original)[0] is False
                and score(actual_columns, actual_rows, gold, amended)[0] is True
                and score(gold["columns"], gold["rows"], {
                    "columns": original["expected_columns"],
                    "rows": original["expected_rows"],
                }, original)[0] is True
                and compare_results(
                    actual_columns, actual_rows, gold["columns"], gold["rows"],
                    bool(original.get("order_sensitive", True)),
                    order_by_column=original.get("order_by_column"),
                    top_n_tie_policy=original.get("top_n_tie_policy"),
                )[0] is True,
                "Alias values or strict mapping do not independently reproduce: " + case_id)
        amended_cases.append(amended)
    require(manifest["dataset"]["version"] == _digest(amended_cases)
            and manifest["dataset"]["case_ids"] == [item["case_id"] for item in candidates]
            and alias_report["summary"] == {
                "case_count": 14, "original_replayed_strict_pass_count": 0,
                "amended_strict_pass_count": 14, "amended_strict_accuracy": 1.0,
                "loose_pass_count": 14, "alias_addition_count": 23,
            }, "Alias report summary or dataset version mismatch")
    return {
        "run_status": "complete",
        "round3": {"executed": 3, "loose_pass": 3, "strict_pass": 3},
        "growth051": {"executed": 0, "tool_failures": 3,
                      "sqlstate": "42883", "invalid_comparison": "bigint = true"},
        "aliases": {"cases": 14, "additions": 23, "old_strict_pass": 0,
                    "new_strict_pass": 14, "postgres_replayed": True},
        "source_identity": manifest["source_identity"],
        "files_sha256": {path.name: digest(path) for path in (ROUND, GROWTH, ALIASES)},
    }


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
