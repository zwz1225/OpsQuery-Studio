"""Immutable capture scope, complete native comparison, budgets and cleanup."""
from contextlib import nullcontext
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from scripts.m2_b_common import BASE, digest_file
from scripts.m2_grain_diagnostics import (SOURCE_SHA, NATIVE_SHA, CASE_IDS, FIRST_SQL_SHA,
    captured_first, query_plan, load_cases, audit_case, run_audit)
from evaluation.bird.budgets import BirdFailure
from evaluation.bird.evidence import Evidence, scorer_gold, public_cases
from evaluation.bird.manifest import code_binding
from evaluation.bird.native import NativeResult, encoded, tagged
from evaluation.bird.replay import native_difference, sql_sha
from evaluation.bird.runtime import BirdRuntime
from scripts.m2_b_structure import expectations

MOD = 'scripts.m2_grain_diagnostics.'
ROOT = BASE/'evaluation/results'
SOURCE = ROOT/'m2_public_intent_v3_development80_server_rerun_v2.json'
NATIVE = ROOT/'m2_public_intent_v3_development80_native_server_rerun_v2.json'


def result(rows, columns=None):
    columns = columns or ['value']
    size = len(encoded({'columns':columns})) + sum(len(encoded([tagged(v) for v in row]))+1 for row in rows)
    return NativeResult(columns, rows, size)


class CapturedFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=json.loads(SOURCE.read_bytes()); cls.native=json.loads(NATIVE.read_bytes())
        cls.cases={c['case_id']:c for c in cls.source['cases']}
        cls.gold=scorer_gold()
        root=Path('E:/PythonLearn/datasets/bird_mini_dev') if sys.platform=='win32' else BASE/'data/external/bird_mini_dev'
        cls.evidence=Evidence.load(root)

    def producer_patches(self):
        # Historical v3 fixture only. Verify all execution/permissions/scoring
        # files, then emulate its producer metadata and policy. Production audit
        # still refuses the changed v4 candidate before any database connection.
        current=code_binding()['files'];saved=self.source['code_binding']['files']
        changed={'evaluation/bird/intent.py','evaluation/bird/relationships.py','evaluation/bird/units_output.py'}
        self.assertEqual(set(current),set(saved))
        self.assertTrue(all(current[k]==v for k,v in saved.items() if k not in changed))
        return (patch(MOD+'code_binding',return_value=self.source['code_binding']),
                patch('evaluation.bird.intent_replay.code_binding',return_value=self.source['code_binding']),
                patch('evaluation.bird.intent_replay.policy',return_value=self.source['intent_candidate_policy']))

    def fixture(self, cid=CASE_IDS[0]):
        case=deepcopy(self.cases[cid]);gold=deepcopy(self.gold[cid])
        first=result([(1.,)]); final=result([(2.,)]); reference=result([(2.,)])
        recorded=None
        if cid!='BIRD-PG-0273':
            case['result']=final.diagnostic()
            recorded=dict(source_identity=case['source_identity'],
                results=dict(captured_generated=dict(diagnostic=final.diagnostic()),frozen_gold=dict(diagnostic=reference.diagnostic())),
                native_comparison=native_difference(final,reference))
        plan=query_plan(case,gold)
        values=dict(captured_first_rejected=first,captured_final=final,frozen_gold=reference)
        calls=[]
        def execute(sql,budget):
            name=list(plan)[len(calls)];calls.append(sql)
            self.assertEqual(sql,plan[name]);return values[name]
        runtime=NS(database_id='toxicology',identity=NS(public=lambda:case['source_identity']),
            domain={'query_role':case['query_role']},names={'atom','bond','molecule','connected'},
            connections=NS(closed=False),execute_native=execute,
            receipt=lambda:dict(database_id='toxicology',role=case['query_role'],live_target_verified=True))
        return runtime,case,gold,recorded,calls,values


class CaptureProvenanceTest(CapturedFixtures):
    def test_real_reports_select_exact_three_unchanged_captures(self):
        p1,p2,p3=self.producer_patches()
        with p1,p2,p3:
            source,selected=load_cases(SOURCE,NATIVE,self.evidence)
        self.assertEqual(digest_file(SOURCE),SOURCE_SHA);self.assertEqual(digest_file(NATIVE),NATIVE_SHA)
        self.assertEqual([c['case_id'] for c,g,r in selected],list(CASE_IDS))
        self.assertEqual([len(query_plan(c,g)) for c,g,r in selected],[3,2,3])
        self.assertEqual(source['summary']['case_count'],80)
        self.assertIsNone(selected[1][2])

    def test_wrong_source_hash_refused_before_gold_and_connections(self):
        with tempfile.TemporaryDirectory() as folder:
            bad=Path(folder)/'changed.json';bad.write_text('{}')
            with patch(MOD+'scorer_gold',side_effect=AssertionError('No Gold')),\
                 patch(MOD+'BirdRegistry',side_effect=AssertionError('No connection')):
                with self.assertRaises(ValueError):run_audit(self.evidence,bad,NATIVE,bad,{})

    def test_wrong_native_hash_refused_before_loading_candidate(self):
        with tempfile.TemporaryDirectory() as folder:
            bad=Path(folder)/'changed.json';bad.write_text('{}')
            with patch(MOD+'load_candidate_capture',side_effect=AssertionError('No candidate load')):
                with self.assertRaises(ValueError):load_cases(SOURCE,bad,self.evidence)

    def test_current_environment_drift_fails_closed(self):
        changed=deepcopy(self.source['code_binding']);changed['kernel']='different'
        with patch(MOD+'code_binding',return_value=changed),patch(MOD+'load_candidate_capture',side_effect=AssertionError('No Gold')):
            with self.assertRaises(ValueError):load_cases(SOURCE,NATIVE,self.evidence)

    def test_current_code_file_drift_fails_closed(self):
        changed=deepcopy(self.source['code_binding']);changed['files']['evaluation/bird/intent.py']='0'*64
        with patch(MOD+'code_binding',return_value=changed),patch(MOD+'load_candidate_capture',side_effect=AssertionError('No Gold')):
            with self.assertRaises(ValueError):load_cases(SOURCE,NATIVE,self.evidence)

    def test_old_production_audit_refuses_v4_before_any_connection(self):
        with patch(MOD+'BirdRegistry',side_effect=AssertionError('No connection')):
            with self.assertRaises(ValueError):run_audit(self.evidence,SOURCE,NATIVE,Path('credentials'),{})

    def test_added_audit_scripts_leave_producer_code_inventory_unchanged(self):
        current=code_binding()['files']
        self.assertEqual(set(current),set(self.source['code_binding']['files']))
        self.assertNotIn('scripts/m2_grain_diagnostics.py',current)
        self.assertNotIn('scripts/check_m2_grain_diagnostics.py',current)

    def test_holdout_and_arbitrary_cases_refused(self):
        case=deepcopy(self.cases[CASE_IDS[0]]);case['case_id']='BIRD-PG-1028'
        with self.assertRaises(ValueError):captured_first(case)

    def test_sql_tampering_redaction_and_truncation_refused(self):
        for key,value in [('text','SELECT 1'),('original_sha256','0'*64),('original_utf8_bytes',1),('redacted',True),('truncated',True)]:
            with self.subTest(key=key):
                case=deepcopy(self.cases[CASE_IDS[0]])
                for event in case['development_diagnostics']['attempts'][:2]:event['sql'][key]=value
                with self.assertRaises(ValueError):captured_first(case)

    def test_first_rejection_must_match_first_decision(self):
        case=deepcopy(self.cases[CASE_IDS[0]])
        case['development_diagnostics']['attempts'][1]['sql']['text']+=' '
        with self.assertRaises(ValueError):captured_first(case)

    def test_prior_execution_cannot_be_called_unexecuted(self):
        case=deepcopy(self.cases[CASE_IDS[0]])
        case['development_diagnostics']['attempts'].insert(1,dict(kind='execute'))
        with self.assertRaises(ValueError):captured_first(case)

    def test_rejection_codes_and_feedback_must_be_preserved(self):
        case=deepcopy(self.cases[CASE_IDS[0]])
        case['development_diagnostics']['attempts'][1]['repair_feedback']['intent_violations']=[]
        with self.assertRaises(ValueError):captured_first(case)

    def test_0273_has_two_queries_and_no_invented_final_sql(self):
        case=deepcopy(self.cases['BIRD-PG-0273']);gold=self.gold['BIRD-PG-0273']
        plan=query_plan(case,gold)
        self.assertEqual(list(plan),['captured_first_rejected','frozen_gold'])
        case['generated_sql']='SELECT 1'
        with self.assertRaises(ValueError):query_plan(case,gold)

    def test_gold_sql_and_database_changes_refused(self):
        case=deepcopy(self.cases[CASE_IDS[0]])
        for key,value in [('gold_sql',self.gold[CASE_IDS[0]]['gold_sql']+' '),('database_id','financial'),('dialect','duckdb')]:
            with self.subTest(key=key):
                gold=deepcopy(self.gold[CASE_IDS[0]]);gold[key]=value
                with self.assertRaises(ValueError):query_plan(case,gold)

    def test_recorded_business_rejections_and_new_contract_are_separate(self):
        from evaluation.bird.intent import violations,build_contract
        evidence=self.evidence;runtime=object.__new__(BirdRuntime);db='toxicology'
        runtime.evidence=evidence;runtime.database_id=db;runtime.domain=evidence.domain(db)
        runtime.tables=evidence.tables(db);runtime.names=set(runtime.domain['tables']);runtime.expected=expectations(evidence.manifest)
        runtime._descriptions,runtime.description_diagnostic=evidence.descriptions(db)
        runtime.catalog=runtime._catalog({t['name']:evidence.validation['structure']['verified_structure']['columns'][t['name']] for t in runtime.tables})
        public={c['case_id']:c for c in public_cases('development80')}
        for cid in CASE_IDS:
            case=self.cases[cid];first,rejection=captured_first(case)
            current=build_contract(runtime,public[cid],case['development_diagnostics']['retrieval']['schema_graph']['value'],
                                   case['retrieval']['intent_selection'],case['canonical_lookup'])
            self.assertTrue(rejection['repair_feedback']['intent_violations'])
            self.assertEqual(violations(runtime,public[cid],current,first['text']),[])


class NativeExecutionTest(CapturedFixtures):
    def run_case(self,cid=CASE_IDS[0],mutate=None):
        runtime,case,gold,recorded,calls,values=self.fixture(cid)
        if mutate:mutate(runtime,case,gold,recorded,values)
        reasons=captured_first(case)[1]['repair_feedback']['intent_violations']
        row={};error=None
        with patch(MOD+'violations',return_value=reasons),patch('evaluation.bird.model.ModelConfig.load',side_effect=AssertionError('No model/config')):
            try:audit_case(runtime,case,gold,recorded,progress=row)
            except Exception as caught:error=caught
        return row,error,calls

    def test_exact_first_final_and_gold_bytes_execute_with_zero_model_budget(self):
        row,error,calls=self.run_case()
        self.assertIsNone(error);self.assertEqual(calls,list(row['queries'].values()))
        self.assertEqual(row['budget']['sql_tool_calls'],3);self.assertEqual(row['budget']['model_http_attempts'],0)
        self.assertEqual(row['query_sha256']['captured_first_rejected'],FIRST_SQL_SHA[CASE_IDS[0]])
        self.assertFalse(row['native_comparisons']['first_vs_gold']['matches_frozen_gold'])
        self.assertTrue(row['native_comparisons']['final_vs_gold']['matches_frozen_gold'])
        self.assertTrue(row['previous_final_diagnostic_preserved']);self.assertTrue(row['previous_gold_diagnostic_preserved'])

    def test_0273_comparison_cannot_be_reported_as_previous_execution(self):
        row,error,calls=self.run_case('BIRD-PG-0273')
        self.assertIsNone(error);self.assertEqual(len(calls),2)
        self.assertFalse(row['first_sql_previously_executed']);self.assertIsNone(row['previous_final_diagnostic_preserved'])
        self.assertNotIn('final_vs_gold',row['native_comparisons'])

    def test_reference_match_is_observed_without_assuming_expected_outcome(self):
        def mutate(rt,c,g,old,values):values['captured_first_rejected']=values['frozen_gold']
        row,error,_=self.run_case(mutate=mutate)
        self.assertIsNone(error);self.assertTrue(row['native_comparisons']['first_vs_gold']['matches_frozen_gold'])

    def test_decimal_float_difference_not_rounded_or_coerced(self):
        def mutate(rt,c,g,old,values):
            values['captured_first_rejected']=result([(Decimal('.1'),)])
            values['frozen_gold']=result([(.1,)])
            old['results']['frozen_gold']['diagnostic']=values['frozen_gold'].diagnostic()
            old['native_comparison']=native_difference(values['captured_final'],values['frozen_gold'])
        row,error,_=self.run_case(mutate=mutate)
        self.assertIsNone(error);self.assertFalse(row['native_comparisons']['first_vs_gold']['matches_frozen_gold'])

    def test_native_comparison_uses_complete_result_beyond_preview(self):
        def mutate(rt,c,g,old,values):
            values['captured_first_rejected']=result([(i,) for i in range(30)])
            values['frozen_gold']=result([(i,) for i in range(29)]+[(999,)])
            old['results']['frozen_gold']['diagnostic']=values['frozen_gold'].diagnostic()
            old['native_comparison']=native_difference(values['captured_final'],values['frozen_gold'])
        row,error,_=self.run_case(mutate=mutate)
        self.assertIsNone(error);self.assertTrue(row['results']['captured_first_rejected']['preview']['preview_truncated'])
        self.assertFalse(row['native_comparisons']['first_vs_gold']['matches_frozen_gold'])

    def test_partial_first_result_fails_before_any_gold_query(self):
        def mutate(rt,c,g,old,values):values['captured_first_rejected'].complete=False
        row,error,calls=self.run_case(mutate=mutate)
        self.assertIsInstance(error,ValueError);self.assertEqual(len(calls),1)
        self.assertEqual(row['status'],'failed');self.assertFalse(row['gold_execution_attempted'])
        self.assertNotIn('native_comparisons',row)

    def test_changed_previous_final_diagnostic_fails_closed(self):
        def mutate(rt,c,g,old,values):values['captured_final']=result([(999.,)])
        row,error,_=self.run_case(mutate=mutate)
        self.assertIsInstance(error,ValueError);self.assertFalse(row['previous_final_diagnostic_preserved'])
        self.assertNotIn('native_comparisons',row)

    def test_changed_previous_gold_diagnostic_fails_closed(self):
        def mutate(rt,c,g,old,values):values['frozen_gold']=result([(999.,)])
        row,error,_=self.run_case(mutate=mutate)
        self.assertIsInstance(error,ValueError);self.assertFalse(row['previous_gold_diagnostic_preserved'])

    def test_query_role_or_source_mismatch_executes_nothing(self):
        for attribute,value in [('domain',{'query_role':'admin'}),('identity',NS(public=lambda:{}))]:
            rt,c,g,old,calls,_=self.fixture();setattr(rt,attribute,value)
            with self.subTest(attribute=attribute),self.assertRaises(ValueError):audit_case(rt,c,g,old)
            self.assertEqual(calls,[])

    def test_readonly_source_policy_preflights_entire_plan(self):
        rt,c,g,old,calls,_=self.fixture()
        for sql in ['DELETE FROM atom','SELECT 1; SELECT 2','SELECT molecule_id FROM private.atom']:
            with self.subTest(sql=sql),patch(MOD+'query_plan',return_value={'captured_first_rejected':sql}):
                with self.assertRaises(ValueError):audit_case(rt,c,g,old)
                self.assertEqual(calls,[])

    def test_unreproducible_business_rejection_stops_before_queries(self):
        rt,c,g,old,calls,_=self.fixture();row={}
        with patch(MOD+'violations',return_value=[]):
            with self.assertRaises(ValueError):audit_case(rt,c,g,old,progress=row)
        self.assertEqual(calls,[]);self.assertEqual(row['status'],'failed')

    def test_gold_timeout_preserves_results_and_budget(self):
        def mutate(rt,c,g,old,values):
            execute=rt.execute_native
            def timeout(sql,budget):
                if sql==g['gold_sql']:raise BirdFailure('sql_timeout','57014')
                return execute(sql,budget)
            rt.execute_native=timeout
        row,error,_=self.run_case(mutate=mutate)
        self.assertIsInstance(error,BirdFailure);self.assertEqual(row['status'],'failed')
        self.assertTrue(row['gold_execution_attempted']);self.assertFalse(row['gold_executed'])
        self.assertEqual(row['budget']['sql_tool_calls'],3)
        self.assertIn('captured_first_rejected',row['results']);self.assertNotIn('native_comparisons',row)


class RegistryLifecycleTest(CapturedFixtures):
    def run_registry(self,fail=False,changed_evidence=False):
        rows={};selected=[]
        for cid in CASE_IDS:
            rt,c,g,old,calls,values=self.fixture(cid);rows[cid]=(rt,c,g,old,calls,values);selected.append((c,g,old))
        closed=[]
        class Registry:
            def __init__(self,*args):self._runtimes={}
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
            def get(self,db):
                runtime=rows[CASE_IDS[0]][0];self._runtimes[db]=runtime;return runtime
            def close(self):
                closed.append(True)
                for runtime in self._runtimes.values():runtime.connections.closed=True
        def execute_case(runtime,case,gold,recorded,progress):
            rt,_,_,_,_,_=rows[case['case_id']]
            if fail:rt.execute_native=lambda *a:(_ for _ in ()).throw(BirdFailure('sql_timeout'))
            reasons=captured_first(case)[1]['repair_feedback']['intent_violations']
            with patch(MOD+'violations',return_value=reasons):return audit_case(rt,case,gold,recorded,progress=progress)
        report={};caught=None
        hashes=lambda p: ('0'*64 if changed_evidence else SOURCE_SHA) if str(p)=='source' else NATIVE_SHA
        with patch(MOD+'load_cases',return_value=(self.source,selected)),patch(MOD+'source_binding',return_value={}),\
             patch(MOD+'code_binding',return_value={'sha256':'unit'}),patch(MOD+'audit_code',return_value={'script':'unit'}),\
             patch(MOD+'digest_file',side_effect=hashes),patch(MOD+'hard_deadline',return_value=nullcontext()),\
             patch(MOD+'audit_case',side_effect=execute_case):
            try:run_audit(None,Path('source'),Path('native'),Path('credentials'),report,registry_factory=Registry)
            except Exception as error:caught=error
        return report,caught,closed

    def test_eight_query_success_does_not_change_candidate_score(self):
        report,error,closed=self.run_registry()
        self.assertIsNone(error);self.assertEqual(report['summary']['sql_execution_count'],8)
        self.assertEqual(report['summary']['case_count'],3);self.assertEqual(report['summary']['new_model_request_count'],0)
        self.assertEqual(len(report['source_receipts']),1);self.assertTrue(report['pools_closed'])
        self.assertGreaterEqual(len(closed),2);self.assertTrue(report['candidate_score_unchanged'])
        self.assertIsNone(report['primary_ex']);self.assertIsNone(report['summary']['formal_ex_denominator'])
        self.assertFalse(report['holdout_live_allowed']);self.assertTrue(report['diagnostic_comparisons_complete'])

    def test_failure_closes_pool_preserves_attempt_and_never_claims_complete(self):
        report,error,closed=self.run_registry(fail=True)
        self.assertIsInstance(error,BirdFailure);self.assertTrue(closed);self.assertTrue(report['pools_closed'])
        self.assertEqual(report['cases'][0]['status'],'failed');self.assertEqual(report['cases'][0]['budget']['sql_tool_calls'],1)
        self.assertNotEqual(report.get('run_status'),'complete');self.assertFalse(report.get('diagnostic_comparisons_complete',False))
        self.assertFalse(report['gold_executed'])

    def test_evidence_change_during_run_closes_pool_and_refuses_complete(self):
        report,error,closed=self.run_registry(changed_evidence=True)
        self.assertIsInstance(error,ValueError);self.assertTrue(report['pools_closed']);self.assertTrue(closed)
        self.assertNotEqual(report.get('run_status'),'complete')


if __name__=='__main__':unittest.main()
