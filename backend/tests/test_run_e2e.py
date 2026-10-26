from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock

from app.errors import PipelineStageError
from app.models import Clarification, QueryResult
from app.querying.duckdb_engine import DuckDbEngine
from app.security import AccessController
from evaluation.run_e2e import evaluate_e2e_case, load_e2e_cases, summarize_e2e


class ServiceEntryEvaluationTest(unittest.TestCase):
    def test_behavior_suite_has_ordered_service_cases(self) -> None:
        cases = load_e2e_cases(
            Path(__file__).resolve().parents[1] / "evaluation/cases/e2e_behavior.json"
        )
        self.assertEqual(len(cases), 8)
        self.assertEqual(len({case["case_id"] for case in cases}), 8)
        self.assertEqual(cases[3]["source_case_id"], cases[0]["case_id"])
        self.assertEqual(cases[5]["source_case_id"], cases[4]["case_id"])

    def test_direct_route_requires_an_answer_without_sql(self) -> None:
        case = next(case for case in load_e2e_cases(
            Path(__file__).resolve().parents[1] / "evaluation/cases/e2e_behavior.json"
        ) if case["case_id"] == "E2E-ROUTE-DIRECT")
        service = Mock()
        service.submit.return_value = QueryResult(
            task_id="task1", status="completed", route="direct_response",
            message="answer", analysis="可以查询数据。",
            route_reason="普通问候", direct_response_type="answer",
        )
        row = evaluate_e2e_case(
            case, service, Mock(), Mock(), run_id="run1", data_version="data1",
        )
        self.assertTrue(row["behavior_correct"])
        self.assertIsNone(row["result_correct"])
        self.assertEqual(row["response_analysis"], "可以查询数据。")
        self.assertEqual(row["route_reason"], "普通问候")
        self.assertEqual(row["direct_response_type"], "answer")
        service.submit.return_value.analysis = ""
        self.assertFalse(evaluate_e2e_case(
            case, service, Mock(), Mock(), run_id="run1", data_version="data1",
        )["behavior_correct"])

    def test_data_qa_uses_the_prior_query_session(self) -> None:
        case = next(case for case in load_e2e_cases(
            Path(__file__).resolve().parents[1] / "evaluation/cases/e2e_behavior.json"
        ) if case["case_id"] == "E2E-ROUTE-QA")
        service = Mock()
        service.submit.return_value = QueryResult(
            task_id="task2", status="completed", route="data_qa",
            message="analysis", analysis="上一轮结果说明。",
        )
        row = evaluate_e2e_case(
            case, service, Mock(), Mock(), run_id="run1", data_version="data1",
        )
        self.assertTrue(row["behavior_correct"])
        self.assertIsNone(row["result_correct"])
        service.submit.assert_called_once_with(
            case["query"], "evaluation-run1-growth_context", user_id="demo_growth_ops",
        )

    def test_clarification_start_requires_options(self) -> None:
        case = next(case for case in load_e2e_cases(
            Path(__file__).resolve().parents[1] / "evaluation/cases/e2e_behavior.json"
        ) if case["case_id"] == "E2E-CLARIFY-START")
        service = Mock()
        service.submit.return_value = QueryResult(
            task_id="task1", status="waiting_clarification",
            route="database_query", message="choose",
            clarification=Clarification(
                parameter="metric", question="选择指标", reason="指标不明确",
                options=[{"id": "clicks", "label": "点击量", "description": "按点击量"},
                         {"id": "impressions", "label": "曝光量", "description": "按曝光量"}],
            ),
        )
        row = evaluate_e2e_case(
            case, service, Mock(), Mock(), run_id="run1", data_version="data1",
        )
        self.assertTrue(row["behavior_correct"])
        self.assertEqual(len(row["trace"]["clarification"]["options"]), 2)
        self.assertIsNone(row["result_correct"])

    def test_manifest_selects_real_cases_without_retrieval_hints_in_service_call(self) -> None:
        cases = load_e2e_cases(
            Path(__file__).resolve().parents[1] / "evaluation/cases/e2e_smoke.json"
        )
        self.assertEqual(len(cases), 3)
        self.assertEqual(len({case["case_id"] for case in cases}), 3)

    def test_completed_query_is_scored_from_service_output(self) -> None:
        case = {
            "case_id": "A", "scenario": "growth_ops", "query": "count users",
            "gold_sql": "SELECT count(*) AS users FROM users",
            "order_sensitive": False, "expected_route": "database_query",
            "expected_status": "completed",
        }
        result = SimpleNamespace(
            task_id="task1", route="database_query", status="completed",
            sql="SELECT count(*) AS users FROM users",
            columns=["users"], rows=[{"users": 2}],
            execution_log=[], tool_calls=[], clarification=None,
        )
        service = Mock()
        service.submit.return_value = result
        engine = Mock()
        engine.execute.return_value = SimpleNamespace(
            success=True, columns=["users"], rows=[{"users": 2}],
            execution_ms=1.0, truncated=False, error=None,
        )
        scope = Mock()
        scope.public.return_value = {"allowed_tables": ["users"]}
        controller = Mock()
        controller.resolve.return_value = scope
        with tempfile.TemporaryDirectory() as directory:
            row = evaluate_e2e_case(
                case, service, engine, controller, run_id="run1",
                data_version="data1", gold_cache_dir=Path(directory),
            )
        self.assertTrue(row["behavior_correct"])
        self.assertTrue(row["result_correct"])
        self.assertTrue(row["strict_result_correct"])
        self.assertEqual(row["trace_id"], "run1:A")
        service.submit.assert_called_once_with(
            "count users", "evaluation-run1-A", user_id="demo_growth_ops",
        )
        self.assertEqual(summarize_e2e([row])["strict_result_accuracy"], 1.0)

    def test_waiting_clarification_is_not_counted_as_sql_failure(self) -> None:
        case = {
            "case_id": "A", "scenario": "growth_ops", "query": "active users",
            "expected_route": "database_query",
            "expected_status": "waiting_clarification",
        }
        service = Mock()
        service.submit.return_value = SimpleNamespace(
            task_id="task1", route="database_query", status="waiting_clarification",
            sql=None, execution_log=[], tool_calls=[], clarification=None,
        )
        row = evaluate_e2e_case(
            case, service, Mock(), Mock(), run_id="run1", data_version="data1",
        )
        self.assertTrue(row["behavior_correct"])
        self.assertIsNone(row["result_correct"])
        self.assertEqual(summarize_e2e([row])["result_scored_count"], 0)

    def test_scoring_failure_does_not_erase_successful_service_behavior(self) -> None:
        case = {
            "case_id": "A", "scenario": "growth_ops", "query": "count users",
            "gold_sql": "SELECT 1", "expected_route": "database_query",
            "expected_status": "completed",
        }
        service = Mock()
        service.submit.return_value = SimpleNamespace(
            task_id="task1", route="database_query", status="completed",
            sql="SELECT 1", columns=["one"], rows=[{"one": 1}],
            execution_log=[], tool_calls=[], clarification=None,
        )
        controller = Mock()
        controller.resolve.side_effect = RuntimeError("gold scope unavailable")
        row = evaluate_e2e_case(
            case, service, Mock(), controller, run_id="run1", data_version="data1",
        )
        self.assertTrue(row["behavior_correct"])
        self.assertTrue(row["sql_execution_success"])
        self.assertIsNone(row["result_correct"])
        self.assertEqual(row["error_stage"], "result_scoring")

    def test_truncated_service_preview_is_reexecuted_for_scoring(self) -> None:
        case = {
            "case_id": "A", "scenario": "growth_ops", "query": "count users",
            "gold_sql": "SELECT 2 AS users", "expected_route": "database_query",
            "expected_status": "completed",
        }
        service = Mock()
        service.submit.return_value = SimpleNamespace(
            task_id="task1", route="database_query", status="completed",
            sql="SELECT 2 AS users", columns=["users"], rows=[{"users": 1}],
            truncated=True, execution_log=[], tool_calls=[], clarification=None,
        )
        engine = Mock()
        engine.execute.return_value = SimpleNamespace(
            success=True, columns=["users"], rows=[{"users": 2}],
            execution_ms=1.0, truncated=False, error=None,
        )
        controller = Mock()
        controller.resolve.return_value.public.return_value = {}
        with tempfile.TemporaryDirectory() as directory:
            row = evaluate_e2e_case(
                case, service, engine, controller, run_id="run1",
                data_version="data1", gold_cache_dir=Path(directory),
            )
        self.assertTrue(row["scoring_reexecuted"])
        self.assertTrue(row["result_correct"])
        self.assertEqual(engine.execute.call_count, 2)

    def test_cross_user_task_access_must_raise_permission_error(self) -> None:
        case = {
            "case_id": "E2E-PERMISSION-READ", "scenario": "content_ops",
            "query": "read another user's task", "operation": "get_task_denied",
            "source_case_id": "GROWTH_OPS-001", "user_id": "demo_content_ops",
            "behavior_type": "permission_denial",
        }
        prior = {"GROWTH_OPS-001": {"task_id": "task1"}}
        service = Mock()
        service.get_task.side_effect = PermissionError("denied")
        row = evaluate_e2e_case(
            case, service, Mock(), Mock(), run_id="run1", data_version="data1",
            prior_results=prior,
        )
        self.assertTrue(row["behavior_correct"])
        self.assertEqual(row["observed_exception"], "PermissionError")
        service.get_task.assert_called_once_with("task1", user_id="demo_content_ops")
        service.get_task.side_effect = None
        self.assertFalse(evaluate_e2e_case(
            case, service, Mock(), Mock(), run_id="run1", data_version="data1",
            prior_results=prior,
        )["behavior_correct"])

    def test_clarification_resume_uses_real_option_from_prior_response(self) -> None:
        case = {
            "case_id": "E2E-CLARIFY-RESUME", "scenario": "channel_ops",
            "query": "choose option", "operation": "clarify",
            "source_case_id": "E2E-CLARIFY-START",
            "clarification_option_index": 0,
            "expected_route": "database_query", "expected_status": "completed",
            "expected_sql_present": True, "score_result": False,
            "behavior_type": "clarification_recovery",
        }
        prior = {"E2E-CLARIFY-START": {
            "task_id": "task1", "status": "waiting_clarification",
            "trace": {"clarification": {"options": [{"id": "clicks", "label": "点击量"}]}},
        }}
        service = Mock()
        service.clarify.return_value = QueryResult(
            task_id="task1", status="completed", route="database_query",
            message="done", sql="SELECT 1 AS clicks", columns=["clicks"],
            rows=[{"clicks": 1}], tool_calls=[{"success": True}],
            standalone_query="按已确认的点击量查询",
            schema_graph={"tables": [{"name": "channels"}], "fields": []},
            execution_log=[{"stage": "clarification_resolved", "success": True,
                            "label": "点击量", "option_id": "clicks"}],
        )
        row = evaluate_e2e_case(
            case, service, Mock(), Mock(), run_id="run1", data_version="data1",
            prior_results=prior,
        )
        self.assertTrue(row["behavior_correct"])
        self.assertIsNone(row["result_correct"])
        self.assertEqual(row["selected_clarification_option_id"], "clicks")
        self.assertEqual(row["selected_clarification_option"]["label"], "点击量")
        self.assertIn("点击量", row["standalone_query"])
        self.assertEqual(row["trace"]["schema_graph"]["tables"][0]["name"], "channels")
        self.assertEqual(row["trace"]["execution_log"][0]["label"], "点击量")
        service.clarify.assert_called_once_with("task1", "clicks", user_id="demo_channel_ops")

    def test_empty_result_gold_is_really_empty_and_behavior_checks_rows(self) -> None:
        case = next(case for case in load_e2e_cases(
            Path(__file__).resolve().parents[1] / "evaluation/cases/e2e_behavior.json"
        ) if case["case_id"] == "E2E-EMPTY-RESULT")
        controller = AccessController()
        gold = DuckDbEngine().execute(
            "short_video_ops", case["gold_sql"],
            controller.resolve("demo_growth_ops"),
        )
        self.assertTrue(gold.success, gold.error)
        self.assertEqual(gold.rows, [])
        service = Mock()
        service.submit.return_value = QueryResult(
            task_id="task1", status="completed", route="database_query",
            message="done", sql=case["gold_sql"], columns=gold.columns, rows=[],
            tool_calls=[{"success": True}],
        )
        with tempfile.TemporaryDirectory() as directory:
            row = evaluate_e2e_case(
                case, service, DuckDbEngine(), controller,
                run_id="run1", data_version="data1",
                gold_cache_dir=Path(directory),
            )
        self.assertTrue(row["behavior_correct"])
        self.assertTrue(row["result_correct"])
        self.assertTrue(row["strict_result_correct"])
        service.submit.return_value.tool_calls = []
        with tempfile.TemporaryDirectory() as directory:
            unexecuted = evaluate_e2e_case(
                case, service, DuckDbEngine(), controller,
                run_id="run1", data_version="data1",
                gold_cache_dir=Path(directory),
            )
        self.assertFalse(unexecuted["behavior_correct"])
        self.assertFalse(unexecuted["behavior_checks"]["tool_success"])

    def test_controlled_workflow_failure_is_reported_as_behavior(self) -> None:
        case = next(case for case in load_e2e_cases(
            Path(__file__).resolve().parents[1] / "evaluation/cases/e2e_behavior.json"
        ) if case["case_id"] == "E2E-FAILURE-PREPROCESS")
        service = Mock()

        def submit(_query, _session_id, *, user_id):
            try:
                service.workflow.invoke({}, "task1")
            except PipelineStageError as exc:
                return QueryResult(
                    task_id="task1", status="failed", route="database_query",
                    message="failed", workflow_mode="failed_explicitly",
                    execution_log=[{"stage": exc.stage, "success": False}],
                )
            raise AssertionError("Expected injected failure")

        service.submit.side_effect = submit
        row = evaluate_e2e_case(
            case, service, Mock(), Mock(), run_id="run1", data_version="data1",
        )
        self.assertTrue(row["behavior_correct"])
        self.assertEqual(row["behavior_checks"]["failure_stage"], True)
        self.assertIsNone(row["result_correct"])
        self.assertEqual(summarize_e2e([row])["behavior_by_type"],
                         {"controlled_failure": {"count": 1, "passed": 1}})


if __name__ == "__main__":
    unittest.main()
