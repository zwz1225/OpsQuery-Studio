"""Offline orchestration gates. No PostgreSQL, API key, or model requests."""
from contextlib import nullcontext
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch, Mock

from scripts import run_m2_v4_development80 as workflow
from scripts.m2_b_common import PreparationError, digest_file


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.args = workflow.parser().parse_args(['--output', str(root/'status.json')])
        self.args.results_dir = root
        self.args.diagnostic_output = root/'capture.json'
        self.args.native_output = root/'native.json'
        self.args.data_root = root/'source'
        self.args.credentials_file = root/'private.json'
        self.args.model_config_file = root/'model.env'
        self.args.index_root = root/'indexes'
        self.ids = [f'dev-{i:02}' for i in range(80)]
        self.accepted = dict(code_binding={'sha256': 'fixed'}, model_configuration={'chat': 'fixed'},
            schema_selection_policy={'coverage_enabled': True}, sql_repair_policy='fixed')
        self.pairs = [({'case_id': cid}, {}) for cid in self.ids[:76]]
        self.excluded = [{'case_id': cid, 'counted_as_success': False} for cid in self.ids[76:]]

    def test_existing_outputs_are_preserved_even_in_check_only(self):
        self.args.check_only = True
        self.args.native_output.write_text('prior evidence')
        with self.assertRaisesRegex(PreparationError, 'new output'):
            workflow.paths(self.args)
        self.assertEqual(self.args.native_output.read_text(), 'prior evidence')

    def test_output_collisions_and_protected_paths_are_rejected(self):
        self.args.native_output = self.args.diagnostic_output
        with self.assertRaisesRegex(PreparationError, 'distinct'):
            workflow.paths(self.args)
        self.args.native_output = self.args.results_dir/workflow.ACCEPTED_NATIVE
        with self.assertRaisesRegex(PreparationError, 'protected'):
            workflow.paths(self.args)

    def test_outputs_cannot_escape_results_directory(self):
        self.args.native_output = self.args.results_dir.parent/'elsewhere.json'
        with self.assertRaisesRegex(PreparationError, 'within results'):
            workflow.paths(self.args)

    def test_replay_only_requires_existing_capture_but_new_native(self):
        self.args.replay_only = True
        with self.assertRaisesRegex(PreparationError, 'existing complete'):
            workflow.paths(self.args)
        self.args.diagnostic_output.write_text('{}')
        workflow.paths(self.args)
        self.args.native_output.write_text('{}')
        with self.assertRaisesRegex(PreparationError, 'new output'):
            workflow.paths(self.args)

    def capture(self):
        return dict(selected_case_ids=self.ids, cases=[{}]*80, case_list_sha256=workflow.CASE_LIST_SHA,
            workers=1, intent_candidate_policy=workflow.policy(),
            **{k: v for k, v in self.accepted.items() if k != 'code_binding'})

    def test_exact80_gate_retains_nonanswers_in_denominator(self):
        self.args.diagnostic_output.write_text('{}')
        with patch.object(workflow, 'load_candidate_capture', return_value=(self.capture(), self.pairs, self.excluded)):
            sha, pairs, excluded = workflow.complete_capture(self.args.diagnostic_output, object(), self.ids, self.accepted)
        self.assertEqual(sha, digest_file(self.args.diagnostic_output))
        self.assertEqual((len(pairs), len(excluded)), (76, 4))

    def test_missing_cases_order_and_changed_settings_are_rejected(self):
        self.args.diagnostic_output.write_text('{}')
        mutations = [lambda r: r.update(cases=[{}]*79),
                     lambda r: r.update(selected_case_ids=list(reversed(self.ids))),
                     lambda r: r.update(model_configuration={'chat': 'different'}),
                     lambda r: r.update(schema_selection_policy={'coverage_enabled': False}),
                     lambda r: r.update(workers=2), lambda r: r.update(case_list_sha256='changed')]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                row = self.capture()
                mutate(row)
                with patch.object(workflow, 'load_candidate_capture', return_value=(row, self.pairs, self.excluded)):
                    with self.assertRaises(PreparationError):
                        workflow.complete_capture(self.args.diagnostic_output, object(), self.ids, self.accepted)

    def test_original_loader_rejects_running_capture_before_replay(self):
        self.args.diagnostic_output.write_text(json.dumps({'run_status': 'running'}))
        with self.assertRaisesRegex(PreparationError, 'termination differs'):
            workflow.complete_capture(self.args.diagnostic_output, object(), self.ids, self.accepted)

    def setup_run(self):
        preflight = patch.object(workflow, 'preflight', return_value=(object(), self.ids, self.accepted)).start()
        self.addCleanup(patch.stopall)
        patch.object(workflow, 'exclusive_run', return_value=nullcontext()).start()
        return preflight

    def test_check_only_does_not_start_any_child(self):
        self.setup_run()
        self.args.check_only = True
        with patch.object(workflow, 'child') as child:
            report = {}
            workflow.run(self.args, report)
        child.assert_not_called()
        self.assertEqual(report['phase'], 'preflight_only')
        self.assertFalse(report['live_readiness_verified'])
        self.assertEqual(report['new_model_request_count'], 0)

    def test_failed_generation_never_starts_replay(self):
        self.setup_run()
        with patch.object(workflow, 'child', side_effect=PreparationError('generation failed')) as child:
            with patch.object(workflow, 'complete_capture') as capture:
                with self.assertRaises(PreparationError):
                    workflow.run(self.args, {})
        self.assertEqual(child.call_count, 1)
        self.assertEqual(child.call_args.args[1], 'evaluation.bird.diagnostic_runner')
        capture.assert_not_called()

    def test_zero_exit_with_incomplete_capture_never_starts_replay(self):
        self.setup_run()
        with patch.object(workflow, 'child') as child:
            with patch.object(workflow, 'complete_capture', side_effect=PreparationError('incomplete')):
                with self.assertRaises(PreparationError):
                    workflow.run(self.args, {})
        self.assertEqual(child.call_count, 1)

    def test_replay_only_uses_hash_of_complete_report_without_generation(self):
        self.setup_run()
        self.args.replay_only = True
        self.args.diagnostic_output.write_text('complete capture bytes')
        sha = digest_file(self.args.diagnostic_output)
        with patch.object(workflow, 'complete_capture', return_value=(sha, self.pairs, self.excluded)):
            with patch.object(workflow, 'child') as child:
                with patch.object(workflow, 'complete_native', return_value={'source_case_count': 80}):
                    self.args.native_output.write_text('native bytes')
                    report = {}
                    workflow.run(self.args, report)
        self.assertEqual(child.call_count, 1)
        options = child.call_args.args[2]
        self.assertEqual(options[options.index('--source-sha256')+1], sha)
        self.assertEqual(report['run_status'], 'complete')

    def test_replay_cannot_silently_change_capture(self):
        self.setup_run()
        self.args.replay_only = True
        self.args.diagnostic_output.write_text('original')
        sha = digest_file(self.args.diagnostic_output)
        def change(*unused):
            self.args.diagnostic_output.write_text('changed')
        with patch.object(workflow, 'complete_capture', return_value=(sha, self.pairs, self.excluded)):
            with patch.object(workflow, 'child', side_effect=change):
                with self.assertRaisesRegex(PreparationError, 'changed during replay'):
                    workflow.run(self.args, {})

    def native(self):
        return dict(run_status='complete', errors=[], native_comparisons_complete=True, pools_closed=True,
            target_data_verified=True, source_report_sha256='capture-sha', code_binding={}, source_binding={},
            formal_benchmark=False, primary_ex=None, holdout_live_allowed=False, new_model_request_count=0,
            selected_case_ids=self.ids[:76], excluded_cases=self.excluded, source_case_count=80,
            cases=[{'case_id': cid, 'native_comparison': {'matches_frozen_gold': i < 49}}
                   for i, cid in enumerate(self.ids[:76])],
            summary=dict(source_case_count=80, development_subset_case_count=80, replayed_case_count=76,
                excluded_case_count=4, new_model_request_count=0, native_match_count=49,
                native_mismatch_count=27, development_subset_native_match_rate=49/80))

    def verify_native(self, row):
        self.args.native_output.write_text(json.dumps(row))
        with patch.object(workflow, 'code_binding', return_value={}):
            with patch.object(workflow, 'source_binding', return_value={}):
                return workflow.complete_native(self.args.native_output, 'capture-sha', self.pairs, self.excluded, object())

    def test_native_denominator_counts_nonanswers_as_failures(self):
        self.assertEqual(self.verify_native(self.native())['development_subset_native_match_rate'], 0.6125)

    def test_native_incomplete_wrong_source_and_inflated_score_rejected(self):
        mutations = [lambda r: r.update(run_status='running'), lambda r: r.update(pools_closed=False),
            lambda r: r.update(source_report_sha256='different'), lambda r: r.update(code_binding={'changed': True}),
            lambda r: r.update(new_model_request_count=1), lambda r: r.update(cases=r['cases'][:-1]),
            lambda r: r['summary'].update(native_match_count=50),
            lambda r: r['summary'].update(development_subset_case_count=76),
            lambda r: r['summary'].update(development_subset_native_match_rate=49/76)]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                row = self.native()
                mutate(row)
                with self.assertRaises(PreparationError):
                    self.verify_native(row)

    def test_child_uses_current_python_argv_without_shell_or_secret(self):
        with patch.object(workflow.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as call:
            report = {}
            workflow.child(self.args, 'scripts.rescore_m2_intent_candidate', ['--source-sha256', 'abc'], report, 'native_replay')
        argv = call.call_args.args[0]
        self.assertEqual(argv[:4], [workflow.sys.executable, '-u', '-m', 'scripts.rescore_m2_intent_candidate'])
        self.assertNotIn('shell', call.call_args.kwargs)
        self.assertNotIn('--model-config-file', argv)
        self.assertEqual(report['child_exit_codes'], {'native_replay': 0})

    def test_child_nonzero_exit_is_not_success(self):
        with patch.object(workflow.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)):
            with self.assertRaisesRegex(PreparationError, 'failed'):
                workflow.child(self.args, 'example', [], {}, 'generation')


class AcceptedEvidenceTest(unittest.TestCase):
    def test_static_preflight_against_reviewed_evidence_without_secrets_or_connections(self):
        args = workflow.parser().parse_args(['--output', str(workflow.DEFAULT_RESULTS/'unused_workflow_test.json')])
        accepted = workflow.read(workflow.DEFAULT_RESULTS/workflow.ACCEPTED_CAPTURE)
        # Only host metadata differs on Windows; execution bytes must still match.
        self.assertEqual(workflow.code_binding()['files'], accepted['code_binding']['files'])
        with tempfile.TemporaryDirectory() as directory:
            args.credentials_file = Path(directory)/'private.json'
            args.credentials_file.write_text('not read by static preflight')
            with patch.object(workflow, 'live_dependencies'):
                with patch.object(workflow, 'code_binding', return_value=accepted['code_binding']):
                    with patch('evaluation.bird.intent_replay.code_binding', return_value=accepted['code_binding']):
                        config = Mock()
                        config.public.return_value = accepted['model_configuration']
                        with patch.object(workflow.ModelConfig, 'load', return_value=config) as load:
                            _, ids, _ = workflow.preflight(args)
                            self.assertEqual(len(ids), 80)
                            args.replay_only = True
                            load.reset_mock()
                            workflow.preflight(args)
                            load.assert_not_called()


if __name__ == '__main__':
    unittest.main()
