from __future__ import annotations

import json
import unittest

from evaluation.models import EvaluationResult
from evaluation.trace import EvaluationTrace


class EvaluationTraceTest(unittest.TestCase):
    def test_trace_can_be_created_with_defaults(self) -> None:
        trace = EvaluationTrace()

        self.assertEqual(trace.request, {})
        self.assertEqual(trace.tool_calls, [])
        self.assertEqual(trace.errors, [])
        self.assertEqual(trace.permission, {})
        self.assertEqual(trace.clarification, {})

    def test_trace_defaults_are_isolated(self) -> None:
        first = EvaluationTrace()
        second = EvaluationTrace()

        first.tool_calls.append({"tool_name": "query_short_video_ops"})
        first.errors.append({"stage": "test"})

        self.assertEqual(second.tool_calls, [])
        self.assertEqual(second.errors, [])

    def test_trace_serializes_to_json_compatible_dict(self) -> None:
        trace = EvaluationTrace(
            request={"case_id": "CASE-001", "question": "查询用户数", "query_type": "汇总"},
            routing={"route": None},
            permission={"checked": True, "user_id": "demo_growth_ops"},
            clarification={"triggered": True, "option_count": 2},
            schema_retrieval={"recall": 1.0, "precision": 0.5, "latency_ms": 8.2},
            agent_decision={"action": "execute_sql", "clarification_required": False},
            tool_calls=[{"tool_name": "query_short_video_ops", "success": True}],
            sql_execution={"generated_sql": "SELECT 1", "success": True, "execution_ms": 2.1},
            result_comparison={"comparison_target": "gold_result", "correct": True},
        )

        payload = trace.to_dict()

        self.assertEqual(payload["request"]["case_id"], "CASE-001")
        self.assertTrue(payload["permission"]["checked"])
        self.assertTrue(payload["clarification"]["triggered"])
        self.assertEqual(payload["tool_calls"][0]["tool_name"], "query_short_video_ops")
        json.dumps(payload, ensure_ascii=False)

    def test_evaluation_result_serializes_trace_without_losing_legacy_fields(self) -> None:
        trace = EvaluationTrace(
            request={"case_id": "CASE-001"},
            result_comparison={"comparison_target": "gold_result", "correct": True},
        )
        result = EvaluationResult(
            case_id="CASE-001",
            question="查询用户数",
            scenario="growth_ops",
            category="趋势汇总",
            query_type="时间趋势",
            difficulty="简单",
            classic=True,
            trace=trace,
            result_metrics={"correct": True, "column_match": True, "reason": "结果一致"},
        )

        payload = result.to_dict()

        self.assertEqual(payload["trace"]["request"]["case_id"], "CASE-001")
        self.assertTrue(payload["result_correct"])
        self.assertEqual(payload["comparison_reason"], "结果一致")


if __name__ == "__main__":
    unittest.main()
