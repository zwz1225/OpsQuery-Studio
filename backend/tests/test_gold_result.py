from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from evaluation.gold_result import resolve_gold_result
from evaluation.models import EvaluationResult


def load_runner():
    """Import the real runner with only external application services stubbed.

    All evaluation code (including comparator, model and reports) stays real.
    The patch is scoped so other tests keep their normal app imports.
    """
    base = next(
        parent for parent in Path(__file__).resolve().parents
        if (parent / "evaluation" / "run_benchmark.py").exists()
    )
    services = {
        "app.config": {"BASE_DIR": base, "settings": SimpleNamespace()},
        "app.errors": {"PipelineStageError": type("PipelineStageError", (Exception,), {})},
        "app.model_client": {"ModelClient": Mock},
        "app.querying.duckdb_engine": {"DuckDbEngine": Mock},
        "app.retrieval": {"SchemaGraphBuilder": Mock, "SchemaIndex": Mock},
        "app.security": {"AccessController": Mock},
        "app.workflows.query_graph": {"QueryWorkflow": Mock},
    }
    modules = {}
    for name, attributes in services.items():
        module = ModuleType(name)
        module.__dict__.update(attributes)
        modules[name] = module
    spec = importlib.util.spec_from_file_location("evaluation_runner_test", base / "evaluation/run_benchmark.py")
    runner = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(runner)
    return runner


class GoldResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_runner()

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.cache = Path(directory.name)
        self.case = dict(case_id="case/001", query="channels", scenario="growth_ops",
                         category="channels", query_type="list", difficulty="simple",
                         classic=True, gold_fields=["channel"], retrieval_terms=[],
                         gold_sql="SELECT channel FROM channels", order_sensitive=True,
                         expected_columns=["channel"], expected_rows=[{"channel": "STALE"}])
        self.rows = [{"channel": "A"}, {"channel": "B"}]
        self.scope = Mock()
        self.scope.public.return_value = {"allowed_tables": ["channels"]}
        self.engine = Mock()
        self.engine.execute.return_value = SimpleNamespace(
            success=True, columns=["channel"], rows=self.rows, execution_ms=2.5, error=None)

    def resolve(self, **kwargs):
        return resolve_gold_result(self.case, self.engine, self.scope, cache_dir=self.cache, **kwargs)

    def live(self, rows, **kwargs):
        schema = Mock()
        schema.retrieve.return_value = {"hits": [{"doc_id": "channel"}]}
        builder = Mock()
        builder.build.return_value = {"tables": ["channels"]}
        builder.context_text.return_value = "schema"
        workflow = Mock()
        workflow.single_database_agent.prepare.return_value = {
            "action": "executed", "execution": {
                "success": True, "columns": ["channel"], "rows": rows,
                "sql": "SELECT channel FROM channels", "execution_ms": 1.0}}
        controller = Mock()
        controller.resolve.return_value = self.scope
        return self.runner.run_live_case(self.case, schema, builder, workflow, controller,
                                        gold_engine=self.engine, gold_cache_dir=self.cache, **kwargs)

    def test_gold_execution_saves_results_even_when_static_answer_is_stale(self):
        result = self.runner.run_gold_case(self.case, self.engine, self.scope, gold_cache_dir=self.cache)
        self.assertIsInstance(result, EvaluationResult)
        self.assertFalse(result.result_metrics["correct"])
        self.assertTrue(result.result_metrics["gold_result_generated"])
        path = Path(result.result_metrics["gold_result_cache_path"])
        self.assertEqual(path.parent, self.cache)
        saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(saved["rows"], self.rows)
        self.assertEqual(saved["gold_sql"], self.case["gold_sql"])
        self.assertIn("generated_at", saved)

    def test_live_matches_dynamic_gold_not_stale_expected_rows(self):
        result = self.live(self.rows).to_dict()
        self.assertTrue(result["result_correct"])
        self.assertEqual(result["comparison_target"], "gold_result")
        self.assertEqual(result["gold_result_source"], "execution")

    def test_live_benchmark_uses_time_field_policy_when_enabled(self):
        schema = Mock()
        schema.retrieve.return_value = {"hits": [{"doc_id": "channel"}]}
        schema.include_time_fields.side_effect = lambda retrieval, *_args, **_kwargs: {
            **retrieval,
            "hits": retrieval["hits"] + [{"doc_id": "metric_date"}],
            "time_field_supplement": {"added_fields": [{"doc_id": "metric_date"}]},
        }
        builder = Mock()
        builder.build.return_value = {"tables": ["channels"]}
        builder.context_text.return_value = "schema"
        workflow = Mock()
        workflow.config = SimpleNamespace(
            time_field_supplement_enabled=True,
            time_field_supplement_max_extra_fields=2,
            time_field_supplement_max_total_fields=22,
        )
        workflow.time_field_policy.propose.return_value = {
            "time_cue": True,
            "matched_metrics": ["channel"],
            "proposals": [{"doc_id": "metric_date", "reason": "test"}],
        }
        workflow.single_database_agent.prepare.return_value = {
            "action": "executed",
            "execution": {
                "success": True, "columns": ["channel"], "rows": self.rows,
                "sql": "SELECT channel FROM channels", "execution_ms": 1.0,
            },
        }
        controller = Mock()
        controller.resolve.return_value = self.scope
        result = self.runner.run_live_case(
            self.case, schema, builder, workflow, controller,
            gold_engine=self.engine, gold_cache_dir=self.cache,
        )
        schema.include_time_fields.assert_called_once()
        self.assertEqual(result.schema_metrics["retrieved_fields"], ["channel", "metric_date"])
        self.assertEqual(
            result.trace.schema_retrieval["time_field_supplement"]["added_fields"],
            [{"doc_id": "metric_date"}],
        )
        self.assertEqual(
            workflow.single_database_agent.prepare.call_args.args[4]["time_field_supplement"]["added_fields"],
            [{"doc_id": "metric_date"}],
        )

    def test_live_rejects_different_results(self):
        self.assertFalse(self.live([{"channel": "A"}, {"channel": "C"}]).result_metrics["correct"])

    def test_live_respects_order_sensitive(self):
        self.assertFalse(self.live(self.rows[::-1]).result_metrics["correct"])
        self.case["order_sensitive"] = False
        self.assertTrue(self.live(self.rows[::-1]).result_metrics["correct"])

    def test_legacy_without_sql_uses_static_answer(self):
        self.case.pop("gold_sql")
        result = self.live(self.case["expected_rows"]).to_dict()
        self.assertTrue(result["result_correct"])
        self.assertEqual(result["comparison_target"], "expected_rows")
        self.assertEqual(result["gold_result_source"], "expected_rows")
        self.engine.execute.assert_not_called()

    def test_cache_hit_skips_execution(self):
        self.resolve()
        self.engine.reset_mock()
        self.assertIsNone(self.resolve()["execution_ms"])
        result = self.live(self.rows).to_dict()
        self.assertTrue(result["result_correct"])
        self.assertEqual(result["gold_result_source"], "cache")
        self.engine.execute.assert_not_called()

    def test_forced_refresh_reexecutes(self):
        self.resolve()
        self.engine.execute.return_value.rows = [{"channel": "NEW"}]
        refreshed = self.resolve(use_cached_gold=False)
        self.assertEqual(refreshed["rows"], [{"channel": "NEW"}])
        self.assertEqual(self.engine.execute.call_count, 2)

    def test_changed_sql_or_scope_invalidates_cache(self):
        self.resolve()
        self.case["gold_sql"] += " ORDER BY channel"
        self.assertEqual(self.resolve()["source"], "execution")
        self.scope.public.return_value = {"allowed_tables": []}
        self.assertEqual(self.resolve()["source"], "execution")

    def test_changed_data_version_invalidates_cache(self):
        self.resolve(data_version="data-v1")
        self.assertEqual(self.resolve(data_version="data-v1")["source"], "cache")
        self.assertEqual(self.resolve(data_version="data-v2")["source"], "execution")

    def test_truncated_gold_is_not_cached_or_scored(self):
        self.engine.execute.return_value.truncated = True
        with self.assertRaisesRegex(RuntimeError, "scoring limit"):
            self.resolve(data_version="data-v1")
        self.assertEqual(list(self.cache.glob("*.json")), [])

    def test_corrupt_cache_is_regenerated(self):
        result = self.resolve()
        Path(result["cache_path"]).write_text("{broken", encoding="utf-8")
        self.assertEqual(self.resolve()["source"], "execution")

    def test_failed_gold_does_not_fall_back_or_save(self):
        self.engine.execute.return_value.success = False
        self.engine.execute.return_value.error = "bad SQL"
        result = self.live(self.case["expected_rows"])
        self.assertFalse(result.result_metrics["correct"])
        self.assertTrue(result.sql_metrics["execution_success"])
        self.assertEqual(result.errors["stage"], "gold_result")
        self.assertEqual(list(self.cache.glob("*.json")), [])

    def test_gold_without_static_answer_generates_but_does_not_claim_correctness(self):
        self.case.pop("expected_rows")
        self.case.pop("expected_columns")
        result = self.runner.run_gold_case(self.case, self.engine, self.scope, gold_cache_dir=self.cache)
        self.assertTrue(result.result_metrics["gold_result_generated"])
        self.assertFalse(result.result_metrics["correct"])
        self.assertEqual(result.result_metrics["comparison_target"], "none")
        self.assertTrue(self.live(self.rows).result_metrics["correct"])

    def test_empty_gold_is_valid(self):
        self.engine.execute.return_value.rows = []
        self.assertTrue(self.live([]).result_metrics["correct"])

    def test_reports_keep_old_fields_and_add_source(self):
        result = self.live(self.rows).to_dict()
        output = self.cache / "report.json"
        self.runner.save_report([result], self.runner.summarize([result], "live"), output)
        saved = json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(saved["cases"][0]["result_correct"])
        self.assertEqual(saved["cases"][0]["gold_result_source"], "execution")
        self.assertIn("gold_result_source", output.with_suffix(".csv").read_text(encoding="utf-8-sig"))
        self.assertTrue(output.with_suffix(".md").exists())


if __name__ == "__main__":
    unittest.main()
