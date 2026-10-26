"""Metrics calculated from evaluation trace data."""

from __future__ import annotations

from collections import Counter
import math
from typing import Any


class ToolMetricsCalculator:
    """Calculate MCP tool calling metrics without executing any tool."""

    @staticmethod
    def calculate(tool_calls: list[dict[str, Any]] | None) -> dict[str, Any]:
        calls = list(tool_calls or [])
        count = len(calls)
        usage = Counter(str(call.get("tool_name") or "unknown") for call in calls)
        if not count:
            return {
                "tool_call_count": 0,
                "tool_success_rate": None,
                "tool_failure_rate": None,
                "average_tool_latency_ms": None,
                "p95_tool_latency_ms": None,
                "tool_retry_count": 0,
                "tool_usage_distribution": {},
            }

        successes = sum(bool(call.get("success")) for call in calls)
        latencies: list[float] = []
        retries = 0
        for call in calls:
            latency = call.get("latency_ms")
            if isinstance(latency, (int, float)) and not isinstance(latency, bool):
                if math.isfinite(float(latency)):
                    latencies.append(float(latency))
            retry_count = call.get("retry_count", 0)
            if isinstance(retry_count, (int, float)) and not isinstance(retry_count, bool):
                retries += max(0, int(retry_count))

        ordered = sorted(latencies)
        p95 = None
        average = None
        if ordered:
            average = round(sum(ordered) / len(ordered), 3)
            index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1))
            p95 = round(ordered[index], 3)

        return {
            "tool_call_count": count,
            "tool_success_rate": round(successes / count, 6),
            "tool_failure_rate": round((count - successes) / count, 6),
            "average_tool_latency_ms": average,
            "p95_tool_latency_ms": p95,
            "tool_retry_count": retries,
            "tool_usage_distribution": dict(usage),
        }

