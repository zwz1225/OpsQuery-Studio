"""Development observation boundaries: source scope, secrecy, unchanged RPCs and no Gold execution."""
from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from evaluation.bird.budgets import BirdFailure
from evaluation.bird.diagnostics import Recorder, sql_record, text_record, pg_error_fields, encoded, SQL_BYTES, GRAPH_BYTES, TOTAL_BYTES
from evaluation.bird.model import ModelConfig
from evaluation.bird.native import NativeResult
from evaluation.bird.runtime import fault
from scripts.m2_b_common import BASE, PreparationError, digest_json


class PrivatePgError(Exception):
    sqlstate='42703'
    diag=SimpleNamespace(message_primary='column "missing" does not exist',statement_position='8',
        schema_name=None,table_name=None,column_name=None,
        message_detail='PRIVATE_DETAIL',message_hint='PRIVATE_HINT',context='PRIVATE_CONTEXT',internal_query='PRIVATE_SQL')
    def __str__(self):raise AssertionError('Never stringify a driver error')


class BoundedDiagnosticsTest(unittest.TestCase):
    def test_long_multibyte_sql_keeps_actual_hash_and_valid_utf8(self):
        sql='SELECT '+('汉'*10000)
        record=sql_record(sql)
        self.assertEqual(record['original_sha256'],hashlib.sha256(sql.encode()).hexdigest())
        self.assertTrue(record['truncated']);self.assertLessEqual(len(record['text'].encode()),SQL_BYTES)
        self.assertEqual(record['original_utf8_bytes'],len(sql.encode()))

    def test_credentials_redacted_before_truncation(self):
        secret='this-is-a-private-key'
        text="SELECT '"+secret+"', 'postgresql://u:p@host/db', 'PG_PASSWORD=hidden', 'Bearer abc.def.ghi'"
        record=sql_record(text,(secret,))
        for value in (secret,'u:p@host','hidden','abc.def.ghi'):self.assertNotIn(value,record['text'])
        self.assertTrue(record['redacted'])

    def test_no_driver_string_or_detail_hint_internal_query(self):
        error=PrivatePgError();failure=fault(error)
        self.assertEqual(failure.public(),{'category':'undefined_column','sqlstate':'42703'})
        recorder=Recorder();recorder.operation('validate',1,'SELECT missing',valid=False,error=failure)
        value=recorder.public()['attempts'][0]
        self.assertIn('does not exist',value['validation_reason']['message_primary'])
        for name in ('PRIVATE_DETAIL','PRIVATE_HINT','PRIVATE_CONTEXT','PRIVATE_SQL'):self.assertNotIn(name,json.dumps(value))

    def test_value_errors_do_not_record_value_message(self):
        error=PrivatePgError();error.sqlstate='22P02'
        detail=pg_error_fields(error)
        self.assertNotIn('message_primary',detail);self.assertEqual(detail['sqlstate'],'22P02')

    def test_late_known_secret_redacted_in_pg_primary(self):
        error=PrivatePgError();error.diag=SimpleNamespace(message_primary='column "private-api-key" does not exist')
        recorder=Recorder(('private-api-key',));recorder.operation('validate',1,'SELECT x',valid=False,error=fault(error))
        self.assertNotIn('private-api-key',json.dumps(recorder.public()))

    def test_clarification_reason_is_explicit_and_bounded(self):
        recorder=Recorder(('private-key',));decision={'action':'clarify','reason':'private-key '+('缺少字段'*2000)}
        original=deepcopy(decision);recorder.model_decision(decision,1)
        result=recorder.public();reason=result['clarification_reason']
        self.assertTrue(reason['provided']);self.assertTrue(reason['truncated']);self.assertTrue(reason['redacted'])
        self.assertLessEqual(len(reason['text'].encode()),2048);self.assertEqual(decision,original)

    def test_missing_reason_is_unknown_not_invented(self):
        recorder=Recorder();recorder.model_decision({'action':'clarify'},1)
        self.assertFalse(recorder.public()['clarification_reason']['provided'])
        self.assertIsNone(recorder.public()['clarification_reason']['text'])

    def test_graph_and_total_bound_are_explicit(self):
        graph={'fields':[{'id':str(i),'description':'z'*2000} for i in range(256)]}
        recorder=Recorder();recorder.set_retrieval({'schema_graph':graph,'candidates':[]})
        result=recorder.public();snapshot=result['retrieval']['schema_graph']
        self.assertFalse(snapshot['complete']);self.assertIsNone(snapshot['value']);self.assertEqual(snapshot['omission_reason'],'graph_byte_limit')
        for _ in range(100):recorder.model_decision({'action':'query','sql':'x'*100000},1)
        result=recorder.public();self.assertLessEqual(len(encoded(result)),TOTAL_BYTES)
        self.assertGreater(result['omitted_events'],0);self.assertLessEqual(len(result['attempts']),21)

    def test_metadata_truncation_is_not_claimed_complete(self):
        recorder=Recorder();recorder.set_retrieval({'schema_graph':{'description':'x'*9000}})
        graph=recorder.public()['retrieval']['schema_graph']
        self.assertFalse(graph['complete']);self.assertEqual(graph['omission_reason'],'metadata_redacted_or_truncated')


class RetrievalDiagnosticsTest(unittest.TestCase):
    def test_real_retrieval_records_cutoffs_and_fk_graph_without_changing_selection(self):
        from evaluation.bird.retrieval import retrieve
        from app.retrieval.store import FieldDocument
        tables=[];documents=[]
        for table_name in ('a','b'):
            names=['id','a_id']+[f'f{i}' for i in range(23)]
            fields=[{'name':n,'label':n,'type':'bigint','description':'official '+n,'role':'field'} for n in names]
            tables.append({'id':'db.'+table_name,'name':'public.'+table_name,'database':'db','label':table_name,'description':'official', 'fields':fields})
            for f in fields:
                raw={'doc_id':'db.'+table_name+'.'+f['name'],'database_id':'db','table_id':'db.'+table_name,
                    'table_label':table_name,'field_name':f['name'],'field_label':f['label'],'field_type':'bigint',
                    'field_description':f['description'],'field_role':'field','aliases':[],'samples':[],'profile':'',
                    'keyword_text':'x','semantic_text':'x','rerank_text':'db.'+table_name+'.'+f['name'],'relation_ids':[]}
                documents.append(FieldDocument(**raw,dense_vector=[0.0]*1024,schema_version='unit',content_hash=digest_json(raw)))
        relation={'left_table':'db.a','left_field':'id','right_table':'db.b','right_field':'a_id','description':'fk'}
        identity={'logical_database_id':'db','backend':'postgresql','dialect':'postgres','prompt_dialect':'PostgreSQL','physical_schema':'public'}
        runtime=SimpleNamespace(database_id='db',domain={'query_role':'ro'},identity=SimpleNamespace(public=lambda:identity),
            catalog=SimpleNamespace(tables=tables,relations=[relation]))
        # Interleave fields from both tables, leaving join keys outside top rerank.
        sequence=[2,27]+[i for i in range(50) if i not in (2,27)]
        bm25=[(i,1/(rank+1)) for rank,i in enumerate(sequence[:30])]
        dense=[(i,.9-rank*.01) for rank,i in enumerate(sequence[15:45])]
        class Store:
            embedding_source='text-embedding-v4'
            def __init__(self,*a):self.documents=documents
            def load(self,*a,**k):return True
            def bm25_search(self,*a):return bm25
            def dense_search(self,*a):return dense
        captured=[]
        class Models:
            config=ModelConfig('fake')
            def embed(self,texts):captured.extend(texts);return [[0.0]*1024]
            def rerank(self,text,texts):
                return {i:(.4 if i==1 or name in ('db.a.id','db.b.a_id') else
                           .99 if name in ('db.a.f0','db.b.f0') else .9-i*.001)
                        for i,name in enumerate(texts) if i!=2}
        public={'case_id':'BIRD-PG-0000','database_id':'db','dialect':'postgres','question':'original question','evidence':'official evidence'}
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'index.json';path.write_text('{}')
            with patch('evaluation.bird.retrieval.LocalSchemaStore',Store):result=retrieve(runtime,Models(),path,public)
        self.assertEqual(captured,['original question\nofficial evidence'])
        diagnostics=result['_report_diagnostics'];reasons={r['selection_reason'] for r in diagnostics['candidates']}
        self.assertEqual(reasons,{'selected','below_threshold','rerank_not_returned','beyond_top20'})
        self.assertEqual(len(diagnostics['candidates']),40);self.assertEqual(result['retrieval']['selected_count'],20)
        self.assertEqual([r['field_id'] for r in sorted((r for r in diagnostics['candidates'] if r['selected']),key=lambda r:r['rerank_rank'])],result['retrieval']['selected_field_ids'])
        self.assertEqual(diagnostics['schema_graph'],result['graph'])
        self.assertTrue(diagnostics['added_relation_key_field_ids'])
        self.assertTrue(set(diagnostics['added_relation_key_field_ids'])<=set(diagnostics['relation_key_field_ids']))
        self.assertNotIn('dense_vector',json.dumps(diagnostics));self.assertNotIn('gold_sql',json.dumps(diagnostics))


class BrokerObservationTest(unittest.TestCase):
    def run_case(self,mode='live',clarify=False):
        from evaluation.bird.case_worker import execute
        sqls=[];contexts=[];feedback=[];responses=[]
        public={'case_id':'BIRD-PG-0000','database_id':'db','dialect':'postgres','question':'question','evidence':'evidence'}
        gold={'case_id':'BIRD-PG-0000','database_id':'db','dialect':'postgres','gold_sql':'SELECT GOLD_PRIVATE',
            'gold_sql_sha256':hashlib.sha256(b'SELECT GOLD_PRIVATE').hexdigest()}
        class Runtime:
            identity=SimpleNamespace(public=lambda:{'logical_database_id':'db'})
            def __init__(self,*a,**k):pass
            def execute_native(self,sql,*a,**k):
                sqls.append(sql)
                if sql=='SELECT missing':raise fault(PrivatePgError())
                if k.get('validate_only'):return {'valid':True}
                return NativeResult(['x'],[(Decimal('1.00000000000000000001'),)],64)
            def close(self):pass
        class Models:
            def __init__(self,config,budget):self.budget=budget
            def chat(self,*a):
                self.budget.model_attempt('chat')
                decision={'action':'query','sql':'SELECT missing'} if not responses else (
                    {'action':'clarify','reason':'Need the missing field definition'} if clarify else {'action':'query','sql':'SELECT good'})
                responses.append(deepcopy(decision));return decision
        class Agent:
            isolation={'unit':'fake'}
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def run(self,context,handler,*a):
                contexts.append(deepcopy(context))
                first=handler('chat',{'system':'same system','user':'same user','sql_round':1})
                feedback.append(handler('validate',{'sql':first['sql'],'sql_round':1}))
                second=handler('chat',{'system':'same system','user':'same user','sql_round':1})
                if second['action']=='clarify':return {'status':'clarification','answered':False,'trace':[]}
                feedback.append(handler('validate',{'sql':second['sql'],'sql_round':1}))
                handler('sql',{'sql':second['sql'],'sql_round':1})
                return {'status':'answered','answered':True,'sql':second['sql'],'trace':[]}
        evidence=SimpleNamespace(domain=lambda db:{'query_role':'ro'},validation={'initialization_id':'unit'},manifest={})
        schema={'retrieval':{},'index_sha256':'index','graph':{'fields':[]},'schema_text':'unchanged schema',
                '_report_diagnostics':{'schema_graph':{'fields':[]},'candidates':[{'field_id':'REPORT_ONLY_CANARY'}]}}
        request={'mode':mode,'input':public,'data_root':'.','results_dir':'.','credentials_file':'private',
            'receipt':{},'index_path':'index','code_sha256':'unit','model_config_private':{'api_key':'PRIVATE_API_KEY'}}
        if mode=='live':request['gold']=gold
        with patch('evaluation.bird.case_worker.code_binding',return_value={'sha256':'unit'}),\
            patch('evaluation.bird.case_worker.Evidence.load',return_value=evidence),\
            patch('evaluation.bird.case_worker.load_credentials',return_value={'passwords':{'ro':'PRIVATE_PG_PASSWORD'}}),\
            patch('evaluation.bird.case_worker.BirdRuntime',Runtime),patch('evaluation.bird.case_worker.IsolatedAgent',Agent),\
            patch('evaluation.bird.model.Models',Models),patch('evaluation.bird.retrieval.retrieve',return_value=schema):
            report=execute(request)
        return report,contexts,feedback,sqls

    def test_report_data_stays_private_while_repair_feedback_is_bounded(self):
        report,contexts,feedback,sqls=self.run_case()
        self.assertTrue(report['ex_correct']);self.assertTrue(report['complete'])
        self.assertEqual(feedback[0]['error'],{'category':'undefined_column','sqlstate':'42703'})
        self.assertEqual(feedback[0]['repair_feedback']['policy'],'bird_authorized_sql_repair_v2')
        self.assertEqual(feedback[1],{'valid':True})
        self.assertEqual(set(contexts[0]['schema']),{'retrieval','index_sha256','graph','schema_text'})
        for private in ('GOLD_PRIVATE','PRIVATE_API_KEY','PRIVATE_PG_PASSWORD','REPORT_ONLY_CANARY','development_diagnostics'):
            self.assertNotIn(private,json.dumps(contexts))
        attempts=report['development_diagnostics']['attempts']
        self.assertEqual([r['kind'] for r in attempts],['model_decision','validate','model_decision','validate','execute'])
        self.assertEqual(attempts[1]['sql']['text'],'SELECT missing')
        self.assertEqual(attempts[1]['validation_reason']['condition'],'undefined_column')
        self.assertIn('SELECT GOLD_PRIVATE',sqls)

    def test_diagnostic_mode_has_no_gold_request_execution_or_ex(self):
        report,contexts,feedback,sqls=self.run_case(mode='diagnostic')
        self.assertEqual(report['status'],'diagnostic_answered');self.assertIsNone(report['ex_correct'])
        self.assertIsNone(report['gold_sql_sha256']);self.assertTrue(report['complete'])
        self.assertNotIn('SELECT GOLD_PRIVATE',sqls)

    def test_clarification_retains_model_explanation_and_failed_attempt(self):
        report,contexts,feedback,sqls=self.run_case(mode='diagnostic',clarify=True)
        self.assertEqual(report['status'],'clarification');self.assertFalse(report['complete'])
        self.assertEqual(report['development_diagnostics']['clarification_reason']['text'],'Need the missing field definition')
        self.assertEqual(report['development_diagnostics']['attempts'][1]['sql']['text'],'SELECT missing')
        self.assertEqual(report['budget']['sql_tool_calls'],0)


class DiagnosticSelectionTest(unittest.TestCase):
    def test_default14_are_development_only_and_unique(self):
        from evaluation.bird.diagnostic_runner import select_development,DEFAULT_CASES
        rows=select_development(DEFAULT_CASES)
        self.assertEqual(len(rows),14);self.assertEqual(len({r['case_id'] for r in rows}),14)
        self.assertEqual(len({r['database_id'] for r in rows}),8)
    def test_holdout_unknown_duplicate_empty_are_refused(self):
        from evaluation.bird.diagnostic_runner import select_development
        for ids in (['BIRD-PG-1028'],['UNKNOWN'],['BIRD-PG-0050']*2,[],[{}]):
            with self.subTest(ids=ids),tempfile.TemporaryDirectory() as root:
                path=Path(root)/'cases.json';path.write_text(json.dumps({'case_ids':ids}))
                with self.assertRaises(PreparationError):select_development(path)
    def test_modified_prerequisite_bytes_refused(self):
        from evaluation.bird.diagnostic_runner import prerequisites
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'baseline.json';path.write_text('{}')
            with self.assertRaises(PreparationError):prerequisites(path,path,path,None)

    def test_formal_gate_still_rejects_old_code_evidence(self):
        from evaluation.bird.evidence import Evidence
        from evaluation.bird.manifest import require_runtime_report
        import sys
        data=Path('E:/PythonLearn/datasets/bird_mini_dev') if sys.platform=='win32' else BASE/'data/external/bird_mini_dev'
        with self.assertRaises(PreparationError):
            require_runtime_report(BASE/'evaluation/results/m2_c_bird_runtime_server.json',Evidence.load(data))


class DiagnosticRunnerTest(unittest.TestCase):
    def test_parent_sends_no_gold_or_historical_feedback_and_never_reports_formal_ex(self,coverage=False):
        from evaluation.bird import diagnostic_runner as runner
        import sys
        requests=[]
        class Registry:
            def __init__(self,*a):self._runtimes={}
            def __enter__(self):return self
            def __exit__(self,*a):self.close()
            def get(self,db):
                runtime=SimpleNamespace(database_id=db,connections=SimpleNamespace(closed=False),
                    receipt=lambda:{'database_id':db,'typed_tables':{'private':'trusted only'},'catalog_content':{},'content_guards':{}})
                self._runtimes[db]=runtime;return runtime
            def close(self):
                for r in self._runtimes.values():r.connections.closed=True
        def worker(request,seconds):
            if request['mode']=='watchdog_probe':raise BirdFailure('case_wall_timeout')
            requests.append(deepcopy(request));public=request['input']
            return {'case_id':public['case_id'],'database_id':public['database_id'],'mode':'diagnostic',
                'status':'clarification','complete':False,'ex_correct':None,'new_model_request_count':3,
                'runtime_closed':True,'development_diagnostics':{'report_only':True}}
        baseline={'code_binding':{'sha256':'old'},'cases':[{'case_id':'BIRD-PG-0050','status':'validation_failed','ex_correct':False}]}
        evidence=SimpleNamespace(manifest={'question_relative_path':'questions.json'},protocol={'protocol_id':'unit'})
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);cases=root/'cases.json';cases.write_text(json.dumps({'case_ids':['BIRD-PG-0050']}))
            old=root/'old.json';old.write_text('{}');output=root/'diagnostic.json'
            args=['diag','--case-list',str(cases),'--output',str(output),'--baseline-report',str(old),
                '--runtime-report',str(old),'--gold-report',str(old),'--index-root',str(root/'indexes')]
            if coverage:args.append('--schema-coverage')
            with patch.object(sys,'argv',args),patch.object(runner,'live_dependencies'),\
                patch.object(runner.Evidence,'load',return_value=evidence),patch.object(runner,'prerequisites',return_value=baseline),\
                patch.object(runner.ModelConfig,'load',return_value=ModelConfig('PRIVATE_API_KEY')),\
                patch.object(runner,'source_binding',return_value={'unit':'source'}),patch.object(runner,'code_binding',return_value={'sha256':'unit'}),\
                patch.object(runner,'budget_checks',return_value=[]),patch.object(runner,'isolation_probe',return_value={'passed':True}),\
                patch.object(runner,'run_case_process',side_effect=worker),patch.object(runner,'BirdRegistry',Registry),\
                patch.object(runner,'build_index',return_value={'path':'index','model_usage':None}):
                with self.assertRaises(SystemExit) as result:runner.main()
                self.assertEqual(result.exception.code,0)
            report=json.loads(output.read_bytes())
        self.assertEqual(len(requests),1)
        self.assertNotIn('gold',requests[0]);self.assertNotIn('historical_baseline',requests[0])
        self.assertNotIn('ex_correct',requests[0]);self.assertIsNone(report['summary']['primary_ex'])
        self.assertFalse(report['formal_benchmark']);self.assertFalse(report['gold_executed']);self.assertFalse(report['holdout_live_allowed'])
        self.assertNotIn('PRIVATE_API_KEY',json.dumps(report))
        self.assertEqual(report['cases'][0]['historical_baseline']['status'],'validation_failed')
        self.assertIs(requests[0].get('schema_coverage_enabled',False),coverage)
        self.assertIs(report['schema_selection_policy']['coverage_enabled'],coverage)

    def test_coverage_option_reaches_worker_and_is_explicit_in_report(self):
        self.test_parent_sends_no_gold_or_historical_feedback_and_never_reports_formal_ex(coverage=True)


if __name__=='__main__':unittest.main()
