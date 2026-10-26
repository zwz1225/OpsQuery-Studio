from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .contracts import CatalogSnapshot
from .values import json_value


def csv_data_version(database_root: Path, database: str) -> str:
    """Same relative-name/content algorithm as historical evaluation data_digest."""
    folder = database_root / database
    paths = sorted(p for p in folder.iterdir() if p.is_file() and
                   (p.suffix == ".csv" or p.name == "_schema.json"))
    entries = [{"path": f"data/databases/{database}/{p.name}",
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
    return hashlib.sha256(json.dumps(entries, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def load_csv_catalog(database_root: Path, database: str) -> CatalogSnapshot:
    folder = database_root / database
    payload = json.loads((folder / "_schema.json").read_text(encoding="utf-8"))
    tables = payload.get("tables") or []
    if not tables or any(table.get("database") != database for table in tables):
        raise ValueError("CSV catalog must belong to the selected logical database")
    names = [str(t.get("name") or t["id"]) for t in tables]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate physical table in CSV catalog")
    missing = [name for name in names if not (folder / f"{name}.csv").is_file()]
    if missing:
        raise ValueError(f"Catalog CSV tables missing: {', '.join(missing)}")
    return CatalogSnapshot(json.dumps({"tables": tables, "relations": payload.get("relations") or []},
                                     ensure_ascii=False, sort_keys=True))


class CsvMetadataProvider:
    """Driver operations stay here, outside retrieval and workflow code."""

    def __init__(self, executor: Any, catalog: CatalogSnapshot) -> None:
        self.executor = executor
        self.catalog = catalog

    def load_catalog(self) -> CatalogSnapshot:
        return self.catalog

    def profile_table(self, table_id: str, field_names: list[str]) -> dict[str, dict[str, Any]]:
        table = next((t for t in self.catalog.tables if t["id"] == table_id), None)
        if table is None:
            raise ValueError(f"Unknown catalog table: {table_id}")
        fields = {f["name"]: f for f in table["fields"]}
        if any(name not in fields for name in field_names):
            raise ValueError("Unknown profile field")
        # Identifiers come only from the validated catalog and are quoted.
        quote = lambda value: '"' + value.replace('"', '""') + '"'
        sql_table = quote(str(table.get("name") or table["id"]))
        output = {}
        with self.executor.connect(table["database"]) as connection:
            for name in field_names:
                column, field = quote(name), fields[name]
                samples = [json_value(row[0]) for row in connection.execute(
                    f"SELECT DISTINCT {column} FROM {sql_table} WHERE {column} IS NOT NULL "
                    f"ORDER BY {column} LIMIT 5").fetchmany(5)]
                if field["type"] in {"数值", "整数"}:
                    row = connection.execute(f"SELECT MIN({column}), MAX({column}), AVG({column}) FROM {sql_table}").fetchone()
                    average = round(row[2], 2) if row[2] is not None else "无"
                    text = f"最小值 {row[0]}，最大值 {row[1]}，平均值 {average}"
                elif field["type"] == "日期":
                    row = connection.execute(f"SELECT MIN({column}), MAX({column}) FROM {sql_table}").fetchone()
                    text = f"范围 {row[0]} 至 {row[1]}"
                else:
                    count = connection.execute(f"SELECT COUNT(DISTINCT {column}) FROM {sql_table}").fetchone()[0]
                    text = f"约 {count} 个不同值"
                output[name] = {"sample_values": samples, "profile_text": text}
        return output
