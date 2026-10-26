from datetime import date, datetime
from decimal import Decimal
from typing import Any


def json_value(value: Any) -> Any:
    """Keep the existing DuckDB result normalization contract."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value
