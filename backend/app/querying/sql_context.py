"""SQL consumers share the caller's runtime; this module opens no connections."""
from __future__ import annotations

from typing import Any

from ..database import SCHEMA
from ..datasources import DataSourceRuntime
from ..datasources.dialects import dialect_for_backend


def sql_reference_rules(source: dict[str, str]) -> str:
    dialect = dialect_for_backend(source["backend"])
    if (source["dialect"], source["prompt_dialect"]) != (dialect.parser, dialect.prompt):
        raise ValueError("SQL context backend/dialect mismatch")
    schema = source["physical_schema"]
    return (
        f"当前后端：{dialect.prompt}；SQL解析方言：{dialect.parser}；物理schema：{schema}。"
        f"表只允许使用未限定的表名，或 {schema}.表名；字段可使用表别名.字段名。"
        "业务数据库ID仅用于选择工具，不能作为SQL的schema或catalog限定名；"
        "只能引用当前runtime catalog及权限允许的表和字段。"
    )


class SqlContext:
    """Legacy standalone calls use DuckDB; injected runtimes never fall back."""

    def __init__(self, runtime: DataSourceRuntime | None = None) -> None:
        self.runtime = runtime
        self.require_open()

    def require_open(self, database: str | None = None) -> None:
        if self.runtime is None:
            return
        self.runtime.require_open()
        identity = self.runtime.identity
        dialect = dialect_for_backend(identity.backend)
        if (identity.dialect, identity.prompt_dialect) != (dialect.parser, dialect.prompt):
            raise ValueError("SQL context backend/dialect mismatch")
        if self.runtime.catalog.version != identity.catalog_version:
            raise ValueError("SQL context catalog version mismatch")
        if database is not None and database != identity.logical_database_id:
            raise ValueError("SQL context database does not match runtime")

    @property
    def dialect(self) -> str:
        self.require_open()
        return self.runtime.identity.dialect if self.runtime else "duckdb"

    def check_graph(self, graph: Any) -> None:
        self.require_open()
        source = graph.get("source_identity") if isinstance(graph, dict) else None
        if source is None:
            return
        if self.runtime:
            if source != self.runtime.identity.public():
                raise ValueError("SQL Schema graph datasource mismatch")
        elif source.get("backend") != "duckdb" or source.get("dialect") != "duckdb":
            raise ValueError("A PostgreSQL SQL context requires an explicit runtime")

    def tables(self, database: str | None = None) -> list[dict[str, Any]]:
        self.require_open(database)
        tables = self.runtime.catalog.tables if self.runtime else SCHEMA
        return [table for table in tables if database is None or
                table.get("database", "short_video_ops") == database]

    def public(self) -> dict[str, str]:
        self.require_open()
        if self.runtime:
            return self.runtime.identity.public()
        return {"backend": "duckdb", "dialect": "duckdb", "prompt_dialect": "DuckDB",
                "physical_schema": "main"}

    def instructions(self) -> str:
        source = self.public()
        text = sql_reference_rules(source)
        if source["backend"] == "postgresql":
            text += (
                "日期格式使用PostgreSQL的TO_CHAR或DATE_TRUNC，不使用STRFTIME；"
                "整数相除计算比率时显式转为numeric或乘1.0，再用NULLIF处理零分母；"
                "ROUND(value, precision)的整个第一个参数必须是numeric："
                "若表达式包含double precision列或目标值，先完成全部加减乘除，"
                "再把完整表达式转为numeric，然后调用ROUND；"
                "只转换分子、分母或子表达式不能保证最终类型。"
                "catalog 中标为 bigint 的真值字段使用 <> 0 与 = 0，不得和 TRUE/FALSE 比较。"
                "ORDER BY 可直接使用SELECT输出别名；若排序项是ABS等函数或算术表达式，"
                "须在其中重复原始计算表达式，不能在函数内部引用同层SELECT别名。"
            )
        return text
