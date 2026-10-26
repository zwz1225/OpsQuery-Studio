"""Local source explanations and independent native development auditing."""
from contextlib import nullcontext
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from evaluation.bird.budgets import BirdFailure
from evaluation.bird.diagnostics import encoded
from evaluation.bird.native import NativeResult
from evaluation.bird.repair import RepairSession,FEEDBACK_BYTES,POLICY
from evaluation.bird.semantics import audit_case,load_cases,run_audit


def context(db='db'):
    tables=[{'id':db+'.t','database':db,'name':'t','fields':[{'name':'id','label':'Identifier','type':'bigint'}]}]
    return SimpleNamespace(database_id=db,domain={'query_role':'ro'},identity=SimpleNamespace(public=lambda:{'logical_database_id':db}),
        catalog=SimpleNamespace(tables=tables))


class SourceFeedbackTest(unittest.TestCase):
    def feedback(self,sql,r=None,secrets=()):
        return RepairSession(r or context(),secrets).feedback(BirdFailure('sql_source_denied'),sql)

    def test_logical_database_is_not_physical_schema(self):
        sql='SELECT t.id FROM db.t'
        f=self.feedback(sql);p=f['source_policy'];ref=p['denied_references'][0]
        self.assertEqual(f['policy'],'bird_authorized_sql_repair_v2')
        self.assertEqual(ref['observed_schema'],'db');self.assertEqual(ref['reason'],'physical_schema_denied')
        self.assertEqual(ref['allowed_current_source_references'],['"t"','"public"."t"'])
        self.assertEqual(p['logical_database_id'],'db');self.assertEqual(p['physical_schema'],'public')
        self.assertIn('local SQL policy',f['local_reason']['text'])
        self.assertEqual(f['server_reason']['text'],'');self.assertIsNone(f['sqlstate']);self.assertFalse(f['position']['available'])
        self.assertEqual(f['authorized_fields'],[])

    def test_unknown_table_never_gets_an_invented_allowed_reference(self):
        f=self.feedback('SELECT secret FROM foreign.private')
        ref=f['source_policy']['denied_references'][0]
        self.assertFalse(ref['table_in_current_catalog']);self.assertEqual(ref['allowed_current_source_references'],[])
        f=self.feedback('SELECT missing FROM public.unknown')
        self.assertEqual(f['source_policy']['denied_references'][0]['reason'],'table_not_authorized')

    def test_catalog_qualification_and_cte_scope_are_distinguished(self):
        f=self.feedback('WITH q AS (SELECT id FROM other.public.t) SELECT id FROM q')
        refs=f['source_policy']['denied_references']
        self.assertEqual(len(refs),1);self.assertEqual(refs[0]['reason'],'catalog_qualification_denied')
        self.assertEqual(refs[0]['observed_catalog'],'other');self.assertEqual(refs[0]['observed_table'],'t')

    def test_quoted_case_is_preserved_and_unquoted_case_normalized(self):
        f=self.feedback('SELECT id FROM "PUBLIC".t')
        self.assertEqual(f['source_policy']['denied_references'][0]['observed_schema'],'PUBLIC')
        self.assertEqual(self.feedback('SELECT id FROM PUBLIC.T')['source_policy']['denied_references'],[])

    def test_credential_scrubbing_and_byte_caps_cover_new_fields(self):
        secret='private-secret-123'
        f=self.feedback('SELECT id FROM "'+secret+'".t',secrets=(secret,))
        self.assertNotIn(secret,json.dumps(f));self.assertIn('[REDACTED]',json.dumps(f))
        sql='SELECT a.id FROM '+','.join('"'+('x'*400)+str(i)+'".t AS a'+str(i) for i in range(10))
        f=self.feedback(sql);self.assertLessEqual(len(encoded(f)),FEEDBACK_BYTES)
        self.assertLessEqual(len(encoded(f['source_policy'])),2048)
        self.assertGreater(f['source_policy']['omitted_reference_count'],0)

    def test_repeat_keeps_local_origin_and_does_not_reclassify_as_pg(self):
        s=RepairSession(context());sql='SELECT id FROM db.t';s.remember(BirdFailure('sql_source_denied'),sql)
        error,f=s.repeated(sql)
        self.assertEqual(error.category,'repeated_invalid_sql');self.assertFalse(f['retryable'])
        self.assertEqual(f['source_policy']['origin'],'local_sql_policy');self.assertIsNone(f['sqlstate'])


def fixture(cid='BIRD-PG-0050'):
    db='california_schools' if cid.endswith('0050') else 'financial';r=context(db)
    predicted=NativeResult(['address','sname'],[('Road',None)],64)
    gold_result=NativeResult(['address','school'],[('Road','Actual School')],64)
    probe=NativeResult(['cds','math','sname','school','address'],[('123',700,None,'Actual School','Road')],128)
    if cid.endswith('0095'):
        predicted=NativeResult(['account_id'],[],32);gold_result=NativeResult(['account_id'],[(7,)],48)
        probe=NativeResult(['client_id'],[(1,)],48)
    expected_sql='SELECT id FROM t';gold={'case_id':cid,'database_id':db,'gold_sql':expected_sql,
        'gold_sql_sha256':hashlib.sha256(expected_sql.encode()).hexdigest()}
    case={'case_id':cid,'database_id':db,'source_identity':r.identity.public(),'generated_sql':'SELECT other FROM t','result':predicted.diagnostic()}
    calls=[];queue=[predicted,gold_result,probe]
    def execute(sql,budget):
        calls.append(sql);return queue.pop(0)
    r.execute_native=execute
    return r,case,gold,calls


class NativeSemanticAuditTest(unittest.TestCase):
    def test_different_name_values_fail_native_comparison_without_alias_relaxation(self):
        runtime,case,gold,calls=fixture();result=audit_case(runtime,case,gold)
        self.assertFalse(result['matches_frozen_gold']);self.assertIsNone(result['primary_ex'])
        self.assertFalse(result['details']['name_pairs'][0]['native_equal'])
        self.assertEqual(result['details']['name_pairs'][0]['satscores_sname'],['null'])
        self.assertEqual(result['budget']['sql_tool_calls'],3);self.assertEqual(result['budget']['model_http_attempts'],0)
        self.assertEqual(calls[:2],[case['generated_sql'],gold['gold_sql']]);self.assertEqual(case['result']['row_count'],1)

    def test_empty_generated_result_is_not_success_against_nonempty_gold(self):
        runtime,case,gold,calls=fixture('BIRD-PG-0095');result=audit_case(runtime,case,gold)
        self.assertFalse(result['matches_frozen_gold'])
        self.assertEqual(result['results']['captured_generated']['diagnostic']['row_count'],0)
        self.assertEqual(result['results']['frozen_gold']['diagnostic']['row_count'],1)

    def test_column_names_do_not_affect_native_comparison(self):
        runtime,case,gold,calls=fixture('BIRD-PG-0095')
        values=[NativeResult(['a'],[(7,)],48),NativeResult(['b'],[(7,)],48),NativeResult(['probe'],[],32)]
        runtime.execute_native=lambda *a:values.pop(0)
        self.assertTrue(audit_case(runtime,case,gold)['matches_frozen_gold'])

    def test_probe_failure_preserves_gold_attempt_and_budget(self):
        runtime,case,gold,calls=fixture();original=runtime.execute_native
        def execute(sql,budget):
            if len(calls)==2:raise BirdFailure('sql_timeout','57014')
            return original(sql,budget)
        runtime.execute_native=execute;record={}
        with self.assertRaises(BirdFailure):audit_case(runtime,case,gold,progress=record)
        self.assertTrue(record['gold_execution_attempted']);self.assertTrue(record['gold_executed'])
        self.assertEqual(record['status'],'failed');self.assertEqual(record['budget']['sql_tool_calls'],3)
        self.assertEqual(record['execution_events'][-1]['error'],{'category':'sql_timeout','sqlstate':'57014'})

    def test_wrong_source_fails_before_any_query(self):
        runtime,case,gold,calls=fixture();case['source_identity']={'logical_database_id':'foreign'}
        with self.assertRaises(ValueError):audit_case(runtime,case,gold)
        self.assertEqual(calls,[])

    def test_modified_source_report_is_rejected_before_loading_gold(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.json';path.write_text('{}')
            with patch('evaluation.bird.semantics.scorer_gold',side_effect=AssertionError('Gold must not be read')):
                with self.assertRaises(ValueError):load_cases(path,None)

    def test_current_accepted_report_binds_only_two_development_cases(self):
        from evaluation.bird.evidence import Evidence
        from scripts.m2_b_common import BASE
        import sys
        root=Path('E:/PythonLearn/datasets/bird_mini_dev') if sys.platform=='win32' else BASE/'data/external/bird_mini_dev'
        rows=load_cases(BASE/'evaluation/results/m2_schema_coverage_validation3_server.json',Evidence.load(root))
        self.assertEqual([case['case_id'] for case,gold in rows],['BIRD-PG-0050','BIRD-PG-0095'])
        self.assertNotEqual(rows[0][0]['generated_sql'],rows[0][1]['gold_sql'])

    def run_registry_audit(self,fail_probe=False):
        selected=[];runtimes={}
        for cid in ('BIRD-PG-0050','BIRD-PG-0095'):
            runtime,case,gold,calls=fixture(cid);runtime.connections=SimpleNamespace(closed=False)
            selected.append((case,gold));runtimes[runtime.database_id]=runtime
        if fail_probe:
            runtime=runtimes['california_schools'];original=runtime.execute_native;count=[]
            def execute(sql,budget):
                count.append(sql)
                if len(count)==3:raise BirdFailure('sql_timeout','57014')
                return original(sql,budget)
            runtime.execute_native=execute
        class Registry:
            def __init__(self,*args):self._runtimes={}
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
            def get(self,db):self._runtimes[db]=runtimes[db];return runtimes[db]
            def close(self):
                for runtime in self._runtimes.values():runtime.connections.closed=True
        report={};error=None
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.json';path.write_text('{}')
            with patch('evaluation.bird.semantics.load_cases',return_value=selected),\
                 patch('evaluation.bird.semantics.source_binding',return_value={}),\
                 patch('evaluation.bird.budgets.hard_deadline',lambda *args:nullcontext()):
                try:run_audit(None,path,path,report,registry_factory=Registry)
                except BirdFailure as caught:error=caught
        return report,error

    def test_registry_closes_and_mismatches_do_not_become_a_formal_score(self):
        report,error=self.run_registry_audit()
        self.assertIsNone(error);self.assertEqual(report['run_status'],'complete');self.assertTrue(report['pools_closed'])
        self.assertTrue(report['gold_executed']);self.assertFalse(report['holdout_live_allowed'])
        self.assertEqual(report['summary']['matches_frozen_gold_count'],0)
        self.assertEqual(report['summary']['audit_sql_execution_count'],6)
        self.assertIsNone(report['summary']['formal_ex_denominator'])

    def test_registry_timeout_retains_partial_gold_record_and_closes_pool(self):
        report,error=self.run_registry_audit(fail_probe=True)
        self.assertEqual(error.category,'sql_timeout');self.assertTrue(report['pools_closed'])
        self.assertTrue(report['gold_executed']);self.assertEqual(len(report['cases']),1)
        self.assertEqual(report['cases'][0]['budget']['sql_tool_calls'],3)


if __name__=='__main__':unittest.main()
