"""Frozen M1 B typed row digest, shared by preparation and live verification."""
from datetime import date, datetime
import hashlib
import json
from typing import Any


def json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="microseconds")
    if isinstance(value, date):
        return value.isoformat()
    return value


def typed_row_hash(values, fields) -> bytes:
    if len(values) != len(fields):
        raise ValueError("Typed row width differs from fields")
    normalized = []
    for value, field in zip(values, fields):
        kind = field["source_type"]
        value = float(value).hex() if value is not None and kind == "DOUBLE" else json_value(value)
        normalized.append([kind, value])
    return hashlib.sha256(json.dumps(normalized, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).digest()


def multiset_hash(hashes) -> str:
    digest = hashlib.sha256()
    for value in sorted(hashes):
        digest.update(value)
    return digest.hexdigest()
