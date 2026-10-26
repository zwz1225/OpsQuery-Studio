from __future__ import annotations

import unittest
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from app.retrieval import SchemaGraphBuilder, SchemaIndex, TimeFieldPolicy
from app.security import AccessController, AccessScope


DB = "short_video_ops"
TABLE = f"{DB}.growth_daily_metrics"
METRIC = f"{TABLE}.new_users"
TIME_FIELD = f"{TABLE}.metric_date"


class FakeDocument:
    doc_id = TIME_FIELD
    database_id = DB
    table_id = TABLE

    def public(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "database_id": self.database_id,
            "table_id": self.table_id,
            "table_label": "Growth daily metrics",
            "field_name": "metric_date",
            "field_label": "Metric date",
            "field_type": "DATE",
            "field_description": "Metric date",
            "field_role": "time",
        }


def metric_hit(name: str = "new_users") -> dict:
    return {
        "doc_id": f"{TABLE}.{name}",
        "database_id": DB,
        "table_id": TABLE,
        "table_label": "Growth daily metrics",
        "field_name": name,
        "field_label": name,
        "field_type": "BIGINT",
        "field_description": name,
        "field_role": "metric",
        "score": 0.8,
    }


class TimeFieldSupplementTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scope = AccessController().resolve("demo_growth_ops")
        self.index = SchemaIndex.__new__(SchemaIndex)
        self.index.store = SimpleNamespace(get=lambda doc_id: FakeDocument() if doc_id == TIME_FIELD else None)

    def test_policy_and_materialization_add_field_before_graph(self) -> None:
        proposal = TimeFieldPolicy().propose(
            "查询2026年每个月的新增用户数", [METRIC], self.scope
        )
        self.assertEqual(proposal["proposals"], [{"doc_id": TIME_FIELD, "reason": "metric:new_users"}])
        retrieval = {"hits": [metric_hit()], "selected_count": 1}
        updated = self.index.include_time_fields(retrieval, proposal["proposals"], self.scope)
        self.assertEqual([hit["doc_id"] for hit in updated["hits"]], [METRIC, TIME_FIELD])
        self.assertEqual(updated["hits"][1]["source"], "time_field_supplement")
        self.assertEqual(updated["selected_count"], 2)
        graph = SchemaGraphBuilder().build(updated["hits"], self.scope)
        self.assertIn(TIME_FIELD, {field["id"] for field in graph["fields"]})

    def test_duplicate_and_no_time_request_add_nothing(self) -> None:
        policy = TimeFieldPolicy()
        self.assertEqual(policy.propose("查询新增用户数", [METRIC], self.scope)["proposals"], [])
        self.assertEqual(
            policy.propose("查询2026年每个月的新增用户数", [METRIC, TIME_FIELD], self.scope)["proposals"],
            [],
        )
        retrieval = {"hits": [metric_hit(), {**FakeDocument().public(), "score": 0.7}]}
        self.index.include_time_fields(retrieval, [{"doc_id": TIME_FIELD}], self.scope)
        self.assertEqual(len(retrieval["hits"]), 2)

    def test_permission_is_checked_in_policy_and_materializer(self) -> None:
        denied = AccessScope("denied", (), frozenset({DB}), frozenset())
        self.assertEqual(
            TimeFieldPolicy().propose("查询2026年每个月的新增用户数", [METRIC], denied)["proposals"],
            [],
        )
        retrieval = {"hits": [metric_hit()]}
        self.index.include_time_fields(retrieval, [{"doc_id": TIME_FIELD}], denied)
        self.assertEqual([hit["doc_id"] for hit in retrieval["hits"]], [METRIC])

    def test_limits_keep_ranked_hits_and_cap_explicit(self) -> None:
        ranked = [metric_hit(f"metric_{index}") for index in range(20)]
        retrieval = {"hits": ranked.copy()}
        self.index.include_time_fields(
            retrieval, [{"doc_id": TIME_FIELD, "reason": "test"}], self.scope,
            max_extra_fields=2, max_total_fields=21,
        )
        self.assertEqual([hit["doc_id"] for hit in retrieval["hits"][:20]], [hit["doc_id"] for hit in ranked])
        self.assertEqual(len(retrieval["hits"]), 21)
        self.assertEqual(retrieval["time_field_supplement"]["added_fields"][0]["doc_id"], TIME_FIELD)
        capped = {"hits": ranked.copy()}
        self.index.include_time_fields(capped, [{"doc_id": TIME_FIELD}], self.scope, max_total_fields=20)
        self.assertEqual(len(capped["hits"]), 20)

    def test_activation_rate_comparison_proposes_both_time_fields(self) -> None:
        cases_path = Path(__file__).resolve().parents[1] / "evaluation" / "cases" / "all_cases.jsonl"
        case = next(
            item for line in cases_path.read_text(encoding="utf-8").splitlines()
            if (item := json.loads(line))["case_id"] == "GROWTH_OPS-150"
        )
        selected = [
            "short_video_ops.user_registrations.registration_id",
            "short_video_ops.growth_targets.activation_rate_target",
            "short_video_ops.user_activations.is_activated",
        ]
        proposal = TimeFieldPolicy().propose(case["query"], selected, self.scope)
        self.assertEqual(
            [item["doc_id"] for item in proposal["proposals"]],
            [
                "short_video_ops.user_registrations.registered_at",
                "short_video_ops.growth_targets.target_month",
            ],
        )


try:
    from app.workflows.query_graph import QueryWorkflow
except ModuleNotFoundError as exc:
    if exc.name != "langgraph":
        raise
    QueryWorkflow = None


@unittest.skipIf(QueryWorkflow is None, "LangGraph is unavailable in this environment")
class WorkflowFlagTest(unittest.TestCase):
    def make_workflow(self, enabled: bool):
        workflow = QueryWorkflow.__new__(QueryWorkflow)
        workflow.schema_index = Mock()
        workflow.schema_index.retrieve.return_value = {"hits": [metric_hit()]}
        workflow.schema_index.include_workspace.side_effect = lambda retrieval, workspace, scope: retrieval
        workflow.schema_index.include_time_fields.side_effect = (
            lambda retrieval, proposals, scope, **kwargs: {**retrieval, "hits": retrieval["hits"] + [FakeDocument().public()], "time_field_supplement": {}}
        )
        workflow.graph_builder = Mock()
        workflow.graph_builder.build.side_effect = lambda hits, scope: {
            "tables": [{"database": DB}], "fields": [{"id": hit["doc_id"]} for hit in hits],
        }
        workflow.graph_builder.context_text.return_value = "schema"
        workflow.config = SimpleNamespace(
            time_field_supplement_max_extra_fields=2,
            time_field_supplement_max_total_fields=22,
        )
        workflow.time_field_policy = TimeFieldPolicy() if enabled else None
        return workflow

    def state(self) -> dict:
        return {
            "standalone_query": "查询2026年每个月的新增用户数",
            "extraction": {"retrieval_terms": ["新增用户数", "月份"]},
            "access_scope": AccessController().resolve("demo_growth_ops").public(),
            "workspace": {},
        }

    def test_disabled_flag_keeps_original_hits(self) -> None:
        workflow = self.make_workflow(False)
        result = workflow._retrieve_schema(self.state())
        workflow.schema_index.include_time_fields.assert_not_called()
        self.assertEqual([field["id"] for field in result["schema_graph"]["fields"]], [METRIC])

    def test_enabled_flag_adds_before_graph(self) -> None:
        workflow = self.make_workflow(True)
        result = workflow._retrieve_schema(self.state())
        workflow.schema_index.include_time_fields.assert_called_once()
        self.assertEqual([field["id"] for field in result["schema_graph"]["fields"]], [METRIC, TIME_FIELD])


if __name__ == "__main__":
    unittest.main()
