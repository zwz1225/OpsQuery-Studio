"""Validated case manifests for reproducible evaluation subsets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_case_ids(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    ids = payload.get("case_ids") if isinstance(payload, dict) else None
    if not isinstance(ids, list) or not ids or any(
        not isinstance(item, str) or not item.strip() for item in ids
    ):
        raise ValueError(f"Invalid or empty case_ids in {path}")
    if len(set(ids)) != len(ids):
        raise ValueError(f"Duplicate case_id in {path}")
    return ids


def select_cases(cases: list[dict[str, Any]], case_ids: list[str]) -> list[dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for case in cases:
        case_id = str(case["case_id"])
        if case_id in indexed:
            raise ValueError(f"Duplicate case_id in case source: {case_id}")
        indexed[case_id] = case
    missing = [case_id for case_id in case_ids if case_id not in indexed]
    if missing:
        raise ValueError(f"Case IDs absent from the selected scope: {', '.join(missing)}")
    return [indexed[case_id] for case_id in case_ids]
