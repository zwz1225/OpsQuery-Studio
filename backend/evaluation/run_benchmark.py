from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import date
from itertools import permutations
import json
import math
import re
import statistics
import threading
import time
from pathlib import Path
from typing import Any

from app.config import BASE_DIR, settings
from app.errors import PipelineStageError
from app.model_client import ModelClient
from app.datasources import DataSourceRuntime, create_datasource_runtime
from app.datasources.contracts import ReadOnlyExecutor, SourceIdentity
from app.retrieval import SchemaGraphBuilder, SchemaIndex
from app.security import AccessController
from evaluation.models import EvaluationResult
from evaluation.gold_result import DEFAULT_CACHE_DIR, gold_metrics, gold_result_evidence, resolve_gold_result
from evaluation.gold_sql import select_gold_sql
from evaluation.run_manifest import build_run_manifest
from evaluation.report_identity import require_resumable
from evaluation.report import BenchmarkReportBuilder
from evaluation.case_selection import load_case_ids, select_cases
from evaluation.snapshot import BenchmarkSnapshotManager
from evaluation.trace import EvaluationTrace


CASES_PATH = BASE_DIR / "evaluation" / "cases" / "all_cases.jsonl"
RESULT_DIR = BASE_DIR / "evaluation" / "results"
LOOSE_MAPPING_LIMIT_REASON = "宽松列匹配候选过多，未评分"


def load_cases(path: Path, scenarios: set[str], classic_only: bool) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if scenarios:
        rows = [row for row in rows if row["scenario"] in scenarios]
    if classic_only:
        rows = [row for row in rows if row["classic"]]
    return rows


def row_values(rows: list[dict[str, Any]]) -> list[list[Any]]:
    return [list(row.values()) for row in rows]


def values_equivalent(actual: Any, expected: Any, column: str) -> bool:
    if actual is None or expected is None:
        return actual is expected
    if (
        isinstance(actual, (int, float))
        and isinstance(expected, (int, float))
        and not isinstance(actual, bool)
        and not isinstance(expected, bool)
    ):
        if isinstance(expected, int):
            tolerance = 1e-8
        else:
            normalized = column.lower()
            # Match complete metric-name parts: "duration" contains "ratio",
            # but an average duration is not a rate metric.
            precision = 4 if re.search(
                r"(?:^|_)(?:rate|ratio|ctr|retention|confidence)(?:_|$)",
                normalized,
            ) else 2
            tolerance = 0.5 * (10 ** -precision) + 1e-9
        return math.isclose(float(actual), float(expected), rel_tol=1e-9, abs_tol=tolerance)

    actual_text = str(actual)
    expected_text = str(expected)
    if actual_text == expected_text:
        return True
    if re.fullmatch(r"\d{4}-\d{2}", expected_text):
        return actual_text.startswith(expected_text + "-01")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", expected_text):
        return actual_text.startswith(expected_text)
    return False


def rows_equivalent(
    actual_rows: list[list[Any]],
    expected_rows: list[list[Any]],
    expected_columns: list[str],
) -> bool:
    unmatched = list(actual_rows)
    for expected in expected_rows:
        matched_index = next(
            (
                index
                for index, actual in enumerate(unmatched)
                if all(
                    values_equivalent(actual_value, expected_value, column)
                    for actual_value, expected_value, column in zip(
                        actual, expected, expected_columns
                    )
                )
            ),
            None,
        )
        if matched_index is None:
            return False
        unmatched.pop(matched_index)
    return not unmatched


def ordered_rows_equivalent(
    actual_rows: list[list[Any]],
    expected_rows: list[list[Any]],
    expected_columns: list[str],
) -> bool:
    """Compare rows positionally while reusing the business value rules."""
    if len(actual_rows) != len(expected_rows):
        return False
    return all(
        len(actual) == len(expected)
        and all(
            values_equivalent(actual_value, expected_value, column)
            for actual_value, expected_value, column in zip(
                actual, expected, expected_columns
            )
        )
        for actual, expected in zip(actual_rows, expected_rows)
    )


def ordered_rows_equivalent_with_ties(
    actual_rows: list[list[Any]],
    expected_rows: list[list[Any]],
    expected_columns: list[str],
    order_by_column: str,
) -> bool:
    """Preserve primary sort order while accepting permutations within ties."""
    if len(actual_rows) != len(expected_rows) or order_by_column not in expected_columns:
        return False
    key_index = expected_columns.index(order_by_column)
    start = 0
    while start < len(expected_rows):
        end = start + 1
        while end < len(expected_rows) and values_equivalent(
            expected_rows[end][key_index], expected_rows[start][key_index],
            order_by_column,
        ):
            end += 1
        if not rows_equivalent(
            actual_rows[start:end], expected_rows[start:end], expected_columns,
        ):
            return False
        start = end
    return True


def top_n_boundary_equivalent(
    actual_rows: list[list[Any]],
    expected_rows: list[list[Any]],
    expected_columns: list[str],
    order_by_column: str,
    policy: dict[str, Any],
) -> bool:
    """Accept verified alternative members only at an annotated Top N cutoff."""
    if (policy.get("limit") != len(expected_rows) or
            len(actual_rows) != len(expected_rows) or
            order_by_column not in expected_columns):
        return False
    cutoff = policy.get("boundary_value")
    candidates = policy.get("boundary_candidates")
    if not isinstance(cutoff, (int, float)) or not isinstance(candidates, list):
        return False
    key_index = expected_columns.index(order_by_column)
    prefix_count = 0
    for index, row in enumerate(expected_rows):
        score = row[key_index]
        if not isinstance(score, (int, float)):
            return False
        if score > cutoff and prefix_count == index:
            prefix_count += 1
        elif not values_equivalent(score, cutoff, order_by_column):
            return False
    if prefix_count >= len(expected_rows):
        return False
    if not ordered_rows_equivalent_with_ties(
        actual_rows[:prefix_count], expected_rows[:prefix_count],
        expected_columns, order_by_column,
    ):
        return False
    try:
        available = [[candidate[column] for column in expected_columns]
                     for candidate in candidates]
    except (KeyError, TypeError):
        return False
    if (len(available) < len(expected_rows) - prefix_count or
            any(not values_equivalent(row[key_index], cutoff, order_by_column)
                for row in available)):
        return False
    for actual in actual_rows[prefix_count:]:
        matched_index = next((index for index, candidate in enumerate(available)
                              if len(actual) == len(candidate) and all(
                                  values_equivalent(value, target, column)
                                  for value, target, column in zip(
                                      actual, candidate, expected_columns))), None)
        if matched_index is None:
            return False
        available.pop(matched_index)
    return True


def compare_results(
    actual_columns: list[str],
    actual_rows: list[dict[str, Any]],
    expected_columns: list[str],
    expected_rows: list[dict[str, Any]],
    order_sensitive: bool,
    *,
    order_by_column: str | None = None,
    top_n_tie_policy: dict[str, Any] | None = None,
) -> tuple[bool, bool, str]:
    column_match = (
        len(actual_columns) == len(expected_columns)
        and set(actual_columns) == set(expected_columns)
    )
    actual = row_values(actual_rows)
    expected = row_values(expected_rows)
    if len(actual) != len(expected):
        return False, column_match, "返回行数不一致"
    if len(actual_columns) < len(expected_columns):
        return False, column_match, "缺少必要返回列"

    expected_width = len(expected_columns)
    if math.perm(len(actual_columns), expected_width) > 10000:
        return False, column_match, LOOSE_MAPPING_LIMIT_REASON
    for selected in permutations(range(len(actual_columns)), expected_width):
        projected = [[row[index] for index in selected] for row in actual]
        rows_match = (
            top_n_boundary_equivalent(
                projected, expected, expected_columns, order_by_column,
                top_n_tie_policy,
            ) if order_sensitive and order_by_column and top_n_tie_policy else
            ordered_rows_equivalent_with_ties(
                projected, expected, expected_columns, order_by_column,
            ) if order_sensitive and order_by_column else
            ordered_rows_equivalent(projected, expected, expected_columns)
            if order_sensitive else
            rows_equivalent(projected, expected, expected_columns)
        )
        if rows_match:
            detail = "结果一致"
            if len(actual_columns) != len(expected_columns) or not column_match:
                detail += "（忽略列顺序和辅助列）"
            return True, column_match, detail
    return False, column_match, "返回数据与标准结果不一致"


def compare_results_strict(
    actual_columns: list[str],
    actual_rows: list[dict[str, Any]],
    expected_columns: list[str],
    expected_rows: list[dict[str, Any]],
    order_sensitive: bool,
    *,
    order_by_column: str | None = None,
    column_aliases: dict[str, list[str]] | None = None,
    allowed_auxiliary_columns: list[str] | None = None,
    top_n_tie_policy: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Compare business columns by explicit names or annotated aliases."""
    aliases = column_aliases or {}
    allowed_extra = set(allowed_auxiliary_columns or [])
    if len(set(actual_columns)) != len(actual_columns):
        return False, "返回列名重复"
    if len(set(expected_columns)) != len(expected_columns):
        return False, "标准列名重复"
    mapping: list[str] = []
    for expected in expected_columns:
        candidates = [name for name in actual_columns if name == expected or
                      name in aliases.get(expected, [])]
        if len(candidates) != 1:
            return False, f"列 {expected} 缺失或映射不唯一"
        mapping.append(candidates[0])
    if len(set(mapping)) != len(mapping):
        return False, "多个标准列映射到同一返回列"
    extras = set(actual_columns) - set(mapping)
    if extras - allowed_extra:
        return False, "存在未声明的辅助列"
    if len(actual_rows) != len(expected_rows):
        return False, "返回行数不一致"
    try:
        actual = [[row[name] for name in mapping] for row in actual_rows]
        expected = [[row[name] for name in expected_columns] for row in expected_rows]
    except KeyError:
        return False, "返回行或标准行缺少声明的列"
    matches = (
        top_n_boundary_equivalent(
            actual, expected, expected_columns, order_by_column,
            top_n_tie_policy,
        ) if order_sensitive and order_by_column and top_n_tie_policy else
        ordered_rows_equivalent_with_ties(
            actual, expected, expected_columns, order_by_column,
        ) if order_sensitive and order_by_column else
        ordered_rows_equivalent(actual, expected, expected_columns)
        if order_sensitive else
        rows_equivalent(actual, expected, expected_columns)
    )
    return (True, "严格结果一致") if matches else (False, "严格结果值不一致")


def field_metrics(retrieved: list[str], expected: list[str]) -> tuple[float, float, int]:
    retrieved_set = set(retrieved)
    expected_set = set(expected)
    true_positive = len(retrieved_set & expected_set)
    recall = true_positive / len(expected_set) if expected_set else 1.0
    precision = true_positive / len(retrieved_set) if retrieved_set else 0.0
    return recall, precision, true_positive


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * ratio) - 1))
    return ordered[index]


def summarize(results: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    count = len(results)
    successful = [row for row in results if row.get("sql_execution_success")]
    scored = [row for row in results if row.get("result_correct") is not None]
    correct = [row for row in scored if row["result_correct"]]
    strict_scored = [row for row in results if row.get("strict_result_correct") is not None]
    strict_correct = [row for row in strict_scored if row["strict_result_correct"]]
    execution_times = [
        float(row["execution_ms"]) for row in successful
        if isinstance(row.get("execution_ms"), (int, float))
        and not isinstance(row["execution_ms"], bool)
    ]
    recalls = [float(row["schema_recall"]) for row in results if row.get("schema_recall") is not None]
    precisions = [float(row["schema_precision"]) for row in results if row.get("schema_precision") is not None]
    errors = [str(row.get("benchmark_error") or "") for row in results]
    timeout_count = sum(
        any(token in error.lower() for token in ("timed out", "timeout", "超时"))
        for error in errors
    )
    return {
        "mode": mode,
        "case_count": count,
        "schema_recall": round(statistics.fmean(recalls), 6) if recalls else None,
        "schema_precision": round(statistics.fmean(precisions), 6) if precisions else None,
        "sql_execution_success_rate": round(len(successful) / count, 6) if count else 0.0,
        "average_execution_ms": round(statistics.fmean(execution_times), 3) if execution_times else None,
        "p95_execution_ms": round(percentile(execution_times, 0.95), 3) if execution_times else None,
        "result_accuracy": round(len(correct) / len(scored), 6) if scored else None,
        "result_scored_count": len(scored),
        "strict_result_accuracy": (
            round(len(strict_correct) / len(strict_scored), 6) if strict_scored else None
        ),
        "strict_scored_count": len(strict_scored),
        "unscored_count": count - len(scored),
        "column_name_match_rate": round(
            sum(bool(row.get("column_match")) for row in results) / count, 6
        ) if count else 0.0,
        "clarification_count": sum(row.get("agent_action") == "clarify" for row in results),
        "error_count": sum(bool(row.get("benchmark_error")) for row in results),
        "timeout_count": timeout_count,
        "connection_error_count": sum("WinError 10054" in error for error in errors),
        "model_request_attempt_count": sum(
            int(row.get("model_request_attempt_count") or 0) for row in results
        ),
        "model_retry_count": sum(int(row.get("model_retry_count") or 0) for row in results),
        "model_timeout_event_count": sum(
            int(row.get("model_timeout_event_count") or 0) for row in results
        ),
        "model_connection_error_event_count": sum(
            int(row.get("model_connection_error_event_count") or 0) for row in results
        ),
        "result_accuracy_given_executed_sql": round(
            len(correct) / len(successful), 6
        ) if successful else 0.0,
    }


def _case_result(
    case: dict[str, Any],
    *,
    route_metrics: dict[str, Any] | None = None,
    schema_metrics: dict[str, Any] | None = None,
    sql_metrics: dict[str, Any] | None = None,
    result_metrics: dict[str, Any] | None = None,
    agent_metrics: dict[str, Any] | None = None,
    trace: EvaluationTrace | None = None,
    errors: dict[str, Any] | None = None,
    raw_output: dict[str, Any] | None = None,
) -> EvaluationResult:
    return EvaluationResult(
        case_id=case["case_id"],
        question=case["query"],
        scenario=case["scenario"],
        category=case["category"],
        query_type=case["query_type"],
        difficulty=case["difficulty"],
        classic=bool(case["classic"]),
        route_metrics=route_metrics or {},
        schema_metrics=schema_metrics or {},
        sql_metrics=sql_metrics or {},
        result_metrics=result_metrics or {},
        agent_metrics=agent_metrics or {},
        trace=trace or EvaluationTrace(
            request={
                "case_id": case["case_id"],
                "question": case["query"],
                "query_type": case["query_type"],
            },
            routing={"route": None},
        ),
        errors=errors or {},
        raw_output=raw_output or {},
    )


def _is_permission_denial(message: Any) -> bool:
    text = str(message or "").lower()
    return any(token in text for token in (
        "无权访问", "权限", "permission denied", "unauthorized", "not authorized",
    ))


def _permission_snapshot(
    scope: Any,
    schema_index: Any = None,
    *,
    sql_permission_check: bool = False,
    sql_error: Any = None,
) -> dict[str, Any]:
    public = scope.public() if scope is not None and hasattr(scope, "public") else {}
    raw_documents = getattr(schema_index, "documents", None) if schema_index is not None else None
    documents = (
        list(raw_documents)
        if isinstance(raw_documents, (list, tuple))
        else []
    )
    before = len(documents) if schema_index is not None else 0
    after = (
        sum(
            bool(scope.allows_table(document.database_id, document.table_id))
            for document in documents
        )
        if schema_index is not None and scope is not None and hasattr(scope, "allows_table")
        else 0
    )
    blocked = sql_permission_check and _is_permission_denial(sql_error)
    return {
        "checked": scope is not None,
        "user_id": public.get("user_id"),
        "roles": list(public.get("roles") or []),
        "allowed_databases": list(public.get("allowed_databases") or []),
        "allowed_tables_count": len(public.get("allowed_tables") or []),
        "schema_filter_applied": schema_index is not None and scope is not None,
        "schema_before_filter_count": before,
        "schema_after_filter_count": after,
        "sql_permission_check": sql_permission_check,
        "sql_blocked": blocked,
        "denied_reason": str(sql_error) if blocked else None,
    }


def _clarification_snapshot(
    clarification: dict[str, Any] | None = None,
    *,
    triggered: bool = False,
    final_status: str | None = None,
    user_responded: bool = False,
    selected_option: Any = None,
    continued_execution: bool = False,
) -> dict[str, Any]:
    payload = clarification if isinstance(clarification, dict) else {}
    return {
        "triggered": triggered,
        "question": payload.get("question") if triggered else None,
        "option_count": len(payload.get("options") or []) if triggered else 0,
        "reason": payload.get("reason") if triggered else None,
        "user_responded": user_responded,
        "selected_option": selected_option,
        "continued_execution": continued_execution,
        "final_status": final_status,
    }


def run_gold_case(case: dict[str, Any], engine: ReadOnlyExecutor, scope: Any, *,
                  use_cached_gold: bool = True,
                  gold_cache_dir: Path = DEFAULT_CACHE_DIR,
                  data_version: str = "") -> EvaluationResult:
    selected_sql = ""
    try:
        source = getattr(engine, "source_identity", None)
        selected_sql = select_gold_sql(case, source if isinstance(source, SourceIdentity) else None).sql
        gold = resolve_gold_result(case, engine, scope, cache_dir=gold_cache_dir,
                                   use_cached_gold=use_cached_gold,
                                   data_version=data_version)
    except Exception as exc:
        return _case_result(
            case, schema_metrics={"gold_fields": case.get("gold_fields", [])},
            sql_metrics={"generated_sql": selected_sql, "execution_success": False},
            result_metrics={"correct": None, "strict_correct": None,
                            "column_match": False, "reason": str(exc),
                            "gold_result_generated": False},
            agent_metrics={"action": "gold_sql"},
            trace=EvaluationTrace(
                request={"case_id": case["case_id"], "question": case["query"],
                         "query_type": case["query_type"]},
                routing={"route": None},
                permission=_permission_snapshot(
                    scope, sql_permission_check=True, sql_error=str(exc),
                ),
                clarification=_clarification_snapshot(),
                agent_decision={"action": "gold_sql"},
                errors=[{"stage": "gold_result", "message": str(exc)}],
            ),
            errors={"stage": "gold_result", "message": str(exc)},
        )
    metrics = gold_metrics(gold, len(gold["rows"]))
    metrics["gold_result_evidence"] = gold_result_evidence(gold)
    if "expected_columns" in case and "expected_rows" in case:
        correct, columns_match, reason = compare_results(
            gold["columns"], gold["rows"], case["expected_columns"], case["expected_rows"],
            bool(case.get("order_sensitive", True)),
            order_by_column=case.get("order_by_column"),
            top_n_tie_policy=case.get("top_n_tie_policy"),
        )
        if reason == LOOSE_MAPPING_LIMIT_REASON:
            correct = None
        strict_correct, strict_reason = compare_results_strict(
            gold["columns"], gold["rows"], case["expected_columns"], case["expected_rows"],
            bool(case.get("order_sensitive", True)),
            order_by_column=case.get("order_by_column"),
            column_aliases=case.get("column_aliases"),
            allowed_auxiliary_columns=case.get("allowed_auxiliary_columns"),
            top_n_tie_policy=case.get("top_n_tie_policy"),
        )
        metrics["comparison_target"] = "expected_rows"
    else:
        # Generation succeeded; this is not an independent correctness verdict.
        correct, columns_match, reason = None, False, "Gold result generated; no static validation target"
        strict_correct, strict_reason = None, "没有独立的标准结果"
        metrics["comparison_target"] = "none"
    return _case_result(
        case,
        schema_metrics={"recall": None, "precision": None, "retrieved_fields": [],
                        "gold_fields": case.get("gold_fields", [])},
        sql_metrics={"generated_sql": gold["gold_sql"],
                     "execution_success": gold["source"] != "expected_rows",
                     "execution_ms": gold["execution_ms"]},
        result_metrics={"correct": correct, "column_match": columns_match,
                        "reason": reason, "strict_correct": strict_correct,
                        "strict_reason": strict_reason, **metrics},
        agent_metrics={"action": "gold_sql"},
        trace=EvaluationTrace(
            request={"case_id": case["case_id"], "question": case["query"],
                     "query_type": case["query_type"]},
            routing={"route": None},
            permission=_permission_snapshot(
                scope, sql_permission_check=gold["source"] == "execution",
            ),
            clarification=_clarification_snapshot(),
            agent_decision={"action": "gold_sql", "clarification_required": False},
            sql_execution={
                **({"source_identity": source.public(), "backend": source.backend, "dialect": source.dialect}
                   if isinstance(source, SourceIdentity) else {}),
                "generated_sql": gold["gold_sql"],
                "success": gold["source"] != "expected_rows",
                "execution_ms": gold["execution_ms"],
                "result_rows": len(gold["rows"]),
                "gold_result_source": gold["source"],
            },
            result_comparison={
                "comparison_target": metrics["comparison_target"],
                "correct": correct,
                "reason": reason,
            },
        ),
    )


def run_live_case(
    case: dict[str, Any],
    schema_index: SchemaIndex,
    graph_builder: SchemaGraphBuilder,
    workflow: QueryWorkflow,
    controller: AccessController,
    *,
    use_cached_gold: bool = True,
    gold_cache_dir: Path = DEFAULT_CACHE_DIR,
    gold_engine: Any = None,
    data_version: str = "",
) -> EvaluationResult:
    runtime = getattr(workflow, "runtime", None)
    if isinstance(runtime, DataSourceRuntime):
        runtime.assert_shared(schema_index, graph_builder, workflow)
        if gold_engine is not None:
            runtime.assert_executor(gold_engine)
    scope = controller.resolve(f"demo_{case['scenario']}")
    permission = _permission_snapshot(scope, schema_index)
    try:
        retrieval_started = time.perf_counter()
        retrieval = schema_index.retrieve(
            case["query"],
            retrieval_terms=case["retrieval_terms"],
            access_scope=scope,
        )
        supplement_enabled = getattr(
            getattr(workflow, "config", None), "time_field_supplement_enabled", False
        ) is True
        time_field_policy = getattr(workflow, "time_field_policy", None)
        if supplement_enabled and time_field_policy is not None:
            proposal = time_field_policy.propose(
                case["query"],
                [str(hit["doc_id"]) for hit in retrieval["hits"]],
                scope,
            )
            retrieval = schema_index.include_time_fields(
                retrieval,
                proposal["proposals"],
                scope,
                max_extra_fields=workflow.config.time_field_supplement_max_extra_fields,
                max_total_fields=workflow.config.time_field_supplement_max_total_fields,
            )
            retrieval["time_field_supplement"].update({
                "time_cue": proposal["time_cue"],
                "matched_metrics": proposal["matched_metrics"],
            })
        retrieval_ms = round((time.perf_counter() - retrieval_started) * 1000, 3)
        retrieved_fields = [str(hit["doc_id"]) for hit in retrieval["hits"]]
        supplement_trace = (
            {"time_field_supplement": retrieval["time_field_supplement"]}
            if "time_field_supplement" in retrieval else {}
        )
        recall, precision, true_positive = field_metrics(retrieved_fields, case["gold_fields"])
        graph = graph_builder.build(retrieval["hits"], scope)
        schema_context = graph_builder.context_text(graph)
        if not graph.get("tables"):
            return _case_result(
                case,
                schema_metrics={
                    "recall": recall,
                    "precision": precision,
                    "true_positive": true_positive,
                    "retrieval_ms": retrieval_ms,
                    "retrieved_fields": retrieved_fields,
                    "gold_fields": case["gold_fields"],
                },
                sql_metrics={
                    "generated_sql": "",
                    "execution_success": False,
                    "execution_ms": 0.0,
                },
                result_metrics={
                    "correct": False,
                    "column_match": False,
                    "reason": "Schema图为空",
                },
                agent_metrics={"action": "not_called"},
                trace=EvaluationTrace(
                    request={"case_id": case["case_id"], "question": case["query"],
                             "query_type": case["query_type"]},
                    routing={"route": None},
                    permission=permission,
                    clarification=_clarification_snapshot(final_status="schema_failed"),
                    schema_retrieval={
                        "retrieved_fields": retrieved_fields, "recall": recall,
                        "precision": precision, "latency_ms": retrieval_ms,
                        **supplement_trace,
                    },
                    agent_decision={"action": "not_called", "clarification_required": False},
                    errors=[{"stage": "schema_retrieval", "message": "Schema图为空"}],
                ),
                errors={"message": "Schema图为空"},
            )
        decision = workflow.single_database_agent.prepare(
            case["query"],
            "short_video_ops",
            graph,
            schema_context,
            retrieval,
            {},
            scope.public(),
        )
        if decision["action"] == "clarify":
            clarification = decision.get("clarification") or {}
            return _case_result(
                case,
                schema_metrics={
                    "recall": recall,
                    "precision": precision,
                    "true_positive": true_positive,
                    "retrieval_ms": retrieval_ms,
                    "retrieved_fields": retrieved_fields,
                    "gold_fields": case["gold_fields"],
                },
                sql_metrics={
                    "generated_sql": "",
                    "execution_success": False,
                    "execution_ms": 0.0,
                },
                result_metrics={
                    "correct": False,
                    "column_match": False,
                    "reason": "智能体发起澄清",
                },
                agent_metrics={"action": "clarify"},
                trace=EvaluationTrace(
                    request={"case_id": case["case_id"], "question": case["query"],
                             "query_type": case["query_type"]},
                    routing={"route": None},
                    permission=permission,
                    clarification=_clarification_snapshot(
                        clarification, triggered=True, final_status="waiting_clarification",
                    ),
                    schema_retrieval={
                        "retrieved_fields": retrieved_fields, "recall": recall,
                        "precision": precision, "latency_ms": retrieval_ms,
                        **supplement_trace,
                    },
                    agent_decision={"action": "clarify", "clarification_required": True},
                ),
            )
        execution = decision["execution"]
        tool_trace = list(decision.get("tool_trace") or [])
        final_trace = tool_trace[-1] if tool_trace else {}
        success = bool(execution.get("success"))
        target_metrics = {}
        gold_error = ""
        score_error_stage = "gold_result"
        gold = None
        scoring_rows = list(execution.get("rows") or [])
        if success:
            try:
                evaluation_engine = gold_engine if gold_engine is not None else workflow.database_engine
                gold = resolve_gold_result(
                    case, evaluation_engine, scope,
                    cache_dir=gold_cache_dir, use_cached_gold=use_cached_gold,
                    data_version=data_version,
                )
                if execution.get("truncated"):
                    complete = evaluation_engine.execute(
                        str(execution.get("database") or "short_video_ops"),
                        str(execution.get("sql") or ""), scope, row_limit=10000,
                    )
                    if not complete.success or getattr(complete, "truncated", False):
                        score_error_stage = "result_scoring"
                        raise RuntimeError(
                            complete.error or "Generated result exceeds the scoring row limit"
                        )
                    scoring_rows = complete.rows
                target_metrics = gold_metrics(gold, len(scoring_rows))
                target_metrics["scoring_reexecuted"] = bool(execution.get("truncated"))
            except Exception as exc:
                gold_error = str(exc)
        if gold_error:
            result_correct, column_match, reason = None, False, gold_error
            strict_correct, strict_reason = None, gold_error
        else:
            result_correct, column_match, reason = compare_results(
                list(execution.get("columns") or []),
                scoring_rows,
                gold["columns"],
                gold["rows"],
                bool(case.get("order_sensitive", True)),
                order_by_column=case.get("order_by_column"),
                top_n_tie_policy=case.get("top_n_tie_policy"),
            ) if success else (False, False, str(execution.get("error") or "SQL执行失败"))
            if reason == LOOSE_MAPPING_LIMIT_REASON:
                result_correct = None
            strict_correct, strict_reason = compare_results_strict(
                list(execution.get("columns") or []),
                scoring_rows,
                gold["columns"],
                gold["rows"],
                bool(case.get("order_sensitive", True)),
                order_by_column=case.get("order_by_column"),
                column_aliases=case.get("column_aliases"),
                allowed_auxiliary_columns=case.get("allowed_auxiliary_columns"),
                top_n_tie_policy=case.get("top_n_tie_policy"),
            ) if success else (False, str(execution.get("error") or "SQL执行失败"))
        permission = _permission_snapshot(
            scope,
            schema_index,
            sql_permission_check=True,
            sql_error=(gold_error or execution.get("error")),
        )
        tool_calls = []
        for item in tool_trace:
            tool_result = item.get("result") or {}
            tool_calls.append({
                "tool_name": item.get("tool"),
                "success": bool(tool_result.get("success")) if "success" in tool_result
                else not bool(tool_result.get("error")),
                "latency_ms": float(tool_result.get("execution_ms") or 0.0),
                "retry_count": 0,
                "call_index": item.get("call_index"),
            })
        return _case_result(
            case,
            schema_metrics={
                "recall": recall,
                "precision": precision,
                "true_positive": true_positive,
                "retrieval_ms": retrieval_ms,
                "retrieved_fields": retrieved_fields,
                "gold_fields": case["gold_fields"],
            },
            sql_metrics={
                "generated_sql": str(execution.get("sql") or ""),
                "execution_success": success,
                "execution_ms": float(execution.get("execution_ms") or 0.0),
            },
            result_metrics={
                "correct": result_correct,
                "column_match": column_match,
                "reason": reason,
                "strict_correct": strict_correct,
                "strict_reason": strict_reason,
                **target_metrics,
            },
            agent_metrics={
                "action": "executed",
                "query_contract": final_trace.get("query_contract", {}),
                "reason": str(final_trace.get("reason") or ""),
            },
            trace=EvaluationTrace(
                request={"case_id": case["case_id"], "question": case["query"],
                         "query_type": case["query_type"]},
                routing={"route": None},
                permission=permission,
                clarification=_clarification_snapshot(final_status="completed"),
                schema_retrieval={
                    "retrieved_fields": retrieved_fields, "recall": recall,
                    "precision": precision, "latency_ms": retrieval_ms,
                    **supplement_trace,
                },
                agent_decision={
                    "action": "executed", "clarification_required": False,
                    "reason": str(final_trace.get("reason") or ""),
                },
                tool_calls=tool_calls,
                sql_execution={
                    **({"source_identity": runtime.identity.public(), "backend": runtime.identity.backend,
                        "dialect": runtime.identity.dialect} if isinstance(runtime, DataSourceRuntime) else {}),
                    "generated_sql": str(execution.get("sql") or ""),
                    "success": success,
                    "execution_ms": float(execution.get("execution_ms") or 0.0),
                },
                result_comparison={
                    "comparison_target": target_metrics.get("comparison_target"),
                    "gold_result_source": target_metrics.get("gold_result_source"),
                    "correct": result_correct,
                    "strict_correct": strict_correct,
                    "reason": reason,
                },
                errors=([{"stage": score_error_stage, "message": gold_error}]
                        if gold_error else []),
            ),
            errors={"stage": score_error_stage, "message": gold_error} if gold_error else {},
        )
    except Exception as exc:  # 单条用例失败不终止整个评测。
        error_stage = exc.stage if isinstance(exc, PipelineStageError) else "benchmark"
        diagnostics = exc.diagnostics if isinstance(exc, PipelineStageError) else {}
        error_details = {"stage": error_stage, "message": str(exc)}
        if diagnostics:
            error_details["diagnostics"] = diagnostics
        return _case_result(
            case,
            schema_metrics={
                "recall": None,
                "precision": None,
                "retrieved_fields": [],
                "gold_fields": case["gold_fields"],
            },
            sql_metrics={
                "generated_sql": "",
                "execution_success": False,
                "execution_ms": 0.0,
            },
            result_metrics={
                "correct": False,
                "column_match": False,
                "reason": "评测链路异常",
            },
            agent_metrics={"action": "error"},
            trace=EvaluationTrace(
                request={"case_id": case["case_id"], "question": case["query"],
                         "query_type": case["query_type"]},
                routing={"route": None},
                permission=permission,
                clarification=_clarification_snapshot(final_status="error"),
                agent_decision={"action": "error", "clarification_required": False},
                errors=[error_details],
            ),
            errors=error_details,
        )


def save_report(
    results: list[dict[str, Any]], summary: dict[str, Any], output: Path,
    run_manifest: dict[str, Any] | None = None,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    json_temp = output.with_suffix(output.suffix + ".tmp")
    json_temp.write_text(
        json.dumps({
            "summary": summary, "cases": results,
            **({"run_manifest": run_manifest} if run_manifest else {}),
            **({"run_status": (
                "complete" if len(results) == len(run_manifest["dataset"]["case_ids"])
                else "partial"
            )} if run_manifest else {}),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    json_temp.replace(output)

    csv_path = output.with_suffix(".csv")
    csv_temp = csv_path.with_suffix(csv_path.suffix + ".tmp")
    columns = [
        "run_id", "trace_id", "case_id", "scenario", "category", "query_type",
        "difficulty", "classic", "query",
        "schema_recall", "schema_precision", "retrieval_ms", "sql_execution_success",
        "execution_ms", "result_correct", "strict_result_correct", "column_match",
        "agent_action", "comparison_reason", "strict_comparison_reason",
        "generated_sql", "query_contract", "agent_reason", "error_stage",
        "model_request_attempt_count", "model_retry_count", "model_timeout_event_count",
        "model_connection_error_event_count",
        "benchmark_error", "gold_result_source", "comparison_target",
    ]
    with csv_temp.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    csv_temp.replace(csv_path)

    sql_rate = float(summary.get("sql_execution_success_rate") or 0.0)
    result_rate = float(summary.get("result_accuracy") or 0.0)
    strict_rate = summary.get("strict_result_accuracy")
    latency = summary.get("average_execution_ms")
    latency_text = f"{float(latency):.2f} ms" if latency is not None else "未测量"
    case_count = int(summary.get("case_count") or 0)
    scored_count = int(summary.get("result_scored_count") or 0)
    strict_scored_count = int(summary.get("strict_scored_count") or 0)
    correct_count = sum(bool(row.get("result_correct")) for row in results)
    required_correct = math.ceil(scored_count * 0.8)
    shortfall = max(0, required_correct - correct_count)

    scenario_labels = {
        "growth_ops": "用户增长运营",
        "channel_ops": "渠道投放运营",
        "content_ops": "内容运营",
    }
    scenario_lines = ["| 场景 | 用例数 | SQL执行成功率 | 宽松正确率（已评分数） |", "| --- | ---: | ---: | ---: |"]
    for scenario in ("growth_ops", "channel_ops", "content_ops"):
        rows = [row for row in results if row.get("scenario") == scenario]
        if not rows:
            continue
        sql_success = sum(bool(row.get("sql_execution_success")) for row in rows)
        scored_rows = [row for row in rows if row.get("result_correct") is not None]
        result_success = sum(bool(row["result_correct"]) for row in scored_rows)
        result_text = f"{result_success / len(scored_rows):.2%}（{len(scored_rows)}）" if scored_rows else "未评分（0）"
        scenario_lines.append(
            f"| {scenario_labels[scenario]} | {len(rows)} | "
            f"{sql_success / len(rows):.2%} | {result_text} |"
        )

    difficulty_lines = ["| 难度 | 用例数 | SQL执行成功率 | 宽松正确率（已评分数） |", "| --- | ---: | ---: | ---: |"]
    for difficulty in ("简单", "中等", "复杂"):
        rows = [row for row in results if row.get("difficulty") == difficulty]
        if not rows:
            continue
        sql_success = sum(bool(row.get("sql_execution_success")) for row in rows)
        scored_rows = [row for row in rows if row.get("result_correct") is not None]
        result_success = sum(bool(row["result_correct"]) for row in scored_rows)
        result_text = f"{result_success / len(scored_rows):.2%}（{len(scored_rows)}）" if scored_rows else "未评分（0）"
        difficulty_lines.append(
            f"| {difficulty} | {len(rows)} | {sql_success / len(rows):.2%} | "
            f"{result_text} |"
        )

    failure_groups = Counter(
        (
            scenario_labels.get(str(row.get("scenario")), str(row.get("scenario"))),
            str(row.get("category") or "未分类"),
            str(row.get("query_type") or "未分类"),
        )
        for row in results
        if row.get("result_correct") is False
    )
    failure_lines = [
        f"- {scenario} / {category} / {query_type}：{count}条"
        for (scenario, category, query_type), count in failure_groups.most_common(8)
    ]

    conclusion = (
        "没有可评分的结果，需先解决 Gold 或评分错误。"
        if not scored_count else
        "SQL执行成功率和查询结果正确率均达到目标。"
        if sql_rate >= 0.9 and result_rate >= 0.8
        else (
            f"SQL执行成功率达到目标；查询结果正确率未达到80%，还差{shortfall}条正确用例。"
            if sql_rate >= 0.9
            else "当前至少有一项核心指标未达到目标，需要继续分析失败用例。"
        )
    )

    markdown = "\n".join([
        "# 问数链路评测报告",
        "",
        f"- 已完成用例：{case_count}",
        *(
            [
                f"- 字段级Schema召回率：{float(summary.get('schema_recall') or 0.0):.2%}",
                f"- 字段级Schema准确率：{float(summary.get('schema_precision') or 0.0):.2%}",
            ] if summary.get("mode") == "live" else []
        ),
        f"- SQL执行成功率：{sql_rate:.2%}（目标≥90%，{'达标' if sql_rate >= 0.9 else '未达标'}）",
        f"- 宽松结果正确率：{result_rate:.2%}（已评分 {scored_count}/{case_count}）"
        if scored_count else f"- 宽松结果正确率：未评分（0/{case_count}）",
        f"- 严格结果正确率：{float(strict_rate):.2%}"
        f"（已评分 {strict_scored_count}/{case_count}）"
        if strict_rate is not None else f"- 严格结果正确率：未评分（0/{case_count}）",
        f"- SQL平均执行时间：{latency_text}",
        f"- 最终超时数：{summary.get('timeout_count', 0)}",
        f"- 模型原始超时事件：{summary.get('model_timeout_event_count', 0)}",
        f"- 模型重试次数：{summary.get('model_retry_count', 0)}",
        "",
        "## 分场景结果",
        "",
        *scenario_lines,
        "",
        "## 分难度结果",
        "",
        *difficulty_lines,
        "",
        "## 主要失败类型",
        "",
        *failure_lines,
        "",
        "## 结论",
        "",
        conclusion,
        "",
    ])
    markdown_path = output.with_suffix(".md")
    markdown_temp = markdown_path.with_suffix(markdown_path.suffix + ".tmp")
    markdown_temp.write_text(markdown, encoding="utf-8")
    markdown_temp.replace(markdown_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="运行短视频运营问数评测")
    parser.add_argument("--mode", choices=("gold", "live"), default="gold")
    parser.add_argument("--scope", choices=("all", "classic"), default="all")
    parser.add_argument("--scenario", action="append", choices=("growth_ops", "channel_ops", "content_ops"))
    parser.add_argument("--case-id", action="append", help="只运行指定用例，可重复传入")
    parser.add_argument("--case-list", type=Path, help="JSON manifest containing case_ids")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--save-snapshot", action="store_true", help="保存本次完整评测结果快照")
    parser.add_argument("--use-cached-gold", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--gold-cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    args = parser.parse_args()

    cases = load_cases(CASES_PATH, set(args.scenario or []), args.scope == "classic")
    if args.case_list:
        cases = select_cases(cases, load_case_ids(args.case_list))
    if args.case_id:
        selected_ids = set(args.case_id)
        cases = [case for case in cases if case["case_id"] in selected_ids]
    if args.limit > 0:
        cases = cases[: args.limit]
    with create_datasource_runtime(settings) as runtime:
        manifest = build_run_manifest(
            cases,
            base_dir=BASE_DIR,
            mode=args.mode,
            scope=args.scope,
            case_source=CASES_PATH,
            case_list=args.case_list,
            runtime=runtime,
            config={
                **settings.public_status(),
                "llm_temperature": settings.temperature,
                "llm_timeout": settings.timeout,
                "llm_max_retries": settings.max_retries,
                "workers": max(1, min(args.workers, 8)),
                "user_roles": sorted({f"demo_{case['scenario']}" for case in cases}),
                "evaluation_date": date.today().isoformat(),
            },
        )
        controller = AccessController()
        suffix = f"{args.mode}_{args.scope}"
        output = args.output or RESULT_DIR / f"benchmark_{suffix}.json"
        previous: dict[str, dict[str, Any]] = {}
        if args.resume and output.exists():
            payload = json.loads(output.read_text(encoding="utf-8"))
            previous_manifest = require_resumable(payload, manifest)
            manifest = previous_manifest
            previous = {str(row["case_id"]): row for row in payload.get("cases", [])}
        results: list[dict[str, Any]] = list(previous.values())
        pending_cases = [case for case in cases if case["case_id"] not in previous]

        if args.mode == "gold":
            engine = runtime.executor
            for index, case in enumerate(pending_cases, 1):
                result = run_gold_case(
                    case, engine, controller.resolve(f"demo_{case['scenario']}"),
                    use_cached_gold=args.use_cached_gold, gold_cache_dir=args.gold_cache_dir,
                    data_version=manifest["versions"]["data"],
                ).to_dict()
                result["run_id"] = manifest["run_id"]
                result["trace_id"] = f"{manifest['run_id']}:{case['case_id']}"
                results.append(result)
                print(f"[{index}/{len(pending_cases)}] {case['case_id']} success={result['sql_execution_success']} correct={result['result_correct']}")
        else:
            if not settings.api_key:
                raise RuntimeError("live评测需要在backend/.env配置LLM_API_KEY")
            thread_state = threading.local()

            def evaluate(case: dict[str, Any]) -> dict[str, Any]:
                if not hasattr(thread_state, "schema_resources"):
                    schema_index = SchemaIndex(ModelClient(settings), settings, runtime=runtime)
                    schema_index.ensure_built()
                    thread_state.schema_resources = (
                        schema_index,
                        SchemaGraphBuilder(runtime=runtime),
                    )
                schema_index, graph_builder = thread_state.schema_resources

                # 每条用例隔离接口熔断状态，避免一次超时污染同线程的后续用例。
                model_client = ModelClient(settings)
                schema_index.model_client = model_client
                from app.workflows.query_graph import QueryWorkflow
                workflow = QueryWorkflow(model_client, schema_index, settings, runtime=runtime)
                evaluation_result = run_live_case(
                    case,
                    schema_index,
                    graph_builder,
                    workflow,
                    controller,
                    gold_engine=runtime.executor,
                    use_cached_gold=args.use_cached_gold, gold_cache_dir=args.gold_cache_dir,
                    data_version=manifest["versions"]["data"],
                )
                evaluation_result.raw_output.update(model_client.metrics())
                return evaluation_result.to_dict()

            workers = max(1, min(args.workers, 8))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(evaluate, case): case for case in pending_cases}
                for index, future in enumerate(as_completed(futures), 1):
                    case = futures[future]
                    try:
                        result = future.result()
                    except Exception as exc:
                        # 单条用例异常只记录失败，避免中断完整评测。
                        result = _case_result(
                            case,
                            schema_metrics={
                                "recall": None,
                                "precision": None,
                                "retrieved_fields": [],
                                "gold_fields": case["gold_fields"],
                            },
                            sql_metrics={
                                "generated_sql": "",
                                "execution_success": False,
                                "execution_ms": 0.0,
                            },
                            result_metrics={
                                "correct": False,
                                "column_match": False,
                                "reason": "评测线程异常",
                            },
                            agent_metrics={"action": "error"},
                            errors={"stage": "benchmark_worker", "message": str(exc)},
                        ).to_dict()
                    result["run_id"] = manifest["run_id"]
                    result["trace_id"] = f"{manifest['run_id']}:{case['case_id']}"
                    results.append(result)
                    print(
                        f"[{index}/{len(pending_cases)}] {case['case_id']} "
                        f"recall={result.get('schema_recall')} precision={result.get('schema_precision')} "
                        f"sql={result['sql_execution_success']} result={result['result_correct']}"
                    )
                    # 每完成一条就保存断点；使用原子替换避免中断时留下半个JSON。
                    order = {item["case_id"]: position for position, item in enumerate(cases)}
                    results.sort(key=lambda row: order.get(row["case_id"], len(order)))
                    save_report(results, summarize(results, args.mode), output, manifest)

        order = {case["case_id"]: position for position, case in enumerate(cases)}
        results.sort(key=lambda row: order.get(row["case_id"], len(order)))
        summary = summarize(results, args.mode)
        save_report(results, summary, output, manifest)
        report_path = output.with_name(f"{output.stem}_report.md")
        if args.mode == "gold":
            report_path.write_text(output.with_suffix(".md").read_text(encoding="utf-8"),
                                   encoding="utf-8")
        else:
            BenchmarkReportBuilder.write_markdown(results, report_path)
        if args.save_snapshot:
            snapshot_path = BenchmarkSnapshotManager.save(
                output,
                mode=args.mode,
                scope=args.scope,
                dataset={
                    "path": CASES_PATH.relative_to(BASE_DIR).as_posix(),
                    "scope": args.scope,
                    "case_ids": [case["case_id"] for case in results],
                },
                metadata={
                    "llm_model": settings.llm_model,
                    "embedding_model": settings.embedding_model,
                    "rerank_model": settings.rerank_model,
                },
                run_manifest=manifest,
            )
            print(f"snapshot: {snapshot_path}")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"report: {output}")
        print(f"summary report: {report_path}")


if __name__ == "__main__":
    main()
