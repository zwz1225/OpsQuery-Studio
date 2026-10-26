"""Offline proposal for explainable endpoint-scope validation feedback.

This is not wired into the running SQL validator. It reads only public input,
authorized catalog fields and a proposed SQL statement. It never reads Gold,
database rows or native-match outcomes.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping

from sqlglot import exp, parse
from sqlglot.errors import ParseError

from evaluation.bird_protocol import validate_agent_input

from .endpoint_scope import public_contract


POLICY = "m3_public_endpoint_validation_feedback_probe_v1"
_BILATERAL = re.compile(
    r"\b(?:both\s+(?:ends?|endpoints?|atoms?|sides?)|"
    r"either\s+(?:end|endpoint|atom|side)|"
    r"any\s+(?:end|endpoint|side)|"
    r"two\s+(?:ends?|endpoints?|atoms?|sides?)|"
    r"regardless\s+of\s+(?:the\s+)?(?:end|endpoint|side))\b",
    re.I,
)


def _fields(table: Mapping) -> set[str]:
    rows = table.get("fields", table.get("columns", []))
    return {row["name"].casefold() for row in rows
            if isinstance(row, Mapping) and isinstance(row.get("name"), str)}


def _decision(status: str, reason: str, **details) -> dict:
    return {"policy": POLICY, "status": status, "enforcement": "offline_proposal_only",
            "reason_code": reason, **details}


def _like_field(node: exp.Expression, pattern: str, operator: str,
                qualifier: set[str]) -> str | None:
    expected_type = exp.Like if operator == "LIKE" else exp.ILike
    if not isinstance(node, expected_type):
        return None
    column, literal = node.this, node.expression
    if (not isinstance(column, exp.Column) or not isinstance(literal, exp.Literal)
            or not literal.is_string or literal.this != pattern
            or column.table.casefold() not in qualifier):
        return None
    return column.name.casefold()


def inspect(public: dict, authorized_tables: Iterable[Mapping], sql: str) -> dict:
    """Identify one narrow repair candidate; never reject or execute SQL."""
    validate_agent_input(public)
    if not isinstance(sql, str) or not sql.strip():
        return _decision("abstain", "missing_sql")
    tables = list(authorized_tables)
    contract = public_contract(public, tables)
    if contract.get("basis") != "public_evidence_explicit_like_endpoint_and_metric":
        return _decision("abstain", "no_unique_public_endpoint")
    if _BILATERAL.search(public["question"]):
        return _decision("abstain", "question_explicitly_mentions_multiple_endpoints")
    try:
        statements = [statement for statement in parse(sql, read="postgres")
                      if statement is not None]
    except (ParseError, ValueError, TypeError):
        return _decision("abstain", "sql_not_parseable")
    if len(statements) != 1:
        return _decision("abstain", "not_one_statement")
    tree = statements[0]
    if not isinstance(tree, exp.Select) or len(list(tree.find_all(exp.Select))) != 1:
        return _decision("abstain", "not_one_simple_select")
    if (any(tree.args.get(key) for key in
            ("with_", "joins", "group", "having", "qualify", "order", "limit", "offset", "distinct"))
            or len(tree.expressions) != 1):
        return _decision("abstain", "additional_query_structure")
    sources = list(tree.find_all(exp.Table))
    table_name = contract["table_id"].split(".")[-1]
    if (len(sources) != 1 or sources[0].name.casefold() != table_name.casefold()
            or sources[0].catalog or sources[0].db.casefold() not in ("", "public")):
        return _decision("abstain", "table_scope_not_unique")
    source = sources[0]
    projection = tree.expressions[0]
    if isinstance(projection, exp.Alias):
        projection = projection.this
    metric = contract["metric_field_id"].split(".")[-1].casefold()
    qualifier = {"", source.name.casefold(), source.alias_or_name.casefold()}
    if (not isinstance(projection, exp.Count) or projection.args.get("distinct")
            or not isinstance(projection.this, (exp.Star, exp.Column))):
        return _decision("abstain", "not_simple_connection_count")
    if isinstance(projection.this, exp.Column) and (
            projection.this.name.casefold() != metric
            or projection.this.table.casefold() not in qualifier):
        return _decision("abstain", "metric_field_differs")
    where = tree.args.get("where")
    if where is None:
        return _decision("abstain", "missing_filter")
    predicate = where.this
    while isinstance(predicate, exp.Paren):
        predicate = predicate.this
    explicit = contract["predicate_field_id"].split(".")[-1].casefold()
    pattern, operator = contract["pattern"], contract["operator"]
    if _like_field(predicate, pattern, operator, qualifier) == explicit:
        return _decision("pass", "named_endpoint_preserved")
    if not isinstance(predicate, exp.Or):
        return _decision("abstain", "filter_shape_not_exact_or")
    branches = []
    for branch in (predicate.this, predicate.expression):
        while isinstance(branch, exp.Paren):
            branch = branch.this
        branches.append(_like_field(branch, pattern, operator, qualifier))
    if explicit not in branches or None in branches or branches[0] == branches[1]:
        return _decision("abstain", "or_branches_not_named_endpoint_pair")
    other = next(field for field in branches if field != explicit)
    owners = [table for table in tables
              if table.get("id", public["database_id"] + "." + str(table.get("name"))) == contract["table_id"]]
    if len(owners) != 1 or other not in _fields(owners[0]):
        return _decision("abstain", "alternate_field_not_authorized")
    return _decision(
        "candidate_repair", "explicit_endpoint_widened_by_or",
        feedback={
            "code": "explicit_endpoint_widened_by_or",
            "origin": "public_question_evidence_and_authorized_catalog",
            "table_id": contract["table_id"],
            "named_filter_field_id": contract["predicate_field_id"],
            "additional_filter_field_id": contract["table_id"] + "." + other,
            "metric_field_id": contract["metric_field_id"],
            "operator": operator,
            "pattern": pattern,
            "reason": "Public evidence binds the filter to the named endpoint, while the SQL broadens the same pattern to another authorized field with OR.",
            "repair_guidance": "Keep the named endpoint predicate and requested count; remove the additional endpoint branch. Preserve all other public conditions.",
            "sql_sha256": hashlib.sha256(sql.encode("utf-8")).hexdigest(),
        },
    )
