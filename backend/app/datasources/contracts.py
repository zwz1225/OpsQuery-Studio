from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from ..querying.models import SqlExecution
    from ..security import AccessScope


@dataclass(frozen=True)
class SourceIdentity:
    logical_database_id: str
    source_id: str
    backend: str
    dialect: str
    prompt_dialect: str
    physical_schema: str
    catalog_version: str
    data_version: str

    def public(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class CatalogSnapshot:
    """Canonical JSON is immutable; consumers receive independent dictionaries."""

    content: str

    @property
    def tables(self) -> list[dict[str, Any]]:
        return json.loads(self.content)["tables"]

    @property
    def relations(self) -> list[dict[str, Any]]:
        return json.loads(self.content)["relations"]

    @property
    def version(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()


class ReadOnlyExecutor(Protocol):
    source_identity: SourceIdentity

    def execute(self, database: str, sql: str, access_scope: AccessScope | None = None,
                *, row_limit: int = 200) -> SqlExecution: ...

    def require_open(self) -> None: ...

    def close(self) -> None: ...


class MetadataProvider(Protocol):
    def load_catalog(self) -> CatalogSnapshot: ...

    def profile_table(self, table_id: str, field_names: list[str]) -> dict[str, dict[str, Any]]: ...
