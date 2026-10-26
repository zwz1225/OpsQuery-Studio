from __future__ import annotations

import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import duckdb
from sqlglot.errors import ParseError

from ..config import BASE_DIR
from ..database import SCHEMA, physical_table_name
from ..datasources.contracts import CatalogSnapshot, SourceIdentity
from ..datasources.sql_policy import clean_sql, validate_readonly_sql
from ..datasources.values import json_value
from ..security import AccessScope
from .models import SqlExecution


DATABASE_ROOT = BASE_DIR / "data" / "databases"


class DuckDbEngine:
    """将 CSV 目录映射为只读 DuckDB 数据库。

    CSV 文件名作为 SQL 表名使用。
    """

    def __init__(self, database_root: Path | None = None, *, catalog: CatalogSnapshot | None = None,
                 source_identity: SourceIdentity | None = None) -> None:
        self.database_root = database_root or DATABASE_ROOT
        self.catalog = catalog
        self.source_identity = source_identity
        self._closed = False

    def bind_source(self, catalog: CatalogSnapshot, identity: SourceIdentity) -> None:
        if self._closed or self.source_identity not in (None, identity):
            raise ValueError("Cannot bind closed/different datasource executor")
        self.catalog = catalog
        self.source_identity = identity

    def require_open(self) -> None:
        if self._closed:
            raise ValueError("Datasource executor is closed")
        if self.source_identity and (self.catalog is None or self.catalog.version != self.source_identity.catalog_version):
            raise ValueError("Datasource executor catalog changed")

    def close(self) -> None:
        # Each query owns a temporary connection; no persistent pool to dispose.
        self._closed = True

    def execute(
        self,
        database: str,
        sql: str,
        access_scope: AccessScope | None = None,
        *,
        row_limit: int = 200,
    ) -> SqlExecution:
        started_at = time.perf_counter()
        try:
            self.require_open()
            if not 1 <= row_limit <= 10000:
                raise ValueError("查询行数上限必须在1到10000之间")
            safe_sql = self._validate_sql(database, sql, access_scope)
            with self.connect(database) as connection:
                cursor = connection.execute(safe_sql)
                raw_rows = cursor.fetchmany(row_limit + 1)
                columns = [item[0] for item in cursor.description or []]
                rows = [
                    {column: self._json_value(value) for column, value in zip(columns, row)}
                    for row in raw_rows[:row_limit]
                ]
            return SqlExecution(
                safe_sql,
                True,
                columns,
                rows,
                execution_ms=round((time.perf_counter() - started_at) * 1000, 3),
                truncated=len(raw_rows) > row_limit,
            )
        except (ValueError, ParseError, duckdb.Error, OSError) as exc:
            return SqlExecution(
                sql,
                False,
                error=str(exc),
                execution_ms=round((time.perf_counter() - started_at) * 1000, 3),
            )

    @contextmanager
    def connect(self, database: str) -> Iterator[duckdb.DuckDBPyConnection]:
        """创建内存连接并将 CSV 文件注册为只读视图。"""
        self.require_open()
        if self.source_identity and database != self.source_identity.logical_database_id:
            raise ValueError("Database does not belong to the datasource runtime")
        folder = self._database_folder(database)
        connection = duckdb.connect(":memory:")
        try:
            csv_files = (sorted(folder / f"{physical_table_name(table)}.csv" for table in self.catalog.tables)
                         if self.catalog else sorted(folder.glob("*.csv")))
            if not csv_files:
                raise ValueError(f"数据库文件夹没有CSV表：{folder}")
            for csv_path in csv_files:
                table = csv_path.stem
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
                    raise ValueError(f"CSV文件名不能作为安全表名：{csv_path.name}")
                path = csv_path.resolve().as_posix().replace("'", "''")
                connection.execute(
                    f'CREATE VIEW "{table}" AS '
                    f"SELECT * FROM read_csv_auto('{path}', header=true, sample_size=-1)"
                )
            yield connection
        finally:
            connection.close()

    def _validate_sql(
        self,
        database: str,
        sql: str,
        access_scope: AccessScope | None = None,
    ) -> str:
        return validate_readonly_sql(database, sql, self.catalog.tables if self.catalog else SCHEMA,
                                     access_scope, dialect="duckdb")

    def _database_folder(self, database: str) -> Path:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", database):
            raise ValueError("数据库名称不合法")
        folder = (self.database_root / database).resolve()
        root = self.database_root.resolve()
        if root not in folder.parents or not folder.is_dir():
            raise ValueError(f"本地CSV数据库不存在：{database}")
        return folder

    clean_sql = staticmethod(clean_sql)
    _json_value = staticmethod(json_value)
