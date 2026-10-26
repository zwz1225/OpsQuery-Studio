"""M2 source parsing, immutable evidence, redaction and read-only preflight gates."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.m2_b_common import (BASE, MIN_FREE_BYTES, PreparationError, load_protocol,
                               require_import_spec, safe_error, write_new_json)
from scripts.m2_b_dump import Statements, classify, scan_dump
from scripts.preflight_m2_b_server import collect_database_state, evaluate_state


class DumpInspectionTest(unittest.TestCase):
    def scan(self, text):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'source.sql';path.write_bytes(text.encode())
            return scan_dump(path, {'sample':'domain'})

    def test_copy_rows_never_become_sql_and_offsets_match_raw_bytes(self):
        text=('CREATE TABLE public.sample (\n id bigint,\n "Display Name" text\n);\n'
              'COPY public.sample (id, "Display Name") FROM stdin;\n'
              '1\tDROP DATABASE important;\n2\t\\N\n\\.\n')
        r=self.scan(text);t=r['tables'][0]
        payload=text.encode()[t['copy_bytes_start']:t['copy_bytes_end']]
        self.assertEqual(t['row_count'],2)
        self.assertEqual(t['null_counts'],[0,1])
        self.assertEqual(t['columns'][1]['name'],'Display Name')
        self.assertEqual(hashlib.sha256(payload).hexdigest(),t['copy_payload_sha256'])
        self.assertEqual(len(r['control_statements']),1)

    def test_semicolons_inside_literal_do_not_split_statements(self):
        lexer=Statements()
        r=lexer.feed("CREATE TABLE public.sample (value text DEFAULT 'a;b'); -- ignored\n")
        self.assertEqual(len(r),1)
        self.assertIn("'a;b'",r[0])

    def test_unknown_controls_file_copy_and_psql_are_rejected(self):
        for sql in ("DROP DATABASE askdata_m1_test;", "COPY public.sample TO PROGRAM 'cmd';",
                    "CREATE ROLE broad SUPERUSER;", "SELECT pg_read_file('/etc/passwd');"):
            with self.subTest(sql=sql),self.assertRaises(PreparationError): classify(sql)
        with self.assertRaises(PreparationError): self.scan('\\! echo command\n')

    def test_incomplete_copy_duplicate_table_and_wrong_columns_fail(self):
        base='CREATE TABLE public.sample (\n id bigint\n);\n'
        for suffix in ('COPY public.sample (id) FROM stdin;\n1\n',
                       'COPY public.sample (other) FROM stdin;\n1\n\\.\n',
                       'COPY public.sample (id) FROM stdin;\n1\t2\n\\.\n',base):
            with self.subTest(suffix=suffix),self.assertRaises(PreparationError): self.scan(base+suffix)

    def test_ownership_is_recorded_for_mapping_not_executed(self):
        r=classify('ALTER TABLE public.sample OWNER TO xiaolongli;')
        self.assertEqual(r['import_action'],'map_to_m2_import_role')
        with self.assertRaises(PreparationError): classify('ALTER TABLE public.sample OWNER TO other_role;')


class ReadonlyServerTest(unittest.TestCase):
    def state(self):
        return {'maintenance_database':'postgres','current_user':'askdata_admin','server_version_num':160015,
                'encoding':'UTF8','maintenance_collation':'C','maintenance_ctype':'C','maintenance_locale_provider':'c',
                'server_address':'127.0.0.1','server_port':55432,'data_directory':str(Path('cluster').resolve()),
                'superuser':False,'can_create_database':True,'can_create_role':True,
                'target_exists':False,'existing_m2_roles':[]}

    def test_expected_cluster_absent_target_and_capacity_pass(self):
        checks=evaluate_state(self.state(),admin_user='askdata_admin',pgdata=Path('cluster'),free_bytes=MIN_FREE_BYTES)
        self.assertTrue(all(c['passed'] for c in checks))

    def test_postgres_inet_host_mask_is_accepted_without_accepting_other_hosts_or_subnets(self):
        for address,expected in [('127.0.0.1',True),('127.0.0.1/32',True),
                                 ('127.0.0.1/24',False),('127.0.0.2/32',False),
                                 ('192.168.0.1/32',False),('::1/128',False),
                                 ('::ffff:127.0.0.1/128',False),('',False),(None,False),
                                 ('127.0.0.1/32 invalid',False)]:
            state=self.state();state['server_address']=address
            checks=evaluate_state(state,admin_user='askdata_admin',pgdata=Path('cluster'),free_bytes=MIN_FREE_BYTES)
            with self.subTest(address=address):
                self.assertEqual(next(c['passed'] for c in checks if c['name']=='local_endpoint'),expected)
        state=self.state();state.update(server_address='127.0.0.1/32',server_port=5432)
        checks=evaluate_state(state,admin_user='askdata_admin',pgdata=Path('cluster'),free_bytes=MIN_FREE_BYTES)
        self.assertFalse(next(c['passed'] for c in checks if c['name']=='local_endpoint'))

    def test_each_wrong_identity_existing_target_roles_and_capacity_fails(self):
        changes=[{'current_user':'askdata_readonly'},{'maintenance_database':'askdata_m1_test'},
                 {'data_directory':str(Path('other_cluster').resolve())},{'server_port':5432},
                 {'server_version_num':150000},{'encoding':'LATIN1'},{'target_exists':True},
                 {'existing_m2_roles':['askdata_m2_import']},{'can_create_role':False}]
        for update in changes:
            state=self.state();state.update(update)
            with self.subTest(update=update):
                self.assertFalse(all(c['passed'] for c in evaluate_state(state,admin_user='askdata_admin',pgdata=Path('cluster'),free_bytes=MIN_FREE_BYTES)))
        self.assertFalse(all(c['passed'] for c in evaluate_state(self.state(),admin_user='askdata_admin',pgdata=Path('cluster'),free_bytes=MIN_FREE_BYTES-1)))

    def test_collector_uses_one_readonly_transaction_and_parameterized_target(self):
        class Result:
            def __init__(self,row):self.row=row
            def fetchone(self):return self.row
            def fetchall(self):return self.row
        class Connection:
            def __init__(self):self.calls=[];self.in_transaction=False
            @contextmanager
            def transaction(self):
                self.in_transaction=True
                try:yield
                finally:self.in_transaction=False
            def execute(self,sql,params=None):
                assert self.in_transaction
                self.calls.append((sql,params))
                if 'server_version_num' in sql:return Result(('postgres','askdata_admin',160015,'UTF8','UTC','/data','127.0.0.1',55432,True,True,True,'C','C','c'))
                if 'WHERE datname=%s' in sql:return Result(None)
                if 'rolname=ANY' in sql:return Result([])
                return Result(None)
        conn=Connection();target={'database':'askdata_m2_bird','import_role':'askdata_m2_import','query_roles':{'x':'askdata_m2_ro_x'}}
        state=collect_database_state(conn,target)
        self.assertFalse(state['target_exists'])
        self.assertEqual(conn.calls[0][0],'SET TRANSACTION READ ONLY')
        self.assertTrue(all(sql.startswith(('SELECT','SET TRANSACTION')) for sql,_ in conn.calls))
        self.assertIn(('SELECT datname FROM pg_catalog.pg_database WHERE datname=%s',('askdata_m2_bird',)),conn.calls)


class EvidenceTest(unittest.TestCase):
    def test_approved_spec_cannot_change_target_copy_hash_or_types(self):
        manifest=json.loads((BASE/'evaluation/cases/bird_mini_dev/m2_b_import_spec_v1.json').read_bytes())
        require_import_spec(manifest)
        for mutation in ('target','copy','type'):
            bad=deepcopy(manifest)
            if mutation=='target':bad['target']['database']='askdata_m1_test'
            elif mutation=='copy':bad['dump']['tables'][0]['copy_payload_sha256']='0'*64
            else:bad['dump']['tables'][0]['columns'][0]['postgres_type']='TEXT'
            with self.subTest(mutation=mutation),self.assertRaises(PreparationError):require_import_spec(bad)

    def test_protocol_and_target_are_independent_from_m1_settings(self):
        protocol,target=load_protocol()
        self.assertEqual(protocol['protocol_id'],'m2_bird_pg_v1')
        self.assertEqual(target['database'],'askdata_m2_bird')
        self.assertEqual(len(target['query_roles']),11)
        self.assertNotIn('askdata_readonly',target['query_roles'].values())

    def test_no_overwrite_and_no_raw_database_exception_text(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'report.json';write_new_json(path,{'result':'first'})
            with self.assertRaises(PreparationError):write_new_json(path,{'result':'second'})
            self.assertEqual(json.loads(path.read_bytes()),{'result':'first'})
        error=RuntimeError('password=private dbname=private SQL content')
        error.sqlstate='28P01'
        public=safe_error(error)
        self.assertNotIn('private',json.dumps(public));self.assertEqual(public['sqlstate'],'28P01')


if __name__=='__main__':unittest.main()
