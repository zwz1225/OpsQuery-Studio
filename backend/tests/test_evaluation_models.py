from __future__ import annotations

import json
import unittest

from evaluation.models import EvaluationResult


class EvaluationResultTest(unittest.TestCase):
    def test_can_create_result_with_metric_groups(self) -> None:
        result = EvaluationResult(
            case_id="CASE-001",
            question="查询用户数",
            scenario="growth_ops",
            category="趋势汇总",
            query_type="时间趋势",
            difficulty="简单",
            classic=True,
            schema_metrics={"recall": 1.0, "precision": 0.5},
            sql_metrics={"generated_sql": "SELECT 1", "execution_success": True},
            result_metrics={"correct": True, "column_match": True, "reason": "结果一致"},
        )

        self.assertEqual(result.case_id, "CASE-001")
        self.assertEqual(result.schema_metrics["recall"], 1.0)
        self.assertTrue(result.result_metrics["correct"])

    def test_mutable_defaults_are_isolated(self) -> None:
        first = EvaluationResult(
            case_id="CASE-001",
            question="问题1",
            scenario="growth_ops",
            category="分类",
            query_type="类型",
            difficulty="简单",
            classic=True,
        )
        second = EvaluationResult(
            case_id="CASE-002",
            question="问题2",
            scenario="growth_ops",
            category="分类",
            query_type="类型",
            difficulty="简单",
            classic=False,
        )

        first.trace.tool_calls.append({"action": "executed"})
        self.assertEqual(second.trace.tool_calls, [])

    def test_to_dict_contains_nested_and_legacy_fields(self) -> None:
        result = EvaluationResult(
            case_id="CASE-001",
            question="查询用户数",
            scenario="growth_ops",
            category="趋势汇总",
            query_type="时间趋势",
            difficulty="简单",
            classic=True,
            schema_metrics={
                "recall": 1.0,
                "precision": 0.5,
                "retrieval_ms": 12.5,
                "retrieved_fields": ["users"],
                "gold_fields": ["users"],
            },
            sql_metrics={
                "generated_sql": "SELECT 1",
                "execution_success": True,
                "execution_ms": 3.2,
            },
            result_metrics={
                "correct": True,
                "column_match": True,
                "reason": "结果一致",
            },
            agent_metrics={"action": "executed"},
        )

        payload = result.to_dict()

        self.assertEqual(payload["schema_metrics"]["recall"], 1.0)
        self.assertEqual(payload["schema_recall"], 1.0)
        self.assertEqual(payload["generated_sql"], "SELECT 1")
        self.assertTrue(payload["result_correct"])
        self.assertEqual(payload["agent_action"], "executed")
        json.dumps(payload, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
