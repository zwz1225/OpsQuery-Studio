"""SQL repair feedback, authorized fields, position origins and bounded real Agent loop."""
from contextlib import contextmanager,nullcontext
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from evaluation.bird.budgets import BirdFailure
from evaluation.bird.diagnostics import encoded
from evaluation.bird.native import NativeResult
from evaluation.bird.repair import RepairSession,fingerprint,position_record,FEEDBACK_BYTES
from evaluation.bird.runtime import BirdRuntime,fault
from scripts.m2_b_common import BASE


def failure(state='42703',message='column t.missing does not exist',position='30',prefix='EXPLAIN (FORMAT JSON) '):
    error=BirdFailure('undefined_column' if state=='42703' else 'sql_error',state)
    error._report_diagnostic={'sqlstate':state,'condition':'undefined_column' if state=='42703' else 'invalid_column_reference',
        'message_primary':message,'statement_position':position}
    if prefix is not None:error._repair_statement_prefix=prefix
    return error


def runtime():
    tables=[{'id':'db.t','name':'t','database':'db','fields':[{'name':'id','type':'bigint','label':'Identifier','description':'Identifier'},
        {'name':'actual_name','type':'text','label':'Name','description':'Full name'}]},
        {'id':'db.other','name':'other','database':'db','fields':[{'name':'unrelated','type':'text'}]},
        {'id':'foreign.private','name':'private','database':'foreign','fields':[{'name':'private_secret','type':'text'}]}]
    return SimpleNamespace(database_id='db',identity=SimpleNamespace(public=lambda:{'logical_database_id':'db','catalog_version':'unit'}),
        catalog=SimpleNamespace(tables=tables))


class RepairUnitTest(unittest.TestCase):
    def test_explain_position_uses_character_offsets_with_multiline_unicode(self):
        sql="SELECT '中文',\n t.missing FROM t";offset=sql.index('t.missing')+1
        error=failure(position=str(offset+22))
        record=position_record(error,sql)
        self.assertEqual(record['sql_position'],offset);self.assertEqual(record['line'],2);self.assertEqual(record['column'],2)
        self.assertEqual(record['origin'],'explain');self.assertTrue(record['available'])

    def test_original_sql_position_and_unknown_origin(self):
        sql='SELECT t.missing FROM t'
        self.assertEqual(position_record(failure(position='8',prefix=''),sql)['sql_position'],8)
        self.assertFalse(position_record(failure(position='8',prefix=None),sql)['available'])
        self.assertFalse(position_record(failure(position='999999999999999'),sql)['available'])

    def test_feedback_names_are_bound_to_referenced_authorized_tables(self):
        session=RepairSession(runtime());value=session.feedback(failure(),'SELECT t.missing FROM t')
        self.assertEqual(value['unresolved_column'],{'name':'missing','table_alias':'t'})
        self.assertEqual({h['field_name'] for h in value['authorized_fields']},{'id','actual_name'})
        for h in value['authorized_fields']:self.assertEqual(h['table_id'],'db.t')
        self.assertNotIn('private_secret',json.dumps(value));self.assertNotIn('unrelated',json.dumps(value['authorized_fields']))

    def test_cross_schema_and_foreign_catalog_hints_are_not_exposed(self):
        session=RepairSession(runtime())
        for sql in ('SELECT missing FROM foreign.private','SELECT missing FROM private','SELECT missing FROM otherdb.public.t'):
            with self.subTest(sql=sql):self.assertEqual(session.feedback(failure(),sql)['authorized_fields'],[])

    def test_cte_and_quoted_identifiers_use_actual_catalog_ownership(self):
        session=RepairSession(runtime())
        value=session.feedback(failure(),'WITH q AS (SELECT a.id FROM public.t a) SELECT q.missing FROM q')
        self.assertTrue(value['authorized_fields']);self.assertTrue(all(h['table_id']=='db.t' for h in value['authorized_fields']))
        self.assertTrue(all(h['sql_reference'].startswith('"a".') for h in value['authorized_fields']))

    def test_known_credentials_and_connection_details_are_redacted(self):
        secret='private-key-123';sql="SELECT '"+secret+"', t.missing FROM t"
        error=failure(message='column '+secret+' does not exist; PG_PASSWORD=hidden postgresql://u:p@host/db')
        value=RepairSession(runtime(),(secret,)).feedback(error,sql)
        text=json.dumps(value)
        for item in (secret,'hidden','u:p@host'):self.assertNotIn(item,text)
        self.assertEqual(value['failed_sql']['original_sha256'],hashlib.sha256(sql.encode()).hexdigest())

    def test_feedback_cap_and_no_detail_or_hint_forwarding(self):
        sql='SELECT '+('x'*90000)+' FROM t';error=failure(message='x'*10000)
        error._report_diagnostic.update(message_detail='PRIVATE_DETAIL',message_hint='PRIVATE_HINT',context='PRIVATE_CONTEXT')
        value=RepairSession(runtime()).feedback(error,sql)
        self.assertLessEqual(len(encoded(value)),FEEDBACK_BYTES)
        self.assertTrue(value['failed_sql']['truncated']);self.assertTrue(value['server_reason']['truncated'])
        self.assertNotIn('PRIVATE_',json.dumps(value))

    def test_fingerprint_ignores_formatting_but_preserves_literal_and_identifier_case(self):
        self.assertEqual(fingerprint('SELECT t.id FROM t'),fingerprint(' select T.ID /* comment */ from T '))
        self.assertNotEqual(fingerprint("SELECT 'Strength'"),fingerprint("SELECT 'strength'"))
        self.assertNotEqual(fingerprint('SELECT "A" FROM t'),fingerprint('SELECT "a" FROM t'))
        self.assertNotEqual(fingerprint('SELECT id FROM t ORDER BY id DESC'),fingerprint('SELECT id FROM t ORDER BY id DESC NULLS LAST'))

    def test_duplicate_is_terminal_and_does_not_reuse_wrong_layout_position(self):
        session=RepairSession(runtime());sql='SELECT t.missing FROM t';session.remember(failure(),sql)
        error,value=session.repeated('select T.MISSING\nfrom T')
        self.assertEqual(error.category,'repeated_invalid_sql');self.assertFalse(value['retryable'])
        self.assertTrue(value['duplicate_failed_sql']);self.assertFalse(value['position']['available'])
        self.assertIsNone(session.repeated('SELECT t.actual_name FROM t'))

    def test_transient_errors_not_memoized_and_history_is_per_case(self):
        sql='SELECT id FROM t';session=RepairSession(runtime())
        session.remember(BirdFailure('sql_timeout','57014'),sql);self.assertIsNone(session.repeated(sql))
        session.remember(failure(),sql);self.assertIsNotNone(session.repeated(sql))
        self.assertIsNone(RepairSession(runtime()).repeated(sql))

    def test_repeated_readonly_policy_denial_is_terminal_without_relaxing_guard(self):
        session=RepairSession(runtime());sql='DELETE FROM t'
        session.remember(BirdFailure('readonly_query_required'),sql)
        error,value=session.repeated(sql)
        self.assertEqual(error.category,'repeated_invalid_sql');self.assertFalse(value['retryable'])

    def test_oversized_invalid_sql_is_not_parsed_and_feedback_still_bounded(self):
        value=RepairSession(runtime()).feedback(BirdFailure('invalid_sql_input'),'SELECT '+('x'*200000))
        self.assertEqual(value['authorized_fields'],[]);self.assertLessEqual(len(encoded(value)),FEEDBACK_BYTES)

    def test_same_layout_repeat_retains_correct_normalized_position(self):
        session=RepairSession(runtime());sql='SELECT t.missing FROM t';session.remember(failure(),sql)
        self.assertEqual(session.repeated(sql)[1]['position']['sql_position'],8)

    def test_distinct_hint_preserves_final_output_contract(self):
        value=RepairSession(runtime()).feedback(failure('42P10','for SELECT DISTINCT, ORDER BY expressions must appear in select list'),
            'SELECT DISTINCT id FROM t ORDER BY actual_name')
        self.assertIn('preserving the requested final output',' '.join(value['guidance']))

    def test_runtime_marks_real_explain_origin_without_leaking_driver_repr(self):
        class DriverError(Exception):
            sqlstate='42703'
            diag=SimpleNamespace(message_primary='column t.missing does not exist',statement_position='30')
            def __str__(self):raise AssertionError('No driver string')
        class Connection:
            def execute(self,sql):raise DriverError()
        @contextmanager
        def transaction():yield Connection()
        r=object.__new__(BirdRuntime);r.require_open=lambda:None;r.names={'t'};r.verified_transaction=transaction
        with patch('evaluation.bird.runtime.hard_deadline',lambda *a:nullcontext()):
            with self.assertRaises(BirdFailure) as result:r.execute_native('SELECT t.missing FROM t',validate_only=True)
        self.assertEqual(position_record(result.exception,'SELECT t.missing FROM t')['sql_position'],8)


class RecordedDevelopmentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from evaluation.bird.evidence import Evidence,public_cases
        from scripts.m2_b_structure import expectations
        data=Path('E:/PythonLearn/datasets/bird_mini_dev') if sys.platform=='win32' else BASE/'data/external/bird_mini_dev'
        e=Evidence.load(data);cls.e=e;cls.expected=expectations(e.manifest)
        cls.public={c['case_id']:c for c in public_cases('development80')}
        cls.cases={c['case_id']:c for c in json.loads((BASE/'evaluation/results/m2_development_diagnostics14_server.json').read_bytes())['cases']}

    def context(self,cid):
        c=self.cases[cid];db=c['database_id'];x=object.__new__(BirdRuntime)
        x.evidence=self.e;x.database_id=db;x.domain=self.e.domain(db);x.tables=self.e.tables(db);x.names=set(x.domain['tables']);x.expected=self.expected
        x._descriptions,x.description_diagnostic=self.e.descriptions(db)
        x.catalog=x._catalog({t['name']:self.e.validation['structure']['verified_structure']['columns'][t['name']] for t in x.tables})
        x.identity=SimpleNamespace(public=lambda:c['source_identity'])
        return x

    def feedback(self,cid):
        c=self.cases[cid];v=next(v for v in c['development_diagnostics']['attempts'] if v['kind']=='validate')
        error=failure(v['error']['sqlstate']);error._report_diagnostic=v['validation_reason']
        session=RepairSession(self.context(cid),public_input=self.public[cid]);return session,v,session.feedback(error,v['sql']['text'])

    def test_0050_real_field_ownership_and_position(self):
        session,event,value=self.feedback('BIRD-PG-0050')
        pairs={(h['table_name'],h['field_name']) for h in value['authorized_fields']}
        self.assertIn(('satscores','sname'),pairs);self.assertIn(('schools','school'),pairs)
        self.assertNotIn(('schools','name'),pairs);self.assertEqual(value['position']['sql_position'],8)
        self.assertEqual(value['source_identity'],self.cases['BIRD-PG-0050']['source_identity'])

    def test_0095_exact_repeated_statement_is_detected(self):
        session,event,value=self.feedback('BIRD-PG-0095')
        error=failure('42P10');error._report_diagnostic=event['validation_reason'];session.remember(error,event['sql']['text'])
        repeat=session.repeated(event['sql']['text'])
        self.assertFalse(repeat[1]['retryable']);self.assertEqual(value['position']['sql_position'],170)
        self.assertIn('SELECT DISTINCT',value['server_reason']['text'])

    def test_1473_date_and_customer_join_key_are_authorized_not_invented(self):
        session,event,value=self.feedback('BIRD-PG-1473')
        pairs={(h['table_name'],h['field_name']) for h in value['authorized_fields']}
        self.assertIn(('yearmonth','date'),pairs);self.assertIn(('customers','customerid'),pairs)
        self.assertNotIn(('yearmonth','yearmonth'),pairs);self.assertEqual(value['position']['sql_position'],169)


class AgentBudgetIntegrationTest(unittest.TestCase):
    def run_agent(self,decisions,policy_failure=False,validate_sources=False):
        from evaluation.bird.case_worker import execute
        # Import only the stdlib-only answer loop; no sandbox/network/process is launched.
        with patch.dict(sys.modules,{'resource':SimpleNamespace()}):agent=importlib.import_module('evaluation.bird.isolated_agent')
        database_calls=[];prompts=[];left=deepcopy(decisions)
        class Runtime:
            identity=runtime().identity;catalog=runtime().catalog
            def __init__(self,*a,**k):pass
            def execute_native(self,sql,*a,**k):
                database_calls.append((sql,k.get('validate_only',False)))
                if validate_sources:
                    from evaluation.bird.sql import validate_sql
                    validate_sql(sql,{'t'})
                if policy_failure:raise BirdFailure('sql_source_denied')
                if 'missing' in sql:raise failure()
                if k.get('validate_only'):return {'valid':True}
                return NativeResult(['id'],[(1,)],32)
            def close(self):pass
        class Models:
            def __init__(self,config,budget):self.budget=budget
            def chat(self,system,user):
                self.budget.model_attempt('chat',prompt=(system+user).encode());prompts.append(json.loads(user))
                return left.pop(0)
        class Agent:
            isolation={'unit':'fake'}
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def run(self,context,handler,*a):
                with patch.object(agent,'rpc',side_effect=lambda operation,**message:handler(operation,message)):
                    return agent.answer(context)
        public={'case_id':'BIRD-PG-0000','database_id':'db','dialect':'postgres','question':'original question','evidence':'official evidence'}
        request={'mode':'diagnostic','input':public,'data_root':'.','results_dir':'.','credentials_file':'private',
            'receipt':{},'index_path':'index','code_sha256':'unit','model_config_private':{'api_key':'PRIVATE_API_KEY'}}
        evidence=SimpleNamespace(domain=lambda db:{'query_role':'ro'},validation={'initialization_id':'unit'},manifest={})
        schema={'retrieval':{},'index_sha256':'index','graph':{},'schema_text':'authorized schema'}
        with patch('evaluation.bird.case_worker.code_binding',return_value={'sha256':'unit'}),\
            patch('evaluation.bird.case_worker.Evidence.load',return_value=evidence),\
            patch('evaluation.bird.case_worker.load_credentials',return_value={'passwords':{'ro':'PRIVATE_PG_PASSWORD'}}),\
            patch('evaluation.bird.case_worker.BirdRuntime',Runtime),patch('evaluation.bird.case_worker.IsolatedAgent',Agent),\
            patch('evaluation.bird.model.Models',Models),patch('evaluation.bird.retrieval.retrieve',return_value=deepcopy(schema)):
            result=execute(request)
        return result,database_calls,prompts

    def test_real_loop_stops_second_identical_invalid_sql_without_third_model_or_db_call(self):
        sql='SELECT t.missing FROM t'
        result,calls,prompts=self.run_agent([{'action':'query','sql':sql}]*3)
        self.assertEqual(result['status'],'repeated_sql');self.assertFalse(result['complete'])
        self.assertEqual(len(calls),1);self.assertEqual(len(prompts),2)
        self.assertEqual(result['budget']['generation_attempts'],{1:2});self.assertEqual(result['budget']['validation_attempts'],{1:2})
        self.assertEqual(result['budget']['model_http_attempts'],2);self.assertEqual(result['budget']['sql_tool_calls'],0)
        self.assertFalse(result['validation_events'][-1]['database_validation_performed'])
        self.assertIn('repair_feedback',prompts[1]['validation_error'])

    def test_three_distinct_repairs_remain_available_and_final_sql_is_not_rewritten(self):
        good='SELECT t.id FROM t'
        result,calls,prompts=self.run_agent([{'action':'query','sql':'SELECT t.missing1 FROM t'},
            {'action':'query','sql':'SELECT t.missing2 FROM t'},{'action':'query','sql':good}])
        self.assertEqual(result['status'],'diagnostic_answered');self.assertEqual(result['generated_sql'],good)
        self.assertEqual(len(prompts),3);self.assertEqual(len(calls),4)
        self.assertEqual(result['budget']['generation_attempts'],{1:3});self.assertEqual(result['budget']['validation_attempts'],{1:3})
        self.assertEqual(result['budget']['sql_tool_calls'],1);self.assertIsNone(result['ex_correct'])
        for secret in ('PRIVATE_API_KEY','PRIVATE_PG_PASSWORD','gold_sql'):
            self.assertNotIn(secret,json.dumps(prompts))

    def test_third_distinct_failure_exhausts_original_limit(self):
        result,calls,prompts=self.run_agent([{'action':'query','sql':f'SELECT t.missing{i} FROM t'} for i in range(3)])
        self.assertEqual(result['status'],'validation_failed');self.assertEqual(len(prompts),3);self.assertEqual(len(calls),3)
        self.assertEqual(result['budget']['model_http_attempts'],3)

    def test_local_policy_rejection_is_not_reported_as_database_validation(self):
        result,calls,prompts=self.run_agent([{'action':'query','sql':'SELECT t.missing FROM t'}]*3,policy_failure=True)
        first,second=result['validation_events']
        self.assertTrue(first['runtime_validation_performed']);self.assertFalse(first['database_validation_performed'])
        self.assertFalse(second['runtime_validation_performed']);self.assertFalse(second['database_validation_performed'])

    def test_real_source_guard_feedback_reaches_next_model_with_allowed_forms(self):
        good='SELECT t.id FROM public.t WHERE t.id > 1'
        result,calls,prompts=self.run_agent([{'action':'query','sql':'SELECT t.id FROM db.t WHERE t.id > 1'},
            {'action':'query','sql':good}],validate_sources=True)
        self.assertEqual(result['status'],'diagnostic_answered');self.assertEqual(result['generated_sql'],good)
        feedback=prompts[1]['validation_error']['repair_feedback']
        self.assertEqual(feedback['source_policy']['denied_references'][0]['observed_schema'],'db')
        self.assertEqual(feedback['source_policy']['denied_references'][0]['allowed_current_source_references'],['"t"','"public"."t"'])
        self.assertFalse(result['validation_events'][0]['database_validation_performed'])
        self.assertEqual(result['budget']['chat_http_attempts'],2);self.assertEqual(result['budget']['sql_tool_calls'],1)


if __name__=='__main__':unittest.main()
