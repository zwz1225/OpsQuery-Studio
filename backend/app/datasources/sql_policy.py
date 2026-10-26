from __future__ import annotations

import re
from typing import Any
import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import traverse_scope
from ..database import physical_table_name
from ..security import AccessScope


def clean_sql(text: str) -> str:
    cleaned = re.sub(r"^```(?:sql)?\s*|\s*```$", "", text.strip(), flags=re.I)
    return cleaned.strip()


def validate_readonly_sql(database: str, sql: str, tables: list[dict[str, Any]],
                          access_scope: AccessScope | None = None, *, dialect: str = "duckdb",
                          physical_schema: str | None = None) -> str:
    cleaned = clean_sql(sql).rstrip(";").strip()
    statements = [item for item in sqlglot.parse(cleaned, read=dialect) if item]
    if len(statements) != 1:
        raise ValueError("一次只允许执行一条SQL")
    statement = statements[0]
    if not isinstance(statement, exp.Query):
        raise ValueError("只允许执行SELECT/WITH只读查询")
    forbidden_nodes = {
        "insert", "update", "delete", "merge", "create", "drop", "alter",
        "copy", "attach", "detach", "command", "transaction", "grant", "revoke",
    }
    if any(node.key in forbidden_nodes for node in statement.walk()):
        raise ValueError("SQL包含禁止的写入或管理操作")

    if dialect == "postgres":
        if any(node.key in {"into", "lock", "objectidentifier"} for node in statement.walk()):
            raise ValueError("SQL包含禁止的写入、锁定或对象类型转换")
        # Only explicitly supported analytical builtins. Read-only transactions
        # alone do not stop advisory locks, session changes, external functions
        # or other side effects of SELECT expressions.
        allowed_functions = {
            "COUNT", "SUM", "AVG", "MIN", "MAX", "CAST", "COALESCE", "NULLIF",
            "ROUND", "FLOOR", "CEIL", "ABS", "GREATEST", "LEAST", "CONCAT",
            "LOWER", "UPPER", "LENGTH", "SUBSTRING", "TRIM", "REPLACE", "SPLIT_PART",
            "EXTRACT", "TIME_TO_STR", "DATE_TRUNC", "TIMESTAMP_TRUNC", "DATE",
            "CURRENT_DATE", "CURRENT_TIMESTAMP", "CURRENT_TIME", "NOW", "AGE",
            "ROW_NUMBER", "RANK", "DENSE_RANK", "LAG", "LEAD", "FIRST_VALUE", "LAST_VALUE",
            "PERCENT_RANK", "CUME_DIST", "NTILE", "BOOL_AND", "BOOL_OR", "STRING_AGG",
            "ARRAY_AGG", "STDDEV", "STDDEV_POP", "STDDEV_SAMP", "VAR_POP", "VAR_SAMP",
            "CASE", "IF", "DATE_DIFF", "TIME_TO_UNIX", "TO_TIMESTAMP",
        }
        for node in statement.walk():
            if isinstance(node, exp.Dot) and isinstance(node.expression, exp.Func):
                raise ValueError("不允许调用限定来源的函数")
            # SQLGlot also models boolean operators as Func subclasses.
            # They are syntax, not callable functions; still inspect every
            # descendant so an unsafe function inside AND/OR/NOT is rejected.
            if isinstance(node, exp.Func) and not isinstance(node, (exp.And, exp.Or, exp.Not)):
                name = node.name.upper() if isinstance(node, exp.Anonymous) else node.sql_name()
                if name not in allowed_functions:
                    raise ValueError("SQL包含不允许的函数")
            if isinstance(node, exp.DataType) and node.this == exp.DataType.Type.USERDEFINED:
                raise ValueError("不允许转换为自定义类型")

    # 查询必须显式列出返回字段。
    for select in statement.find_all(exp.Select):
        if any(
            isinstance(projection, exp.Star)
            or isinstance(projection, exp.Column) and projection.is_star
            for projection in select.expressions
        ):
            raise ValueError("不允许使用SELECT *，必须明确列出查询字段")

    if access_scope and not access_scope.allows_database(database):
        raise ValueError("当前用户无权访问该数据库")

    database_tables = [
        table
        for table in tables
        if table.get("database", "short_video_ops") == database
    ]
    allowed = {
        physical_table_name(table): table["id"]
        for table in database_tables
    }
    # Resolve CTE/derived aliases by scope. A global CTE-name set can hide a
    # real table referenced inside a same-named, non-recursive CTE.
    physical_sources = [source for scope in traverse_scope(statement)
                        for source in scope.sources.values() if isinstance(source, exp.Table)]
    for table in physical_sources:
        if table.catalog or table.db not in ("", physical_schema or "main"):
            raise ValueError("SQL引用了不允许的schema或catalog限定来源")
    referenced = {table.name for table in physical_sources}
    unknown = {name for name in referenced if name not in allowed}
    if unknown:
        raise ValueError(f"SQL引用了未知数据表：{', '.join(sorted(unknown))}")
    if access_scope:
        denied = {
            table
            for table in referenced
            if not access_scope.allows_table(database, allowed[table])
        }
        if denied:
            raise ValueError("SQL引用了当前用户无权访问的数据表")
    return cleaned
