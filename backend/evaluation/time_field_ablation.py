"""Offline evaluation of the same time-field policy used by the workflow.

Gold fields are used only after candidate selection, to score the experiment.
The CLI never invokes the workflow, agent, model, or SQL execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.retrieval.time_field_policy import (
    DEFAULT_CATALOG,
    TimeFieldPolicy,
    has_explicit_time_request,
)
from app.security import AccessController

from .retrieval_ablation import _ids, _summarize_selection


def current_schema_version() -> str:
    from app.datasources import create_datasource_runtime
    with create_datasource_runtime() as runtime:
        return runtime.index_signature()[:12]


class TimeFieldExperiment:
    """Evaluation adapter around the exact policy used by the workflow."""

    def __init__(
        self,
        catalog_path: Path = DEFAULT_CATALOG,
        controller: AccessController | None = None,
        max_extra_fields: int = 2,
    ) -> None:
        self.controller = controller or AccessController()
        self.policy = TimeFieldPolicy(catalog_path, max_extra_fields)
        self.max_extra_fields = max_extra_fields

    def propose(
        self, case: dict[str, Any], *, include_schema_fallback: bool = True
    ) -> dict[str, Any]:
        scope = self.controller.resolve(f"demo_{case['scenario']}")
        selected = _ids(case["retrieval"]["stages"]["final"]["candidates"])
        return self.policy.propose(
            str(case.get("query") or ""),
            selected,
            scope,
            include_schema_fallback=include_schema_fallback,
        )


def build_time_field_ablation(
    diagnosis: dict[str, Any], experiment: TimeFieldExperiment | None = None
) -> dict[str, Any]:
    experiment = experiment or TimeFieldExperiment()
    cases = [case for case in diagnosis.get("cases", []) if "retrieval" in case]
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

    baseline: dict[str, list[str]] = {}
    catalog_append: dict[str, list[str]] = {}
    catalog_reserve: dict[str, list[str]] = {}
    append: dict[str, list[str]] = {}
    reserve: dict[str, list[str]] = {}
    details: list[dict[str, Any]] = []
    for case in cases:
        case_id = str(case["case_id"])
        original = _ids(case["retrieval"]["stages"]["final"]["candidates"])
        catalog_proposal = experiment.propose(case, include_schema_fallback=False)
        proposal = experiment.propose(case)
        catalog_extras = [
            item["doc_id"] for item in catalog_proposal["proposals"][: experiment.max_extra_fields]
        ]
        extras = [item["doc_id"] for item in proposal["proposals"][: experiment.max_extra_fields]]
        limit = int(case["retrieval"]["config"]["max_schema_fields"])
        if max(len(extras), len(catalog_extras)) > limit:
            raise ValueError("More proposed fields than the configured field limit")
        baseline[case_id] = original
        catalog_append[case_id] = original + catalog_extras
        catalog_reserve[case_id] = original[: limit - len(catalog_extras)] + catalog_extras
        append[case_id] = original + extras
        reserve[case_id] = original[: limit - len(extras)] + extras
        details.append({
            "case_id": case_id,
            "time_cue": proposal["time_cue"],
            "matched_metrics": proposal["matched_metrics"],
            "catalog_proposed_fields": catalog_proposal["proposals"],
            "proposed_fields": proposal["proposals"],
            "selected_extra_fields": extras,
            "reserve_evicted_fields": original[limit - len(extras):] if extras else [],
            "baseline_field_count": len(original),
            "append_field_count": len(append[case_id]),
            "reserve_field_count": len(reserve[case_id]),
        })

    return {
        "source_case_count": len(diagnosis.get("cases", [])),
        "analyzed_case_count": len(cases),
        "excluded_case_ids": [
            str(case.get("case_id")) for case in diagnosis.get("cases", [])
            if "retrieval" not in case
        ],
        "index_version": cases[0]["retrieval"].get("index_version") if cases else None,
        "current_schema_version": current_schema_version(),
        "schema_version_match": (
            cases[0]["retrieval"].get("index_version") == current_schema_version()
            if cases else None
        ),
        "max_extra_fields": experiment.max_extra_fields,
        "variants": {
            "baseline": _summarize_selection(cases, baseline),
            "catalog_append": _summarize_selection(cases, catalog_append),
            "catalog_reserve": _summarize_selection(cases, catalog_reserve),
            "append": _summarize_selection(cases, append),
            "reserve": _summarize_selection(cases, reserve),
        },
        "case_details": details,
        "limitations": [
            "Candidate selection uses the question, catalog, final table presence, schema, and role only; Gold fields are scoring labels.",
            "Append may exceed the current field limit; reserve may evict a useful field.",
            "This does not execute SQL or predict result accuracy and latency.",
        ],
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8.2.1 Time Field Supplementation — Offline Experiment",
        "",
        f"Cases: {result['analyzed_case_count']}; index version: `{result['index_version']}`.",
        f"Current Schema version: `{result['current_schema_version']}`; "
        f"matches diagnosis: `{result['schema_version_match']}`.",
        "",
        "| Variant | Gold Recall | Gold Precision | Complete Gold | Avg fields | Gained cases | Lost cases |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, item in result["variants"].items():
        lines.append(
            f"| {name} | {item['average_recall']:.2%} | {item['average_precision']:.2%} "
            f"| {item['complete_gold_coverage_count']} | {item['average_field_count']} "
            f"| {len(item['gained_gold_fields_vs_final'])} "
            f"| {len(item['lost_gold_fields_vs_final'])} |"
            if item["case_count"] else f"| {name} | N/A | N/A | 0 | N/A | 0 | 0 |"
        )
    lines.extend(["", "## Cases with proposed time fields", ""])
    for item in result["case_details"]:
        if not item["selected_extra_fields"]:
            continue
        lines.append(
            f"- `{item['case_id']}`: add {', '.join(item['selected_extra_fields'])}; "
            f"reserve evicts {', '.join(item['reserve_evicted_fields']) or 'none'}"
        )
    if not any(item["selected_extra_fields"] for item in result["case_details"]):
        lines.append("- None")
    lines.extend(["", "## Limits", "", *[f"- {value}" for value in result["limitations"]], ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline time-field supplementation experiment")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    diagnosis = json.loads(args.input.read_text(encoding="utf-8"))
    result = build_time_field_ablation(diagnosis)
    result["created_at"] = datetime.now(timezone.utc).isoformat()
    result["source_file"] = str(args.input)
    output = args.output or args.input.with_name(args.input.stem + "_time_field_ablation.json")
    if output.resolve() == args.input.resolve():
        parser.error("--output must differ from --input")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown = output.with_suffix(".md")
    markdown.write_text(render_markdown(result), encoding="utf-8")
    print(f"time field ablation: {output}")
    print(f"markdown report: {markdown}")


if __name__ == "__main__":
    main()
