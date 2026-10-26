"""Aggregate primary failure categories across benchmark dimensions."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable

from evaluation.error_taxonomy import ErrorClassifier
from evaluation.models import EvaluationResult


class FailureDiagnosis:
    """Count each failed case once using its primary error category."""

    @staticmethod
    def analyze(results: Iterable[EvaluationResult | dict[str, Any]]) -> dict[str, Any]:
        distribution: Counter[str] = Counter()
        dimensions: dict[str, defaultdict[str, Counter[str]]] = {
            key: defaultdict(Counter) for key in ("scenario", "category", "difficulty")
        }
        case_count = 0
        for result in results:
            row = result.to_dict() if isinstance(result, EvaluationResult) else result
            case_count += 1
            category = ErrorClassifier.classify(row)
            if category is None:
                continue
            label = category.value
            distribution[label] += 1
            for key, groups in dimensions.items():
                raw = row.get(key)
                group = str(raw).strip() if raw is not None and str(raw).strip() else "unknown"
                groups[group][label] += 1

        failed = sum(distribution.values())
        return {
            "error_distribution": dict(distribution),
            "failure_rate": round(failed / case_count, 9) if case_count else 0.0,
            "successful_case_count": case_count - failed,
            "failed_case_count": failed,
            "scenario_error_analysis": {
                group: dict(counts) for group, counts in dimensions["scenario"].items()
            },
            "category_error_analysis": {
                group: dict(counts) for group, counts in dimensions["category"].items()
            },
            "difficulty_error_analysis": {
                group: dict(counts) for group, counts in dimensions["difficulty"].items()
            },
        }

    @classmethod
    def build(cls, results: Iterable[EvaluationResult | dict[str, Any]]) -> dict[str, Any]:
        return cls.analyze(results)
