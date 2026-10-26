"""Deterministic metric planning from a governed business metric catalog."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

import sqlglot
from sqlglot import exp

from ..database import physical_table_name
from ..datasources import DataSourceRuntime
from .sql_context import SqlContext


DEFAULT_CATALOG_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "metrics" / "metric_catalog.json"
)


@dataclass
class MetricPlan:
    metrics: list[dict[str, Any]] = field(default_factory=list)
    formulas: list[dict[str, Any]] = field(default_factory=list)
    joins: list[dict[str, str]] = field(default_factory=list)
    selected_sources: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics": [dict(item) for item in self.metrics],
            "formulas": [dict(item) for item in self.formulas],
            "joins": [dict(item) for item in self.joins],
            "selected_sources": list(self.selected_sources),
            "warnings": list(self.warnings),
        }


def _catalog_schema(tables: list[dict[str, Any]]) -> dict[str, set[str]]:
    return {
        physical_table_name(table): {
            str(field["name"]) for field in table.get("fields") or []
        }
        for table in tables
    }


class MetricPlanner:
    """Select catalog metrics and check SQL against their essential sources."""

    def __init__(self, catalog_path: Path | None = None, *, runtime: DataSourceRuntime | None = None) -> None:
        self.runtime = runtime
        self.context = SqlContext(runtime)
        path = catalog_path or DEFAULT_CATALOG_PATH
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.database = str(payload["database"])
        self.context.require_open(self.database)
        self.catalog = list(payload["metrics"])
        self._validate_catalog()

    def _validate_catalog(self) -> None:
        known = _catalog_schema(self.context.tables(self.database))
        names: set[str] = set()
        for metric in self.catalog:
            name = str(metric["name"])
            if name in names:
                raise ValueError(f"重复的指标定义：{name}")
            names.add(name)
            if not metric.get("aliases"):
                raise ValueError(f"指标缺少可识别名称：{name}")
            references: list[dict[str, str]] = [metric["time_field"]]
            if metric["kind"] == "aggregate":
                references.append(metric["canonical_source"])
                for alternative in metric.get("confirmed_alternatives") or []:
                    references.extend((alternative["source"], alternative["time_field"]))
            elif metric["kind"] == "ratio":
                references.extend((metric["numerator"], metric["denominator"]))
                for join in metric["joins"]:
                    for side in ("left", "right"):
                        table, field_name = join[side].split(".", 1)
                        references.append({"table": table, "field": field_name})
                references.extend(metric.get("required_filters") or [])
            else:
                raise ValueError(f"不支持的指标类型：{metric['kind']}")
            for reference in references:
                table, field_name = reference["table"], reference["field"]
                if field_name not in known.get(table, set()):
                    raise ValueError(f"指标 {name} 引用不存在的字段：{table}.{field_name}")

    def plan(
        self,
        question: str,
        schema: dict[str, Any],
        access_scope: dict[str, Any] | None = None,
        confirmed_clarifications: dict[str, Any] | None = None,
    ) -> MetricPlan:
        self.context.require_open(self.database)
        plan = MetricPlan()
        self.context.check_graph(schema)
        graph_tables = {
            str(table.get("name") or "")
            for table in schema.get("tables") or []
            if isinstance(table, dict)
        }
        allowed = set((access_scope or {}).get("allowed_tables") or [])
        matched = [
            definition for definition in self.catalog
            if any(str(alias) in question for alias in definition["aliases"])
        ]
        # In a funnel question, "activated users" is the numerator of the
        # activation-rate cohort, not the standalone daily KPI.
        ratio_names = {
            definition["name"] for definition in matched
            if definition["kind"] == "ratio"
        }
        for definition in matched:
            if definition["name"] == "activated_users" and "activation_rate" in ratio_names:
                continue
            name = definition["name"]
            confirmed_source = None
            if definition["kind"] == "aggregate":
                for alternative in definition.get("confirmed_alternatives") or []:
                    if any(
                        item.get("label") == alternative["label"]
                        and all(term in str(item.get("description") or "")
                                for term in alternative["description_terms"])
                        for item in (confirmed_clarifications or {}).values()
                        if isinstance(item, dict)
                    ):
                        confirmed_source = alternative
                        break
            if definition["kind"] == "aggregate":
                required_tables = {(confirmed_source["source"] if confirmed_source else
                                    definition["canonical_source"])["table"]}
            else:
                required_tables = {
                    definition["numerator"]["table"],
                    definition["denominator"]["table"],
                }
                required_tables.update(
                    join[side].split(".", 1)[0]
                    for join in definition.get("joins") or []
                    for side in ("left", "right")
                )
                required_tables.update(
                    item["table"] for item in definition.get("required_filters") or []
                )
            if access_scope is not None and "allowed_tables" in access_scope and any(
                f"{self.database}.{table}" not in allowed for table in required_tables
            ):
                plan.warnings.append(f"指标 {name} 在当前权限范围不可用")
                continue
            if definition["kind"] == "aggregate":
                source = confirmed_source["source"] if confirmed_source else definition["canonical_source"]
                metric = {
                    "name": name,
                    "kind": "aggregate",
                    "description": (confirmed_source.get("description", definition["description"])
                                    if confirmed_source else definition["description"]),
                    "source_table": source["table"],
                    "source_field": source["field"],
                    "aggregation": source["aggregation"],
                    "time_field": confirmed_source["time_field"] if confirmed_source else definition["time_field"],
                    "source_selection": "confirmed_clarification" if confirmed_source else "canonical",
                }
                plan.selected_sources.append(f"{source['table']}.{source['field']}")
            else:
                numerator, denominator = definition["numerator"], definition["denominator"]
                metric = {
                    "name": name,
                    "kind": "ratio",
                    "description": definition["description"],
                    "numerator": numerator,
                    "denominator": denominator,
                    "aggregation": "RATIO",
                    "time_field": definition["time_field"],
                    "formula": definition["formula"],
                    "joins": definition["joins"],
                    "required_filters": definition.get("required_filters") or [],
                }
                plan.formulas.append({
                    "metric": name,
                    "expression": definition["formula"],
                    "numerator": numerator,
                    "denominator": denominator,
                })
                plan.joins.extend(definition["joins"])
                plan.selected_sources.extend((
                    f"{numerator['table']}.{numerator['field']}",
                    f"{denominator['table']}.{denominator['field']}",
                ))
            missing = required_tables - graph_tables
            metric["available"] = not missing
            if missing:
                alternatives = definition.get("alternative_sources") or []
                available_alternatives = [
                    item["table"] for item in alternatives
                    if item["table"] in graph_tables
                ]
                detail = f"标准来源未进入 Schema 图：{', '.join(sorted(missing))}"
                if available_alternatives:
                    detail += (
                        f"；备选来源 {', '.join(available_alternatives)} 不等同于标准口径，"
                        "不能静默替代"
                    )
                plan.warnings.append(detail)
            plan.metrics.append(metric)
        plan.joins = list(dict.fromkeys(
            (join["left"], join["right"]) for join in plan.joins
        ))
        plan.joins = [{"left": left, "right": right} for left, right in plan.joins]
        plan.selected_sources = list(dict.fromkeys(plan.selected_sources))
        return plan

    def validate_sql(self, sql: str, plan: MetricPlan) -> list[str]:
        """Reject clear metric-source and cohort mistakes for the selected dialect."""
        self.context.require_open(self.database)
        if not any(metric.get("available") for metric in plan.metrics):
            return []
        try:
            expression = sqlglot.parse_one(sql, read=self.context.dialect)
        except sqlglot.errors.SqlglotError:
            return []
        if expression is None:
            return []
        aliases = {
            table.alias_or_name.casefold(): table.name.casefold()
            for table in expression.find_all(exp.Table)
        }
        tables = set(aliases.values())

        def matches(column: exp.Column, table: str, field_name: str) -> bool:
            if column.name.casefold() != field_name.casefold():
                return False
            if column.table:
                return aliases.get(column.table.casefold()) == table.casefold()
            return len(tables) == 1 and table.casefold() in tables

        errors: list[str] = []
        for metric in plan.metrics:
            if not metric.get("available"):
                continue
            if metric["kind"] == "aggregate":
                table, field_name = metric["source_table"], metric["source_field"]
                aggregation = metric["aggregation"].upper()
                aggregate_type = exp.Count if aggregation == "COUNT" else exp.Sum
                if table not in tables or not any(
                    matches(column, table, field_name)
                    for aggregate in expression.find_all(aggregate_type)
                    for column in aggregate.find_all(exp.Column)
                ):
                    errors.append(
                        f"指标 {metric['name']} 必须从 {table}.{field_name} 使用 {aggregation} 汇总，"
                        "不能以事件记录数替代"
                    )
            else:
                numerator, denominator = metric["numerator"], metric["denominator"]
                needed_tables = {numerator["table"], denominator["table"]}
                needed_tables.update(
                    join[side].split(".", 1)[0]
                    for join in metric.get("joins") or []
                    for side in ("left", "right")
                )
                if not needed_tables <= tables:
                    errors.append(
                        f"指标 {metric['name']} 必须使用规定的事实表："
                        f"{', '.join(sorted(needed_tables))}"
                    )
                    continue
                for join in metric.get("joins") or []:
                    left_table, left_field = join["left"].split(".", 1)
                    right_table, right_field = join["right"].split(".", 1)
                    linked = any(
                        isinstance(eq.left, exp.Column) and isinstance(eq.right, exp.Column)
                        and (
                            matches(eq.left, left_table, left_field)
                            and matches(eq.right, right_table, right_field)
                            or matches(eq.right, left_table, left_field)
                            and matches(eq.left, right_table, right_field)
                        )
                        for eq in expression.find_all(exp.EQ)
                    )
                    if not linked:
                        errors.append(
                            f"指标 {metric['name']} 必须沿 "
                            f"{join['left']} = {join['right']} 关联事实记录"
                        )
                if not any(
                    matches(column, numerator["table"], numerator["field"])
                    for aggregate in expression.find_all(exp.Sum, exp.Count)
                    for column in aggregate.find_all(exp.Column)
                ):
                    errors.append(
                        f"指标 {metric['name']} 的分子必须统计 "
                        f"{numerator['table']}.{numerator['field']} 为真的注册记录"
                    )
                if not any(
                    (not denominator.get("require_distinct") and isinstance(count.this, exp.Star))
                    or (any(
                        matches(column, denominator["table"], denominator["field"])
                        for column in count.find_all(exp.Column)
                    ) and (not denominator.get("require_distinct")
                           or isinstance(count.this, exp.Distinct)))
                    for count in expression.find_all(exp.Count)
                ):
                    errors.append(
                        f"指标 {metric['name']} 的分母必须统计 "
                        f"{denominator['table']}.{denominator['field']}"
                        + (" 的去重数" if denominator.get("require_distinct") else " 的记录数")
                    )
                for required in metric.get("required_filters") or []:
                    value = str(required["value"])
                    present = any(
                        isinstance(eq.left, exp.Column)
                        and matches(eq.left, required["table"], required["field"])
                        and isinstance(eq.right, exp.Literal) and eq.right.this == value
                        or isinstance(eq.right, exp.Column)
                        and matches(eq.right, required["table"], required["field"])
                        and isinstance(eq.left, exp.Literal) and eq.left.this == value
                        for where in expression.find_all(exp.Where)
                        for eq in where.find_all(exp.EQ)
                    )
                    if not present:
                        errors.append(
                            f"指标 {metric['name']} 必须过滤 "
                            f"{required['table']}.{required['field']}={value}"
                        )
        return errors
