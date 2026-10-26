"""Read-only Schema retrieval diagnosis without running the SQL agent."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import BASE_DIR, settings
from app.errors import PipelineStageError
from app.model_client import ModelClient
from app.retrieval import SchemaGraphBuilder, SchemaIndex
from app.security import AccessController

from .case_selection import load_case_ids, select_cases

CASES_PATH = BASE_DIR / "evaluation" / "cases" / "all_cases.jsonl"
RESULT_DIR = BASE_DIR / "evaluation" / "results"


def _load_cases(scope: str) -> list[dict[str, Any]]:
    cases = [
        json.loads(line)
        for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [case for case in cases if case.get("classic")] if scope == "classic" else cases


def _stage_metrics(candidates: list[dict[str, Any]], gold_fields: list[str]) -> dict[str, Any]:
    ids = [str(item["doc_id"]) for item in candidates]
    def coverage(retrieved: list[str]) -> tuple[float, float, int]:
        retrieved_set = set(retrieved)
        expected_set = set(gold_fields)
        true_positive = len(retrieved_set & expected_set)
        recall = true_positive / len(expected_set) if expected_set else 1.0
        precision = true_positive / len(retrieved_set) if retrieved_set else 0.0
        return recall, precision, true_positive

    recall, precision, true_positive = coverage(ids)
    cutoffs = {}
    for size in (5, 10, 20):
        recall_at_k, precision_at_k, _ = coverage(ids[:size])
        cutoffs[str(size)] = {"recall": recall_at_k, "precision": precision_at_k}
    return {
        "recall": recall,
        "precision": precision,
        "true_positive": true_positive,
        "missing_gold_fields": sorted(set(gold_fields) - set(ids)),
        "at_k": cutoffs,
    }


def diagnose_case(
    case: dict[str, Any],
    schema_index: SchemaIndex,
    graph_builder: SchemaGraphBuilder,
    controller: AccessController,
) -> dict[str, Any]:
    """Capture existing ranking stages using the benchmark's role and terms."""
    scope = controller.resolve(f"demo_{case['scenario']}")
    retrieval = schema_index.retrieve(
        case["query"],
        retrieval_terms=case["retrieval_terms"],
        access_scope=scope,
        include_diagnostics=True,
    )
    diagnostics = retrieval["diagnostics"]
    gold_fields = list(case["gold_fields"])
    stages = {
        name: {
            **stage,
            "metrics": _stage_metrics(stage["candidates"], gold_fields),
        }
        for name, stage in diagnostics["stages"].items()
    }

    graph = graph_builder.build(retrieval["hits"], scope)
    hit_ids = {str(hit["doc_id"]) for hit in retrieval["hits"]}
    selected_tables = {str(hit["table_id"]) for hit in retrieval["hits"]}
    added_fields = [
        str(field["id"])
        for field in graph["fields"]
        if str(field["id"]) not in hit_ids
    ]
    added_tables = [
        str(table["id"])
        for table in graph["tables"]
        if str(table["id"]) not in selected_tables
    ]
    return {
        "case_id": case["case_id"],
        "scenario": case["scenario"],
        "category": case.get("category"),
        "query_type": case.get("query_type"),
        "difficulty": case.get("difficulty"),
        "query": case["query"],
        "gold_fields": gold_fields,
        "retrieval": {
            "retrieval_terms": diagnostics["retrieval_terms"],
            "index_version": diagnostics["index_version"],
            "embedding_model": diagnostics["embedding_model"],
            "rerank_model": diagnostics["rerank_model"],
            "candidate_document_count": diagnostics["candidate_document_count"],
            "config": diagnostics["config"],
            "timings_ms": diagnostics["timings_ms"],
            "total_latency_ms": diagnostics["total_latency_ms"],
            "stages": stages,
        },
        "graph": {
            "field_count": len(graph["fields"]),
            "table_count": len(graph["tables"]),
            "added_relation_fields": added_fields,
            "added_relation_tables": added_tables,
            "context_chars": len(graph_builder.context_text(graph)),
            "metrics": _stage_metrics(
                [{"doc_id": str(field["id"])} for field in graph["fields"]],
                gold_fields,
            ),
        },
    }


def summarize_diagnosis(cases: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [case for case in cases if "retrieval" in case]
    stage_names = ("bm25", "dense", "rrf", "rerank", "final")

    def average(values: list[float]) -> float | None:
        return round(statistics.fmean(values), 6) if values else None

    stage_summary = {}
    for name in stage_names:
        rows = [case["retrieval"]["stages"][name] for case in valid]
        stage_summary[name] = {
            "average_count": average([float(row["count"]) for row in rows]),
            "average_recall": average([row["metrics"]["recall"] for row in rows]),
            "average_precision": average([row["metrics"]["precision"] for row in rows]),
            "average_latency_ms": average([row["latency_ms"] for row in rows]),
            "complete_gold_coverage_count": sum(
                not row["metrics"]["missing_gold_fields"] for row in rows
            ),
        }
    latencies = sorted(case["retrieval"]["total_latency_ms"] for case in valid)
    at_cap = sum(
        case["retrieval"]["stages"]["final"]["count"]
        == case["retrieval"]["config"]["max_schema_fields"]
        for case in valid
    )
    return {
        "case_count": len(cases),
        "successful_retrieval_count": len(valid),
        "error_count": len(cases) - len(valid),
        "at_final_field_cap_count": at_cap,
        "average_total_latency_ms": average(latencies),
        "p95_total_latency_ms": (
            latencies[math.ceil(len(latencies) * 0.95) - 1] if latencies else None
        ),
        "stages": stage_summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="诊断 Schema 检索阶段，不执行问数智能体")
    parser.add_argument("--scope", choices=("classic", "all"), default="classic")
    parser.add_argument("--case-id", action="append", help="只诊断指定用例，可重复传入")
    parser.add_argument("--case-list", type=Path, help="JSON manifest containing case_ids")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cases = _load_cases(args.scope)
    if args.case_list:
        cases = select_cases(cases, load_case_ids(args.case_list))
    if args.case_id:
        selected = set(args.case_id)
        cases = [case for case in cases if case["case_id"] in selected]
    if args.limit > 0:
        cases = cases[: args.limit]

    schema_index = SchemaIndex(ModelClient(settings), settings)
    try:
        graph_builder = SchemaGraphBuilder(runtime=schema_index.runtime)
        controller = AccessController()
        records: list[dict[str, Any]] = []
        for index, case in enumerate(cases, 1):
            try:
                record = diagnose_case(case, schema_index, graph_builder, controller)
                count = record["retrieval"]["stages"]["final"]["count"]
                print(f"[{index}/{len(cases)}] {case['case_id']} final_fields={count}")
            except Exception as exc:  # Keep a failed retrieval visible without dropping other cases.
                record = {
                    "case_id": case["case_id"],
                    "scenario": case["scenario"],
                    "error_stage": exc.stage if isinstance(exc, PipelineStageError) else "retrieval_diagnosis",
                    "error": str(exc),
                }
                print(f"[{index}/{len(cases)}] {case['case_id']} error={record['error_stage']}")
            records.append(record)

        output = args.output or RESULT_DIR / f"retrieval_diagnosis_{args.scope}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "scope": args.scope,
            "case_source": CASES_PATH.relative_to(BASE_DIR).as_posix(),
            "summary": summarize_diagnosis(records),
            "cases": records,
        }
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"retrieval diagnosis: {output}")

    finally:
        schema_index.close()


if __name__ == "__main__":
    main()
