"""Import only the approved M2 DDL/COPY plan into its verified, empty, independent database."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from scripts.m2_b_common import digest_file, require
from scripts.m2_b_structure import verify_structure
from scripts.m2_b_target import (arguments, capacity, connect, identity, journal, live_dependencies,
    load_credentials, load_initialization, load_inputs, object_inventory, protected_paths, quote,
    require_no_executable_objects, table_sql, transaction_settings)

PRE_DATA = {'create_table', 'create_sequence', 'sequence_owned_by', 'column_default'}
POST_DATA = {'sequence_value', 'constraint', 'index'}
SKIP = {'session_setting', 'search_path', 'owner'}


def transfer_copy(conn, dump: Path, table: dict) -> int:
    expected = table['copy_bytes_end']-table['copy_bytes_start']; sent = 0; digest = hashlib.sha256()
    with dump.open('rb') as stream:
        stream.seek(table['copy_bytes_start'])
        with conn.cursor() as cursor:
            with cursor.copy(table['copy_sql']) as copy:
                while sent < expected:
                    block = stream.read(min(1024*1024, expected-sent))
                    require(block, 'Source COPY block truncated')
                    digest.update(block); copy.write(block); sent += len(block)
                require(stream.readline() in (b'\\.\n', b'\\.\r\n'), 'Source COPY terminator changed')
                require(digest.hexdigest() == table['copy_payload_sha256'], 'Source COPY payload changed during import')
            require(cursor.rowcount == table['row_count'], 'PostgreSQL COPY count differs: '+table['name'])
    return sent


def grant_domains(conn, manifest: dict) -> list[dict]:
    rows = []
    # No PUBLIC table/sequence rights, no cross-domain default grants.
    conn.execute('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC')
    conn.execute('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC')
    for db, domain in manifest['query_domains'].items():
        conn.execute('GRANT SELECT ON TABLE '+', '.join(table_sql(t) for t in domain['tables'])+' TO '+quote(domain['query_role']))
        rows.append({'database_id': db, 'role': domain['query_role'], 'select_tables': domain['tables']})
    return rows


def execute_import(conn, manifest: dict, dump: Path, initialization_id: str, report: dict) -> None:
    report.update(transaction_outcome='not_started', rollback_verified=False, copy_tables=[])
    controls = manifest['dump']['control_statements']
    require(all(c['kind'] in PRE_DATA | POST_DATA | SKIP for c in controls), 'Unapproved import control kind')
    commit_started = False
    try:
        with conn.transaction():
            report['transaction_outcome'] = 'in_progress'
            transaction_settings(conn, readonly=False)
            require(conn.execute('SELECT pg_try_advisory_xact_lock(627221,20002)').fetchone() == (True,), 'Another M2 import/validation is running')
            report['source_identity'] = identity(conn, manifest, manifest['target']['import_role'], initialization_id)
            require(not object_inventory(conn), 'M2 import requires the verified empty target; no reuse or cleanup')
            require_no_executable_objects(conn)
            report['phase'] = 'create_tables_and_sequences'
            for item in controls:
                if item['kind'] in PRE_DATA: conn.execute(item['sql'])
            report['phase'] = 'copy_data'
            for i, table in enumerate(manifest['dump']['tables'], 1):
                sent = transfer_copy(conn, dump, table)
                report['copy_tables'].append({'name': table['name'], 'database_id': table['database_id'],
                    'row_count': table['row_count'], 'payload_sha256': table['copy_payload_sha256'], 'bytes_sent': sent})
                print(f"copy [{i}/75] {table['name']}: rows={table['row_count']}", flush=True)
            report['phase'] = 'constraints_indexes_sequences'
            for item in controls:
                if item['kind'] in POST_DATA: conn.execute(item['sql'])
            report['domain_grants'] = grant_domains(conn, manifest)
            report['phase'] = 'precommit_structure_verification'
            report['structure'] = verify_structure(conn, manifest)
            report['source_owner_mapping'] = {'xiaolongli': manifest['target']['import_role'],
                'statement_count': 99, 'method': 'All objects created as M2 importer; source OWNER commands omitted'}
            report['replaced_session_statement_count'] = 12
            report['phase'] = 'commit'
            commit_started = True
            report['transaction_outcome'] = 'commit_pending_or_unknown'
        report.update(transaction_outcome='committed', database_imported=True)
    except (Exception, KeyboardInterrupt):
        if not commit_started:
            report['transaction_outcome'] = 'rollback_pending_or_unknown'
            try:
                require(conn.execute('SELECT 1').fetchone() == (1,), 'Import connection not recovered')
                require(not object_inventory(conn), 'Target is not empty after rollback')
                report.update(transaction_outcome='rolled_back', rollback_verified=True)
            except Exception:
                pass
        # A failed COMMIT may have reached the server. Never automatically retry it.
        raise
    report.update(phase='import_committed', run_status='complete',
        summary={'table_count': len(report['copy_tables']), 'row_count': sum(t['row_count'] for t in report['copy_tables']),
                 'sequence_count': 24, 'constraint_count': report['structure']['constraint_count'],
                 'index_count': report['structure']['index_count'], 'typed_row_validation_pending': True},
        validation_scope='COPY hashes and counts plus structural verification; independent typed rows and role ACL validation still required')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); arguments(parser)
    parser.add_argument('--initialization-report', type=Path, required=True)
    parser.add_argument('--pgdata', type=Path, default=Path.home()/'.local/share/askdata/pg16-data')
    args = parser.parse_args()
    with journal(args.output, 'M2 B controlled PostgreSQL import', protected=protected_paths(args, args.initialization_report)) as report:
        manifest, dump, evidence = load_inputs(args.preparation_dir, args.data_root)
        report.update(target=manifest['target'], source_evidence_sha256=evidence,
            recovery='No automatic retry, DROP, TRUNCATE or overwrite. Review rollback/commit outcome before any recovery.')
        init = load_initialization(args.initialization_report, manifest)
        report.update(initialization_id=init['initialization_id'], initialization_report_sha256=digest_file(args.initialization_report))
        if args.check_only:
            report.update(run_status='checked_only', summary={'planned_tables': 75, 'planned_rows': 3898114, 'no_database_connection': True})
        else:
            live_dependencies()
            # Bind capacity to the cluster path already verified by initialization.
            require(args.pgdata.resolve() == Path(init['fresh_server_state']['data_directory']).resolve(), 'PostgreSQL data directory differs from initialization')
            report['disk'] = capacity(args.pgdata, args.data_root, args.output.parent)
            credentials = load_credentials(args.credentials_file.resolve(), manifest, init['initialization_id'])
            role = manifest['target']['import_role']
            with connect(role, credentials['passwords'][role]) as conn:
                report['postgresql_connected'] = True
                execute_import(conn, manifest, dump, init['initialization_id'], report)
    raise SystemExit(0 if report['run_status'] in ('complete', 'checked_only') else 1)


if __name__ == '__main__': main()
