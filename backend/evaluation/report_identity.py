"""Validate declared source identities before copying or resuming reports."""
from __future__ import annotations

from typing import Any
import re

from app.datasources.dialects import validated_source
from evaluation.run_manifest import _digest


def validate_report_identity(report: dict[str, Any], *, allow_partial: bool = False) -> dict:
    manifest = report.get("run_manifest")
    if not isinstance(manifest, dict):
        raise ValueError("Report has no run manifest")
    source = validated_source(manifest.get("source_identity") or {})
    versions = manifest.get("versions") or {}
    if versions.get("data") != source["data_version"] or versions.get("schema") != source["catalog_version"]:
        raise ValueError("Report source and version labels differ")
    if manifest.get("manifest_version") not in (3, 4):
        raise ValueError("Unsupported or legacy manifest version")
    expected = (manifest.get("dataset") or {}).get("case_ids")
    cases = report.get("cases")
    if not isinstance(expected, list) or not expected or len(set(expected)) != len(expected) or not isinstance(cases, list):
        raise ValueError("Invalid report case list")
    actual = [c.get("case_id") for c in cases if isinstance(c, dict)]
    if len(actual) != len(cases) or len(set(actual)) != len(actual):
        raise ValueError("Duplicate or malformed report cases")
    if (not allow_partial and actual != expected) or any(c not in expected for c in actual):
        raise ValueError("Report has missing or unexpected cases")
    if report.get("mode", manifest["mode"]) != manifest["mode"]:
        raise ValueError("Report and manifest modes differ")
    comparable = {k: v for k, v in manifest.items() if k not in ("run_id", "created_at", "fingerprint")}
    if manifest.get("fingerprint") != _digest(comparable):
        raise ValueError("Report manifest fingerprint is invalid")
    if manifest["manifest_version"] >= 4:
        policy = manifest.get("result_policy")
        if not isinstance(policy, dict) or versions.get("result_policy") != _digest(policy):
            raise ValueError("Report result policy identity is invalid")
        verification = manifest.get("source_verification") or {}
        if verification.get("data_version") != source["data_version"] or verification.get("catalog_version") != source["catalog_version"]:
            raise ValueError("Report verified source versions differ")
        if source["backend"] == "postgresql" and (verification.get("kind") != "live_postgresql_verification"
                or verification.get("live_target_verified") is not True
                or not re.fullmatch(r"[0-9a-f]{64}", str(versions.get("physical_schema", "")))
                or verification.get("physical_schema_version") != versions.get("physical_schema")):
            raise ValueError("Report lacks matching live PostgreSQL verification")
    if report.get("source_identity") is not None and validated_source(report["source_identity"]) != source:
        raise ValueError("Report root source identity differs from manifest")
    if report.get("backend", source["backend"]) != source["backend"] or report.get("dialect", source["dialect"]) != source["dialect"]:
        raise ValueError("Report root backend/dialect differs from manifest")
    for row in cases:
        trace = row.get("trace") or {}
        execution = trace.get("sql_execution") or {} if isinstance(trace, dict) else {}
        for labels in (row, execution):
            if labels.get("source_identity") is not None and validated_source(labels["source_identity"]) != source:
                raise ValueError("Case source identity differs from report manifest")
            if labels.get("backend", source["backend"]) != source["backend"] or labels.get("dialect", source["dialect"]) != source["dialect"]:
                raise ValueError("Case backend/dialect differs from report manifest")
        if row.get("run_id", manifest["run_id"]) != manifest["run_id"]:
            raise ValueError("Case run_id differs from report manifest")
    return manifest


def require_resumable(previous: dict[str, Any], current_manifest: dict[str, Any]) -> dict:
    old = validate_report_identity(previous, allow_partial=True)
    if old["source_identity"] != current_manifest.get("source_identity"):
        raise ValueError("Cannot resume across datasource identities")
    comparable = {k: v for k, v in current_manifest.items() if k not in ("run_id", "created_at", "fingerprint")}
    if current_manifest.get("fingerprint") != _digest(comparable) or old["fingerprint"] != current_manifest["fingerprint"]:
        raise ValueError("Cannot resume: run inputs or versions differ from saved report")
    return old
