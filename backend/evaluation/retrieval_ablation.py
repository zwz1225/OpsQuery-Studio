"""Offline comparisons over a saved Schema retrieval diagnosis JSON.

This module reads recorded candidates only. It never calls a model, database,
agent, or retriever, and cannot estimate SQL accuracy or counterfactual latency.
"""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RANKING_STAGES = ("bm25", "dense", "rrf", "rerank")
DEFAULT_CUTOFFS = (5, 10, 15, 20, 30, 40)
DEFAULT_FIELD_LIMITS = (10, 15, 20)
DEFAULT_THRESHOLDS = (0.40, 0.50, 0.55, 0.60)


def _ids(candidates: list[dict[str, Any]]) -> list[str]:
    return [str(item["doc_id"]) for item in candidates]


def _selected_at_threshold(
    candidates: list[dict[str, Any]], field_limit: int, threshold: float
) -> list[str]:
    return [
        str(item["doc_id"])
        for item in candidates
        if float(item["score"]) >= threshold
    ][:field_limit]


def _summarize_selection(
    cases: list[dict[str, Any]], selections: dict[str, list[str]]
) -> dict[str, Any]:
    recalls: list[float] = []
    precisions: list[float] = []
    counts: list[int] = []
    complete_count = 0
    gained: dict[str, list[str]] = {}
    lost: dict[str, list[str]] = {}
    missing: dict[str, list[str]] = {}

    for case in cases:
        case_id = str(case["case_id"])
        gold = set(map(str, case["gold_fields"]))
        chosen = set(selections[case_id])
        baseline = set(_ids(case["retrieval"]["stages"]["final"]["candidates"]))
        recalls.append(len(gold & chosen) / len(gold) if gold else 1.0)
        precisions.append(len(gold & chosen) / len(chosen) if chosen else 0.0)
        counts.append(len(selections[case_id]))
        complete_count += gold <= chosen
        if gained_fields := sorted((gold & chosen) - baseline):
            gained[case_id] = gained_fields
        if lost_fields := sorted((gold & baseline) - chosen):
            lost[case_id] = lost_fields
        if missing_fields := sorted(gold - chosen):
            missing[case_id] = missing_fields

    def mean(values: list[float | int]) -> float | None:
        return round(statistics.fmean(values), 6) if values else None

    return {
        "case_count": len(cases),
        "average_recall": mean(recalls),
        "average_precision": mean(precisions),
        "average_field_count": mean(counts),
        "complete_gold_coverage_count": complete_count,
        "gained_gold_fields_vs_final": gained,
        "lost_gold_fields_vs_final": lost,
        "missing_gold_fields": missing,
    }


def build_ablation(
    diagnosis: dict[str, Any],
    *,
    cutoffs: tuple[int, ...] = DEFAULT_CUTOFFS,
    field_limits: tuple[int, ...] = DEFAULT_FIELD_LIMITS,
    thresholds: tuple[float, ...] = DEFAULT_THRESHOLDS,
) -> dict[str, Any]:
    """Re-score existing candidate lists; never recompute retrieval or SQL."""
    cases = [case for case in diagnosis.get("cases", []) if "retrieval" in case]
    excluded = [str(case.get("case_id")) for case in diagnosis.get("cases", []) if "retrieval" not in case]
    if len({case["case_id"] for case in cases}) != len(cases):
        raise ValueError("Duplicate case IDs in diagnosis")

    fingerprints = {
        json.dumps({
            key: case["retrieval"].get(key)
            for key in ("index_version", "embedding_model", "rerank_model", "config")
        }, sort_keys=True, ensure_ascii=False)
        for case in cases
    }
    if len(fingerprints) > 1:
        raise ValueError("Diagnosis cases use different index or model configurations")

    config = cases[0]["retrieval"]["config"] if cases else None
    for case in cases:
        stages = case["retrieval"]["stages"]
        expected_final = _selected_at_threshold(
            stages["rerank"]["candidates"],
            int(config["max_schema_fields"]),
            float(config["rerank_threshold"]),
        )
        if expected_final != _ids(stages["final"]["candidates"]):
            raise ValueError(f"Recorded final selection cannot be reproduced: {case['case_id']}")

    baseline_selections = {
        str(case["case_id"]): _ids(case["retrieval"]["stages"]["final"]["candidates"])
        for case in cases
    }
    ranking: dict[str, dict[str, Any]] = {}
    for stage in RANKING_STAGES:
        stage_limit = {
            "bm25": "bm25_top_k", "dense": "dense_top_k",
            "rrf": "rrf_top_k", "rerank": "rrf_top_k",
        }[stage]
        for cutoff in cutoffs:
            if cutoff <= 0 or not cases or cutoff > int(config[stage_limit]):
                continue
            selections = {
                str(case["case_id"]): _ids(
                    case["retrieval"]["stages"][stage]["candidates"][:cutoff]
                )
                for case in cases
            }
            ranking[f"{stage}_top_{cutoff}"] = {
                "stage": stage,
                "top_k": cutoff,
                **_summarize_selection(cases, selections),
            }

    selection: dict[str, dict[str, Any]] = {}
    for field_limit in field_limits:
        if field_limit <= 0:
            continue
        for threshold in thresholds:
            if not 0 <= threshold <= 1:
                raise ValueError("Threshold must be between 0 and 1")
            selections = {
                str(case["case_id"]): _selected_at_threshold(
                    case["retrieval"]["stages"]["rerank"]["candidates"],
                    field_limit,
                    threshold,
                )
                for case in cases
            }
            selection[f"rerank_limit_{field_limit}_threshold_{threshold:.2f}"] = {
                "field_limit": field_limit,
                "threshold": threshold,
                **_summarize_selection(cases, selections),
            }

    return {
        "source_case_count": len(diagnosis.get("cases", [])),
        "analyzed_case_count": len(cases),
        "excluded_case_ids": excluded,
        "index_version": cases[0]["retrieval"].get("index_version") if cases else None,
        "config": config,
        "baseline_final": _summarize_selection(cases, baseline_selections),
        "ranking_experiments": ranking,
        "selection_experiments": selection,
        "limitations": [
            "Uses only recorded candidate lists; fields outside those lists cannot be recovered.",
            "Offline coverage does not measure SQL execution success or result accuracy.",
            "Observed retrieval latency cannot predict latency under a changed pipeline.",
        ],
    }


def render_markdown(result: dict[str, Any]) -> str:
    def percent(value: float | None) -> str:
        return "N/A" if value is None else f"{value:.2%}"

    def rows(items: dict[str, dict[str, Any]]) -> list[str]:
        return [
            f"| {name} | {item['case_count']} | {percent(item['average_recall'])} "
            f"| {percent(item['average_precision'])} | {item['complete_gold_coverage_count']} "
            f"| {item['average_field_count']} | {len(item['gained_gold_fields_vs_final'])} "
            f"| {len(item['lost_gold_fields_vs_final'])} |"
            for name, item in items.items()
        ]

    heading = (
        "| Variant | Cases | Recall | Precision | Complete Gold | Avg fields "
        "| Gained cases | Lost cases |\n"
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
    )
    baseline = result["baseline_final"]
    lines = [
        "# Schema Retrieval Offline Ablation",
        "",
        f"Analyzed cases: {result['analyzed_case_count']}; excluded: {len(result['excluded_case_ids'])}.",
        f"Index version: `{result['index_version']}`.",
        "",
        "## Recorded final selection",
        "",
        heading,
        *rows({"final_actual": baseline}),
        "",
        "## Ranking at fixed K (no score threshold)",
        "",
        heading,
        *rows(result["ranking_experiments"]),
        "",
        "## Rerank selection simulations",
        "",
        heading,
        *rows(result["selection_experiments"]),
        "",
        "## Interpretation limits",
        "",
        *[f"- {item}" for item in result["limitations"]],
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline Schema retrieval ablation from diagnosis JSON")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="Output JSON; defaults beside input")
    args = parser.parse_args()

    diagnosis = json.loads(args.input.read_text(encoding="utf-8"))
    result = build_ablation(diagnosis)
    result["created_at"] = datetime.now(timezone.utc).isoformat()
    result["source_file"] = str(args.input)
    output = args.output or args.input.with_name(args.input.stem + "_ablation.json")
    if output.resolve() == args.input.resolve():
        parser.error("--output must differ from --input")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown = output.with_suffix(".md")
    markdown.write_text(render_markdown(result), encoding="utf-8")
    print(f"offline ablation: {output}")
    print(f"markdown report: {markdown}")


if __name__ == "__main__":
    main()
