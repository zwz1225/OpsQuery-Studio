from __future__ import annotations

from typing import Annotated, Callable

from pydantic import Field

from ...datasources.contracts import ReadOnlyExecutor
from ...datasources import DataSourceRuntime
from ...querying.sql_context import SqlContext
from ...security import AccessScope
from ..schemas import DatabaseQueryResult


SqlStatement = Annotated[
    str,
    Field(
        description=(
            "需要执行的一条符合当前数据库方言的 SELECT或WITH只读SQL。"
            "只能引用当前工具对应数据库中的表，最多返回200行。"
        ),
        min_length=8,
        max_length=12000,
    ),
]


def build_database_query_tool(
    database: str,
    engine: ReadOnlyExecutor,
    access_scope: AccessScope,
    *, dialect: str = "DuckDB",
    runtime: DataSourceRuntime | None = None,
) -> Callable[[SqlStatement], DatabaseQueryResult]:
    """为一个数据库创建一个独立的MCP查询工具。"""
    if runtime:
        runtime.assert_executor(engine)
        context = SqlContext(runtime)
        context.require_open(database)
        dialect = runtime.identity.prompt_dialect
        reference_rules = context.instructions()
    else:
        reference_rules = "仅引用当前工具对应的受控表。"

    def query_database(sql: SqlStatement) -> DatabaseQueryResult:
        # 工具处理器再次执行数据库、表和固定SQL规则校验。
        execution = engine.execute(database, sql, access_scope)
        return DatabaseQueryResult(
            database=database,
            sql=execution.sql,
            success=execution.success,
            columns=execution.columns,
            rows=execution.rows,
            row_count=len(execution.rows),
            truncated=execution.truncated,
            execution_ms=execution.execution_ms,
            error=execution.error,
        )

    query_database.__annotations__["sql"] = Annotated[
        str, Field(description=f"一条{dialect} SELECT或WITH只读SQL；最多200行。{reference_rules}",
                   min_length=8, max_length=12000)]
    query_database.__name__ = f"query_{database}"
    return query_database
