"""Immutable, self-contained snapshots of completed benchmark reports."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any
from evaluation.report_identity import validate_report_identity


DEFAULT_SNAPSHOT_DIR = Path(__file__).resolve().parent / "results" / "snapshots"
MODEL_METADATA_KEYS = ("llm_model", "embedding_model", "rerank_model")


class BenchmarkSnapshotManager:
    """Copy an existing benchmark JSON into a timestamped snapshot."""

    @staticmethod
    def load(path: Path | str) -> dict[str, Any]:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Benchmark snapshot must contain a JSON object")
        return payload

    @classmethod
    def save(
        cls,
        benchmark: Path | str | dict[str, Any],
        *,
        mode: str,
        scope: str,
        dataset: str | dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        run_manifest: dict[str, Any] | None = None,
        snapshot_dir: Path | str = DEFAULT_SNAPSHOT_DIR,
        created_at: datetime | None = None,
    ) -> Path:
        source = cls.load(benchmark) if isinstance(benchmark, (Path, str)) else benchmark
        if not isinstance(source, dict) or not isinstance(source.get("summary"), dict):
            raise ValueError("Benchmark report must contain a summary object")
        cases = source.get("cases")
        if not isinstance(cases, list):
            raise ValueError("Benchmark report must contain a cases list")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", mode) or not re.fullmatch(
            r"[A-Za-z0-9_-]+", scope
        ):
            raise ValueError("mode and scope must be non-empty filename-safe values")
        inherited_manifest = source.get("run_manifest")
        if run_manifest is not None and inherited_manifest is not None and run_manifest != inherited_manifest:
            raise ValueError("Supplied snapshot manifest differs from benchmark report")
        run_manifest = run_manifest if run_manifest is not None else inherited_manifest
        source_identity = None
        if run_manifest is not None:
            validated = validate_report_identity({**source, "run_manifest": run_manifest})
            if (mode, scope) != (validated["mode"], validated["scope"]):
                raise ValueError("Snapshot mode/scope differs from benchmark manifest")
            source_identity = validated["source_identity"]
            if isinstance(dataset, dict) and "case_ids" in dataset and dataset["case_ids"] != validated["dataset"]["case_ids"]:
                raise ValueError("Snapshot dataset differs from benchmark manifest")
            metadata_labels = metadata or {}
            if metadata_labels.get("data_backend", source_identity["backend"]) != source_identity["backend"] or metadata_labels.get("data_source_id", source_identity["source_id"]) != source_identity["source_id"]:
                raise ValueError("Snapshot metadata source differs from benchmark manifest")

        timestamp = created_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        timestamp = timestamp.astimezone(timezone.utc)
        stamp = timestamp.strftime("%Y%m%dT%H%M%S%fZ")
        snapshot_id = f"benchmark_{mode}_{scope}_{stamp}"
        folder = Path(snapshot_dir) / source_identity["source_id"] if source_identity else Path(snapshot_dir)
        destination = folder / f"{snapshot_id}.json"
        if destination.exists():
            raise FileExistsError(f"Snapshot already exists: {destination}")
        supplied_metadata = metadata or {}
        snapshot_metadata = {
            key: supplied_metadata.get(key) for key in MODEL_METADATA_KEYS
        }
        snapshot_metadata.update(supplied_metadata)
        default_dataset = {
            "scope": scope,
            "case_ids": [case.get("case_id") for case in cases if isinstance(case, dict)],
        }
        snapshot = {
            "snapshot_id": snapshot_id,
            "created_at": timestamp.isoformat().replace("+00:00", "Z"),
            "dataset": dataset if dataset is not None else run_manifest["dataset"] if run_manifest else default_dataset,
            "mode": mode,
            "metadata": snapshot_metadata,
            "summary": source["summary"],
            "cases": cases,
            **({"source_identity": source_identity, "run_status": source.get("run_status", "complete")} if source_identity else {}),
            **({"run_manifest": run_manifest} if run_manifest else {}),
        }
        serialized = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
        destination.parent.mkdir(parents=True, exist_ok=True)
        # A snapshot is write-once; an exclusive open avoids silently replacing
        # another run with the same timestamp.
        with destination.open("x", encoding="utf-8") as handle:
            handle.write(serialized)
        return destination
