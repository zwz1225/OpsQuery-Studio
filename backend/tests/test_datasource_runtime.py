from __future__ import annotations

from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app.config import BASE_DIR, settings
from app.datasources import create_datasource_runtime
from app.datasources.csv_metadata import csv_data_version, load_csv_catalog
from app.model_client import ModelClient
from app.querying.duckdb_engine import DuckDbEngine
from app.retrieval import SchemaGraphBuilder, SchemaIndex
from app.security import AccessController
from evaluation.gold_result import resolve_gold_result
from evaluation.run_manifest import comparison_identity, data_digest


class DatasourceRuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = replace(settings, api_key="", session_archive_enabled=False)
        cls.runtime = create_datasource_runtime(cls.config)
        cls.scope = AccessController().resolve("demo_growth_ops")

    @classmethod
    def tearDownClass(cls):
        cls.runtime.close()

    def test_snapshot_and_recorded_data_match_existing_catalog(self):
        from app.database import RELATIONS, SCHEMA
        self.assertEqual(self.runtime.catalog.tables, SCHEMA)
        self.assertEqual(self.runtime.catalog.relations, RELATIONS)
        self.assertEqual(self.runtime.identity.data_version, data_digest(BASE_DIR))
        copied = self.runtime.catalog.tables
        copied[0]["fields"][0]["label"] = "mutated"
        self.assertNotEqual(copied, self.runtime.catalog.tables)

    def test_index_and_graph_share_catalog_and_source(self):
        index = SchemaIndex(ModelClient(self.config), self.config, runtime=self.runtime)
        graph = SchemaGraphBuilder(runtime=self.runtime)
        self.runtime.assert_shared(index, graph)
        raw = index._build_raw_documents()
        self.assertEqual(len(raw), 276)
        self.assertEqual(index.tables, self.runtime.metadata.load_catalog().tables)
        self.assertEqual(index._schema_signature(self.runtime), self.runtime.index_signature())
        self.assertIn(self.runtime.identity.source_id, index.index_path.parts)
        self.assertEqual(graph.build([])["source_identity"], self.runtime.identity.public())
        index.close()  # An injected runtime remains owned by its caller.
        self.runtime.require_open()

    def test_unsupported_backend_has_no_fallback(self):
        with self.assertRaisesRegex(ValueError, "Unsupported DATA_BACKEND"):
            create_datasource_runtime(replace(self.config, data_backend="mysql"))

    def test_source_id_cannot_escape_cache_directory(self):
        with self.assertRaisesRegex(ValueError, "DATA_SOURCE_ID"):
            create_datasource_runtime(replace(self.config, data_source_id="../other"))

    def test_dynamic_metadata_profiles_validated_fields_with_typed_samples(self):
        profile = self.runtime.metadata.profile_table(
            "short_video_ops.user_registrations", ["registered_at"])["registered_at"]
        self.assertGreater(len(profile["sample_values"]), 0)
        self.assertTrue(all(isinstance(value, str) for value in profile["sample_values"]))
        self.assertEqual(profile["sample_values"], sorted(profile["sample_values"]))
        with self.assertRaisesRegex(ValueError, "Unknown profile field"):
            self.runtime.metadata.profile_table("short_video_ops.user_registrations", ["not_a_column"])
        with self.assertRaisesRegex(ValueError, "Unknown catalog table"):
            self.runtime.metadata.profile_table("other.user_registrations", ["registered_at"])

    def test_success_empty_and_preview_scoring_limits_keep_contract(self):
        empty = self.runtime.executor.execute("short_video_ops",
            "SELECT user_id FROM user_registrations WHERE registered_at < '1900-01-01'", self.scope)
        self.assertTrue(empty.success, empty.error)
        self.assertEqual(empty.columns, ["user_id"])
        self.assertEqual(empty.rows, [])
        self.assertFalse(empty.truncated)
        sql = "SELECT user_id FROM user_registrations ORDER BY user_id LIMIT 201"
        preview = self.runtime.executor.execute("short_video_ops", sql, self.scope)
        scoring = self.runtime.executor.execute("short_video_ops", sql, self.scope, row_limit=10000)
        self.assertEqual(len(preview.rows), 200)
        self.assertTrue(preview.truncated)
        self.assertEqual(len(scoring.rows), 201)
        self.assertFalse(scoring.truncated)
        self.assertEqual(preview.rows, scoring.rows[:200])

    def test_namespace_and_role_rejections_precede_database_connection(self):
        bad = ["SELECT user_id FROM short_video_ops.user_registrations",
               "SELECT user_id FROM other.user_registrations",
               "SELECT user_id FROM memory.main.user_registrations",
               "WITH contents AS (SELECT content_id FROM contents) SELECT content_id FROM contents",
               "SELECT content_id FROM contents", "SELECT * FROM user_registrations",
               "DELETE FROM user_registrations",
               "SELECT user_id FROM user_registrations; SELECT user_id FROM user_registrations",
               "WITH x AS (SELECT user_id FROM user_registrations) SELECT user_id FROM main.x"]
        with patch("app.querying.duckdb_engine.duckdb.connect") as connect:
            for sql in bad:
                with self.subTest(sql=sql):
                    result = self.runtime.executor.execute("short_video_ops", sql, self.scope)
                    self.assertFalse(result.success)
                    self.assertTrue(result.error)
            connect.assert_not_called()

    def test_legal_schema_and_cte_query_still_execute(self):
        for sql in ["SELECT user_id FROM main.user_registrations LIMIT 1",
                    "WITH x AS (SELECT user_id FROM user_registrations LIMIT 1) SELECT user_id FROM x"]:
            with self.subTest(sql=sql):
                result = self.runtime.executor.execute("short_video_ops", sql, self.scope)
                self.assertTrue(result.success, result.error)
                self.assertEqual(len(result.rows), 1)

    def test_gold_cache_uses_actual_source_and_rejects_wrong_version(self):
        case = {"case_id": "M1-A", "query": "count", "scenario": "growth_ops",
                "gold_sql": "SELECT COUNT(user_id) AS users FROM user_registrations"}
        with tempfile.TemporaryDirectory() as folder:
            result = resolve_gold_result(case, self.runtime.executor, self.scope, cache_dir=Path(folder))
            self.assertEqual(result["source_identity"], self.runtime.identity.public())
            self.assertEqual(Path(result["cache_path"]).parent.name, self.runtime.identity.source_id)
            cached = resolve_gold_result(case, self.runtime.executor, self.scope, cache_dir=Path(folder))
            self.assertEqual(cached["source"], "cache")
            self.assertEqual(cached["rows"], result["rows"])
            with self.assertRaisesRegex(ValueError, "Gold data version"):
                resolve_gold_result(case, self.runtime.executor, self.scope, cache_dir=Path(folder), data_version="wrong")

    def test_concurrent_index_build_publishes_one_complete_version(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as folder:
            config = replace(self.config, api_key="test-no-network")
            model = Mock(config=config, enabled=True)
            model.embed.side_effect = lambda texts: [[1.0, 0.0] for text in texts]
            indexes = [SchemaIndex(model, config, Path(folder) / "index.json", runtime=self.runtime)
                       for _ in range(2)]
            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(lambda index: index.ensure_built(), indexes))
            self.assertEqual(model.embed.call_count, 1)
            self.assertEqual([len(index.documents) for index in indexes], [276, 276])
            payload = json.loads((Path(folder) / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["signature"], indexes[0].index_signature())
            self.assertEqual(payload["cache_identity"], indexes[0].index_identity())
            self.assertEqual(len(payload["documents"]), 276)

    def test_source_changes_isolate_index_and_regression_identity(self):
        with create_datasource_runtime(replace(self.config, data_source_id="another_duckdb")) as other:
            self.assertNotEqual(other.index_signature(), self.runtime.index_signature())
            self.assertNotEqual(comparison_identity({"source_identity": other.identity.public()}),
                                comparison_identity({"source_identity": self.runtime.identity.public()}))
            with self.assertRaisesRegex(ValueError, "runtime mismatch"):
                self.runtime.assert_shared(SimpleNamespace(runtime=other))
            with self.assertRaisesRegex(ValueError, "same datasource"):
                self.runtime.assert_executor(other.executor)

    def test_content_change_changes_data_and_index_version(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            database = root / "short_video_ops"
            database.mkdir()
            schema = {"tables": [{"database": "short_video_ops", "id": "short_video_ops.t",
                                  "name": "t", "fields": []}], "relations": []}
            (database / "_schema.json").write_text(json.dumps(schema), encoding="utf-8")
            csv = database / "t.csv"
            csv.write_text("id\n1\n", encoding="utf-8")
            before = csv_data_version(root, "short_video_ops")
            csv.write_text("id\n2\n", encoding="utf-8")
            self.assertNotEqual(before, csv_data_version(root, "short_video_ops"))
            csv.unlink()
            with self.assertRaisesRegex(ValueError, "tables missing"):
                load_csv_catalog(root, "short_video_ops")

    def test_close_is_idempotent_and_stops_later_queries(self):
        runtime = create_datasource_runtime(self.config)
        runtime.close()
        runtime.close()
        with self.assertRaisesRegex(RuntimeError, "closed"):
            runtime.require_open()
        self.assertFalse(runtime.executor.execute("short_video_ops", "SELECT 1 AS value", self.scope).success)


@unittest.skipUnless(importlib.util.find_spec("langgraph"), "LangGraph requires project environment")
class DatasourceEntryIntegrationTest(unittest.TestCase):
    def setUp(self):
        from app.services.askdata_service import AskDataService
        self.config = replace(settings, api_key="", session_archive_enabled=False)
        self.runtime = create_datasource_runtime(self.config)
        self.addCleanup(self.runtime.close)
        self.model = ModelClient(self.config)
        self.service = AskDataService(self.model, runtime=self.runtime)

    def test_service_workflow_index_mcp_use_one_executor(self):
        service = self.service
        self.runtime.assert_shared(service, service.workflow, service.schema_index, service.workflow.graph_builder)
        self.assertIs(service.workflow.database_engine, self.runtime.executor)
        self.assertIs(service.schema_index.data_engine, self.runtime.executor)
        client = service.workflow.mcp_client(service.access_controller.resolve("demo_growth_ops").public())
        tools = client.list_tools()
        tool = next(t for t in tools if t["name"] == "query_short_video_ops")
        self.assertIn("DuckDB", tool["description"])
        result = client.call_tool("query_short_video_ops", {
            "sql": "SELECT COUNT(user_id) AS users FROM user_registrations"})
        self.assertTrue(result["success"], result.get("error"))
        self.assertGreater(result["rows"][0]["users"], 0)
        service.close()
        self.runtime.require_open()  # Caller owns the injected runtime.

    def test_constructor_and_benchmark_reject_mixed_sources(self):
        from app.services.askdata_service import AskDataService
        from evaluation.run_benchmark import run_live_case
        from evaluation.run_e2e import evaluate_e2e_case
        with create_datasource_runtime(replace(self.config, data_source_id="wrong_source")) as other:
            with self.assertRaisesRegex(ValueError, "runtime mismatch"):
                AskDataService(self.model, self.service.schema_index, runtime=other)
            with self.assertRaisesRegex(ValueError, "same datasource"):
                run_live_case({}, self.service.schema_index, self.service.workflow.graph_builder,
                              self.service.workflow, self.service.access_controller, gold_engine=other.executor)
            with self.assertRaisesRegex(ValueError, "same datasource"):
                evaluate_e2e_case({}, self.service, other.executor, self.service.access_controller,
                                  run_id="test", data_version=other.identity.data_version)

    def test_workflow_rejects_cross_source_request_and_resume(self):
        from langgraph.types import Command
        workflow = self.service.workflow
        with self.assertRaisesRegex(ValueError, "Request datasource"):
            workflow.invoke({"query": "hello", "source_identity": {"source_id": "wrong"}}, "task")
        with self.assertRaisesRegex(ValueError, "Cannot resume"):
            workflow.invoke(Command(resume={"option_id": "x"}), "unknown-task")

    def test_direct_route_preserves_source_in_checkpoint_without_model_requests(self):
        result = self.service.submit("你好", "m1-a-test", user_id="demo_growth_ops")
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.route, "direct_response")
        state = self.service.workflow.graph.get_state(self.service.workflow.run_config(result.task_id)).values
        self.assertEqual(state["source_identity"], self.runtime.identity.public())
        self.assertEqual(self.model.request_attempt_count, 0)
