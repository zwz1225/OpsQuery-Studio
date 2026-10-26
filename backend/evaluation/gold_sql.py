"""Select explicit dialect variants; never transpile or change scoring rules."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from app.datasources.contracts import SourceIdentity
from app.datasources.dialects import validated_source

GOLD_SQL_SELECTION_VERSION = 1


class GoldSqlSelectionError(ValueError):
    pass


@dataclass(frozen=True)
class GoldSqlSelection:
    sql: str
    dialect: str
    selection_key: str

    def public(self) -> dict[str, Any]:
        return {**asdict(self), "selection_version": GOLD_SQL_SELECTION_VERSION}


def select_gold_sql(case: Mapping[str, Any], source: SourceIdentity | Mapping[str, str] | None = None) -> GoldSqlSelection:
    dialect = validated_source(source)["dialect"] if source is not None else "duckdb"
    if dialect == "postgres":
        variants = case.get("gold_sql_by_dialect")
        sql = variants.get("postgres") if isinstance(variants, dict) else None
        if not isinstance(sql, str) or not sql.strip():
            raise GoldSqlSelectionError("PostgreSQL Gold requires non-empty gold_sql_by_dialect.postgres")
        return GoldSqlSelection(sql, dialect, "gold_sql_by_dialect.postgres")
    sql = case.get("gold_sql")
    if sql is None:
        sql = ""
    if not isinstance(sql, str):
        raise GoldSqlSelectionError("DuckDB gold_sql must be a string")
    return GoldSqlSelection(sql if sql.strip() else "", dialect, "gold_sql" if sql.strip() else "expected_rows")


def gold_selection_identity(cases: list[dict[str, Any]], source=None) -> dict[str, Any]:
    """Scored cases require Gold; route/permission behavior cases need none."""
    selected = []
    for case in cases:
        scored = any(key in case for key in ("gold_sql", "gold_sql_by_dialect", "expected_columns", "expected_rows"))
        selected.append({"case_id": case["case_id"],
                         "gold": select_gold_sql(case, source).public() if scored else None})
    return {"selection_version": GOLD_SQL_SELECTION_VERSION, "cases": selected}
