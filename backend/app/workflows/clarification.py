"""Carry the business meaning of a selected clarification into the query."""

from __future__ import annotations

from typing import Any

from ..database import SCHEMA


def apply_clarification_choice(state: dict[str, Any], response: Any) -> dict[str, Any]:
    payload = state.get("clarification") or {}
    option_id = str(response.get("option_id") if isinstance(response, dict) else response)
    option = next((item for item in payload.get("options") or []
                   if str(item.get("id")) == option_id), None)
    if option is None:
        raise ValueError(f"Unknown clarification option: {option_id}")
    parameter = str(payload.get("parameter") or "other")
    selection = {
        "option_id": option_id, "label": str(option.get("label") or option_id),
        "description": str(option.get("description") or ""),
        "question": str(payload.get("question") or ""),
    }
    workspace = dict(state.get("workspace") or {})
    tables = list(workspace.get("confirmed_schema_tables") or [])
    if any(table["id"] == option_id for table in SCHEMA):
        tables = list(dict.fromkeys([*tables, option_id]))
    workspace["confirmed_schema_tables"] = tables
    workspace["confirmed_parameters"] = {
        **dict(workspace.get("confirmed_parameters") or {}), parameter: option_id,
    }
    choices = {**dict(workspace.get("confirmed_clarifications") or {}), parameter: selection}
    workspace["confirmed_clarifications"] = choices
    base_query = str(state.get("clarification_base_query") or state["standalone_query"])
    confirmation = "\n".join(
        f"- {name}：{item['label']}；{item['description']}" for name, item in choices.items()
    )
    query = (f"{base_query}\n\n用户已确认的查询口径：\n{confirmation}\n"
             "按以上确认口径继续查询，已确认的参数无需再次询问。")
    extraction = dict(state.get("extraction") or {})
    extraction["retrieval_terms"] = list(dict.fromkeys([
        *list(extraction.get("retrieval_terms") or []), selection["label"],
        *([selection["description"]] if selection["description"] else []),
    ]))
    log = [*list(state.get("execution_log") or []), {
        "stage": "clarification_resolved", "success": True,
        "parameter": parameter, **selection,
    }]
    return {
        "workspace": workspace, "clarification_base_query": base_query,
        "standalone_query": query, "extraction": extraction,
        "execution_log": log, "rewritten": True,
        "clarification": None, "direct_sql": "", "result": {},
    }
