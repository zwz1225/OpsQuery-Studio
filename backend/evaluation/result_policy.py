"""Versioned result strategy; changing these identities invalidates cached evidence.

Comparison algorithms remain in run_benchmark.py. This module records their
existing contract, without relaxing names, tolerance, order or tie handling.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

RESULT_POLICY_VERSION = 1
RESULT_NORMALIZATION_VERSION = 1
SCORING_ROW_LIMIT = 10000


def result_policy(case: dict[str, Any], row_limit: int = SCORING_ROW_LIMIT) -> dict[str, Any]:
    if isinstance(row_limit, bool) or not isinstance(row_limit, int) or not 1 <= row_limit <= SCORING_ROW_LIMIT:
        raise ValueError("Scoring row limit must be 1..10000")
    return json.loads(json.dumps({
        "version": RESULT_POLICY_VERSION, "normalization_version": RESULT_NORMALIZATION_VERSION,
        "row_limit": row_limit, "reject_truncation": True,
        "numeric_comparison": "existing_business_tolerance_v1",
        "column_mapping": "explicit_per_case_aliases_v1",
        "expected_columns": case.get("expected_columns"),
        "order_sensitive": bool(case.get("order_sensitive", True)),
        "order_by_column": case.get("order_by_column"),
        "column_aliases": case.get("column_aliases") or {},
        "allowed_auxiliary_columns": case.get("allowed_auxiliary_columns") or [],
        "top_n_tie_policy": case.get("top_n_tie_policy"),
    }, ensure_ascii=False, sort_keys=True, allow_nan=False))


def policy_identity(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {"version": RESULT_POLICY_VERSION, "cases": [
        {"case_id": c["case_id"], "policy": result_policy(c)} for c in cases]}


def evidence_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def valid_result(columns: Any, rows: Any, row_limit: int) -> bool:
    if (not isinstance(columns, list) or not all(isinstance(c, str) and c for c in columns)
            or len(set(columns)) != len(columns) or not isinstance(rows, list) or len(rows) > row_limit):
        return False
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(columns):
            return False
        for value in row.values():
            if value is not None and not isinstance(value, (str, bool, int, float)):
                return False
            if isinstance(value, float) and not math.isfinite(value):
                return False
    return True
