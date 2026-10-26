"""Annotate the verified cutoff members for CONTENT_OPS-025 once."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.config import BASE_DIR


SOURCE = BASE_DIR / "evaluation" / "cases" / "all_cases.jsonl"
BACKUP = BASE_DIR / "evaluation" / "results" / "m0_all_cases_before_topn_tie_20260929.jsonl"
EXPECTED_SHA256 = "36e65b72415c78199d6069559700a3abcc177dba860c92e49f9cafc6dfc31f5d"
TIED_TITLES = [
    "体育内容002575", "体育内容002711", "体育内容003797",
    "体育内容006542", "体育内容006759", "体育内容008320",
    "体育内容011482", "体育内容011509", "体育内容012056",
    "体育内容012155", "体育内容013558", "体育内容013837",
]


def main() -> None:
    original = SOURCE.read_bytes()
    if hashlib.sha256(original).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Case source changed since the tie audit")
    if BACKUP.exists():
        raise FileExistsError(BACKUP)
    lines = original.decode("utf-8").splitlines()
    cases = [json.loads(line) for line in lines]
    matches = [index for index, case in enumerate(cases)
               if case["case_id"] == "CONTENT_OPS-025"]
    if len(matches) != 1:
        raise ValueError("Expected one CONTENT_OPS-025 case")
    index = matches[0]
    case = cases[index]
    if (case.get("top_n_tie_policy") or case["order_by_column"] != "plays"
            or case["column_aliases"] != {"plays": ["play_count"]}
            or len(case["expected_rows"]) != 10):
        raise ValueError("CONTENT_OPS-025 contract differs from review")
    candidates = [{"content_title": title, "plays": 8} for title in TIED_TITLES]
    if not all(row in candidates for row in case["expected_rows"][7:]):
        raise ValueError("Gold cutoff rows are absent from reviewed candidates")
    case["top_n_tie_policy"] = {
        "limit": 10,
        "boundary_value": 8,
        "boundary_candidates": candidates,
    }
    lines[index] = json.dumps(case, ensure_ascii=False, separators=(",", ":"))
    updated = ("\n".join(lines) + "\n").encode("utf-8")
    BACKUP.write_bytes(original)
    SOURCE.write_bytes(updated)
    print({"backup": str(BACKUP), "source_sha256": hashlib.sha256(updated).hexdigest(),
           "boundary_candidates": len(candidates)})


if __name__ == "__main__":
    main()
