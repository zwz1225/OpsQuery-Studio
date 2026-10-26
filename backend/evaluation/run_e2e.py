"""Service-entry evaluation for data QA and ordered behavior scenarios."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import time
from typing import Any
from unittest.mock import patch

from app.config import BASE_DIR, settings
from app.errors import PipelineStageError
from app.datasources import DataSourceRuntime, create_datasource_runtime
from app.security import AccessController
from evaluation.gold_result import DEFAULT_CACHE_DIR, resolve_gold_result
from evaluation.run_benchmark import (
    CASES_PATH, LOOSE_MAPPING_LIMIT_REASON, RESULT_DIR,
    compare_results, compare_results_strict, load_cases,
)
from evaluation.run_manifest import build_run_manifest
from evaluation.snapshot import BenchmarkSnapshotManager


DEFAULT_CASE_LIST = BASE_DIR / "evaluation" / "cases" / "e2e_smoke.json"


def load_e2e_cases(path: Path, source: Path = CASES_PATH) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    specs = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(specs, list) or not specs:
        raise ValueError("E2E case list must contain a nonempty cases array")
    indexed = {str(row["case_id"]): row for row in load_cases(source, set(), False)}
    selected = []
    seen = set()
    for spec in specs:
        if not isinstance(spec, dict) or not isinstance(spec.get("case_id"), str):
            raise ValueError("Invalid E2E case specification")
        case_id = spec["case_id"]
        if case_id in seen:
            raise ValueError(f"Duplicate E2E case: {case_id}")
        seen.add(case_id)
        if case_id in indexed:
            selected.append({**indexed[case_id], **spec})
        elif (case_id.startswith("E2E-") and isinstance(spec.get("query"), str)
              and spec["query"].strip() and
              spec.get("scenario") in {"growth_ops", "channel_ops", "content_ops"}):
            selected.append(spec)
        else:
            raise ValueError(f"Unknown E2E case without complete inline definition: {case_id}")
        operation = selected[-1].get("operation", "submit")
        if operation not in {"submit", "get_task_denied", "clarify",
                             "submit_with_injected_workflow_error"}:
            raise ValueError(f"Unknown E2E operation: {operation}")
        source_id = selected[-1].get("source_case_id")
        if operation in {"get_task_denied", "clarify"} and source_id not in seen - {case_id}:
            raise ValueError(f"E2E case {case_id} needs an earlier source_case_id")
        if source_id:
            source_case = next(case for case in selected[:-1]
                               if case["case_id"] == source_id)
            source_user = str(source_case.get("user_id") or
                              f"demo_{source_case['scenario']}")
            target_user = str(selected[-1].get("user_id") or
                              f"demo_{selected[-1]['scenario']}")
            if operation == "get_task_denied" and source_user == target_user:
                raise ValueError(f"Permission case {case_id} uses the source user")
            if operation == "clarify" and source_user != target_user:
                raise ValueError(f"Clarification case {case_id} changed user")
        if (case_id not in indexed and selected[-1].get("score_result") is not False
                and not selected[-1].get("gold_sql")):
            raise ValueError(f"Scored inline E2E case {case_id} needs gold_sql")
    return selected


def evaluate_e2e_case(
    case: dict[str, Any],
    service: Any,
    engine: Any,
    controller: Any,
    *,
    run_id: str,
    data_version: str,
    gold_cache_dir: Path = DEFAULT_CACHE_DIR,
    use_cached_gold: bool = True,
    prior_results: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    runtime = getattr(service, "runtime", None)
    if isinstance(runtime, DataSourceRuntime):
        runtime.assert_shared(service.schema_index, service.workflow)
        runtime.assert_executor(engine)
    source_labels = ({"source_identity": runtime.identity.public(), "backend": runtime.identity.backend,
                      "dialect": runtime.identity.dialect} if isinstance(runtime, DataSourceRuntime) else {})
    case_id = str(case["case_id"])
    user_id = str(case.get("user_id") or f"demo_{case['scenario']}")
    session_id = f"evaluation-{run_id}-{case.get('session_group') or case_id}"
    operation = str(case.get("operation") or "submit")
    behavior_type = str(case.get("behavior_type") or "data_query")
    started = time.perf_counter()
    try:
        prior = (prior_results or {}).get(str(case.get("source_case_id") or ""))
        if operation == "get_task_denied":
            if not prior or not prior.get("task_id"):
                raise ValueError("Permission case has no source task")
            denied = False
            observed = "none"
            try:
                service.get_task(prior["task_id"], user_id=user_id)
            except PermissionError:
                denied = True
                observed = "PermissionError"
            except Exception as exc:
                observed = type(exc).__name__
            return {
                **source_labels,
                "case_id": case_id, "run_id": run_id,
                "trace_id": f"{run_id}:{case_id}", "query": case["query"],
                "scenario": case["scenario"], "operation": operation,
                "behavior_type": behavior_type, "route": "task_access",
                "status": "denied" if denied else "unexpected_access",
                "route_correct": denied, "status_correct": denied,
                "behavior_checks": {"permission_denied": denied},
                "behavior_correct": denied, "observed_exception": observed,
                "source_case_id": case["source_case_id"],
                "sql_execution_success": False, "result_correct": None,
                "strict_result_correct": None,
                "comparison_reason": "cross-user task access denied" if denied
                else f"cross-user task access was not denied: {observed}",
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            }
        if operation == "clarify":
            if not prior or prior.get("status") != "waiting_clarification":
                raise ValueError("Clarification source did not pause")
            options = ((prior.get("trace") or {}).get("clarification") or {}).get("options") or []
            option_index = int(case.get("clarification_option_index", 0))
            if option_index < 0 or option_index >= len(options):
                raise ValueError("Clarification option is unavailable")
            selected_option = options[option_index]
            result = service.clarify(
                prior["task_id"], str(selected_option["id"]), user_id=user_id,
            )
        elif operation == "submit_with_injected_workflow_error":
            stage = str(case.get("injected_stage") or "")
            if stage not in {"preprocess", "qa_answer", "sql_generation"}:
                raise ValueError("Unsupported injected failure stage")
            with patch.object(service.workflow, "invoke", side_effect=PipelineStageError(
                stage, "M0 controlled workflow failure",
            )):
                result = service.submit(case["query"], session_id, user_id=user_id)
        else:
            result = service.submit(case["query"], session_id, user_id=user_id)
            if result.status == "waiting_clarification" and case.get("clarification_option_id"):
                result = service.clarify(
                    result.task_id, str(case["clarification_option_id"]), user_id=user_id,
                )
        route_ok = result.route == case.get("expected_route", "database_query")
        status_ok = result.status == case.get("expected_status", "completed")
        checks = {"route": route_ok, "status": status_ok}
        if "expected_sql_present" in case:
            checks["sql_present"] = bool(result.sql) == bool(case["expected_sql_present"])
        if "expected_sql_contains" in case:
            checks["sql_contains"] = all(
                str(fragment).lower() in str(result.sql or "").lower()
                for fragment in case["expected_sql_contains"]
            )
        if "expected_tool_success" in case:
            checks["tool_success"] = any(
                item.get("success") is True for item in result.tool_calls
            ) == bool(case["expected_tool_success"])
        if "expected_empty_rows" in case:
            checks["empty_rows"] = (len(getattr(result, "rows", []) or []) == 0) == bool(
                case["expected_empty_rows"])
        if "expected_analysis_present" in case:
            checks["analysis_present"] = bool((result.analysis or "").strip()) == bool(
                case["expected_analysis_present"])
        if "expected_clarification_options_min" in case:
            checks["clarification_options"] = bool(result.clarification) and len(
                result.clarification.options) >= int(case["expected_clarification_options_min"])
        if "expected_failure_stage" in case:
            checks["failure_stage"] = any(
                item.get("stage") == case["expected_failure_stage"] and
                item.get("success") is False for item in result.execution_log
            )
        if "expected_workflow_mode" in case:
            checks["workflow_mode"] = result.workflow_mode == case["expected_workflow_mode"]
        response = {
            **source_labels,
            "case_id": case_id,
            "run_id": run_id,
            "trace_id": f"{run_id}:{case_id}",
            "task_id": result.task_id,
            "query": case["query"],
            "scenario": case["scenario"],
            "operation": operation,
            "behavior_type": behavior_type,
            "route": result.route,
            "status": result.status,
            "response_message": getattr(result, "message", None),
            "response_analysis": getattr(result, "analysis", None),
            "route_reason": getattr(result, "route_reason", None),
            "direct_response_type": getattr(result, "direct_response_type", None),
            "workflow_mode": getattr(result, "workflow_mode", None),
            "result_validation_reason": getattr(result, "result_validation_reason", None),
            "standalone_query": getattr(result, "standalone_query", None),
            "route_correct": route_ok,
            "status_correct": status_ok,
            "behavior_checks": checks,
            "behavior_correct": all(checks.values()),
            "sql_execution_success": result.route == "database_query"
            and result.status == "completed" and bool(result.sql),
            "row_count": len(getattr(result, "rows", []) or []),
            "result_correct": None,
            "strict_result_correct": None,
            "comparison_reason": "result scoring not requested" if
            case.get("score_result") is False else "not a completed database query",
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
            "trace": {
                "schema_graph": getattr(result, "schema_graph", None),
                "execution_log": result.execution_log,
                "tool_calls": result.tool_calls,
                "clarification": result.clarification.model_dump(mode="json")
                if result.clarification else None,
            },
        }
        if operation == "clarify":
            response["source_case_id"] = case["source_case_id"]
            response["selected_clarification_option_id"] = selected_option["id"]
            response["selected_clarification_option"] = selected_option
        if response["sql_execution_success"] and case.get("score_result") is not False:
            response["generated_sql"] = result.sql
            try:
                scope = controller.resolve(user_id)
                gold = resolve_gold_result(
                    case, engine, scope, cache_dir=gold_cache_dir,
                    use_cached_gold=use_cached_gold, data_version=data_version,
                )
                actual_rows = result.rows
                if getattr(result, "truncated", False) or len(actual_rows) >= 200:
                    complete = engine.execute(
                        "short_video_ops", result.sql, scope, row_limit=10000,
                    )
                    if not complete.success or complete.truncated:
                        raise RuntimeError(
                            complete.error or "Generated result exceeds scoring row limit"
                        )
                    actual_rows = complete.rows
                    response["scoring_reexecuted"] = True
                loose, _, reason = compare_results(
                    result.columns, actual_rows, gold["columns"], gold["rows"],
                    bool(case.get("order_sensitive", True)),
                    order_by_column=case.get("order_by_column"),
                    top_n_tie_policy=case.get("top_n_tie_policy"),
                )
                if reason == LOOSE_MAPPING_LIMIT_REASON:
                    loose = None
                strict, strict_reason = compare_results_strict(
                    result.columns, actual_rows, gold["columns"], gold["rows"],
                    bool(case.get("order_sensitive", True)),
                    order_by_column=case.get("order_by_column"),
                    column_aliases=case.get("column_aliases"),
                    allowed_auxiliary_columns=case.get("allowed_auxiliary_columns"),
                    top_n_tie_policy=case.get("top_n_tie_policy"),
                )
                response.update({
                    "result_correct": loose,
                    "strict_result_correct": strict,
                    "comparison_reason": reason,
                    "strict_comparison_reason": strict_reason,
                    "gold_result_source": gold["source"],
                    "generated_result_rows": len(actual_rows),
                })
            except Exception as exc:
                response["comparison_reason"] = str(exc)
                response["error_stage"] = "result_scoring"
        return response
    except Exception as exc:
        return {
            **source_labels,
            "case_id": case_id,
            "run_id": run_id,
            "trace_id": f"{run_id}:{case_id}",
            "query": case["query"],
            "scenario": case["scenario"],
            "operation": operation,
            "behavior_type": behavior_type,
            "route_correct": False,
            "status_correct": False,
            "behavior_checks": {"service_entry": False},
            "behavior_correct": False,
            "sql_execution_success": False,
            "result_correct": None,
            "strict_result_correct": None,
            "comparison_reason": str(exc),
            "error_stage": "service_entry",
            "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        }


def summarize_e2e(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    scored = [row for row in rows if row.get("result_correct") is not None]
    strict_scored = [row for row in rows if row.get("strict_result_correct") is not None]
    behavior_by_type: dict[str, dict[str, int]] = {}
    for row in rows:
        category = str(row.get("behavior_type") or "data_query")
        bucket = behavior_by_type.setdefault(category, {"count": 0, "passed": 0})
        bucket["count"] += 1
        bucket["passed"] += int(bool(row.get("behavior_correct")))
    return {
        "case_count": count,
        "behavior_pass_count": sum(bool(row.get("behavior_correct")) for row in rows),
        "behavior_success_rate": sum(bool(row.get("behavior_correct")) for row in rows) / count
        if count else None,
        "behavior_by_type": behavior_by_type,
        "sql_case_count": sum(row.get("route") == "database_query" for row in rows),
        "result_scored_count": len(scored),
        "result_accuracy": sum(bool(row["result_correct"]) for row in scored) / len(scored)
        if scored else None,
        "strict_scored_count": len(strict_scored),
        "strict_result_accuracy": (
            sum(bool(row["strict_result_correct"]) for row in strict_scored)
            / len(strict_scored) if strict_scored else None
        ),
        "unscored_count": count - len(scored),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AskData service-entry evaluation")
    parser.add_argument("--case-list", type=Path, default=DEFAULT_CASE_LIST)
    parser.add_argument("--output", type=Path, default=RESULT_DIR / "benchmark_e2e_smoke.json")
    parser.add_argument("--save-snapshot", action="store_true")
    parser.add_argument("--use-cached-gold", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    if not settings.api_key:
        raise RuntimeError("E2E live evaluation needs LLM_API_KEY")
    cases = load_e2e_cases(args.case_list)
    scope_name = "behavior" if any(case["case_id"].startswith("E2E-") for case in cases) else "smoke"
    with create_datasource_runtime(settings) as runtime:
        manifest = build_run_manifest(
            cases, base_dir=BASE_DIR, mode="e2e", scope=scope_name,
            config={
                **settings.public_status(),
                "llm_temperature": settings.temperature,
                "user_roles": sorted({
                    str(case.get("user_id") or f"demo_{case['scenario']}") for case in cases
                }),
                "evaluation_date": date.today().isoformat(),
            },
            case_source=CASES_PATH, case_list=args.case_list,
            runtime=runtime,
        )
        from app.services.askdata_service import AskDataService
        service = AskDataService(runtime=runtime)
        engine = runtime.executor
        controller = AccessController()
        rows = []
        prior_results: dict[str, dict[str, Any]] = {}
        for case in cases:
            row = evaluate_e2e_case(
                case, service, engine, controller, run_id=manifest["run_id"],
                data_version=manifest["versions"]["data"],
                use_cached_gold=args.use_cached_gold,
                prior_results=prior_results,
            )
            rows.append(row)
            prior_results[case["case_id"]] = row
            print(f"[{len(rows)}/{len(cases)}] {case['case_id']}"
                  f" behavior={row['behavior_correct']} result={row['result_correct']}",
                  flush=True)
        report = {
            "run_manifest": manifest, "run_status": "complete",
            "summary": summarize_e2e(rows), "cases": rows,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temp = args.output.with_suffix(args.output.suffix + ".tmp")
        temp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(args.output)
        if args.save_snapshot:
            path = BenchmarkSnapshotManager.save(
                report, mode="e2e", scope=scope_name,
                dataset=manifest["dataset"], metadata=manifest["config"],
                run_manifest=manifest,
            )
            print(f"snapshot: {path}")
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
        print(f"report: {args.output}")


if __name__ == "__main__":
    main()
