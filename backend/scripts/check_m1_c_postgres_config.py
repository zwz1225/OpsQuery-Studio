"""Offline M1 C1 settings/evidence check. Does not open a database connection."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from app.config import BASE_DIR, settings
from app.datasources.postgres_config import PostgresConfig, PostgresConfigError, load_recorded_source


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-missing-password", action="store_true",
        help="Check parameters/evidence only; credentials remain pending")
    parser.add_argument("--output", type=Path, default=BASE_DIR/"evaluation/results/m1_c1_postgres_config_server.json")
    args = parser.parse_args()
    output = args.output.resolve()
    protected = (BASE_DIR/"data/databases").resolve()
    if protected in output.parents:
        raise PostgresConfigError("Output must be outside frozen data directories")
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"stage": "M1 C1 PostgreSQL settings and recorded source", "run_status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(), "password_required": not args.allow_missing_password,
        "application_backend": settings.data_backend, "application_source_id": settings.data_source_id,
        "postgresql_connected": False, "live_target_verified": False, "runtime_available": False,
        "new_model_request_count": 0, "errors": []}
    # Reserve independent evidence before work; never overwrite previous files.
    with output.open("x", encoding="utf-8") as stream:
        try:
            config = PostgresConfig.from_settings(settings, require_password=not args.allow_missing_password)
            report["configuration"] = config.public()
            report["recorded_source"] = load_recorded_source(config).public()
            report.update(run_status="complete", credentials_configured=bool(config.password),
                pending_steps=["Connection lifecycle/pool", "Live metadata/data verification", "PostgreSQL executor and catalog assembly"])
        except Exception as error:
            report["run_status"] = "failed"
            report["errors"].append({"type": type(error).__name__,
                "message": str(error) if isinstance(error, PostgresConfigError) else "Configuration check failed; raw details omitted"})
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["run_status"] == "complete" else 1)


if __name__ == "__main__":
    main()
