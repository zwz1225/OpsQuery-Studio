"""External runtime/budget/result boundaries, with fakes unless marked Linux isolation."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import date,datetime,timezone
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import urllib.error

from scripts.m2_b_common import BASE,PreparationError,digest_json
from evaluation.bird.evidence import Evidence,scorer_gold,public_cases
from evaluation.bird.budgets import Budget,BirdFailure
from evaluation.bird.native import consume,tagged
from evaluation.bird.sql import validate_sql
from evaluation.bird.model import Models,ModelConfig
from evaluation.bird.runtime import BirdConnections,BirdRuntime,BirdRegistry
from evaluation.bird_protocol import compare_ex_rows,validate_agent_input

DATA=Path('E:/PythonLearn/datasets/bird_mini_dev') if sys.platform=='win32' else BASE/'data/external/bird_mini_dev'


class Result:
    def __init__(self,one=None,many=None):self.one=one;self.many=many
    def fetchone(self):return self.one
    def fetchall(self):return self.many


class Cursor:
    def __init__(self,rows,columns=None):
        self.rows=iter(rows);self.calls=[];self.description=[SimpleNamespace(name=n) for n in (columns or ['x'])]
    def fetchmany(self,n):
        self.calls.append(n);out=[]
        for _ in range(n):
            try:out.append(next(self.rows))
            except StopIteration:break
        return out


class NativeResultTest(unittest.TestCase):
    def test_native_precision_datetime_and_column_positions_survive(self):
        row=(2**62,Decimal('1.00000000000000000001'),date(2020,1,1),datetime(2020,1,1,tzinfo=timezone.utc),None)
        result=consume(Cursor([row],['a','b','c','d','e']))
        self.assertEqual(result.rows,[row]);self.assertIsInstance(result.rows[0][1],Decimal)
        self.assertTrue(compare_ex_rows(result.rows,[row]))
        self.assertFalse(compare_ex_rows(result.rows,[(row[0],Decimal(1),*row[2:])]))
        self.assertEqual(tagged(row[1]),['decimal','1.00000000000000000001'])

    def test_row_limit_probes_one_more_and_never_returns_partial(self):
        cursor=Cursor([(1,),(2,)])
        self.assertTrue(consume(cursor,row_limit=2).complete);self.assertIn(1,cursor.calls)
        with self.assertRaises(BirdFailure) as cm:consume(Cursor([(1,),(2,),(3,)]),row_limit=2)
        self.assertEqual(cm.exception.category,'result_row_limit')

    def test_payload_limit_and_unhashable_results_fail_closed(self):
        for value in [('x'*1000,),([1,2],),({'x':1},)]:
            with self.subTest(value=type(value[0]).__name__),self.assertRaises(BirdFailure):consume(Cursor([value]),byte_limit=100)

    def test_empty_duplicate_names_order_and_multiplicity(self):
        self.assertEqual(consume(Cursor([])).rows,[])
        result=consume(Cursor([(1,2),(1,2)],['same','same']))
        self.assertEqual(result.columns,['same','same']);self.assertEqual(len(result.rows),2)
        self.assertTrue(compare_ex_rows(result.rows,[(1,2)]));self.assertFalse(compare_ex_rows(result.rows,[(2,1)]))
        self.assertTrue(result.preview()['preview_only'])

    def test_preview_cap_does_not_change_native_rows(self):
        result=consume(Cursor([(i,) for i in range(250)]))
        self.assertEqual(len(result.rows),250);self.assertEqual(len(result.preview()['rows']),200)
        self.assertTrue(result.preview()['preview_truncated'])


class BudgetTest(unittest.TestCase):
    def test_attempts_shared_across_operations_and_retries(self):
        b=Budget();b.model_attempt('embedding');b.model_attempt('rerank',retry=1)
        for _ in range(14):b.model_attempt('embedding')
        with self.assertRaises(BirdFailure):b.model_attempt('chat')
        self.assertEqual(b.total_attempts,16);self.assertEqual(b.chat_attempts,0)
        self.assertTrue(all(e['usage'] is None for e in b.events))

    def test_chat_cap_separate_from_total_and_each_case_fresh(self):
        b=Budget()
        for _ in range(10):b.model_attempt('chat')
        with self.assertRaises(BirdFailure):b.model_attempt('chat')
        self.assertEqual(Budget().total_attempts,0)

    def test_sql_and_validation_and_generation_caps_cannot_be_reset_by_request(self):
        b=Budget()
        for _ in range(3):b.sql_call();b.validation(1);b.generation(1)
        for action in (b.sql_call,lambda:b.validation(1),lambda:b.generation(1),lambda:b.validation(True),lambda:b.validation(4)):
            with self.assertRaises(BirdFailure):action()
        b.validation(2);self.assertEqual(b.validation_attempts[2],1)

    def test_utf8_bytes_transport_retry_and_expired_deadline(self):
        b=Budget();b.model_attempt('chat',prompt=('中'*32768).encode())
        with self.assertRaises(BirdFailure):b.model_attempt('chat',prompt=('中'*32769).encode())
        with self.assertRaises(BirdFailure):b.model_attempt('chat',retry=2)
        b.started-=601
        with self.assertRaises(BirdFailure):b.remaining()


class SqlBoundaryTest(unittest.TestCase):
    def test_original_gold110_passes_policy_without_rewriting(self):
        e=Evidence.load(DATA)
        for g in scorer_gold().values():
            with self.subTest(case_id=g['case_id']):self.assertEqual(validate_sql(g['gold_sql'],set(e.domain(g['database_id'])['tables'])),g['gold_sql'])

    def test_unknown_cross_schema_write_and_side_effects_are_rejected(self):
        queries=['SELECT 1; SELECT 2','DELETE FROM account','WITH x AS (DELETE FROM account RETURNING *) SELECT * FROM x',
            'SELECT * INTO x FROM account','SELECT * FROM account FOR UPDATE','SELECT pg_sleep(1)',
            "SELECT pg_read_file('/etc/passwd')",'SELECT set_config(\'x\',\'y\',false)',
            'SELECT * FROM pg_catalog.pg_roles','SELECT * FROM other.account','SELECT * FROM otherdb.public.account',
            'SELECT * FROM users','WITH account AS (SELECT * FROM pg_authid) SELECT * FROM account',
            'SELECT public.count(*) FROM account',"SELECT 'account'::regclass"]
        for query in queries:
            with self.subTest(query=query),self.assertRaises((BirdFailure,ValueError)):validate_sql(query,{'account'})

    def test_quoted_names_cte_and_unquoted_postgres_case(self):
        for query,names in [('SELECT * FROM ACCOUNT',{'account'}),('SELECT "School Name" FROM public.schools',{'schools'}),
            ('WITH x AS (SELECT account_id FROM account) SELECT account_id FROM x',{'account'})]:
            self.assertEqual(validate_sql(query,names),query)
        with self.assertRaises(BirdFailure):validate_sql('SELECT * FROM "ACCOUNT"',{'account'})


class EvidenceTest(unittest.TestCase):
    def test_accepted_versions_all_domains_and_no_legacy_fallback(self):
        e=Evidence.load(DATA)
        self.assertEqual(sum(len(e.tables(d)) for d in e.manifest['query_domains']),75)
        with self.assertRaises(PreparationError):e.domain('short_video_ops')
        with self.assertRaises(PreparationError):e.domain('public')
        for split,count in [('smoke8',8),('development80',80),('holdout30',30)]:
            rows=public_cases(split);self.assertEqual(len(rows),count)
            for row in rows:
                validate_agent_input(row)
                with self.assertRaises(ValueError):validate_agent_input({**row,'gold_sql':'SELECT 1'})

    def test_description_mapping_uses_only_domain_files(self):
        e=Evidence.load(DATA);total=0
        if not DATA.is_dir():self.skipTest('Official local source descriptions not present')
        for db in e.manifest['query_domains']:
            values,diagnostic=e.descriptions(db)
            self.assertEqual(set(values),set(e.domain(db)['tables']));total+=sum(len(v) for v in values.values())
            self.assertEqual(len(diagnostic['files']),len(e.tables(db)))
        self.assertEqual(total,798)


class HttpTest(unittest.TestCase):
    @contextmanager
    def deadline(self,*args):yield
    def test_retry_consumes_shared_budget_and_redacts_error_body(self):
        b=Budget();m=Models(ModelConfig('fake-private-key'),b)
        error=urllib.error.HTTPError('https://example.invalid',503,'SECRET_PROVIDER_BODY',{},None)
        with patch('evaluation.bird.model.hard_deadline',self.deadline),patch('evaluation.bird.model.open_url',side_effect=error):
            with self.assertRaises(BirdFailure) as cm:m.post('embedding','https://example.invalid',{'input':['x']})
        self.assertEqual(b.total_attempts,2);self.assertNotIn('SECRET',str(cm.exception));self.assertNotIn('fake-private-key',repr(m.config))

    def test_chat_configuration_output_limit_usage_and_returned_model(self):
        b=Budget();m=Models(ModelConfig('fake-private-key'),b);requests=[]
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,n):return json.dumps({'model':'returned-version','choices':[{'message':{'content':'{"action":"clarify"}'}}]}).encode()
        def opening(request,timeout,**kwargs):requests.append(json.loads(request.data));return Response()
        with patch('evaluation.bird.model.hard_deadline',self.deadline),patch('evaluation.bird.model.open_url',side_effect=opening):
            result=m.chat('system','question')
        self.assertEqual(result['action'],'clarify');self.assertEqual(requests[0]['max_tokens'],4096)
        self.assertEqual(requests[0]['model'],'qwen3.7-plus');self.assertFalse(requests[0]['enable_thinking'])
        self.assertIsNone(b.events[0]['usage']);self.assertEqual(b.events[0]['returned_model'],'returned-version')

    def test_oversized_prompt_never_starts_http_request(self):
        m=Models(ModelConfig('fake-private-key'),Budget())
        with patch('evaluation.bird.model.open_url') as request:
            with self.assertRaises(BirdFailure):m.chat('x'*98305,'q')
            request.assert_not_called()

    def test_provider_reported_output_over_cap_is_not_used(self):
        m=Models(ModelConfig('fake-private-key'),Budget())
        with patch.object(m,'post',return_value={'usage':{'completion_tokens':4097},'choices':[{'message':{'content':'{"action":"query","sql":"SELECT 1"}'}}]}):
            with self.assertRaises(BirdFailure) as cm:m.chat('system','question')
        self.assertEqual(cm.exception.category,'chat_output_token_limit')


class FakeConnection:
    def __init__(self,status):self.status=status;self.pgconn=SimpleNamespace(transaction_status=status.IDLE);self.autocommit=True;self.closed=False;self.sql=[]
    @contextmanager
    def transaction(self):
        self.pgconn.transaction_status=self.status.INTRANS
        try:yield
        finally:self.pgconn.transaction_status=self.status.IDLE
    def execute(self,sql,args=None):self.sql.append(sql);return Result((1,))
    def rollback(self):self.pgconn.transaction_status=self.status.IDLE
    def close(self):self.closed=True


class Pool:
    def __init__(self,**kwargs):self.kwargs=kwargs;self.close_count=0;self.returned=[]
    def open(self,**kwargs):pass
    def wait(self,**kwargs):pass
    def getconn(self,**kwargs):return self.connection
    def putconn(self,conn):self.returned.append(conn)
    def close(self,**kwargs):self.close_count+=1


class LifecycleTest(unittest.TestCase):
    def test_bounded_role_pool_cleanup_and_idempotent_close(self):
        e=Evidence.load(DATA);manager=BirdConnections(e,'superhero','fake',pool_factory=Pool)
        self.assertEqual(manager.pool.kwargs['max_size'],1);self.assertEqual(manager.pool.kwargs['max_waiting'],1)
        self.assertEqual(manager.pool.kwargs['kwargs']['user'],'askdata_m2_ro_superhero')
        conn=FakeConnection(manager.status);manager.pool.connection=conn;manager.open()
        with self.assertRaises(BirdFailure):
            with manager.transaction():raise BirdFailure('query_test_failure')
        self.assertIn('RESET ROLE',conn.sql);self.assertIn('RESET ALL',conn.sql)
        self.assertEqual(manager.pool.returned,[conn]);self.assertEqual(conn.pgconn.transaction_status,manager.status.IDLE)
        manager.close();manager.close();self.assertEqual(manager.pool.close_count,1)
        with self.assertRaises(BirdFailure):manager.open()

    def test_bad_cleanup_discards_connection(self):
        e=Evidence.load(DATA);manager=BirdConnections(e,'superhero','fake',pool_factory=Pool)
        conn=FakeConnection(manager.status);manager.pool.connection=conn;manager.open()
        original=conn.execute
        def execute(sql,*args):
            if sql=='RESET ROLE':raise RuntimeError('private-driver-error')
            return original(sql,*args)
        conn.execute=execute
        with self.assertRaises(BirdFailure):
            with manager.transaction():pass
        self.assertTrue(conn.closed);self.assertEqual(manager.pool.returned,[conn]);manager.close()


class RuntimeBindingTest(unittest.TestCase):
    def make_runtime(self):
        e=Evidence.load(DATA)
        if not DATA.is_dir():self.skipTest('Official description files not present')
        columns=e.validation['structure']['verified_structure']['columns']
        tables=e.tables('superhero');selected={t['name']:columns[t['name']] for t in tables}
        typed={t['name']:t['target'] for t in e.validation['tables'] if t['name'] in selected}
        guards={t['name']:[t['row_count'],'a'*64] for t in tables}
        class Connections:
            closed=False
            def open(self):return self
            def require_open(self):
                if self.closed:raise BirdFailure('runtime_closed')
            @contextmanager
            def transaction(self):yield SimpleNamespace(execute=lambda *args:Result(('1:1:',)))
            def close(self):self.closed=True
        con=Connections()
        with patch.object(BirdRuntime,'_structure',return_value=selected),patch.object(BirdRuntime,'_verify_typed',return_value=typed),patch.object(BirdRuntime,'_content_guards',return_value=guards):
            runtime=BirdRuntime(e,'superhero','fake',connections=con)
        return runtime,e,selected,guards,Connections

    def test_catalog_contains_only_own_fields_and_receipt_identity(self):
        runtime,e,selected,guards,C=self.make_runtime()
        self.assertEqual({t['name'] for t in runtime.catalog.tables},set(e.domain('superhero')['tables']))
        self.assertEqual(runtime.identity.logical_database_id,'superhero');self.assertEqual(runtime.identity.catalog_version,runtime.catalog.version)
        receipt=runtime.receipt();receipt['database_id']='financial'
        with patch.object(BirdRuntime,'_structure',return_value=selected),self.assertRaises(PreparationError):BirdRuntime(e,'superhero','fake',receipt=receipt,connections=C())
        runtime.close()


    def test_changed_content_rejected_before_query_and_closed_context_rejected(self):
        runtime,e,selected,guards,C=self.make_runtime()
        changed=deepcopy(guards);changed[next(iter(changed))][1]='b'*64
        with patch.object(BirdRuntime,'_structure',return_value=selected),patch.object(BirdRuntime,'_content_guards',return_value=changed):
            with self.assertRaises(PreparationError):
                with runtime.verified_transaction():self.fail('Changed data reached query')
        runtime.close()
        with self.assertRaises(BirdFailure):runtime.load_catalog()

    def test_wrong_database_and_profile_scope_rejected(self):
        runtime,*_=self.make_runtime()
        self.assertFalse(runtime.execute('short_video_ops','SELECT 1').success)
        with self.assertRaises(PreparationError):runtime.profile_table('financial.account',['account_id'])
        with self.assertRaises(PreparationError):runtime.profile_table(runtime.catalog.tables[0]['id'],['not_a_column'])
        runtime.close()


class IndexIsolationTest(unittest.TestCase):
    def test_indexer_receives_only_authorized_metadata_and_profiles(self):
        from evaluation.bird.retrieval import raw_documents
        table={'id':'db.t','name':'t','database':'db','label':'t','fields':[{'name':'x','label':'X','type':'bigint',
            'description':'official description','value_description':'','role':'field'}]}
        profile={'x':{'samples':[['int','1']],'sample_truncated':[False]}}
        runtime=SimpleNamespace(database_id='db',catalog=SimpleNamespace(tables=[table]),profile_table=lambda *a:profile)
        seen=[]
        class Indexer:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def run(self,context,*args):
                seen.append(context)
                return [{'doc_id':'db.t.x','database_id':'db','table_id':'db.t','table_label':'t','field_name':'x',
                    'field_label':'X','field_type':'bigint','field_description':'official description','field_role':'field',
                    'aliases':[],'samples':[['int','1']],'profile':'profile','semantic_text':'only authorized metadata','relation_ids':[]}]
        with patch('evaluation.bird.supervisor.IsolatedAgent',Indexer):documents=raw_documents(runtime)
        self.assertEqual(set(seen[0]),{'mode','database_id','tables','profiles'})
        self.assertNotIn('gold_sql',json.dumps(seen));self.assertNotIn('question',seen[0])
        self.assertEqual(documents[0]['keyword_text'],documents[0]['semantic_text'])

    def test_cross_source_cached_documents_are_rejected_even_with_correct_id(self):
        from app.retrieval.store import FieldDocument
        from evaluation.bird.retrieval import validate_store
        raw={'doc_id':'db.t.x','database_id':'db','table_id':'db.t','table_label':'t','field_name':'x','field_label':'X',
            'field_type':'bigint','field_description':'description','field_role':'field','aliases':[],'samples':[],
            'profile':'profile','keyword_text':'text','semantic_text':'text','rerank_text':'text','relation_ids':[]}
        d=FieldDocument(**raw,dense_vector=[0.0]*1024,schema_version='v',content_hash=digest_json(raw))
        store=SimpleNamespace(embedding_source='text-embedding-v4',documents=[d])
        runtime=SimpleNamespace(database_id='db',catalog=SimpleNamespace(tables=[{'id':'db.t','fields':[{'name':'x'}]}]))
        validate_store(store,runtime)
        for field,value in [('database_id','other'),('content_hash','bad'),('dense_vector',[float('nan')]*1024)]:
            original=getattr(d,field);setattr(d,field,value)
            with self.subTest(field=field),self.assertRaises(BirdFailure):validate_store(store,runtime)
            setattr(d,field,original)


class ScorerBoundaryTest(unittest.TestCase):
    def run_case(self,*,cleanup_failure=False,skip_validation=False):
        from evaluation.bird.case_worker import execute
        from evaluation.bird.native import NativeResult
        from evaluation.bird.evidence import digest_bytes
        evidence=Evidence.load(DATA);public={'case_id':'BIRD-PG-0000','database_id':'superhero','dialect':'postgres','question':'Original English','evidence':'Official evidence'}
        gold={'case_id':public['case_id'],'database_id':'superhero','dialect':'postgres','gold_sql':'SELECT secret_gold_canary',
            'gold_sql_sha256':digest_bytes(b'SELECT secret_gold_canary')}
        seen=[]
        class Runtime:
            identity=SimpleNamespace(public=lambda:{'logical_database_id':'superhero'})
            def __init__(self,*a,**k):pass
            def execute_native(self,sql,*a,**k):
                if k.get('validate_only'):return {'valid':True}
                # Both native values must reach EX without a float conversion.
                return NativeResult(['value'],[(Decimal('1.00000000000000000001'),)],100)
            def close(self):
                if cleanup_failure:raise RuntimeError('private cleanup driver detail')
        class Agent:
            isolation={'filesystem':'unit fake, not OS verified'}
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def run(self,context,handler,*a):
                seen.append(context)
                handler('chat',{'system':'public system','user':'original public input','sql_round':1})
                if not skip_validation:handler('validate',{'sql':'SELECT predicted','sql_round':1})
                result=handler('sql',{'sql':'SELECT predicted','sql_round':1})
                self_result={'answered':result['success'],'status':'answered','sql':'SELECT predicted','trace':[]}
                return self_result
        class ModelsFake:
            def __init__(self,config,budget):self.config=config;self.budget=budget
            def chat(self,*a):self.budget.model_attempt('chat');return {'action':'query','sql':'SELECT predicted'}
        request={'mode':'live','gold':gold,'input':public,'data_root':str(DATA),'results_dir':str(BASE/'evaluation/results'),
            'credentials_file':'fake-private-path','receipt':{},'model_config_file':'fake.env','index_path':'fake-index.json',
            'code_sha256':__import__('evaluation.bird.manifest',fromlist=['code_binding']).code_binding()['sha256']}
        with patch('evaluation.bird.case_worker.Evidence.load',return_value=evidence),\
            patch('evaluation.bird.case_worker.load_credentials',return_value={'passwords':{'askdata_m2_ro_superhero':'fake'}}),\
            patch('evaluation.bird.case_worker.BirdRuntime',Runtime),patch('evaluation.bird.case_worker.IsolatedAgent',Agent),\
            patch('evaluation.bird.model.Models',ModelsFake),patch('evaluation.bird.model.ModelConfig.load',return_value=ModelConfig('fake')),\
            patch('evaluation.bird.retrieval.retrieve',return_value={'retrieval':{},'index_sha256':'index','graph':{},'schema_text':'authorized'}):
            report=execute(request)
        return report,seen

    def test_native_scoring_and_no_gold_crosses_agent_context(self):
        report,seen=self.run_case()
        self.assertTrue(report['ex_correct']);self.assertTrue(report['complete'])
        self.assertNotIn('secret_gold_canary',json.dumps(seen));self.assertEqual(report['new_model_request_count'],1)

    def test_skipping_validation_cannot_execute_sql(self):
        report,_=self.run_case(skip_validation=True)
        self.assertFalse(report['ex_correct']);self.assertEqual(report['status'],'unvalidated_sql_tool_call')

    def test_cleanup_failure_cannot_leave_a_passing_primary_score(self):
        report,_=self.run_case(cleanup_failure=True)
        self.assertFalse(report['ex_correct']);self.assertFalse(report['complete']);self.assertEqual(report['status'],'runtime_close_failed')
        self.assertNotIn('private cleanup',json.dumps(report))

class ReadinessGateTest(unittest.TestCase):
    def fixture(self):
        from evaluation.bird.manifest import source_binding
        from evaluation.bird.evidence import DATA_VERSION,ACCEPTED_VALIDATION_SHA
        e=Evidence.load(DATA);domains=[]
        for db,domain in e.manifest['query_domains'].items():
            typed={t['name']:t['target'] for t in e.validation['tables'] if t['database_id']==db}
            data=digest_json({'accepted_data_version':DATA_VERSION,'database_id':db,'tables':typed,'digest_policy':'m2_copy_native_typed_multiset_v1'})
            identity={'logical_database_id':db,'source_id':'bird_mini_dev_postgres_'+db,'backend':'postgresql','dialect':'postgres','prompt_dialect':'PostgreSQL',
                'physical_schema':'public','data_version':data,'catalog_version':'a'*64}
            domains.append({'database_id':db,'role':domain['query_role'],'source_identity':identity,
                'native_duplicate_names_preserved':True,'cross_domain_sql_denied':True,'cross_domain_profile_denied':True,
                'verification':{'role':domain['query_role'],'authorized_data_version':data,'authorized_catalog_version':'a'*64,
                    'accepted_validation_sha256':ACCEPTED_VALIDATION_SHA}})
        report={'stage':'M2 C domain runtime, profiles, budgets and isolation','run_status':'complete','errors':[],
            'runtime_verified':True,'target_data_verified':True,'agent_isolation_verified':True,'budget_enforcement_verified':True,
            'pools_closed':True,'source_binding':source_binding(e),'code_binding':{'sha256':'unit'},'domains':domains,
            'isolation':{'passed':True,'probes':{'read_denials':[True]*4,'network_socket_denied':True,'process_creation_denied':True,'secret_environment_absent':True}},
            'hard_process_timeout_probe':{'passed':True,'formal_case_timeout_seconds':600},'budget_counter_probes':[{'passed':True} for _ in range(7)]}
        return e,report

    def test_runtime_gate_rejects_wrong_roles_code_and_failed_isolation(self):
        from evaluation.bird.manifest import require_runtime_report
        e,good=self.fixture()
        with tempfile.TemporaryDirectory() as root,patch('evaluation.bird.manifest.code_binding',return_value={'sha256':'unit'}):
            path=Path(root)/'runtime.json';path.write_text(json.dumps(good));require_runtime_report(path,e)
            variants=[]
            r=deepcopy(good);r['domains'][0]['role']='askdata_readonly';variants.append(r)
            r=deepcopy(good);r['code_binding']={'sha256':'other'};variants.append(r)
            r=deepcopy(good);r['isolation']['probes']['read_denials'][0]=False;variants.append(r)
            for row in variants:
                path.write_text(json.dumps(row))
                with self.assertRaises(PreparationError):require_runtime_report(path,e)

    def test_gold_gate_requires_all_110_complete_cases_and_same_actual_sql(self):
        from evaluation.bird.manifest import require_gold_report,source_binding
        from scripts.m2_b_common import digest_file
        e,runtime=self.fixture();ids={d['database_id']:d['source_identity'] for d in runtime['domains']}
        cases=[{'case_id':g['case_id'],'database_id':g['database_id'],'mode':'gold','gold_sql_sha256':g['gold_sql_sha256'],
            'status':'gold_ready','complete':True,'errors':[],'source_identity':ids[g['database_id']],
            'runtime_closed':True,'new_model_request_count':0,'result':{'complete':True,'within_row_limit':True,'within_payload_limit':True,'native_hashable':True}} for g in scorer_gold().values()]
        with tempfile.TemporaryDirectory() as root,patch('evaluation.bird.manifest.code_binding',return_value={'sha256':'unit'}):
            rt=Path(root)/'runtime.json';rt.write_text(json.dumps(runtime));path=Path(root)/'gold.json'
            good={'stage':'M2 C BIRD external benchmark','mode':'gold','run_status':'complete','gold110_ready':True,'errors':[],
                'source_binding':source_binding(e),'code_binding':{'sha256':'unit'},'runtime_report_sha256':digest_file(rt),'cases':cases}
            path.write_text(json.dumps(good));require_gold_report(path,e,rt)
            bad=deepcopy(good);bad['cases']=bad['cases'][:-1];path.write_text(json.dumps(bad))
            with self.assertRaises(PreparationError):require_gold_report(path,e,rt)
            bad=deepcopy(good);bad['cases'][0]['gold_sql_sha256']='b'*64;path.write_text(json.dumps(bad))
            with self.assertRaises(PreparationError):require_gold_report(path,e,rt)


class SummaryTest(unittest.TestCase):
    def test_failed_cases_and_clarifications_remain_in_primary_and_group_denominators(self):
        from evaluation.bird.metrics import summarize
        cases=[{'case_id':'a','database_id':'db','status':'scored','complete':True,'ex_correct':True,'errors':[],'case_wall_seconds':1},
            {'case_id':'b','database_id':'db','status':'clarification','complete':False,'ex_correct':False,'case_wall_seconds':3},
            {'case_id':'c','database_id':'db','status':'result_row_limit','complete':False,'ex_correct':False,'case_wall_seconds':2}]
        metadata={k:{'difficulty':'simple'} for k in ('a','b','c')}
        out=summarize(cases,metadata,'live')
        self.assertEqual(out['primary_denominator'],3);self.assertEqual(out['primary_ex'],1/3)
        self.assertEqual(out['by_difficulty']['simple']['case_count'],3);self.assertEqual(out['by_database']['db']['case_count'],3)
        self.assertEqual(out['ex_given_complete_results'],1);self.assertEqual(out['latency_seconds']['p50'],2)


@unittest.skipUnless(sys.platform=='linux','Linux kernel isolation is verified on the server')
class LinuxIsolationTest(unittest.TestCase):
    def test_real_indexer_builds_without_project_file_access(self):
        from evaluation.bird.supervisor import IsolatedAgent
        field={'name':'x','label':'X','type':'bigint','description':'official','value_description':'','role':'field'}
        context={'mode':'index','database_id':'db','tables':[{'id':'db.t','name':'t','database':'db','label':'t','fields':[field]}],
            'profiles':{'db.t':{'x':{'row_count':1,'null_count':0,'samples':[['int','1']],'sample_truncated':[False]}}}}
        with IsolatedAgent() as indexer:result=indexer.run(context,lambda *a:self.fail('Unexpected indexer RPC'),time.monotonic()+10)
        self.assertEqual(result[0]['doc_id'],'db.t.x');self.assertIn('official',result[0]['semantic_text'])
    def test_real_filesystem_network_process_and_env_isolation(self):
        from evaluation.bird.supervisor import isolation_probe
        with tempfile.TemporaryDirectory() as root:
            private=Path(root)/'gold_private';private.write_text('do-not-read')
            self.assertTrue(isolation_probe([private])['passed'])
    def test_hard_supervisor_timeout(self):
        from evaluation.bird.supervisor import run_case_process
        started=time.monotonic()
        with self.assertRaises(BirdFailure) as cm:run_case_process({'mode':'watchdog_probe'},seconds=.5)
        self.assertEqual(cm.exception.category,'case_wall_timeout');self.assertLess(time.monotonic()-started,7)


if __name__=='__main__':unittest.main()
