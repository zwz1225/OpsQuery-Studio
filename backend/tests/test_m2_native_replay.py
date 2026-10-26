"""Captured-SQL replay scope, native equality, full results and failure lifecycle."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

from evaluation.bird.budgets import BirdFailure
from evaluation.bird.native import NativeResult
from evaluation.bird.replay import (SOURCE_SHA,load_capture,native_difference,reviewer_hints,
    replay_case,run_replay,sql_sha,structure)
from scripts.m2_b_common import BASE


def result(rows,columns=None):return NativeResult(columns or ['v'],rows,64)


def fixture(cid='BIRD-PG-0050',predicted=None,gold_result=None):
    pred=predicted or result([(1,)])
    expected=gold_result or result([(2,)])
    identity={'logical_database_id':'db','data_version':'accepted','catalog_version':'accepted'}
    runtime=SimpleNamespace(database_id='db',domain={'query_role':'ro'},identity=SimpleNamespace(public=lambda:identity),
        connections=SimpleNamespace(closed=False),receipt=lambda:{'database_id':'db','role':'ro','snapshot':'unit'})
    calls=[];queue=[pred,expected]
    def execute(sql,budget):calls.append(sql);return queue.pop(0)
    runtime.execute_native=execute
    sql='-- exact captured bytes\n SELECT v FROM t;\n'
    case={'case_id':cid,'database_id':'db','source_identity':identity,'generated_sql':sql,'result':pred.diagnostic()}
    reference='SELECT expected FROM t'
    gold={'case_id':cid,'database_id':'db','gold_sql':reference,'gold_sql_sha256':sql_sha(reference)}
    return runtime,case,gold,calls


class NativeDifferenceTest(unittest.TestCase):
    def test_frozen_predicate_ignores_order_duplicates_and_names(self):
        p=result([(1,),(2,),(1,)],['left']);g=result([(2,),(1,)],['right'])
        d=native_difference(p,g)
        self.assertTrue(d['matches_frozen_gold']);self.assertEqual(d['difference_codes'],[])
        self.assertEqual(d['prediction_row_count'],3);self.assertEqual(d['prediction_unique_tuple_count'],2)

    def test_native_numeric_equality_is_not_replaced_with_type_equality(self):
        d=native_difference(result([(Decimal('1'),)]),result([(1.0,)]))
        self.assertTrue(d['matches_frozen_gold']);self.assertTrue(d['native_type_sets_differ'])

    def test_numeric_mismatch_is_not_rounded_or_coerced(self):
        d=native_difference(result([(Decimal('0.1'),)]),result([(0.1,)]))
        self.assertFalse(d['matches_frozen_gold'])
        self.assertEqual(d['prediction_only_preview']['rows'],[[['decimal','0.1']]])
        self.assertEqual(d['gold_only_preview']['rows'],[[['float',(.1).hex()]]])

    def test_projection_shape_and_empty_prediction_are_explicit(self):
        d=native_difference(result([(None,None)],['a','b']),result([(None,)*6],list('abcdef')))
        self.assertFalse(d['matches_frozen_gold']);self.assertIn('column_count_differs',d['difference_codes'])
        d=native_difference(result([]),result([(2836,)]))
        self.assertIn('prediction_empty_gold_nonempty',d['difference_codes'])

    def test_two_empty_results_keep_upstream_predicate_even_if_shapes_differ(self):
        d=native_difference(result([],['a']),result([],['a','b']))
        self.assertTrue(d['matches_frozen_gold']);self.assertEqual(d['difference_codes'],[])

    def test_comparison_uses_rows_beyond_the_twenty_row_preview(self):
        p=result([(i,) for i in range(30)]);g=result([(i,) for i in range(29)]+[(999,)])
        d=native_difference(p,g)
        self.assertFalse(d['matches_frozen_gold']);self.assertEqual(d['prediction_only_tuple_count'],1)
        self.assertEqual(d['gold_only_preview']['rows'],[[['int','999']]])

    def test_difference_previews_have_both_row_and_byte_bounds(self):
        d=native_difference(result([('x'*70000,)]+[(str(i),) for i in range(20)]),result([]))
        preview=d['prediction_only_preview']
        self.assertEqual(len(preview['rows']),5);self.assertLessEqual(preview['utf8_bytes'],65536)
        self.assertEqual(preview['oversized_rows_omitted'],1);self.assertTrue(preview['preview_truncated'])

    def test_incomplete_native_results_are_never_scored(self):
        p=result([(1,)]);p.complete=False
        with self.assertRaises(ValueError):native_difference(p,result([(1,)]))


class ReviewerHintTest(unittest.TestCase):
    def test_root_null_policy_difference_is_a_hypothesis_not_a_rewrite(self):
        p='SELECT n FROM t ORDER BY v DESC LIMIT 1';g='SELECT n FROM t ORDER BY v DESC NULLS LAST LIMIT 1'
        h=reviewer_hints(p,g)
        self.assertIn('root_order_null_policy_differs',h['codes'])
        self.assertFalse(h['causes_confirmed']);self.assertEqual(p,'SELECT n FROM t ORDER BY v DESC LIMIT 1')
        self.assertEqual(h['scope'],'trusted_reviewer_only_not_model_feedback')

    def test_literal_case_where_and_related_table_differences_are_recorded(self):
        h=reviewer_hints("SELECT a.* FROM a WHERE name='strength'",
                         "SELECT a.id FROM a JOIN b ON a.id=b.id WHERE name='Strength' AND b.segment='SME'")
        self.assertIn('projection_star_vs_reference_projection',h['codes'])
        self.assertIn('referenced_tables_differ',h['codes']);self.assertIn('case_only_literal_difference',h['codes'])
        self.assertIn('segment',h['missing_where_columns']);self.assertIn('SME',h['missing_reference_literals'])

    def test_count_star_is_not_a_wildcard_output_projection(self):
        self.assertFalse(structure('SELECT COUNT(*) FROM t')['projection_star'])
        self.assertTrue(structure('SELECT t.* FROM t')['projection_star'])


class CaptureSelectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from evaluation.bird.evidence import Evidence
        root=Path('E:/PythonLearn/datasets/bird_mini_dev') if sys.platform=='win32' else BASE/'data/external/bird_mini_dev'
        cls.evidence=Evidence.load(root)
        cls.path=BASE/'evaluation/results/m2_schema_coverage_diagnostics14_server.json'

    def test_current_report_selects_exactly_ten_executed_and_four_unanswered(self):
        source,selected,excluded=load_capture(self.path,self.evidence)
        self.assertEqual(len(selected),10);self.assertEqual(len(excluded),4)
        self.assertEqual([c['case_id'] for c,g in selected],['BIRD-PG-0050','BIRD-PG-0095','BIRD-PG-1473','BIRD-PG-0036',
            'BIRD-PG-0082','BIRD-PG-1486','BIRD-PG-0159','BIRD-PG-1405','BIRD-PG-0368','BIRD-PG-0766'])
        self.assertEqual({c['case_id'] for c in excluded},{'BIRD-PG-1435','BIRD-PG-0201','BIRD-PG-1399','BIRD-PG-0586'})
        self.assertTrue(all(sql_sha(g['gold_sql'])==g['gold_sql_sha256'] for c,g in selected))

    def test_changed_source_bytes_are_rejected_before_gold_is_read(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'source.json';p.write_text('{}')
            with patch('evaluation.bird.replay.scorer_gold',side_effect=AssertionError('No Gold read')):
                with self.assertRaises(ValueError):load_capture(p,self.evidence)

    def test_nested_scope_and_sql_integrity_checks_fail_closed(self):
        original=json.loads(self.path.read_bytes())
        changes=[lambda r:r['cases'][0].update(case_id='BIRD-PG-1028'),
                 lambda r:r['cases'][0].update(generated_sql=r['cases'][0]['generated_sql']+' '),
                 lambda r:r['cases'][0].update(database_id='foreign'),
                 lambda r:r['cases'][0].update(status='clarification'),
                 lambda r:r['cases'].pop()]
        for mutate in changes:
            with self.subTest(mutate=mutate),tempfile.TemporaryDirectory() as folder:
                row=deepcopy(original);mutate(row);p=Path(folder)/'source.json';p.write_text(json.dumps(row),encoding='utf-8')
                # Bypass only checksum inside this test to exercise the remaining gates.
                with patch('evaluation.bird.replay.digest_file',return_value=SOURCE_SHA),\
                     patch('evaluation.bird.replay.scorer_gold',side_effect=AssertionError('No Gold read')):
                    with self.assertRaises(ValueError):load_capture(p,self.evidence)


class ReplayLifecycleTest(unittest.TestCase):
    def test_exact_captured_sql_executes_without_generation_or_rewriting(self):
        runtime,case,gold,calls=fixture()
        with patch('evaluation.bird.model.ModelConfig.load',side_effect=AssertionError('No config/model')):
            record=replay_case(runtime,case,gold)
        self.assertEqual(calls,[case['generated_sql'],gold['gold_sql']])
        self.assertEqual(record['generated_sql_sha256'],sql_sha(case['generated_sql']))
        self.assertEqual(record['budget']['sql_tool_calls'],2);self.assertEqual(record['budget']['model_http_attempts'],0)
        self.assertFalse(record['native_comparison']['matches_frozen_gold'])
        self.assertTrue(record['captured_native_diagnostic_preserved'])

    def test_changed_replay_result_is_flagged_without_fabricating_old_values(self):
        runtime,case,gold,calls=fixture();case['result']=result([(999,)]).diagnostic()
        record=replay_case(runtime,case,gold)
        self.assertFalse(record['captured_native_diagnostic_preserved'])
        self.assertEqual(record['results']['captured_generated']['preview']['rows'],[[['int','1']]])

    def test_wrong_runtime_and_modified_gold_fail_before_queries(self):
        for change in ('source','gold'):
            runtime,case,gold,calls=fixture()
            if change=='source':case['source_identity']={'logical_database_id':'other'}
            else:gold['gold_sql']+=' '
            with self.subTest(change=change),self.assertRaises(ValueError):replay_case(runtime,case,gold)
            self.assertEqual(calls,[])

    def test_gold_timeout_preserves_prediction_and_partial_budget(self):
        runtime,case,gold,calls=fixture();original=runtime.execute_native
        def execute(sql,budget):
            if len(calls)==1:raise BirdFailure('sql_timeout','57014')
            return original(sql,budget)
        runtime.execute_native=execute;record={}
        with self.assertRaises(BirdFailure):replay_case(runtime,case,gold,progress=record)
        self.assertEqual(record['status'],'failed');self.assertEqual(record['budget']['sql_tool_calls'],2)
        self.assertTrue(record['gold_execution_attempted']);self.assertFalse(record['gold_executed'])
        self.assertIn('captured_generated',record['results']);self.assertNotIn('native_comparison',record)

    def test_incomplete_gold_cannot_become_a_match(self):
        incomplete=result([(1,)]);incomplete.complete=False
        runtime,case,gold,calls=fixture(gold_result=incomplete)
        with self.assertRaises(ValueError):replay_case(runtime,case,gold)

    def run_registry(self,fail=False):
        runtime,case,gold,calls=fixture()
        if fail:runtime.execute_native=lambda *args:(_ for _ in ()).throw(BirdFailure('sql_timeout'))
        class Registry:
            def __init__(self,*args):self._runtimes={}
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
            def get(self,db):self._runtimes[db]=runtime;return runtime
            def close(self):runtime.connections.closed=True
        source={'cases':[case,{}],'code_binding':{'sha256':'producer'}};report={};caught=None
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'source.json';p.write_text('{}')
            with patch('evaluation.bird.replay.load_capture',return_value=(source,[(case,gold)],[{'case_id':'excluded'}])),\
                 patch('evaluation.bird.replay.source_binding',return_value={}),\
                 patch('evaluation.bird.replay.code_binding',return_value={'sha256':'reviewer'}),\
                 patch('evaluation.bird.replay.hard_deadline'):
                try:run_replay(None,p,p,report,registry_factory=Registry)
                except BirdFailure as error:caught=error
        return report,caught

    def test_registry_records_mismatch_and_exclusions_and_closes(self):
        report,error=self.run_registry()
        self.assertIsNone(error);self.assertEqual(report['run_status'],'complete');self.assertTrue(report['pools_closed'])
        self.assertTrue(report['gold_executed']);self.assertEqual(report['summary']['native_mismatch_count'],1)
        self.assertEqual(report['summary']['excluded_case_count'],1);self.assertIsNone(report['summary']['formal_ex_denominator'])
        self.assertEqual(len(report['fixed_error_list']),1);self.assertFalse(report['holdout_live_allowed'])

    def test_registry_failure_closes_and_keeps_partial_case_without_false_complete(self):
        report,error=self.run_registry(fail=True)
        self.assertEqual(error.category,'sql_timeout');self.assertTrue(report['pools_closed'])
        self.assertFalse(report['gold_executed']);self.assertNotEqual(report.get('run_status'),'complete')
        self.assertEqual(report['cases'][0]['budget']['sql_tool_calls'],1)


if __name__=='__main__':unittest.main()
