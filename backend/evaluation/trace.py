"""Structured execution trace for one evaluation case."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EvaluationTrace:
    """Serializable trace sections collected by the benchmark runners."""

    request: dict[str, Any] = field(default_factory=dict)
    routing: dict[str, Any] = field(default_factory=dict)
    permission: dict[str, Any] = field(default_factory=dict)
    clarification: dict[str, Any] = field(default_factory=dict)
    schema_retrieval: dict[str, Any] = field(default_factory=dict)
    agent_decision: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    sql_execution: dict[str, Any] = field(default_factory=dict)
    result_comparison: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible copy without exposing mutable internals."""
        return asdict(self)
