"""M3 E04 public scalar-count shape rule for an isolated development candidate.

This module reads only the public question and generated SQL. It does not use
case IDs, Gold SQL, scores, or database results to choose its behavior.
"""
from __future__ import annotations

import re

from sqlglot import exp, parse_one
from sqlglot.errors import ParseError

from evaluation.bird_protocol import validate_agent_input


POLICY = "m3_public_scalar_count_shape_candidate_v2"
_HOW_MANY = re.compile(r"\bhow\s+many\b", re.I)
_COUNT_NOUN = re.compile(r"\b(?:no\.|number|count)\s+of\b", re.I)
_COUNT_LEAD = re.compile(
    r"^\s*(?:list(?:\s+out)?|show|return|give|what\s+is)\s+"
    r"(?:the\s+)?(?:no\.|number|count)\s+of\b", re.I,
)
_GROUP_OUTPUT = re.compile(
    r"\b(?:for\s+each|for\s+every|per\s+\w+|group(?:ed)?\s+by|"
    r"break(?:down)?\s+by)\b", re.I,
)
_COUNT_MODIFIER = re.compile(
    r"\b(?:average|highest|biggest|largest|lowest|smallest|maximum|minimum)\s+"
    r"(?:no\.|number|count)\s+of\b", re.I,
)
_OTHER_OUTPUT = re.compile(
    r"\b(?:also\s+(?:list|show|give|return)|along\s+with|"
    r"(?:and|then)\s+(?:list|show|give|return)|with\s+their\s+(?:names?|details?)|"
    r"and\s+(?:their\s+)?(?:names?|details?|ids?|identifiers?)|"
    r"and\s+what\s+(?:are|is)\s+their\s+(?:names?|details?))\b",
    re.I,
)
_EVIDENCE_OUTPUT_GROUP = re.compile(
    r"\b(?:output|return|report|show|display|result)\b[^.;]{0,90}"
    r"\b(?:for\s+each|per\s+\w+|group(?:ed)?\s+by|break(?:down)?\s+by)\b",
    re.I,
)


def public_contract(public: dict) -> dict:
    """Conservatively identify a request for one count value.

    An advisory result means the wording needs human/model interpretation; it
    must never become a hard validation failure.
    """
    validate_agent_input(public)
    question = public["question"]
    markers = list(_HOW_MANY.finditer(question)) + list(_COUNT_NOUN.finditer(question))
    markers.sort(key=lambda match: match.start())
    if not markers:
        return {"policy": POLICY, "enforcement": "none", "basis": "no_count_request"}
    if len(markers) != 1:
        return {"policy": POLICY, "enforcement": "advisory", "basis": "multiple_count_phrases"}
    marker = markers[0]
    if _COUNT_MODIFIER.search(question) or re.search(r"\bhow\s+many\s+more\b", question, re.I):
        return {"policy": POLICY, "enforcement": "advisory", "basis": "rank_average_or_difference"}
    if _EVIDENCE_OUTPUT_GROUP.search(public["evidence"]):
        return {"policy": POLICY, "enforcement": "advisory", "basis": "evidence_requests_grouped_output"}
    if _GROUP_OUTPUT.search(question) or re.search(r"\bby\s+[\w-]+", question[marker.end():], re.I):
        return {"policy": POLICY, "enforcement": "advisory", "basis": "grouped_output_possible"}
    if _OTHER_OUTPUT.search(question) or question.count("?") > 1 or re.search(r"\?\s*\S", question):
        return {"policy": POLICY, "enforcement": "advisory", "basis": "multiple_outputs_possible"}
    if not (_HOW_MANY.fullmatch(marker.group()) or _COUNT_LEAD.search(question)):
        return {"policy": POLICY, "enforcement": "advisory", "basis": "count_phrase_is_modifier"}
    return {
        "policy": POLICY,
        "enforcement": "hard_for_simple_outer_select",
        "basis": "single_public_count_request",
        "guidance": "Return one overall count. A grouped eligibility subquery may be counted by the outer SELECT.",
    }


def shape_issues(contract: dict, sql: str) -> list[dict]:
    """Inspect the outer result shape; leave complex SQL to existing checks."""
    if contract.get("enforcement") != "hard_for_simple_outer_select":
        return []
    try:
        tree = parse_one(sql, read="postgres")
    except (ParseError, ValueError, TypeError):
        return []
    if not isinstance(tree, exp.Select):
        return []
    issues = []
    group = tree.args.get("group")
    if group and group.expressions:
        issues.append({
            "code": "scalar_count_outer_group",
            "reason": "The public question requests one overall count, but the outer SELECT groups rows and can return multiple counts. Count eligible groups in an outer SELECT instead.",
        })
    if len(tree.expressions) > 1:
        issues.append({
            "code": "scalar_count_multiple_outputs",
            "reason": "The public question requests one count value, but the outer SELECT projects multiple values.",
        })
    return issues
