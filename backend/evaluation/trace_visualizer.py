"""Turn a recorded EvaluationTrace into ordered visualization nodes."""

from __future__ import annotations

from typing import Any

from evaluation.trace import EvaluationTrace


def _section(trace: dict[str, Any], key: str) -> dict[str, Any]:
    value = trace.get(key)
    return value if isinstance(value, dict) else {}


def _node(
    name: str,
    status: str,
    summary: str,
    *,
    metrics: dict[str, Any] | None = None,
    latency_ms: int | float | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "summary": summary,
        "metrics": metrics or {},
        "latency_ms": latency_ms,
    }


class TraceVisualizer:
    """Describe recorded stages; missing fields never imply success."""

    @staticmethod
    def visualize(trace: EvaluationTrace | dict[str, Any] | None) -> dict[str, Any]:
        data = trace.to_dict() if isinstance(trace, EvaluationTrace) else trace or {}
        if not isinstance(data, dict):
            raise TypeError("trace must be an EvaluationTrace or a dict")
        request = _section(data, "request")
        routing = _section(data, "routing")
        schema = _section(data, "schema_retrieval")
        permission = _section(data, "permission")
        decision = _section(data, "agent_decision")
        clarification = _section(data, "clarification")
        sql = _section(data, "sql_execution")
        comparison = _section(data, "result_comparison")
        calls = data.get("tool_calls") if isinstance(data.get("tool_calls"), list) else []
        errors = data.get("errors") if isinstance(data.get("errors"), list) else []
        error_stages = [
            str(item.get("stage") or "").lower()
            for item in errors if isinstance(item, dict)
        ]

        def error_message(tokens: tuple[str, ...]) -> str | None:
            for item in errors:
                if isinstance(item, dict) and any(
                    token in str(item.get("stage") or "").lower() for token in tokens
                ):
                    return str(item.get("message") or "") or None
            return None

        nodes = [
            _node(
                "Request", "success" if request else "skipped",
                str(request.get("question") or "No request recorded"),
                metrics={key: request[key] for key in ("case_id", "query_type") if key in request},
            ),
            _node(
                "Routing", "success" if routing.get("route") else "skipped",
                str(routing.get("route") or "No route recorded"),
                metrics={"route": routing["route"]} if routing.get("route") else {},
            ),
        ]

        schema_failed = any(
            any(token in stage for token in ("schema", "retrieval", "embedding", "rerank"))
            for stage in error_stages
        )
        schema_error_message = error_message(("schema", "retrieval", "embedding", "rerank"))
        nodes.append(_node(
            "Schema Retrieval",
            "failed" if schema_failed else "success" if schema else "skipped",
            "Schema retrieval failed" if schema_failed else
            "Schema fields retrieved" if schema else "No schema retrieval recorded",
            metrics={
                **{key: schema[key] for key in ("retrieved_fields", "recall", "precision")
                   if key in schema},
                **({"error": schema_error_message} if schema_failed and schema_error_message else {}),
            },
            latency_ms=schema.get("latency_ms"),
        ))

        if permission:
            denied = bool(permission.get("sql_blocked") or permission.get("denied_reason"))
            nodes.append(_node(
                "Permission Check",
                "failed" if denied else "success" if permission.get("checked") else "skipped",
                str(permission.get("denied_reason") or
                    ("Access allowed" if permission.get("checked") else "No permission check recorded")),
                metrics={key: permission[key] for key in (
                    "roles", "schema_before_filter_count", "schema_after_filter_count", "sql_blocked",
                ) if key in permission},
            ))

        action = decision.get("action")
        decision_failed = action == "error" or any("agent" in stage for stage in error_stages)
        nodes.append(_node(
            "Agent Decision",
            "failed" if decision_failed else "success" if action and action != "not_called" else "skipped",
            str(action or "No agent decision recorded"),
            metrics={key: decision[key] for key in ("action", "clarification_required", "reason")
                     if key in decision},
        ))

        if clarification and clarification.get("triggered"):
            status = str(clarification.get("final_status") or "").lower()
            failed = status in {"failed", "error", "abandoned", "cancelled", "canceled"}
            pending = not clarification.get("user_responded") and not clarification.get("continued_execution")
            nodes.append(_node(
                "Clarification", "failed" if failed else "pending" if pending else "success",
                str(clarification.get("question") or status or "Clarification requested"),
                metrics={key: clarification[key] for key in (
                    "option_count", "user_responded", "continued_execution", "final_status",
                ) if key in clarification},
            ))

        if calls:
            for index, call in enumerate(calls, 1):
                if not isinstance(call, dict):
                    continue
                success = call.get("success")
                nodes.append(_node(
                    "MCP Tool Call",
                    "success" if success is True else "failed" if success is False else "skipped",
                    str(call.get("tool_name") or f"Tool call {index}"),
                    metrics={"call_index": call.get("call_index", index), **{
                        key: call[key] for key in ("tool_name", "success", "retry_count", "error")
                        if key in call
                    }},
                    latency_ms=call.get("latency_ms"),
                ))
        else:
            nodes.append(_node("MCP Tool Call", "skipped", "No tool call recorded"))

        sql_error = any(
            any(token in stage for token in ("sql_execution", "execute_sql", "duckdb"))
            for stage in error_stages
        )
        sql_failed = sql.get("success") is False or sql_error
        sql_status = "failed" if sql_failed else "success" if sql.get("success") is True else "skipped"
        sql_error_message = (
            sql.get("error")
            or error_message(("sql_execution", "execute_sql", "duckdb", "gold_result"))
            or comparison.get("reason")
        ) if sql_failed else None
        nodes.append(_node(
            "SQL Execution", sql_status,
            "SQL execution failed" if sql_failed else
            "SQL executed" if sql_status == "success" else "No SQL execution recorded",
            metrics={
                **{key: sql[key] for key in ("generated_sql", "success", "result_rows", "backend", "dialect", "source_identity")
                   if key in sql},
                **({"error": str(sql_error_message)} if sql_error_message else {}),
            },
            latency_ms=sql.get("execution_ms"),
        ))

        comparison_status = (
            "skipped" if sql_status == "failed" else
            "success" if comparison.get("correct") is True else
            "failed" if comparison.get("correct") is False else "skipped"
        )
        nodes.append(_node(
            "Result Comparison", comparison_status,
            str(comparison.get("reason") or (
                "Result comparison skipped" if comparison_status == "skipped" else
                "Result matches expected output" if comparison_status == "success" else
                "Result differs from expected output"
            )),
            metrics={key: comparison[key] for key in (
                "comparison_target", "gold_result_source", "correct",
            ) if key in comparison},
        ))

        valid_errors = [item for item in errors if isinstance(item, dict)]
        if valid_errors:
            nodes.append(_node(
                "Error", "failed", "Recorded execution errors",
                metrics={"errors": valid_errors},
            ))
        return {"nodes": nodes}

    @classmethod
    def build(cls, trace: EvaluationTrace | dict[str, Any] | None) -> dict[str, Any]:
        return cls.visualize(trace)
