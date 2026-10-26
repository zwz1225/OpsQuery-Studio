"""Bounded PostgreSQL connections for future executor and metadata borrowers.

Import and construction do not connect. The owner opens/closes this manager;
borrowers use transaction(), never own or retain a connection themselves.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import fields
from importlib.metadata import version, PackageNotFoundError
import re
from threading import RLock
from types import SimpleNamespace
from typing import Any, Iterator
from uuid import uuid4

from .postgres_config import PostgresConfig

DEPENDENCIES = {"psycopg": "3.2.13", "psycopg-pool": "3.2.8"}


class PostgresConnectionError(RuntimeError):
    """Deliberately excludes driver text, connection strings and SQL text."""

    def __init__(self, category: str, sqlstate: str | None = None):
        self.category = category
        self.sqlstate = sqlstate if isinstance(sqlstate, str) and re.fullmatch(r"[A-Z0-9]{5}", sqlstate) else None
        super().__init__("PostgreSQL operation failed: " + category)

    def public(self) -> dict[str, Any]:
        return {"category": self.category, "sqlstate": self.sqlstate, "message": str(self)}


def safe_error(error: Exception) -> PostgresConnectionError:
    if isinstance(error, PostgresConnectionError):
        return error
    state = getattr(error, "sqlstate", None)
    name = type(error).__name__
    category = {"PoolTimeout": "pool_wait_timeout", "TooManyRequests": "pool_queue_full",
                "PoolClosed": "manager_closed"}.get(name)
    if category is None:
        category = {"57014": "query_cancelled", "25006": "read_only_violation",
                    "42501": "permission_denied", "25P02": "transaction_aborted",
                    "55P03": "lock_timeout", "28P01": "authentication_failed",
                    "28000": "authentication_failed", "3D000": "target_not_found",
                    "53100": "disk_full"}.get(state)
    if category is None:
        if name in {"OperationalError", "InterfaceError"} or (isinstance(state, str) and state.startswith("08")):
            category = "connection_failed"
        else:
            category = "query_error" if state else "operation_failed"
    return PostgresConnectionError(category, state)


class PostgresConnectionManager:
    """One owner, many synchronous borrowers; closed managers cannot reopen.

    close() stops admission and waiting borrowers. Checked-out connections are
    closed on return, so the owner must drain operations before process exit.
    This layer provides connections, not the application SQL policy boundary.
    """

    def __init__(self, config: PostgresConfig, *, _pool_factory=None):
        # Revalidate even configs created/replaced directly by another caller.
        values = {"pg_" + f.name: getattr(config, f.name) for f in fields(config)}
        self.config = PostgresConfig.from_settings(SimpleNamespace(**values))
        try:
            for package, expected in DEPENDENCIES.items():
                if version(package) != expected:
                    raise PostgresConnectionError("dependency_version_mismatch")
            import psycopg
            from psycopg.pq import TransactionStatus
            from psycopg_pool import ConnectionPool
        except (ImportError, PackageNotFoundError):
            raise PostgresConnectionError("dependency_missing") from None
        self._status = TransactionStatus
        self._lock = RLock()
        self._close_lock = RLock()
        self._state = "new"
        self._active = 0
        self._close_complete = False
        self._connect_error = None
        self._identity = None
        manager = self

        class RedactedConnection(psycopg.Connection):
            @classmethod
            def connect(cls, *args, **kwargs):
                try:
                    return super().connect(*args, **kwargs)
                except Exception as error:
                    fault = safe_error(error)
                    with manager._lock:
                        manager._connect_error = fault
                    raise fault from None

            def __repr__(self):
                # psycopg_pool includes connection repr in some warning logs.
                return "<AskDataPostgresConnection closed=" + str(self.closed) + ">"

        c = self.config
        options = ("-c default_transaction_read_only=on -c search_path=pg_catalog," + c.schema
                   + " -c TimeZone=UTC -c statement_timeout=" + str(c.statement_timeout_ms)
                   + " -c lock_timeout=" + str(c.lock_timeout_ms))
        factory = _pool_factory or ConnectionPool
        self._pool = factory(conninfo="", connection_class=RedactedConnection,
            kwargs={"host": c.host, "port": c.port, "dbname": c.database, "user": c.user,
                    "password": c.password, "connect_timeout": c.connect_timeout_seconds,
                    "autocommit": True, "client_encoding": "UTF8", "options": options,
                    "application_name": "askdata_" + c.source_id},
            min_size=c.pool_min_size, max_size=c.pool_max_size,
            timeout=c.pool_wait_timeout_seconds, max_waiting=c.pool_max_waiting,
            name="askdata_pg_" + uuid4().hex[:12], open=False,
            configure=self._configure, check=self._check)

    def _configure(self, conn) -> None:
        try:
            # Verify the actual login, not just configured strings. This is a
            # connection identity check, not full M1 B live data verification.
            row = conn.execute("""SELECT current_database(), current_user,
                current_setting('server_version_num')::int,
                current_setting('server_encoding'), current_setting('TimeZone'),
                current_setting('default_transaction_read_only'),
                d.datcollate, d.datctype, d.datlocprovider,
                r.rolcanlogin, r.rolsuper, r.rolcreatedb, r.rolcreaterole,
                r.rolreplication, r.rolbypassrls,
                has_database_privilege(current_database(), 'CREATE'),
                has_database_privilege(current_database(), 'TEMP'),
                has_schema_privilege(%s, 'USAGE'), has_schema_privilege(%s, 'CREATE'),
                pg_has_role(current_user, 'askdata_import', 'MEMBER'),
                (SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname=%s)
                FROM pg_database d, pg_roles r
                WHERE d.datname=current_database() AND r.rolname=current_user""",
                (self.config.schema,) * 3).fetchone()
            valid = (row is not None and row[0:2] == (self.config.database, self.config.user)
                and 160000 <= row[2] < 170000
                and row[3:9] == ("UTF8", "UTC", "on", "C", "C", "c")
                and row[9:15] == (True, False, False, False, False, False)
                and row[15:21] == (False, False, True, False, False, "askdata_import"))
            if not valid:
                raise PostgresConnectionError("connection_identity_mismatch")
            if not conn.autocommit or conn.pgconn.transaction_status != self._status.IDLE:
                raise PostgresConnectionError("connection_not_idle")
            with self._lock:
                self._identity = {"database": row[0], "query_role": row[1],
                    "server_version_num": row[2], "encoding": row[3], "timezone": row[4],
                    "connection_identity_verified": True}
        except Exception as error:
            fault = safe_error(error)
            with self._lock:
                self._connect_error = fault
            conn.close()
            raise fault from None

    def _check(self, conn) -> None:
        try:
            if conn.closed or not conn.autocommit or conn.pgconn.transaction_status != self._status.IDLE:
                raise PostgresConnectionError("connection_not_idle")
            conn.execute("SELECT 1").fetchone()
        except Exception as error:
            # Discard here so the pool cannot attempt a second, unredacted
            # rollback of a contaminated or failed connection on checkout.
            conn.close()
            raise safe_error(error) from None

    def open(self) -> PostgresConnectionManager:
        with self._lock:
            if self._state == "open":
                return self
            if self._state != "new":
                raise PostgresConnectionError("manager_closed" if self._state == "closed" else "manager_opening")
            self._state = "opening"
        try:
            self._pool.open(wait=False)
            self._pool.wait(timeout=self.config.pool_wait_timeout_seconds)
            with self._lock:
                if self._state == "closed":
                    raise PostgresConnectionError("manager_closed")
                self._state = "open"
            return self
        except Exception as error:
            fault = self._connect_error or safe_error(error)
            self.close()
            raise fault from None

    def require_open(self) -> None:
        with self._lock:
            if self._state != "open":
                raise PostgresConnectionError("manager_closed" if self._state == "closed" else "manager_not_open")

    def _reset(self, conn) -> None:
        """Synchronous cleanup before putconn; a failed cleanup discards it."""
        try:
            status = conn.pgconn.transaction_status
            if conn.closed or status == self._status.UNKNOWN:
                conn.close()
                return
            if status == self._status.ACTIVE:
                raise PostgresConnectionError("connection_active_on_return")
            if status in (self._status.INTRANS, self._status.INERROR):
                conn.rollback()
            conn.autocommit = True
            conn.execute("RESET ROLE")
            conn.execute("RESET ALL")
            if conn.pgconn.transaction_status != self._status.IDLE:
                raise PostgresConnectionError("connection_not_idle")
        except Exception as error:
            conn.close()
            raise safe_error(error) from None

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        self.require_open()
        try:
            conn = self._pool.getconn(timeout=self.config.pool_wait_timeout_seconds)
        except Exception as error:
            raise safe_error(error) from None
        with self._lock:
            self._active += 1
        primary_error = False
        operation_error = None
        try:
            self.require_open()  # close may race with checkout
            with conn.transaction():
                conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
                for key, value in [("search_path", "pg_catalog," + self.config.schema),
                    ("TimeZone", "UTC"), ("DateStyle", "ISO, YMD"), ("extra_float_digits", "3"),
                    ("statement_timeout", str(self.config.statement_timeout_ms)),
                    ("lock_timeout", str(self.config.lock_timeout_ms))]:
                    conn.execute("SELECT set_config(%s, %s, true)", (key, value))
                try:
                    yield conn
                except BaseException as error:
                    # A failed rollback must not replace the original query
                    # failure (or cancellation); cleanup still discards it.
                    operation_error = error
                    raise
                status = conn.pgconn.transaction_status
                if status != self._status.INTRANS:
                    raise PostgresConnectionError("transaction_aborted" if status == self._status.INERROR
                        else "transaction_boundary_changed")
        except BaseException as error:
            primary_error = True
            fault = operation_error or error
            if isinstance(fault, Exception):
                raise safe_error(fault) from None
            raise fault
        finally:
            cleanup_error = None
            try:
                self._reset(conn)
            except Exception as error:
                cleanup_error = safe_error(error)
            try:
                self._pool.putconn(conn)
            except Exception as error:
                conn.close()
                cleanup_error = cleanup_error or safe_error(error)
            finally:
                with self._lock:
                    self._active -= 1
            if cleanup_error is not None and not primary_error:
                raise cleanup_error from None

    def close(self) -> None:
        # Do not hold the state lock while joining pool workers: configure()
        # may still be finishing a connection on one of those workers.
        with self._close_lock:
            with self._lock:
                self._state = "closed"
                if self._close_complete:
                    return
            try:
                self._pool.close(timeout=5.0)
            except Exception as error:
                raise safe_error(error) from None
            self._close_complete = True

    def public_status(self) -> dict[str, Any]:
        with self._lock:
            return {"state": self._state, "active_operation_count": self._active,
                "dependencies": dict(DEPENDENCIES), "connection_identity": self._identity,
                "pool": {k: v for k, v in self._pool.get_stats().items() if isinstance(v, int)},
                "live_target_verified": False, "runtime_available": False}

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
