from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from app.retrieval.service import SchemaIndex
from app.datasources.contracts import SourceIdentity
from app.security.access_control import AccessScope
from evaluation.retrieval_diagnosis import _stage_metrics, diagnose_case, summarize_diagnosis


class FakeDocument:
    def __init__(self, name: str, table: str = "t") -> None:
        self.doc_id = f"db.{table}.{name}"
        self.database_id = "db"
        self.table_id = table
        self.table_label = table
        self.field_name = name
        self.field_label = name
        self.rerank_text = name

    def public(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "database_id": self.database_id,
            "table_id": self.table_id,
            "table_label": self.table_label,
            "field_name": self.field_name,
            "field_label": self.field_label,
        }


class FakeStore:
    signature = "test-version"

    def __init__(self) -> None:
        self.documents = [FakeDocument("a"), FakeDocument("b"), FakeDocument("c", "other")]

    def active_documents(self) -> list[FakeDocument]:
        return self.documents

    def bm25_search(self, query: str, top_k: int, allowed_doc_ids: set[str] | None):
        assert allowed_doc_ids is None or self.documents[0].doc_id in allowed_doc_ids
        return [(0, 1.0), (1, 0.5)]

    def dense_search(self, vector: list[float], top_k: int, allowed_doc_ids: set[str] | None):
        assert vector == [1.0]
        return [(1, 0.9), (0, 0.7)]


class FakeModel:
    def __init__(self) -> None:
        self.embed_count = 0
        self.rerank_count = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.embed_count += 1
        return [[1.0]]

    def rerank(self, query: str, texts: list[str], top_n: int):
        self.rerank_count += 1
        return [(0, 0.9), (1, 0.7)]


def make_index() -> SchemaIndex:
    index = SchemaIndex.__new__(SchemaIndex)
    index.store = FakeStore()
    index.model_client = FakeModel()
    index.embedding_source = "test-embedding"
    index.config = SimpleNamespace(
        bm25_top_k=3,
        dense_top_k=3,
        rrf_top_k=3,
        rerank_model="test-rerank",
        schema_recall_threshold=0.55,
        max_schema_fields=2,
        embedding_model="test-embedding",
        embedding_dimensions=1,
    )
    index.runtime = SimpleNamespace(identity=SourceIdentity(
        "db", "fixture_duckdb", "duckdb", "duckdb", "DuckDB", "main", "1"*64, "2"*64))
    index.ensure_built = lambda: None
    return index


class RetrievalDiagnosisTest(unittest.TestCase):
    def test_diagnostics_preserve_retrieval_result_and_model_calls(self) -> None:
        index = make_index()
        scope = AccessScope("tester", (), frozenset({"db"}), frozenset({"t"}))
        args = {"retrieval_terms": ["a"], "access_scope": scope}
        ordinary = index.retrieve("a", **args)
        diagnosed = index.retrieve("a", include_diagnostics=True, **args)

        self.assertEqual(ordinary, {key: value for key, value in diagnosed.items() if key != "diagnostics"})
        self.assertEqual((index.model_client.embed_count, index.model_client.rerank_count), (2, 2))
        stages = diagnosed["diagnostics"]["stages"]
        self.assertEqual([item["doc_id"] for item in stages["bm25"]["candidates"]], ["db.t.a", "db.t.b"])
        self.assertEqual([item["doc_id"] for item in stages["dense"]["candidates"]], ["db.t.b", "db.t.a"])
        self.assertEqual([item["doc_id"] for item in stages["final"]["candidates"]], ["db.t.a", "db.t.b"])
        self.assertEqual(diagnosed["diagnostics"]["candidate_document_count"], 2)
        self.assertGreaterEqual(diagnosed["diagnostics"]["total_latency_ms"], 0)
        json.dumps(diagnosed["diagnostics"])

    def test_no_permission_returns_empty_stages_without_model_calls(self) -> None:
        index = make_index()
        scope = AccessScope("tester", (), frozenset({"db"}), frozenset())
        diagnosed = index.retrieve("a", retrieval_terms=["a"], access_scope=scope, include_diagnostics=True)
        self.assertEqual(diagnosed["hits"], [])
        self.assertTrue(all(stage["count"] == 0 for stage in diagnosed["diagnostics"]["stages"].values()))
        self.assertEqual(index.model_client.embed_count, 0)
        self.assertEqual(index.model_client.rerank_count, 0)

    def test_stage_metrics_include_cutoffs(self) -> None:
        candidates = [{"doc_id": f"f{i}"} for i in range(12)]
        metrics = _stage_metrics(candidates, ["f0", "f11"])
        self.assertEqual(metrics["recall"], 1.0)
        self.assertEqual(metrics["precision"], 2 / 12)
        self.assertEqual(metrics["at_k"]["5"]["recall"], 0.5)
        self.assertEqual(metrics["at_k"]["20"]["recall"], 1.0)
        self.assertEqual(metrics["missing_gold_fields"], [])

    def test_case_records_graph_expansion_and_stage_metrics(self) -> None:
        index = make_index()
        scope = AccessScope("tester", (), frozenset({"db"}), frozenset({"t"}))
        controller = SimpleNamespace(resolve=lambda user_id: scope)

        class Graph:
            def build(self, hits, access_scope):
                self.assert_scope = access_scope
                return {
                    "fields": [{"id": hit["doc_id"]} for hit in hits] + [{"id": "db.t.join_key"}],
                    "tables": [{"id": "t"}, {"id": "join_table"}],
                }

            def context_text(self, graph):
                return "context"

        graph = Graph()
        case = {
            "case_id": "C-1", "scenario": "growth_ops", "query": "a",
            "retrieval_terms": ["a"], "gold_fields": ["db.t.a"],
        }
        result = diagnose_case(case, index, graph, controller)
        self.assertIs(graph.assert_scope, scope)
        self.assertEqual(result["retrieval"]["stages"]["final"]["metrics"]["recall"], 1.0)
        self.assertEqual(result["graph"]["added_relation_fields"], ["db.t.join_key"])
        self.assertEqual(result["graph"]["added_relation_tables"], ["join_table"])
        self.assertEqual(result["graph"]["metrics"]["recall"], 1.0)

    def test_summary_handles_empty_and_failed_cases(self) -> None:
        empty = summarize_diagnosis([])
        self.assertEqual(empty["case_count"], 0)
        self.assertIsNone(empty["average_total_latency_ms"])
        failed = summarize_diagnosis([{"case_id": "C-1", "error": "failed"}])
        self.assertEqual(failed["error_count"], 1)
        self.assertEqual(failed["successful_retrieval_count"], 0)


if __name__ == "__main__":
    unittest.main()
