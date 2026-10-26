"""Read-only server preflight. Does not create roles, databases or import data."""
from __future__ import annotations

import argparse
import getpass
from importlib.metadata import version
import ipaddress
import json
import os
from pathlib import Path
import platform
import shutil

from scripts.m2_b_common import (BASE, MIN_FREE_BYTES, PreparationError, load_protocol,
    nearest_existing, now, require, safe_error, write_new_json)


def collect_database_state(conn, target: dict) -> dict:
    """Only SELECT inside an explicit read-only transaction; no target connection."""
    with conn.transaction():
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SELECT pg_catalog.set_config('search_path', 'pg_catalog', true)")
        conn.execute("SELECT pg_catalog.set_config('statement_timeout', '10000', true)")
        identity = conn.execute("""SELECT current_database(), current_user,
            current_setting('server_version_num')::int, current_setting('server_encoding'),
            current_setting('TimeZone'), current_setting('data_directory'),
            inet_server_addr()::text, inet_server_port(),
            r.rolsuper, r.rolcreatedb, r.rolcreaterole,
            d.datcollate, d.datctype, d.datlocprovider
            FROM pg_roles r JOIN pg_database d ON d.datname=current_database()
            WHERE r.rolname=current_user""").fetchone()
        target_row = conn.execute("SELECT datname FROM pg_catalog.pg_database WHERE datname=%s",
                                  (target["database"],)).fetchone()
        names = [target["import_role"], *target["query_roles"].values()]
        roles = conn.execute("SELECT rolname FROM pg_catalog.pg_roles WHERE rolname=ANY(%s)", (names,)).fetchall()
    require(identity is not None, "Missing PostgreSQL connection identity")
    return {"maintenance_database":identity[0], "current_user":identity[1], "server_version_num":identity[2],
            "encoding":identity[3], "timezone":identity[4], "data_directory":identity[5],
            "server_address":identity[6], "server_port":identity[7], "superuser":identity[8],
            "can_create_database":identity[9], "can_create_role":identity[10],
            "maintenance_collation":identity[11], "maintenance_ctype":identity[12],
            "maintenance_locale_provider":identity[13], "target_exists":target_row is not None,
            "existing_m2_roles":sorted(row[0] for row in roles)}


def evaluate_state(state: dict, *, admin_user: str, pgdata: Path, free_bytes: int) -> list[dict]:
    # PostgreSQL inet::text may preserve the /32 host mask. Accept the exact
    # configured IPv4 host in either representation, never a wider subnet.
    endpoint_matches=False
    try:
        address=ipaddress.ip_interface(state["server_address"])
        endpoint_matches=(isinstance(address,ipaddress.IPv4Interface)
            and address.ip==ipaddress.IPv4Address("127.0.0.1")
            and address.network.prefixlen==32 and state["server_port"]==55432)
    except (ValueError,TypeError):
        pass
    checks = [
        ("maintenance_identity", state["maintenance_database"]=="postgres" and state["current_user"]==admin_user),
        ("postgresql_16", 160000<=state["server_version_num"]<170000),
        ("encoding_locale", (state["encoding"],state["maintenance_collation"],state["maintenance_ctype"],state["maintenance_locale_provider"])==("UTF8","C","C","c")),
        ("local_endpoint", endpoint_matches),
        ("expected_cluster_directory", Path(state["data_directory"]).resolve()==pgdata.resolve()),
        ("initialization_privileges", state["superuser"] or (state["can_create_database"] and state["can_create_role"])),
        ("independent_target_absent", not state["target_exists"]),
        ("m2_roles_absent", not state["existing_m2_roles"]),
        ("import_capacity_budget", free_bytes>=MIN_FREE_BYTES),
    ]
    return [{"name":name,"passed":bool(passed)} for name,passed in checks]


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-user", default="askdata_admin")
    parser.add_argument("--pgdata",type=Path,default=Path.home()/".local/share/askdata/pg16-data")
    parser.add_argument("--data-root",type=Path,default=BASE/"data/external/bird_mini_dev")
    parser.add_argument("--prompt-password",action="store_true")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    output=args.output.resolve()
    require(not output.exists(),"Choose a new output path; preserve previous evidence")
    require(not output.is_relative_to(args.data_root.resolve()),"Report must be outside external source data")
    report={"stage":"M2 B read-only server preflight","preflight_check_version":2,
            "run_status":"failed","started_at":now(),
            "postgresql_connected":False,"ready_for_initialization":False,"database_created":False,
            "data_imported":False,"new_model_request_count":0,"errors":[]}
    try:
        _,target=load_protocol()
        report["target"]=target
        require(platform.system()=="Linux", "Server preflight requires the Linux PostgreSQL host")
        require(args.pgdata.is_dir(),"Expected PostgreSQL data directory does not exist")
        report["host"]={"system":platform.system(),"machine":platform.machine(),"python":platform.python_version()}
        dependencies={name:version(name) for name in ("psycopg","psycopg-pool")}
        report["dependencies"]=dependencies
        require(dependencies=={"psycopg":"3.2.13","psycopg-pool":"3.2.8"},"PostgreSQL dependency versions differ from the verified M1 pins")
        password=getpass.getpass("M2 PostgreSQL admin password: ") if args.prompt_password else os.getenv("M2_PG_ADMIN_PASSWORD", "")
        require(bool(password),"Use --prompt-password or set M2_PG_ADMIN_PASSWORD; M1 PG_PASSWORD is not read")
        import psycopg
        with psycopg.connect(host="127.0.0.1",port=55432,dbname="postgres",user=args.admin_user,password=password,
                connect_timeout=10,autocommit=True,application_name="askdata_m2_preflight",
                options="-c default_transaction_read_only=on -c TimeZone=UTC -c statement_timeout=10000") as conn:
            report["postgresql_connected"]=True
            state=collect_database_state(conn,target)
        report["database_state"]=state
        actual_pgdata=Path(state["data_directory"])
        require(actual_pgdata.is_dir(),"Connected cluster data directory is not locally accessible")
        paths={"postgres_data":actual_pgdata,"project":BASE,"source_storage":nearest_existing(args.data_root.resolve()),
               "report_storage":nearest_existing(output.parent)}
        report["disk"]={name:{"path":str(path),"free_bytes":shutil.disk_usage(path).free} for name,path in paths.items()}
        free=min(report["disk"][name]["free_bytes"] for name in ("postgres_data","source_storage"))
        report["capacity_policy"]={"minimum_additional_free_bytes":MIN_FREE_BYTES,
            "scope":"Conservative preparation gate, not a measured import footprint; recheck after source upload"}
        report["checks"]=evaluate_state(state,admin_user=args.admin_user,pgdata=args.pgdata,free_bytes=free)
        report["ready_for_initialization"]=all(c["passed"] for c in report["checks"])
        report["run_status"]="complete" if report["ready_for_initialization"] else "blocked"
    except Exception as error:
        report["errors"].append(safe_error(error))
    report["finished_at"]=now()
    write_new_json(output,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(0 if report["ready_for_initialization"] else 1)


if __name__=="__main__":
    main()
