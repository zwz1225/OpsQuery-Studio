"""Failure boundaries and exact COPY/native semantics; no PostgreSQL/model connection."""
from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from scripts.m2_b_common import APPROVED_IMPORT_SPEC, BASE, PreparationError, digest_json
from scripts.m2_b_target import (identity, journal, load_initialization, marker, protected_paths,
                                 quote, write_credentials)
from scripts.m2_b_structure import canonical, expectations, verify_structure
from scripts.m2_b_typed_rows import Rows, decode_copy, row_hash, source_rows, source_value
from scripts.import_m2_b_postgres import execute_import, transfer_copy
from scripts.validate_m2_b_postgres import check_domain_acl, denial_probes

MANIFEST = json.loads((BASE/'evaluation/cases/bird_mini_dev/m2_b_import_spec_v1.json').read_bytes())
INIT = '1'*32


class Result:
    def __init__(self, one=None, many=None): self.one = one; self.many = many
    def fetchone(self): return self.one
    def fetchall(self): return self.many


class CopyCursor:
    def __init__(self, count): self.rowcount = count; self.blocks = []
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def copy(self, sql): self.sql = sql; return self
    def write(self, block): self.blocks.append(block)


class CopyConnection:
    def __init__(self, count): self.cur = CopyCursor(count)
    def cursor(self): return self.cur


class TypedCopyTest(unittest.TestCase):
    def test_copy_escapes_null_literal_backslash_and_utf8(self):
        self.assertIsNone(decode_copy(b'\\N'))
        self.assertEqual(decode_copy(b'\\\\N'), '\\N')
        self.assertEqual(decode_copy(br'hello\tworld\n\\\101\x42\r\b\f\v'), 'hello\tworld\n\\AB\r\b\f\v')
        self.assertEqual(decode_copy('中文'.encode()), '中文')
        with self.assertRaises(PreparationError): decode_copy(b'bad\\')

    def test_real_is_native_binary32_and_utc_is_instant(self):
        self.assertEqual(source_value(b'1.1', 'REAL'), struct.unpack('!f', struct.pack('!f', 1.1))[0])
        self.assertEqual(source_value(b'2010-07-19 19:39:07.1+08', 'TIMESTAMPTZ'),
                         datetime.fromisoformat('2010-07-19T19:39:07.100000+08:00'))
        columns = [{'postgres_type': t} for t in ('BIGINT', 'REAL', 'TEXT', 'DATE', 'TIMESTAMPTZ')]
        a = (1, source_value(b'1.1','REAL'), '\\N', date(2020,1,1), datetime.fromisoformat('2020-01-01T08:00:00+08:00'))
        b = (*a[:4], datetime(2020,1,1,tzinfo=timezone.utc))
        self.assertEqual(row_hash(a, columns), row_hash(b, columns))
        self.assertNotEqual(row_hash(a, columns), row_hash((2,*a[1:]), columns))
        with self.assertRaises(PreparationError): row_hash((True,*a[1:]), columns)
        with self.assertRaises(PreparationError): row_hash((*a[:4],datetime(2020,1,1)), columns)

    def test_null_text_empty_order_and_duplicates(self):
        columns = [{'postgres_type':'TEXT'}]
        def digest(values):
            x = Rows(columns)
            for v in values: x.add((v,))
            return x.finish()
        self.assertEqual(digest(['a',None,'a']), digest(['a','a',None]))
        self.assertNotEqual(digest(['a',None,'a']), digest(['a',None]))
        self.assertNotEqual(digest([None]), digest(['']))
        self.assertNotEqual(digest(['\\N']), digest([None]))

    def test_copy_offsets_counts_and_typed_source_are_independent(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'dump.sql'; payload=b'1\t1.1\t\\N\n2\t2.5\t\\\\N\n'
            path.write_bytes(b'PREFIX\n'+payload+b'\\.\nAFTER\n')
            table={'name':'t','copy_sql':'COPY public.t (i,f,t) FROM stdin;', 'copy_bytes_start':7,
                'copy_bytes_end':7+len(payload), 'copy_payload_sha256':hashlib.sha256(payload).hexdigest(),
                'row_count':2,'null_counts':[0,0,1],
                'columns':[{'postgres_type':t} for t in ('BIGINT','REAL','TEXT')]}
            source=source_rows(path,table); self.assertEqual(source['row_count'],2)
            conn=CopyConnection(2); self.assertEqual(transfer_copy(conn,path,table),len(payload))
            self.assertEqual(b''.join(conn.cur.blocks),payload)
            for change in [{'copy_payload_sha256':'0'*64},{'row_count':3},{'copy_bytes_end':table['copy_bytes_end']-1}]:
                with self.subTest(change=change), self.assertRaises(PreparationError):
                    transfer_copy(CopyConnection(2),path,{**table,**change})
            with self.assertRaises(PreparationError): source_rows(path,{**table,'null_counts':[0,0,0]})


class BoundaryTest(unittest.TestCase):
    def test_exact_approved_structural_expectations(self):
        result=expectations(MANIFEST)
        self.assertEqual({k:len(v) for k,v in result.items()},
            {'constraints':155,'indexes':93,'defaults':95,'primary':68,'ownership':24,'values':24})
        self.assertEqual(canonical('a::bigint'),canonical('CAST(a AS BIGINT)'))
        self.assertEqual(quote('a"b'),'"a""b"')
        self.assertNotEqual(canonical('"A"'),canonical('a'))

    def test_initialization_evidence_rejects_checked_only_and_wrong_source(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'init.json'
            good={'stage':'M2 B independent initialization','run_status':'complete','initialization_verified':True,
                'target':MANIFEST['target'],'import_spec_sha256':APPROVED_IMPORT_SPEC,'initialization_id':INIT,'errors':[]}
            path.write_text(json.dumps(good)); self.assertEqual(load_initialization(path,MANIFEST),good)
            for change in [{'run_status':'checked_only'},{'initialization_verified':False},
                {'target':{**MANIFEST['target'],'database':'askdata_m1_test'}},{'import_spec_sha256':'0'*64}]:
                path.write_text(json.dumps({**good,**change}))
                with self.subTest(change=change),self.assertRaises(PreparationError):load_initialization(path,MANIFEST)

    def test_journal_exclusive_protected_and_redacted(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'report.json'
            with patch('builtins.print'):
                with journal(path,'unit',protected=[]) as row:
                    raise RuntimeError('password=sensitive host=secret')
            data=json.loads(path.read_bytes()); self.assertEqual(data['run_status'],'failed')
            self.assertNotIn('sensitive',path.read_text()); self.assertNotIn('host=secret',path.read_text())
            with self.assertRaises(PreparationError):
                with journal(path,'unit',protected=[]):pass
            with self.assertRaises(PreparationError):
                with journal(Path(root)/'new.json','unit',protected=[Path(root)]):pass

    def test_credentials_refuse_overwrite_and_project_location(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'private.json'; write_credentials(path,{'passwords':{'role':'secret'}})
            with self.assertRaises(FileExistsError):write_credentials(path,{'passwords':{}})
            self.assertIn('secret',path.read_text())
        with self.assertRaises(PreparationError):write_credentials(BASE/'private_test_never_created.json',{})


class ImportFake:
    def __init__(self, *, commit_failure=False):self.commit_failure=commit_failure;self.sql=[];self.active=False
    @contextmanager
    def transaction(self):
        self.active=True
        try:
            yield
            if self.commit_failure:raise RuntimeError('COMMIT lost response secret')
        finally:self.active=False
    def execute(self,sql,*args):
        self.sql.append(sql)
        if sql=='SELECT 1' or 'pg_try_advisory_xact_lock' in sql:return Result((1,))
        return Result()


class ImportRecoveryTest(unittest.TestCase):
    def context(self):
        return patch.multiple('scripts.import_m2_b_postgres',transaction_settings=lambda *a,**k:None,
            identity=lambda *a: {},object_inventory=lambda *a: [],require_no_executable_objects=lambda *a:None,
            transfer_copy=lambda *a: 1,grant_domains=lambda *a:[],verify_structure=lambda *a:{'constraint_count':155,'index_count':93})

    def test_success_executes_whitelist_not_author_settings_or_data_sql(self):
        conn=ImportFake();report={}
        with self.context(),patch('builtins.print'):execute_import(conn,MANIFEST,Path('ignored'),INIT,report)
        self.assertEqual(report['transaction_outcome'],'committed');self.assertEqual(len(report['copy_tables']),75)
        executed='\n'.join(conn.sql)
        self.assertNotIn('OWNER TO xiaolongli',executed)
        self.assertNotIn('SET statement_timeout = 0',executed)
        self.assertEqual(len([x for x in conn.sql if x.startswith('CREATE TABLE ')]),75)

    def test_precommit_failure_rolls_back_without_cleanup(self):
        conn=ImportFake();report={}
        with self.context(),patch('scripts.import_m2_b_postgres.transfer_copy',side_effect=PreparationError('bad copy')):
            with self.assertRaises(PreparationError):execute_import(conn,MANIFEST,Path('ignored'),INIT,report)
        self.assertEqual(report['transaction_outcome'],'rolled_back');self.assertTrue(report['rollback_verified'])
        self.assertFalse(any('DROP ' in s or 'TRUNCATE ' in s for s in conn.sql))

    def test_commit_connection_loss_stays_unknown_and_never_claims_rollback(self):
        conn=ImportFake(commit_failure=True);report={}
        with self.context(),patch('builtins.print'):
            with self.assertRaises(RuntimeError):execute_import(conn,MANIFEST,Path('ignored'),INIT,report)
        self.assertEqual(report['transaction_outcome'],'commit_pending_or_unknown')
        self.assertFalse(report['rollback_verified']);self.assertNotIn('SELECT 1',conn.sql)

    def test_nonempty_target_rejected_before_ddl(self):
        conn=ImportFake();report={}
        with self.context(),patch('scripts.import_m2_b_postgres.object_inventory',return_value=[('existing','r')]):
            with self.assertRaises(PreparationError):execute_import(conn,MANIFEST,Path('ignored'),INIT,report)
        self.assertFalse(any(x.startswith('CREATE') for x in conn.sql))


class InitializationConflictTest(unittest.TestCase):
    def test_fresh_target_or_role_conflict_prevents_credentials_and_database_mutations(self):
        from scripts.initialize_m2_b_postgres import initialize
        with tempfile.TemporaryDirectory() as root:
            root=Path(root); prior=root/'prior.json'
            prior.write_text(json.dumps({'run_status':'complete','ready_for_initialization':True,
                'preflight_check_version':2,'target':MANIFEST['target'],'errors':[]}))
            args=SimpleNamespace(pgdata=root,data_root=root,output=root/'out.json',credentials_file=root/'private.json',
                prompt_password=False,server_preflight=prior,admin_user='askdata_admin')
            state={'maintenance_database':'postgres','current_user':'askdata_admin','server_version_num':160015,
                'encoding':'UTF8','timezone':'UTC','data_directory':str(root),'server_address':'127.0.0.1/32',
                'server_port':55432,'superuser':True,'can_create_database':True,'can_create_role':True,
                'maintenance_collation':'C','maintenance_ctype':'C','maintenance_locale_provider':'c',
                'target_exists':False,'existing_m2_roles':[]}
            class Admin:
                def __enter__(self):return self
                def __exit__(self,*a):pass
                def execute(self,text,*a):
                    if text.startswith('SELECT'):return Result((True,))
                    raise AssertionError('Mutation must never run')
            for change in [{'target_exists':True},{'existing_m2_roles':['askdata_m2_import']}]:
                with self.subTest(change=change),patch.multiple('scripts.initialize_m2_b_postgres',
                    admin_password=lambda *a:'not-a-real-password',connect=lambda *a:Admin(),
                    capacity=lambda *a:[{'free_bytes':20*1024**3}],collect_database_state=lambda *a:{**state,**change}),\
                    patch('scripts.initialize_m2_b_postgres.write_credentials') as credentials,\
                    patch('scripts.initialize_m2_b_postgres.create_roles') as roles:
                    with self.assertRaises(PreparationError):initialize(args,MANIFEST,{})
                    credentials.assert_not_called();roles.assert_not_called()


class AclFake:
    def __init__(self,domain,*,leak=False,success=None):self.domain=domain;self.leak=leak;self.success=success;self.calls=[]
    @contextmanager
    def transaction(self,**kwargs):yield
    def execute(self,sql,args=None):
        self.calls.append((sql,args))
        if 'has_database_privilege' in sql:return Result((True,False,False,True,False))
        if 'has_table_privilege' in sql:
            allowed=args[0] in { 'public.'+quote(t) for t in MANIFEST['query_domains'][self.domain]['tables']}
            return Result((allowed or self.leak,False,False,False,False,False,False))
        if 'has_any_column_privilege' in sql:
            allowed=args[0] in {'public.'+quote(t) for t in MANIFEST['query_domains'][self.domain]['tables']}
            return Result((allowed,False,False,False))
        if 'has_sequence_privilege' in sql:return Result((False,False,False))
        if sql.startswith('SET TRANSACTION') or sql.startswith('SET LOCAL') and not sql.startswith('SET LOCAL ROLE'):return Result()
        if sql.startswith('SELECT count(*) FROM'):
            t=next(t for t in MANIFEST['dump']['tables'] if t['name']==MANIFEST['query_domains'][self.domain]['tables'][0])
            return Result((t['row_count'],))
        if sql==self.success:return Result()
        error=RuntimeError('driver secret');error.sqlstate='42501';raise error


class DomainAclTest(unittest.TestCase):
    def test_all_domains_check_all_tables_not_only_own_tables(self):
        for db in MANIFEST['query_domains']:
            conn=AclFake(db);result=check_domain_acl(conn,MANIFEST,db)
            self.assertEqual(result['checked_table_count'],75)
            self.assertEqual(sum(t['grants']['SELECT'] for t in result['table_acl']),len(MANIFEST['query_domains'][db]['tables']))

    def test_one_cross_domain_grant_is_rejected(self):
        with self.assertRaises(PreparationError):check_domain_acl(AclFake('financial',leak=True),MANIFEST,'financial')

    def test_real_write_mode_probes_require_expected_sqlstate_and_recovery(self):
        result=denial_probes(AclFake('financial'),MANIFEST,'financial')
        self.assertEqual(len(result['checks']),8);self.assertTrue(result['connection_recovered'])
        self.assertTrue(result['read_write_probe_transaction_rolled_back'])

    def test_unexpected_probe_success_is_failure_and_records_it(self):
        conn=AclFake('financial',success='SET LOCAL ROLE "askdata_m2_import"');output={}
        with self.assertRaises(PreparationError):denial_probes(conn,MANIFEST,'financial',output)
        self.assertFalse(output['checks'][-1]['passed']);self.assertTrue(output['read_write_probe_transaction_rolled_back'])


class StructureFake:
    """Catalog fixture with server-style definitions; mutations model live drift."""
    def __init__(self, mutation=None):
        self.expected=expectations(MANIFEST);self.mutation=mutation
    def execute(self,sql,args=None):
        e=self.expected;owner=MANIFEST['target']['import_role']
        if sql.startswith('SET LOCAL'):return Result()
        if sql.startswith('SELECT count(*)'):return Result((0,))
        if 'SELECT c.relname,c.relkind' in sql:
            objects=sorted([(t['name'],'r') for t in MANIFEST['dump']['tables']]+
                [(s,'S') for s in MANIFEST['dump']['sequences']]+[(i,'i') for i in e['indexes']])
            if self.mutation=='extra_object':objects.append(('unexpected','v'))
            return Result(many=objects)
        if 'c.relrowsecurity' in sql:
            return Result((owner,self.mutation=='rls',False,'p','r',False))
        if 'SELECT a.attname,format_type' in sql:
            name=args[0];t=next(t for t in MANIFEST['dump']['tables'] if t['name']==name)
            from scripts.m2_b_target import TYPE_NAMES
            rows=[(c['name'],TYPE_NAMES[c['postgres_type']],c['not_null'] or c['name'] in e['primary'].get(name,[]),
                '','',e['defaults'].get((name,c['name']))) for c in t['columns']]
            if self.mutation=='default' and name=='account':rows[0]=(*rows[0][:5],'99::bigint')
            if self.mutation=='type' and name=='account':rows[0]=(rows[0][0],'text',*rows[0][2:])
            return Result(many=rows)
        if 'SELECT c.relname,k.conname' in sql:
            rows=[]
            for (table,name),text in e['constraints'].items():
                import sqlglot
                tree=sqlglot.parse_one(text,read='postgres');definition=tree.args['actions'][0].expressions[0].expressions[0].sql(dialect='postgres')
                rows.append((table,name,definition,self.mutation!='unvalidated',False,False,'p' if 'PRIMARY KEY' in text else 'f'))
            if self.mutation=='missing_constraint':rows.pop()
            return Result(many=rows)
        if 'SELECT i.relname,pg_get_indexdef' in sql:
            rows=[(n,d,self.mutation!='index_invalid',True,owner) for n,d in e['indexes'].items()]
            if self.mutation=='missing_index':rows.pop()
            return Result(many=rows)
        if 'FROM pg_sequence s' in sql:return Result(('bigint',1,1,9223372036854775807,1,1,False,owner))
        if 'FROM pg_depend d' in sql:
            return Result(many=[(*e['ownership'][args[0]],'n' if self.mutation=='sequence_link' else 'a')])
        if sql.startswith('SELECT last_value,is_called'):
            name=sql.split('public."',1)[1][:-1]
            return Result((0,False) if self.mutation=='sequence_value' else e['values'][name])
        raise AssertionError(sql)


class StructureDriftTest(unittest.TestCase):
    def test_catalog_accepts_matching_structure(self):
        result=verify_structure(StructureFake(),MANIFEST)
        self.assertEqual((result['table_count'],result['column_count'],result['constraint_count'],result['index_count'],result['sequence_count']),
                         (75,798,155,93,24))
    def test_catalog_rejects_specific_live_drift(self):
        for mutation in ['extra_object','rls','default','type','unvalidated','missing_constraint','index_invalid','missing_index','sequence_link','sequence_value']:
            with self.subTest(mutation=mutation),self.assertRaises(PreparationError):
                verify_structure(StructureFake(mutation),MANIFEST)


if __name__=='__main__':unittest.main()
