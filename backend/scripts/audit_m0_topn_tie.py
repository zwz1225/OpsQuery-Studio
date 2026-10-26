"""Print the full cutoff group for the reviewed CONTENT_OPS-025 Top N case."""

from __future__ import annotations

import json

from app.config import BASE_DIR
from app.querying.duckdb_engine import DuckDbEngine
from app.security import AccessController


def main() -> None:
    source = BASE_DIR / "evaluation" / "cases" / "all_cases.jsonl"
    case = next(row for line in source.read_text(encoding="utf-8").splitlines()
                if (row := json.loads(line))["case_id"] == "CONTENT_OPS-025")
    sql = case["gold_sql"]
    assert sql.endswith(" LIMIT 10")
    scope = AccessController().resolve("demo_content_ops")
    result = DuckDbEngine().execute("short_video_ops", sql[:-9], scope,
                                    row_limit=10000)
    if not result.success or result.truncated:
        raise RuntimeError(result.error or "Full ranking was truncated")
    cutoff = result.rows[9]["plays"]
    above = [row for row in result.rows if row["plays"] > cutoff]
    tied = [row for row in result.rows if row["plays"] == cutoff]
    policy = case["top_n_tie_policy"]
    if (policy["limit"] != 10 or policy["boundary_value"] != cutoff or
            policy["boundary_candidates"] != tied or
            case["expected_rows"][:len(above)] != above or
            not all(row in tied for row in case["expected_rows"][len(above):])):
        raise ValueError("Case tie annotation differs from the complete ranking")
    print({"full_count": len(result.rows), "cutoff": cutoff,
           "above_count": len(above), "tied_count": len(tied),
           "above": above, "tied": tied})


if __name__ == "__main__":
    main()
