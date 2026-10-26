"""Independent full typed-row, structure and per-domain real-login ACL verification."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import uuid

from scripts.m2_b_common import APPROVED_IMPORT_SPEC, digest_file, digest_json, require
from scripts.m2_b_structure import verify_structure
from scripts.m2_b_target import (arguments, connect, identity, journal, live_dependencies, load_credentials,
    load_initialization, load_inputs, protected_paths, quote, table_sql, transaction_settings)
from scripts.m2_b_typed_rows import POLICY, Rows, source_rows

TABLE_PRIVILEGES = ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'REFERENCES', 'TRIGGER')


def verify_rows(conn, manifest: dict, dump: Path, report: dict) -> str:
    report['tables'] = []
    report['snapshot'] = str(conn.execute('SELECT pg_current_snapshot()').fetchone()[0])
    for i, table in enumerate(manifest['dump']['tables'], 1):
        source = source_rows(dump, table)
        target = Rows(table['columns'])
        with conn.cursor(name='m2_rows_'+str(i)) as cursor:
            cursor.execute('SELECT '+', '.join(quote(c['name']) for c in table['columns'])+' FROM '+table_sql(table['name']))
            while batch := cursor.fetchmany(4096):
                for row in batch: target.add(row)
        actual = target.finish()
        # Record a mismatch before stopping; no row values or Gold are exposed.
        record = {'name': table['name'], 'database_id': table['database_id'], 'source': source,
                  'target': actual, 'passed': source == actual}
        report['tables'].append(record)
        require(record['passed'], 'Typed row/null/count mismatch: '+table['name'])
        print(f"typed [{i}/75] {table['name']}: rows={actual['row_count']}", flush=True)
    return digest_json({'policy': POLICY, 'import_spec_sha256': APPROVED_IMPORT_SPEC,
                        'tables': [{'name': t['name'], **t['target']} for t in report['tables']]})


def check_domain_acl(conn, manifest: dict, db: str) -> dict:
    domain = manifest['query_domains'][db]; allowed = set(domain['tables'])
    grants = conn.execute("""SELECT has_database_privilege(current_user,current_database(),'CONNECT'),
        has_database_privilege(current_user,current_database(),'CREATE'),has_database_privilege(current_user,current_database(),'TEMP'),
        has_schema_privilege(current_user,'public','USAGE'),has_schema_privilege(current_user,'public','CREATE')""").fetchone()
    require(grants == (True, False, False, True, False), 'Domain database/schema rights differ: '+db)
    tables = []
    for table in manifest['dump']['tables']:
        name = table['name']
        values = conn.execute('SELECT '+', '.join('has_table_privilege(current_user,%s,%s)' for _ in TABLE_PRIVILEGES),
            tuple(v for privilege in TABLE_PRIVILEGES for v in (table_sql(name), privilege))).fetchone()
        require(values == (name in allowed, False, False, False, False, False, False), 'Domain table ACL differs: '+db+'/'+name)
        column_grants = conn.execute("SELECT has_any_column_privilege(current_user,%s,'SELECT'),has_any_column_privilege(current_user,%s,'INSERT'),has_any_column_privilege(current_user,%s,'UPDATE'),has_any_column_privilege(current_user,%s,'REFERENCES')",
            (table_sql(name),)*4).fetchone()
        require(column_grants == (name in allowed, False, False, False), 'Domain column ACL differs: '+db+'/'+name)
        tables.append({'name': name, 'grants': dict(zip(TABLE_PRIVILEGES, values))})
    for sequence in manifest['dump']['sequences']:
        rights = conn.execute("SELECT has_sequence_privilege(current_user,%s,'USAGE'),has_sequence_privilege(current_user,%s,'SELECT'),has_sequence_privilege(current_user,%s,'UPDATE')", (table_sql(sequence),)*3).fetchone()
        require(rights == (False, False, False), 'Domain has unexpected sequence privilege')
    return {'database_id': db, 'role': domain['query_role'], 'database_schema_grants': list(grants),
            'table_acl': tables, 'checked_table_count': 75, 'checked_sequence_count': 24}


def denial_probes(conn, manifest: dict, db: str, output: dict | None = None) -> dict:
    allowed = manifest['query_domains'][db]['tables']
    table = next(t for t in manifest['dump']['tables'] if t['name'] == allowed[0])
    other = next(t['name'] for t in manifest['dump']['tables'] if t['name'] not in allowed)
    name = table_sql(table['name']); col = quote(table['columns'][0]['name'])
    probe = quote('_m2_probe_'+uuid.uuid4().hex)
    cases = [
        ('cross_domain_select', 'SELECT 1 FROM '+table_sql(other)+' LIMIT 1'),
        ('insert', 'INSERT INTO '+name+' SELECT * FROM '+name+' WHERE FALSE'),
        ('update', 'UPDATE '+name+' SET '+col+'='+col+' WHERE FALSE'),
        ('delete', 'DELETE FROM '+name+' WHERE FALSE'),
        ('create_table', 'CREATE TABLE public.'+probe+' (probe bigint)'),
        ('create_temp', 'CREATE TEMP TABLE '+probe+' (probe bigint)'),
        ('create_schema', 'CREATE SCHEMA '+probe),
        ('set_import_role', 'SET LOCAL ROLE '+quote(manifest['target']['import_role'])),
    ]
    output = {} if output is None else output
    records = []; output['checks'] = records
    # Read-write mode proves actual ACL denial beyond the configurable read-only default.
    # All writes have WHERE FALSE; any unexpected DDL success is rolled back.
    with conn.transaction(force_rollback=True):
        transaction_settings(conn, readonly=False)
        for operation, sql in cases:
            state = None
            try:
                with conn.transaction(): conn.execute(sql)
            except Exception as error:
                state = getattr(error, 'sqlstate', None)
            records.append({'operation': operation, 'sqlstate': state, 'passed': state == '42501'})
    output['read_write_probe_transaction_rolled_back'] = True
    require(all(r['passed'] for r in records), 'Expected ACL denial not observed: '+db)
    with conn.transaction():
        transaction_settings(conn, readonly=True)
        require(conn.execute('SELECT count(*) FROM '+name).fetchone() == (table['row_count'],), 'Domain read/count failed after denial recovery')
    output.update(connection_recovered=True, allowed_table_read_count=table['row_count'])
    return output


def validate(manifest: dict, dump: Path, initialization_id: str, credentials: dict, report: dict) -> None:
    role = manifest['target']['import_role']
    with connect(role, credentials['passwords'][role]) as conn:
        report['postgresql_connected'] = True
        with conn.transaction():
            transaction_settings(conn, readonly=True)
            require(conn.execute('SELECT pg_try_advisory_xact_lock(627221,20002)').fetchone() == (True,), 'Another M2 import/validation is running')
            report['source_identity'] = identity(conn, manifest, role, initialization_id)
            report['phase'] = 'structure'
            report['structure'] = verify_structure(conn, manifest)
            report['phase'] = 'typed_rows'
            data_version = verify_rows(conn, manifest, dump, report)
            report['phase'] = 'query_role_acl'
            report['domain_checks'] = []
            for db, domain in manifest['query_domains'].items():
                with connect(domain['query_role'], credentials['passwords'][domain['query_role']]) as query:
                    defaults = {key: query.execute('SHOW '+key).fetchone()[0] for key in
                        ('default_transaction_read_only', 'search_path', 'TimeZone', 'statement_timeout', 'lock_timeout')}
                    require(defaults == {'default_transaction_read_only': 'on', 'search_path': 'pg_catalog, public',
                        'TimeZone': 'UTC', 'statement_timeout': '30s', 'lock_timeout': '5s'}, 'Domain session defaults differ: '+db)
                    with query.transaction():
                        transaction_settings(query, readonly=True)
                        source = identity(query, manifest, domain['query_role'], initialization_id)
                        checks = check_domain_acl(query, manifest, db)
                    checks.update(identity=source, defaults=defaults, probes={})
                    report['domain_checks'].append(checks)
                    denial_probes(query, manifest, db, checks['probes'])
                    print('acl ['+str(len(report['domain_checks']))+'/11] '+db+': passed', flush=True)
    report.update(run_status='complete', phase='target_verified', target_data_verified=True,
        verified_data_version=data_version, verified_catalog_version=report['structure']['catalog_version'],
        validation_scope='Full native typed row multiset in one repeatable-read owner snapshot; independent domain logins/ACL and rollback probes. Revalidate after target changes. No runtime, Gold110 or model validation yet.',
        summary={'table_count': len(report['tables']), 'column_count': 798,
            'typed_row_match_count': sum(t['passed'] for t in report['tables']),
            'row_count': sum(t['target']['row_count'] for t in report['tables']),
            'query_role_count': len(report['domain_checks']), 'table_acl_checks': 75*11,
            'sequence_acl_checks': 24*11, 'denial_probe_count': 8*11})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); arguments(parser)
    parser.add_argument('--initialization-report', type=Path, required=True)
    parser.add_argument('--import-report', type=Path, required=True)
    args = parser.parse_args()
    with journal(args.output, 'M2 B PostgreSQL target consistency and ACL', protected=protected_paths(args, args.initialization_report, args.import_report)) as report:
        manifest, dump, evidence = load_inputs(args.preparation_dir, args.data_root)
        init = load_initialization(args.initialization_report, manifest)
        imported = json.loads(args.import_report.read_bytes())
        require(imported.get('stage') == 'M2 B controlled PostgreSQL import' and imported.get('run_status') == 'complete'
            and imported.get('transaction_outcome') == 'committed' and imported.get('database_imported') is True
            and imported.get('initialization_id') == init['initialization_id'] and imported.get('target') == manifest['target']
            and imported.get('import_spec_sha256') == APPROVED_IMPORT_SPEC and not imported.get('errors')
            and imported.get('initialization_report_sha256') == digest_file(args.initialization_report), 'Successful matching committed import evidence is required')
        report.update(target=manifest['target'], initialization_id=init['initialization_id'],
            source_evidence_sha256=evidence, import_report_sha256=digest_file(args.import_report),
            initialization_report_sha256=digest_file(args.initialization_report))
        if args.check_only:
            report.update(run_status='checked_only', summary={'planned_tables': 75, 'planned_query_roles': 11, 'no_database_connection': True})
        else:
            live_dependencies()
            credentials = load_credentials(args.credentials_file.resolve(), manifest, init['initialization_id'])
            validate(manifest, dump, init['initialization_id'], credentials, report)
    raise SystemExit(0 if report['run_status'] in ('complete', 'checked_only') else 1)


if __name__ == '__main__': main()
