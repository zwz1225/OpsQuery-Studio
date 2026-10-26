from __future__ import annotations

import json
import re
from fnmatch import fnmatch
from typing import Any, Callable, TYPE_CHECKING

from ..errors import PipelineStageError
from ..datasources import DataSourceRuntime
if TYPE_CHECKING:
    from ..mcp_runtime.client import LocalMcpClient
from ..model_client import ModelClient
from ..skills import SkillDefinition
from ..security import AccessScope
from .sql_context import SqlContext
from .metric_planner import MetricPlan, MetricPlanner
from .constraint_planner import ConstraintPlanner
from .constraint_validator import ConstraintValidator
from .sql_validator import SQLValidator


class SingleDatabaseAgent:
    """让模型通过MCP工具完成单数据库查询。"""

    def __init__(
        self,
        model_client: ModelClient,
        mcp_client_factory: Callable[[dict[str, Any]], LocalMcpClient],
        skill: SkillDefinition,
        max_tool_calls: int = 3,
        *, runtime: DataSourceRuntime | None = None,
    ) -> None:
        self.runtime = runtime
        self.model_client = model_client
        self.mcp_client_factory = mcp_client_factory
        self.skill = skill
        self.max_tool_calls = min(max_tool_calls, skill.max_tool_calls)
        self.sql_context = SqlContext(runtime)
        self.sql_validator = SQLValidator(runtime=runtime)
        self.metric_planner = MetricPlanner(runtime=runtime)
        self.constraint_planner = ConstraintPlanner(runtime=runtime)
        self.constraint_validator = ConstraintValidator(runtime=runtime)
        if runtime:
            runtime.assert_shared(self, self.sql_validator, self.metric_planner,
                                  self.constraint_planner, self.constraint_validator)

    def prepare(
        self,
        query: str,
        database: str,
        schema_graph: dict[str, Any],
        schema_context: str,
        retrieval: dict[str, Any],
        workspace: dict[str, Any],
        access_scope: dict[str, Any],
    ) -> dict[str, Any]:
        self.sql_context.check_graph(schema_graph)
        if self.runtime:
            self.runtime.require_open()
            if database != self.runtime.identity.logical_database_id:
                raise ValueError("Agent database does not match runtime")
            source = schema_graph.get("source_identity")
            if source is not None and source != self.runtime.identity.public():
                raise ValueError("Agent Schema graph datasource mismatch")
        database_tool = f"query_{database}"
        mcp_client = self.mcp_client_factory(access_scope)

        # 每次请求都通过MCP tools/list获取当前工具定义。
        catalog = mcp_client.list_tools()
        tools = [
            tool
            for tool in catalog
            if any(fnmatch(tool["name"], pattern) for pattern in self.skill.allowed_tools)
            and (not tool["name"].startswith("query_") or tool["name"] == database_tool)
        ]
        tool_names = {tool["name"] for tool in tools}
        if database_tool not in tool_names:
            raise PipelineStageError(
                "mcp_tool_discovery",
                f"没有找到数据库工具：{database_tool}",
            )

        metric_plan = self.metric_planner.plan(
            query, schema_graph, access_scope,
            workspace.get("confirmed_clarifications"),
        )
        constraint_plan = self.constraint_planner.plan(query, metric_plan, schema_graph)
        system = (
            f"你是单数据库问数智能体。\n\n{self.sql_context.instructions()}\n\n{self.skill.instructions}\n\n"
            "输入中的 metric_plan 是指标目录生成的标准业务口径。"
            "当指标可用时，SQL 必须遵守其来源、聚合、分子分母和关联键；"
            "不能用相邻事件表的记录数替代标准指标。"
            "输入中的 constraint_plan 包含有明确依据的查询条件，SQL 必须满足这些条件。"
        )

        observations: list[dict[str, Any]] = []
        tool_trace: list[dict[str, Any]] = []
        base_payload = {
            **({"source_identity": self.runtime.identity.public()} if self.runtime else {}),
            "sql_context": self.sql_context.public(),
            "access_scope": access_scope,
            "query": query,
            "database": database,
            "schema_graph": schema_graph,
            "retrieval": {
                "threshold": retrieval.get("threshold"),
                "selected_fields": retrieval.get("hits", []),
                "low_confidence_candidates": retrieval.get("low_confidence_candidates", []),
            },
            "confirmed_fields": workspace.get("schema_fields", []),
            "confirmed_parameters": workspace.get("confirmed_parameters", {}),
            "confirmed_clarifications": workspace.get("confirmed_clarifications", {}),
            "schema_text": schema_context,
            "metric_plan": metric_plan.to_dict(),
            "constraint_plan": constraint_plan.to_dict(),
            "mcp_tools": tools,
        }

        try:
            for call_index in range(1, self.max_tool_calls + 1):
                payload = {**base_payload, "tool_results": observations}
                decision = self._validated_decision(
                    system, payload, tool_names, metric_plan, constraint_plan
                )
                action = str(decision["action"])

                if action == "clarify":
                    clarification = decision.get("clarification")
                    if not isinstance(clarification, dict) or len(
                        clarification.get("options") or []
                    ) < 2:
                        raise ValueError("智能体返回的澄清信息不完整")
                    return {
                        "action": "clarify",
                        "clarification": clarification,
                        "tool_trace": tool_trace,
                    }

                if action != "call_tool":
                    raise ValueError("智能体必须返回call_tool或clarify")

                tool_name = str(decision["tool_name"])
                arguments = decision["arguments"]

                tool_result = mcp_client.call_tool(tool_name, arguments)
                trace = {
                    "call_index": call_index,
                    "tool": tool_name,
                    "arguments": arguments,
                    "query_contract": decision.get("query_contract", {}),
                    "result": tool_result,
                    "reason": str(decision.get("reason") or ""),
                    "sql_validation": decision.get("sql_validation"),
                    "sql_validation_attempts": decision.get("sql_validation_attempts", []),
                    "sql_round_numeric_repair": decision.get("sql_round_numeric_repair"),
                    "sql_bigint_boolean_repair": decision.get("sql_bigint_boolean_repair"),
                    "sql_order_alias_repair": decision.get("sql_order_alias_repair"),
                    "metric_planning": metric_plan.to_dict(),
                    "metric_validation": decision.get("metric_validation"),
                    "metric_validation_attempts": decision.get("metric_validation_attempts", []),
                    "constraint_validation": decision.get("constraint_validation"),
                    "constraint_validation_attempts": decision.get("constraint_validation_attempts", []),
                    "sql_context": self.sql_context.public(),
                }
                tool_trace.append(trace)

                if tool_name == database_tool:
                    if not bool(tool_result.get("success")) and call_index < self.max_tool_calls:
                        observations.append({
                            "tool": tool_name,
                            "result": tool_result,
                            "instruction": (
                                "上一条SQL执行失败。只根据数据库错误、原问题和Schema修正SQL，"
                                "不得改变查询口径，然后重新调用同一个数据库工具。"
                            ),
                        })
                        continue
                    return {
                        "action": "executed",
                        "execution": tool_result,
                        "tool_trace": tool_trace,
                        "source": "model_mcp",
                    }

                observations.append({"tool": tool_name, "result": tool_result})

            raise ValueError(f"MCP工具调用超过上限：{self.max_tool_calls}")
        except PipelineStageError:
            raise
        except (RuntimeError, KeyError, TypeError, ValueError) as exc:
            raise PipelineStageError("single_database_agent", str(exc)) from exc

    def _validated_decision(
        self,
        system: str,
        payload: dict[str, Any],
        tool_names: set[str],
        metric_plan: MetricPlan,
        constraint_plan: Any,
    ) -> dict[str, Any]:
        """结构化结果不完整时让模型最多修正两次，不执行不完整的工具调用。"""
        validation_error = ""
        previous_decision: dict[str, Any] | None = None
        validation_attempts: list[dict[str, Any]] = []
        metric_validation_attempts: list[dict[str, Any]] = []
        constraint_validation_attempts: list[dict[str, Any]] = []
        rejected_decisions: list[dict[str, Any]] = []
        for attempt in range(3):
            effective_constraint_plan = constraint_plan
            request_payload = dict(payload)
            if validation_error:
                request_payload["previous_invalid_output"] = previous_decision
                request_payload["output_validation_error"] = validation_error
                request_payload["output_validation_instruction"] = (
                    "上一次输出未通过调用前校验。根据错误修正JSON字段或SQL，"
                    "保持原查询口径并重新输出完整对象。"
                )
            decision = self.model_client.chat_json(
                system,
                json.dumps(request_payload, ensure_ascii=False),
            )
            previous_decision = decision
            validation_error = self._decision_error(decision, tool_names)
            if not validation_error and decision.get("action") == "clarify":
                parameter = str((decision.get("clarification") or {}).get("parameter") or "")
                confirmed = (payload.get("confirmed_clarifications") or {}).get(parameter)
                if confirmed:
                    validation_error = (
                        f"参数 {parameter} 已确认：{confirmed['label']}；"
                        f"{confirmed['description']}。按确认口径查询，不要重复询问同一参数。"
                    )
            if not validation_error:
                validation_error = self._explicit_filter_error(decision, payload)
            if not validation_error and decision.get("action") == "call_tool" and str(
                decision.get("tool_name") or ""
            ).startswith("query_"):
                validation = self.sql_validator.validate(
                    str((decision.get("arguments") or {}).get("sql") or ""),
                    str(payload.get("database") or ""),
                    payload.get("schema_graph"),
                    AccessScope.from_dict(payload["access_scope"]) if payload.get("access_scope") else None,
                )
                validation_attempts.append(validation.to_dict())
                if (validation.status == "BLOCK"
                    and self.sql_context.dialect == "postgres"
                    and validation.errors
                    and all(
                        "PostgreSQL ROUND(value, precision)" in error
                        or "PostgreSQL bigint Boolean comparison" in error
                        or "PostgreSQL ORDER BY expression cannot use SELECT alias" in error
                        for error in validation.errors
                    )):
                    original_sql = str((decision.get("arguments") or {}).get("sql") or "")
                    repaired_sql = original_sql
                    repair_round = any("PostgreSQL ROUND(value, precision)" in error
                                       for error in validation.errors)
                    repair_boolean = any("PostgreSQL bigint Boolean comparison" in error
                                         for error in validation.errors)
                    repair_order_alias = any(
                        "PostgreSQL ORDER BY expression cannot use SELECT alias" in error
                        for error in validation.errors
                    )
                    if repair_round:
                        repaired_sql = self.sql_validator.repair_postgres_round_numeric(repaired_sql)
                    if repair_boolean:
                        repaired_sql = self.sql_validator.repair_postgres_bigint_boolean(repaired_sql)
                    if repair_order_alias:
                        repaired_sql = self.sql_validator.repair_postgres_nested_order_aliases(
                            repaired_sql, str(payload.get("database") or ""),
                            payload.get("schema_graph"),
                        )
                    if repaired_sql != original_sql:
                        repaired_validation = self.sql_validator.validate(
                            repaired_sql, str(payload.get("database") or ""),
                            payload.get("schema_graph"),
                            AccessScope.from_dict(payload["access_scope"])
                            if payload.get("access_scope") else None,
                        )
                        validation_attempts.append(repaired_validation.to_dict())
                        if repaired_validation.status != "BLOCK":
                            decision["arguments"]["sql"] = repaired_sql
                            if repair_round:
                                decision["sql_round_numeric_repair"] = {
                                    "original_sql": original_sql,
                                    "repaired_sql": repaired_sql,
                                    "reason": "PostgreSQL two-argument ROUND requires numeric",
                                }
                            if repair_boolean:
                                decision["sql_bigint_boolean_repair"] = {
                                    "original_sql": original_sql,
                                    "repaired_sql": repaired_sql,
                                    "reason": "PostgreSQL bigint flag uses nonzero/zero semantics",
                                }
                            if repair_order_alias:
                                decision["sql_order_alias_repair"] = {
                                    "original_sql": original_sql,
                                    "repaired_sql": repaired_sql,
                                    "reason": "PostgreSQL nested ORDER BY alias expanded",
                                }
                            validation = repaired_validation
                decision["sql_validation"] = validation.to_dict()
                if validation.status == "BLOCK":
                    validation_error = "；".join(validation.errors)
                if not validation_error:
                    metric_errors = self.metric_planner.validate_sql(
                        str((decision.get("arguments") or {}).get("sql") or ""),
                        metric_plan,
                    )
                    decision["metric_validation"] = {"errors": metric_errors}
                    metric_validation_attempts.append({"errors": metric_errors})
                    if metric_errors:
                        validation_error = "；".join(metric_errors)
                if not validation_error:
                    effective_constraint_plan = self.constraint_planner.plan_for_sql(
                        str(payload.get("query") or ""), metric_plan,
                        payload.get("schema_graph") or {},
                        str((decision.get("arguments") or {}).get("sql") or ""),
                    )
                    if not isinstance(decision.get("query_contract"), dict):
                        decision["query_contract"] = {}
                    decision["query_contract"]["constraint_plan"] = effective_constraint_plan.to_dict()
                    constraint_validation = self.constraint_validator.validate(
                        str((decision.get("arguments") or {}).get("sql") or ""),
                        str(payload.get("database") or ""),
                        effective_constraint_plan,
                        str(payload.get("query") or ""),
                    )
                    decision["constraint_validation"] = constraint_validation.to_dict()
                    constraint_validation_attempts.append(constraint_validation.to_dict())
                    if constraint_validation.status == "BLOCK":
                        validation_error = "；".join(constraint_validation.errors)
            if not validation_error:
                contract = decision.get("query_contract")
                if not isinstance(contract, dict):
                    contract = {}
                contract["metric_plan"] = payload.get("metric_plan", {})
                contract["constraint_plan"] = effective_constraint_plan.to_dict()
                contract["constraint_validation"] = decision.get(
                    "constraint_validation", {"status": "PASS"}
                )
                decision["query_contract"] = contract
                decision["sql_validation_attempts"] = validation_attempts
                decision["metric_validation_attempts"] = metric_validation_attempts
                decision["constraint_validation_attempts"] = constraint_validation_attempts
                return decision
            arguments = decision.get("arguments")
            candidate_sql = (arguments.get("sql") if isinstance(arguments, dict)
                             and isinstance(arguments.get("sql"), str) else "")
            rejected_decisions.append({
                "attempt": attempt + 1,
                "action": str(decision.get("action") or ""),
                "candidate_sql": candidate_sql,
                "rejection_reason": validation_error,
                "sql_validation": decision.get("sql_validation"),
                "metric_validation": decision.get("metric_validation"),
                "constraint_validation": decision.get("constraint_validation"),
            })
            if attempt == 2:
                raise PipelineStageError(
                    "single_database_agent", validation_error,
                    diagnostics={"rejected_decisions": rejected_decisions},
                )
        raise ValueError(validation_error)

    def _decision_error(self, decision: dict[str, Any], tool_names: set[str]) -> str:
        action = str(decision.get("action") or "")
        if action not in self.skill.output_actions:
            return f"Skill不允许输出动作：{action}"
        if action == "clarify":
            clarification = decision.get("clarification")
            if not isinstance(clarification, dict) or len(clarification.get("options") or []) < 2:
                return "智能体返回的澄清信息不完整"
            return ""
        if action != "call_tool":
            return "智能体必须返回call_tool或clarify"
        tool_name = str(decision.get("tool_name") or "")
        if tool_name not in tool_names:
            return f"智能体选择了未提供的MCP工具：{tool_name}"
        if not isinstance(decision.get("arguments"), dict):
            return "MCP工具参数必须是JSON对象"
        return ""

    @staticmethod
    def _explicit_filter_error(
        decision: dict[str, Any],
        payload: dict[str, Any],
    ) -> str:
        """用户明确写出Schema样例值时，SQL必须使用该值。"""
        if decision.get("action") != "call_tool":
            return ""
        if not str(decision.get("tool_name") or "").startswith("query_"):
            return ""
        sql = str((decision.get("arguments") or {}).get("sql") or "")
        if not sql:
            return "数据库工具调用缺少SQL参数"
        query = str(payload.get("query") or "")
        selected_fields = (
            (payload.get("retrieval") or {}).get("selected_fields") or []
        )
        matched_samples: list[tuple[str, str, str, bool]] = []
        for field in selected_fields:
            field_identity = " ".join(
                str(field.get(key) or "")
                for key in ("field_name", "field_label", "field_type")
            ).casefold()
            if any(
                token in field_identity
                for token in ("date", "time", "month", "year", "日期", "时间", "月份", "年度")
            ):
                continue
            samples = list(field.get("samples") or [])
            if len(samples) > 20:
                continue
            for sample in samples:
                value = str(sample).strip()
                if len(value) < 2:
                    continue
                if isinstance(sample, (int, float)) and not isinstance(sample, bool):
                    query_pattern = rf"(?<![\d.]){re.escape(value)}(?![\d.])"
                    if not re.search(query_pattern, query):
                        continue
                    pattern = rf"(?<![\w.]){re.escape(value)}(?![\w.])"
                else:
                    if value.casefold() not in query.casefold():
                        continue
                    escaped = re.escape(value.replace("'", "''"))
                    pattern = rf"'\s*{escaped}\s*'"
                matched_samples.append(
                    (
                        str(field.get("field_name") or ""),
                        value,
                        pattern,
                        not isinstance(sample, (int, float)) or isinstance(sample, bool),
                    )
                )

        # 同一段文本可能同时命中“侵权”和“侵权搬运”等重叠枚举，
        # 此时只校验信息更完整的最长值，避免把正确SQL误判为缺少短枚举。
        precise_samples: list[tuple[str, str, str, bool]] = []
        for candidate in matched_samples:
            _, value, _, is_text = candidate
            if is_text and any(
                other_is_text
                and len(other_value) > len(value)
                and value.casefold() in other_value.casefold()
                for _, other_value, _, other_is_text in matched_samples
            ):
                continue
            precise_samples.append(candidate)

        missing = [
            f"{field_name}={value}"
            for field_name, value, pattern, _ in precise_samples
            if not re.search(pattern, sql, flags=re.IGNORECASE)
        ]
        if missing:
            return "SQL遗漏用户明确给出的Schema取值：" + "、".join(dict.fromkeys(missing))
        return ""
