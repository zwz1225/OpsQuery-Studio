"""Create a fresh independent M2 database and twelve private roles. Never reuses or drops a target."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import secrets
import uuid

from scripts.m2_b_common import APPROVED_IMPORT_SPEC, require, digest_file, now
from scripts.m2_b_target import (arguments, admin_password, capacity, connect, identity, journal,
    live_dependencies, load_inputs, marker, object_inventory, protected_paths, quote,
    require_no_executable_objects, transaction_settings, write_credentials)
from scripts.preflight_m2_b_server import collect_database_state, evaluate_state


def create_roles(conn, target: dict, passwords: dict) -> None:
    from psycopg import sql
    with conn.transaction():
        conn.execute("SET LOCAL statement_timeout TO '60s'")
        conn.execute("SET LOCAL lock_timeout TO '5s'")
        conn.execute("SET LOCAL password_encryption TO 'scram-sha-256'")
        for role in [target['import_role'], *target['query_roles'].values()]:
            conn.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}')
                         .format(sql.Identifier(role), sql.Literal(passwords[role])))


def configure_database(conn, target: dict, initialization_id: str) -> None:
    from psycopg import sql
    db = quote(target['database']); owner = quote(target['import_role'])
    with conn.transaction():
        conn.execute("SET LOCAL statement_timeout TO '60s'")
        conn.execute("SET LOCAL lock_timeout TO '5s'")
        conn.execute('REVOKE ALL ON DATABASE '+db+' FROM PUBLIC')
        conn.execute('ALTER SCHEMA public OWNER TO '+owner)
        conn.execute('REVOKE ALL ON SCHEMA public FROM PUBLIC')
        for role in [target['import_role'], *target['query_roles'].values()]:
            ident = quote(role)
            conn.execute('GRANT CONNECT ON DATABASE '+db+' TO '+ident)
            conn.execute('GRANT USAGE ON SCHEMA public TO '+ident)
            for key, value in [('search_path', 'pg_catalog, public'), ('TimeZone', 'UTC'),
                               ('statement_timeout', '30000'), ('lock_timeout', '5000'),
                               ('default_transaction_read_only', 'off' if role == target['import_role'] else 'on')]:
                if key == 'search_path':
                    conn.execute('ALTER ROLE '+ident+' IN DATABASE '+db+' SET search_path TO pg_catalog, public')
                else:
                    conn.execute(sql.SQL('ALTER ROLE {} IN DATABASE {} SET {} TO {}').format(
                        sql.Identifier(role), sql.Identifier(target['database']), sql.Identifier(key), sql.Literal(value)))
        conn.execute(sql.SQL('COMMENT ON DATABASE {} IS {}').format(sql.Identifier(target['database']), sql.Literal(marker(initialization_id))))


def initialize(args, manifest: dict, report: dict) -> None:
    from psycopg import sql
    require(args.pgdata.is_dir(), 'Expected local PostgreSQL data directory is missing')
    target = manifest['target']; password = admin_password(args.prompt_password)
    report['disk'] = capacity(args.pgdata, args.data_root, args.output.parent, args.credentials_file.parent)
    prior = json.loads(args.server_preflight.read_bytes())
    require(prior.get('run_status') == 'complete' and prior.get('ready_for_initialization') is True
        and prior.get('preflight_check_version') == 2 and prior.get('target') == target
        and not prior.get('errors'), 'Successful matching v2 server preflight report is required')
    report['server_preflight_sha256'] = digest_file(args.server_preflight)
    with connect(args.admin_user, password, 'postgres') as admin:
        report['postgresql_connected'] = True
        admin.execute("SELECT pg_catalog.set_config('statement_timeout','60000',false)")
        admin.execute("SELECT pg_catalog.set_config('lock_timeout','5000',false)")
        require(admin.execute("SELECT pg_try_advisory_lock(627221, 20001)").fetchone() == (True,), 'Another M2 initializer is running')
        state = collect_database_state(admin, target)
        checks = evaluate_state(state, admin_user=args.admin_user, pgdata=args.pgdata,
                                free_bytes=min(x['free_bytes'] for x in report['disk']))
        report.update(fresh_server_state=state, checks=checks)
        require(all(c['passed'] for c in checks), 'Fresh server checks failed; no target is reused or removed')
        initialization_id = uuid.uuid4().hex
        passwords = {role: secrets.token_urlsafe(36) for role in [target['import_role'], *target['query_roles'].values()]}
        write_credentials(args.credentials_file.resolve(), {'version': 1, 'created_at': now(),
            'initialization_id': initialization_id, 'import_spec_sha256': APPROVED_IMPORT_SPEC,
            'target': target, 'passwords': passwords})
        report.update(initialization_id=initialization_id, credentials_file_created=True,
                      credential_storage='Private 0600 file outside project; passwords never included in reports',
                      recovery='No automatic DROP/role deletion. On partial failure preserve report and private credentials for review.')
        report['phase'] = 'create_roles'
        report['roles_creation_outcome'] = 'pending_or_unknown'
        create_roles(admin, target, passwords)
        report['roles_creation_outcome'] = 'committed'
        report['roles_created'] = sorted(passwords)
        report['phase'] = 'create_database'
        report['database_creation_outcome'] = 'pending_or_unknown'
        admin.execute(sql.SQL("CREATE DATABASE {} OWNER {} TEMPLATE template0 ENCODING 'UTF8' LOCALE_PROVIDER libc LC_COLLATE 'C' LC_CTYPE 'C'")
                      .format(sql.Identifier(target['database']), sql.Identifier(target['import_role'])))
        report.update(database_created=True, database_creation_outcome='created')
        report['phase'] = 'configure_target'
        with connect(args.admin_user, password, target['database']) as target_admin:
            configure_database(target_admin, target, initialization_id)
        # Login verification uses actual new accounts, never SET ROLE as an admin.
        report['phase'] = 'verify_logins'
        report['login_checks'] = []
        for role in passwords:
            with connect(role, passwords[role]) as conn:
                defaults = conn.execute('SHOW default_transaction_read_only').fetchone()[0]
                require(defaults == ('off' if role == target['import_role'] else 'on'), 'M2 role read-only default differs')
                with conn.transaction():
                    transaction_settings(conn, readonly=True)
                    observed = identity(conn, manifest, role, initialization_id)
                    require(not object_inventory(conn), 'Initialized target is not empty')
                    require_no_executable_objects(conn)
                    rights = conn.execute("SELECT has_database_privilege(current_user,current_database(),'CREATE'),has_database_privilege(current_user,current_database(),'TEMP'),has_schema_privilege(current_user,'public','CREATE')").fetchone()
                    require(rights == ((True, True, True) if role == target['import_role'] else (False, False, False)), 'Initial M2 privileges differ')
                    report['login_checks'].append({'identity': observed, 'default_read_only': defaults,
                                                  'create_temp_schema_create': list(rights), 'empty': True})
        report.update(run_status='complete', phase='initialized_empty', initialization_verified=True,
                      summary={'role_login_count': 12, 'database_count': 1, 'table_count': 0})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); arguments(parser)
    parser.add_argument('--admin-user', default='askdata_admin')
    parser.add_argument('--prompt-password', action='store_true')
    parser.add_argument('--pgdata', type=Path, default=Path.home()/'.local/share/askdata/pg16-data')
    parser.add_argument('--server-preflight', type=Path, default=Path('evaluation/results/m2_b_server_preflight_server_v2.json'))
    args = parser.parse_args()
    with journal(args.output, 'M2 B independent initialization', protected=protected_paths(args, args.server_preflight)) as report:
        manifest, _, evidence = load_inputs(args.preparation_dir, args.data_root)
        report.update(target=manifest['target'], source_evidence_sha256=evidence)
        if args.check_only:
            report.update(run_status='checked_only', initialization_verified=False,
                          summary={'planned_roles': 12, 'planned_tables': 75, 'no_database_connection': True})
        else:
            live_dependencies(); initialize(args, manifest, report)
    raise SystemExit(0 if report['run_status'] in ('complete', 'checked_only') else 1)


if __name__ == '__main__': main()
