"""Markdown report and CLI for deterministic benchmark insights."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from evaluation.analytics import BenchmarkAnalytics
from evaluation.insight import BenchmarkInsightGenerator, InsightResult
from evaluation.regression import RegressionComparator
from evaluation.report import BenchmarkReportBuilder
from evaluation.snapshot import BenchmarkSnapshotManager


DEFAULT_INSIGHT_REPORT = Path(__file__).resolve().parent / "results" / "benchmark_insight_report.md"


class InsightReportBuilder:
    """Present rule triggers and investigation steps in priority order."""

    @staticmethod
    def render_markdown(result: InsightResult) -> str:
        lines = ["# Benchmark Optimization Insight", ""]
        for severity, heading in (("high", "High Priority Issues"),
                                  ("medium", "Medium Priority Issues")):
            lines.extend([f"## {heading}", ""])
            issues = [item for item in result.insights if item["severity"] == severity]
            if not issues:
                lines.extend(["No issues detected.", ""])
                continue
            for item in issues:
                lines.extend([
                    f"### {item['title']}", "",
                    f"Category: `{item['category']}`", "",
                    "Observation:", "",
                    item["observation"], "",
                    "Possible Causes:", "",
                ])
                lines.extend(f"- {cause}" for cause in item["possible_causes"])
                lines.extend(["", "Suggestions:", ""])
                lines.extend(f"- {suggestion}" for suggestion in item["suggestions"])
                lines.append("")
        lines.extend([
            "## Summary", "",
            f"Total Issues: {len(result.insights)}",
            f"High Priority: {sum(item['severity'] == 'high' for item in result.insights)}",
            f"Medium Priority: {sum(item['severity'] == 'medium' for item in result.insights)}",
            "",
        ])
        return "\n".join(lines)

    @classmethod
    def write_markdown(cls, result: InsightResult, output: Path | str = DEFAULT_INSIGHT_REPORT) -> Path:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(cls.render_markdown(result), encoding="utf-8")
        return path

    @classmethod
    def from_benchmark(
        cls,
        benchmark_json: Path | str,
        *,
        output: Path | str = DEFAULT_INSIGHT_REPORT,
        generator: BenchmarkInsightGenerator | None = None,
        baseline: Path | str | None = None,
        candidate: Path | str | None = None,
    ) -> InsightResult:
        payload = json.loads(Path(benchmark_json).read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
            raise ValueError("Benchmark JSON must contain a cases list")
        cases: list[dict[str, Any]] = payload["cases"]
        if any(not isinstance(case, dict) for case in cases):
            raise ValueError("Every benchmark case must be an object")
        summary = payload.get("summary")
        if not isinstance(summary, dict):
            summary = BenchmarkReportBuilder.build(cases).to_dict()
        analytics = BenchmarkAnalytics.analyze(cases)
        engine = generator or BenchmarkInsightGenerator()
        if (baseline is None) != (candidate is None):
            raise ValueError("baseline and candidate must be provided together")
        if candidate is not None:
            candidate_cases = BenchmarkSnapshotManager.load(candidate).get("cases")
            if not isinstance(candidate_cases, list) or any(
                not isinstance(case, dict) for case in candidate_cases
            ):
                raise ValueError("candidate snapshot must contain a cases list")
            case_key = lambda case: str(case.get("case_id"))
            if sorted(cases, key=case_key) != sorted(candidate_cases, key=case_key):
                raise ValueError("candidate snapshot cases must match the input benchmark JSON")
        regression = RegressionComparator.compare(baseline, candidate) if baseline is not None else None
        result = engine.generate(
            summary,
            analytics=analytics,
            error_metrics=analytics["error_metrics"],
            regression_result=regression,
            trace_metrics=engine.trace_metrics_from_cases(cases),
        )
        cls.write_markdown(result, output)
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate rule-based benchmark optimization insights")
    parser.add_argument("--input", type=Path, required=True, help="Existing benchmark JSON file")
    parser.add_argument("--output", type=Path, default=DEFAULT_INSIGHT_REPORT)
    parser.add_argument("--baseline", type=Path, help="Optional baseline regression snapshot")
    parser.add_argument("--candidate", type=Path, help="Optional candidate regression snapshot")
    parser.add_argument("--latency-threshold-ms", type=float, default=3000.0)
    args = parser.parse_args()
    if (args.baseline is None) != (args.candidate is None):
        parser.error("--baseline and --candidate must be supplied together")
    engine = BenchmarkInsightGenerator(latency_threshold_ms=args.latency_threshold_ms)
    result = InsightReportBuilder.from_benchmark(
        args.input, output=args.output, generator=engine,
        baseline=args.baseline, candidate=args.candidate,
    )
    print(f"insight report: {args.output} ({len(result.insights)} issues)")


if __name__ == "__main__":
    main()
