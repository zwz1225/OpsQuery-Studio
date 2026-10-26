"""Render saved benchmark comparisons as Markdown."""

from __future__ import annotations

from pathlib import Path

from evaluation.regression import RegressionResult


_METRIC_LABELS = {
    "result_accuracy": "Result accuracy",
    "strict_result_accuracy": "Strict result accuracy",
    "sql_execution_success_rate": "SQL execution success rate",
    "schema_recall": "Schema recall",
    "schema_precision": "Schema precision",
    "average_latency": "Average execution latency",
    "tool_success_rate": "Tool success rate",
    "permission_success_rate": "Permission success rate",
    "clarification_rate": "Clarification rate",
}


def _format(value: float | int | None, *, latency: bool = False, delta: bool = False) -> str:
    if value is None:
        return "N/A"
    prefix = "+" if delta and value > 0 else ""
    return f"{prefix}{value:.3f} ms" if latency else f"{prefix}{value:.2%}"


class RegressionReportBuilder:
    """Present comparator output without recalculating any benchmark metric."""

    @staticmethod
    def render_markdown(result: RegressionResult) -> str:
        lines = [
            "# AskData Studio Regression Report", "",
            "## Overall Comparison", "",
            f"- Baseline: `{result.baseline_snapshot_id}`",
            f"- Candidate: `{result.candidate_snapshot_id}`",
            f"- Dataset match: {'Yes' if result.dataset_match else 'No'}",
            f"- Comparable: {'Yes' if not result.comparison_warnings else 'No'}",
            *[f"- Comparison warning: {item}" for item in result.comparison_warnings],
            "- Delta = candidate - baseline; positive latency means slower execution.", "",
            "## Metric Delta", "",
            "| Metric | Baseline | Candidate | Delta |",
            "|---|---:|---:|---:|",
        ]
        for section, baseline, candidate, deltas in (
            ("Overall", result.overall_baseline, result.overall_candidate, result.overall_delta),
            ("Agent", result.agent_baseline, result.agent_candidate, result.agent_delta),
        ):
            for key, delta in deltas.items():
                latency = key == "average_latency"
                lines.append(
                    f"| {section}: {_METRIC_LABELS.get(key, key)} | "
                    f"{_format(baseline.get(key), latency=latency)} | "
                    f"{_format(candidate.get(key), latency=latency)} | "
                    f"{_format(delta, latency=latency, delta=True)} |"
                )
        lines.extend(["", "## Improvement Cases", ""])
        improved = result.case_changes["failure_to_success"]
        lines.extend([f"- `{case['case_id']}`: failed → successful" for case in improved]
                     or ["- None"])
        lines.extend(["", "## Regression Cases", ""])
        regressed = result.case_changes["success_to_failure"]
        lines.extend([f"- `{case['case_id']}`: successful → failed" for case in regressed]
                     or ["- None"])
        lines.extend(["", "## Other Result Changes", ""])
        transitions = {case["case_id"] for case in improved + regressed}
        other_changes = [
            case for case in result.case_changes["result_changes"]
            if case["case_id"] not in transitions
        ]
        lines.extend([f"- `{case['case_id']}`: result fields changed" for case in other_changes]
                     or ["- None"])
        if result.case_changes["added_cases"] or result.case_changes["removed_cases"]:
            lines.extend(["", "## Case Set Changes", ""])
            lines.append("- Added: " + ", ".join(result.case_changes["added_cases"] or ["None"]))
            lines.append("- Removed: " + ", ".join(result.case_changes["removed_cases"] or ["None"]))
        lines.extend([
            "", "## Error Distribution Change", "",
            f"- Failure count delta: {result.error_delta['failure_count']:+d}", "",
            "| Error Type | Baseline | Candidate | Delta |",
            "|---|---:|---:|---:|",
        ])
        distribution = result.error_delta["error_distribution"]
        for name in sorted(distribution):
            lines.append(
                f"| {name} | {result.error_delta['baseline_error_distribution'].get(name, 0)} | "
                f"{result.error_delta['candidate_error_distribution'].get(name, 0)} | "
                f"{distribution[name]:+d} |"
            )
        if not distribution:
            lines.append("| No failures | 0 | 0 | 0 |")
        lines.append("")
        return "\n".join(lines)

    @classmethod
    def write_markdown(cls, result: RegressionResult, output: Path | str) -> Path:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(cls.render_markdown(result), encoding="utf-8")
        return path
