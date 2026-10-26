"""Resolve standard results without depending on the model or database client."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile
from typing import Any

from app.datasources.contracts import SourceIdentity
from app.datasources.dialects import validated_source
from evaluation.gold_sql import select_gold_sql
from evaluation.result_policy import SCORING_ROW_LIMIT, result_policy, valid_result, evidence_digest


DEFAULT_CACHE_DIR = Path(__file__).parent / "cache" / "gold_results"
GOLD_CACHE_VERSION = 3


def resolve_gold_result(case: dict[str, Any], engine: Any, scope: Any, *,
                        cache_dir: Path = DEFAULT_CACHE_DIR,
                        use_cached_gold: bool = True,
                        data_version: str = "",
                        max_result_rows: int = SCORING_ROW_LIMIT) -> dict[str, Any]:
    """Cache -> execute gold SQL -> legacy rows (only when SQL is absent).

    Cache validity includes the database content digest. Unversioned direct
    calls are supported for tests; benchmark runs always provide a digest.
    """
    source = getattr(engine, "source_identity", None)
    if isinstance(source, SourceIdentity):
        validated_source(source)
        engine.require_open()
        if data_version and data_version != source.data_version:
            raise ValueError("Gold data version differs from executor datasource")
        data_version = source.data_version
        cache_dir = Path(cache_dir) / source.source_id
    selection = select_gold_sql(case, source if isinstance(source, SourceIdentity) else None)
    sql = selection.sql
    database = source.logical_database_id if isinstance(source, SourceIdentity) else "short_video_ops"
    identity = {
        "gold_cache_version": GOLD_CACHE_VERSION,
        "result_policy": result_policy(case, max_result_rows),
        "gold_selection": selection.public(),
        **({"source_identity": source.public()} if isinstance(source, SourceIdentity) else {}),
        "case_id": case["case_id"], "question": case["query"], "gold_sql": sql,
        "database": database, "scenario": case["scenario"],
        "scope": json.loads(json.dumps(scope.public(), sort_keys=True)),
        "data_version": data_version,
        "max_result_rows": max_result_rows,
    }
    # Keep the case recognizable while preventing path traversal. The hash
    # makes collisions between unusual IDs impossible.
    case_id = str(case["case_id"])
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", case_id).strip("._") or "case"
    suffix = hashlib.sha256(case_id.encode()).hexdigest()[:12]
    filename = f"{safe_id}_{suffix}.json"
    path = Path(cache_dir) / filename
    if use_cached_gold and path.exists():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            valid = all(cached.get(key) == value for key, value in identity.items())
            columns, rows = cached["columns"], cached["rows"]
            valid = valid and valid_result(columns, rows, max_result_rows)
            if valid:
                return {**cached, "rows": [{c: r[c] for c in columns} for r in rows],
                        "source": "cache", "cache_path": str(path), "generated": False,
                        "execution_ms": None}
        except (ValueError, KeyError, TypeError):
            pass  # Invalid cache is regenerated, never used as a gold answer.
    if not sql:
        return {**identity, "columns": case["expected_columns"],
                "rows": case["expected_rows"], "source": "expected_rows",
                "cache_path": "", "generated": False, "execution_ms": 0.0}
    execution = engine.execute(database, sql, scope, row_limit=max_result_rows)
    if not execution.success:
        raise RuntimeError(f"Gold SQL execution failed: {execution.error}")
    if getattr(execution, "truncated", False):
        raise RuntimeError(f"Gold result exceeds scoring limit of {max_result_rows} rows")
    if not valid_result(execution.columns, execution.rows, max_result_rows):
        raise RuntimeError("Gold result has invalid columns, rows or non-finite values")
    payload = {**identity, "columns": execution.columns, "rows": execution.rows,
               "generated_at": datetime.now(timezone.utc).isoformat()}
    path.parent.mkdir(parents=True, exist_ok=True)
    # Unique temporary files also support concurrent runs of the same case.
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         suffix=".tmp", delete=False) as stream:
            temp_path = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2)
        temp_path.replace(path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return {**payload, "source": "execution", "cache_path": str(path),
            "generated": True, "execution_ms": execution.execution_ms}


def gold_result_evidence(gold: dict[str, Any]) -> dict[str, Any]:
    """Self-contained scoring evidence for Gold reports; never sent to a model."""
    payload = {key: gold.get(key) for key in (
        "gold_cache_version", "source_identity", "case_id", "question", "scenario",
        "database", "scope", "data_version", "gold_selection", "gold_sql",
        "max_result_rows", "result_policy", "columns", "rows", "generated_at",
    )}
    payload["result_source"] = gold["source"]
    return json.loads(json.dumps({**payload, "sha256": evidence_digest(payload)}, ensure_ascii=False, allow_nan=False))


def gold_metrics(gold: dict[str, Any], generated_rows: int) -> dict[str, Any]:
    return {
        "comparison_target": "expected_rows" if gold["source"] == "expected_rows" else "gold_result",
        "gold_result_source": gold["source"],
        "gold_result_generated": gold["generated"],
        "gold_result_cache_path": gold["cache_path"],
        "generated_result_rows": generated_rows,
        "gold_result_rows": len(gold["rows"]),
        "gold_sql": gold["gold_sql"],
        "gold_dialect": gold["gold_selection"]["dialect"],
        "gold_selection_key": gold["gold_selection"]["selection_key"],
        "gold_selection_version": gold["gold_selection"]["selection_version"],
    }
