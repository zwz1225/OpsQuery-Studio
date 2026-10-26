"""Canonical backend names and safe public source identities; no connections."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping

from .contracts import SourceIdentity


@dataclass(frozen=True)
class SqlDialect:
    backend: str
    parser: str
    prompt: str


DIALECTS = {
    "duckdb": SqlDialect("duckdb", "duckdb", "DuckDB"),
    "postgresql": SqlDialect("postgresql", "postgres", "PostgreSQL"),
}
SOURCE_FIELDS = frozenset(SourceIdentity.__dataclass_fields__)


def dialect_for_backend(backend: str) -> SqlDialect:
    try:
        return DIALECTS[backend]
    except (KeyError, TypeError):
        raise ValueError("Unsupported datasource backend") from None


def validated_source(source: SourceIdentity | Mapping[str, str]) -> dict[str, str]:
    """Reject contradictory aliases, unsafe path components and public secrets."""
    value = source.public() if isinstance(source, SourceIdentity) else dict(source)
    if set(value) != SOURCE_FIELDS or not all(isinstance(v, str) and v for v in value.values()):
        raise ValueError("Invalid public datasource identity fields")
    dialect = dialect_for_backend(value["backend"])
    if (value["dialect"], value["prompt_dialect"]) != (dialect.parser, dialect.prompt):
        raise ValueError("Datasource backend and dialect differ")
    for name in ("source_id", "logical_database_id", "physical_schema"):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value[name]):
            raise ValueError("Invalid datasource identifier: " + name)
    for name in ("catalog_version", "data_version"):
        if not re.fullmatch(r"[0-9a-f]{64}", value[name]):
            raise ValueError("Invalid datasource version: " + name)
    return value
