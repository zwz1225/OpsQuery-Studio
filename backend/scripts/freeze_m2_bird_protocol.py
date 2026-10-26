"""Freeze/check M2 inputs without connecting to a DB or a model.

Run from backend. Existing bundles and reports are never overwritten.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from evaluation.bird_protocol import (
    ARCHIVE_SHA256, DATASET_REVISION, PROTOCOL_ID, QUESTIONS_SHA256, SQL_DUMP_SHA256,
    UPSTREAM_COMMIT, UPSTREAM_EX_SHA256, UPSTREAM_UTILS_SHA256, BirdProtocolError,
    json_bytes, load_canonical_questions, make_bundle, sha256,
)

PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = PROJECT.parent / "datasets/bird_mini_dev"
DEFAULT_REPO = PROJECT.parent / "bird-mini-dev"
DEFAULT_OUTPUT = PROJECT / "backend/evaluation/cases/bird_mini_dev/m2_pg_v1"


def hash_file(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def official_reference(repo: Path) -> tuple[dict, dict[str, bytes]]:
    paths = {"evaluation_ex.py": UPSTREAM_EX_SHA256, "evaluation_utils.py": UPSTREAM_UTILS_SHA256}
    sources = {}
    for name, expected in paths.items():
        data = subprocess.check_output(["git", "-C", str(repo), "show", f"{UPSTREAM_COMMIT}:evaluation/{name}"])
        if sha256(data) != expected:
            raise BirdProtocolError(f"Official reference content changed: {name}")
        sources[name] = data.decode("utf-8")
    functions = {}
    for file, function in (("evaluation_ex.py", "calculate_ex"), ("evaluation_utils.py", "execute_sql")):
        tree = ast.parse(sources[file])
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function)
        functions[function] = (ast.get_source_segment(sources[file], node) + "\n").encode("utf-8")
    return {
        "repository": "https://github.com/bird-bench/mini_dev", "commit": UPSTREAM_COMMIT,
        "ex_file_sha256": UPSTREAM_EX_SHA256, "utils_file_sha256": UPSTREAM_UTILS_SHA256,
        "ex_source_url": f"https://github.com/bird-bench/mini_dev/blob/{UPSTREAM_COMMIT}/evaluation/evaluation_ex.py#L18",
        "calculate_ex_function_sha256": sha256(functions["calculate_ex"]),
        "execute_sql_function_sha256": sha256(functions["execute_sql"]),
        "snapshot_method": "git show pinned_commit:path (raw Git bytes, independent of checkout line endings)",
        "review_note": "Retain comparator semantics only; official connection helpers and fallback db_id behavior are not used",
    }, {"reference/official_calculate_ex.py.txt": functions["calculate_ex"],
        "reference/official_execute_sql.py.txt": functions["execute_sql"]}


def source_lineage(data_root: Path) -> tuple[list[dict], dict]:
    release = data_root / "releases" / ("hf_" + DATASET_REVISION)
    question_path = release / "mini_dev_pg-00000-of-00001.json"
    rows = load_canonical_questions(question_path.read_bytes())
    metadata = json.loads((release / "source_metadata.json").read_text(encoding="utf-8"))
    if metadata["sha"] != DATASET_REVISION or metadata["cardData"]["license"] != "cc-by-sa-4.0":
        raise BirdProtocolError("Dataset metadata version/license changed")
    required = {
        "archives": (data_root / "downloads/minidev_0703.zip", ARCHIVE_SHA256),
        "postgres_dump": (data_root / "extracted/minidev/MINIDEV_postgresql/BIRD_dev.sql", SQL_DUMP_SHA256),
    }
    files = []
    for kind, (path, expected) in required.items():
        digest = hash_file(path)
        if digest != expected:
            raise BirdProtocolError(f"Source changed: {kind}")
        files.append({"kind": kind, "relative_to_data_root": path.relative_to(data_root).as_posix(),
                      "size_bytes": path.stat().st_size, "sha256": digest})
    tables_path = data_root / "extracted/minidev/MINIDEV/dev_tables.json"
    tables = json.loads(tables_path.read_bytes())
    if {t["db_id"] for t in tables} != {r["db_id"] for r in rows}:
        raise BirdProtocolError("Logical schemas do not cover the canonical question databases")
    csvs = sorted((data_root / "extracted/minidev/MINIDEV/dev_databases").glob("*/database_description/*.csv"))
    if len(csvs) != 75:
        raise BirdProtocolError("Expected all 75 official column descriptions")
    acquisition = json.loads((PROJECT / "backend/evaluation/results/m2_a_data_ready_20261015.json").read_text(encoding="utf-8"))
    expected_files = {r["path"]: r["sha256"] for r in acquisition["extracted_files"]}
    for path in [tables_path, *csvs]:
        digest = hash_file(path)
        member = path.relative_to(data_root / "extracted").as_posix()
        if digest != expected_files[member]:
            raise BirdProtocolError(f"Description/schema source changed: {member}")
        files.append({"kind": "logical_schema" if path == tables_path else "column_description",
                      "relative_to_data_root": path.relative_to(data_root).as_posix(),
                      "size_bytes": path.stat().st_size, "sha256": digest})
    return rows, {
        "dataset_revision": DATASET_REVISION, "questions_sha256": QUESTIONS_SHA256,
        "question_relative_path": question_path.relative_to(data_root).as_posix(),
        "question_count": 500, "logical_database_count": 11,
        "files": files, "target_live_data_version": None,
        "scope": "Frozen local source files; verified target data/catalog identity will be bound after import",
        "acquisition_evidence_sha256": hash_file(PROJECT / "backend/evaluation/results/m2_a_data_ready_20261015.json"),
        "antivirus_evidence": "User reported Tencent scan completed with no threats; machine scan log not reviewed",
    }


def write_or_check_bundle(output: Path, artifacts: dict[str, bytes], *, check: bool) -> None:
    if check:
        actual = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}
        if actual != set(artifacts):
            raise BirdProtocolError("Frozen bundle file set changed")
        for name, expected in artifacts.items():
            if (output / name).read_bytes() != expected:
                raise BirdProtocolError(f"Frozen artifact differs: {name}")
        return
    if output.exists():
        raise BirdProtocolError("Choose a new bundle directory, or use --check; preserve previous versions")
    output.mkdir(parents=True)
    for name, data in sorted(artifacts.items()):
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--official-repo", type=Path, default=DEFAULT_REPO)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report_path = args.report.resolve()
    if report_path.exists():
        raise BirdProtocolError("Choose a new report path; preserve previous evidence")
    if report_path.is_relative_to(args.output_dir.resolve()):
        raise BirdProtocolError("Audit reports must be outside the immutable bundle")
    rows, lineage = source_lineage(args.data_root.resolve())
    reference, reference_files = official_reference(args.official_repo.resolve())
    bundle = make_bundle(rows, lineage, reference, reference_files)
    write_or_check_bundle(args.output_dir.resolve(), bundle, check=args.check)
    protocol = json.loads(bundle["protocol.json"])
    development = json.loads(bundle["development80.json"])
    holdout = json.loads(bundle["holdout30.json"])
    report = {
        "stage": "M2 A protocol and deterministic database-separated split",
        "run_status": "complete", "operation": "check" if args.check else "freeze",
        "recorded_at": datetime.now(timezone.utc).isoformat(), "protocol_id": PROTOCOL_ID,
        "protocol_sha256": sha256(bundle["protocol.json"]), "artifact_count": len(bundle),
        "artifacts": {name: sha256(data) for name, data in sorted(bundle.items())},
        "development_case_count": 80, "holdout_case_count": 30, "smoke_case_count": 8,
        "development_databases": development["database_ids"], "holdout_databases": holdout["database_ids"],
        "development_difficulty_counts": development["difficulty_counts"],
        "holdout_difficulty_counts": holdout["difficulty_counts"],
        "official_evidence_provided": True, "scoring_policy": protocol["scoring"]["policy_id"],
        "upstream_commit": UPSTREAM_COMMIT,
        "runtime_integration_ready": False, "postgresql_connected": False,
        "database_imported": False, "gold_execution_verified": False, "new_model_request_count": 0,
        "next": "Controlled import plan and generic source adapter; no existing internal runner is claimed compatible",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("xb") as stream:
        stream.write(json_bytes(report))
    print(json.dumps({k:v for k,v in report.items() if k != "artifacts"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
