"""Multi-dimensional analytics for persisted benchmark results.

This module only aggregates fields already present in ``EvaluationResult``
records.  It never executes a query or invokes an agent.
"""

from __future__ import annotations

from collections import defaultdict
import math
from typing import Any, Iterable

from evaluation.diagnosis import FailureDiagnosis
from evaluation.models import EvaluationResult


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        return number if math.isfinite(number) else None
    return None


def _metric(row: dict[str, Any], section: str, key: str, default: Any = None) -> Any:
    value = row.get(section)
    if isinstance(value, dict) and key in value:
        return value[key]
    legacy = {
        ("sql_metrics", "execution_success"): "sql_execution_success",
        ("sql_metrics", "execution_ms"): "execution_ms",
        ("result_metrics", "correct"): "result_correct",
    }.get((section, key), key)
    return row.get(legacy, default)


def _mean(values: list[float], digits: int = 3) -> float:
    return round(sum(values) / len(values), digits) if values else 0.0


class BenchmarkAnalytics:
    """Build scenario/category/difficulty/query-type metric dimensions."""

    @staticmethod
    def _rows(results: Iterable[EvaluationResult | dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            result.to_dict() if isinstance(result, EvaluationResult) else dict(result)
            for result in results
        ]

    @staticmethod
    def _dimension(row: dict[str, Any], name: str) -> str:
        value = row.get(name)
        return str(value).strip() if value is not None and str(value).strip() else "unknown"

    @classmethod
    def _group_metrics(
        cls,
        rows: list[dict[str, Any]],
        dimension: str,
        *,
        include_agent: bool = False,
        include_latency: bool = False,
    ) -> dict[str, dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[cls._dimension(row, dimension)].append(row)

        output: dict[str, dict[str, Any]] = {}
        for name, group in groups.items():
            count = len(group)
            successful = [
                row for row in group
                if bool(_metric(row, "sql_metrics", "execution_success", False))
            ]
            correct = sum(bool(_metric(row, "result_metrics", "correct", False)) for row in group)
            metrics: dict[str, Any] = {
                "case_count": count,
                "result_accuracy": round(correct / count, 9) if count else 0.0,
            }
            if dimension in {"scenario", "category"}:
                metrics["sql_execution_success_rate"] = (
                    round(len(successful) / count, 9) if count else 0.0
                )
            if include_latency:
                latencies = [
                    number for row in successful
                    if (number := _number(_metric(row, "sql_metrics", "execution_ms"))) is not None
                ]
                metrics["average_execution_ms"] = _mean(latencies)
            if include_agent:
                metrics.update(cls._agent_metrics(group))
            output[name] = metrics
        return output

    @staticmethod
    def _agent_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
        tool_count = 0
        successful_tools = 0.0
        permission_checks = 0
        successful_permissions = 0.0
        clarification_rates: list[float] = []
        for row in rows:
            value = row.get("agent_metrics")
            agent = value if isinstance(value, dict) else {}
            calls = int(_number(agent.get("tool_call_count")) or 0)
            tool_count += calls
            tool_rate = _number(agent.get("tool_success_rate"))
            if tool_rate is not None:
                successful_tools += tool_rate * calls

            checks = int(_number(agent.get("permission_check_count")) or 0)
            permission_checks += checks
            permission_rate = _number(agent.get("permission_success_rate"))
            if permission_rate is not None:
                successful_permissions += permission_rate * checks

            clarification_rate = _number(agent.get("clarification_rate"))
            if clarification_rate is not None:
                clarification_rates.append(clarification_rate)

        return {
            "tool_success_rate": round(successful_tools / tool_count, 9) if tool_count else 0.0,
            "permission_success_rate": (
                round(successful_permissions / permission_checks, 9)
                if permission_checks else 0.0
            ),
            "clarification_rate": _mean(clarification_rates, 6),
        }

    @classmethod
    def analyze(cls, results: Iterable[EvaluationResult | dict[str, Any]]) -> dict[str, Any]:
        rows = cls._rows(results)
        return {
            "scenario_metrics": cls._group_metrics(
                rows, "scenario", include_agent=True, include_latency=True
            ),
            "category_metrics": cls._group_metrics(rows, "category"),
            "difficulty_metrics": cls._group_metrics(rows, "difficulty", include_latency=True),
            "query_type_metrics": cls._group_metrics(rows, "query_type"),
            "error_metrics": FailureDiagnosis.analyze(rows),
        }

    @classmethod
    def build(cls, results: Iterable[EvaluationResult | dict[str, Any]]) -> dict[str, Any]:
        """Alias for callers that use report-builder terminology."""
        return cls.analyze(results)
