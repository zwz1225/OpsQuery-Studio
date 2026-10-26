"""PostgreSQL adapter with the existing bounded SqlExecution contract."""
from math import isfinite
from time import perf_counter
from uuid import uuid4
from sqlglot.errors import ParseError

from ..datasources.postgres_connections import PostgresConnectionError
from ..datasources.sql_policy import validate_readonly_sql
from ..datasources.values import json_value
from .models import SqlExecution


def postgres_json_value(value):
    value = json_value(value)
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("PostgreSQL结果包含无法表示的非有限数值")
    return value


class PostgresEngine:
    def __init__(self, metadata):
        self.metadata = metadata
        self.catalog = metadata.load_catalog()
        self.source_identity = metadata.identity
        self.connections = metadata.connections
        self._closed = False
        if self.source_identity is None or self.source_identity.catalog_version != self.catalog.version:
            raise ValueError("PostgreSQL executor requires verified metadata/catalog")

    def require_open(self):
        if self._closed:
            raise ValueError("Datasource executor is closed")
        self.connections.require_open()
        if self.catalog != self.metadata.load_catalog() or self.source_identity != self.metadata.identity:
            raise ValueError("PostgreSQL executor/catalog identity changed")

    def close(self):
        self.connections.close()
        self._closed = True

    def execute(self, database, sql, access_scope=None, *, row_limit=200):
        start = perf_counter()
        try:
            self.require_open()
            if database != self.source_identity.logical_database_id:
                raise ValueError("Database does not belong to the datasource runtime")
            if isinstance(row_limit, bool) or not isinstance(row_limit, int) or not 1 <= row_limit <= 10000:
                raise ValueError("查询行数上限必须在1到10000之间")
            safe_sql = validate_readonly_sql(database, sql, self.catalog.tables, access_scope,
                dialect="postgres", physical_schema=self.source_identity.physical_schema)
            with self.metadata.verified_transaction() as conn:
                # A named cursor prevents client-side buffering of the whole
                # result before fetching the preview/scoring row limit.
                with conn.cursor(name="askdata_query_" + uuid4().hex) as cursor:
                    cursor.execute(safe_sql)
                    raw = cursor.fetchmany(row_limit + 1)
                    columns = [item.name for item in cursor.description or []]
                    if len(set(columns)) != len(columns):
                        raise ValueError("查询结果列名重复，请使用明确且唯一的别名")
                    rows = [{c: postgres_json_value(v) for c, v in zip(columns, row)} for row in raw[:row_limit]]
            return SqlExecution(safe_sql, True, columns, rows,
                execution_ms=round((perf_counter()-start)*1000, 3), truncated=len(raw) > row_limit)
        except (ValueError, ParseError, PostgresConnectionError) as error:
            if isinstance(error, PostgresConnectionError):
                message = "PostgreSQL " + ("permission denied" if error.category == "permission_denied" else error.category)
                if error.sqlstate:
                    message += " (SQLSTATE " + error.sqlstate + ")"
            elif isinstance(error, ParseError):
                message = "PostgreSQL SQL解析失败"
            else:
                message = str(error)
            return SqlExecution(sql, False, error=message, execution_ms=round((perf_counter()-start)*1000, 3))
