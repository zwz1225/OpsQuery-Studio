"""Clarification observability metrics calculated from trace data."""

from __future__ import annotations

from typing import Any


class ClarificationMetricsCalculator:
    """Calculate clarification counts for one query or a sequence of events."""

    @staticmethod
    def _events(clarification: dict[str, Any] | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        if clarification is None:
            return []
        if isinstance(clarification, list):
            return [item for item in clarification if isinstance(item, dict)]
        events = clarification.get("events")
        if isinstance(events, list):
            return [item for item in events if isinstance(item, dict)]
        return [clarification]

    @staticmethod
    def calculate(
        clarification: dict[str, Any] | list[dict[str, Any]] | None,
        *,
        total_queries: int = 1,
    ) -> dict[str, Any]:
        events = ClarificationMetricsCalculator._events(clarification)
        triggered = [event for event in events if bool(event.get("triggered"))]
        response_count = sum(bool(event.get("user_responded")) for event in triggered)
        resolution_count = 0
        abandon_count = 0
        for event in triggered:
            status = str(event.get("final_status") or "").lower()
            failed_status = status in {"failed", "error", "abandoned", "cancelled", "canceled"}
            resolved = bool(event.get("user_responded")) and bool(
                event.get("continued_execution")
            ) and not failed_status
            if resolved:
                resolution_count += 1
            if status in {"abandoned", "cancelled", "canceled"} or (
                not event.get("user_responded") and not event.get("continued_execution")
            ):
                abandon_count += 1

        trigger_count = len(triggered)
        denominator = max(0, int(total_queries))
        return {
            "clarification_trigger_count": trigger_count,
            "clarification_response_count": response_count,
            "clarification_resolution_count": resolution_count,
            "clarification_abandon_count": abandon_count,
            "clarification_rate": (
                min(1.0, round(trigger_count / denominator, 6)) if denominator else None
            ),
            "clarification_resolution_rate": (
                round(resolution_count / trigger_count, 6) if trigger_count else None
            ),
        }
