"""Offline M3 endpoint-scope candidate based on public evidence and source fields.

This module is not connected to the running Agent. It uses no scorer data,
case IDs, database values, or generated result values to select a rule.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError

from evaluation.bird_protocol import validate_agent_input


POLICY = "m3_public_explicit_endpoint_scope_candidate_v1"
_SUBJECT = r"[A-Za-z][A-Za-z0-9 _-]{0,79}"
_FIELD = r"[A-Za-z_][A-Za-z0-9_]*"
_PATTERN_CLAUSE = re.compile(
    rf"(?P<subject>{_SUBJECT})\s+refers\s+to\s+"
    rf"(?P<field>{_FIELD})\s+(?P<operator>LIKE|ILIKE)\s+"
    r"'(?P<pattern>[^'\r\n]{1,64})'",
    re.I,
)
_METRIC_CLAUSE = re.compile(
    rf"(?P<subject>{_SUBJECT})\s+refers\s+to\s+(?P<field>{_FIELD})",
    re.I,
)


def _fields(table: Mapping) -> set[str]:
    rows = table.get("fields", table.get("columns", []))
    return {row["name"].casefold() for row in rows if isinstance(row, Mapping)
            and isinstance(row.get("name"), str)}


def _mentioned(subject: str, question: str) -> bool:
    return bool(re.search(r"(?<!\w)" + r"\s+".join(map(re.escape, subject.split()))
                          + r"(?!\w)", question, re.I))


def public_contract(public: dict, authorized_tables: Iterable[Mapping]) -> dict:
    """Bind one explicitly named LIKE endpoint to one authorized table.

    Ambiguous evidence or table ownership stays advisory and supplies no field
    recommendation. The candidate never imposes a predicate on its own.
    """
    validate_agent_input(public)
    result = {"policy": POLICY, "enforcement": "none", "basis": "no_unique_public_endpoint"}
    clauses = [part.strip() for part in public["evidence"].split(";") if part.strip()]
    if len(clauses) != 2:
        return result
    predicates = [m for clause in clauses if (m := _PATTERN_CLAUSE.fullmatch(clause))]
    metrics = [m for clause in clauses if (m := _METRIC_CLAUSE.fullmatch(clause))]
    if len(predicates) != 1 or len(metrics) != 1:
        return result
    predicate, metric = predicates[0], metrics[0]
    pattern = predicate["pattern"]
    if (not re.fullmatch(r"[A-Za-z0-9_%.-]{1,64}", pattern)
            or len(re.sub(r"[%_]", "", pattern)) < 2
            or predicate["field"].casefold() == metric["field"].casefold()
            or not _mentioned(predicate["subject"], public["question"])
            or not _mentioned(metric["subject"], public["question"])):
        return result
    owners = []
    for table in authorized_tables:
        if table.get("database_id", table.get("database", public["database_id"])) != public["database_id"]:
            continue
        name = table.get("name")
        if not isinstance(name, str):
            continue
        fields = _fields(table)
        if {predicate["field"].casefold(), metric["field"].casefold()} <= fields:
            owners.append(table)
    if len(owners) != 1:
        return {"policy": POLICY, "enforcement": "advisory_only",
                "basis": "ambiguous_or_missing_authorized_owner"}
    table = owners[0]
    table_id = table.get("id", public["database_id"] + "." + table["name"])
    return {
        "policy": POLICY,
        "enforcement": "advisory_only",
        "basis": "public_evidence_explicit_like_endpoint_and_metric",
        "table_id": table_id,
        "predicate_field_id": table_id + "." + predicate["field"],
        "metric_field_id": table_id + "." + metric["field"],
        "operator": predicate["operator"].upper(),
        "pattern": pattern,
        "guidance": "The public evidence names the filter endpoint. Preserve that field's role; "
                    "include another endpoint only when the question or evidence requests it.",
    }


def observe_sql(contract: dict, sql: str) -> list[dict]:
    """Report visible endpoint widening in a simple SELECT; never reject SQL."""
    if contract.get("basis") != "public_evidence_explicit_like_endpoint_and_metric":
        return []
    try:
        tree = parse_one(sql, read="postgres")
    except (ParseError, ValueError, TypeError):
        return []
    if not isinstance(tree, exp.Select) or not tree.args.get("where"):
        return []
    tables = list(tree.find_all(exp.Table))
    if len(tables) != 1 or tables[0].name.casefold() != contract["table_id"].split(".")[-1].casefold():
        return []
    alias = tables[0].alias_or_name.casefold()
    explicit_field = contract["predicate_field_id"].split(".")[-1].casefold()
    matches = []
    for node in tree.args["where"].find_all(exp.Like, exp.ILike):
        field, literal = node.this, node.expression
        if (isinstance(field, exp.Column) and isinstance(literal, exp.Literal)
                and literal.is_string and literal.this == contract["pattern"]
                and (not field.table or field.table.casefold() == alias)):
            matches.append((field.name.casefold(), node))
    if any(field == explicit_field for field, _ in matches):
        other = sorted({field for field, node in matches
                        if field != explicit_field and node.find_ancestor(exp.Or)})
        if other:
            return [{"code": "explicit_endpoint_widened_by_or", "severity": "advisory",
                     "field_id": contract["predicate_field_id"], "other_fields": other,
                     "reason": contract["guidance"]}]
    return []
