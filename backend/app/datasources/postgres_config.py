"""PostgreSQL preparation settings and recorded evidence; opens no connections."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
APPROVED_IMPORT_SPEC = "8f936c3089614a38b17194b76e0c073c20cfe5b194ecb8f9f1e27b8f4d2ca7fd"


class PostgresConfigError(ValueError):
    """Messages name settings/checks, never passwords, hosts or raw file data."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PostgresConfigError(message)


def integer(value: Any, name: str, minimum: int, maximum: int) -> int:
    require(not isinstance(value, bool) and re.fullmatch(r"[0-9]{1,10}", str(value).strip()) is not None,
            name + " must be an integer")
    parsed = int(str(value).strip())
    require(minimum <= parsed <= maximum, name + f" must be {minimum}..{maximum}")
    return parsed


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PostgresConfig:
    host: str = field(repr=False)
    port: int
    database: str
    schema: str
    user: str
    password: str = field(repr=False)
    source_id: str
    connect_timeout_seconds: int
    statement_timeout_ms: int
    lock_timeout_ms: int
    pool_min_size: int
    pool_max_size: int
    pool_wait_timeout_seconds: int
    pool_max_waiting: int
    verified_data_version: str
    import_report_path: Path = field(repr=False)
    validation_report_path: Path = field(repr=False)

    @classmethod
    def from_settings(cls, settings: Any, *, require_password: bool = True, base_dir: Path = BASE_DIR) -> PostgresConfig:
        host = str(settings.pg_host).strip()
        require(bool(host) and len(host) <= 253 and re.fullmatch(r"[A-Za-z0-9_.:-]+", host) is not None,
                "PG_HOST must be a single TCP host/IP")
        password = settings.pg_password
        require(isinstance(password, str) and "\0" not in password, "PG_PASSWORD has an invalid value")
        require(not require_password or bool(password), "PG_PASSWORD is required")
        fixed = {"pg_database": "askdata_m1_test", "pg_schema": "askdata_ops",
                 "pg_user": "askdata_readonly", "pg_source_id": "short_video_ops_postgres"}
        for key, expected in fixed.items():
            require(str(getattr(settings, key)).strip() == expected, key.upper() + " differs from accepted M1 B source")
        version = str(settings.pg_verified_data_version).strip()
        require(re.fullmatch(r"[0-9a-f]{64}", version) is not None, "PG_VERIFIED_DATA_VERSION must be a lowercase SHA256")
        def path(name: str) -> Path:
            value = str(getattr(settings, name)).strip()
            require(bool(value) and "\0" not in value, name.upper() + " is required")
            candidate = Path(value)
            return (candidate if candidate.is_absolute() else base_dir/candidate).resolve()
        result = cls(host=host, port=integer(settings.pg_port, "PG_PORT", 1, 65535),
            database=fixed["pg_database"], schema=fixed["pg_schema"], user=fixed["pg_user"], password=password,
            source_id=fixed["pg_source_id"],
            connect_timeout_seconds=integer(settings.pg_connect_timeout_seconds, "PG_CONNECT_TIMEOUT_SECONDS", 2, 120),
            statement_timeout_ms=integer(settings.pg_statement_timeout_ms, "PG_STATEMENT_TIMEOUT_MS", 1000, 1800000),
            lock_timeout_ms=integer(settings.pg_lock_timeout_ms, "PG_LOCK_TIMEOUT_MS", 100, 60000),
            pool_min_size=integer(settings.pg_pool_min_size, "PG_POOL_MIN_SIZE", 1, 32),
            pool_max_size=integer(settings.pg_pool_max_size, "PG_POOL_MAX_SIZE", 1, 32),
            pool_wait_timeout_seconds=integer(settings.pg_pool_wait_timeout_seconds, "PG_POOL_WAIT_TIMEOUT_SECONDS", 1, 120),
            pool_max_waiting=integer(settings.pg_pool_max_waiting, "PG_POOL_MAX_WAITING", 1, 256),
            verified_data_version=version, import_report_path=path("pg_import_report_path"),
            validation_report_path=path("pg_validation_report_path"))
        require(result.pool_min_size <= result.pool_max_size, "PG_POOL_MIN_SIZE must not exceed PG_POOL_MAX_SIZE")
        require(result.lock_timeout_ms <= result.statement_timeout_ms, "PG_LOCK_TIMEOUT_MS must not exceed PG_STATEMENT_TIMEOUT_MS")
        require(result.import_report_path != result.validation_report_path, "PG report paths must refer to different files")
        return result

    def public(self) -> dict[str, Any]:
        return {"source_id": self.source_id, "logical_database_id": "short_video_ops", "backend": "postgresql",
            "dialect": "postgres", "prompt_dialect": "PostgreSQL", "physical_database": self.database,
            "physical_schema": self.schema, "query_role": self.user, "password_configured": bool(self.password),
            "recorded_data_version": self.verified_data_version,
            "limits": {key: getattr(self, key) for key in ["connect_timeout_seconds", "statement_timeout_ms", "lock_timeout_ms",
                "pool_min_size", "pool_max_size", "pool_wait_timeout_seconds", "pool_max_waiting"]}}


@dataclass(frozen=True)
class RecordedPostgresSource:
    config: PostgresConfig = field(repr=False)
    physical_schema_version: str
    import_report_sha256: str
    validation_report_sha256: str

    def public(self) -> dict[str, Any]:
        return {**self.config.public(), "recorded_physical_schema_version": self.physical_schema_version,
            "evidence_sha256": {"import": self.import_report_sha256, "validation": self.validation_report_sha256},
            "recorded_evidence_verified": True, "live_target_verified": False,
            "catalog_version": None, "runtime_available": False,
            "scope": "Recorded M1 B snapshot only. Live metadata/data verification precedes runtime assembly."}


def read_record(path: Path, name: str) -> tuple[dict, str]:
    def pairs(items):
        output = {}
        for key, value in items:
            require(key not in output, name + " contains duplicate JSON keys")
            output[key] = value
        return output
    def constant(value):
        raise PostgresConfigError(name + " contains a non-finite JSON number")
    try:
        raw = path.read_bytes()
        record = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (OSError, ValueError) as exc:
        raise PostgresConfigError(name + " cannot be read as valid JSON") from None
    require(isinstance(record, dict), name + " must be a JSON object")
    return record, hashlib.sha256(raw).hexdigest()


def load_recorded_source(config: PostgresConfig) -> RecordedPostgresSource:
    imported, import_hash = read_record(config.import_report_path, "PG_IMPORT_REPORT_PATH")
    validated, validation_hash = read_record(config.validation_report_path, "PG_VALIDATION_REPORT_PATH")
    expected_target = {"source_id": config.source_id, "logical_database_id": "short_video_ops", "backend": "postgresql",
        "dialect": "postgres", "physical_database": config.database, "physical_schema": config.schema,
        "import_role": "askdata_import", "query_role": config.user}
    summary = {"table_count": 41, "field_count": 276, "row_count": 722732, "relation_count": 53,
               "error_count": 0, "full_typed_row_match_count": 41}
    schema_versions = []
    try:
        for mode, report in [("import", imported), ("validation", validated)]:
            require(report["mode"] == mode and report["run_status"] == "complete" and report["phase"] == "completed",
                    "M1 B report is incomplete")
            require(report["target"] == expected_target and report["postgresql_connected"] and report["target_data_verified"],
                    "M1 B source identity differs")
            require(not report["errors"] and report["source_files_unchanged"] and report["new_model_request_count"] == 0,
                    "M1 B report contains failed checks")
            require(report["source_preparation"]["canonical_import_spec_sha256"] == APPROVED_IMPORT_SPEC,
                    "M1 B import specification differs")
            require(report["verified_target_data_version"] == config.verified_data_version, "PG_VERIFIED_DATA_VERSION differs from M1 B evidence")
            validation = report["validation"]
            require(validation["status"] == "passed" and not validation["errors"] and validation["summary"] == summary,
                    "M1 B data validation is incomplete")
            tables = validation["tables"]
            require(len(tables) == 41 and len({t["name"] for t in tables}) == 41 and
                    sum(len(t["columns"]) for t in tables) == 276 and sum(t["row_count"] for t in tables) == 722732,
                    "M1 B physical schema/counts differ")
            for table in tables:
                require(table["full_row_count"] == table["row_count"] and table["primary_key_null_rows"] ==
                        table["primary_key_duplicate_groups"] == 0 and table["owner"] == "askdata_import" and table["readonly_select_granted"],
                        "M1 B table verification is incomplete")
            selected = [{key: table[key] for key in ["name", "columns", "primary_key", "row_count", "typed_row_multiset_sha256"]} for table in tables]
            require(digest({"target": expected_target, "tables": selected}) == config.verified_data_version ==
                    validation["verified_snapshot_data_version"], "Recomputed M1 B target data version differs")
            schema_versions.append(digest([{key: table[key] for key in ["name", "columns", "primary_key"]} for table in tables]))
            identity = report["connection_identity"]
            require(identity["physical_database"] == config.database and identity["execution_role"] ==
                    ("askdata_import" if mode == "import" else config.user) and identity["server_version"].split(".")[0] == "16" and
                    [identity[key] for key in ["encoding", "timezone", "collation", "ctype", "locale_provider"]] == ["UTF8", "UTC", "C", "C", "c"],
                    "M1 B environment/role differs")
        require(imported["source_preparation"] == validated["source_preparation"], "M1 B source preparation differs between reports")
        require(imported["commit_state"] == "committed" and validated["commit_state"] == "not_started", "M1 B commit states differ")
        require(validated["import_record"] == {"sha256": import_hash, "commit_state": "committed",
                "expected_target_data_version": config.verified_data_version, "recovery_of_unknown_commit": False},
                "M1 B import report reference/hash differs")
        acl = validated["readonly_acl"]
        require(acl["status"] == "passed" and acl["database_schema_grants"] == [True, False, False, True, False, False],
                "M1 B readonly database/schema ACL differs")
        grants = {key: key == "SELECT" for key in ["SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"]}
        require(acl["tables"] == [{"name": t["name"], "grants": grants} for t in validated["validation"]["tables"]],
                "M1 B readonly table ACL differs")
        require(validated["write_denial_probes"] == {"status": "passed", "read_write_transaction_used": True,
                "all_probe_changes_rolled_back": True, "connection_recovered": True,
                "checks": [{"operation": op, "sqlstate": "42501", "permission_denied": True}
                           for op in ["insert", "update", "delete", "create_table"]]}, "M1 B actual write denial evidence differs")
        require(schema_versions[0] == schema_versions[1], "M1 B physical schema versions differ")
    except (KeyError, TypeError, IndexError, AttributeError, ValueError) as exc:
        if isinstance(exc, PostgresConfigError): raise
        raise PostgresConfigError("M1 B report structure is invalid") from None
    return RecordedPostgresSource(config, schema_versions[1], import_hash, validation_hash)
