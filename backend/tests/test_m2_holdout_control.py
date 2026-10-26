"""Offline holdout contract, native scoring, budget and durable attempt tests."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from scripts import m2_holdout_control as control
from scripts import m2_holdout_worker as worker
from scripts import run_m2_holdout30 as runner
from scripts.m2_b_common import PreparationError, digest_file, digest_json
from evaluation.bird.budgets import Budget, BirdFailure
from evaluation.bird.native import NativeResult, encoded, tagged


class FreezeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'candidate.json'
        with patch.object(control, 'LEDGER_ROOT', Path(self.temp.name)/'ledger'):
            self.row = control.build_candidate()
        self.path.write_text(json.dumps(self.row), encoding='utf-8')

    def checked(self):
        with patch.object(control, 'code_binding', return_value=self.row['payload']['producer_binding']):
            return control.candidate(self.path)

    def save_changed(self, change):
        change(self.row['payload'])
        self.row['candidate_sha256'] = digest_json(self.row['payload'])
        self.row['candidate_id'] = 'm2_v4_'+self.row['candidate_sha256']
        self.path.write_text(json.dumps(self.row), encoding='utf-8')

    def test_reviewed_candidate_freezes_without_opening_gold_or_secrets(self):
        row = self.checked()
        self.assertEqual(row['payload']['scoring']['primary_denominator'], 30)
        self.assertFalse(row['payload']['holdout_results_observed_before_freeze'])
        self.assertEqual(len(row['payload']['producer_binding']['files']), 96)
        self.assertEqual(row['payload']['source_binding']['budgets'], row['payload']['budgets'])
        serialized = json.dumps(row)
        self.assertNotIn('api_key', serialized)
        self.assertNotIn('gold_sql', serialized.replace('gold_sql_calls_per_answer', ''))

    def test_digest_change_is_rejected(self):
        row = json.loads(self.path.read_text())
        row['payload']['holdout_case_count'] = 29
        self.path.write_text(json.dumps(row))
        with self.assertRaisesRegex(PreparationError, 'digest'):
            self.checked()

    def test_recomputed_manifest_cannot_relax_scoring(self):
        self.save_changed(lambda p: p['scoring'].update(primary_denominator=29))
        with self.assertRaisesRegex(PreparationError, 'contract'):
            self.checked()

    def test_recomputed_manifest_cannot_change_controller_bytes(self):
        self.save_changed(lambda p: p['controller_files'].update({'scripts/m2_holdout_worker.py': '0'*64}))
        with self.assertRaisesRegex(PreparationError, 'controller'):
            self.checked()

    def test_dependency_or_host_change_is_rejected(self):
        with patch.object(control, 'code_binding', return_value={'different': True}):
            with self.assertRaisesRegex(PreparationError, 'host identity'):
                control.candidate(self.path)

    def test_refreeze_after_attempt_is_not_described_as_unseen_holdout(self):
        root = Path(self.temp.name)/'ledger'
        root.mkdir()
        (root/'old_attempt').mkdir()
        with patch.object(control, 'LEDGER_ROOT', root):
            with self.assertRaisesRegex(PreparationError, 'disclose reuse'):
                control.build_candidate()


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.row = dict(candidate_id='m2_v4_'+'a'*64, candidate_sha256='a'*64)

    def test_only_one_concurrent_reservation_can_win(self):
        def reserve(_):
            try:
                return control.reserve(self.row, self.root)
            except PreparationError:
                return None
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(reserve, range(8)))
        self.assertEqual(sum(v is not None for v in results), 1)

    def test_crash_after_directory_creation_still_consumes_attempt(self):
        (self.root/self.row['candidate_id']).mkdir()
        with self.assertRaisesRegex(PreparationError, 'registered attempt'):
            control.reserve(self.row, self.root)

    def test_hash_linked_events_and_case_artifacts_are_verified(self):
        attempt = control.reserve(self.row, self.root)
        attempt.gold(dict(case_id='BIRD-PG-0001', status='gold_ready'))
        attempt.case(dict(case_id='BIRD-PG-0001', status='scored', ex_correct=False))
        attempt.event('completed', primary_ex=0)
        summary = control.verify_ledger(attempt.path)
        self.assertEqual(summary['event_count'], 4)
        self.assertEqual(summary['last_event'], 'completed')
        (attempt.path/'cases/BIRD-PG-0001.json').write_text('{}')
        with self.assertRaisesRegex(PreparationError, 'artifact changed'):
            control.verify_ledger(attempt.path)

    def test_failed_attempt_is_preserved_and_not_reusable(self):
        attempt = control.reserve(self.row, self.root)
        attempt.event('failed_or_interrupted', saved_case_count=0)
        with self.assertRaises(PreparationError):
            control.reserve(self.row, self.root)
        self.assertEqual(control.verify_ledger(attempt.path)['last_event'], 'failed_or_interrupted')

    def test_overwriting_a_case_or_event_is_rejected(self):
        attempt = control.reserve(self.row, self.root)
        case = dict(case_id='BIRD-PG-0001', status='scored')
        attempt.case(case)
        with self.assertRaises(FileExistsError):
            attempt.case(case)

    def test_deleted_or_tampered_event_is_detected(self):
        attempt = control.reserve(self.row, self.root)
        attempt.event('probes_passed')
        event = attempt.path/'0002_probes_passed.json'
        row = control.read(event)
        row['previous_event_sha256'] = 'wrong'
        event.write_text(json.dumps(row))
        with self.assertRaisesRegex(PreparationError, 'chain'):
            control.verify_ledger(attempt.path)


def native(rows, columns=None, complete=True):
    columns = columns or ['value']
    size = len(encoded({'columns': columns}))+sum(len(encoded([tagged(v) for v in row]))+1 for row in rows)
    return NativeResult(columns, rows, size, complete)


class WorkerTest(unittest.TestCase):
    def setUp(self):
        self.request = dict(input=dict(case_id='BIRD-PG-0001', database_id='test'), gold={'gold_sql': 'GOLD'},
            candidate_sha256='frozen', receipt={}, data_root='source', results_dir='results', credentials_file='private',
            index_path='index', code_sha256='code', model_config_private={'api_key': 'private-key'})
        self.frozen = dict(candidate_sha256='frozen')
        self.gold = dict(case_id='BIRD-PG-0001', database_id='test', gold_sql='GOLD', gold_sql_sha256='goldhash')
        self.prediction = native([(Decimal('1.23456'),)])
        self.reference = self.prediction
        self.budget = Budget()
        self.budget.model_attempt('chat')
        self.calls = []
        test = self

        class FakeRuntime:
            def __init__(self, *args, **kwargs):
                self.connections = NS(closed=False)
                self.identity = NS(public=lambda: {'source': 'same'})
                self.domain = {'query_role': 'readonly'}
                self.evidence = NS(manifest={}, validation={'initialization_id': 'init'})

            def execute_native(self, sql, budget=None, *, validate_only=False):
                test.calls.append(sql)
                test.assertIs(budget, test.budget)
                return test.reference if sql == 'GOLD' else test.prediction

            def close(self):
                self.connections.closed = True

        self.runtime_class = FakeRuntime

    def generation(self, request):
        self.assertNotIn('gold', request)
        self.assertNotIn('candidate_sha256', request)
        self.assertNotIn('difficulty', request['input'])
        self.assertEqual(request['mode'], 'diagnostic')
        self.assertTrue(request['schema_coverage_enabled'] and request['intent_candidate_enabled'])
        runtime = worker.case_worker.BirdRuntime()
        self.budget.sql_call()
        result = runtime.execute_native('PREDICTED', self.budget)
        runtime.close()
        self.calls.append('AGENT_EXITED')
        return dict(case_id='BIRD-PG-0001', database_id='test', mode='diagnostic', status='diagnostic_answered',
            complete=True, result=result.diagnostic(), generated_sql='PREDICTED', runtime_closed=True,
            source_identity={'source': 'same'}, errors=[], budget=self.budget.public(), new_model_request_count=1)

    def execute(self, generation=None):
        with patch.object(worker, 'checked_request', return_value=(self.frozen, self.gold)):
            with patch.object(worker, 'candidate', return_value=self.frozen):
                with patch.object(worker.case_worker, 'BirdRuntime', self.runtime_class):
                    with patch.object(worker.case_worker, 'execute', side_effect=generation or self.generation):
                        with patch('scripts.m2_b_target.load_credentials', return_value={'passwords': {'readonly': 'private'}}):
                            with patch.object(worker, 'hard_deadline', return_value=nullcontext()):
                                result = worker.execute(self.request)
                        self.assertIs(worker.case_worker.BirdRuntime, self.runtime_class)
        return result

    def test_gold_stays_out_of_generation_and_runs_after_agent_exit(self):
        report = self.execute()
        self.assertEqual(self.calls, ['PREDICTED', 'AGENT_EXITED', 'GOLD'])
        self.assertTrue(report['ex_correct'])
        self.assertEqual(report['status'], 'scored')
        self.assertEqual(report['new_model_request_count'], 1)
        self.assertEqual(report['budget']['sql_tool_calls'], 1)
        self.assertTrue(report['scorer_runtime_closed'])

    def test_native_values_are_compared_before_json_without_rounding(self):
        self.reference = native([(Decimal('1.23457'),)])
        report = self.execute()
        self.assertFalse(report['ex_correct'])
        self.assertEqual(report['native_results']['prediction']['preview']['rows'][0][0], ['decimal', '1.23456'])

    def test_column_position_is_not_relaxed(self):
        self.prediction = native([('name', 'address')], ['name', 'address'])
        self.reference = native([('address', 'name')], ['address', 'name'])
        self.assertFalse(self.execute()['ex_correct'])

    def test_row_order_and_duplicate_multiplicity_follow_frozen_set_semantics(self):
        self.prediction = native([(1,), (2,), (2,)])
        self.reference = native([(2,), (1,)])
        report = self.execute()
        self.assertTrue(report['ex_correct'])
        self.assertFalse(report['result_diagnostics']['ordered_rows_match'])
        self.assertFalse(report['result_diagnostics']['row_multiset_match'])

    def test_preview_or_partial_prediction_never_scores(self):
        self.prediction = native([(1,)], complete=False)
        report = self.execute()
        self.assertFalse(report['ex_correct'])
        self.assertNotIn('GOLD', self.calls)

    def test_partial_gold_never_scores(self):
        self.reference = native([(1,)], complete=False)
        report = self.execute()
        self.assertFalse(report['ex_correct'])
        self.assertFalse(report['complete'])
        self.assertTrue(report['scorer_runtime_closed'])

    def test_exhausted_generation_budget_does_not_get_a_second_scoring_window(self):
        def exhausted(request):
            result = self.generation(request)
            self.budget.started -= 601
            return result
        report = self.execute(exhausted)
        self.assertFalse(report['ex_correct'])
        self.assertEqual(report['status'], 'case_wall_timeout')
        self.assertNotIn('GOLD', self.calls)

    def test_clarification_counts_as_failure_without_gold_query(self):
        report = self.execute(lambda request: dict(case_id='BIRD-PG-0001', database_id='test', mode='diagnostic',
            status='clarification', complete=False, errors=[], new_model_request_count=1, runtime_closed=True))
        self.assertFalse(report['ex_correct'])
        self.assertEqual(report['status'], 'clarification')
        self.assertEqual(self.calls, [])

    def test_only_original_frozen_holdout_public_input_is_admitted(self):
        self.request['input']['question'] = 'changed'
        with patch.object(worker, 'candidate', return_value={'candidate_sha256': 'frozen'}):
            with patch.object(worker, 'public_cases', return_value=[dict(case_id='BIRD-PG-0001', database_id='test')]):
                with self.assertRaisesRegex(PreparationError, 'exact frozen'):
                    worker.checked_request(self.request)


class SummaryTest(unittest.TestCase):
    def report(self):
        cases = [dict(case_id=f'BIRD-PG-{i:04}', database_id='db', status='scored' if i < 20 else 'clarification',
            complete=i < 20, ex_correct=i < 15, errors=[], new_model_request_count=3,
            budget={'sql_tool_calls': 1}, gold_execution_attempted=i < 20, case_wall_seconds=1) for i in range(30)]
        return dict(cases=cases, selected_case_ids=[c['case_id'] for c in cases], index_builds=[], gold_readiness_cases=[{}]*30)

    def metadata(self, report):
        return {c['case_id']: {'difficulty': ('simple', 'moderate', 'challenging')[i % 3]}
                for i, c in enumerate(report['cases'])}

    def test_failures_and_clarifications_stay_in_fixed30_denominator(self):
        report = self.report()
        runner.finish_summary(report, self.metadata(report))
        self.assertEqual(report['primary_ex'], 15/30)
        self.assertEqual(report['summary']['complete_result_count'], 20)
        self.assertEqual(report['summary']['ex_given_complete_results'], 15/20)

    def test_killed_worker_usage_is_unknown_not_zero(self):
        report = self.report()
        report['cases'][-1]['new_model_request_count'] = None
        runner.finish_summary(report, self.metadata(report))
        self.assertIsNone(report['new_model_request_count'])
        self.assertTrue(report['summary']['model_attempt_count_incomplete'])

    def test_missing_or_reordered_cases_cannot_complete(self):
        for mutation in (lambda r: r['cases'].pop(), lambda r: r['cases'].reverse()):
            report = self.report()
            metadata = self.metadata(report)
            mutation(report)
            with self.assertRaisesRegex(PreparationError, 'all30'):
                runner.finish_summary(report, metadata)


class FrozenPipelineIntegrationTest(unittest.TestCase):
    def test_actual_v4_worker_and_agent_prompts_repairs_and_budgets_are_unchanged(self):
        import importlib
        import sys
        from test_m2_intent_candidate import context, field, public
        with patch.dict(sys.modules, {'resource': NS()}):
            agent_module = importlib.import_module('evaluation.bird.isolated_agent')
        catalog_runtime = context()
        catalog_runtime.catalog.tables[0]['fields'].append(field('attribute_name'))
        original_sql = "SELECT id FROM items WHERE attribute_name='strength' ORDER BY score DESC LIMIT 1"
        fixed_sql = original_sql.replace('DESC', 'DESC NULLS LAST').replace("'strength'", "'Strength'")
        public_input = public('Highest strength', "attribute_name='strength'")
        source = NS(domain=lambda db: {'query_role': 'ro'}, validation={'initialization_id': 'unit'}, manifest={})
        ids = ['db.items.id', 'db.items.score', 'db.items.attribute_name']
        schema = dict(graph={'fields': [{'id': name} for name in ids]}, retrieval={'selected_field_ids': ids},
            index_sha256='unit', _intent_selection=dict(baseline_field_ids=ids, sample_condition_candidates=[]))
        gold = dict(case_id=public_input['case_id'], database_id='db', gold_sql='GOLD', gold_sql_sha256='gold')
        frozen = {'candidate_sha256': 'frozen'}
        def run(adapted):
            calls, prompts = [], []
            choices = [dict(action='query', sql=original_sql), dict(action='query', sql=fixed_sql)]
            class Runtime:
                identity = catalog_runtime.identity
                catalog = catalog_runtime.catalog
                domain = {'query_role': 'ro'}
                evidence = source
                def __init__(self, *a, **kw):
                    self.connections = NS(closed=False)
                def __getattr__(self, name):
                    return getattr(catalog_runtime, name)
                def execute_native(self, sql, budget, *, validate_only=False):
                    calls.append((sql, validate_only))
                    if 'canonical_value' in sql:
                        return NativeResult(['probe_id', 'value'], [(0, 'Strength')], 64)
                    return {'valid': True} if validate_only else NativeResult(['id'], [(7,)], 64)
                def close(self):
                    self.connections.closed = True
            class Models:
                def __init__(self, config, budget):
                    self.budget = budget
                def chat(self, system, user):
                    self.budget.model_attempt('chat', prompt=(system+user).encode())
                    prompts.append((system, json.loads(user)))
                    return choices.pop(0)
            class Agent:
                isolation = {'unit': 'fake'}
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    calls.append(('AGENT_EXITED', False))
                def run(self, ctx, handler, *args):
                    with patch.object(agent_module, 'rpc', side_effect=lambda op, **msg: handler(op, msg)):
                        return agent_module.answer(ctx)
            request = dict(mode='diagnostic', input=public_input, schema_coverage_enabled=True,
                intent_candidate_enabled=True, code_sha256='unit', data_root='.', results_dir='.',
                credentials_file='private', receipt={}, index_path='index',
                model_config_private={'api_key': 'SECRET_API_KEY'}, gold=gold, candidate_sha256='frozen')
            with patch.multiple(worker.case_worker, code_binding=Mock(return_value={'sha256': 'unit'}),
                BirdRuntime=Runtime, IsolatedAgent=Agent, load_credentials=Mock(return_value={'passwords': {'ro': 'SECRET_PASSWORD'}})):
                with patch.object(worker.case_worker.Evidence, 'load', return_value=source):
                    with patch('evaluation.bird.model.Models', Models):
                        with patch('evaluation.bird.retrieval.retrieve', return_value=deepcopy(schema)):
                            with patch.object(worker, 'checked_request', return_value=(frozen, gold)):
                                with patch.object(worker, 'candidate', return_value=frozen):
                                    with patch('scripts.m2_b_target.load_credentials', return_value={'passwords': {'ro': 'SECRET_PASSWORD'}}):
                                        with patch.object(worker, 'hard_deadline', return_value=nullcontext()):
                                            report = worker.execute(request) if adapted else worker.case_worker.execute(request)
            return report, calls, prompts
        original, old_calls, old_prompts = run(False)
        adapted, new_calls, new_prompts = run(True)
        self.assertEqual(original['status'], 'diagnostic_answered')
        self.assertEqual(adapted['status'], 'scored')
        self.assertTrue(adapted['ex_correct'])
        self.assertEqual(old_prompts, new_prompts)
        self.assertEqual(new_calls, old_calls+[('GOLD', False)])
        self.assertEqual(new_calls[-2], ('AGENT_EXITED', False))
        for key in ('generated_sql', 'canonical_lookup', 'intent_contract', 'retrieval',
                    'validation_events', 'executions', 'development_diagnostics'):
            self.assertEqual(original[key], adapted[key], key)
        for key in ('model_http_attempts', 'chat_http_attempts', 'sql_tool_calls',
                    'validation_attempts', 'generation_attempts', 'model_events'):
            self.assertEqual(original['budget'][key], adapted['budget'][key], key)
        for secret in ('SECRET_API_KEY', 'SECRET_PASSWORD', 'GOLD', 'gold_sql'):
            self.assertNotIn(secret, json.dumps(new_prompts))


class SupervisorTest(unittest.TestCase):
    def test_deadline_failure_kills_owned_session_and_closes_pipes(self):
        process = Mock(pid=12345, returncode=0)
        channel = Mock()
        channel.receive.side_effect = BirdFailure('case_wall_timeout')
        with patch.object(worker.sys, 'platform', 'linux'):
            with patch.object(worker.signal, 'SIGKILL', 9, create=True):
                with patch.object(worker.subprocess, 'Popen', return_value=process) as launch:
                    with patch.object(worker, 'Channel', return_value=channel):
                        with patch.object(worker.os, 'killpg', create=True) as kill:
                            with self.assertRaisesRegex(BirdFailure, 'case_wall_timeout'):
                                worker.run_process({'private': 'pipe only'}, seconds=600)
        kill.assert_called_once_with(12345, 9)
        process.stdin.close.assert_called_once()
        process.stdout.close.assert_called_once()
        self.assertTrue(launch.call_args.kwargs['start_new_session'])
        self.assertTrue(launch.call_args.kwargs['close_fds'])
        self.assertNotIn('LLM_API_KEY', launch.call_args.kwargs['env'])
        self.assertNotIn('PG_PASSWORD', launch.call_args.kwargs['env'])


class ReadinessGateTest(unittest.TestCase):
    def test_failed_gold_is_saved_and_blocks_all_index_and_agent_calls(self):
        public = dict(case_id='BIRD-PG-0001', database_id='db')
        gold = dict(gold_sql_sha256='gold')
        report = {}
        args = NS(output=Path('unused.json'), data_root=Path('data'), credentials_file=Path('private'),
                  index_root=Path('indexes'))
        frozen = dict(candidate_id='fixed', candidate_sha256='sha',
            payload=dict(scope='project', producer_binding={'sha256': 'producer'},
                controller_files={}, intent_candidate_policy={}, scoring={}))
        attempt = Mock(id='attempt', path=Path('ledger'))
        runtime = Mock()
        runtime.receipt.return_value = dict(database_id='db', live_target_verified=True)
        registry = Mock()
        registry.__enter__ = Mock(return_value=registry)
        registry.__exit__ = Mock(return_value=False)
        registry.get.return_value = runtime
        evidence = NS(manifest={'question_relative_path': 'questions.json'})
        def dispatch(request, *, seconds):
            if request['mode'] == 'watchdog_probe':
                raise BirdFailure('case_wall_timeout')
            return dict(case_id=public['case_id'], database_id='db', mode='gold', status='sql_error', complete=False)
        with patch.multiple(runner, public_cases=Mock(return_value=[public]*30),
            scorer_gold=Mock(return_value={public['case_id']: gold}),
            budget_checks=Mock(return_value=[]), isolation_probe=Mock(return_value={}),
            checkpoint=Mock(), source_binding=Mock(return_value={}), digest_file=Mock(return_value='hash'),
            run_case_process=Mock(side_effect=dispatch), BirdRegistry=Mock(return_value=registry)):
            with patch.object(control, 'read', return_value={'case_ids': [public['case_id']]*30,
                                                            'selection_metadata': [{'case_id': public['case_id']}] } ):
                with patch.object(runner, 'build_index') as index:
                    with patch.object(runner, 'run_process') as agent:
                        with self.assertRaisesRegex(PreparationError, 'Gold readiness failed'):
                            runner.registered_run(args, frozen, evidence, Mock(public=lambda: {}), attempt, report)
        attempt.gold.assert_called_once()
        self.assertEqual(len(report['gold_readiness_cases']), 1)
        index.assert_not_called()
        agent.assert_not_called()


if __name__ == '__main__':
    unittest.main()
