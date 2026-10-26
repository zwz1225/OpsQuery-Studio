"""Offline baseline report for a fixed Schema retrieval validation cohort."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from app.config import BASE_DIR
from app.retrieval.time_field_policy import has_explicit_time_request

from .case_selection import load_case_ids, select_cases


DEFAULT_CASE_LIST = BASE_DIR / "evaluation" / "cases" / "phase83_validation.json"
DEFAULT_CASE_SOURCE = BASE_DIR / "evaluation" / "cases" / "all_cases.jsonl"


def _mean(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 3) if values else None


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[math.ceil(len(ordered) * 0.95) - 1], 3)


def _numeric(rows: list[dict[str, Any]], key: str) -> list[float]:
    return [
        float(row[key]) for row in rows
        if isinstance(row.get(key), (int, float)) and not isinstance(row[key], bool)
    ]


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    return {
        "case_count": count,
        "complete_gold_coverage_count": sum(row["complete_gold_coverage"] for row in rows),
        "schema_metric_observed_count": len(_numeric(rows, "schema_recall")),
        "average_schema_recall": _mean(_numeric(rows, "schema_recall")),
        "average_schema_precision": _mean(_numeric(rows, "schema_precision")),
        "average_retrieved_fields": _mean(_numeric(rows, "retrieved_field_count")),
        "median_retrieved_fields": (
            statistics.median(_numeric(rows, "retrieved_field_count")) if rows else None
        ),
        "p95_retrieved_fields": _p95(_numeric(rows, "retrieved_field_count")),
        "at_20_or_more_fields_count": sum(row["retrieved_field_count"] >= 20 for row in rows),
        "average_retrieval_ms": _mean(_numeric(rows, "retrieval_ms")),
        "p95_retrieval_ms": _p95(_numeric(rows, "retrieval_ms")),
        "retrieval_latency_observed_count": len(_numeric(rows, "retrieval_ms")),
        "sql_execution_success_rate": (
            round(sum(row["sql_execution_success"] is True for row in rows) / count, 6)
            if count else None
        ),
        "result_accuracy": (
            round(sum(row["result_correct"] is True for row in rows) / count, 6)
            if count else None
        ),
        "supplemented_case_count": sum(bool(row["supplemented_fields"]) for row in rows),
    }


def build_validation_report(
    case_ids: list[str],
    cases: list[dict[str, Any]],
    benchmark: dict[str, Any],
    diagnosis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Combine existing JSON outputs; never execute retrieval or SQL."""
    if len(set(case_ids)) != len(case_ids) or not case_ids:
        raise ValueError("Validation case IDs must be unique and nonempty")
    selected = select_cases(cases, case_ids)
    if any(case.get("classic") for case in selected):
        raise ValueError("The expanded validation cohort must exclude classic cases")
    if any(not case.get("gold_sql") or not case.get("gold_fields") for case in selected):
        raise ValueError("All validation cases require Gold SQL and Gold fields")
    benchmark_cases = benchmark.get("cases")
    if not isinstance(benchmark_cases, list):
        raise ValueError("Benchmark JSON must contain cases")
    if len(benchmark_cases) != len(case_ids):
        raise ValueError("Benchmark case count does not match the manifest")
    by_id = {str(case.get("case_id")): case for case in benchmark_cases}
    if len(by_id) != len(case_ids) or set(by_id) != set(case_ids):
        raise ValueError("Benchmark case IDs do not match the manifest")

    rows: list[dict[str, Any]] = []
    for case in selected:
        result = by_id[case["case_id"]]
        fields = list(result.get("retrieved_fields") or [])
        gold = set(case["gold_fields"])
        supplement = (
            (result.get("trace") or {}).get("schema_retrieval") or {}
        ).get("time_field_supplement") or {}
        rows.append({
            "case_id": case["case_id"],
            "scenario": case["scenario"],
            "category": case.get("category"),
            "query_type": case.get("query_type"),
            "difficulty": case.get("difficulty"),
            "explicit_time_cue": has_explicit_time_request(case["query"]),
            "gold_field_count": len(gold),
            "gold_table_count": len({field.rsplit(".", 1)[0] for field in gold}),
            "retrieved_field_count": len(fields),
            "complete_gold_coverage": gold.issubset(fields),
            "missing_gold_fields": sorted(gold - set(fields)),
            "schema_recall": result.get("schema_recall"),
            "schema_precision": result.get("schema_precision"),
            "retrieval_ms": result.get("retrieval_ms"),
            "sql_execution_success": result.get("sql_execution_success"),
            "result_correct": result.get("result_correct"),
            "supplemented_fields": [
                str(item["doc_id"]) for item in supplement.get("added_fields", [])
            ],
        })

    groups: dict[str, dict[str, Any]] = {}
    for scenario in sorted({row["scenario"] for row in rows}):
        groups[scenario] = _summary([row for row in rows if row["scenario"] == scenario])
    for difficulty in sorted({str(row["difficulty"]) for row in rows}):
        groups[f"difficulty={difficulty}"] = _summary([
            row for row in rows if str(row["difficulty"]) == difficulty
        ])
    for multi_table in (False, True):
        groups[f"multi_table={str(multi_table).lower()}"] = _summary([
            row for row in rows if (row["gold_table_count"] > 1) is multi_table
        ])
    for cue in (False, True):
        groups[f"explicit_time_cue={str(cue).lower()}"] = _summary([
            row for row in rows if row["explicit_time_cue"] is cue
        ])

    stage_timings: dict[str, dict[str, float | None]] = {}
    diagnosis_config: dict[str, Any] = {}
    if diagnosis is not None:
        diagnosis_cases = diagnosis.get("cases")
        if not isinstance(diagnosis_cases, list) or len(diagnosis_cases) != len(case_ids):
            raise ValueError("Diagnosis case count does not match the manifest")
        diagnosis_by_id = {str(case.get("case_id")): case for case in diagnosis_cases}
        if len(diagnosis_by_id) != len(case_ids) or set(diagnosis_by_id) != set(case_ids):
            raise ValueError("Diagnosis case IDs do not match the manifest")
        if any("retrieval" not in case for case in diagnosis_cases):
            raise ValueError("Diagnosis contains failed retrieval cases")
        fingerprints = {
            json.dumps({
                key: case["retrieval"].get(key)
                for key in ("index_version", "embedding_model", "rerank_model", "config")
            }, sort_keys=True, ensure_ascii=False)
            for case in diagnosis_cases
        }
        if len(fingerprints) != 1:
            raise ValueError("Diagnosis cases have inconsistent retrieval configuration")
        diagnosis_config = {
            key: diagnosis_cases[0]["retrieval"].get(key)
            for key in ("index_version", "embedding_model", "rerank_model", "config")
        }
        names = sorted({
            name for case in diagnosis_cases
            for name in case["retrieval"].get("timings_ms", {})
        })
        for name in names:
            values = [
                float(case["retrieval"]["timings_ms"][name])
                for case in diagnosis_cases
                if isinstance(case["retrieval"].get("timings_ms", {}).get(name), (int, float))
            ]
            stage_timings[name] = {"average_ms": _mean(values), "p95_ms": _p95(values)}
        totals = _numeric([
            {"total": case["retrieval"].get("total_latency_ms")}
            for case in diagnosis_cases
        ], "total")
        stage_timings["total"] = {"average_ms": _mean(totals), "p95_ms": _p95(totals)}

    return {
        "cohort_case_count": len(case_ids),
        "scenario_distribution": dict(Counter(case["scenario"] for case in selected)),
        "summary": _summary(rows),
        "groups": groups,
        "diagnosis_config": diagnosis_config,
        "diagnosis_stage_timings": stage_timings,
        "cases": rows,
        "limitations": [
            "This cohort uses existing cases from the same synthetic dataset, not an external generalization benchmark.",
            "Gold field coverage is diagnostic; a missing Gold field does not always make the final SQL wrong.",
            "Benchmark retrieval_ms and diagnosis stage timings come from separate runs and are not additive.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Phase 8.3.1 Schema Retrieval Validation Baseline", "",
        f"Cases: {summary['case_count']}; complete Gold coverage: "
        f"{summary['complete_gold_coverage_count']}/{summary['case_count']}.",
        f"Index version: `{report['diagnosis_config'].get('index_version')}`; "
        f"embedding: `{report['diagnosis_config'].get('embedding_model')}`; "
        f"rerank: `{report['diagnosis_config'].get('rerank_model')}`.",
        f"Schema recall: {summary['average_schema_recall']}; "
        f"precision: {summary['average_schema_precision']} "
        f"({summary['schema_metric_observed_count']} observed cases).",
        f"Retrieved fields: average {summary['average_retrieved_fields']}, "
        f"median {summary['median_retrieved_fields']}, "
        f"P95 {summary['p95_retrieved_fields']}; "
        f"20 or more: {summary['at_20_or_more_fields_count']} cases.",
        f"Retrieval latency: average {summary['average_retrieval_ms']} ms, "
        f"P95 {summary['p95_retrieval_ms']} ms "
        f"({summary['retrieval_latency_observed_count']} observed cases).",
        f"SQL success: {summary['sql_execution_success_rate']}; "
        f"result accuracy: {summary['result_accuracy']}.",
        f"Cases with time-field additions: {summary['supplemented_case_count']}.",
        "", "## By scenario, difficulty, table count, and time cue", "",
        "| Group | Cases | Complete Gold | Avg fields | Recall | Precision | P95 retrieval ms | Result accuracy |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, item in report["groups"].items():
        lines.append(
            f"| {name} | {item['case_count']} | {item['complete_gold_coverage_count']} "
            f"| {item['average_retrieved_fields']} | {item['average_schema_recall']} "
            f"| {item['average_schema_precision']} | {item['p95_retrieval_ms']} "
            f"| {item['result_accuracy']} |"
        )
    lines.extend(["", "## Retrieval stage latency (separate diagnosis run)", ""])
    if report["diagnosis_stage_timings"]:
        lines.extend(["| Stage | Average ms | P95 ms |", "| --- | ---: | ---: |"])
        for name, item in report["diagnosis_stage_timings"].items():
            lines.append(f"| {name} | {item['average_ms']} | {item['p95_ms']} |")
    else:
        lines.append("No diagnosis JSON supplied.")
    lines.extend(["", "## Incomplete Gold coverage", ""])
    missing = [row for row in report["cases"] if row["missing_gold_fields"]]
    if missing:
        for row in missing:
            lines.append(
                f"- `{row['case_id']}`: {', '.join(row['missing_gold_fields'])}; "
                f"result correct: {row['result_correct']}"
            )
    else:
        lines.append("None.")
    lines.extend(["", "## Limits", "", *[f"- {item}" for item in report["limitations"]], ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize a fixed Schema validation cohort")
    parser.add_argument("--case-list", type=Path, default=DEFAULT_CASE_LIST)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--diagnosis", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    ids = load_case_ids(args.case_list)
    cases = [
        json.loads(line) for line in DEFAULT_CASE_SOURCE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    benchmark = json.loads(args.benchmark.read_text(encoding="utf-8"))
    diagnosis = json.loads(args.diagnosis.read_text(encoding="utf-8")) if args.diagnosis else None
    result = build_validation_report(ids, cases, benchmark, diagnosis)
    output = args.output or args.benchmark.with_name(args.benchmark.stem + "_retrieval_validation.json")
    if output.resolve() in {args.benchmark.resolve(), args.case_list.resolve()}:
        parser.error("--output must not overwrite an input file")
    if args.diagnosis and output.resolve() == args.diagnosis.resolve():
        parser.error("--output must not overwrite diagnosis input")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown = output.with_suffix(".md")
    markdown.write_text(render_markdown(result), encoding="utf-8")
    print(f"retrieval validation: {output}")
    print(f"markdown report: {markdown}")


if __name__ == "__main__":
    main()
