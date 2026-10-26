"""Classify recorded benchmark failures without changing their raw fields."""

from __future__ import annotations

from enum import Enum
from typing import Any

from evaluation.models import EvaluationResult


class ErrorCategory(str, Enum):
    MODEL_ERROR = "MODEL_ERROR"
    SCHEMA_RETRIEVAL_ERROR = "SCHEMA_RETRIEVAL_ERROR"
    SQL_GENERATION_ERROR = "SQL_GENERATION_ERROR"
    SQL_EXECUTION_ERROR = "SQL_EXECUTION_ERROR"
    RESULT_COMPARISON_ERROR = "RESULT_COMPARISON_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    MCP_TOOL_ERROR = "MCP_TOOL_ERROR"
    CLARIFICATION_ERROR = "CLARIFICATION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _recorded_errors(row: dict[str, Any], trace: dict[str, Any]) -> list[tuple[str, str]]:
    records: list[tuple[str, str]] = []
    errors = _mapping(row.get("errors"))
    stage = str(row.get("error_stage") or errors.get("stage") or "").strip().lower()
    message = str(row.get("benchmark_error") or errors.get("message") or "").strip().lower()
    if stage or message:
        records.append((stage, message))
    trace_errors = trace.get("errors")
    if isinstance(trace_errors, list):
        for item in trace_errors:
            if isinstance(item, dict):
                records.append((
                    str(item.get("stage") or "").strip().lower(),
                    str(item.get("message") or "").strip().lower(),
                ))
    return records


class ErrorClassifier:
    """Assign one primary category per failed case, or ``None`` for success.

    Explicit stage and trace evidence wins over missing SQL and generic
    execution flags, which are also false when a query stops earlier.
    """

    @staticmethod
    def classify(result: EvaluationResult | dict[str, Any]) -> ErrorCategory | None:
        row = result.to_dict() if isinstance(result, EvaluationResult) else result
        trace = _mapping(row.get("trace"))
        permission = _mapping(trace.get("permission"))
        clarification = _mapping(trace.get("clarification"))
        agent = _mapping(row.get("agent_metrics"))
        sql = _mapping(row.get("sql_metrics"))
        comparison = _mapping(row.get("result_metrics"))
        records = _recorded_errors(row, trace)
        stages = [stage for stage, _ in records]
        messages = [message for _, message in records]
        text = " ".join(messages)
        tool_calls = trace.get("tool_calls")
        tool_failed = isinstance(tool_calls, list) and any(
            isinstance(call, dict) and call.get("success") is False for call in tool_calls
        )
        tool_failed = tool_failed or bool(agent.get("tool_failure_rate"))
        permission_denied = bool(permission.get("sql_blocked")) or bool(
            permission.get("denied_reason")
        ) or bool(agent.get("permission_denied_count")) or bool(
            agent.get("sql_permission_blocked_count")
        )
        sql_success = sql.get("execution_success", row.get("sql_execution_success"))
        result_correct = comparison.get("correct", row.get("result_correct"))
        generated_sql = sql.get("generated_sql", row.get("generated_sql"))
        status = str(clarification.get("final_status") or "").lower()
        clarification_failed = status in {"failed", "error", "abandoned", "cancelled", "canceled"} or bool(
            agent.get("clarification_abandon_count")
        )
        clarification_pending = bool(clarification.get("triggered")) and not bool(
            clarification.get("continued_execution")
        ) and result_correct is False
        comparison_target = comparison.get("comparison_target", row.get("comparison_target"))
        action = agent.get("action", row.get("agent_action"))
        gold_without_verdict = (
            action == "gold_sql" and comparison_target == "none" and sql_success is True
            and not records and not tool_failed and not permission_denied
        )
        if gold_without_verdict:
            return None
        failure = (
            bool(records) or tool_failed or permission_denied or clarification_failed
            or clarification_pending or sql_success is False or result_correct is False
        )
        if not failure:
            return None

        if "query_embedding" in stages or any(
            token in stage for stage in stages for token in ("model", "llm", "model_client")
        ) or any(token in text for token in (
            "model api", "model service", "model request", "modelclient", "llm",
            "模型接口", "模型调用",
        )):
            return ErrorCategory.MODEL_ERROR

        if permission_denied or any(
            token in f"{stage} {message}"
            for stage, message in records
            for token in ("permission", "access_control", "schema_access", "无权", "权限")
        ):
            return ErrorCategory.PERMISSION_ERROR

        if any(token in f"{stage} {message}" for stage, message in records
               for token in ("timeout", "timed out", "time out", "超时")) or (
            row.get("model_timeout_event_count") or 0
        ):
            return ErrorCategory.TIMEOUT_ERROR

        if any(token in stage for stage in stages for token in (
            "schema", "retrieval", "embedding", "rerank",
        )):
            return ErrorCategory.SCHEMA_RETRIEVAL_ERROR

        if clarification_failed or clarification_pending or any("clarif" in stage for stage in stages):
            return ErrorCategory.CLARIFICATION_ERROR
        if tool_failed or any("mcp" in stage or "tool" in stage for stage in stages):
            return ErrorCategory.MCP_TOOL_ERROR

        if any(token in stage for stage in stages for token in (
            "sql_generation", "generate_sql", "sql_generator", "sql_planning",
        )):
            return ErrorCategory.SQL_GENERATION_ERROR
        if any(token in stage for stage in stages for token in (
            "sql_execution", "execute_sql", "duckdb", "gold_result",
        )):
            return ErrorCategory.SQL_EXECUTION_ERROR
        if any(token in stage for stage in stages for token in (
            "result_comparison", "compare_results", "comparison",
        )):
            return ErrorCategory.RESULT_COMPARISON_ERROR

        # An unattempted SQL query has no execution error to diagnose.
        if generated_sql is not None and not str(generated_sql).strip() and sql_success is False:
            return ErrorCategory.SQL_GENERATION_ERROR
        if sql_success is False:
            return ErrorCategory.SQL_EXECUTION_ERROR
        if result_correct is False:
            return ErrorCategory.RESULT_COMPARISON_ERROR
        return ErrorCategory.UNKNOWN_ERROR
