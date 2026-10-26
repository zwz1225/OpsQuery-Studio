"""Apply reviewed, per-case M0 phase83 column aliases without changing scoring rules."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.config import BASE_DIR


ROOT = BASE_DIR / "evaluation"
SOURCE = ROOT / "cases" / "all_cases.jsonl"
BACKUP = ROOT / "results" / "m0_all_cases_before_phase83_aliases_20260929.jsonl"
AUDIT = ROOT / "results" / "m0_phase83_column_candidates.json"
OFF = ROOT / "results" / "m0_phase83_live_off_server.json"
ON = ROOT / "results" / "m0_phase83_live_on_server.json"
EXPECTED_SOURCE_SHA256 = "58eb71d92af6d078b9ebacf7e91ce15daf986a0ece1adc77d9e09414211d7708"

# These names were checked against the question, Gold projection, and both saved
# generated SQL projections. Every annotation is scoped to exactly one Case.
APPROVED_IDS = (
    "GROWTH_OPS-007", "GROWTH_OPS-050", "GROWTH_OPS-051", "GROWTH_OPS-075",
    "GROWTH_OPS-100", "GROWTH_OPS-102", "GROWTH_OPS-126", "GROWTH_OPS-148",
    "CHANNEL_OPS-006", "CHANNEL_OPS-025", "CHANNEL_OPS-026", "CHANNEL_OPS-050",
    "CHANNEL_OPS-080", "CHANNEL_OPS-100", "CHANNEL_OPS-102", "CHANNEL_OPS-126",
    "CHANNEL_OPS-136", "CONTENT_OPS-002", "CONTENT_OPS-025", "CONTENT_OPS-026",
    "CONTENT_OPS-050", "CONTENT_OPS-052", "CONTENT_OPS-077", "CONTENT_OPS-100",
    "CONTENT_OPS-101", "CONTENT_OPS-125", "CONTENT_OPS-150",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    original = SOURCE.read_bytes()
    if hashlib.sha256(original).hexdigest() != EXPECTED_SOURCE_SHA256:
        raise ValueError("Case source changed since review; do not apply aliases")
    if BACKUP.exists():
        raise FileExistsError(BACKUP)
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    if audit["sources"]["off_sha256"] != sha(OFF) or audit["sources"]["on_sha256"] != sha(ON):
        raise ValueError("Audit source reports changed")
    records = {record["case_id"]: record for record in audit["cases"]}
    if len(records) != 30 or len(APPROVED_IDS) != 27 or len(set(APPROVED_IDS)) != 27:
        raise ValueError("Reviewed cohort is incomplete")

    approved: dict[str, dict[str, list[str]]] = {}
    for case_id in APPROVED_IDS:
        record = records[case_id]
        aliases: dict[str, list[str]] = {}
        for run in record["runs"].values():
            if not run["result_correct"]:
                continue
            mappings = run["candidate_mappings"]
            if len(mappings) != 1:
                raise ValueError(f"Expected unique column mapping: {case_id}")
            for expected, observed_names in mappings[0]["column_aliases"].items():
                names = aliases.setdefault(expected, [])
                for observed in observed_names:
                    if observed not in names:
                        names.append(observed)
        if case_id == "CONTENT_OPS-025":
            # Both SQL projections compute SUM(play_count); the Top N tie issue
            # affects selected rows, not this column's meaning.
            if record["runs"]["off"]["actual_columns"] != ["content_title", "play_count"] or \
                    record["runs"]["on"]["actual_columns"] != ["content_title", "play_count"]:
                raise ValueError("CONTENT_OPS-025 projection changed")
            aliases = {"plays": ["play_count"]}
        if not aliases or "*" in str(aliases):
            raise ValueError(f"Missing or wildcard aliases: {case_id}")
        approved[case_id] = aliases

    changed: set[str] = set()
    output_lines = []
    for line in original.splitlines(keepends=True):
        raw = line.rstrip(b"\r\n")
        newline = line[len(raw):]
        case = json.loads(raw)
        case_id = case["case_id"]
        if case_id not in approved:
            output_lines.append(line)
            continue
        if "column_aliases" in case or "allowed_auxiliary_columns" in case:
            raise ValueError(f"Existing column annotation in {case_id}")
        aliases = approved[case_id]
        if any(expected not in case["expected_columns"] for expected in aliases):
            raise ValueError(f"Alias does not target a declared column: {case_id}")
        case["column_aliases"] = aliases
        output_lines.append(json.dumps(case, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + newline)
        changed.add(case_id)
    if changed != set(APPROVED_IDS):
        raise ValueError("Approved Case list did not match source")
    BACKUP.write_bytes(original)
    temp = SOURCE.with_suffix(SOURCE.suffix + ".tmp")
    temp.write_bytes(b"".join(output_lines))
    temp.replace(SOURCE)
    print(f"approved_cases={len(changed)}")
    print(f"backup={BACKUP}")
    print(f"source_sha256={sha(SOURCE)}")


if __name__ == "__main__":
    main()
