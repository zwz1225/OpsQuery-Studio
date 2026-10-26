"""Offline evidence review of M1 A E2E; no model requests or report rewrites."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from app.config import BASE_DIR
from app.datasources import create_datasource_runtime
from app.security import AccessController
from evaluation.run_e2e import load_e2e_cases, summarize_e2e
from evaluation.run_benchmark import compare_results, compare_results_strict
from evaluation.gold_result import resolve_gold_result
from evaluation.run_manifest import build_run_manifest, data_digest


def require(condition, message):
    if not condition:
        raise ValueError(message)


def review():
    source = BASE_DIR / "evaluation/results/m1_a_e2e_behavior_server.json"
    source_bytes = source.read_bytes()
    saved = json.loads(source_bytes)
    manifest = saved["run_manifest"]
    case_path = BASE_DIR / "evaluation/cases/all_cases.jsonl"
    list_path = BASE_DIR / "evaluation/cases/e2e_behavior.json"
    case_bytes, list_bytes = case_path.read_bytes(), list_path.read_bytes()
    cases = load_e2e_cases(list_path)
    rows = saved["cases"]
    indexed = {c["case_id"]: c for c in rows}
    require(saved["run_status"] == "complete", "Incomplete source report")
    require(manifest["mode"] == "e2e" and manifest["scope"] == "behavior", "Unexpected mode/scope")
    require(len(rows) == len(indexed) == 8, "Expected 8 unique cases")
    require([c["case_id"] for c in cases] == [c["case_id"] for c in rows] == manifest["dataset"]["case_ids"], "Case IDs/order mismatch")
    require(summarize_e2e(rows) == saved["summary"], "Summary differs from case records")
    require(all(c["behavior_correct"] and all(c["behavior_checks"].values()) for c in rows), "Behavior check failed")
    require(all(c["run_id"] == manifest["run_id"] and c["trace_id"] == manifest["run_id"] + ":" + c["case_id"] for c in rows), "Run/trace mismatch")
    start, resume = indexed["E2E-CLARIFY-START"], indexed["E2E-CLARIFY-RESUME"]
    selected = resume["selected_clarification_option"]
    require(start["task_id"] == resume["task_id"] and resume["source_case_id"] == start["case_id"], "Clarification task changed")
    require(selected == start["trace"]["clarification"]["options"][0] and selected["id"] == resume["selected_clarification_option_id"], "Option changed")
    require(selected["label"] in resume["standalone_query"] and selected["description"] in resume["standalone_query"], "Option semantics missing from question")
    require(indexed["E2E-PERMISSION-READ"]["observed_exception"] == "PermissionError", "Wrong permission failure")
    require(not indexed["E2E-ROUTE-QA"]["trace"]["tool_calls"] and not indexed["E2E-ROUTE-DIRECT"]["trace"]["tool_calls"], "Unexpected database query")
    require(indexed["E2E-FAILURE-PREPROCESS"]["status"] == "failed" and indexed["E2E-FAILURE-PREPROCESS"]["workflow_mode"] == "failed_explicitly", "Controlled failure not explicit")
    replays = []
    with create_datasource_runtime() as runtime:
        identity = runtime.identity.public()
        require(identity == manifest["source_identity"], "Runtime source differs")
        local = build_run_manifest(cases, base_dir=BASE_DIR, mode="e2e", scope="behavior", config=manifest["config"],
            case_source=case_path, case_list=list_path, source_identity=identity)
        require(local["dataset"] == manifest["dataset"] and local["versions"] == manifest["versions"], "Dataset/code/data versions differ")
        classic = json.loads((BASE_DIR / "evaluation/results/m1_a_live_classic_server.json").read_text(encoding="utf-8"))
        require(classic["run_manifest"]["source_identity"] == identity and classic["run_manifest"]["versions"] == manifest["versions"], "Classic report source/code mismatch")
        graph_cases = []
        for row in rows:
            graph = (row.get("trace") or {}).get("schema_graph")
            if graph:
                require(graph["source_identity"] == identity, "Graph source mismatch: " + row["case_id"])
                graph_cases.append(row["case_id"])
        for case, row in zip(cases, rows):
            logs = (row.get("trace") or {}).get("execution_log") or []
            successful = [l for l in logs if l.get("stage") == "mcp_tool_call" and (l.get("result") or {}).get("success")]
            if not successful:
                continue
            result = successful[-1]["result"]
            scope = AccessController().resolve("demo_" + case["scenario"])
            actual = runtime.executor.execute("short_video_ops", result["sql"], scope, row_limit=10000)
            require(actual.success and not actual.truncated, "Replay failed: " + str(actual.error))
            require(actual.columns == result["columns"] and actual.rows == result["rows"] and len(actual.rows) == row["row_count"], "Rows differ from server: " + row["case_id"])
            evidence = {"case_id": row["case_id"], "sql": result["sql"], "columns": actual.columns,
                "rows": actual.rows, "server_rows_equal": True}
            if case.get("score_result") is not False:
                gold = resolve_gold_result(case, runtime.executor, scope, data_version=identity["data_version"])
                loose, _, reason = compare_results(actual.columns, actual.rows, gold["columns"], gold["rows"],
                    case.get("order_sensitive", False), order_by_column=case.get("order_by_column"), top_n_tie_policy=case.get("top_n_tie_policy"))
                strict, strict_reason = compare_results_strict(actual.columns, actual.rows, gold["columns"], gold["rows"],
                    case.get("order_sensitive", False), order_by_column=case.get("order_by_column"),
                    column_aliases=case.get("column_aliases"), allowed_auxiliary_columns=case.get("allowed_auxiliary_columns"), top_n_tie_policy=case.get("top_n_tie_policy"))
                require(loose is True and strict is True and row["result_correct"] is True and row["strict_result_correct"] is True, "Result comparison failed")
                evidence.update(loose_correct=loose, strict_correct=strict, gold_result_source=gold["source"], comparison_reason=reason, strict_reason=strict_reason)
            replays.append(evidence)
            print("Reviewed " + row["case_id"], flush=True)
        with runtime.executor.connect("short_video_ops") as conn:
            min_date, max_date, count = conn.execute("SELECT MIN(metric_date), MAX(metric_date), COUNT(*) FROM growth_daily_metrics").fetchone()
            months = [r[0] for r in conn.execute("SELECT DISTINCT strftime(metric_date, '%Y-%m') FROM growth_daily_metrics WHERE metric_date >= '2026-01-01' AND metric_date < '2027-01-01' ORDER BY 1").fetchall()]
        require(data_digest(BASE_DIR) == identity["data_version"], "Data changed during review")
    require(source.read_bytes() == source_bytes and case_path.read_bytes() == case_bytes and list_path.read_bytes() == list_bytes, "Source or case definitions changed")
    warnings = []
    tool_failures = []
    for row in rows:
        for log in (row.get("trace") or {}).get("execution_log") or []:
            validation = log.get("constraint_validation") or {}
            if validation.get("status") == "WARN":
                item = {"case_id": row["case_id"], "warnings": validation["warnings"]}
                if item not in warnings:
                    warnings.append(item)
            if log.get("stage") == "mcp_tool_call" and log.get("success") is False:
                tool_failures.append({"case_id": row["case_id"], "sql": log["arguments"]["sql"], "error": log["result"]["error"]})
    payload = {
        "stage": "M1 A E2E review", "status": "passed_with_recorded_followups", "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "source_report_sha256": hashlib.sha256(source_bytes).hexdigest(), "source_run_id": manifest["run_id"],
        "source_identity": identity, "verified_versions": manifest["versions"], "verified_dataset": manifest["dataset"],
        "summary": saved["summary"], "new_model_request_count": 0, "graph_source_identity_verified_cases": graph_cases,
        "clarification": {"same_task_id": start["task_id"], "selected_option": selected,
            "standalone_query": resume["standalone_query"], "resolution_log": resume["trace"]["execution_log"][0]},
        "sql_replays": replays, "constraint_warnings": warnings, "recovered_tool_failures": tool_failures,
        "growth_source_coverage": {"min_metric_date": str(min_date), "max_metric_date": str(max_date), "row_count": count, "months_in_2026": months},
        "response_quality_followups": [
            {"case_id": "E2E-ROUTE-DIRECT", "issue": "Reply identifies an internal preprocessing component instead of the user-facing assistant."},
            {"case_id": "E2E-ROUTE-QA", "issue": "Reply conflates new_users with registered or activated users and speculates about causes without evidence."},
            {"case_id": "GROWTH_OPS-001", "issue": "Validation calls a correct result partial because the fixed dataset contains only Jan-Aug; missing months alone do not prove incomplete SQL."}
        ],
        "limits": ["Service-entry in-process evaluation, not real HTTP/browser acceptance.",
            "Only the first clarification option was exercised; recovery is not a Gold-scored case.",
            "Empty-set equality verifies state and columns but alone cannot prove all date-boundary behavior.",
            "Four database-graph identities are directly visible; non-database/preprocessing-failure paths have no graph.",
            "No application, case, original report, or scoring-rule changes."]
    }
    out = BASE_DIR / "evaluation/results/m1_a_e2e_review_local.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "sql_replay_count": len(replays), "warn_case_count": len(warnings), "growth_source_coverage": payload["growth_source_coverage"]}, ensure_ascii=True))

if __name__ == "__main__":
    review()
