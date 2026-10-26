"""Read-only review of downloaded M1 A rescore/Gold reports; saves separate evidence."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from app.config import BASE_DIR
from evaluation.case_selection import load_case_ids
from evaluation.run_benchmark import compare_results_strict, summarize
from evaluation.run_manifest import build_run_manifest, _digest
from scripts.audit_m1_a_classic import ALIASES, require


RESULTS = BASE_DIR / "evaluation/results"


def read(name: str):
    data = (RESULTS / name).read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def case_strict(row, expected_columns, expected_rows, case, aliases=None):
    return compare_results_strict(row["actual_columns"], row["actual_rows"],
        expected_columns, expected_rows, case.get("order_sensitive", False),
        order_by_column=case.get("order_by_column"),
        column_aliases=case.get("column_aliases", {}) if aliases is None else aliases,
        allowed_auxiliary_columns=case.get("allowed_auxiliary_columns"),
        top_n_tie_policy=case.get("top_n_tie_policy"))


def review():
    names = ["m1_a_live_classic_alias_rescore_server.json", "m1_a_duckdb_gold_server.json",
        "m1_a_live_classic_alias_rescore_local.json", "m1_a_live_classic_server.json",
        "m1_a_duckdb_gold_local.json", "m1_a_e2e_behavior_server.json"]
    originals = {name: (RESULTS / name).read_bytes() for name in names}
    loaded = {name: read(name) for name in names}
    server = loaded[names[0]][0]
    gold = loaded[names[1]][0]
    local = loaded[names[2]][0]
    live = loaded[names[3]][0]
    local_gold = loaded[names[4]][0]
    e2e = loaded[names[5]][0]
    backup_path = RESULTS / "m1_all_cases_before_classic_aliases_20261007.jsonl"
    formal_path = BASE_DIR / "evaluation/cases/all_cases.jsonl"
    backup_bytes, formal_bytes = backup_path.read_bytes(), formal_path.read_bytes()
    old = [json.loads(line) for line in backup_bytes.decode("utf-8").splitlines() if line.strip()]
    new = [json.loads(line) for line in formal_bytes.decode("utf-8").splitlines() if line.strip()]
    old_by_id, new_by_id = {c["case_id"]: c for c in old}, {c["case_id"]: c for c in new}
    require(len(old) == len(new) == len(old_by_id) == len(new_by_id) == 430, "Incorrect full case count")
    require(list(old_by_id) == list(new_by_id), "Full case IDs/order changed")
    changed = []
    addition_count = 0
    for before, after in zip(old, new):
        if before != after:
            case_id = before["case_id"]
            changed.append(case_id)
            require({k: v for k, v in before.items() if k != "column_aliases"} ==
                    {k: v for k, v in after.items() if k != "column_aliases"}, "Non-alias mutation")
            expected = json.loads(json.dumps(before))
            for column, additions in ALIASES[case_id].items():
                expected.setdefault("column_aliases", {}).setdefault(column, []).extend(additions)
                addition_count += len(additions)
            require(after == expected, "Unreviewed alias mutation")
    require(set(changed) == set(ALIASES) and len(changed) == 8 and addition_count == 13,
            "Alias change scope differs")
    identity = server["run_manifest"]["source_identity"]
    versions = server["run_manifest"]["versions"]
    for name, (report, digest) in loaded.items():
        require(report["run_status"] == "complete", "Incomplete report: " + name)
        require(report["run_manifest"]["source_identity"] == identity and
                report["run_manifest"]["versions"] == versions, "Source/code version mismatch: " + name)
    old_classic, new_classic = [c for c in old if c["classic"]], [c for c in new if c["classic"]]
    ids = [c["case_id"] for c in new_classic]
    require(len(ids) == len(set(ids)) == 49, "Incorrect classic count")
    require(server["mode"] == server["run_manifest"]["mode"] == "offline_rescore" and
            server["run_manifest"]["scope"] == "classic", "Wrong rescore mode")
    require(server["formal_aliases_applied"] is True and server["alias_additions"] == ALIASES and
            server["changed_case_ids"] == changed, "Wrong formal alias record")
    require(server["source_run_id"] == live["run_manifest"]["run_id"] and
            server["source_report_sha256"] == loaded[names[3]][1], "Original source identity differs")
    require(server["source_manifest"] == live["run_manifest"] and server["source_summary"] == live["summary"],
            "Original source metadata differs")
    require(server["original_dataset_version"] == _digest(old_classic) == live["run_manifest"]["dataset"]["version"], "Old dataset differs")
    require(server["formal_dataset_version"] == _digest(new_classic) == server["run_manifest"]["dataset"]["version"], "Formal dataset differs")
    require(server["original_cases_sha256"] == hashlib.sha256(backup_bytes).hexdigest() and
            server["formal_cases_sha256"] == hashlib.sha256(formal_bytes).hexdigest(), "Full case file hash differs")
    for key in ["summary", "alias_additions", "changed_case_ids", "original_dataset_version",
                "formal_dataset_version", "original_cases_sha256", "formal_cases_sha256", "review_report_sha256"]:
        require(server[key] == local[key], "Local/server calibration metadata differs: " + key)
    require(server["run_manifest"]["fingerprint"] == local["run_manifest"]["fingerprint"], "Rescore fingerprint differs")
    require([c["case_id"] for c in server["cases"]] == ids == server["run_manifest"]["dataset"]["case_ids"], "Classic report IDs differ")
    local_index = {c["case_id"]: c for c in local["cases"]}
    live_index = {c["case_id"]: c for c in live["cases"]}
    checks = []
    raw_identical = 0
    for row in server["cases"]:
        case_id = row["case_id"]
        counterpart = local_index[case_id]
        before, after = old_by_id[case_id], new_by_id[case_id]
        original_ok, original_reason = case_strict(row, row["gold_columns"], row["gold_rows"], before)
        formal_ok, formal_reason = case_strict(row, row["gold_columns"], row["gold_rows"], after)
        cross_ok, cross_reason = case_strict(row, counterpart["gold_columns"], counterpart["gold_rows"], after)
        require(original_ok == row["source_strict_result_correct"] == row["original_replayed_strict_result_correct"] == live_index[case_id]["strict_result_correct"], "Original scoring differs: " + case_id)
        require(formal_ok and cross_ok and row["strict_result_correct"] and row["result_correct"], "Formal/cross-environment scoring differs: " + case_id)
        for key in ["generated_sql", "gold_sql", "actual_columns", "gold_columns", "column_aliases", "alias_additions", "order_sensitive"]:
            require(row[key] == counterpart[key], "Local/server case metadata differs: " + case_id)
        require(row["column_aliases"] == after.get("column_aliases", {}) and row["alias_additions"] == ALIASES.get(case_id, {}), "Case aliases differ")
        identical = row["actual_rows"] == counterpart["actual_rows"] and row["gold_rows"] == counterpart["gold_rows"]
        raw_identical += int(identical)
        checks.append({"case_id": case_id, "original_strict_correct": original_ok,
            "formal_strict_correct": formal_ok, "against_local_gold_correct": cross_ok,
            "raw_local_server_rows_identical": identical, "strict_reason": formal_reason,
            "actual_row_count": len(row["actual_rows"]), "gold_row_count": len(row["gold_rows"])})
    require(sum(c["original_strict_correct"] for c in checks) == 41, "Original strict count differs")
    require(server["summary"]["strict_pass_count"] == len(checks) == 49 and
            server["summary"]["new_model_request_count"] == 0, "Rescore summary differs")
    # Gold preceded the explicit alias closure. Match the preserved original
    # 79-case definitions, then prove current definitions only add aliases.
    gold_manifest = gold["run_manifest"]
    require(gold_manifest["mode"] == "gold" and gold_manifest["scope"] == "all", "Wrong Gold mode/scope")
    gold_ids = load_case_ids(BASE_DIR / "evaluation/cases/m1_a_duckdb_regression.json")
    require(gold_ids == gold_manifest["dataset"]["case_ids"] == [c["case_id"] for c in gold["cases"]], "Gold case list/order differs")
    require(len(gold_ids) == len(set(gold_ids)) == 79 and sum(old_by_id[i]["classic"] for i in gold_ids) == 49,
            "Expected classic49 plus extension30")
    old_gold_cases = [old_by_id[i] for i in gold_ids]
    require(_digest(old_gold_cases) == gold_manifest["dataset"]["version"] == local_gold["run_manifest"]["dataset"]["version"], "Pre-alias Gold dataset differs")
    require(summarize(gold["cases"], "gold") == gold["summary"], "Gold summary differs from case records")
    local_gold_index = {c["case_id"]: c for c in local_gold["cases"]}
    gold_checks = []
    for row in gold["cases"]:
        case_id = row["case_id"]
        definition = old_by_id[case_id]
        counterpart = local_gold_index[case_id]
        require(row["generated_sql"] == definition["gold_sql"] == counterpart["generated_sql"] and
                row["query"] == definition["query"] and row["agent_action"] == "gold_sql", "Wrong Gold SQL/question/action")
        require(row["sql_execution_success"] is True and row["result_correct"] is True and
                row["strict_result_correct"] is True and row["column_match"] is True,
                "Gold case did not pass: " + case_id)
        require(row["result_metrics"]["correct"] is True and row["result_metrics"]["strict_correct"] is True and
                row["result_metrics"]["gold_result_generated"] is True and row["gold_result_source"] == "execution",
                "Gold nested state/cache source differs")
        require(not row.get("benchmark_error") and not row.get("error_stage") and not row["trace"]["errors"], "Gold error recorded")
        require(row["result_metrics"]["generated_result_rows"] == counterpart["result_metrics"]["generated_result_rows"] and
                row["result_metrics"]["gold_result_rows"] == counterpart["result_metrics"]["gold_result_rows"], "Gold row count differs")
        require(row["run_id"] == gold_manifest["run_id"] and row["trace_id"] == gold_manifest["run_id"] + ":" + case_id,
                "Gold run/trace mismatch")
        gold_checks.append({"case_id": case_id, "sql_execution_success": True,
            "result_correct": True, "strict_result_correct": True,
            "local_server_row_count_equal": True, "gold_result_source": "execution",
            "row_count": row["result_metrics"]["generated_result_rows"]})
    local_manifest = build_run_manifest(new_classic, base_dir=BASE_DIR, mode="offline_rescore", scope="classic",
        config=server["run_manifest"]["config"], case_source=formal_path, source_identity=identity)
    require(local_manifest["versions"] == versions and local_manifest["dataset"] == server["run_manifest"]["dataset"],
            "Current local versions differ")
    require(gold["summary"]["model_request_attempt_count"] == 0 and gold["summary"]["unscored_count"] == 0,
            "Gold model requests/unscored cases")
    for name, data in originals.items():
        require((RESULTS / name).read_bytes() == data, "Source report changed")
    require(backup_path.read_bytes() == backup_bytes and formal_path.read_bytes() == formal_bytes, "Case files changed")
    output = {"stage": "M1 A final archive review", "status": "passed", "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "report_sha256": {name: pair[1] for name, pair in loaded.items()}, "source_identity": identity,
        "verified_versions": versions, "server_run_ids": {"classic_rescore": server["run_manifest"]["run_id"],
            "gold": gold_manifest["run_id"], "e2e": e2e["run_manifest"]["run_id"]},
        "summary": {"server_rescore_case_count": 49, "server_original_strict_pass_count": 41,
            "server_formal_strict_pass_count": 49, "local_server_raw_identical_case_count": raw_identical,
            "server_gold_case_count": 79, "server_gold_strict_pass_count": 79,
            "changed_cases": 8, "explicit_alias_additions": 13, "new_model_requests": 0},
        "dataset_versions": {"classic_before": server["original_dataset_version"], "classic_after": server["formal_dataset_version"],
            "gold_before_alias_closure": gold_manifest["dataset"]["version"],
            "current_79_case_definition_version": _digest([new_by_id[i] for i in gold_ids])},
        "gold_dataset_difference_explained": "Gold executed before alias closure. Its original dataset matches the preserved backup; current definitions only append 13 approved aliases. Gold SQL/questions/results/scoring rules unchanged.",
        "classic_case_checks": checks, "gold_case_checks": gold_checks,
        "limits": ["Gold report stores scoring flags and row counts, not full rows; no new 79-case SQL replay was performed.",
            "Gold validates fixed SQL/data material; it does not measure live model accuracy.",
            "Known E2E/month-resolution/schema-prefix/response-quality followups remain recorded."]}
    path = RESULTS / "m1_a_server_archive_review.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], indent=2))
    print(json.dumps(output["dataset_versions"], indent=2))
    return output


if __name__ == "__main__":
    review()
