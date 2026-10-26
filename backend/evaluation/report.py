"""Summary reports for already-computed evaluation results."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Iterable

from evaluation.analytics import BenchmarkAnalytics
from evaluation.models import EvaluationResult


def _nested(row: dict[str, Any], section: str, key: str, default: Any = None) -> Any:
    """Read a metric from nested output, with legacy flat-field fallback."""
    if key in row:
        return row[key]
    nested_value = row.get(section)
    nested = nested_value if isinstance(nested_value, dict) else {}
    if key in nested:
        return nested[key]
    legacy_keys = {
        ("sql_metrics", "execution_success"): ("sql_execution_success",),
        ("result_metrics", "correct"): ("result_correct",),
        ("schema_metrics", "recall"): ("schema_recall",),
        ("schema_metrics", "precision"): ("schema_precision",),
        ("schema_metrics", "retrieval_ms"): ("retrieval_ms",),
    }.get((section, key), ())
    for legacy_key in legacy_keys:
        if legacy_key in row:
            return row[legacy_key]
    return default


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = float(value)
        return value if math.isfinite(value) else None
    return None


def _mean(values: list[float], digits: int = 3) -> float:
    return round(sum(values) / len(values), digits) if values else 0.0


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1))
    return round(ordered[index], 3)


def _error_label(row: dict[str, Any]) -> str | None:
    errors_value = row.get("errors")
    errors = errors_value if isinstance(errors_value, dict) else {}
    stage = str(row.get("error_stage") or errors.get("stage") or "").strip()
    message = str(row.get("benchmark_error") or errors.get("message") or "").strip()
    if not stage and not message:
        return None
    text = f"{stage} {message}".lower()
    if any(token in text for token in (
        "permission", "access_control", "schema_access", "\u6743\u9650", "\u65e0\u6743",
    )):
        return "permission"
    if any(token in text for token in (
        "sql_execution", "execute_sql", "duckdb", "sql\u6267\u884c",
    )):
        return "sql_execution"
    if "embedding" in text:
        return "query_embedding"
    return stage or "benchmark"


@dataclass(frozen=True)
class BenchmarkSummary:
    summary_metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"summary_metrics": self.summary_metrics}


class BenchmarkReportBuilder:
    """Aggregate persisted EvaluationResult fields without running business logic."""

    @staticmethod
    def _rows(results: Iterable[EvaluationResult | dict[str, Any]]) -> list[dict[str, Any]]:
        return [result.to_dict() if isinstance(result, EvaluationResult) else dict(result) for result in results]

    @classmethod
    def build(cls, results: Iterable[EvaluationResult | dict[str, Any]]) -> BenchmarkSummary:
        rows = cls._rows(results)
        count = len(rows)
        successful = [row for row in rows if bool(_nested(row, "sql_metrics", "execution_success", False))]
        correct = [row for row in rows if bool(_nested(row, "result_metrics", "correct", False))]
        execution_times = [
            value for row in successful
            if (value := _number(_nested(row, "sql_metrics", "execution_ms"))) is not None
        ]
        retrieval_times = [
            value for row in rows
            if (value := _number(_nested(row, "schema_metrics", "retrieval_ms"))) is not None
        ]
        recalls = [
            value for row in rows
            if (value := _number(_nested(row, "schema_metrics", "recall"))) is not None
        ]
        precisions = [
            value for row in rows
            if (value := _number(_nested(row, "schema_metrics", "precision"))) is not None
        ]
        column_matches = sum(bool(_nested(row, "result_metrics", "column_match", False)) for row in rows)

        tool_calls = 0
        successful_tools = 0.0
        tool_latency_total = 0.0
        tool_latency_count = 0
        permission_checks = 0
        successful_permissions = 0.0
        permission_denied = 0
        clarification_rates: list[float] = []
        clarification_triggers = 0
        clarification_resolutions = 0
        for row in rows:
            agent_value = row.get("agent_metrics")
            agent = agent_value if isinstance(agent_value, dict) else {}
            call_count = int(_number(agent.get("tool_call_count")) or 0)
            tool_calls += call_count
            rate = _number(agent.get("tool_success_rate"))
            if rate is not None:
                successful_tools += rate * call_count
            latency = _number(agent.get("average_tool_latency_ms"))
            if latency is not None and call_count:
                tool_latency_total += latency * call_count
                tool_latency_count += call_count

            checks = int(_number(agent.get("permission_check_count")) or 0)
            permission_checks += checks
            permission_rate = _number(agent.get("permission_success_rate"))
            if permission_rate is not None:
                successful_permissions += permission_rate * checks
            permission_denied += int(_number(agent.get("permission_denied_count")) or 0)

            clarification_rate = _number(agent.get("clarification_rate"))
            if clarification_rate is not None:
                clarification_rates.append(clarification_rate)
            clarification_triggers += int(_number(agent.get("clarification_trigger_count")) or 0)
            clarification_resolutions += int(_number(agent.get("clarification_resolution_count")) or 0)

        errors: dict[str, int] = {}
        for row in rows:
            label = _error_label(row)
            if label:
                errors[label] = errors.get(label, 0) + 1

        agent_metrics = {
            "tool_call_count": tool_calls,
            "tool_success_rate": round(successful_tools / tool_calls, 9) if tool_calls else 0.0,
            "average_tool_latency_ms": round(tool_latency_total / tool_latency_count, 3)
            if tool_latency_count else 0.0,
            "permission_success_rate": round(successful_permissions / permission_checks, 9)
            if permission_checks else 0.0,
            "permission_denied_count": permission_denied,
            "clarification_rate": _mean(clarification_rates, 6),
            "clarification_resolution_rate": (
                round(clarification_resolutions / clarification_triggers, 9)
                if clarification_triggers else None
            ),
        }
        metrics = {
            "overall": {
                "case_count": count,
                "sql_execution_success_rate": round(len(successful) / count, 9) if count else 0.0,
                "result_accuracy": round(len(correct) / count, 9) if count else 0.0,
                "column_match_rate": round(column_matches / count, 9) if count else 0.0,
                "average_execution_ms": _mean(execution_times),
                "p95_execution_ms": _p95(execution_times),
            },
            "schema_retrieval": {
                "schema_recall": _mean(recalls, 6),
                "schema_precision": _mean(precisions, 6),
                "average_retrieval_ms": _mean(retrieval_times),
            },
            "agent_behavior": agent_metrics,
            "error_analysis": {
                "error_count": sum(errors.values()),
                "error_distribution": errors,
            },
        }
        metrics.update(BenchmarkAnalytics.analyze(rows))
        return BenchmarkSummary(metrics)

    @staticmethod
    def render_markdown(summary: BenchmarkSummary) -> str:
        metrics = summary.summary_metrics
        overall = metrics["overall"]
        schema = metrics["schema_retrieval"]
        agent = metrics["agent_behavior"]
        errors = metrics["error_analysis"]
        scenario_metrics = metrics.get("scenario_metrics", {})
        category_metrics = metrics.get("category_metrics", {})
        difficulty_metrics = metrics.get("difficulty_metrics", {})
        query_type_metrics = metrics.get("query_type_metrics", {})
        diagnosis = metrics.get("error_metrics", {})
        error_lines = [
            f"- `{name}`: {count}" for name, count in errors["error_distribution"].items()
        ] or ["- No errors"]
        resolution = (
            f"{agent['clarification_resolution_rate']:.2%}"
            if agent["clarification_resolution_rate"] is not None else "N/A"
        )
        scenario_lines = [
            f"| {name} | {item['case_count']} | {item['result_accuracy']:.2%} | "
            f"{item['sql_execution_success_rate']:.2%} |"
            for name, item in sorted(scenario_metrics.items())
        ] or ["| No data | 0 | 0.00% | 0.00% |"]
        category_lines = [
            f"| {name} | {item['case_count']} | {item['result_accuracy']:.2%} |"
            for name, item in sorted(category_metrics.items())
        ] or ["| No data | 0 | 0.00% |"]
        difficulty_lines = [
            f"| {name} | {item['case_count']} | {item['result_accuracy']:.2%} | "
            f"{item['average_execution_ms']:.3f} ms |"
            for name, item in sorted(difficulty_metrics.items())
        ] or ["| No data | 0 | 0.00% | 0.000 ms |"]
        query_type_lines = [
            f"| {name} | {item['case_count']} | {item['result_accuracy']:.2%} |"
            for name, item in sorted(query_type_metrics.items())
        ] or ["| No data | 0 | 0.00% |"]
        diagnosis_lines = [
            f"| {name} | {count} |"
            for name, count in sorted(diagnosis.get("error_distribution", {}).items())
        ] or ["| No failures | 0 |"]

        def dimension_errors(dimension: str) -> list[str]:
            rows = [
                f"| {group} | {name} | {count} |"
                for group, distribution in sorted(diagnosis.get(dimension, {}).items())
                for name, count in sorted(distribution.items())
            ]
            return rows or ["| No failures | — | 0 |"]

        return "\n".join([
            "# AskData Studio Benchmark Report", "",
            "## Overall Performance", "",
            f"- Case count: {overall['case_count']}",
            f"- SQL execution success rate: {overall['sql_execution_success_rate']:.2%}",
            f"- Result accuracy: {overall['result_accuracy']:.2%}",
            f"- Column match rate: {overall['column_match_rate']:.2%}",
            f"- Average execution latency: {overall['average_execution_ms']:.3f} ms",
            f"- P95 execution latency: {overall['p95_execution_ms']:.3f} ms", "",
            "## Schema Retrieval", "",
            f"- Recall: {schema['schema_recall']:.2%}",
            f"- Precision: {schema['schema_precision']:.2%}",
            f"- Average retrieval latency: {schema['average_retrieval_ms']:.3f} ms", "",
            "## Agent Behavior", "",
            f"- Tool call count: {agent['tool_call_count']}",
            f"- Tool success rate: {agent['tool_success_rate']:.2%}",
            f"- Average tool latency: {agent['average_tool_latency_ms']:.3f} ms",
            f"- Permission success rate: {agent['permission_success_rate']:.2%}",
            f"- Permission denied count: {agent['permission_denied_count']}",
            f"- Clarification rate: {agent['clarification_rate']:.2%}",
            f"- Clarification resolution rate: {resolution}", "",
            "## Error Analysis", "",
            f"- Error count: {errors['error_count']}", *error_lines, "",
            "## Scenario Performance", "",
            "| Scenario | Cases | Accuracy | SQL Success |",
            "|---|---:|---:|---:|",
            *scenario_lines, "",
            "## Category Performance", "",
            "| Category | Cases | Accuracy |",
            "|---|---:|---:|",
            *category_lines, "",
            "## Difficulty Analysis", "",
            "| Difficulty | Cases | Accuracy | Latency |",
            "|---|---:|---:|---:|",
            *difficulty_lines, "",
            "## Query Type Analysis", "",
            "| Query Type | Cases | Accuracy |",
            "|---|---:|---:|",
            *query_type_lines, "",
            "## Failure Diagnosis", "",
            f"- Failed cases: {diagnosis.get('failed_case_count', 0)}",
            f"- Failure rate: {diagnosis.get('failure_rate', 0.0):.2%}", "",
            "### Error Distribution", "",
            "| Error Type | Count |",
            "|---|---:|",
            *diagnosis_lines, "",
            "### Scenario Failure Analysis", "",
            "| Scenario | Error Type | Count |",
            "|---|---|---:|",
            *dimension_errors("scenario_error_analysis"), "",
            "### Category Failure Analysis", "",
            "| Category | Error Type | Count |",
            "|---|---|---:|",
            *dimension_errors("category_error_analysis"), "",
            "### Difficulty Failure Analysis", "",
            "| Difficulty | Error Type | Count |",
            "|---|---|---:|",
            *dimension_errors("difficulty_error_analysis"), "",
        ])

    @classmethod
    def write_markdown(
        cls,
        results: Iterable[EvaluationResult | dict[str, Any]],
        output: Path | str,
    ) -> BenchmarkSummary:
        summary = cls.build(results)
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(cls.render_markdown(summary), encoding="utf-8")
        return summary
