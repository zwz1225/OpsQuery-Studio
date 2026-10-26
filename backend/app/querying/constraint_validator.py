"""Conservative SQL AST checks for explicitly required month constraints."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import Scope, traverse_scope

from ..database import physical_table_name
from ..datasources import DataSourceRuntime
from .sql_context import SqlContext
from .constraint_planner import ConstraintPlan


@dataclass
class ConstraintValidationResult:
    status: str = "PASS"
    missing_constraints: list[dict[str, Any]] = field(default_factory=list)
    missing_group_constraints: list[dict[str, Any]] = field(default_factory=list)
    unsupported_constraints: list[dict[str, Any]] = field(default_factory=list)
    join_violations: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def errors(self) -> list[str]:
        missing = [
            f"SQL 缺少必要{'日期' if item.get('operator') == 'day_equals' else '月份'}约束："
            f"{item['field']}={item['value']}"
            for item in self.missing_constraints
        ]
        unsupported = [
            f"SQL 包含用户问题未明确要求的过滤条件：{item['field']} {item['operator']} {item['value']}。"
            f"{item.get('reason', '')}"
            for item in self.unsupported_constraints
        ]
        missing_groups = [
            f"SQL 未按要求的 {item.get('grain')} 粒度分组：{item['field']}"
            for item in self.missing_group_constraints
        ]
        return [*missing, *missing_groups, *unsupported]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "missing_constraints": [dict(item) for item in self.missing_constraints],
            "missing_group_constraints": [dict(item) for item in self.missing_group_constraints],
            "unsupported_constraints": [dict(item) for item in self.unsupported_constraints],
            "join_violations": [dict(item) for item in self.join_violations],
            "warnings": list(self.warnings),
        }


def _canonical_tables(database: str, tables: list[dict[str, Any]]) -> dict[str, dict[str, set[str]]]:
    result: dict[str, dict[str, set[str]]] = {}
    for table in tables:
        if table.get("database", "short_video_ops") != database:
            continue
        name = physical_table_name(table).casefold()
        result[name] = {
            "fields": {str(item["name"]).casefold() for item in table.get("fields") or []},
        }
    return result


def _field_in_scope(column: exp.Column, table_name: str, field_name: str, scope: Scope,
                    known: dict[str, dict[str, set[str]]]) -> bool:
    if column.name.casefold() != field_name.casefold():
        return False
    if column.table:
        source = scope.sources.get(column.table.casefold())
        if isinstance(source, exp.Table):
            return source.name.casefold() == table_name.casefold()
        if isinstance(source, Scope):
            return False
        # sqlglot can expose physical table names as source aliases.
        return column.table.casefold() == table_name.casefold()
    matching_tables = [
        source.name.casefold()
        for source in scope.sources.values()
        if isinstance(source, exp.Table) and field_name.casefold() in known.get(source.name.casefold(), {}).get("fields", set())
    ]
    return matching_tables == [table_name.casefold()]


def _predicate_has_month(
    expression: exp.Expression,
    table_name: str,
    field_name: str,
    month: str,
    scope: Scope,
    known: dict[str, dict[str, set[str]]],
) -> bool:
    comparisons = list(expression.find_all(exp.EQ, exp.GTE, exp.GT, exp.LT, exp.LTE, exp.Between))

    def references_target(node: exp.Expression) -> bool:
        return any(
            _field_in_scope(column, table_name, field_name, scope, known)
            for column in node.find_all(exp.Column)
        )

    month_start = f"{month}-01"
    year, month_num = map(int, month.split("-"))
    next_month = date(year + (month_num == 12), month_num % 12 + 1, 1).isoformat()
    lower_ok = upper_ok = False
    for comparison in comparisons:
        literals = [str(l.this) for l in comparison.find_all(exp.Literal) if l.is_string]
        if not references_target(comparison):
            continue
        if month in literals:
            return True
        if isinstance(comparison, (exp.GTE, exp.GT)) and month_start in literals:
            lower_ok = True
        if isinstance(comparison, (exp.LT, exp.LTE)) and next_month in literals:
            upper_ok = True
        if isinstance(comparison, exp.Between) and month_start in literals and next_month in literals:
            return True
    # Date-range constraints may be split across an AND; both boundaries must exist.
    if lower_ok and upper_ok:
        return True
    # Also support year-month fields constrained by an inclusive range.
    return False


def _predicate_has_month_on_or_before(
    expression: exp.Expression,
    table_name: str,
    field_name: str,
    month: str,
    scope: Scope,
    known: dict[str, dict[str, set[str]]],
) -> bool:
    """Require an inclusive month upper bound without excluding earlier months."""
    if expression.find(exp.Or) or expression.find(exp.Not):
        return False
    year, month_num = map(int, month.split("-"))
    next_month = date(year + (month_num == 12), month_num % 12 + 1, 1)
    next_month_day = next_month.isoformat()
    next_month_label = next_month.strftime("%Y-%m")
    month_start = f"{month}-01"

    def references_target(node: exp.Expression) -> bool:
        return any(
            _field_in_scope(column, table_name, field_name, scope, known)
            for column in node.find_all(exp.Column)
        )

    # A single-month range must not satisfy an "up to and including" request.
    for comparison in expression.find_all(exp.GT, exp.GTE):
        if references_target(comparison.this) and not references_target(comparison.expression):
            literals = {str(item.this) for item in comparison.expression.find_all(exp.Literal)
                        if item.is_string}
            if any(value >= month_start for value in literals if len(value) >= 10) or any(
                value >= month for value in literals if len(value) == 7
            ):
                return False

    for comparison in expression.find_all(exp.LT, exp.LTE):
        left, right = comparison.this, comparison.expression
        if not references_target(left):
            continue
        if references_target(right):
            continue
        literals = {str(item.this) for item in right.find_all(exp.Literal)
                    if item.is_string}
        if isinstance(comparison, exp.LT) and next_month_day in literals:
            return True
        if isinstance(left, (exp.TimeToStr, exp.ToChar)):
            format_arg = left.args.get("format")
            format_name = str(getattr(format_arg, "this", ""))
            if format_name in {"%Y-%m", "YYYY-MM"}:
                if isinstance(comparison, exp.LTE) and month in literals:
                    return True
                if isinstance(comparison, exp.LT) and next_month_label in literals:
                    return True
    return False


def _predicate_has_day(
    expression: exp.Expression,
    table_name: str,
    field_name: str,
    day: str,
    scope: Scope,
    known: dict[str, dict[str, set[str]]],
) -> bool:
    if expression.find(exp.Or):
        return False
    next_day = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    lower_ok = upper_ok = False
    for comparison in expression.find_all(exp.EQ, exp.GTE, exp.LT):
        if not any(_field_in_scope(column, table_name, field_name, scope, known)
                   for column in comparison.find_all(exp.Column)):
            continue
        literals = {str(item.this) for item in comparison.find_all(exp.Literal)
                    if item.is_string}
        if isinstance(comparison, exp.EQ) and day in literals:
            return True
        if isinstance(comparison, exp.GTE) and day in literals:
            lower_ok = True
        if isinstance(comparison, exp.LT) and next_day in literals:
            upper_ok = True
    return lower_ok and upper_ok


def _predicate_filter_value(
    expression: exp.Expression,
    table_name: str,
    field_name: str,
    scope: Scope,
    known: dict[str, dict[str, set[str]]],
) -> str | None:
    for comparison in expression.find_all(exp.EQ):
        if not any(
            _field_in_scope(column, table_name, field_name, scope, known)
            for column in comparison.find_all(exp.Column)
        ):
            continue
        literals = [literal for literal in comparison.find_all(exp.Literal)]
        if len(literals) != 1:
            continue
        literal = literals[0]
        return str(literal.this).casefold()
    return None


def _expression_groups_by_field(
    expression: exp.Expression,
    table_name: str,
    field_name: str,
    scope: Scope,
    known: dict[str, dict[str, set[str]]],
) -> bool | None:
    """Return True for a clear day key, False for a different key, None if unclear."""
    if isinstance(expression, exp.Literal) and not expression.is_string:
        try:
            position = int(expression.this) - 1
        except (TypeError, ValueError):
            return False
        projections = list(getattr(scope.expression, "expressions", []) or [])
        if position < 0 or position >= len(projections):
            return False
        projection = projections[position]
        if isinstance(projection, exp.Alias):
            projection = projection.this
        return _expression_groups_by_field(
            projection, table_name, field_name, scope, known
        )

    if isinstance(expression, exp.Column):
        if _field_in_scope(expression, table_name, field_name, scope, known):
            return True
        if not expression.table:
            for projection in getattr(scope.expression, "expressions", []) or []:
                if isinstance(projection, exp.Alias) and projection.alias.casefold() == expression.name.casefold():
                    return _expression_groups_by_field(
                        projection.this, table_name, field_name, scope, known
                    )
        return False

    if isinstance(expression, exp.Cast):
        return any(
            _field_in_scope(column, table_name, field_name, scope, known)
            for column in expression.find_all(exp.Column)
        )

    target_columns = [
        column for column in expression.find_all(exp.Column)
        if _field_in_scope(column, table_name, field_name, scope, known)
    ]
    if not target_columns:
        return False

    if isinstance(expression, exp.TimeToStr) or (
        isinstance(expression, exp.Anonymous) and expression.name.casefold() == "strftime"
    ):
        formats = [str(item.this) for item in expression.find_all(exp.Literal) if item.is_string]
        if any("%Y-%m-%d" in value for value in formats):
            return True
        if any("%Y-%m" in value or "%Y" in value for value in formats):
            return False
        return None

    if isinstance(expression, (exp.DateTrunc, exp.TimestampTrunc)):
        unit = expression.args.get("unit")
        return str(getattr(unit, "this", "")).strip("'\"").casefold() == "day"

    return None


class ConstraintValidator:
    """Check required month predicates and configured conditional filters."""

    def __init__(self, *, runtime: DataSourceRuntime | None = None) -> None:
        self.runtime = runtime
        self.context = SqlContext(runtime)

    def validate(
        self,
        sql: str,
        database: str,
        plan: ConstraintPlan | dict[str, Any],
        question: str = "",
    ) -> ConstraintValidationResult:
        self.context.require_open(database)
        result = ConstraintValidationResult()
        plan_data = plan.to_dict() if isinstance(plan, ConstraintPlan) else plan
        constraints = list((plan_data or {}).get("time_constraints") or [])
        group_constraints = list((plan_data or {}).get("group_constraints") or [])
        filter_rules = list((plan_data or {}).get("conditional_filter_rules") or [])
        if not constraints and not group_constraints and not filter_rules:
            result.status = "WARN" if (plan_data or {}).get("warnings") else "PASS"
            result.warnings.extend((plan_data or {}).get("warnings") or [])
            return result
        try:
            statements = [item for item in sqlglot.parse(sql, read=self.context.dialect) if item]
        except sqlglot.errors.SqlglotError as exc:
            result.status = "WARN"
            result.warnings.append(f"SQL 无法解析，未执行约束拦截：{exc}")
            return result
        if len(statements) != 1 or not isinstance(statements[0], exp.Query):
            result.status = "WARN"
            result.warnings.append("无法确定单条查询的月份约束，未执行约束拦截")
            return result

        known = _canonical_tables(database, self.context.tables(database))
        scopes = list(traverse_scope(statements[0]))
        # Also include the root query for SQL without CTEs.
        if not scopes:
            scopes = [Scope(statements[0], None, {}, {})]
        predicates: list[tuple[exp.Expression, Scope]] = []
        where_predicates: list[tuple[exp.Expression, Scope]] = []
        for scope in scopes:
            for where in scope.expression.find_all(exp.Where):
                predicates.append((where.this, scope))
                where_predicates.append((where.this, scope))
            for join in scope.expression.find_all(exp.Join):
                on = join.args.get("on")
                if on is not None:
                    predicates.append((on, scope))

        for constraint in constraints:
            operator = constraint.get("operator")
            if operator not in {"month_equals", "month_on_or_before", "day_equals"}:
                result.warnings.append(f"暂不支持的约束类型：{constraint.get('operator')}")
                continue
            field = str(constraint.get("field") or "")
            if "." not in field:
                result.warnings.append(f"约束字段格式不明确：{field}")
                continue
            table_name, field_name = field.rsplit(".", 1)
            checker = {
                "day_equals": _predicate_has_day,
                "month_equals": _predicate_has_month,
                "month_on_or_before": _predicate_has_month_on_or_before,
            }[operator]
            satisfied = any(checker(
                predicate, table_name, field_name,
                str(constraint.get("value") or ""), scope, known,
            ) for predicate, scope in predicates)
            if not satisfied:
                result.missing_constraints.append(dict(constraint))

        for constraint in group_constraints:
            if constraint.get("grain") != "day":
                result.warnings.append(f"暂不支持的分组粒度：{constraint.get('grain')}")
                continue
            field = str(constraint.get("field") or "")
            if "." not in field:
                result.warnings.append(f"分组约束字段格式不明确：{field}")
                continue
            table_name, field_name = field.rsplit(".", 1)
            checked = False
            matched = False
            uncertain = False
            for scope in scopes:
                group = scope.expression.args.get("group")
                if group is None:
                    continue
                checked = True
                for expression in group.expressions:
                    status = _expression_groups_by_field(
                        expression, table_name, field_name, scope, known
                    )
                    matched = matched or status is True
                    uncertain = uncertain or status is None
            if matched:
                continue
            if uncertain:
                result.warnings.append(
                    f"无法确认表达式是否保留日粒度：{field}"
                )
            elif checked or not checked:
                result.missing_group_constraints.append(dict(constraint))

        question_folded = question.casefold()
        for rule in filter_rules:
            field = str(rule.get("field") or "")
            if "." not in field:
                result.warnings.append(f"过滤策略字段格式不明确：{field}")
                continue
            table_name, field_name = field.rsplit(".", 1)
            supported_phrases = rule.get("supported_phrases_by_value") or {}
            guard_values = {str(value).casefold() for value in rule.get("guard_values") or []}
            for predicate, scope in where_predicates:
                value = _predicate_filter_value(
                    predicate, table_name, field_name, scope, known
                )
                if value is None or value not in guard_values:
                    continue
                phrases = [
                    str(phrase).casefold()
                    for phrase in supported_phrases.get(value, [])
                ]
                if any(phrase in question_folded for phrase in phrases):
                    continue
                item = {
                    "field": field,
                    "operator": "=",
                    "value": value,
                    "source": "model_inferred",
                    "reason": str(rule.get("reason") or "用户问题没有明确支持该过滤条件"),
                }
                result.unsupported_constraints.append(item)

        if result.missing_constraints or result.missing_group_constraints or result.unsupported_constraints:
            result.status = "BLOCK"
        elif result.warnings or (plan_data or {}).get("warnings"):
            result.status = "WARN"
            result.warnings.extend((plan_data or {}).get("warnings") or [])
        return result

