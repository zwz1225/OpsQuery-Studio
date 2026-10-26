"""Dialect/Gold/source contracts; uses no model or PostgreSQL connection."""
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from app.datasources.contracts import CatalogSnapshot, SourceIdentity
from app.datasources.dialects import dialect_for_backend, validated_source
from app.datasources.runtime import DataSourceRuntime
from evaluation.gold_result import resolve_gold_result
from evaluation.gold_sql import GoldSqlSelectionError, gold_selection_identity, select_gold_sql
from evaluation.run_manifest import EVALUATOR_FILES, build_run_manifest, comparison_identity


def source(backend="postgresql", **changes):
    d = dialect_for_backend(backend)
    return replace(SourceIdentity("short_video_ops", "short_video_ops_" + backend,
        backend, d.parser, d.prompt, "askdata_ops" if backend == "postgresql" else "main",
        "1" * 64, "2" * 64), **changes)


class D1ContractsTest(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.case = {"case_id": "D1-001", "query": "day", "scenario": "growth_ops",
            "category": "date", "query_type": "date", "difficulty": "simple", "classic": False,
            "gold_sql": "SELECT strftime(DATE '2026-01-01','%Y-%m') AS month",
            "gold_sql_by_dialect": {"postgres": "SELECT to_char(DATE '2026-01-01','YYYY-MM') AS month"},
            "expected_columns": ["month"], "expected_rows": [{"month": "2026-01"}]}
        self.scope = Mock()
        self.scope.public.return_value = {"allowed_tables": []}
        self.engine = Mock(source_identity=source())
        self.engine.execute.return_value = SimpleNamespace(success=True, columns=["month"],
            rows=[{"month": "2026-01"}], execution_ms=1.0, error=None, truncated=False)

    def resolve(self, **kwargs):
        return resolve_gold_result(self.case, self.engine, self.scope, cache_dir=self.root/"cache", **kwargs)

    def runtime(self):
        catalog = CatalogSnapshot(json.dumps({"tables": [], "relations": [], "backend": "postgresql"}, sort_keys=True))
        identity = source(catalog_version=catalog.version)
        executor = Mock(source_identity=identity)
        metadata = SimpleNamespace(load_catalog=lambda: catalog, verification={
            "live_target_verified": True, "data_version": identity.data_version,
            "catalog_version": identity.catalog_version, "physical_schema_version": "3"*64})
        runtime = DataSourceRuntime(identity, catalog, executor, metadata)
        self.addCleanup(runtime.close)
        return runtime

    def manifest(self, **kwargs):
        for name in (*EVALUATOR_FILES, "app/query.py", "evaluation/cases/cases.jsonl",
                     "data/metrics/metric_catalog.json"):
            p = self.root/name
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                p.write_text(name, encoding="utf-8")
        return build_run_manifest([self.case], base_dir=self.root, mode="gold", scope="d1",
            config={}, case_source=self.root/"evaluation/cases/cases.jsonl", **kwargs)

    def test_canonical_backend_aliases(self):
        self.assertEqual(dialect_for_backend("postgresql").parser, "postgres")
        self.assertEqual(dialect_for_backend("duckdb").prompt, "DuckDB")
        with self.assertRaises(ValueError):
            dialect_for_backend("postgres")

    def test_invalid_alias_path_and_secret_fields_are_rejected(self):
        for changes in [{"dialect": "postgresql"}, {"prompt_dialect": "DuckDB"},
                        {"source_id": "../escape"}, {"data_version": "unknown"}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validated_source(source(**changes))
        with self.assertRaises(ValueError):
            validated_source({**source().public(), "password": "private"})

    def test_duckdb_retains_original_even_when_postgres_variant_exists(self):
        selected = select_gold_sql(self.case, source("duckdb"))
        self.assertEqual(selected.sql, self.case["gold_sql"])
        self.assertEqual(selected.selection_key, "gold_sql")
        self.assertEqual(select_gold_sql(self.case).sql, self.case["gold_sql"])

    def test_postgres_uses_explicit_variant(self):
        result = self.resolve()
        self.assertEqual(result["gold_sql"], self.case["gold_sql_by_dialect"]["postgres"])
        self.engine.execute.assert_called_once_with("short_video_ops", result["gold_sql"], self.scope, row_limit=10000)
        self.assertEqual(result["gold_selection"]["selection_key"], "gold_sql_by_dialect.postgres")

    def test_missing_or_malformed_postgres_variant_never_executes_or_falls_back(self):
        for variants in [None, {}, {"postgresql": "SELECT 1"}, {"postgres": "  "}, {"postgres": 42}]:
            self.case["gold_sql_by_dialect"] = variants
            with self.subTest(variants=variants), self.assertRaises(GoldSqlSelectionError):
                self.resolve()
        self.engine.execute.assert_not_called()
        self.assertFalse((self.root/"cache").exists())

    def test_postgres_missing_variant_is_rejected_before_using_cache(self):
        self.resolve()
        del self.case["gold_sql_by_dialect"]
        self.engine.execute.reset_mock()
        with self.assertRaises(GoldSqlSelectionError):
            self.resolve()
        self.engine.execute.assert_not_called()

    def test_duckdb_without_sql_keeps_legacy_expected_rows(self):
        self.engine.source_identity = source("duckdb")
        del self.case["gold_sql"]
        result = self.resolve()
        self.assertEqual(result["source"], "expected_rows")
        self.engine.execute.assert_not_called()

    def test_selected_sql_and_source_versions_control_cache_validity(self):
        self.assertEqual(self.resolve()["source"], "execution")
        self.assertEqual(self.resolve()["source"], "cache")
        self.case["gold_sql_by_dialect"]["postgres"] += " ORDER BY month"
        self.assertEqual(self.resolve()["source"], "execution")
        self.engine.source_identity = source(data_version="4"*64)
        self.assertEqual(self.resolve()["source"], "execution")
        self.engine.source_identity = source(data_version="4"*64, catalog_version="5"*64)
        self.assertEqual(self.resolve()["source"], "execution")

    def test_other_source_or_old_cache_format_cannot_hit(self):
        first = self.resolve()
        p = Path(first["cache_path"])
        payload = json.loads(p.read_text())
        del payload["gold_cache_version"]
        p.write_text(json.dumps(payload))
        self.assertEqual(self.resolve()["source"], "execution")
        self.engine.source_identity = source("duckdb")
        other = self.resolve()
        self.assertEqual(other["source"], "execution")
        self.assertNotEqual(Path(other["cache_path"]).parent, p.parent)

    def test_wrong_data_version_is_rejected_before_execution(self):
        with self.assertRaisesRegex(ValueError, "Gold data version"):
            self.resolve(data_version="9"*64)
        self.engine.execute.assert_not_called()

    def test_non_scored_behavior_case_needs_no_postgres_gold(self):
        selection = gold_selection_identity([{"case_id":"route","operation":"ask"}], source())
        self.assertIsNone(selection["cases"][0]["gold"])

    def test_manifest_uses_verified_postgres_versions_without_any_csv_files(self):
        runtime = self.runtime()
        first = self.manifest(runtime=runtime)
        self.assertFalse((self.root/"data/databases").exists())
        self.assertEqual(first["versions"]["data"], runtime.identity.data_version)
        self.assertEqual(first["versions"]["schema"], runtime.catalog.version)
        self.assertEqual(first["versions"]["physical_schema"], "3"*64)
        self.assertEqual(first["gold_selection"]["cases"][0]["gold"]["sql"], self.case["gold_sql_by_dialect"]["postgres"])
        self.assertEqual(first["manifest_version"], 4)

    def test_manifest_rejects_public_postgres_label_without_runtime(self):
        with self.assertRaisesRegex(ValueError, "verified runtime"):
            self.manifest(source_identity=source().public())

    def test_manifest_rejects_conflicting_source_closed_runtime_and_unverified_data(self):
        runtime = self.runtime()
        with self.assertRaisesRegex(ValueError, "differs from runtime"):
            self.manifest(runtime=runtime, source_identity=source("duckdb").public())
        runtime.metadata.verification["data_version"]="7"*64
        with self.assertRaisesRegex(ValueError, "matching live verification"):
            self.manifest(runtime=runtime)
        runtime.close()
        with self.assertRaisesRegex(RuntimeError, "closed"):
            self.manifest(runtime=runtime)

    def test_manifest_rejects_missing_postgres_gold_before_running_cases(self):
        runtime = self.runtime()
        del self.case["gold_sql_by_dialect"]
        with self.assertRaises(GoldSqlSelectionError):
            self.manifest(runtime=runtime)
        runtime.executor.execute.assert_not_called()

    def test_selected_gold_and_physical_versions_change_regression_identity(self):
        runtime = self.runtime()
        first=self.manifest(runtime=runtime)
        self.case["gold_sql_by_dialect"]["postgres"] += " ORDER BY month"
        second=self.manifest(runtime=runtime)
        self.assertNotEqual(first["versions"]["gold_selection"], second["versions"]["gold_selection"])
        self.assertNotEqual(comparison_identity(first), comparison_identity(second))
        runtime.metadata.verification["physical_schema_version"]="8"*64
        self.assertNotEqual(comparison_identity(second), comparison_identity(self.manifest(runtime=runtime)))
        self.assertNotEqual(comparison_identity(first), comparison_identity({**first,"manifest_version":2}))

    def test_gold_runner_records_executed_postgres_sql(self):
        from tests.test_gold_result import load_runner
        runner=load_runner()
        row=runner.run_gold_case(self.case, self.engine, self.scope, gold_cache_dir=self.root/"cache").to_dict()
        sql=self.case["gold_sql_by_dialect"]["postgres"]
        self.assertEqual(row["generated_sql"], sql)
        self.assertEqual(row["gold_sql"], sql)
        self.assertEqual(row["trace"]["sql_execution"]["generated_sql"], sql)
        self.assertTrue(row["strict_result_correct"])
        del self.case["gold_sql_by_dialect"]
        failed=runner.run_gold_case(self.case, self.engine, self.scope, gold_cache_dir=self.root/"cache").to_dict()
        self.assertEqual(failed["error_stage"], "gold_result")
        self.assertEqual(failed["generated_sql"], "")


if __name__ == "__main__":
    unittest.main()
