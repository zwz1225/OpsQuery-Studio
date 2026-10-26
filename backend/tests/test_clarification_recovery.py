from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import Mock

from app.database import SCHEMA
from app.errors import PipelineStageError
from app.querying.single_database_agent import SingleDatabaseAgent
from app.skills import SkillDefinition
from app.workflows.clarification import apply_clarification_choice


QUERY = "请找出2026年5月表现最好的日期；如果表现没有明确指标，请先让我选择指标。"
CLARIFICATION = {
    "parameter": "表现指标", "question": "按哪个指标衡量？",
    "reason": "排序依据不同", "options": [
        {"id": "option_1", "label": "新增用户数", "description": "按2026年5月新增用户数降序排列"},
        {"id": "option_2", "label": "成本", "description": "按成本升序排列"},
    ],
}
GRAPH = {"tables": [{"name": "growth_daily_metrics", "id": "short_video_ops.growth_daily_metrics",
                      "database": "short_video_ops"}], "fields": []}
SQL = ("SELECT metric_date, SUM(new_users) AS new_users FROM growth_daily_metrics "
       "WHERE metric_date >= '2026-05-01' AND metric_date < '2026-06-01' "
       "GROUP BY metric_date ORDER BY new_users DESC")


def state() -> dict:
    return {"standalone_query": QUERY, "clarification": copy.deepcopy(CLARIFICATION),
            "workspace": {}, "extraction": {"retrieval_terms": ["表现", "日期"]}}


def make_agent(decisions: list[dict]):
    model, mcp = Mock(), Mock()
    model.chat_json.side_effect = decisions
    mcp.list_tools.return_value = [{"name": "query_short_video_ops"}]
    mcp.call_tool.return_value = {"success": True, "sql": SQL,
                                  "columns": ["metric_date", "new_users"], "rows": []}
    skill = SkillDefinition(name="database_query", description="", instructions="",
                            allowed_tools=("query_*",), max_tool_calls=3,
                            output_actions=("call_tool", "clarify"))
    return SingleDatabaseAgent(model, lambda scope: mcp, skill), model, mcp


def call_decision(sql: str = SQL) -> dict:
    return {"action": "call_tool", "tool_name": "query_short_video_ops",
            "arguments": {"sql": sql}, "query_contract": {}}


class ClarificationRecoveryTest(unittest.TestCase):
    def test_choice_reaches_model_and_metric_planner_and_blocks_repeat_question(self):
        original = state()
        resumed = apply_clarification_choice(original, {"option_id": "option_1"})
        repeat = {"action": "clarify", "clarification": copy.deepcopy(CLARIFICATION)}
        agent, model, mcp = make_agent([repeat, call_decision()])
        result = agent.prepare(resumed["standalone_query"], "short_video_ops", GRAPH,
                               "", {}, resumed["workspace"], {})
        payload = json.loads(model.chat_json.call_args_list[0].args[1])
        self.assertEqual(payload["confirmed_clarifications"]["表现指标"]["label"], "新增用户数")
        self.assertIn("new_users", [m["name"] for m in payload["metric_plan"]["metrics"]])
        self.assertIn("新增用户数", resumed["extraction"]["retrieval_terms"])
        self.assertIn("降序排列", resumed["standalone_query"])
        self.assertIn("已确认", json.loads(model.chat_json.call_args_list[1].args[1])["output_validation_error"])
        self.assertEqual(result["action"], "executed")
        self.assertEqual(mcp.call_tool.call_count, 1)
        self.assertEqual(original, state())

    def test_repeated_question_exhaustion_stops_without_tool_call(self):
        resumed = apply_clarification_choice(state(), {"option_id": "option_1"})
        agent, _, mcp = make_agent([{"action": "clarify", "clarification": copy.deepcopy(CLARIFICATION)}
                                    for _ in range(3)])
        with self.assertRaises(PipelineStageError):
            agent.prepare(resumed["standalone_query"], "short_video_ops", GRAPH,
                          "", {}, resumed["workspace"], {})
        mcp.call_tool.assert_not_called()

    def test_unknown_option_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_clarification_choice(state(), {"option_id": "unknown"})

    def test_multiple_answers_accumulate_without_repeating_original_query(self):
        first = apply_clarification_choice(state(), {"option_id": "option_1"})
        second_state = {**state(), **first, "clarification": {
            "parameter": "数量", "question": "返回多少行？",
            "options": [{"id": "top_5", "label": "前5行", "description": "返回前5行"}],
        }}
        second = apply_clarification_choice(second_state, {"option_id": "top_5"})
        self.assertEqual(second["standalone_query"].count(QUERY), 1)
        self.assertIn("新增用户数", second["standalone_query"])
        self.assertIn("返回前5行", second["standalone_query"])
        self.assertEqual(len(second["execution_log"]), 2)

    def test_schema_table_option_remains_confirmed(self):
        table_id = SCHEMA[0]["id"]
        value = {**state(), "clarification": {"parameter": "表", "options": [
            {"id": table_id, "label": SCHEMA[0]["label"], "description": "指定数据表"}]}}
        result = apply_clarification_choice(value, {"option_id": table_id})
        self.assertIn(table_id, result["workspace"]["confirmed_schema_tables"])


try:
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command
    from app.workflows.query_graph import QueryWorkflow
except ModuleNotFoundError as exc:
    if exc.name not in {"langgraph", "mcp"}:
        raise
    QueryWorkflow = None


@unittest.skipIf(QueryWorkflow is None, "LangGraph/MCP requires the server environment")
class WorkflowClarificationIntegrationTest(unittest.TestCase):
    def test_interrupt_resume_finishes_same_task_with_selection_in_trace(self):
        from types import SimpleNamespace
        workflow = QueryWorkflow.__new__(QueryWorkflow)
        from app.datasources import create_datasource_runtime
        workflow.runtime = create_datasource_runtime()
        self.addCleanup(workflow.runtime.close)
        workflow.preprocessor = Mock()
        workflow.preprocessor.prepare.return_value = SimpleNamespace(
            source="model", action="database_query", confidence=1.0, reason="问数",
            response_type="answer", response="", standalone_query=QUERY,
            rewritten=False, retrieval=SimpleNamespace(public=lambda: {"retrieval_terms": []}),
        )
        workflow.schema_index = Mock()
        workflow.schema_index.retrieve.return_value = {"hits": []}
        workflow.schema_index.include_workspace.side_effect = lambda retrieval, workspace, scope: retrieval
        workflow.graph_builder = Mock()
        workflow.graph_builder.build.return_value = GRAPH
        workflow.graph_builder.context_text.return_value = "schema"
        workflow.time_field_policy = None
        workflow.single_database_agent, model, _ = make_agent([
            {"action": "clarify", "clarification": copy.deepcopy(CLARIFICATION)}, call_decision(),
        ])
        workflow.response_generator = Mock()
        workflow.response_generator.finalize.return_value = {"valid": True, "analysis": "done"}
        workflow.checkpointer = InMemorySaver()
        workflow.graph = workflow._compile()
        first = workflow.invoke({"task_id": "task1", "query": QUERY, "workspace": {}}, "task1")
        self.assertEqual(first.status, "waiting_clarification")
        result = workflow.invoke(Command(resume={"option_id": "option_1"}), "task1")
        self.assertEqual((result.task_id, result.status), ("task1", "completed"))
        self.assertIn("新增用户数", result.standalone_query)
        self.assertEqual(result.execution_log[0]["stage"], "clarification_resolved")
        self.assertIn("新增用户数", workflow.schema_index.retrieve.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
