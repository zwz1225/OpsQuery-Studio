"""M2 target/evidence boundaries. Does not load application settings or M1 secrets."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import getpass
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import uuid

from scripts.m2_b_common import (APPROVED_IMPORT_SPEC, BASE, MIN_FREE_BYTES, PROTOCOL_DIR,
    PROTOCOL_SHA256, digest_file, digest_json, load_protocol, nearest_existing, now,
    require, require_import_spec, safe_error)

DEFAULT_PREPARATION = BASE / 'evaluation/results/m2_b_source_server_20261015'
DEFAULT_CREDENTIALS = Path.home() / '.local/share/askdata/m2_bird_credentials.json'
TYPE_NAMES = {'BIGINT': 'bigint', 'TEXT': 'text', 'DATE': 'date',
              'TIMESTAMPTZ': 'timestamp with time zone', 'REAL': 'real'}


def quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_sql(name: str) -> str:
    return 'public.' + quote(name)


def arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--preparation-dir', type=Path, default=DEFAULT_PREPARATION)
    parser.add_argument('--data-root', type=Path, default=BASE/'data/external/bird_mini_dev')
    parser.add_argument('--credentials-file', type=Path, default=DEFAULT_CREDENTIALS)
    parser.add_argument('--check-only', action='store_true', help='Offline inputs only; no database or credentials created/read')
    parser.add_argument('--output', type=Path, required=True)


def load_inputs(preparation: Path, data_root: Path) -> tuple[dict, Path, dict]:
    require(version('sqlglot') == '30.17.0', 'SQLGlot version differs from frozen preparation dependency')
    _, target = load_protocol()
    paths = {n: preparation/n for n in ('source_preflight.json', 'import_manifest.json', 'preparation_review.json')}
    records = {n: json.loads(p.read_bytes()) for n, p in paths.items()}
    manifest = records['import_manifest.json']
    require_import_spec(manifest)
    require(manifest['target'] == target, 'M2 target differs from frozen protocol')
    for n in ('source_preflight.json', 'preparation_review.json'):
        row = records[n]
        require(row['run_status'] == 'complete' and not row.get('errors'), 'Source preparation did not pass')
        require(row['import_spec_sha256'] == APPROVED_IMPORT_SPEC, 'Source preparation identity differs')
    for n, h in records['preparation_review.json']['input_artifact_sha256'].items():
        require(n in paths and digest_file(paths[n]) == h, 'Source preparation evidence link differs')
    for item in manifest['sources']:
        path = (data_root/item['relative_to_data_root']).resolve()
        require(path.is_relative_to(data_root.resolve()), 'Source path escapes data root')
        require(path.is_file() and path.stat().st_size == item['size_bytes']
                and digest_file(path) == item['sha256'], 'Frozen source missing or changed: '+item['relative_to_data_root'])
    from evaluation.bird_protocol import load_canonical_questions
    load_canonical_questions((data_root/manifest['question_relative_path']).read_bytes())
    dump = next(data_root/s['relative_to_data_root'] for s in manifest['sources'] if s['kind'] == 'postgres_dump')
    return manifest, dump, {n: digest_file(p) for n, p in paths.items()}


def live_dependencies() -> None:
    require(platform.system() == 'Linux', 'Live M2 operations require the Linux PostgreSQL host')
    require({n: version(n) for n in ('psycopg', 'psycopg-pool')} ==
            {'psycopg': '3.2.13', 'psycopg-pool': '3.2.8'}, 'PostgreSQL dependencies differ from verified pins')


def capacity(*paths: Path) -> list[dict]:
    result = [{'path': str(p), 'free_bytes': shutil.disk_usage(nearest_existing(p)).free} for p in paths]
    require(all(r['free_bytes'] >= MIN_FREE_BYTES for r in result), 'Fewer than 10 GiB free; operation not started')
    return result


def admin_password(prompt: bool) -> str:
    password = getpass.getpass('M2 PostgreSQL admin password: ') if prompt else os.getenv('M2_PG_ADMIN_PASSWORD', '')
    require(bool(password), 'Use --prompt-password or M2_PG_ADMIN_PASSWORD; M1 PG_PASSWORD is not read')
    return password


def connect(role: str, password: str, database: str = 'askdata_m2_bird'):
    import psycopg
    return psycopg.connect(host='127.0.0.1', port=55432, dbname=database, user=role,
        password=password, connect_timeout=10, autocommit=True, client_encoding='UTF8',
        application_name='askdata_m2_preparation', options='-c TimeZone=UTC')


def transaction_settings(conn, *, readonly: bool) -> None:
    conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, '+('READ ONLY' if readonly else 'READ WRITE'))
    conn.execute('SET LOCAL search_path TO pg_catalog, public')
    conn.execute("SET LOCAL TimeZone TO 'UTC'")
    conn.execute("SET LOCAL DateStyle TO 'ISO, YMD'")
    conn.execute('SET LOCAL extra_float_digits TO 3')
    conn.execute('SET LOCAL standard_conforming_strings TO on')
    conn.execute("SET LOCAL default_tablespace TO ''")
    conn.execute("SET LOCAL default_table_access_method TO 'heap'")
    conn.execute("SET LOCAL statement_timeout TO '600s'")
    conn.execute("SET LOCAL lock_timeout TO '5s'")


def marker(initialization_id: str) -> str:
    require(uuid.UUID(initialization_id).hex == initialization_id, 'Invalid initialization identity')
    return 'askdata_m2_bird:'+initialization_id+':'+APPROVED_IMPORT_SPEC


def write_credentials(path: Path, content: dict) -> None:
    require(not path.is_relative_to(BASE.parent), 'Credentials must be outside project directory')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write((json.dumps(content, ensure_ascii=False)+'\n').encode())
        stream.flush(); os.fsync(stream.fileno())
    if os.name == 'posix':
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)


def load_credentials(path: Path, manifest: dict, initialization_id: str) -> dict:
    require(not path.is_relative_to(BASE.parent), 'Credentials must be outside project directory')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                and info.st_mode & 0o077 == 0 and info.st_nlink == 1 and info.st_size <= 65536,
                'Credential file must be a private regular file owned by current user (0600)')
        value = json.load(stream)
    require(value.get('version') == 1 and value['initialization_id'] == initialization_id and value['target'] == manifest['target']
            and value['import_spec_sha256'] == APPROVED_IMPORT_SPEC, 'Credential identity differs')
    expected = {manifest['target']['import_role'], *manifest['target']['query_roles'].values()}
    require(set(value['passwords']) == expected and all(isinstance(p, str) and len(p) >= 32
            for p in value['passwords'].values()), 'Missing or malformed M2 role credentials')
    return value


def load_initialization(path: Path, manifest: dict) -> dict:
    row = json.loads(path.read_bytes())
    require(row.get('stage') == 'M2 B independent initialization' and row.get('run_status') == 'complete'
        and row.get('initialization_verified') is True and not row.get('errors')
        and row.get('target') == manifest['target'] and row.get('import_spec_sha256') == APPROVED_IMPORT_SPEC,
        'A successful matching initialization report is required')
    marker(row['initialization_id'])
    return row


def identity(conn, manifest: dict, role: str, initialization_id: str) -> dict:
    row = conn.execute("""SELECT current_database(),current_user,current_setting('server_version_num')::int,
        current_setting('server_encoding'),current_setting('TimeZone'),d.datcollate,d.datctype,
        d.datlocprovider::text,pg_get_userbyid(d.datdba),shobj_description(d.oid,'pg_database'),
        inet_server_addr()::text,inet_server_port() FROM pg_database d WHERE datname=current_database()""").fetchone()
    from ipaddress import ip_interface
    require(row and row[:2] == (manifest['target']['database'], role), 'Connected M2 database/user differs')
    require(160000 <= row[2] < 170000 and row[3:8] == ('UTF8', 'UTC', 'C', 'C', 'c'), 'Target PostgreSQL/locale differs')
    require(row[8] == manifest['target']['import_role'] and row[9] == marker(initialization_id), 'Target owner or initialization marker differs')
    require(str(ip_interface(row[10])) == '127.0.0.1/32' and row[11] == 55432, 'Target endpoint differs')
    flags = conn.execute('SELECT rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolinherit FROM pg_roles WHERE rolname=current_user').fetchone()
    require(flags == (True, False, False, False, False, False, False), 'M2 role has unexpected privilege flags')
    memberships = conn.execute('SELECT count(*) FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member WHERE r.rolname=current_user').fetchone()[0]
    require(memberships == 0, 'M2 role must not have role memberships')
    settings = conn.execute("""SELECT s.setconfig FROM pg_db_role_setting s JOIN pg_roles r ON r.oid=s.setrole
        JOIN pg_database d ON d.oid=s.setdatabase WHERE r.rolname=current_user AND d.datname=current_database()""").fetchone()
    wanted = {'search_path=pg_catalog, public', 'TimeZone=UTC', 'statement_timeout=30000', 'lock_timeout=5000',
              'default_transaction_read_only='+('off' if role == manifest['target']['import_role'] else 'on')}
    require(settings and set(settings[0]) == wanted, 'Recorded per-database role settings differ')
    require(conn.execute("SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname='public'").fetchone() ==
            (manifest['target']['import_role'],), 'M2 schema owner differs')
    schemas = conn.execute("SELECT nspname FROM pg_namespace WHERE nspname !~ '^pg_' AND nspname<>'information_schema' ORDER BY 1").fetchall()
    require(schemas == [('public',)], 'Unexpected user schema in M2 target')
    return {'database': row[0], 'role': row[1], 'server_version_num': row[2], 'encoding': row[3],
            'timezone': row[4], 'collation': row[5], 'ctype': row[6], 'locale_provider': row[7],
            'database_owner': row[8], 'initialization_id': initialization_id,
            'logical_domains': sorted(manifest['query_domains']), 'import_spec_sha256': APPROVED_IMPORT_SPEC}


def object_inventory(conn) -> list[tuple]:
    return conn.execute("""SELECT c.relname,c.relkind::text FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' ORDER BY 1""").fetchall()


def require_no_executable_objects(conn) -> None:
    for query in (
        "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'",
        "SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal",
        "SELECT count(*) FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'",
        "SELECT count(*) FROM pg_event_trigger",
        "SELECT count(*) FROM pg_default_acl d JOIN pg_roles r ON r.oid=d.defaclrole WHERE r.rolname LIKE 'askdata_m2_%'",
    ):
        require(conn.execute(query).fetchone() == (0,), 'Unexpected function/trigger/policy/default privilege in target')


@contextmanager
def journal(path: Path, stage: str, *, protected: list[Path]):
    path = path.resolve()
    require(not any(path == p.resolve() or path.is_relative_to(p.resolve()) for p in protected), 'Report path overlaps protected inputs')
    require(not path.exists(), 'Choose a new output path; preserve previous evidence')
    path.parent.mkdir(parents=True, exist_ok=True)
    report = {'stage': stage, 'run_status': 'running', 'started_at': now(), 'errors': [],
        'postgresql_connected': False, 'database_created': False, 'database_imported': False,
        'target_data_verified': False, 'new_model_request_count': 0, 'protocol_sha256': PROTOCOL_SHA256,
        'import_spec_sha256': APPROVED_IMPORT_SPEC}
    # Reserve the name and test durable report storage before database mutations.
    with path.open('xb') as stream:
        stream.write((json.dumps(report)+'\n').encode()); stream.flush(); os.fsync(stream.fileno())
    try:
        yield report
    except (Exception, KeyboardInterrupt) as error:
        report['run_status'] = 'failed'; report['errors'].append(safe_error(error))
    finally:
        report['finished_at'] = now()
        temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
        with temporary.open('xb') as stream:
            stream.write((json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode())
            stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        print(json.dumps({'output': str(path), 'stage': stage, 'run_status': report['run_status'],
            'summary': report.get('summary'), 'errors': report['errors']}, ensure_ascii=False, indent=2))


def protected_paths(args, *extra: Path) -> list[Path]:
    return [args.data_root, PROTOCOL_DIR, args.preparation_dir, args.credentials_file, *extra]
