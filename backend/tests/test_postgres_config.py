from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import BASE_DIR, Settings, settings
from app.datasources.postgres_config import PostgresConfig, PostgresConfigError, load_recorded_source
from app.datasources.runtime import create_datasource_runtime

DEFAULTS = dict(pg_host="127.0.0.1", pg_port="55432", pg_database="askdata_m1_test", pg_schema="askdata_ops",
    pg_user="askdata_readonly", pg_password="test-only-secret", pg_source_id="short_video_ops_postgres",
    pg_connect_timeout_seconds="10", pg_statement_timeout_ms="120000", pg_lock_timeout_ms="5000",
    pg_pool_min_size="1", pg_pool_max_size="4", pg_pool_wait_timeout_seconds="10", pg_pool_max_waiting="16",
    pg_verified_data_version="882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1",
    pg_import_report_path="evaluation/results/m1_b_postgres_import_server.json",
    pg_validation_report_path="evaluation/results/m1_b_postgres_validation_server.json")


class PostgresConfigTests(unittest.TestCase):
    def setUp(self):
        self.settings = replace(settings, **DEFAULTS)

    def config(self, **overrides):
        return PostgresConfig.from_settings(replace(self.settings, **overrides))

    def test_defaults_and_limits_are_typed(self):
        config = self.config()
        self.assertEqual((config.port, config.pool_min_size, config.pool_max_size), (55432, 1, 4))
        self.assertEqual(config.statement_timeout_ms, 120000)
        self.assertEqual(config.user, "askdata_readonly")

    def test_new_settings_read_environment_on_construction(self):
        with patch.dict(os.environ, {"PG_PORT": "55555", "PG_POOL_MAX_SIZE": "6", "PG_PASSWORD": "fresh-secret"}):
            sample = Settings()
        self.assertEqual((sample.pg_port, sample.pg_pool_max_size, sample.pg_password), ("55555", "6", "fresh-secret"))

    def test_password_host_and_paths_are_not_public_or_repr(self):
        config = self.config(pg_host="private-host", pg_password="private-password")
        text = repr(config)+json.dumps(config.public())+repr(replace(self.settings, pg_host="private-host", pg_password="private-password"))
        self.assertNotIn("private-password", text)
        self.assertNotIn("private-host", text)
        status = replace(self.settings, pg_host="private-host", pg_password="private-password").public_status()
        self.assertNotIn("private-password", json.dumps(status))
        self.assertNotIn("private-host", json.dumps(status))
        self.assertNotIn(str(config.validation_report_path), json.dumps(config.public()))

    def test_password_is_required_in_ready_check(self):
        with self.assertRaisesRegex(PostgresConfigError, "PG_PASSWORD is required"):
            self.config(pg_password="")

    def test_offline_missing_password_is_explicitly_allowed(self):
        config = PostgresConfig.from_settings(replace(self.settings, pg_password=""), require_password=False)
        self.assertFalse(config.public()["password_configured"])

    def test_password_whitespace_is_preserved(self):
        self.assertEqual(self.config(pg_password="  meaningful spaces  ").password, "  meaningful spaces  ")

    def test_port_and_numeric_limits_reject_invalid_values_without_echo(self):
        invalid = {"pg_port": ["0", "65536", "private-invalid-value", True],
                   "pg_connect_timeout_seconds": ["0", "121"], "pg_statement_timeout_ms": ["0", "1800001"],
                   "pg_lock_timeout_ms": ["0", "60001"], "pg_pool_min_size": ["0", "33"],
                   "pg_pool_max_size": ["0", "33"], "pg_pool_wait_timeout_seconds": ["0", "121"],
                   "pg_pool_max_waiting": ["0", "257"]}
        for name, values in invalid.items():
            for value in values:
                with self.subTest(name=name, value=value):
                    with self.assertRaises(PostgresConfigError) as error: self.config(**{name: value})
                    self.assertNotIn("private-invalid-value", str(error.exception))

    def test_pool_minimum_cannot_exceed_maximum(self):
        with self.assertRaisesRegex(PostgresConfigError, "PG_POOL_MIN_SIZE"):
            self.config(pg_pool_min_size="5")

    def test_lock_timeout_must_fit_statement_timeout(self):
        with self.assertRaisesRegex(PostgresConfigError, "PG_LOCK_TIMEOUT_MS"):
            self.config(pg_statement_timeout_ms="1000")

    def test_admin_import_and_wrong_target_are_rejected(self):
        for overrides in [{"pg_user": "askdata_admin"}, {"pg_user": "askdata_import"}, {"pg_database": "postgres"},
                          {"pg_schema": "public"}, {"pg_source_id": "short_video_ops_duckdb"}]:
            with self.subTest(overrides=overrides):
                with self.assertRaises(PostgresConfigError): self.config(**overrides)

    def test_host_is_single_explicit_tcp_endpoint(self):
        for host in ["", "postgresql://private-password@host", "localhost,another", "/tmp", "host value"]:
            with self.assertRaises(PostgresConfigError) as error: self.config(pg_host=host)
            self.assertNotIn("private-password", str(error.exception))

    def test_relative_paths_use_backend_not_current_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            try:
                os.chdir(tmp)
                config = self.config()
            finally: os.chdir(previous)
        self.assertEqual(config.validation_report_path, BASE_DIR/DEFAULTS["pg_validation_report_path"])

    def test_invalid_unused_pg_values_do_not_break_duckdb_runtime(self):
        sample = replace(self.settings, data_backend="duckdb", data_source_id="short_video_ops_duckdb", pg_port="invalid")
        with create_datasource_runtime(sample) as runtime:
            self.assertEqual(runtime.identity.backend, "duckdb")

    def test_postgres_application_runtime_remains_unavailable(self):
        with self.assertRaisesRegex(ValueError, "DATA_SOURCE_ID"):
            create_datasource_runtime(replace(self.settings, data_backend="postgresql"))


class PostgresEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.import_path, self.validation_path = [self.folder/name for name in ["import.json", "validation.json"]]
        for source, destination in [(DEFAULTS["pg_import_report_path"], self.import_path),
                                    (DEFAULTS["pg_validation_report_path"], self.validation_path)]:
            destination.write_bytes((BASE_DIR/source).read_bytes())
        self.config = PostgresConfig.from_settings(replace(settings, **{**DEFAULTS,
            "pg_import_report_path": str(self.import_path), "pg_validation_report_path": str(self.validation_path)}))

    def modify(self, path, change):
        record = json.loads(path.read_bytes())
        change(record)
        path.write_text(json.dumps(record), encoding="utf-8")

    def test_accepted_evidence_has_distinct_recorded_not_live_identity(self):
        with patch("socket.create_connection", side_effect=AssertionError("No database connections in C1")):
            public = load_recorded_source(self.config).public()
        self.assertTrue(public["recorded_evidence_verified"])
        self.assertFalse(public["live_target_verified"])
        self.assertFalse(public["runtime_available"])
        self.assertIsNone(public["catalog_version"])
        self.assertEqual(public["recorded_data_version"], DEFAULTS["pg_verified_data_version"])
        self.assertEqual(public["evidence_sha256"]["import"], hashlib.sha256(self.import_path.read_bytes()).hexdigest())

    def test_missing_evidence_has_safe_error(self):
        self.validation_path.unlink()
        with self.assertRaises(PostgresConfigError) as error: load_recorded_source(self.config)
        self.assertNotIn(str(self.folder), str(error.exception))

    def test_wrong_expected_version_is_rejected(self):
        with self.assertRaisesRegex(PostgresConfigError, "PG_VERIFIED_DATA_VERSION"):
            load_recorded_source(replace(self.config, verified_data_version="0"*64))

    def test_uncommitted_import_is_rejected(self):
        self.modify(self.import_path, lambda r: r.update(commit_state="rolled_back"))
        with self.assertRaises(PostgresConfigError): load_recorded_source(self.config)

    def test_import_bytes_must_match_validation_reference(self):
        self.import_path.write_bytes(self.import_path.read_bytes()+b"\n")
        with self.assertRaisesRegex(PostgresConfigError, "reference/hash"):
            load_recorded_source(self.config)

    def test_wrong_schema_or_account_evidence_is_rejected(self):
        self.modify(self.validation_path, lambda r: r["target"].update(physical_schema="public"))
        with self.assertRaisesRegex(PostgresConfigError, "identity"):
            load_recorded_source(self.config)

    def test_modified_rows_fail_recomputed_version(self):
        self.modify(self.validation_path, lambda r: r["validation"]["tables"][0].update(typed_row_multiset_sha256="0"*64))
        with self.assertRaisesRegex(PostgresConfigError, "Recomputed"):
            load_recorded_source(self.config)

    def test_write_permission_in_evidence_is_rejected(self):
        self.modify(self.validation_path, lambda r: r["readonly_acl"]["tables"][0]["grants"].update(UPDATE=True))
        with self.assertRaisesRegex(PostgresConfigError, "ACL"):
            load_recorded_source(self.config)

    def test_readonly_transaction_error_is_not_permission_evidence(self):
        self.modify(self.validation_path, lambda r: r["write_denial_probes"]["checks"][0].update(sqlstate="25006"))
        with self.assertRaisesRegex(PostgresConfigError, "write denial"):
            load_recorded_source(self.config)

    def test_duplicate_keys_and_raw_sensitive_data_are_not_reported(self):
        self.validation_path.write_text('{"mode":"validation","mode":"private-value"}', encoding="utf-8")
        with self.assertRaises(PostgresConfigError) as error: load_recorded_source(self.config)
        self.assertNotIn("private-value", str(error.exception))

    def test_evidence_files_remain_unchanged(self):
        before = [self.import_path.read_bytes(), self.validation_path.read_bytes()]
        load_recorded_source(self.config)
        self.assertEqual(before, [self.import_path.read_bytes(), self.validation_path.read_bytes()])


if __name__ == "__main__":
    unittest.main()
