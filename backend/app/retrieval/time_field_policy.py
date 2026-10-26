"""Permission-aware, deterministic time-field candidates for a query."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..config import BASE_DIR
from ..database import SCHEMA
from ..security import AccessScope


DEFAULT_CATALOG = BASE_DIR / "data" / "metrics" / "metric_catalog.json"
_TIME_WORDS = (
    "月份", "每月", "按月", "月度", "每个月", "每天", "每日", "按天", "按日",
    "日期", "时间趋势", "按时间", "本月", "上月", "今天", "昨天",
)
_DATE_PATTERN = re.compile(r"(?<!\d)20\d{2}(?:年|[-/]\d{1,2})")


def has_explicit_time_request(question: str) -> bool:
    return bool(_DATE_PATTERN.search(question)) or any(word in question for word in _TIME_WORDS)


class TimeFieldPolicy:
    def __init__(self, catalog_path: Path = DEFAULT_CATALOG, max_extra_fields: int = 2,
                 *, tables: list[dict[str, Any]] | None = None) -> None:
        if max_extra_fields < 0:
            raise ValueError("max_extra_fields must be non-negative")
        tables = SCHEMA if tables is None else tables
        self.catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.database = str(self.catalog["database"])
        self.max_extra_fields = max_extra_fields
        self.fields_by_id = {
            f"{table['id']}.{field['name']}": field
            for table in tables
            for field in table.get("fields", [])
        }
        self.single_time_field: dict[str, str] = {}
        for table in tables:
            time_fields = [
                str(field["name"]) for field in table.get("fields", [])
                if field.get("role") == "time"
            ]
            if len(time_fields) == 1:
                self.single_time_field[str(table["id"])] = time_fields[0]

    def propose(
        self,
        question: str,
        selected_doc_ids: list[str],
        access_scope: AccessScope | dict[str, Any] | None,
        *,
        include_schema_fallback: bool = True,
    ) -> dict[str, Any]:
        if not has_explicit_time_request(question):
            return {"time_cue": False, "matched_metrics": [], "proposals": []}
        scope = (
            access_scope if isinstance(access_scope, AccessScope)
            else AccessScope.from_dict(access_scope)
        )
        selected_tables = {str(doc_id).rsplit(".", 1)[0] for doc_id in selected_doc_ids}
        matched = [
            metric for metric in self.catalog.get("metrics", [])
            if any(str(alias) in question for alias in metric.get("aliases", []))
        ]
        if "activation_rate" in {str(metric["name"]) for metric in matched}:
            matched = [metric for metric in matched if metric["name"] != "activated_users"]
        matched_names = {str(metric["name"]) for metric in matched}
        proposals: list[dict[str, str]] = []
        seen = set(selected_doc_ids)

        def add(table: str, field: str, reason: str) -> None:
            table_id = f"{self.database}.{table}"
            doc_id = f"{table_id}.{field}"
            if (
                doc_id in seen
                or table_id not in selected_tables
                or doc_id not in self.fields_by_id
                or not scope.allows_table(self.database, table_id)
            ):
                return
            proposals.append({"doc_id": doc_id, "reason": reason})
            seen.add(doc_id)

        for metric in matched:
            time_field = metric.get("time_field") or {}
            table, field = str(time_field.get("table") or ""), str(time_field.get("field") or "")
            if table and field:
                add(table, field, f"metric:{metric['name']}")

        for rule in self.catalog.get("comparison_constraints", []):
            if (
                str(rule.get("required_metric") or "") in matched_names
                and any(str(term) in question for term in rule.get("trigger_terms", []))
                and _DATE_PATTERN.search(question)
            ):
                add(str(rule["target_table"]), str(rule["target_field"]), f"comparison:{rule['name']}")

        if include_schema_fallback:
            for doc_id in selected_doc_ids:
                field = self.fields_by_id.get(doc_id)
                if not field or field.get("role") != "metric":
                    continue
                names = [str(field.get("label") or ""), str(field.get("name") or "")]
                names.extend(str(alias) for alias in field.get("aliases") or [])
                if not any(len(name) >= 2 and name in question for name in names):
                    continue
                table_id = str(doc_id).rsplit(".", 1)[0]
                time_field = self.single_time_field.get(table_id)
                if time_field:
                    add(
                        table_id.removeprefix(self.database + "."),
                        time_field,
                        f"schema_metric:{doc_id}",
                    )

        return {
            "time_cue": True,
            "matched_metrics": [str(metric["name"]) for metric in matched],
            "proposals": proposals,
        }
