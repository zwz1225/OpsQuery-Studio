"""Conservative column-existence checks before a database tool call.

The validator only blocks references that can be resolved to a known table
whose complete column list is available. The selected executor remains the final authority
for SQL validity and access control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import Scope, traverse_scope

from ..database import SCHEMA, physical_table_name
from ..datasources import DataSourceRuntime
from ..datasources.sql_policy import validate_readonly_sql
from ..security import AccessScope
from .sql_context import SqlContext


@dataclass
class SQLValidationResult:
    status: str = "PASS"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    invalid_columns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "invalid_columns": list(self.invalid_columns),
        }


def _field_names(fields: Any) -> set[str]:
    if not isinstance(fields, (list, tuple, set)):
        return set()
    names = set()
    for field in fields:
        name = field if isinstance(field, str) else field.get("name") or field.get("field_name")
        if name:
            names.add(str(name).casefold())
    return names


def _schema_columns(schema: Any, database: str, tables: list[dict[str, Any]] | None = None) -> dict[str, set[str]]:
    """Expand retrieved graph tables against canonical metadata when available.

    A retrieval graph only contains selected columns. Treating that subset as
    the complete table schema would incorrectly block valid SQL columns.
    """
    if tables is not None:
        return {physical_table_name(table).casefold(): _field_names(table.get("fields"))
                for table in tables}
    if isinstance(schema, dict) and "tables" in schema:
        tables = schema.get("tables") or []
        graph_fields = schema.get("fields") or []
    elif isinstance(schema, (list, tuple)):
        tables, graph_fields = schema, []
    elif isinstance(schema, dict):
        tables = [{"name": name, "fields": fields} for name, fields in schema.items()]
        graph_fields = []
    else:
        return {}

    canonical = {
        physical_table_name(table).casefold(): table
        for table in SCHEMA
        if table.get("database", "short_video_ops") == database
    }
    columns: dict[str, set[str]] = {}
    for table in tables:
        if not isinstance(table, dict):
            continue
        name = str(table.get("name") or table.get("id") or "").casefold()
        if not name:
            continue
        definition = canonical.get(name)
        explicit = _field_names(table.get("fields") or table.get("columns"))
        if definition is not None:
            # Full metadata is authoritative; retrieval hits are only a subset.
            columns[name] = _field_names(definition.get("fields"))
        elif explicit:
            columns[name] = explicit
        else:
            selected = [
                item for item in graph_fields
                if isinstance(item, dict)
                and str(item.get("table_name") or item.get("table_id") or "").casefold() == name
            ]
            # Selected hits alone do not prove that another field is absent.
            if selected:
                continue
    return columns


def _source_columns(source: Any, known: dict[str, set[str]]) -> set[str] | None:
    if isinstance(source, exp.Table):
        return known.get(source.name.casefold())
    if isinstance(source, Scope):
        names = source.expression.named_selects
        if not names or "*" in names:
            return None
        return {name.casefold() for name in names}
    return None


def _postgres_nested_order_aliases(
    statement: exp.Expression, known: dict[str, set[str]],
) -> list[tuple[exp.Column, exp.Expression]]:
    """Find output aliases nested inside ORDER BY expressions in PostgreSQL.

    PostgreSQL accepts ``ORDER BY alias`` but resolves ``ABS(alias)`` against
    input columns. Only classify an alias when every source has complete
    metadata and no source owns a physical column with that name.
    """
    references = []
    for scope in traverse_scope(statement):
        select = scope.expression
        if not isinstance(select, exp.Select) or not select.args.get("order"):
            continue
        projections: dict[str, list[exp.Expression]] = {}
        for projection in select.expressions:
            if isinstance(projection, exp.Alias):
                projections.setdefault(projection.alias.casefold(), []).append(projection.this)
        sources = [_source_columns(source, known) for source in scope.sources.values()]
        if any(fields is None for fields in sources):
            continue
        for ordered in select.args["order"].expressions:
            if isinstance(ordered.this, exp.Column):
                continue
            for column in ordered.this.find_all(exp.Column):
                name = column.name.casefold()
                if (column.table or len(projections.get(name, [])) != 1
                        or any(name in fields for fields in sources)):
                    continue
                references.append((column, projections[name][0]))
    return references


def _postgres_round_type_errors(statement: exp.Expression, tables: list[dict[str, Any]]) -> list[str]:
    """Block a provable float argument to PostgreSQL's two-argument ROUND.

    This is intentionally conservative: unknown CTE columns and ambiguous
    unqualified columns are left for PostgreSQL, not guessed from a name.
    """
    floating = {
        physical_table_name(table).casefold(): {
            str(field["name"]).casefold()
            for field in table.get("fields") or []
            if str(field.get("postgresql_type") or "").casefold() in
            {"double precision", "real"}
        }
        for table in tables
    }
    errors = []
    for scope in traverse_scope(statement):
        sources = {
            alias.casefold(): source.name.casefold()
            for alias, source in scope.sources.items()
            if isinstance(source, exp.Table)
        }
        for rounded in scope.expression.find_all(exp.Round):
            if rounded.args.get("decimals") is None or rounded.find_ancestor(exp.Select) is not scope.expression:
                continue
            for column in rounded.this.find_all(exp.Column):
                if column.table:
                    source = sources.get(column.table.casefold())
                else:
                    matches = [table for table in sources.values()
                               if column.name.casefold() in floating.get(table, set())]
                    source = matches[0] if len(matches) == 1 else None
                if source is None or column.name.casefold() not in floating.get(source, set()):
                    continue
                ancestor = column.parent
                numeric_cast = False
                while ancestor is not None and ancestor is not rounded:
                    if isinstance(ancestor, (exp.Cast, exp.TryCast)) and (
                        ancestor.args.get("to") is not None and
                        ancestor.args["to"].this == exp.DataType.Type.DECIMAL
                    ):
                        numeric_cast = True
                        break
                    ancestor = ancestor.parent
                if not numeric_cast:
                    errors.append(
                        "PostgreSQL ROUND(value, precision) 包含未转换的浮点字段 "
                        f"{source}.{column.name}；请对完整的第一个参数显式转换为numeric"
                    )
                    break
    return list(dict.fromkeys(errors))


def _postgres_bigint_boolean_predicates(
    statement: exp.Expression, tables: list[dict[str, Any]],
) -> list[tuple[exp.EQ, exp.Column, bool, str]]:
    """Find boolean equality on a verified PostgreSQL bigint field."""
    bigint = {
        physical_table_name(table).casefold(): {
            str(field["name"]).casefold()
            for field in table.get("fields") or []
            if str(field.get("postgresql_type") or "").casefold() == "bigint"
        }
        for table in tables
    }
    found = []
    for scope in traverse_scope(statement):
        sources = {
            alias.casefold(): source.name.casefold()
            for alias, source in scope.sources.items()
            if isinstance(source, exp.Table)
        }
        for predicate in scope.expression.find_all(exp.EQ):
            if predicate.find_ancestor(exp.Select) is not scope.expression:
                continue
            column, boolean = (
                (predicate.left, predicate.right)
                if isinstance(predicate.left, exp.Column)
                and isinstance(predicate.right, exp.Boolean)
                else (predicate.right, predicate.left)
            )
            if not isinstance(column, exp.Column) or not isinstance(boolean, exp.Boolean):
                continue
            if column.table:
                source = sources.get(column.table.casefold())
            else:
                matches = [table for table in sources.values()
                           if column.name.casefold() in bigint.get(table, set())]
                source = matches[0] if len(matches) == 1 else None
            if source and column.name.casefold() in bigint.get(source, set()):
                found.append((predicate, column, bool(boolean.this), source))
    return found


def _postgres_bigint_boolean_errors(
    statement: exp.Expression, tables: list[dict[str, Any]],
) -> list[str]:
    return list(dict.fromkeys(
        f"PostgreSQL bigint Boolean comparison {source}.{column.name} = "
        f"{'TRUE' if truth else 'FALSE'}; use <> 0 or = 0 on this flag"
        for _, column, truth, source in _postgres_bigint_boolean_predicates(statement, tables)
    ))


class SQLValidator:
    """Classify provable bad columns as BLOCK and uncertainty as WARN."""

    def __init__(self, *, runtime: DataSourceRuntime | None = None) -> None:
        self.runtime = runtime
        self.context = SqlContext(runtime)

    def repair_postgres_nested_order_aliases(
        self, sql: str, database: str, schema: Any,
    ) -> str:
        """Expand only provably invalid nested ORDER BY output aliases."""
        if self.context.dialect != "postgres":
            return sql
        statements = [item for item in sqlglot.parse(sql, read="postgres") if item]
        if len(statements) != 1 or not isinstance(statements[0], exp.Query):
            return sql
        statement = statements[0]
        known = _schema_columns(
            schema, database, self.context.tables(database) if self.runtime else None,
        )
        references = _postgres_nested_order_aliases(statement, known)
        for column, projection in references:
            column.replace(projection.copy())
        return statement.sql(dialect="postgres") if references else sql

    def repair_postgres_round_numeric(self, sql: str) -> str:
        """Cast the full first argument of two-argument ROUND to numeric.

        Call only after the ordinary validator identified ROUND type errors
        as the sole BLOCK reason. The caller must validate the rewritten SQL
        again before it reaches the executor.
        """
        if self.context.dialect != "postgres":
            return sql
        statements = [item for item in sqlglot.parse(sql, read="postgres") if item]
        if len(statements) != 1:
            return sql
        statement = statements[0]
        changed = False
        for rounded in statement.find_all(exp.Round):
            if rounded.args.get("decimals") is None:
                continue
            argument = rounded.this
            if isinstance(argument, (exp.Cast, exp.TryCast)) and (
                argument.args.get("to") is not None
                and argument.args["to"].this == exp.DataType.Type.DECIMAL
            ):
                continue
            rounded.set("this", exp.Cast(
                this=argument.copy(), to=exp.DataType.build("numeric", dialect="postgres"),
            ))
            changed = True
        return statement.sql(dialect="postgres") if changed else sql

    def repair_postgres_bigint_boolean(self, sql: str) -> str:
        """Translate only verified bigint = TRUE/FALSE to nonzero/zero tests."""
        if self.context.dialect != "postgres":
            return sql
        statements = [item for item in sqlglot.parse(sql, read="postgres") if item]
        if len(statements) != 1:
            return sql
        statement = statements[0]
        matches = _postgres_bigint_boolean_predicates(
            statement, self.context.tables(self.runtime.identity.logical_database_id),
        )
        for predicate, column, truth, _ in matches:
            comparison = exp.NEQ if truth else exp.EQ
            predicate.replace(comparison(
                this=column.copy(), expression=exp.Literal.number(0),
            ))
        return statement.sql(dialect="postgres") if matches else sql

    def validate(self, sql: str, database: str, schema: Any,
                 access_scope: AccessScope | None = None) -> SQLValidationResult:
        self.context.require_open(database)
        self.context.check_graph(schema)
        result = SQLValidationResult()
        try:
            if self.runtime:
                try:
                    sql = validate_readonly_sql(database, sql, self.context.tables(database), access_scope,
                        dialect=self.context.dialect, physical_schema=self.runtime.identity.physical_schema)
                except ValueError as exc:
                    result.status = "BLOCK"
                    result.errors.append(str(exc))
                    return result
            statements = [statement for statement in sqlglot.parse(sql, read=self.context.dialect) if statement]
        except sqlglot.errors.SqlglotError as exc:
            result.warnings.append(f"SQL 无法解析，交由数据库校验：{exc}")
            result.status = "WARN"
            return result
        if len(statements) != 1 or not isinstance(statements[0], exp.Query):
            result.warnings.append("无法确定单条查询的字段归属，交由数据库校验")
            result.status = "WARN"
            return result

        known = _schema_columns(schema, database, self.context.tables(database) if self.runtime else None)
        if not known:
            result.warnings.append("没有完整的表字段元数据，交由数据库校验")
            result.status = "WARN"
            return result

        for scope in traverse_scope(statements[0]):
            sources = {
                alias.casefold(): _source_columns(source, known)
                for alias, source in scope.sources.items()
            }
            output_aliases = {
                name.casefold() for name in scope.expression.named_selects
            }
            for column in scope.columns:
                name = column.name.casefold()
                if column.table:
                    alias = column.table.casefold()
                    fields = sources.get(alias)
                    if alias not in sources or fields is None:
                        result.warnings.append(f"无法确定字段来源：{column.sql()}")
                    elif name not in fields:
                        result.invalid_columns.append(column.sql())
                    continue

                # SQL dialects permit SELECT aliases in GROUP BY / ORDER BY.
                if name in output_aliases and column.find_ancestor(
                    exp.Group, exp.Order, exp.Having
                ):
                    continue
                available = list(sources.values())
                if not available or any(fields is None for fields in available):
                    result.warnings.append(f"无法确定字段来源：{column.sql()}")
                elif not any(name in fields for fields in available):
                    result.invalid_columns.append(column.sql())
                elif sum(name in fields for fields in available) > 1:
                    result.warnings.append(f"字段可能有多个来源：{column.sql()}")

        result.invalid_columns = list(dict.fromkeys(result.invalid_columns))
        result.warnings = list(dict.fromkeys(result.warnings))
        round_errors = (_postgres_round_type_errors(statements[0], self.context.tables(database))
                        if self.context.dialect == "postgres" else [])
        boolean_errors = (_postgres_bigint_boolean_errors(statements[0], self.context.tables(database))
                          if self.context.dialect == "postgres" else [])
        order_alias_errors = (list(dict.fromkeys(
            column.name for column, _ in _postgres_nested_order_aliases(statements[0], known)
        )) if self.context.dialect == "postgres" else [])
        if result.invalid_columns:
            result.status = "BLOCK"
            result.errors = [
                f"字段 {name} 不存在于对应表，请根据 Schema 重新选择字段"
                for name in result.invalid_columns
            ]
        elif round_errors or boolean_errors or order_alias_errors:
            result.status = "BLOCK"
            result.errors = round_errors + boolean_errors + [
                "PostgreSQL ORDER BY expression cannot use SELECT alias "
                f"{name}; repeat its expression or sort by the bare alias"
                for name in order_alias_errors
            ]
        elif result.warnings:
            result.status = "WARN"
        return result
