from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import duckdb
try:
    from psycopg.pq import TransactionStatus
except ImportError:
    raise unittest.SkipTest("Optional M1 B tests require requirements-postgres.txt")

from scripts import import_m1_b_postgres as importer
from scripts import m1_b_postgres_common as common
from scripts.validate_m1_b_postgres import load_import_record


class Result:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    """Transaction failure injection only; not a PostgreSQL integration substitute."""
    def __init__(self, commit_failure=False, probe_state="42501"):
        self.closed = False
        self.info = SimpleNamespace(transaction_status=TransactionStatus.IDLE)
        self.depth = self.commits = self.rollbacks = self.forced_rollbacks = 0
        self.commit_failure, self.probe_state = commit_failure, probe_state

    @contextmanager
    def transaction(self, force_rollback=False):
        self.depth += 1
        try:
            yield
        except BaseException:
            self.rollbacks += 1
            raise
        else:
            if force_rollback:
                self.forced_rollbacks += 1
            elif self.depth == 1:
                if self.commit_failure:
                    self.closed = True
                    raise ConnectionError("Commit connection lost")
                self.commits += 1
        finally:
            self.depth -= 1

    def execute(self, sql, params=None):
        if sql.startswith(("INSERT", "UPDATE", "DELETE", "CREATE TABLE")) and self.probe_state:
            error = RuntimeError("Raw database detail is private")
            error.sqlstate = self.probe_state
            raise error
        return Result((True,) if "pg_try_advisory_xact_lock" in sql else (1,))


class ImportTransactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "new_report.json"
        self.report = common.begin_report(self.output, Path(self.tmp.name) / "preparation", "import")
        self.manifest = {"tables": []}
        self.patches = [patch.object(importer, "configure_transaction"), patch.object(importer, "check_identity", return_value={}),
                       patch.object(importer, "relation_objects", return_value=[]), patch.object(importer, "copy_tables"),
                       patch.object(importer, "check_source_files"), patch.object(importer, "verify_target", side_effect=self.verified)]
        self.mocks = [item.start() for item in self.patches]
        for item in self.patches:
            self.addCleanup(item.stop)

    def verified(self, connection, manifest, result):
        result["summary"] = {"table_count": 41}
        return "d" * 64

    def run_import(self, connection):
        importer.execute_import(connection, self.manifest, self.report, self.output, 120000)

    def test_success_commits_only_after_validation(self):
        connection = FakeConnection()
        self.run_import(connection)
        self.assertEqual(connection.commits, 1)
        self.assertEqual(self.report["commit_state"], "committed")
        self.assertTrue(self.report["target_data_verified"])
        self.mocks[5].assert_called_once()

    def test_copy_failure_rolls_back(self):
        self.mocks[3].side_effect = RuntimeError("copy failed")
        connection = FakeConnection()
        with self.assertRaises(RuntimeError): self.run_import(connection)
        self.assertEqual((connection.commits, connection.rollbacks), (0, 1))
        self.assertEqual(self.report["commit_state"], "rolled_back")
        self.assertFalse(self.report["target_data_verified"])

    def test_data_mismatch_rolls_back_before_commit(self):
        self.mocks[5].side_effect = common.CheckFailed("Target data differs")
        connection = FakeConnection()
        with self.assertRaises(common.CheckFailed): self.run_import(connection)
        self.assertEqual((connection.commits, connection.rollbacks), (0, 1))

    def test_nonempty_schema_refuses_copy(self):
        self.mocks[2].return_value = [("existing_table", "r")]
        connection = FakeConnection()
        with self.assertRaises(common.CheckFailed): self.run_import(connection)
        self.mocks[3].assert_not_called()
        self.assertEqual(connection.commits, 0)

    def test_wrong_target_identity_refuses_copy(self):
        self.mocks[1].side_effect = common.CheckFailed("Wrong database")
        with self.assertRaises(common.CheckFailed): self.run_import(FakeConnection())
        self.mocks[3].assert_not_called()

    def test_source_drift_refuses_commit(self):
        self.mocks[4].side_effect = common.CheckFailed("Source changed")
        connection = FakeConnection()
        with self.assertRaises(common.CheckFailed): self.run_import(connection)
        self.assertEqual((connection.commits, connection.rollbacks), (0, 1))

    def test_commit_connection_loss_is_unknown(self):
        connection = FakeConnection(commit_failure=True)
        with self.assertRaises(ConnectionError): self.run_import(connection)
        self.assertEqual(self.report["commit_state"], "unknown")
        self.assertFalse(self.report["target_data_verified"])
        self.assertEqual(self.report["candidate_target_data_version"], "d" * 64)

    def test_cannot_save_commit_record_causes_rollback(self):
        connection = FakeConnection()
        with patch.object(importer, "save_report", side_effect=OSError("Disk full")):
            with self.assertRaises(OSError): self.run_import(connection)
        self.assertEqual((connection.commits, connection.rollbacks), (0, 1))
        self.assertEqual(self.report["commit_state"], "rolled_back")

    def test_interrupt_before_commit_rolls_back(self):
        self.mocks[3].side_effect = KeyboardInterrupt()
        connection = FakeConnection()
        with self.assertRaises(KeyboardInterrupt): self.run_import(connection)
        self.assertEqual(connection.rollbacks, 1)
        self.assertEqual(self.report["commit_state"], "rolled_back")


class DigestOracleConnection:
    """Execute real aggregation/row reads in DuckDB; PG catalogs are separate stubs."""
    def __init__(self, rows):
        self.db = duckdb.connect(config={"threads": 1})
        self.db.execute('CREATE SCHEMA askdata_ops')
        self.db.execute('CREATE TABLE askdata_ops.fixture (id VARCHAR, value BIGINT)')
        self.db.executemany('INSERT INTO askdata_ops.fixture VALUES (?,?)', rows)

    def execute(self, sql, params=None):
        if "pg_current_snapshot" in sql: return Result(("fixture-snapshot",))
        if sql.startswith("LOCK TABLE"): return Result((None,))
        if "pg_get_userbyid" in sql: return Result((common.TARGET["import_role"], False, False))
        if "has_table_privilege" in sql: return Result((True,))
        return self.db.execute(sql)

    def cursor(self, name=None):
        return self.db.cursor()


class WholeRowVerificationTests(unittest.TestCase):
    def setUp(self):
        self.rows = [("U1", 10), ("U2", 20), ("U3", 30), ("U4", 40)]
        fields = [{"name": "id", "source_type": "VARCHAR", "postgresql_type": "text", "null_count": 0,
                   "non_null_distinct_count": 4, "minimum": "U1", "maximum": "U4"},
                  {"name": "value", "source_type": "BIGINT", "postgresql_type": "bigint", "null_count": 0,
                   "non_null_distinct_count": 4, "minimum": 10, "maximum": 40, "sum": 100, "average": 25.0}]
        self.table = {"name": "fixture", "primary_key": ["id"], "row_count": 4, "columns": fields,
                      "typed_row_multiset_sha256": common.multiset_hash([common.typed_row_hash(r, fields) for r in self.rows])}
        self.manifest = {"tables": [self.table], "business_relations": [],
                         "floating_aggregate_comparison": {"relative_tolerance": 1e-9, "absolute_tolerance": 1e-6}}
        metadata = [{"name": f["name"], "postgresql_type": f["postgresql_type"], "not_null": f["name"] == "id",
                     "identity": "", "generated": "", "has_default": False} for f in fields]
        for mock in [patch.object(common, "relation_objects", return_value=[("fixture", "r")]),
                     patch.object(common, "column_metadata", return_value=metadata),
                     patch.object(common, "primary_key", return_value=["id"])]:
            mock.start()
            self.addCleanup(mock.stop)

    def test_reordered_rows_match(self):
        connection = DigestOracleConnection(list(reversed(self.rows)))
        self.addCleanup(connection.db.close)
        result = {}
        version = common.verify_target(connection, self.manifest, result)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(len(version), 64)

    def test_same_statistics_different_row_associations_fail(self):
        connection = DigestOracleConnection([("U1", 10), ("U2", 30), ("U3", 20), ("U4", 40)])
        self.addCleanup(connection.db.close)
        result = {}
        with self.assertRaises(common.CheckFailed): common.verify_target(connection, self.manifest, result)
        self.assertEqual([error["check"] for error in result["errors"]], ["full_typed_row_content"])


class GuardAndPermissionTests(unittest.TestCase):
    def test_atomic_report_failure_preserves_previous_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"report.json"
            path.write_bytes(b"previous complete record")
            with patch.object(common.os, "replace", side_effect=OSError("Disk error")):
                with self.assertRaises(OSError): common.save_report(path, {"commit_state": "committed"})
            self.assertEqual(path.read_bytes(), b"previous complete record")
            self.assertEqual(list(Path(tmp).glob("*.tmp")), [])

    def test_interrupted_commit_can_be_independently_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"report.json"
            record = {"mode": "import", "target": common.TARGET, "run_status": "running",
                      "commit_state": "commit_in_progress", "candidate_target_data_version": "a"*64,
                      "source_preparation": {"canonical_import_spec_sha256": common.APPROVED_SPEC}}
            path.write_text(json.dumps(record), encoding="utf-8")
            evidence = load_import_record(path)
            self.assertTrue(evidence["recovery_of_unknown_commit"])
            self.assertEqual(evidence["expected_target_data_version"], "a"*64)

    def test_existing_report_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            path.write_bytes(b"original report")
            with self.assertRaises(FileExistsError): common.begin_report(path, Path(tmp)/"prep", "import")
            self.assertEqual(path.read_bytes(), b"original report")

    def test_password_error_text_is_not_reported(self):
        result = common.safe_error(RuntimeError("password=private-value host=private-host"))
        self.assertNotIn("private-value", json.dumps(result))
        self.assertNotIn("private-host", json.dumps(result))

    def test_bigint_sum_is_exact_and_decimal_not_lost(self):
        policy = {"relative_tolerance": 1e-9, "absolute_tolerance": 1e-6}
        self.assertTrue(common.stat_equal(Decimal("9223372036854775807"), 9223372036854775807, "BIGINT", "sum", policy))
        self.assertFalse(common.stat_equal(Decimal("9223372036854775806"), 9223372036854775807, "BIGINT", "sum", policy))

    def test_timestamp_microsecond_loss_fails(self):
        value = datetime(2026, 1, 1, 12, 0, 0, 123456)
        expected = "2026-01-01 12:00:00.123456"
        self.assertTrue(common.stat_equal(value, expected, "TIMESTAMP", "minimum", {}))
        self.assertFalse(common.stat_equal(value.replace(microsecond=123000), expected, "TIMESTAMP", "minimum", {}))

    def test_actual_permission_denial_uses_read_write_and_recovers(self):
        connection, result = FakeConnection(), {}
        common.write_denial_probes(connection, {"name": "fixture", "primary_key": ["id"], "columns": [{"name": "id"}]}, result)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(connection.forced_rollbacks, 1)
        self.assertEqual(connection.rollbacks, 4)

    def test_readonly_transaction_denial_is_not_acl_proof(self):
        connection, result = FakeConnection(probe_state="25006"), {}
        with self.assertRaises(common.CheckFailed):
            common.write_denial_probes(connection, {"name": "fixture", "primary_key": ["id"], "columns": [{"name": "id"}]}, result)
        self.assertTrue(result["all_probe_changes_rolled_back"])
        self.assertFalse(any(c["permission_denied"] for c in result["checks"]))

    def test_unexpected_write_success_fails_and_rolls_back(self):
        connection, result = FakeConnection(probe_state=None), {}
        with self.assertRaises(common.CheckFailed):
            common.write_denial_probes(connection, {"name": "fixture", "primary_key": ["id"], "columns": [{"name": "id"}]}, result)
        self.assertEqual(connection.forced_rollbacks, 1)

    def test_tampered_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for name in ["source_preflight.json", "import_manifest.json", "preparation_review.json"]:
                (folder/name).write_bytes((common.DEFAULT_PREPARATION/name).read_bytes())
            manifest = json.loads((folder/"import_manifest.json").read_bytes())
            manifest["tables"][0]["row_count"] += 1
            (folder/"import_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(common.CheckFailed): common.load_preparation(folder)

    def test_check_only_report_cannot_be_used_as_import_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"check.json"
            path.write_text(json.dumps({"mode": "import_check_only", "target": common.TARGET}), encoding="utf-8")
            with self.assertRaises(common.CheckFailed): load_import_record(path)


class CopyStreamTests(unittest.TestCase):
    def run_copy(self, *, expected_hash=None, copied_rows=2):
        self.payload = b'\xef\xbb\xbfid,value\n"A",1\n"B",2\n'
        self.sent = bytearray()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder/"fixture.csv").write_bytes(self.payload)
            table = {"name": "fixture", "csv_relative_path": "fixture.csv", "row_count": 2,
                     "csv_sha256": expected_hash or hashlib.sha256(self.payload).hexdigest(),
                     "create_table_sql": "CREATE TABLE fixture ...", "copy_from_stdin_sql": "COPY fixture ..."}
            parent = self
            class Cursor:
                rowcount = -1
                def __enter__(self): return self
                def __exit__(self, *args): pass
                @contextmanager
                def copy(self, sql):
                    yield SimpleNamespace(write=parent.sent.extend)
                    self.rowcount = copied_rows
            connection = SimpleNamespace(execute=lambda sql: None, cursor=Cursor)
            records = []
            with patch.object(importer, "BASE", folder):
                importer.copy_tables(connection, {"tables": [table]}, records)
            return records

    def test_raw_csv_bom_preserved_and_rowcount_read_after_copy(self):
        records = self.run_copy()
        self.assertEqual(bytes(self.sent), self.payload)
        self.assertEqual(records[0]["copy_row_count"], 2)
        self.assertEqual(records[0]["csv_bytes_sent"], len(self.payload))

    def test_stream_checksum_mismatch_refuses_import(self):
        with self.assertRaises(common.CheckFailed): self.run_copy(expected_hash="0"*64)

    def test_copy_row_count_mismatch_refuses_import(self):
        with self.assertRaises(common.CheckFailed): self.run_copy(copied_rows=1)


if __name__ == "__main__":
    unittest.main()
