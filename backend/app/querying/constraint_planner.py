"""Deterministic planning of high-confidence query constraints."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import json
from pathlib import Path
import re
from typing import Any

import sqlglot
from sqlglot import exp

from ..database import physical_table_name
from ..datasources import DataSourceRuntime
from .sql_context import SqlContext

from .metric_planner import DEFAULT_CATALOG_PATH, MetricPlan


_MONTH_PATTERNS = (
    re.compile(r"(?<!\d)(20\d{2})-(0?[1-9]|1[0-2])(?!\d)"),
    re.compile(r"(?<!\d)(20\d{2})/(0?[1-9]|1[0-2])(?!\d)"),
    re.compile(r"(?<!\d)(20\d{2})年\s*(0?[1-9]|1[0-2])月?"),
)
_DAY_GRAIN_TERMS = ("每天", "每日", "按天", "按日", "逐日", "日趋势", "每天的")
_EXPLICIT_DAY_PATTERNS = (
    re.compile(r"(?<!\d)((?:19|20)\d{2})-(0?[1-9]|1[0-2])-(0?[1-9]|[12]\d|3[01])(?!\d)"),
    re.compile(r"(?<!\d)((?:19|20)\d{2})/(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])(?!\d)"),
    re.compile(r"(?<!\d)((?:19|20)\d{2})年\s*(0?[1-9]|1[0-2])月\s*(0?[1-9]|[12]\d|3[01])日"),
)


def _day_in_question(question: str) -> str | None:
    for pattern in _EXPLICIT_DAY_PATTERNS:
        match = pattern.search(question)
        if match:
            try:
                return date(*(int(part) for part in match.groups())).isoformat()
            except ValueError:
                return None
    return None


def _month_in_question(question: str) -> str | None:
    for pattern in _MONTH_PATTERNS:
        match = pattern.search(question)
        if match:
            return f"{match.group(1)}-{int(match.group(2)):02d}"
    return None


def _month_operator(question: str, month: str) -> str:
    """Distinguish an inclusive through-month request from one-month filtering."""
    for pattern in _MONTH_PATTERNS:
        for match in pattern.finditer(question):
            if f"{match.group(1)}-{int(match.group(2)):02d}" != month:
                continue
            prefix = question[max(0, match.start() - 12):match.start()]
            if re.search(r"(?:截至|截止)(?:到|至)?\s*$", prefix):
                return "month_on_or_before"
    return "month_equals"


def _metric_plan_dict(metric_plan: MetricPlan | dict[str, Any]) -> dict[str, Any]:
    if isinstance(metric_plan, MetricPlan):
        return metric_plan.to_dict()
    return metric_plan if isinstance(metric_plan, dict) else {}


@dataclass
class ConstraintPlan:
    filter_constraints: list[dict[str, Any]] = field(default_factory=list)
    time_constraints: list[dict[str, Any]] = field(default_factory=list)
    group_constraints: list[dict[str, Any]] = field(default_factory=list)
    join_constraints: list[dict[str, Any]] = field(default_factory=list)
    conditional_filter_rules: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    time_field_resolution: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "filter_constraints": [dict(item) for item in self.filter_constraints],
            "time_constraints": [dict(item) for item in self.time_constraints],
            "group_constraints": [dict(item) for item in self.group_constraints],
            "join_constraints": [dict(item) for item in self.join_constraints],
            "conditional_filter_rules": [dict(item) for item in self.conditional_filter_rules],
            "warnings": list(self.warnings),
            "time_field_resolution": dict(self.time_field_resolution),
        }


class ConstraintPlanner:
    """Plan explicit month constraints using metric and comparison metadata."""

    def __init__(self, catalog_path: Path | None = None, *, runtime: DataSourceRuntime | None = None) -> None:
        self.runtime = runtime
        self.context = SqlContext(runtime)
        path = catalog_path or DEFAULT_CATALOG_PATH
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.comparison_constraints = list(payload.get("comparison_constraints") or [])
        self.conditional_filter_rules = list(payload.get("conditional_filter_rules") or [])

    def plan_for_sql(
        self, question: str, metric_plan: MetricPlan | dict[str, Any],
        schema: dict[str, Any], sql: str,
    ) -> ConstraintPlan:
        """Resolve dates against validated SQL sources after schema validation.

        Catalog fields are considered only for source tables already present in
        the accessible graph. A field must still match an explicit user label.
        """
        initial = self.plan(question, metric_plan, schema)
        day = _day_in_question(question)
        month = None if day else _month_in_question(question)
        month_operator = _month_operator(question, month) if month else None
        if (not day and not month) or _metric_plan_dict(metric_plan).get("metrics"):
            return initial
        try:
            tree = sqlglot.parse_one(sql, read=self.context.dialect)
        except sqlglot.errors.ParseError:
            return initial
        graph_names = {str(t.get("name") or "").casefold()
                       for t in schema.get("tables") or []}
        sources = {t.name.casefold() for t in tree.find_all(exp.Table)} & graph_names
        if not sources:
            return initial
        if month:
            candidates = {
                (physical_table_name(table), str(field["name"]))
                for table in self.context.tables()
                if physical_table_name(table).casefold() in sources
                for field in table.get("fields") or []
                if str(field.get("source_type") or "").upper() in {"DATE", "TIMESTAMP"}
            }
            aliases = {
                table.alias_or_name.casefold(): table.name.casefold()
                for table in tree.find_all(exp.Table)
            }
            predicate_fields = set()
            for where in tree.find_all(exp.Where):
                for column in where.find_all(exp.Column):
                    if column.table:
                        matching = {
                            item for item in candidates
                            if item[0].casefold() == aliases.get(column.table.casefold())
                            and item[1].casefold() == column.name.casefold()
                        }
                    else:
                        matching = {item for item in candidates
                                    if item[1].casefold() == column.name.casefold()}
                    predicate_fields.update(matching)
            selected = predicate_fields if len(predicate_fields) == 1 else candidates
            if len(selected) != 1:
                return initial
            table, field_name = next(iter(selected))
            initial.time_constraints.append({
                "field": f"{table}.{field_name}", "operator": month_operator,
                "value": month, "source": "validated_sql_sources_and_schema",
                "confidence": 1.0,
            })
            initial.warnings = [warning for warning in initial.warnings
                                if not warning.startswith(f"问题包含月份 {month}，但没有可用指标时间字段")]
            initial.time_field_resolution = {
                "month": month, "source": "validated_sql_sources_and_schema",
                "status": "resolved", "candidates": [f"{t}.{f}" for t, f in sorted(candidates)],
                "selected_fields": [f"{table}.{field_name}"],
                "sql_source_tables": sorted(sources),
            }
            return initial
        fields = [dict(f) for f in schema.get("fields") or []
                  if str(f.get("table_name") or "").casefold() in sources]
        known = {(str(f.get("table_name") or ""), str(f.get("name") or ""))
                 for f in fields}
        for table in self.context.tables():
            name = physical_table_name(table)
            if name.casefold() not in sources:
                continue
            for field_definition in table.get("fields") or []:
                key = (name, str(field_definition["name"]))
                if key not in known:
                    fields.append({**field_definition, "table_name": name})
                    known.add(key)
        narrowed = {**schema, "fields": fields,
                    "tables": [t for t in schema.get("tables") or []
                               if str(t.get("name") or "").casefold() in sources]}
        resolved = self.plan(question, metric_plan, narrowed)
        resolved.time_field_resolution.update({
            "source": "validated_sql_sources_and_schema",
            "sql_source_tables": sorted(sources),
            "retrieval_candidates": initial.time_field_resolution.get("candidates", []),
        })
        return resolved

    def plan(
        self,
        question: str,
        metric_plan: MetricPlan | dict[str, Any],
        schema: dict[str, Any] | None = None,
    ) -> ConstraintPlan:
        self.context.require_open()
        self.context.check_graph(schema)
        result = ConstraintPlan()
        day = _day_in_question(question)
        month = None if day else _month_in_question(question)
        month_operator = _month_operator(question, month) if month else None
        metric_data = _metric_plan_dict(metric_plan)
        metrics = [item for item in metric_data.get("metrics") or [] if item.get("available", True)]
        matched_metric_names = {str(item.get("name") or "") for item in metrics}
        explicit_day_grain = any(term in question for term in _DAY_GRAIN_TERMS)
        if explicit_day_grain:
            for metric in metrics:
                time_field = metric.get("time_field") or {}
                table = str(time_field.get("table") or "")
                field_name = str(time_field.get("field") or "")
                if table and field_name:
                    result.group_constraints.append({
                        "field": f"{table}.{field_name}",
                        "grain": "day",
                        "source": "user_requirement",
                        "confidence": 1.0,
                    })
        graph_tables = {
            str(table.get("name") or "").casefold()
            for table in (schema or {}).get("tables") or []
            if isinstance(table, dict)
        }
        if day:
            day_fields = {
                (str((item.get("time_field") or {}).get("table") or ""),
                 str((item.get("time_field") or {}).get("field") or ""))
                for item in metrics
                if (item.get("time_field") or {}).get("table") and
                (item.get("time_field") or {}).get("field")
            }
            candidates = set(day_fields)
            resolution_source = "metric_catalog"
            if not day_fields:
                explicit_fields = {
                    (str(field.get("table_name") or ""), str(field.get("name") or ""))
                    for field in (schema or {}).get("fields") or []
                    if isinstance(field, dict) and
                    str(field.get("type") or "").casefold() in
                    {"日期", "时间", "date", "datetime", "timestamp"} and
                    ((bool(field.get("label")) and str(field["label"]) in question) or
                     (bool(field.get("name")) and str(field["name"]) in question))
                }
                explicit_fields = {item for item in explicit_fields if all(item)}
                candidates = explicit_fields
                resolution_source = "explicit_field_in_schema"
                if len(explicit_fields) == 1:
                    day_fields = explicit_fields
            result.time_field_resolution = {
                "date": day, "source": resolution_source,
                "status": "resolved" if day_fields else "ambiguous" if candidates else "missing",
                "candidates": [f"{table}.{name}" for table, name in sorted(candidates)],
                "selected_fields": [f"{table}.{name}" for table, name in sorted(day_fields)],
            }
            if day_fields:
                for table, field_name in sorted(day_fields):
                    if table and field_name:
                        result.time_constraints.append({
                            "field": f"{table}.{field_name}",
                            "operator": "day_equals",
                            "value": day,
                            "source": "user_requirement",
                            "confidence": 1.0,
                        })
            else:
                result.warnings.append(
                    f"问题包含日期 {day}，但无法唯一确定过滤时间字段"
                )
        question_folded = question.casefold()
        for rule in self.conditional_filter_rules:
            field_name = str(rule.get("field") or "")
            table_name = field_name.rsplit(".", 1)[0] if "." in field_name else ""
            if table_name.casefold() not in graph_tables:
                continue
            relevance_terms = [str(term).casefold() for term in rule.get("relevance_terms") or []]
            if relevance_terms and not any(term in question_folded for term in relevance_terms):
                continue
            # These policies describe conditions that need explicit user
            # evidence; they do not themselves add a filter to the SQL plan.
            result.conditional_filter_rules.append(dict(rule))

        if month:
            if not metrics:
                result.warnings.append(
                    f"问题包含月份 {month}，但没有可用指标时间字段可用于确定过滤列"
                )
            else:
                metric_time_fields: set[tuple[str, str]] = set()
                for metric in metrics:
                    time_field = metric.get("time_field") or {}
                    table = str(time_field.get("table") or "")
                    field_name = str(time_field.get("field") or "")
                    if table and field_name:
                        metric_time_fields.add((table, field_name))

                for table, field_name in sorted(metric_time_fields):
                    result.time_constraints.append({
                        "field": f"{table}.{field_name}",
                        "operator": month_operator,
                        "value": month,
                        "source": "user_requirement",
                        "confidence": 1.0,
                    })
                if metric_time_fields:
                    result.time_field_resolution = {
                        "month": month,
                        "source": ("confirmed_clarification" if any(
                            metric.get("source_selection") == "confirmed_clarification"
                            for metric in metrics) else "metric_catalog"),
                        "status": "resolved",
                        "candidates": [f"{table}.{field_name}"
                                       for table, field_name in sorted(metric_time_fields)],
                        "selected_fields": [f"{table}.{field_name}"
                                            for table, field_name in sorted(metric_time_fields)],
                    }

        for rule in self.comparison_constraints if month else []:
            trigger = any(str(term).casefold() in question_folded for term in rule.get("trigger_terms") or [])
            if not trigger or str(rule.get("required_metric") or "") not in matched_metric_names:
                continue
            target_table = str(rule.get("target_table") or "")
            target_field = str(rule.get("target_field") or "")
            if target_table.casefold() not in graph_tables:
                result.warnings.append(
                    f"检测到目标对比问题，但 Schema 图未包含 {target_table}；未生成强制目标月份约束"
                )
                continue
            result.time_constraints.append({
                "field": f"{target_table}.{target_field}",
                "operator": month_operator,
                "value": month,
                "source": "metric_definition",
                "confidence": 1.0,
                "rule": str(rule.get("name") or ""),
            })

        result.join_constraints = [dict(item) for item in metric_data.get("joins") or []]
        return result
