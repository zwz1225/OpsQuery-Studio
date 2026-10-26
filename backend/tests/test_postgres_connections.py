"""Lifecycle/failure tests without network; real pool admission is checked on server."""
from contextlib import contextmanager
from dataclasses import replace
from importlib.util import find_spec
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app.config import settings
from app.datasources.postgres_config import PostgresConfig, PostgresConfigError
from app.datasources.postgres_connections import PostgresConnectionError, PostgresConnectionManager, safe_error

AVAILABLE = find_spec("psycopg") is not None and find_spec("psycopg_pool") is not None
if AVAILABLE:
    from psycopg.pq import TransactionStatus as S
    from psycopg_pool import PoolTimeout, TooManyRequests, PoolClosed


class DriverError(Exception):
    def __init__(self, state):
        self.sqlstate = state
        super().__init__("private-password private-host private-SQL")


class FakeConnection:
    @classmethod
    def connect(cls, *args, **kwargs):
        return cls()

    def __init__(self):
        self.pgconn = SimpleNamespace(transaction_status=S.IDLE)
        self.autocommit = True
        self.closed = False
        self.calls = []
        self.commits = self.rollbacks = 0
        self.reset_fails = self.rollback_fails = False
        self.row = ("askdata_m1_test", "askdata_readonly", 160015, "UTF8", "UTC", "on", "C", "C", "c",
                    True, False, False, False, False, False, False, False, True, False, False, "askdata_import")

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        if self.reset_fails and sql == "RESET ALL":
            raise DriverError("08006")
        return self

    def fetchone(self):
        return self.row

    def close(self):
        self.closed = True
        self.pgconn.transaction_status = S.UNKNOWN

    def rollback(self):
        if self.rollback_fails:
            raise DriverError("08006")
        self.rollbacks += 1
        self.pgconn.transaction_status = S.IDLE

    @contextmanager
    def transaction(self):
        self.pgconn.transaction_status = S.INTRANS
        try:
            yield self
        except BaseException:
            self.rollback()
            raise
        else:
            self.commits += 1
            self.pgconn.transaction_status = S.IDLE


class FakePool:
    def __init__(self, **kwargs):
        self.options = kwargs
        self.conn = FakeConnection()
        self.opens = self.closes = 0
        self.returned = []
        self.checkout_error = self.startup_error = None
        self.closed = False

    def open(self, **kwargs):
        self.opens += 1

    def wait(self, **kwargs):
        if self.startup_error:
            raise self.startup_error
        self.options["configure"](self.conn)

    def getconn(self, **kwargs):
        if self.checkout_error:
            raise self.checkout_error
        self.options["check"](self.conn)
        return self.conn

    def putconn(self, conn):
        self.returned.append(conn)
        if self.closed:
            conn.close()

    def close(self, **kwargs):
        self.closes += 1
        self.closed = True

    def get_stats(self):
        return {"pool_min": self.options["min_size"], "pool_max": self.options["max_size"]}


@unittest.skipUnless(AVAILABLE, "Optional pinned PostgreSQL dependencies not installed")
class PostgresConnectionTests(unittest.TestCase):
    def setUp(self):
        self.config = PostgresConfig.from_settings(replace(settings, pg_password="private-password", pg_host="private-host"))
        self.manager = PostgresConnectionManager(self.config, _pool_factory=FakePool)
        self.pool = self.manager._pool
        self.conn = self.pool.conn
        self.addCleanup(self.manager.close)

    def test_construction_does_not_open_connections(self):
        self.assertEqual(self.pool.opens, 0)
        self.assertFalse(self.pool.options["open"])
        self.assertEqual(self.manager.public_status()["state"], "new")

    def test_actual_installed_pool_constructor_is_compatible_and_lazy(self):
        manager = PostgresConnectionManager(self.config)
        self.addCleanup(manager.close)
        self.assertEqual(manager.public_status()["state"], "new")
        self.assertTrue(manager._pool.closed)

    def test_versions_must_match_pins(self):
        with patch("app.datasources.postgres_connections.version", return_value="99.0"):
            with self.assertRaisesRegex(PostgresConnectionError, "dependency_version_mismatch"):
                PostgresConnectionManager(self.config, _pool_factory=FakePool)

    def test_untrusted_dataclass_values_are_revalidated(self):
        for change in [{"user": "askdata_admin"}, {"pool_max_waiting": 0}, {"pool_min_size": 5}, {"schema": "other"}]:
            with self.subTest(change=change), self.assertRaises(PostgresConfigError):
                PostgresConnectionManager(replace(self.config, **change), _pool_factory=FakePool)

    def test_bounded_pool_and_secure_startup_defaults(self):
        options = self.pool.options
        self.assertEqual((options["min_size"], options["max_size"], options["timeout"], options["max_waiting"]), (1, 4, 10, 16))
        self.assertTrue(options["kwargs"]["autocommit"])
        self.assertIn("default_transaction_read_only=on", options["kwargs"]["options"])
        self.assertIn("search_path=pg_catalog,askdata_ops", options["kwargs"]["options"])

    def test_open_and_close_are_idempotent(self):
        self.manager.open().open()
        self.assertEqual(self.pool.opens, 1)
        self.manager.close()
        self.manager.close()
        self.assertEqual(self.pool.closes, 1)

    def test_use_before_open_is_rejected(self):
        with self.assertRaisesRegex(PostgresConnectionError, "manager_not_open"):
            with self.manager.transaction():
                pass

    def test_contaminated_connection_is_closed_during_checkout_check(self):
        self.conn.pgconn.transaction_status = S.INERROR
        with self.assertRaisesRegex(PostgresConnectionError, "connection_not_idle"):
            self.manager._check(self.conn)
        self.assertTrue(self.conn.closed)

    def test_reopen_and_checkout_after_close_are_rejected(self):
        self.manager.open()
        self.manager.close()
        with self.assertRaisesRegex(PostgresConnectionError, "manager_closed"):
            self.manager.open()
        with self.assertRaisesRegex(PostgresConnectionError, "manager_closed"):
            with self.manager.transaction():
                pass

    def test_startup_failure_closes_pool(self):
        self.pool.startup_error = PoolTimeout("private-host private-password")
        with self.assertRaisesRegex(PostgresConnectionError, "pool_wait_timeout"):
            self.manager.open()
        self.assertEqual(self.pool.closes, 1)

    def test_identity_mismatch_closes_connection_and_pool(self):
        self.conn.row = ("wrong",) + self.conn.row[1:]
        with self.assertRaisesRegex(PostgresConnectionError, "connection_identity_mismatch"):
            self.manager.open()
        self.assertTrue(self.conn.closed)
        self.assertEqual(self.pool.closes, 1)

    def test_login_checks_reject_role_flags_and_privileges(self):
        for index, bad in [(2, 150000), (3, "LATIN1"), (4, "local"), (5, "off"), (6, "en_US"),
                           (9, False), (10, True), (11, True), (12, True), (13, True), (14, True),
                           (15, True), (16, True), (17, False), (18, True), (19, True), (20, "other")]:
            conn = FakeConnection()
            row = list(conn.row)
            row[index] = bad
            conn.row = tuple(row)
            with self.subTest(index=index), self.assertRaises(PostgresConnectionError):
                self.manager._configure(conn)
            self.assertTrue(conn.closed)

    def test_each_operation_has_readonly_repeatable_read_and_local_settings(self):
        self.manager.open()
        with self.manager.transaction() as conn:
            self.assertEqual(self.manager.public_status()["active_operation_count"], 1)
            self.assertEqual(conn.pgconn.transaction_status, S.INTRANS)
        local = [p for q, p in self.conn.calls if q == "SELECT set_config(%s, %s, true)"]
        self.assertEqual(dict(local), {"search_path": "pg_catalog,askdata_ops", "TimeZone": "UTC",
            "DateStyle": "ISO, YMD", "extra_float_digits": "3", "statement_timeout": "120000", "lock_timeout": "5000"})
        self.assertIn(("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY", None), self.conn.calls)
        self.assertEqual(self.conn.commits, 1)
        self.assertEqual(self.conn.pgconn.transaction_status, S.IDLE)
        self.assertEqual(self.conn.calls[-2:], [("RESET ROLE", None), ("RESET ALL", None)])
        self.assertEqual(len(self.pool.returned), 1)

    def test_query_failure_rolls_back_and_redacts_driver_text(self):
        self.manager.open()
        with self.assertRaises(PostgresConnectionError) as caught:
            with self.manager.transaction():
                raise DriverError("42601")
        self.assertEqual(caught.exception.sqlstate, "42601")
        self.assertEqual(self.conn.rollbacks, 1)
        self.assertNotIn("private", str(caught.exception))
        with self.manager.transaction():
            pass
        self.assertEqual(self.conn.commits, 1)

    def test_timeout_rolls_back_and_connection_can_be_reused(self):
        self.manager.open()
        with self.assertRaisesRegex(PostgresConnectionError, "query_cancelled"):
            with self.manager.transaction():
                raise DriverError("57014")
        self.assertEqual(self.conn.pgconn.transaction_status, S.IDLE)
        with self.manager.transaction():
            pass

    def test_client_exception_also_rolls_back(self):
        self.manager.open()
        with self.assertRaisesRegex(PostgresConnectionError, "operation_failed"):
            with self.manager.transaction():
                raise ValueError("private-password")
        self.assertEqual(self.conn.rollbacks, 1)

    def test_swallowed_sql_error_does_not_report_success(self):
        self.manager.open()
        with self.assertRaisesRegex(PostgresConnectionError, "transaction_aborted"):
            with self.manager.transaction():
                self.conn.pgconn.transaction_status = S.INERROR
        self.assertEqual(self.conn.rollbacks, 1)
        self.assertEqual(self.conn.commits, 0)

    def test_caller_cannot_silently_end_transaction_boundary(self):
        self.manager.open()
        with self.assertRaisesRegex(PostgresConnectionError, "transaction_boundary_changed"):
            with self.manager.transaction():
                self.conn.pgconn.transaction_status = S.IDLE

    def test_interrupt_rolls_back_and_returns_connection(self):
        self.manager.open()
        with self.assertRaises(KeyboardInterrupt):
            with self.manager.transaction():
                raise KeyboardInterrupt()
        self.assertEqual(self.conn.rollbacks, 1)
        self.assertEqual(len(self.pool.returned), 1)

    def test_reset_failure_discards_connection(self):
        self.manager.open()
        self.conn.reset_fails = True
        with self.assertRaises(PostgresConnectionError):
            with self.manager.transaction():
                pass
        self.assertTrue(self.conn.closed)
        self.assertEqual(len(self.pool.returned), 1)
        self.assertEqual(self.manager.public_status()["active_operation_count"], 0)

    def test_cleanup_failure_does_not_mask_primary_error(self):
        self.manager.open()
        self.conn.reset_fails = True
        with self.assertRaises(PostgresConnectionError) as caught:
            with self.manager.transaction():
                raise DriverError("57014")
        self.assertEqual(caught.exception.category, "query_cancelled")
        self.assertTrue(self.conn.closed)

    def test_broken_connection_is_not_returned_as_healthy(self):
        self.manager.open()
        with self.assertRaises(PostgresConnectionError):
            with self.manager.transaction():
                self.conn.close()
                raise DriverError("08006")
        self.assertTrue(self.pool.returned[0].closed)

    def test_rollback_failure_discards_connection(self):
        self.manager.open()
        self.conn.rollback_fails = True
        with self.assertRaises(PostgresConnectionError) as caught:
            with self.manager.transaction():
                raise DriverError("57014")
        self.assertTrue(self.conn.closed)
        self.assertEqual(caught.exception.category, "query_cancelled")

    def test_real_pool_enforces_capacity_queue_limit_and_timeout(self):
        # The real installed pool and worker threads, with an in-memory wire
        # stand-in. PostgreSQL SQL semantics remain a server acceptance gate.
        from psycopg_pool import ConnectionPool
        from scripts.check_m1_c2_postgres_connections import queue_probes

        def factory(**kwargs):
            kwargs["connection_class"] = FakeConnection
            return ConnectionPool(**kwargs)

        config = replace(self.config, pool_min_size=1, pool_max_size=1,
                         pool_max_waiting=1, pool_wait_timeout_seconds=2)
        manager = PostgresConnectionManager(config, _pool_factory=factory)
        with manager:
            # scalar() expects SELECT 1; identity callback needs full tuple.
            old_execute = FakeConnection.execute
            def execute(conn, sql, params=None):
                result = old_execute(conn, sql, params)
                conn.row = (1,) if sql == "SELECT 1" else conn.row
                return result
            with patch.object(FakeConnection, "execute", execute):
                result = queue_probes(manager)
            self.assertEqual(result["waiting_timeout"], "pool_wait_timeout")
            self.assertEqual(result["queue_full"]["category"], "pool_queue_full")

    def test_driver_connect_errors_and_connection_repr_are_redacted(self):
        import psycopg
        connection_class = self.pool.options["connection_class"]
        with patch.object(psycopg.Connection, "connect", side_effect=DriverError("08006")):
            with self.assertRaises(PostgresConnectionError) as caught:
                connection_class.connect(password="private-password", host="private-host")
        self.assertNotIn("private", str(caught.exception))
        self.assertEqual(connection_class.__repr__(SimpleNamespace(closed=False)),
                         "<AskDataPostgresConnection closed=False>")

    def test_diagnostic_unexpected_write_success_is_rolled_back(self):
        from scripts.check_m1_c2_postgres_connections import expected_failure
        self.manager.open()
        with self.assertRaisesRegex(PostgresConnectionError, "probe_failed_expected_sqlstate"):
            expected_failure(self.manager, "CREATE TABLE diagnostic_only (id integer)", {"25006", "42501"})
        self.assertEqual(self.conn.rollbacks, 1)
        self.assertEqual(self.conn.commits, 0)

    def test_checkout_failures_are_distinct_and_redacted(self):
        self.manager.open()
        for error, category in [(PoolTimeout("private-password"), "pool_wait_timeout"),
                                (TooManyRequests("private-host"), "pool_queue_full"),
                                (PoolClosed("private-host"), "manager_closed")]:
            self.pool.checkout_error = error
            with self.assertRaises(PostgresConnectionError) as caught:
                with self.manager.transaction():
                    pass
            self.assertEqual(caught.exception.category, category)
            self.assertNotIn("private", str(caught.exception))

    def test_close_during_lease_closes_returned_connection(self):
        self.manager.open()
        with self.manager.transaction():
            self.manager.close()
            self.assertFalse(self.conn.closed)
        self.assertTrue(self.conn.closed)
        self.assertEqual(self.pool.closes, 1)

    def test_context_owner_closes_on_exception(self):
        with self.assertRaises(ValueError):
            with self.manager:
                raise ValueError("caller")
        self.assertEqual(self.pool.closes, 1)

    def test_public_status_contains_no_connection_secrets(self):
        self.manager.open()
        serialized = json.dumps(self.manager.public_status())
        self.assertNotIn("private-password", serialized)
        self.assertNotIn("private-host", serialized)
        self.assertFalse(self.manager.public_status()["live_target_verified"])


class SafeErrorTests(unittest.TestCase):
    def test_sqlstate_is_validated_and_text_is_removed(self):
        self.assertEqual(safe_error(DriverError("42501")).category, "permission_denied")
        self.assertEqual(safe_error(DriverError("25006")).category, "read_only_violation")
        self.assertIsNone(safe_error(DriverError("private-password")).sqlstate)
        self.assertNotIn("private", str(safe_error(DriverError("private-password"))))


if __name__ == "__main__":
    unittest.main()
