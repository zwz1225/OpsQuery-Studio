from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
import threading
from typing import Any

from .contracts import CatalogSnapshot, MetadataProvider, ReadOnlyExecutor, SourceIdentity


@dataclass(frozen=True)
class DataSourceRuntime:
    identity: SourceIdentity
    catalog: CatalogSnapshot
    executor: ReadOnlyExecutor
    metadata: MetadataProvider
    index_build_lock: Any = field(default_factory=threading.RLock, init=False, compare=False, repr=False)
    _closed: bool = field(default=False, init=False, compare=False)

    def __post_init__(self) -> None:
        if self.executor.source_identity != self.identity or self.catalog.version != self.identity.catalog_version:
            raise ValueError("Datasource executor/catalog identity mismatch")
        if self.metadata.load_catalog() != self.catalog:
            raise ValueError("Datasource metadata/catalog mismatch")

    def require_open(self) -> None:
        if self._closed:
            raise RuntimeError("Datasource runtime is closed")
        if self.executor.source_identity != self.identity:
            raise ValueError("Datasource executor identity changed")
        self.executor.require_open()

    def assert_shared(self, *participants: Any) -> None:
        self.require_open()
        if any(participant.runtime is not self for participant in participants):
            raise ValueError("Datasource runtime mismatch between application entries")

    def assert_executor(self, executor: Any) -> None:
        self.require_open()
        if executor is not self.executor:
            raise ValueError("Scoring executor must use the same datasource runtime")

    def index_signature(self) -> str:
        payload = {"store_version": "datasource_v1", "source": self.identity.public()}
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    def close(self) -> None:
        if not self._closed:
            self.executor.close()
            object.__setattr__(self, "_closed", True)

    def __enter__(self) -> DataSourceRuntime:
        self.require_open()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


def create_datasource_runtime(config: Any = None, *, database_root: Path | None = None,
                              executor: Any = None) -> DataSourceRuntime:
    """Assemble an explicitly selected, verified source without backend fallback."""
    from ..config import BASE_DIR, settings
    from ..querying.duckdb_engine import DuckDbEngine
    from .csv_metadata import CsvMetadataProvider, csv_data_version, load_csv_catalog

    config = config or settings
    backend = getattr(config, "data_backend", "duckdb")
    if backend == "postgresql":
        from .postgres_config import PostgresConfig
        from .postgres_connections import PostgresConnectionManager
        from .postgres_metadata import PostgresMetadataProvider
        from ..querying.postgres_engine import PostgresEngine
        if getattr(config, "data_source_id", "") != "short_video_ops_postgres":
            raise ValueError("DATA_SOURCE_ID must match PostgreSQL PG_SOURCE_ID")
        if executor is not None:
            raise ValueError("An external PostgreSQL executor must supply a verified DataSourceRuntime explicitly")
        connections = PostgresConnectionManager(PostgresConfig.from_settings(config))
        try:
            annotations = (database_root or BASE_DIR / "data/databases") / "short_video_ops/_schema.json"
            metadata = PostgresMetadataProvider.from_recorded_source(connections, annotations)
            connections.open()
            metadata.verify()
            return DataSourceRuntime(metadata.identity, metadata.load_catalog(), PostgresEngine(metadata), metadata)
        except BaseException:
            connections.close()
            raise
    if backend != "duckdb":
        raise ValueError(f"Unsupported DATA_BACKEND: {backend}")
    source_id = getattr(config, "data_source_id", "short_video_ops_duckdb")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", source_id):
        raise ValueError("DATA_SOURCE_ID must contain only letters, digits, _ or -")
    database = "short_video_ops"
    root = (database_root or (executor.database_root if executor is not None else
                              BASE_DIR / "data/databases")).resolve()
    catalog = load_csv_catalog(root, database)
    identity = SourceIdentity(database, source_id, backend, "duckdb", "DuckDB", "main",
                              catalog.version, csv_data_version(root, database))
    if executor is None:
        executor = DuckDbEngine(root, catalog=catalog, source_identity=identity)
    else:
        if not isinstance(executor, DuckDbEngine):
            raise ValueError("An external executor must supply a DataSourceRuntime explicitly")
        if getattr(executor, "source_identity", None) not in (None, identity):
            raise ValueError("Cannot rebind an executor to another datasource")
        executor.bind_source(catalog, identity)
    return DataSourceRuntime(identity, catalog, executor, CsvMetadataProvider(executor, catalog))
