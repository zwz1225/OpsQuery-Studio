"""Compare two saved benchmark runs without executing any cases."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from evaluation.diagnosis import FailureDiagnosis
from evaluation.report import BenchmarkReportBuilder
from evaluation.snapshot import BenchmarkSnapshotManager
from evaluation.run_manifest import comparison_identity
from evaluation.report_identity import validate_report_identity


def _metric(row: dict[str, Any], section: str, key: str, legacy: str) -> Any:
    nested = row.get(section)
    if isinstance(nested, dict) and key in nested:
        return nested[key]
    return row.get(legacy)


def _delta(baseline: Any, candidate: Any, *, digits: int = 9) -> float | None:
    if isinstance(baseline, (int, float)) and not isinstance(baseline, bool) and isinstance(
        candidate, (int, float)
    ) and not isinstance(candidate, bool):
        return round(float(candidate) - float(baseline), digits)
    return None


def _case_index(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for case in cases:
        if not isinstance(case, dict) or not case.get("case_id"):
            raise ValueError("Every snapshot case must have a case_id")
        case_id = str(case["case_id"])
        if case_id in indexed:
            raise ValueError(f"Duplicate case_id in snapshot: {case_id}")
        indexed[case_id] = case
    return indexed


@dataclass(frozen=True)
class RegressionResult:
    baseline_snapshot_id: str
    candidate_snapshot_id: str
    dataset_match: bool
    comparison_warnings: list[str]
    overall_baseline: dict[str, Any]
    overall_candidate: dict[str, Any]
    overall_delta: dict[str, float | None]
    agent_baseline: dict[str, Any]
    agent_candidate: dict[str, Any]
    agent_delta: dict[str, float | None]
    error_delta: dict[str, Any]
    case_changes: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RegressionComparator:
    """Calculate candidate minus baseline deltas from stored results."""

    @staticmethod
    def _load(value: Path | str | dict[str, Any]) -> dict[str, Any]:
        return BenchmarkSnapshotManager.load(value) if isinstance(value, (Path, str)) else value

    @staticmethod
    def _overall(snapshot: dict[str, Any]) -> dict[str, Any]:
        summary = snapshot.get("summary") or {}
        computed = BenchmarkReportBuilder.build(snapshot["cases"]).summary_metrics

        def existing(key: str, fallback: Any) -> Any:
            return summary[key] if key in summary else fallback

        return {
            "result_accuracy": existing("result_accuracy", computed["overall"]["result_accuracy"]),
            "strict_result_accuracy": summary.get("strict_result_accuracy"),
            "sql_execution_success_rate": existing(
                "sql_execution_success_rate", computed["overall"]["sql_execution_success_rate"]
            ),
            "schema_recall": existing("schema_recall", computed["schema_retrieval"]["schema_recall"]),
            "schema_precision": existing(
                "schema_precision", computed["schema_retrieval"]["schema_precision"]
            ),
            "average_latency": existing(
                "average_execution_ms", computed["overall"]["average_execution_ms"]
            ),
        }

    @staticmethod
    def _agent(snapshot: dict[str, Any]) -> dict[str, Any]:
        rows = snapshot["cases"]
        metrics = BenchmarkReportBuilder.build(rows).summary_metrics["agent_behavior"]
        permission_checks = sum(
            int((case.get("agent_metrics") or {}).get("permission_check_count") or 0)
            for case in rows
        )
        return {
            "tool_success_rate": metrics["tool_success_rate"]
            if metrics["tool_call_count"] else None,
            "permission_success_rate": metrics["permission_success_rate"]
            if permission_checks else None,
            "clarification_rate": metrics["clarification_rate"] if rows else None,
        }

    @classmethod
    def compare(
        cls,
        baseline: Path | str | dict[str, Any],
        candidate: Path | str | dict[str, Any],
        *,
        allow_incompatible: bool = False,
    ) -> RegressionResult:
        before = cls._load(baseline)
        after = cls._load(candidate)
        for snapshot in (before, after):
            if not isinstance(snapshot, dict) or not isinstance(snapshot.get("cases"), list):
                raise ValueError("Snapshots must contain a cases list")
        warnings = []
        for label, snapshot in (("baseline", before), ("candidate", after)):
            manifest = snapshot.get("run_manifest")
            if not isinstance(manifest, dict):
                warnings.append(f"{label} has no run manifest")
                continue
            try:
                validate_report_identity(snapshot)
            except (ValueError, KeyError, TypeError) as exc:
                warnings.append(f"{label} invalid report identity: {exc}")
            expected_ids = manifest.get("dataset", {}).get("case_ids", [])
            actual_ids = [str(case.get("case_id")) for case in snapshot["cases"]]
            if len(actual_ids) != len(expected_ids) or set(actual_ids) != set(expected_ids):
                warnings.append(f"{label} has missing or unexpected cases")
        baseline_manifest = before.get("run_manifest")
        candidate_manifest = after.get("run_manifest")
        if isinstance(baseline_manifest, dict) and isinstance(candidate_manifest, dict):
            old_identity = comparison_identity(baseline_manifest)
            new_identity = comparison_identity(candidate_manifest)
            for key in old_identity:
                if old_identity[key] != new_identity[key]:
                    warnings.append(f"{key} differs")
        if warnings and not allow_incompatible:
            raise ValueError("Incomparable benchmark runs: " + "; ".join(warnings))
        baseline_cases = _case_index(before["cases"])
        candidate_cases = _case_index(after["cases"])
        overall_baseline = cls._overall(before)
        overall_candidate = cls._overall(after)
        agent_baseline = cls._agent(before)
        agent_candidate = cls._agent(after)
        before_errors = FailureDiagnosis.analyze(before["cases"])["error_distribution"]
        after_errors = FailureDiagnosis.analyze(after["cases"])["error_distribution"]
        error_names = sorted(before_errors.keys() | after_errors.keys())

        regressions: list[dict[str, Any]] = []
        improvements: list[dict[str, Any]] = []
        result_changes: list[dict[str, Any]] = []
        for case_id in sorted(baseline_cases.keys() & candidate_cases.keys()):
            old = baseline_cases[case_id]
            new = candidate_cases[case_id]
            old_correct = _metric(old, "result_metrics", "correct", "result_correct")
            new_correct = _metric(new, "result_metrics", "correct", "result_correct")
            old_sql_success = _metric(old, "sql_metrics", "execution_success", "sql_execution_success")
            new_sql_success = _metric(new, "sql_metrics", "execution_success", "sql_execution_success")
            old_columns = _metric(old, "result_metrics", "column_match", "column_match")
            new_columns = _metric(new, "result_metrics", "column_match", "column_match")
            old_rows = _metric(old, "result_metrics", "generated_result_rows", "generated_result_rows")
            new_rows = _metric(new, "result_metrics", "generated_result_rows", "generated_result_rows")
            change = {
                "case_id": case_id,
                "baseline_correct": old_correct,
                "candidate_correct": new_correct,
                "baseline_sql_success": old_sql_success,
                "candidate_sql_success": new_sql_success,
                "baseline_column_match": old_columns,
                "candidate_column_match": new_columns,
                "baseline_result_rows": old_rows,
                "candidate_result_rows": new_rows,
            }
            if (old_correct != new_correct or old_sql_success != new_sql_success
                    or old_columns != new_columns or old_rows != new_rows):
                result_changes.append(change)
            if old_correct is True and new_correct is False:
                regressions.append(change)
            elif old_correct is False and new_correct is True:
                improvements.append(change)

        return RegressionResult(
            baseline_snapshot_id=str(before.get("snapshot_id") or "baseline"),
            candidate_snapshot_id=str(after.get("snapshot_id") or "candidate"),
            dataset_match=(
                isinstance(baseline_manifest, dict)
                and isinstance(candidate_manifest, dict)
                and not any(
                    item.startswith("dataset_version differs")
                    or item.startswith("case_ids differs")
                    or item.endswith("has missing or unexpected cases")
                    for item in warnings
                )
            ),
            comparison_warnings=warnings,
            overall_baseline=overall_baseline,
            overall_candidate=overall_candidate,
            overall_delta={
                key: _delta(overall_baseline[key], overall_candidate[key],
                            digits=3 if key == "average_latency" else 9)
                for key in overall_baseline
            },
            agent_baseline=agent_baseline,
            agent_candidate=agent_candidate,
            agent_delta={
                key: _delta(agent_baseline[key], agent_candidate[key]) for key in agent_baseline
            },
            error_delta={
                "failure_count": sum(after_errors.values()) - sum(before_errors.values()),
                "error_distribution": {
                    key: after_errors.get(key, 0) - before_errors.get(key, 0)
                    for key in error_names
                },
                "baseline_error_distribution": before_errors,
                "candidate_error_distribution": after_errors,
            },
            case_changes={
                "success_to_failure": regressions,
                "failure_to_success": improvements,
                "result_changes": result_changes,
                "added_cases": sorted(candidate_cases.keys() - baseline_cases.keys()),
                "removed_cases": sorted(baseline_cases.keys() - candidate_cases.keys()),
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two saved benchmark snapshots")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument(
        "--allow-incompatible", action="store_true",
        help="Diagnostic comparison only; labels incompatible conditions in the report",
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).resolve().parent / "results" / "regression_report.md",
    )
    args = parser.parse_args()
    result = RegressionComparator.compare(
        args.baseline, args.candidate, allow_incompatible=args.allow_incompatible,
    )
    from evaluation.regression_report import RegressionReportBuilder

    RegressionReportBuilder.write_markdown(result, args.output)
    print(f"regression report: {args.output}")


if __name__ == "__main__":
    main()
