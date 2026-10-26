"""M2 preparation helpers, independent of application .env and M1 runtime."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

BASE = Path(__file__).resolve().parents[1]
PROTOCOL_DIR = BASE / "evaluation/cases/bird_mini_dev/m2_pg_v1"
PROTOCOL_SHA256 = "174a4d909131d0b8333d446f5bcb0815fe27ec6023a98e51729f3096f975ac77"
TARGET_DATABASE = "askdata_m2_bird"
IMPORT_ROLE = "askdata_m2_import"
MIN_FREE_BYTES = 10 * 1024**3
APPROVED_IMPORT_SPEC = "46bb3555b5906478264c81b6ebc8ba2e86c6c3136bc3d8e3ecfc079770b0eede"


class PreparationError(ValueError):
    """Only controlled messages may be included verbatim in reports."""


def require(value: Any, message: str) -> None:
    if not value:
        raise PreparationError(message)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def digest_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def require_import_spec(manifest: dict) -> str:
    digest = digest_json(manifest)
    require(digest == APPROVED_IMPORT_SPEC, "Import specification differs from reviewed M2 B source manifest")
    return digest


def load_protocol(directory: Path = PROTOCOL_DIR) -> tuple[dict, dict]:
    require(digest_file(directory/"protocol.json") == PROTOCOL_SHA256, "Frozen M2 protocol differs")
    protocol = json.loads((directory/"protocol.json").read_bytes())
    for name, expected in protocol["artifact_sha256"].items():
        path = (directory/name).resolve()
        require(path.is_relative_to(directory.resolve()), "Invalid protocol artifact path")
        require(digest_file(path) == expected, "Frozen protocol artifact differs: " + name)
    dev = json.loads((directory/"development80.json").read_bytes())
    hold = json.loads((directory/"holdout30.json").read_bytes())
    require(not set(dev["database_ids"]) & set(hold["database_ids"]), "Database split overlap")
    roles = {db: "askdata_m2_ro_" + db for db in dev["database_ids"]+hold["database_ids"]}
    return protocol, {"database": TARGET_DATABASE, "schema": "public", "import_role": IMPORT_ROLE,
                      "query_roles": dict(sorted(roles.items()))}


def safe_error(error: BaseException) -> dict:
    state = getattr(error, "sqlstate", None)
    return {"type": type(error).__name__,
            "sqlstate": state if isinstance(state, str) and re.fullmatch(r"[A-Z0-9]{5}", state) else None,
            "message": str(error) if isinstance(error, PreparationError) else
                "Preparation failed; raw driver, SQL values and credential details omitted"}


def write_new_json(path: Path, report: dict) -> None:
    require(not path.exists(), "Choose a new output path; preserve previous evidence")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Serialize before opening, avoiding partial JSON on serialization errors.
    data = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False)+"\n").encode()
    with path.open("xb") as stream:
        stream.write(data)


def nearest_existing(path: Path) -> Path:
    while not path.exists():
        require(path.parent != path, "No existing ancestor for disk check")
        path = path.parent
    return path
