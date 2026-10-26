from __future__ import annotations

import copy
import unittest

from evaluation.error_taxonomy import ErrorCategory, ErrorClassifier
from evaluation.models import EvaluationResult
from evaluation.trace import EvaluationTrace


def failed_case(**overrides):
    row = {
        "result_correct": False,
        "sql_execution_success": False,
        "generated_sql": "",
        "errors": {},
        "trace": {},
    }
    row.update(overrides)
    return row


class ErrorClassifierTest(unittest.TestCase):
    def test_model_embedding_error_has_priority_over_schema_keyword(self) -> None:
        row = failed_case(error_stage="query_embedding", benchmark_error="模型调用失败")
        self.assertEqual(ErrorClassifier.classify(row), ErrorCategory.MODEL_ERROR)

    def test_schema_retrieval_error(self) -> None:
        row = failed_case(errors={"stage": "schema_rerank", "message": "reranker failed"})
        self.assertEqual(ErrorClassifier.classify(row), ErrorCategory.SCHEMA_RETRIEVAL_ERROR)

    def test_sql_execution_error(self) -> None:
        row = failed_case(generated_sql="SELECT 1", error_stage="sql_execution")
        self.assertEqual(ErrorClassifier.classify(row), ErrorCategory.SQL_EXECUTION_ERROR)

    def test_permission_signal_precedes_missing_sql(self) -> None:
        row = failed_case(trace={"permission": {"sql_blocked": True}})
        self.assertEqual(ErrorClassifier.classify(row), ErrorCategory.PERMISSION_ERROR)

    def test_mcp_failure_precedes_generic_execution_flag(self) -> None:
        row = failed_case(trace={"tool_calls": [{"tool_name": "query", "success": False}]})
        self.assertEqual(ErrorClassifier.classify(row), ErrorCategory.MCP_TOOL_ERROR)

    def test_unknown_error(self) -> None:
        row = failed_case(sql_execution_success=True, generated_sql="SELECT 1",
                          result_correct=True, error_stage="benchmark_worker",
                          benchmark_error="unexpected failure")
        self.assertEqual(ErrorClassifier.classify(row), ErrorCategory.UNKNOWN_ERROR)

    def test_generation_comparison_clarification_and_timeout(self) -> None:
        self.assertEqual(ErrorClassifier.classify(failed_case()), ErrorCategory.SQL_GENERATION_ERROR)
        self.assertEqual(ErrorClassifier.classify(failed_case(
            sql_execution_success=True, generated_sql="SELECT 1",
        )), ErrorCategory.RESULT_COMPARISON_ERROR)
        self.assertEqual(ErrorClassifier.classify(failed_case(
            trace={"clarification": {"triggered": True, "final_status": "error"}},
        )), ErrorCategory.CLARIFICATION_ERROR)
        self.assertEqual(ErrorClassifier.classify(failed_case(
            benchmark_error="request timed out",
        )), ErrorCategory.TIMEOUT_ERROR)

    def test_trace_errors_and_evaluation_result_are_supported_without_mutation(self) -> None:
        result = EvaluationResult(
            case_id="CASE-001", question="question", scenario="growth_ops",
            category="trend", query_type="ranking", difficulty="easy", classic=True,
            sql_metrics={"generated_sql": "", "execution_success": False},
            result_metrics={"correct": False},
            trace=EvaluationTrace(errors=[{"stage": "schema_retrieval", "message": "empty graph"}]),
        )
        original = copy.deepcopy(result.to_dict())
        self.assertEqual(ErrorClassifier.classify(result), ErrorCategory.SCHEMA_RETRIEVAL_ERROR)
        self.assertEqual(result.to_dict(), original)

    def test_success_is_not_classified(self) -> None:
        row = failed_case(sql_execution_success=True, generated_sql="SELECT 1", result_correct=True)
        self.assertIsNone(ErrorClassifier.classify(row))

    def test_metrics_fallback_and_waiting_clarification(self) -> None:
        self.assertEqual(ErrorClassifier.classify(failed_case(
            agent_metrics={"tool_failure_rate": 0.5},
        )), ErrorCategory.MCP_TOOL_ERROR)
        self.assertEqual(ErrorClassifier.classify(failed_case(
            agent_metrics={"permission_denied_count": 1},
        )), ErrorCategory.PERMISSION_ERROR)
        self.assertEqual(ErrorClassifier.classify(failed_case(
            trace={"clarification": {"triggered": True, "final_status": "waiting_clarification"}},
        )), ErrorCategory.CLARIFICATION_ERROR)

    def test_gold_result_without_comparison_target_is_unscored(self) -> None:
        row = failed_case(sql_execution_success=True, generated_sql="SELECT 1",
                          agent_action="gold_sql", comparison_target="none")
        self.assertIsNone(ErrorClassifier.classify(row))


if __name__ == "__main__":
    unittest.main()
