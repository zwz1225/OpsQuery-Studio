"""Permission observability metrics calculated from a trace snapshot."""

from __future__ import annotations

from collections import Counter
from typing import Any


class PermissionMetricsCalculator:
    """Calculate per-query permission metrics without changing authorization."""

    @staticmethod
    def calculate(permission: dict[str, Any] | None) -> dict[str, Any]:
        data = permission or {}
        checked = bool(data.get("checked"))
        denied = bool(data.get("sql_blocked")) or bool(data.get("denied_reason"))
        before = data.get("schema_before_filter_count")
        after = data.get("schema_after_filter_count")
        filtered = 0
        if isinstance(before, int) and isinstance(after, int):
            filtered = max(0, before - after)

        roles = [str(role) for role in data.get("roles") or []]
        return {
            "permission_check_count": 1 if checked else 0,
            "permission_success_rate": (1.0 if not denied else 0.0) if checked else None,
            "permission_denied_count": 1 if denied else 0,
            "schema_permission_filter_count": filtered,
            "sql_permission_blocked_count": 1 if data.get("sql_blocked") else 0,
            "role_distribution": dict(Counter(roles)),
        }

