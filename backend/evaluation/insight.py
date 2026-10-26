"""Deterministic optimization insights from saved benchmark metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Iterable

from evaluation.models import EvaluationResult
from evaluation.regression import RegressionResult


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        return number if math.isfinite(number) else None
    return None


def _first_number(*values: Any) -> float | None:
    for value in values:
        number = _number(value)
        if number is not None:
            return number
    return None


@dataclass
class InsightResult:
    insights: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"insights": [dict(item) for item in self.insights]}


class BenchmarkInsightGenerator:
    """Apply documented thresholds; suggestions are hypotheses, not diagnoses."""

    def __init__(
        self,
        *,
        schema_precision_threshold: float = 0.1,
        schema_recall_drop_threshold: float = 0.05,
        minimum_result_accuracy: float = 0.9,
        latency_threshold_ms: float = 3000.0,
    ) -> None:
        if not (0 <= schema_precision_threshold <= 1):
            raise ValueError("schema_precision_threshold must be between 0 and 1")
        if not (0 <= schema_recall_drop_threshold <= 1):
            raise ValueError("schema_recall_drop_threshold must be between 0 and 1")
        if not (0 <= minimum_result_accuracy <= 1):
            raise ValueError("minimum_result_accuracy must be between 0 and 1")
        if not math.isfinite(latency_threshold_ms) or latency_threshold_ms <= 0:
            raise ValueError("latency_threshold_ms must be positive")
        self.schema_precision_threshold = schema_precision_threshold
        self.schema_recall_drop_threshold = schema_recall_drop_threshold
        self.minimum_result_accuracy = minimum_result_accuracy
        self.latency_threshold_ms = latency_threshold_ms

    @staticmethod
    def trace_metrics_from_cases(
        cases: Iterable[EvaluationResult | dict[str, Any]],
    ) -> dict[str, Any]:
        """Read already-recorded agent metrics, falling back to trace tool calls."""
        tool_count = 0
        tool_failures = 0.0
        permission_denied = 0
        stage_latencies: dict[str, list[float]] = {
            "average_schema_retrieval_ms": [],
            "average_tool_latency_ms": [],
            "average_sql_execution_ms": [],
        }
        for case in cases:
            row = case.to_dict() if isinstance(case, EvaluationResult) else case
            agent = _mapping(row.get("agent_metrics"))
            trace = _mapping(row.get("trace"))
            call_count = _number(agent.get("tool_call_count"))
            failure_rate = _number(agent.get("tool_failure_rate"))
            success_rate = _number(agent.get("tool_success_rate"))
            if failure_rate is None and success_rate is not None:
                failure_rate = 1 - success_rate
            if call_count is not None and failure_rate is not None:
                count = max(0, int(call_count))
                tool_count += count
                tool_failures += max(0.0, failure_rate) * count
            else:
                calls = trace.get("tool_calls")
                if isinstance(calls, list):
                    valid = [call for call in calls if isinstance(call, dict)]
                    tool_count += len(valid)
                    tool_failures += sum(call.get("success") is False for call in valid)

            denied = _number(agent.get("permission_denied_count"))
            permission = _mapping(trace.get("permission"))
            trace_denied = bool(permission.get("sql_blocked") or permission.get("denied_reason"))
            permission_denied += max(max(0, int(denied)) if denied is not None else 0,
                                     int(trace_denied))

            schema_latency = _number(_mapping(trace.get("schema_retrieval")).get("latency_ms"))
            sql_latency = _number(_mapping(trace.get("sql_execution")).get("execution_ms"))
            if schema_latency is not None:
                stage_latencies["average_schema_retrieval_ms"].append(schema_latency)
            if sql_latency is not None:
                stage_latencies["average_sql_execution_ms"].append(sql_latency)
            calls = trace.get("tool_calls")
            if isinstance(calls, list):
                for call in calls:
                    latency = _number(_mapping(call).get("latency_ms"))
                    if latency is not None:
                        stage_latencies["average_tool_latency_ms"].append(latency)

        return {
            "tool_call_count": tool_count,
            "tool_failure_rate": round(tool_failures / tool_count, 9) if tool_count else None,
            "permission_denied_count": permission_denied,
            **{
                key: round(sum(values) / len(values), 3) if values else None
                for key, values in stage_latencies.items()
            },
        }

    def generate(
        self,
        summary: dict[str, Any],
        analytics: dict[str, Any] | None = None,
        error_metrics: dict[str, Any] | None = None,
        regression_result: RegressionResult | dict[str, Any] | None = None,
        trace_metrics: dict[str, Any] | None = None,
    ) -> InsightResult:
        summary = _mapping(summary)
        metrics = _mapping(summary.get("summary_metrics")) or summary
        overall = _mapping(metrics.get("overall"))
        schema = _mapping(metrics.get("schema_retrieval"))
        agent = _mapping(metrics.get("agent_behavior"))
        analytics = _mapping(analytics)
        errors = _mapping(error_metrics) or _mapping(analytics.get("error_metrics")) or _mapping(
            metrics.get("error_metrics")
        )
        distribution = _mapping(errors.get("error_distribution"))
        regression = (
            regression_result.to_dict()
            if isinstance(regression_result, RegressionResult) else _mapping(regression_result)
        )
        overall_delta = _mapping(regression.get("overall_delta"))
        trace = _mapping(trace_metrics)
        case_count = _first_number(overall.get("case_count"), metrics.get("case_count"))
        if case_count == 0:
            return InsightResult()

        precision = _first_number(schema.get("schema_precision"), metrics.get("schema_precision"))
        recall_delta = _number(overall_delta.get("schema_recall"))
        sql_rate = _first_number(
            overall.get("sql_execution_success_rate"), metrics.get("sql_execution_success_rate")
        )
        accuracy = _first_number(overall.get("result_accuracy"), metrics.get("result_accuracy"))
        accuracy_delta = _number(overall_delta.get("result_accuracy"))
        sql_error_count = _number(distribution.get("SQL_EXECUTION_ERROR")) or 0
        execution_latency = _first_number(
            overall.get("average_execution_ms"), metrics.get("average_execution_ms")
        )
        latency = execution_latency if execution_latency is not None else _first_number(
            overall.get("average_latency"), metrics.get("average_latency")
        )
        latency_label = "平均 SQL 执行耗时" if execution_latency is not None else "平均耗时"
        tool_failure_rate = _first_number(trace.get("tool_failure_rate"), agent.get("tool_failure_rate"))
        tool_count = _first_number(trace.get("tool_call_count"), agent.get("tool_call_count"))
        if tool_failure_rate is None and tool_count and tool_count > 0:
            tool_success_rate = _number(agent.get("tool_success_rate"))
            if tool_success_rate is not None:
                tool_failure_rate = 1 - tool_success_rate
        denied_values = [
            value for value in (
                _number(trace.get("permission_denied_count")),
                _number(agent.get("permission_denied_count")),
                _number(distribution.get("PERMISSION_ERROR")),
            ) if value is not None
        ]
        denied = max(denied_values) if denied_values else None

        insights: list[dict[str, Any]] = []

        def add(
            category: str, severity: str, title: str, observation: str,
            possible_causes: list[str], suggestions: list[str],
        ) -> None:
            insights.append({
                "category": category,
                "severity": severity,
                "title": title,
                "observation": observation,
                "possible_causes": possible_causes,
                "suggestions": suggestions,
            })

        if precision is not None and precision < self.schema_precision_threshold:
            add(
                "schema_retrieval", "high", "Schema Retrieval Precision Low",
                f"Schema precision 为 {precision:.2%}，低于 {self.schema_precision_threshold:.2%} 阈值。",
                ["候选字段数量偏多", "字段相关性排序可能不够准确"],
                ["检查误召回字段样本", "评估降低 BM25_TOP_K 和 DENSE_TOP_K",
                 "评估收紧 RRF 候选范围并优化字段 rerank"],
            )
        if recall_delta is not None and recall_delta <= -self.schema_recall_drop_threshold:
            add(
                "schema_retrieval", "high", "Schema Recall Regressed",
                f"相较基线，Schema recall 下降 {abs(recall_delta):.2%}，达到 "
                f"{self.schema_recall_drop_threshold:.2%} 的关注阈值。",
                ["候选召回或重排规则变化", "模型或字段索引变化"],
                ["对照回退案例的 gold_fields 与 retrieved_fields", "核对检索配置与字段索引版本"],
            )
        if (sql_rate is not None and sql_rate < 1) or sql_error_count > 0:
            observation = (
                f"SQL 执行成功率为 {sql_rate:.2%}；失败案例占比 {1 - sql_rate:.2%}。"
                if sql_rate is not None and sql_rate < 1 else
                f"错误分类中有 {int(sql_error_count)} 条 SQL 执行失败案例。"
            )
            add(
                "sql_execution", "high", "SQL Execution Failures",
                observation,
                ["生成 SQL 与可访问 Schema 不匹配", "查询约束或 SQL 语法不满足执行要求"],
                ["检查失败案例的 generated_sql 和执行错误", "核对 Schema 匹配与查询约束"],
            )
        accuracy_observations: list[str] = []
        comparison_failures = _number(distribution.get("RESULT_COMPARISON_ERROR")) or 0
        if accuracy is not None and accuracy < self.minimum_result_accuracy:
            accuracy_observations.append(
                f"结果准确率为 {accuracy:.2%}，低于 {self.minimum_result_accuracy:.2%} 目标。"
            )
        if accuracy_delta is not None and accuracy_delta < 0:
            accuracy_observations.append(f"相较基线，结果准确率下降 {abs(accuracy_delta):.2%}。")
        if comparison_failures > 0:
            accuracy_observations.append(
                f"错误分类中有 {int(comparison_failures)} 条结果比较不一致案例。"
            )
        if accuracy_observations:
            add(
                "result_quality", "high", "Result Accuracy Needs Attention",
                " ".join(accuracy_observations),
                ["SQL 聚合口径或时间过滤条件可能偏离问题", "Gold Result 对照结果可能发生变化"],
                ["逐条复查错误案例的 SQL 逻辑、聚合口径和时间过滤",
                 "对照 Gold Result、生成结果及比较原因"],
            )
        if (tool_failure_rate is not None and tool_failure_rate > 0) or (
            _number(distribution.get("MCP_TOOL_ERROR")) or 0
        ) > 0:
            observation = (
                f"已记录的 MCP 工具调用失败率为 {tool_failure_rate:.2%}。"
                if tool_failure_rate is not None else
                f"错误分类中有 {int(distribution['MCP_TOOL_ERROR'])} 条 MCP 工具失败案例。"
            )
            add(
                "tool_call", "medium", "MCP Tool Calls Failed",
                observation,
                ["工具返回异常", "重试不足或数据库连接不稳定"],
                ["查看失败调用的 tool_name、错误和耗时", "核对重试策略及数据库连接状态"],
            )
        if denied is not None and denied > 0:
            add(
                "permission", "medium", "Permission Denials Observed",
                f"评测中记录到 {int(denied)} 次权限拒绝。",
                ["测试用户角色与用例预期不一致", "Schema 过滤或 SQL 访问规则触发拒绝"],
                ["先核对被拒绝用例的预期角色与授权范围",
                 "对照 Schema 过滤和 SQL 权限检查记录；确认属于异常后再调整配置"],
            )
        if latency is not None and latency > self.latency_threshold_ms:
            stage_labels = (
                ("average_schema_retrieval_ms", "Schema Retrieval"),
                ("average_tool_latency_ms", "MCP Tool"),
                ("average_sql_execution_ms", "SQL Execution"),
            )
            observed_stages = [
                f"{label} {value:.1f} ms"
                for key, label in stage_labels
                if (value := _number(trace.get(key))) is not None
            ]
            stage_detail = (
                " 已记录阶段均值：" + "、".join(observed_stages) + "。"
                if observed_stages else ""
            )
            add(
                "performance", "medium", "Average Latency Above Threshold",
                f"{latency_label}为 {latency:.1f} ms，超过 "
                f"{self.latency_threshold_ms:.1f} ms 阈值。{stage_detail}",
                ["检索、工具调用或 SQL 执行中的一个或多个阶段耗时偏高"],
                ["对照 Trace 中的 Schema Retrieval、MCP Tool 和 SQL Execution 耗时",
                 "定位慢查询与高耗时字段检索案例"],
            )
        return InsightResult(insights)
