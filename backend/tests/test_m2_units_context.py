"""Trusted probe shape, provenance, exact scoring and lifecycle regression tests."""
from contextlib import nullcontext
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import sqlglot
from sqlglot import exp

from scripts.m2_b_common import BASE,digest_file
from scripts.m2_units_context import (SOURCE_SHA,NATIVE_SHA,CASE_IDS,load_cases,
    numeric_variants,context_variants,query_plan,audit_case,run_audit,projected)
from evaluation.bird.budgets import BirdFailure
from evaluation.bird.native import NativeResult,encoded,tagged
from evaluation.bird.replay import native_difference,sql_sha
from evaluation.bird.sql import validate_sql

NUMERIC_SQL="SELECT CAST(SUM(CASE WHEN a.element='c' THEN 1 ELSE 0 END) AS REAL)/NULLIF(COUNT(DISTINCT a.atom_id),0) AS percentage FROM atom a WHERE EXISTS(SELECT 1 FROM bond b WHERE b.molecule_id=a.molecule_id AND b.bond_type='=')"
CONTEXT_SQL="SELECT DISTINCT u.displayname FROM users u JOIN votes v ON u.id=v.userid JOIN posts p ON v.postid=p.id WHERE v.bountyamount=50 AND p.title ILIKE '%variance%'"


def result(columns,rows):
    size=len(encoded({'columns':columns}))+sum(len(encoded([tagged(v) for v in row]))+1 for row in rows)
    return NativeResult(columns,rows,size)


def fixture(cid):
    numeric=cid==CASE_IDS[0];db='toxicology' if numeric else 'codebase_community'
    sql=NUMERIC_SQL if numeric else CONTEXT_SQL
    predicted=result(['percentage'],[(.5,)]) if numeric else result(['displayname'],[('User',)])
    reference=result(['reference'],[(50.,)]) if numeric else result(['displayname','title'],[('User','variance')])
    gold_sql=sql if numeric else CONTEXT_SQL.replace('u.displayname FROM','u.displayname,p.title FROM')
    identity={'logical_database_id':db,'source_id':'source_'+db}
    case=dict(case_id=cid,database_id=db,source_identity=identity,generated_sql=sql,result=predicted.diagnostic())
    gold=dict(case_id=cid,database_id=db,gold_sql=gold_sql,gold_sql_sha256=sql_sha(gold_sql))
    recorded=dict(source_identity=identity,results={'captured_generated':{'diagnostic':predicted.diagnostic()},
                                                 'frozen_gold':{'diagnostic':reference.diagnostic()}})
    plan=query_plan(case,gold);calls=[]
    values={'captured_generated':predicted,'frozen_gold':reference}
    for name in plan:
        if name not in values:
            values[name]=result(['count','denominator'],[(1,2)]) if name=='captured_counts' else (
                result(['percentage'],[(.5 if name=='numeric_unscaled' else 50.,)]) if numeric else
                result(['displayname','title'],[('User','variance')]))
    def execute(sql,budget):
        name=list(plan)[len(calls)];calls.append(sql)
        assert sql==plan[name]
        return values[name]
    runtime=NS(database_id=db,identity=NS(public=lambda:identity),domain={'query_role':'ro'},names={'atom','bond'} if numeric else {'users','votes','posts'},
        connections=NS(closed=False),execute_native=execute,receipt=lambda:dict(database_id=db,role='ro'))
    return runtime,case,gold,recorded,calls,values


class ProbePlanTest(unittest.TestCase):
    def test_nine_numeric_and_six_context_queries_preserve_original_bytes(self):
        for cid,expected in zip(CASE_IDS,(9,6)):
            r,c,g,old,calls,values=fixture(cid);plan=query_plan(c,g)
            self.assertEqual(len(plan),expected)
            self.assertEqual(plan['captured_generated'],c['generated_sql'])
            self.assertEqual(plan['frozen_gold'],g['gold_sql'])
            for sql in plan.values():self.assertEqual(validate_sql(sql,r.names),sql)

    def test_numeric_population_and_denominator_are_unchanged(self):
        original=sqlglot.parse_one(NUMERIC_SQL,read='postgres')
        for name,sql in numeric_variants(NUMERIC_SQL).items():
            tree=sqlglot.parse_one(sql,read='postgres')
            self.assertEqual(tree.args['where'],original.args['where'])
            self.assertEqual(tree.args['from_'],original.args['from_'])
            self.assertFalse(tree.args.get('joins'))
            self.assertEqual([v.sql() for v in tree.find_all(exp.Count)],[v.sql() for v in original.find_all(exp.Count)])

    def test_numeric_types_and_order_have_no_hidden_double_cast(self):
        variants=numeric_variants(NUMERIC_SQL)
        for prefix,kind in (('real','FLOAT'),('double','DOUBLE'),('numeric','DECIMAL')):
            for name,sql in variants.items():
                if not name.startswith(prefix+'_'):continue
                tree=sqlglot.parse_one(sql,read='postgres');casts=list(tree.find_all(exp.Cast))
                self.assertEqual(len(casts),1,sql)
                self.assertEqual(str(casts[0].args['to']).upper(),kind)
                self.assertTrue(next(tree.find_all(exp.Div)).args['typed'])
        before=sqlglot.parse_one(variants['real_scaled_before'],read='postgres').selects[0].unalias()
        after=sqlglot.parse_one(variants['real_scaled_after'],read='postgres').selects[0].unalias()
        self.assertIsInstance(before,exp.Div);self.assertIsInstance(before.left,exp.Mul)
        self.assertIsInstance(after,exp.Mul);self.assertIsInstance(after.left,exp.Div)

    def test_context_changes_only_projection_case_sensitivity_and_distinct(self):
        original=sqlglot.parse_one(CONTEXT_SQL,read='postgres')
        for name,sql in context_variants(CONTEXT_SQL).items():
            tree=sqlglot.parse_one(sql,read='postgres')
            self.assertEqual(tree.args['joins'],original.args['joins'])
            self.assertEqual([v.sql() for v in tree.selects],['u.displayname','p.title'])
            self.assertEqual(bool(tree.args.get('distinct')),name.endswith('_distinct'))
            self.assertEqual(len(list(tree.find_all(exp.ILike))),int('_ilike_' in name))
            # Normalize the single operator to prove that no predicate changed.
            for node in list(tree.find_all(exp.Like)):
                node.replace(exp.ILike(this=node.this.copy(),expression=node.expression.copy()))
            self.assertEqual(tree.args['where'],original.args['where'])

    def test_unexpected_shapes_do_not_generate_arbitrary_variants(self):
        for sql in ('SELECT 1','SELECT CAST(COUNT(*) AS REAL)/COUNT(*) FROM t','SELECT 1; SELECT 2'):
            with self.assertRaises(ValueError):numeric_variants(sql)
        for sql in ('SELECT x FROM t',CONTEXT_SQL.replace('ILIKE','LIKE'),CONTEXT_SQL.replace('DISTINCT ','')):
            with self.assertRaises(ValueError):context_variants(sql)

    def test_unknown_case_and_changed_gold_hash_are_refused(self):
        r,c,g,old,calls,values=fixture(CASE_IDS[0]);g['gold_sql_sha256']='wrong'
        with self.assertRaises(ValueError):query_plan(c,g)
        c['case_id']=g['case_id']='BIRD-PG-1399'
        with self.assertRaises(ValueError):query_plan(c,g)

    def test_projection_comparison_does_not_relax_full_native_scoring(self):
        user=result(['user'],[('User',)]);context=result(['user','title'],[('User','variance')])
        self.assertFalse(native_difference(user,context)['matches_frozen_gold'])
        self.assertTrue(native_difference(user,projected(context,[0]))['matches_frozen_gold'])
        reference=result(['value'],[(38.80961092816197,)])
        scaled=result(['value'],[(0.3880961092816197*100,)])
        self.assertFalse(native_difference(scaled,reference)['matches_frozen_gold'])


class ProbeExecutionTest(unittest.TestCase):
    def test_all_queries_are_counted_in_bounded_zero_model_batches(self):
        for cid,expected,batches in zip(CASE_IDS,(9,6),(3,2)):
            r,c,g,old,calls,values=fixture(cid);row=audit_case(r,c,g,old)
            self.assertEqual(len(calls),expected);self.assertEqual(row['sql_execution_count'],expected)
            self.assertEqual(len(row['batches']),batches)
            for batch in row['batches']:
                self.assertEqual(batch['budget']['sql_tool_calls'],3)
                self.assertEqual(batch['budget']['model_http_attempts'],0)
            self.assertFalse(row['native_comparisons']['captured_generated']['matches_frozen_gold'])
            self.assertTrue(row['captured_native_diagnostic_preserved']);self.assertTrue(row['frozen_native_diagnostic_preserved'])
            self.assertIsNone(row['primary_ex']);self.assertFalse(row['formal_benchmark'])
            if cid==CASE_IDS[1]:self.assertTrue(row['factor_comparisons']['captured_user_vs_gold_user']['matches_frozen_gold'])

    def test_wrong_runtime_or_policy_denied_plan_executes_nothing(self):
        r,c,g,old,calls,values=fixture(CASE_IDS[0]);r.identity=NS(public=lambda:{})
        with self.assertRaises(ValueError):audit_case(r,c,g,old)
        self.assertEqual(calls,[])
        r,c,g,old,calls,values=fixture(CASE_IDS[0]);r.names={'foreign'}
        with self.assertRaises(BirdFailure):audit_case(r,c,g,old)
        self.assertEqual(calls,[])

    def test_failed_query_retains_consumed_budget_and_partial_evidence(self):
        r,c,g,old,calls,values=fixture(CASE_IDS[0]);execute=r.execute_native
        def fail(sql,budget):
            if len(calls)==3:raise BirdFailure('sql_timeout','57014')
            return execute(sql,budget)
        r.execute_native=fail;row={}
        with self.assertRaises(BirdFailure):audit_case(r,c,g,old,progress=row)
        self.assertEqual(row['sql_execution_count'],4);self.assertTrue(row['gold_executed'])
        self.assertEqual(row['execution_events'][-1]['error'],{'category':'sql_timeout','sqlstate':'57014'})
        self.assertEqual(row['status'],'failed');self.assertEqual(len(row['results']),3)

    def test_all_batches_share_the_original_case_clock(self):
        r,c,g,old,calls,values=fixture(CASE_IDS[0]);execute=r.execute_native;clocks=[]
        def track(sql,budget):
            clocks.append(budget.started)
            return execute(sql,budget)
        r.execute_native=track;audit_case(r,c,g,old)
        self.assertEqual(len(clocks),9);self.assertEqual(len(set(clocks)),1)

    def test_incomplete_result_and_result_drift_cannot_pass(self):
        r,c,g,old,calls,values=fixture(CASE_IDS[0]);values['real_scaled_before'].complete=False
        with self.assertRaises(ValueError):audit_case(r,c,g,old)
        r,c,g,old,calls,values=fixture(CASE_IDS[1]);old['results']['frozen_gold']['diagnostic']={}
        row={}
        with self.assertRaises(ValueError):audit_case(r,c,g,old,progress=row)
        self.assertFalse(row['frozen_native_diagnostic_preserved']);self.assertNotIn('native_comparisons',row)

    def registry_run(self,fail=False):
        fixtures=[fixture(cid) for cid in CASE_IDS];runtimes={r.database_id:r for r,*_ in fixtures}
        selected=[(c,g,old) for r,c,g,old,*_ in fixtures]
        if fail:
            def execute(sql,budget):raise BirdFailure('sql_timeout')
            fixtures[0][0].execute_native=execute
        class Registry:
            def __init__(self,*args):self._runtimes={}
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
            def get(self,db):self._runtimes[db]=runtimes[db];return runtimes[db]
            def close(self):
                for r in self._runtimes.values():r.connections.closed=True
        row={}
        with patch('scripts.m2_units_context.load_cases',return_value=({'code_binding':{'sha256':'old'}},selected)),\
             patch('scripts.m2_units_context.source_binding',return_value={}),\
             patch('scripts.m2_units_context.hard_deadline',side_effect=lambda *a:nullcontext()):
            if fail:
                with self.assertRaises(BirdFailure):run_audit(None,None,None,None,row,registry_factory=Registry)
            else:run_audit(None,None,None,None,row,registry_factory=Registry)
        return row

    def test_registry_closes_pools_and_never_promotes_variants_to_formal_scores(self):
        row=self.registry_run();self.assertTrue(row['pools_closed']);self.assertEqual(row['run_status'],'complete')
        self.assertEqual(row['summary']['sql_execution_count'],15);self.assertEqual(row['summary']['new_model_request_count'],0)
        self.assertEqual(row['summary']['captured_native_diagnostic_preserved_count'],2)
        self.assertFalse(row['holdout_live_allowed']);self.assertIsNone(row['primary_ex'])

    def test_registry_timeout_retains_failure_and_closes_pools(self):
        row=self.registry_run(fail=True);self.assertTrue(row['pools_closed'])
        self.assertFalse(row['gold_executed']);self.assertEqual(row['cases'][0]['sql_execution_count'],1)


class ProvenanceTest(unittest.TestCase):
    def test_wrong_hash_rejected_before_gold_loader_or_connection(self):
        with patch('scripts.m2_units_context.digest_file',return_value='wrong'),\
             patch('scripts.m2_units_context.load_candidate_capture',side_effect=AssertionError('No private Gold loader')),\
             patch('scripts.m2_units_context.BirdRegistry',side_effect=AssertionError('No connection')):
            with self.assertRaises(ValueError):load_cases(None,None,None)

    def test_two_real_reports_and_all_variants_have_exact_provenance(self):
        from evaluation.bird.evidence import Evidence,DEFAULT_DATA
        from evaluation.bird.manifest import code_binding
        path=BASE/'evaluation/results/m2_public_intent_v2_diagnostics14_server.json'
        native=BASE/'evaluation/results/m2_public_intent_v2_native14_server.json'
        captured=json.loads(path.read_bytes());server=captured['code_binding']
        current=code_binding()['files']
        changed_generation={'evaluation/bird/intent.py','evaluation/bird/retrieval.py',
                            'evaluation/bird/relationships.py','evaluation/bird/units_output.py'}
        self.assertTrue(all(current.get(name)==sha for name,sha in server['files'].items() if name not in changed_generation))
        root=Path('E:/PythonLearn/datasets/bird_mini_dev') if Path('E:/PythonLearn/datasets/bird_mini_dev').exists() else DEFAULT_DATA
        evidence=Evidence.load(root)
        # This historical fixture emulates the accepted v2 producer. Execution,
        # permissions and scoring files are verified above; this does not make
        # the old production audit accept a different current candidate version.
        with patch('scripts.m2_units_context.code_binding',return_value=server),\
             patch('evaluation.bird.intent_replay.code_binding',return_value=server),\
             patch('evaluation.bird.intent_replay.policy',return_value=captured['intent_candidate_policy']):
            source,selected=load_cases(path,native,evidence)
        self.assertEqual(digest_file(path),SOURCE_SHA);self.assertEqual(digest_file(native),NATIVE_SHA)
        self.assertEqual([c['case_id'] for c,g,n in selected],list(CASE_IDS))
        for c,g,n in selected:
            for sql in query_plan(c,g).values():validate_sql(sql,set(evidence.domain(c['database_id'])['tables']))


if __name__=='__main__':unittest.main()
