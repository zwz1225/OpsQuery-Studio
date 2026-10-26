"""Internal result models used by the evaluation runners."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .clarification_metrics import ClarificationMetricsCalculator
from .metrics import ToolMetricsCalculator
from .permission_metrics import PermissionMetricsCalculator
from .trace import EvaluationTrace


@dataclass
class EvaluationResult:
    """Normalized result for one benchmark case.

    The nested metric groups are the internal representation.  ``to_dict`` also
    exposes the legacy flat keys consumed by the existing reports.
    """

    case_id: str
    question: str
    scenario: str
    category: str
    query_type: str
    difficulty: str
    classic: bool
    route_metrics: dict[str, Any] = field(default_factory=dict)
    schema_metrics: dict[str, Any] = field(default_factory=dict)
    sql_metrics: dict[str, Any] = field(default_factory=dict)
    result_metrics: dict[str, Any] = field(default_factory=dict)
    agent_metrics: dict[str, Any] = field(default_factory=dict)
    trace: EvaluationTrace = field(default_factory=EvaluationTrace)
    errors: dict[str, Any] = field(default_factory=dict)
    raw_output: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        tool_calls = self.trace.tool_calls if isinstance(self.trace, EvaluationTrace) else []
        permission = self.trace.permission if isinstance(self.trace, EvaluationTrace) else None
        clarification = (
            self.trace.clarification if isinstance(self.trace, EvaluationTrace) else None
        )
        self.agent_metrics = {
            **ToolMetricsCalculator.calculate(tool_calls),
            **PermissionMetricsCalculator.calculate(permission),
            **ClarificationMetricsCalculator.calculate(clarification),
            **self.agent_metrics,
        }

    def to_dict(self) -> dict[str, Any]:
        """Return nested data plus the legacy flat report fields."""
        schema = self.schema_metrics
        sql = self.sql_metrics
        result = self.result_metrics
        agent = self.agent_metrics
        errors = self.errors

        payload: dict[str, Any] = {
            "case_id": self.case_id,
            "scenario": self.scenario,
            "category": self.category,
            "query_type": self.query_type,
            "difficulty": self.difficulty,
            "classic": self.classic,
            "query": self.question,
            "route_metrics": dict(self.route_metrics),
            "schema_metrics": dict(schema),
            "sql_metrics": dict(sql),
            "result_metrics": dict(result),
            "agent_metrics": dict(agent),
            "trace": (
                self.trace.to_dict()
                if isinstance(self.trace, EvaluationTrace)
                else list(self.trace)
            ),
            "errors": dict(errors),
            "raw_output": dict(self.raw_output),
            # Existing report and summary fields.
            "schema_recall": schema.get("recall"),
            "schema_precision": schema.get("precision"),
            "schema_true_positive": schema.get("true_positive"),
            "retrieval_ms": schema.get("retrieval_ms"),
            "retrieved_fields": schema.get("retrieved_fields", []),
            "gold_fields": schema.get("gold_fields", []),
            "generated_sql": sql.get("generated_sql", ""),
            "sql_execution_success": sql.get("execution_success", False),
            "execution_ms": sql.get("execution_ms", 0.0),
            "result_correct": result.get("correct", False),
            "strict_result_correct": result.get("strict_correct"),
            "strict_comparison_reason": result.get("strict_reason"),
            "column_match": result.get("column_match", False),
            "comparison_reason": result.get("reason", ""),
            "gold_result_source": result.get("gold_result_source"),
            "gold_sql": result.get("gold_sql"),
            "gold_dialect": result.get("gold_dialect"),
            "gold_selection_key": result.get("gold_selection_key"),
            "gold_selection_version": result.get("gold_selection_version"),
            "comparison_target": result.get("comparison_target"),
            "agent_action": agent.get("action", ""),
            "query_contract": agent.get("query_contract", {}),
            "agent_reason": agent.get("reason", ""),
            "error_stage": errors.get("stage"),
            "benchmark_error": errors.get("message", ""),
        }
        # ModelClient metrics retain their existing top-level names for
        # summarize(), CSV output, and previously generated report consumers.
        payload.update(self.raw_output)
        return payload

