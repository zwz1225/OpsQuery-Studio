from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.config import settings
from app.datasources.contracts import CatalogSnapshot, SourceIdentity
from app.datasources.postgres_config import digest
from app.datasources.postgres_connections import PostgresConnectionError
from app.datasources.postgres_metadata import PostgresMetadataProvider, SOURCE_TYPES
from app.datasources.row_digest import typed_row_hash, multiset_hash
from app.datasources.runtime import create_datasource_runtime, DataSourceRuntime
from app.querying.postgres_engine import PostgresEngine, postgres_json_value
from app.security import AccessScope


FIELDS = [{"name": "id", "postgresql_type": "bigint", "not_null": True, "identity": "", "generated": "", "has_default": False},
          {"name": "value", "postgresql_type": "text", "not_null": False, "identity": "", "generated": "", "has_default": False}]
ROWS = [(1, "a"), (2, None)]
TARGET = {"test_target": "source"}
TABLE = {"name": "t", "columns": FIELDS, "primary_key": ["id"], "row_count": 2,
         "typed_row_multiset_sha256": multiset_hash([typed_row_hash(r, [{"source_type": "BIGINT"}, {"source_type": "VARCHAR"}]) for r in ROWS])}
PHYSICAL = [{k: TABLE[k] for k in ["name", "columns", "primary_key"]}]
VERSION = digest({"target": TARGET, "tables": [TABLE]})
ANNOTATIONS = CatalogSnapshot(json.dumps({"tables": [{"id": "short_video_ops.t", "name": "t", "database": "short_video_ops",
    "primary_key": ["id"], "fields": [{"name": "id", "source_type": "BIGINT"}, {"name": "value", "source_type": "VARCHAR"}]}], "relations": []}, sort_keys=True))


class Cursor:
    def __init__(self, rows=ROWS, columns=("id", "value")):
        self.rows = list(rows)
        self.description = [SimpleNamespace(name=c) for c in columns]
        self.fetches = []
        self.closed = False
    def execute(self, sql):
        self.sql = sql
    def fetchmany(self, count):
        self.fetches.append(count)
        result, self.rows = self.rows[:count], self.rows[count:]
        return result
    def __enter__(self): return self
    def __exit__(self, *args): self.closed = True


class WireConnection:
    """SQL-dispatch fixture; exercises all validation branches without a DB."""
    def __init__(self):
        self.calls = []
        self.overrides = {}
        self.rows = list(ROWS)
        self.cursors = []
        self.result = None
    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        key = None
        if "c.relname,c.relkind" in sql: key, result = "objects", [("t", "r", "askdata_import", False, False, "p", False)]
        elif "SELECT EXISTS" in sql: key, result = "unsupported", (False,)
        elif "SELECT current_database(),current_user" in sql:
            key, result = "identity", ("askdata_m1_test", "askdata_readonly", 160015, "UTF8", "UTC", "C", "C", "c", True, False, False, False, False, False, False, "askdata_import")
        elif "has_database_privilege" in sql: key, result = "schema_acl", (True, False, False, True, False, False)
        elif "a.attidentity" in sql:
            key, result = "columns", [tuple(c.values()) + (("default", "pg_catalog") if c["postgresql_type"] == "text" else (None, None)) for c in FIELDS]
        elif "WITH ORDINALITY" in sql: key, result = "pk", [("id",)]
        elif "k.contype::text" in sql: key, result = "constraints", [("p", True, False, False)]
        elif "i.indisprimary" in sql: key, result = "indexes", [(True, True, True, True)]
        elif "has_any_column_privilege" in sql: key, result = "column_acl", (False, False, False)
        elif "has_table_privilege" in sql: key, result = "table_acl", (True, False, False, False, False, False, False)
        elif "string_agg(h" in sql:
            key, result = "guard", (len(self.rows), hashlib.sha256(repr(self.rows).encode()).hexdigest())
        elif "SELECT COUNT(*) FROM" in sql: key, result = "count", (len(self.rows),)
        elif "pg_current_snapshot" in sql: key, result = "snapshot", ("12:13:",)
        elif "SELECT DISTINCT" in sql: key, result = "samples", [("a",)]
        elif "COUNT(DISTINCT" in sql: key, result = "distinct", (1,)
        elif "MIN(" in sql: key, result = "numeric_profile", (1, 2, Decimal("1.5"))
        else: key, result = "lock", None
        self.result = self.overrides.get(key, result)
        return self
    def fetchone(self): return self.result
    def fetchall(self): return self.result
    def fetchmany(self, n): return self.result[:n]
    def cursor(self, **kwargs):
        cursor = Cursor(self.rows)
        self.cursors.append(cursor)
        return cursor


class Connections:
    def __init__(self):
        self.config = SimpleNamespace(schema="askdata_ops", database="askdata_m1_test", user="askdata_readonly",
                                     source_id="short_video_ops_postgres", verified_data_version=VERSION)
        self.conn = WireConnection()
        self.closed = False
        self.borrows = 0
        self.completed = 0
    def require_open(self):
        if self.closed: raise PostgresConnectionError("manager_closed")
    @contextmanager
    def transaction(self):
        self.require_open()
        self.borrows += 1
        yield self.conn
        self.completed += 1
    def close(self): self.closed = True


class PostgresMetadataTests(unittest.TestCase):
    def setUp(self):
        self.connections = Connections()
        self.provider = PostgresMetadataProvider(self.connections, [TABLE], ANNOTATIONS, TARGET, digest(PHYSICAL))
    def test_verify_matches_typed_version_and_assembles_actual_types(self):
        self.provider.verify()
        field = self.provider.load_catalog().tables[0]["fields"][1]
        self.assertEqual(field["postgresql_type"], "text")
        self.assertTrue(field["nullable"])
        self.assertEqual(self.provider.identity.data_version, VERSION)
        self.assertEqual(self.provider.identity.catalog_version, self.provider.load_catalog().version)
        self.assertNotEqual(self.provider.load_catalog().version, ANNOTATIONS.version)
        self.assertTrue(self.connections.conn.cursors[0].closed)
        self.assertTrue(all(n == 4096 for n in self.connections.conn.cursors[0].fetches))
    def test_no_catalog_or_identity_is_published_before_verification(self):
        with self.assertRaisesRegex(PostgresConnectionError, "not_verified"): self.provider.load_catalog()
        self.assertIsNone(self.provider.identity)
    def test_metadata_and_acl_drift_are_rejected(self):
        cases = {"objects": [("t", "v", "askdata_import", False, False, "p", False)],
            "unsupported": (True,), "identity": ("wrong",), "schema_acl": (True, True, False, True, False, False),
            "columns": [], "pk": [("value",)], "constraints": [("c", True, False, False)],
            "indexes": [(False, True, True, True)], "table_acl": (True, True, False, False, False, False, False),
            "column_acl": (False, True, False)}
        for key, value in cases.items():
            with self.subTest(key=key):
                self.connections.conn.overrides = {key: value}
                with self.assertRaises(PostgresConnectionError): self.provider.verify()
                self.assertIsNone(self.provider.identity)
                self.assertIsNone(self.provider._catalog)
    def test_same_count_changed_values_fail_initial_typed_hash(self):
        self.connections.conn.rows = [(1, "changed"), (2, None)]
        with self.assertRaisesRegex(PostgresConnectionError, "typed_data_changed"): self.provider.verify()
    def test_extra_rows_abort_bounded_initial_read(self):
        self.connections.conn.rows += [(3, "extra")]
        with self.assertRaisesRegex(PostgresConnectionError, "row_count_changed"): self.provider.verify()
    def test_runtime_read_rechecks_content_with_same_count(self):
        self.provider.verify()
        self.connections.conn.rows = [(1, "changed"), (2, None)]
        with self.assertRaisesRegex(PostgresConnectionError, "content_changed"):
            with self.provider.verified_transaction(): self.fail("Must not yield a changed source")
    def test_runtime_read_rechecks_column_permissions(self):
        self.provider.verify()
        self.connections.conn.overrides["column_acl"] = (False, True, False)
        with self.assertRaisesRegex(PostgresConnectionError, "column_acl_changed"):
            with self.provider.verified_transaction(): self.fail("Must not yield broader permissions")
    def test_metadata_reads_are_schema_scoped_and_identifiers_quoted(self):
        self.provider.verify()
        for sql, params in self.connections.conn.calls:
            if "pg_namespace n" in sql:
                self.assertIn("n.nspname=%s", sql)
                self.assertIn("askdata_ops", params)
        self.assertIn('"askdata_ops"."t"', self.connections.conn.calls[0][0])
    def test_invalid_profile_names_fail_before_borrow(self):
        self.provider.verify()
        before = self.connections.borrows
        for table, fields in [("other.t", ["id"]), ("short_video_ops.t", ["id;DROP"] )]:
            with self.assertRaises(PostgresConnectionError): self.provider.profile_table(table, fields)
        self.assertEqual(before, self.connections.borrows)
    def test_profiles_share_verified_transaction_and_typed_samples(self):
        self.provider.verify()
        profile = self.provider.profile_table("short_video_ops.t", ["value"])
        self.assertEqual(profile["value"]["sample_values"], ["a"])
        self.assertIn("1", profile["value"]["profile_text"])
    def test_numeric_profiles_preserve_average_and_numeric_samples(self):
        self.provider.verify()
        self.connections.conn.overrides["samples"] = [(1,), (2,)]
        profile = self.provider.profile_table("short_video_ops.t", ["id"])
        self.assertEqual(profile["id"]["sample_values"], [1, 2])
        self.assertIn("1.50", profile["id"]["profile_text"])
    def test_broken_annotation_relations_fail_without_publishing(self):
        payload = json.loads(ANNOTATIONS.content)
        payload["relations"] = [{"left_table": "short_video_ops.t", "left_field": "bad", "right_table": "short_video_ops.t", "right_field": "id"}]
        self.provider._annotations = CatalogSnapshot(json.dumps(payload))
        with self.assertRaisesRegex(PostgresConnectionError, "relation_endpoint_changed"): self.provider.verify()
    def test_original_row_digest_format_matches_frozen_m1_b(self):
        fields = [{"source_type": "TIMESTAMP"}, {"source_type": "DOUBLE"}, {"source_type": "VARCHAR"}]
        values = [datetime(2026, 1, 1, microsecond=123400), -0.0, None]
        expected = hashlib.sha256(json.dumps([["TIMESTAMP", "2026-01-01 00:00:00.123400"], ["DOUBLE", "-0x0.0p+0"], ["VARCHAR", None]], separators=(",", ":")).encode()).digest()
        self.assertEqual(typed_row_hash(values, fields), expected)


class PostgresExecutorTests(unittest.TestCase):
    def setUp(self):
        self.connections = Connections()
        self.metadata = PostgresMetadataProvider(self.connections, [TABLE], ANNOTATIONS, TARGET, digest(PHYSICAL)).verify()
        self.engine = PostgresEngine(self.metadata)
        self.scope = AccessScope("test", ("role",), frozenset({"short_video_ops"}), frozenset({"short_video_ops.t"}))
    def test_success_empty_result_and_unique_columns_contract(self):
        result = self.engine.execute("short_video_ops", "SELECT id,value FROM askdata_ops.t", self.scope)
        self.assertTrue(result.success, result.error)
        self.assertEqual(result.rows, [{"id": 1, "value": "a"}, {"id": 2, "value": None}])
        self.connections.conn.rows = []
        with patch.object(self.metadata, "_content_guards", return_value=self.metadata._guards):
            empty = self.engine.execute("short_video_ops", "SELECT id FROM t WHERE FALSE", self.scope)
        self.assertTrue(empty.success, empty.error)
        self.assertEqual(empty.rows, [])
        self.assertFalse(empty.truncated)
    def test_named_cursor_fetches_only_limit_plus_one(self):
        self.connections.conn.rows = [(i, str(i)) for i in range(202)]
        with patch.object(self.metadata, "_content_guards", return_value=self.metadata._guards):
            result = self.engine.execute("short_video_ops", "SELECT id,value FROM t", self.scope, row_limit=200)
        self.assertTrue(result.success, result.error)
        self.assertTrue(result.truncated)
        self.assertEqual(len(result.rows), 200)
        self.assertEqual(self.connections.conn.cursors[-1].fetches, [201])
        self.assertTrue(self.connections.conn.cursors[-1].closed)
    def test_scoring_limit_10000_is_bounded(self):
        self.connections.conn.rows = [(i, str(i)) for i in range(10002)]
        with patch.object(self.metadata, "_content_guards", return_value=self.metadata._guards):
            result = self.engine.execute("short_video_ops", "SELECT id,value FROM t", self.scope, row_limit=10000)
        self.assertTrue(result.success, result.error)
        self.assertEqual(len(result.rows), 10000)
        self.assertEqual(self.connections.conn.cursors[-1].fetches, [10001])
    def test_unsafe_queries_fail_before_checkout(self):
        bad = ["SELECT * FROM t", "SELECT id FROM public.t", "SELECT id FROM main.t", "SELECT id FROM db.askdata_ops.t",
            "SELECT id FROM pg_catalog.pg_class", "SELECT id FROM unknown", "DELETE FROM t", "SELECT id INTO x FROM t",
            "SELECT id FROM t FOR UPDATE", "SELECT pg_sleep(0)", "SELECT pg_catalog.pg_sleep(0)", "SELECT set_config('TimeZone','UTC',false)",
            "SELECT pg_read_file('private')", "SELECT nextval('seq')", "SELECT 1::regclass", "SELECT 1;SELECT 2",
            "WITH x AS (DELETE FROM t RETURNING id) SELECT id FROM x"]
        before = self.connections.borrows
        denied = AccessScope("unknown", (), frozenset(), frozenset())
        for sql in bad:
            with self.subTest(sql=sql): self.assertFalse(self.engine.execute("short_video_ops", sql, self.scope).success)
        self.assertFalse(self.engine.execute("other", "SELECT 1", self.scope).success)
        self.assertFalse(self.engine.execute("short_video_ops", "SELECT id FROM t", denied).success)
        self.assertEqual(before, self.connections.borrows)
    def test_legal_analytical_functions_and_cte_pass_policy(self):
        queries = ["SELECT count(*) AS n FROM t", "SELECT round(avg(id),2) AS n FROM t",
            "WITH x AS (SELECT id FROM t) SELECT id FROM x", "WITH t AS (SELECT id FROM t) SELECT id FROM t",
            "SELECT to_char(CURRENT_DATE,'YYYY-MM') AS month FROM t",
            "SELECT date_trunc('month',CURRENT_TIMESTAMP) AS month FROM t",
            "SELECT CASE WHEN id=1 THEN 'a' ELSE 'b' END AS segment FROM t"]
        for sql in queries:
            with self.subTest(sql=sql):
                result = self.engine.execute("short_video_ops", sql, self.scope)
                self.assertTrue(result.success, result.error)
    def test_source_drift_is_failure_not_empty_success(self):
        self.connections.conn.rows = [(1, "changed"), (2, None)]
        result = self.engine.execute("short_video_ops", "SELECT id FROM t", self.scope)
        self.assertFalse(result.success)
        self.assertIn("source_content_changed", result.error)
        self.assertEqual(result.rows, [])
    def test_sql_failure_is_redacted_and_next_query_works(self):
        @contextmanager
        def failed(): raise PostgresConnectionError("query_error", "22012"); yield
        with patch.object(self.metadata, "verified_transaction", failed):
            result = self.engine.execute("short_video_ops", "SELECT 1/0", self.scope)
        self.assertFalse(result.success)
        self.assertIn("22012", result.error)
        self.assertTrue(self.engine.execute("short_video_ops", "SELECT id FROM t", self.scope).success)
    def test_close_is_owned_by_executor_and_prevents_profile_and_query(self):
        runtime = DataSourceRuntime(self.metadata.identity, self.metadata.load_catalog(), self.engine, self.metadata)
        runtime.close(); runtime.close()
        self.assertTrue(self.connections.closed)
        self.assertFalse(self.engine.execute("short_video_ops", "SELECT id FROM t", self.scope).success)
        with self.assertRaises(PostgresConnectionError): self.metadata.profile_table("short_video_ops.t", ["id"])
    def test_typed_json_values_and_nonfinite_values(self):
        self.assertEqual(postgres_json_value(date(2026,1,1)), "2026-01-01")
        self.assertEqual(postgres_json_value(Decimal("1.25")), 1.25)
        self.assertIsNone(postgres_json_value(None))
        for value in [float('nan'), float('inf'), Decimal('Infinity')]:
            with self.assertRaises(ValueError): postgres_json_value(value)
    def test_invalid_row_limits_never_borrow(self):
        before = self.connections.borrows
        for limit in [True, 0, 10001, 1.5, "200"]:
            self.assertFalse(self.engine.execute("short_video_ops", "SELECT id FROM t", self.scope, row_limit=limit).success)
        self.assertEqual(before, self.connections.borrows)
    def test_duplicate_column_labels_are_a_failure(self):
        with patch.object(self.connections.conn, "cursor", return_value=Cursor(columns=("id", "id"))):
            result = self.engine.execute("short_video_ops", "SELECT id,id FROM t", self.scope)
        self.assertFalse(result.success)
        self.assertEqual(result.rows, [])
        self.assertIn("列名重复", result.error)


class PostgresAssemblyTests(unittest.TestCase):
    def test_wrong_source_rejected_before_connecting(self):
        with patch("app.datasources.postgres_connections.PostgresConnectionManager") as manager:
            with self.assertRaisesRegex(ValueError, "DATA_SOURCE_ID"):
                create_datasource_runtime(replace(settings, data_backend="postgresql", data_source_id="short_video_ops_duckdb"))
            manager.assert_not_called()
    def test_failed_verification_closes_owned_pool_without_duckdb_fallback(self):
        config = replace(settings, data_backend="postgresql", data_source_id="short_video_ops_postgres", pg_password="test-only")
        with patch("app.datasources.postgres_connections.PostgresConnectionManager") as manager, patch.object(PostgresMetadataProvider, "from_recorded_source") as provider:
            provider.return_value.verify.side_effect = PostgresConnectionError("source_typed_data_changed")
            with self.assertRaises(PostgresConnectionError): create_datasource_runtime(config)
            manager.return_value.close.assert_called_once()


if __name__ == '__main__': unittest.main()
