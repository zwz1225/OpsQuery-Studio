"""Reproducible identities for evaluation datasets, data, code, and runs."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid
from typing import Any
from app.datasources.runtime import DataSourceRuntime
from app.datasources.dialects import validated_source
from evaluation.gold_sql import gold_selection_identity
from evaluation.result_policy import policy_identity


MANIFEST_VERSION = 4
EVALUATOR_FILES = (
    "evaluation/run_benchmark.py",
    "evaluation/run_e2e.py",
    "evaluation/gold_result.py",
    "evaluation/gold_sql.py",
    "evaluation/models.py",
    "evaluation/result_policy.py",
    "evaluation/report_identity.py",
    "evaluation/compare_backends.py",
)


def _digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def files_digest(root: Path, paths: list[Path]) -> str:
    """Hash relative names and contents so additions, removals, and edits matter."""
    entries = []
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix()):
        entries.append({
            "path": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    return _digest(entries)


def data_digest(base_dir: Path) -> str:
    folder = base_dir / "data" / "databases" / "short_video_ops"
    paths = [path for path in folder.iterdir() if path.is_file() and
             (path.suffix == ".csv" or path.name == "_schema.json")]
    if not paths or not (folder / "_schema.json").exists():
        raise FileNotFoundError(f"Missing database files under {folder}")
    return files_digest(base_dir, paths)


def build_run_manifest(
    cases: list[dict[str, Any]],
    *,
    base_dir: Path,
    mode: str,
    scope: str,
    config: dict[str, Any],
    case_source: Path,
    case_list: Path | None = None,
    source_identity: dict[str, str] | None = None,
    runtime: DataSourceRuntime | None = None,
) -> dict[str, Any]:
    if not cases:
        raise ValueError("An evaluation run needs at least one case")
    case_ids = [str(case["case_id"]) for case in cases]
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("Duplicate case_id in evaluation run")
    if runtime is not None:
        runtime.require_open()
        actual_source = validated_source(runtime.identity)
        if source_identity is not None and validated_source(source_identity) != actual_source:
            raise ValueError("Manifest datasource differs from runtime")
        source_identity = actual_source
    elif source_identity is not None:
        source_identity = validated_source(source_identity)
        if source_identity["backend"] == "postgresql":
            raise ValueError("PostgreSQL manifest requires a verified runtime")
    gold_selection = gold_selection_identity(cases, source_identity)
    result_policy = policy_identity(cases)
    app_files = list((base_dir / "app").rglob("*.py"))
    app_files.append(base_dir / "data" / "metrics" / "metric_catalog.json")
    skill_files = list((base_dir / "app" / "skills").rglob("SKILL.md"))
    skill_files += list((base_dir / "app" / "skills").rglob("config.json"))
    evaluation_files = list((base_dir / "evaluation").glob("*.py"))
    evaluator_files = [base_dir / item for item in EVALUATOR_FILES]
    if any(not path.is_file() for path in evaluator_files):
        raise FileNotFoundError("Evaluator source files are missing")
    if not case_source.is_file():
        raise FileNotFoundError(case_source)
    resolved_case_list = (
        (base_dir / case_list).resolve() if case_list and not case_list.is_absolute()
        else case_list
    )
    dataset = {
        "source": case_source.relative_to(base_dir).as_posix(),
        "case_list": (
            resolved_case_list.relative_to(base_dir).as_posix()
            if resolved_case_list and resolved_case_list.is_relative_to(base_dir)
            else resolved_case_list.as_posix() if resolved_case_list else None
        ),
        "case_ids": case_ids,
        "version": _digest(cases),
    }
    versions = {
        "data": source_identity["data_version"] if source_identity else data_digest(base_dir),
        "schema": source_identity["catalog_version"] if source_identity else hashlib.sha256(
            (base_dir / "data" / "databases" / "short_video_ops" / "_schema.json").read_bytes()
        ).hexdigest(),
        "application": files_digest(base_dir, app_files + skill_files),
        "evaluator": files_digest(base_dir, evaluator_files),
        "evaluation_code": files_digest(base_dir, evaluation_files),
        "gold_selection": _digest(gold_selection),
        "result_policy": _digest(result_policy),
    }
    if source_identity and source_identity["backend"] == "duckdb" and source_identity["data_version"] != data_digest(base_dir):
        raise ValueError("Manifest data version differs from actual datasource")
    if source_identity and source_identity["backend"] == "postgresql":
        verification = getattr(runtime.metadata, "verification", None)
        if not isinstance(verification, dict) or verification.get("live_target_verified") is not True or any(
            verification.get(key) != source_identity[key] for key in ("data_version", "catalog_version")
        ):
            raise ValueError("PostgreSQL manifest requires matching live verification")
        physical = verification.get("physical_schema_version")
        if not isinstance(physical, str) or len(physical) != 64 or any(c not in "0123456789abcdef" for c in physical):
            raise ValueError("PostgreSQL manifest requires a physical schema version")
        versions["physical_schema"] = physical
    verification_labels = None
    if runtime is not None:
        if source_identity["backend"] == "postgresql":
            verification_labels = {"kind": "live_postgresql_verification", **{
                key: runtime.metadata.verification.get(key) for key in (
                    "live_target_verified", "data_version", "catalog_version", "physical_schema_version",
                    "table_count", "field_count", "row_count", "full_typed_row_match_count",
                    "readonly_table_acl_match_count", "readonly_column_acl_match_count")}}
        else:
            verification_labels = {"kind": "csv_content_digest", "data_version": source_identity["data_version"],
                                   "catalog_version": source_identity["catalog_version"]}
    comparable = {
        **({"source_identity": source_identity} if source_identity else {}),
        "manifest_version": MANIFEST_VERSION,
        "mode": mode,
        "scope": scope,
        "dataset": dataset,
        "gold_selection": gold_selection,
        "result_policy": result_policy,
        **({"source_verification": verification_labels} if verification_labels else {}),
        "versions": versions,
        "config": config,
    }
    return {
        **comparable,
        "run_id": uuid.uuid4().hex,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "fingerprint": _digest(comparable),
    }


def comparison_identity(manifest: dict[str, Any]) -> dict[str, Any]:
    """Conditions that must match before two runs can be scored as a regression."""
    versions = manifest.get("versions") or {}
    dataset = manifest.get("dataset") or {}
    config = manifest.get("config") or {}
    return {
        "manifest_version": manifest.get("manifest_version"),
        "mode": manifest.get("mode"),
        "source_identity": manifest.get("source_identity"),
        "dataset_version": dataset.get("version"),
        "case_ids": dataset.get("case_ids"),
        "data_version": versions.get("data"),
        "schema_version": versions.get("schema"),
        "physical_schema_version": versions.get("physical_schema"),
        "gold_selection_version": versions.get("gold_selection"),
        "result_policy_version": versions.get("result_policy"),
        "evaluator_version": versions.get("evaluator"),
        "user_roles": config.get("user_roles"),
        "evaluation_date": config.get("evaluation_date"),
    }
