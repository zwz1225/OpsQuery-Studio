"""C3 storage failures must not mask validation errors or replace history."""
from contextlib import redirect_stdout
import errno
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from app.datasources.postgres_connections import PostgresConnectionError, safe_error
from scripts import check_m1_c3_postgres_runtime as script


class ReportStorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "report.json"
        self.report = {"run_status": "running", "live_target_verified": False,
                       "runtime_available": False, "checks": [], "errors": []}

    @staticmethod
    def passed(report):
        report["checks"].append({"name": "probe", "passed": True})

    def test_complete_report_is_saved_and_temporary_file_removed(self):
        self.assertTrue(script.execute_report(self.output, self.report, self.passed))
        self.assertEqual(json.loads(self.output.read_text(encoding="utf-8")), self.report)
        self.assertEqual(self.report["report_write_status"], "complete")
        self.assertEqual(self.report["check_pass_count"], 1)
        self.assertEqual(list(self.output.parent.iterdir()), [self.output])

    def test_existing_report_is_unchanged_and_checks_do_not_run(self):
        self.output.write_bytes(b"historical-report")
        checks = Mock()
        self.assertFalse(script.execute_report(self.output, self.report, checks))
        checks.assert_not_called()
        self.assertEqual(self.output.read_bytes(), b"historical-report")
        self.assertEqual(self.report["report_write_error"]["category"], "output_exists")

    def test_initial_disk_full_is_detected_before_database_work(self):
        checks = Mock()
        with patch.object(script.os, "fsync", side_effect=OSError(errno.ENOSPC, "private-path")):
            self.assertFalse(script.execute_report(self.output, self.report, checks))
        checks.assert_not_called()
        self.assertEqual(self.report["report_write_error"], {
            "phase": "initial", "type": "OSError", "category": "disk_full", "errno": errno.ENOSPC})
        self.assertNotIn("private-path", json.dumps(self.report))

    def test_final_disk_full_preserves_running_marker_and_primary_error(self):
        def failed(report):
            self.passed(report)
            raise PostgresConnectionError("disk_full", "53100")

        with patch.object(script.os, "fsync", side_effect=[None, OSError(errno.ENOSPC, "private-path")]):
            self.assertFalse(script.execute_report(self.output, self.report, failed))
        marker = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(marker["run_status"], "running")
        self.assertEqual(self.report["errors"][0]["sqlstate"], "53100")
        self.assertEqual(self.report["report_write_error"]["phase"], "final")
        self.assertEqual(self.report["validation_run_status"], "failed")
        self.assertEqual(list(self.output.parent.iterdir()), [self.output])

    def test_validation_success_without_saved_report_is_failed(self):
        with patch.object(script.os, "replace", side_effect=OSError(errno.ENOSPC, "private-path")):
            self.assertFalse(script.execute_report(self.output, self.report, self.passed))
        self.assertEqual(self.report["run_status"], "failed")
        self.assertEqual(self.report["validation_run_status"], "complete")
        self.assertEqual(json.loads(self.output.read_text())["run_status"], "running")

    def test_database_failure_is_recorded_without_raw_driver_text(self):
        class DriverError(Exception):
            sqlstate = "53100"

        def failed(report):
            raise DriverError("private-password private-host private-SQL")

        self.assertFalse(script.execute_report(self.output, self.report, failed))
        saved = json.loads(self.output.read_text())
        self.assertEqual(saved["report_write_status"], "complete")
        self.assertEqual(saved["errors"][0]["category"], "disk_full")
        self.assertNotIn("private-password", json.dumps(saved))

    def test_quota_failure_has_distinct_code(self):
        self.assertEqual(script.public_failure(OSError(errno.EDQUOT, "private-path"))["category"], "quota_exceeded")

    def test_main_prints_both_errors_and_exits_nonzero(self):
        console = io.StringIO()
        with patch("sys.argv", ["check", "--output", str(self.output)]), \
             patch.object(script, "run_checks", side_effect=PostgresConnectionError("query_error", "22012")), \
             patch.object(script.os, "fsync", side_effect=[None, OSError(errno.ENOSPC, "private-path")]), \
             redirect_stdout(console), self.assertRaises(SystemExit) as raised:
            script.main()
        self.assertEqual(raised.exception.code, 1)
        summary = json.loads(console.getvalue())
        self.assertEqual(summary["errors"][0]["sqlstate"], "22012")
        self.assertEqual(summary["report_write_error"]["errno"], errno.ENOSPC)
        self.assertNotIn("private-path", console.getvalue())


if __name__ == "__main__":
    unittest.main()
