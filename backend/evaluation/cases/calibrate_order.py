"""Audit and annotate cases that explicitly request result ordering."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


CASE_FILE = Path(__file__).with_name("all_cases.jsonl")
EXPLICIT_ORDER_PHRASES = ("按时间升序", "从高到低展示", "从低到高展示")


def order_column(case: dict) -> str | None:
    sql = case["gold_sql"].upper()
    if " ORDER BY " not in sql:
        if len(case["expected_rows"]) <= 1:
            return None
        raise ValueError(f"{case['case_id']}: ordered multirow case has no Gold ORDER BY")
    final_order = sql.rsplit(" ORDER BY ", 1)[1]
    token = final_order.split(",", 1)[0].split()[0]
    columns = case["expected_columns"]
    if token.isdigit():
        position = int(token) - 1
        if position < 0 or position >= len(columns):
            raise ValueError(f"{case['case_id']}: invalid ORDER BY position {token}")
        return columns[position]
    column = token.rsplit(".", 1)[-1].lower()
    if column not in columns:
        raise ValueError(f"{case['case_id']}: ORDER BY column {column} is not projected")
    return column


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write calibrated annotations")
    parser.add_argument("--cases", type=Path, default=CASE_FILE)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    selected = []
    for case in rows:
        if not any(phrase in case["query"] for phrase in EXPLICIT_ORDER_PHRASES):
            continue
        column = order_column(case)
        case["order_sensitive"] = True
        if column is not None:
            case["order_by_column"] = column
        selected.append(case["case_id"])
    if args.write:
        args.cases.write_text(
            "\n".join(json.dumps(case, ensure_ascii=False, separators=(",", ":"))
                      for case in rows) + "\n", encoding="utf-8",
        )
    print(f"cases={len(rows)} explicit_order={len(selected)} write={args.write}")


if __name__ == "__main__":
    main()
