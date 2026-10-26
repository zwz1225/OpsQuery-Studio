"""Offline BIRD Mini-Dev protocol, deterministic splits and native EX semantics.

This module neither creates a datasource runtime nor calls a model. BIRD's EX
policy is separate from the existing operational-case strict comparison policy.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from typing import Any


PROTOCOL_ID = "m2_bird_pg_v1"
DATASET_REVISION = "f65faf4ae3b638c1fa6df1d3370c8d92c8366301"
QUESTIONS_SHA256 = "7fa740ef9225389cff6c34432120e8325d0ca3008d73db1ae38731234bc10da7"
QUESTION_OBJECTS_SHA256 = "267777cc59514afe7f2fde7c235d697c95f81a75313d2a98e83c86e0a9a471aa"
ARCHIVE_SHA256 = "aeb211c0e39010bbdae3838bb5e8bd27dc446ed77495b1709f85ccc9bf67f2be"
SQL_DUMP_SHA256 = "31b1da211849d24a57c9af7636da46a5b82fc8a3ca1542bb3ebd8775e9a31cec"
UPSTREAM_COMMIT = "abd11b6db92a1c9f809b32f7564c7c71b34d67f0"
UPSTREAM_EX_SHA256 = "da1bbcd4530be83692d7c650c814ea9704bb710d0c953eb75d02ccb38233cf89"
UPSTREAM_UTILS_SHA256 = "f6943d249caac5aeaef9bce21d43dbf29dcef85a0c965a76df032a9542f308bf"
SPLIT_SEED = "askdata-m2-bird-pg-v1"
DIFFICULTIES = {"simple": 3, "moderate": 5, "challenging": 2}
RESULT_ROW_LIMIT = 100_000
PUBLIC_KEYS = frozenset({"case_id", "database_id", "dialect", "question", "evidence"})


class BirdProtocolError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join((json.dumps(row, ensure_ascii=False, sort_keys=True,
                               allow_nan=False) + "\n").encode("utf-8") for row in rows)


def load_canonical_questions(data: bytes) -> list[dict[str, Any]]:
    if sha256(data) != QUESTIONS_SHA256:
        raise BirdProtocolError("Canonical question file hash differs from the frozen revision")
    rows = json.loads(data)
    validate_rows(rows)
    return rows


def validate_rows(rows: Any) -> None:
    keys = {"question_id", "db_id", "question", "evidence", "SQL", "difficulty"}
    if not isinstance(rows, list) or len(rows) != 500:
        raise BirdProtocolError("Expected all 500 canonical PostgreSQL questions")
    ids = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != keys:
            raise BirdProtocolError("Unexpected question schema")
        qid = row["question_id"]
        if type(qid) is not int or qid < 0:
            raise BirdProtocolError("Invalid question_id")
        if any(not isinstance(row[k], str) or not row[k].strip()
               for k in ("db_id", "question", "SQL")) or not isinstance(row["evidence"], str):
            raise BirdProtocolError("Invalid question text or database")
        if row["difficulty"] not in DIFFICULTIES:
            raise BirdProtocolError("Unknown difficulty")
        ids.append(qid)
    if len(ids) != len(set(ids)) or len({r["db_id"] for r in rows}) != 11:
        raise BirdProtocolError("Duplicate question_id or unexpected database count")


def case_id(row: dict[str, Any]) -> str:
    return f"BIRD-PG-{row['question_id']:04d}"


def _rank(scope: str, value: Any) -> str:
    return sha256(f"{SPLIT_SEED}|{scope}|{value}".encode("utf-8"))


def select_splits(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Use only db_id, question_id and difficulty, never SQL or question content."""
    validate_rows(rows)
    databases = sorted({r["db_id"] for r in rows}, key=lambda db: (_rank("database", db), db))
    holdout = set(databases[:3])
    development_rows, holdout_rows, smoke_rows = [], [], []
    for db in sorted(databases):
        chosen = []
        for difficulty, quota in DIFFICULTIES.items():
            candidates = [r for r in rows if r["db_id"] == db and r["difficulty"] == difficulty]
            candidates.sort(key=lambda r: (_rank("question", r["question_id"]), r["question_id"]))
            if len(candidates) < quota:
                raise BirdProtocolError(f"Insufficient {difficulty} questions in {db}; do not silently replace")
            chosen.extend(candidates[:quota])
        chosen.sort(key=lambda r: r["question_id"])
        if db in holdout:
            holdout_rows.extend(chosen)
        else:
            development_rows.extend(chosen)
            smoke_rows.append(min(chosen, key=lambda r: (_rank("smoke", r["question_id"]), r["question_id"])))
    return {"development80": development_rows, "holdout30": holdout_rows,
            "smoke8": sorted(smoke_rows, key=lambda r: (r["db_id"], r["question_id"]))}


def agent_input(row: dict[str, Any]) -> dict[str, Any]:
    payload = {"case_id": case_id(row), "database_id": row["db_id"], "dialect": "postgres",
               "question": row["question"], "evidence": row["evidence"]}
    validate_agent_input(payload)
    return payload


def validate_agent_input(payload: Any) -> None:
    if not isinstance(payload, dict) or set(payload) != PUBLIC_KEYS:
        raise BirdProtocolError("Agent input must contain only the approved public fields")
    if any(not isinstance(v, str) for v in payload.values()):
        raise BirdProtocolError("Agent input values must be text")
    if (payload["dialect"] != "postgres" or not payload["question"].strip()
            or not payload["database_id"].strip() or not payload["case_id"].startswith("BIRD-PG-")):
        raise BirdProtocolError("Invalid external question identity")


def compare_ex_rows(predicted: list[tuple], gold: list[tuple], *,
                    predicted_complete: bool = True, gold_complete: bool = True) -> bool:
    """Pinned upstream set-of-native-tuples predicate, with complete-result guards.

    Native driver values must reach this function before JSON serialization.
    Column names are deliberately not an argument. No rounding or alias rules.
    """
    if predicted_complete is not True or gold_complete is not True:
        raise BirdProtocolError("Incomplete results cannot be scored as full EX")
    for rows in (predicted, gold):
        if not isinstance(rows, list) or len(rows) > RESULT_ROW_LIMIT:
            raise BirdProtocolError("Result row limit exceeded or invalid result container")
        if any(not isinstance(row, tuple) for row in rows):
            raise BirdProtocolError("Expected positional tuples from the database driver")
    try:
        return set(predicted) == set(gold)
    except TypeError as exc:
        raise BirdProtocolError("Unsupported unhashable result value; no permissive conversion") from exc


def make_bundle(rows: list[dict[str, Any]], lineage: dict[str, Any],
                reference: dict[str, Any], reference_files: dict[str, bytes]) -> dict[str, bytes]:
    validate_rows(rows)
    canonical = json.dumps(sorted(rows, key=lambda r: r["question_id"]), ensure_ascii=False,
                           sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if sha256(canonical) != QUESTION_OBJECTS_SHA256:
        raise BirdProtocolError("Cannot freeze changed question/evidence/Gold objects as the original protocol")
    splits = select_splits(rows)
    artifacts: dict[str, bytes] = {}
    for name, selected in splits.items():
        manifest = {
            "protocol_id": PROTOCOL_ID, "split": name, "case_ids": [case_id(r) for r in selected],
            "database_ids": sorted({r["db_id"] for r in selected}),
            "case_count": len(selected), "difficulty_counts": dict(Counter(r["difficulty"] for r in selected)),
            "selection_metadata": [{"case_id": case_id(r), "question_id": r["question_id"],
                                     "database_id": r["db_id"], "difficulty": r["difficulty"]} for r in selected],
        }
        artifacts[name + ".json"] = json_bytes(manifest)
        artifacts[f"inputs/{name}.jsonl"] = jsonl_bytes([agent_input(r) for r in selected])
    selected = splits["development80"] + splits["holdout30"]
    artifacts["scorer/gold110.jsonl"] = jsonl_bytes([
        {"case_id": case_id(r), "database_id": r["db_id"], "dialect": "postgres",
         "gold_sql": r["SQL"], "gold_sql_sha256": sha256(r["SQL"].encode("utf-8"))} for r in selected])
    artifacts["source_lineage.json"] = json_bytes(lineage)
    artifacts.update(reference_files)
    protocol = {
        "protocol_id": PROTOCOL_ID, "protocol_version": 1,
        "scope": "Self-selected original Mini-Dev PostgreSQL subset; not an official leaderboard score",
        "stage_status": "protocol_frozen_runtime_integration_pending",
        "dataset": {"repository": "birdsql/bird_mini_dev", "revision": DATASET_REVISION,
                    "questions_sha256": QUESTIONS_SHA256, "archive_sha256": ARCHIVE_SHA256,
                    "postgres_dump_sha256": SQL_DUMP_SHA256, "language": "en", "translation": False,
                    "license_declared_by_dataset_card": "cc-by-sa-4.0"},
        "splits": {"development": "development80.json", "holdout": "holdout30.json", "smoke": "smoke8.json",
                   "unit": "database_id", "seed": SPLIT_SEED, "database_rank": "sha256(seed|database|db_id)",
                   "holdout_database_count": 3, "development_database_count": 8,
                   "per_database_quota": DIFFICULTIES, "question_rank": "sha256(seed|question|question_id)",
                   "smoke_is_subset_of_development": True, "unused_case_count": 390,
                   "rank_inputs_exclude_question_evidence_and_gold": True},
        "agent": {"input_keys": sorted(PUBLIC_KEYS), "official_evidence": "provided_verbatim",
                  "question": "original_English_verbatim", "schema": "authorized_live_metadata_and_official_descriptions_for_database_id",
                  "value_samples": {"max_distinct_values_per_column": 3, "order": "database_type_order_ascending_nulls_last",
                                    "max_text_characters": 64, "truncation_must_be_recorded": True},
                  "retrieval": {"source": "natural_question_and_allowed_evidence_only", "gold_retrieval_terms": False,
                                "schema_recall_threshold": 0.55, "bm25_top_k": 30, "dense_top_k": 30,
                                "rrf_top_k": 40, "max_schema_fields": 20, "time_field_supplement_enabled": False},
                  "short_video_metric_catalog": False, "cross_case_memory": False,
                  "clarification": "record_as_no_answer; no Gold-derived automatic answer or option selection",
                  "gold_access": "scorer_only; agent and indexer must not load scorer directory or full question bank"},
        "model": {"llm_model": "qwen3.7-plus", "temperature": 0, "enable_thinking": False,
                  "embedding_model": "text-embedding-v4", "embedding_dimensions": 1024,
                  "rerank_model": "qwen3-rerank", "selection_basis": "M1 v7 baseline model names",
                  "alias_mutability": "Record provider returned model identifier and run date; alias is not a fixed weight snapshot"},
        "budgets": {"workers": 1, "case_wall_timeout_seconds": 600, "model_request_timeout_seconds": 180,
                    "max_transport_retries_per_request": 1, "max_total_model_http_attempts_per_case": 16,
                    "max_chat_http_attempts_per_case": 10, "chat_max_output_tokens": 4096,
                    "max_prompt_utf8_bytes": 98304, "max_sql_tool_calls": 3,
                    "max_validation_attempts_per_sql_round": 3, "connect_timeout_seconds": 10,
                    "sql_statement_timeout_ms": 30000, "lock_timeout_ms": 5000,
                    "result_row_limit": RESULT_ROW_LIMIT, "result_payload_byte_limit": 67108864,
                    "result_limit_probe": "fetch limit+1; never score preview or partial rows",
                    "usage": "record provider usage when available; missing usage is unknown, never zero",
                    "shared_attempt_counters": "Include generation, preprocessing, embeddings, reranking and transport retries; shared index build reported separately",
                    "enforcement_status": "required_in_external_runner_before_live; existing internal runners are not claimed compliant"},
        "scoring": {"policy_id": "bird_native_tuple_set_ex_v1", "upstream_reference": reference,
                    "predicate": "set(predicted_native_row_tuples) == set(gold_native_row_tuples)",
                    "column_names": "ignored", "row_order": "ignored", "duplicate_row_multiplicity": "ignored",
                    "column_value_positions": "preserved", "numeric_tolerance": "none beyond native Python equality",
                    "comparison_before_json_serialization": True, "explicit_per_case_alias_rules": False,
                    "primary_metric": "end_to_end_ex_pass_count / frozen_split_case_count",
                    "primary_denominator": "all frozen cases, including failures, refusals, clarification and resource-limit failures",
                    "gold_preflight": "all selected 110 Gold SQLs must execute with complete supported results before formal live",
                    "bad_gold_policy": "stop readiness; preserve IDs and evidence; any correction creates a new protocol version",
                    "preview_scoring": False, "timeout_or_truncation": "correctness unknown, primary contribution zero; record distinct failure category",
                    "secondary_metrics": ["first_sql_execution_success", "final_sql_execution_success", "ex_given_complete_results",
                                          "per_database_and_difficulty", "row_multiset_diagnostic", "ordered_result_diagnostic",
                                          "clarification_rate", "failure_categories", "latency_p50_p95", "model_attempts_and_usage"],
                    "soft_f1_and_rves": "deferred; do not mix with primary EX",
                    "compatibility_limit": "Native EX predicate retained; subset, English+evidence Agent task, independent read-only transactions and bounded resources are project conditions, not the full official execution harness"},
        "holdout_control": {"first_live_after": "freeze successful development run code, prompts, dependencies, source versions and budgets",
                            "gold_preflight_visibility": "scorer verifies environment; no Gold hints or correctness feedback to Agent/tuning",
                            "tuning": "development80 only", "attempt_policy": "one formal run per frozen candidate; all attempts preserved",
                            "after_observing_holdout": "no longer untouched for tuning; subsequent tuned runs must disclose reuse and version changes",
                            "limitations": "Public benchmark may be in model training data; this is not a private unseen test"},
        "runtime_gate": {"required_before_live": ["generic external datasource adapter", "db_id to verified authorized table mapping",
                           "isolated PostgreSQL target and read-only role", "verified target data and catalog versions",
                           "source-scoped index/cache/snapshot identities", "agent/scorer input boundary",
                           "tuple-preserving complete-result scorer", "enforced shared budgets", "110-case Gold preflight"],
                         "required_execution_binding": ["protocol and split hashes", "code and prompt versions", "dependency versions",
                           "model and endpoint configuration excluding secrets", "retrieval configuration", "permissions",
                           "verified target identity/data/catalog versions", "scoring policy and reference hashes"],
                         "refuse": ["cross-source resume", "short_video_ops runtime fallback", "unknown db_id", "unverified target versions"]},
        "artifact_sha256": {name: sha256(data) for name, data in sorted(artifacts.items())},
    }
    artifacts["protocol.json"] = json_bytes(protocol)
    return artifacts
