"""Offline preparation, ordering, identity, finite retry and pair-summary tests."""
from contextlib import nullcontext
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from scripts import m3_pair_common as c
from scripts import prepare_m3_e01_pair24 as prepare
from scripts import run_m3_e01_pair24 as runner
from scripts import m3_pair_side as checker

BASE=Path(__file__).resolve().parents[1]
BUNDLE=Path(os.environ.get('M3_PAIR24_TEST_BUNDLE',str(BASE/'.downloads/m3_e01_pair24_bundle_20261021_v2')))


class PreparedTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name);source=self.home/'source/backend';source.mkdir(parents=True)
        (source/'data/external/bird_mini_dev').mkdir(parents=True)
        (source/'.env').write_text('LLM_API_KEY=PRIVATE_TEST_KEY')
        private=self.home/'private.json';private.write_text('{"password":"PRIVATE_TEST_PASSWORD"}')
        self.root=self.home/'pair'
        self.args=prepare.parser().parse_args(['--bundle-root',str(BUNDLE),'--source-backend',str(source),
            '--workspace',str(self.root),'--credentials-file',str(private)])

    def prepared(self):
        prepare.prepare(self.args)
        return c.workspace(self.root)


class PreparationTest(PreparedTest):
    def test_independent_96_97_directories_without_reading_or_copying_secrets(self):
        original=Path.read_bytes;private={self.args.credentials_file,self.args.source_backend/'.env'}
        def guarded(path):
            self.assertNotIn(path,private)
            return original(path)
        with patch.object(Path,'read_bytes',guarded):self.prepared()
        self.assertFalse(list(self.root.rglob('.env')))
        self.assertEqual(c.read(self.root/'preparation.json')['prepared_side_count'],2)
        for side in c.SIDES:
            self.assertFalse((c.side_base(self.root,side)/'data/m3_indexes').exists())
            self.assertTrue((c.side_base(self.root,side)/c.CASE_LIST).is_file())
        self.assertEqual((self.args.source_backend/'.env').read_text(),'LLM_API_KEY=PRIVATE_TEST_KEY')

    def test_refuse_existing_workspace_without_overwrite(self):
        self.prepared();path=self.root/'workspace.json';before=path.read_bytes()
        with self.assertRaisesRegex(c.PairError,'new workspace'):prepare.prepare(self.args)
        self.assertEqual(path.read_bytes(),before)

    def test_overlap_missing_input_and_capacity_refused_before_creation(self):
        self.args.workspace=self.args.source_backend/'nested'
        with self.assertRaisesRegex(c.PairError,'overlaps'):prepare.prepare(self.args)
        self.args.workspace=self.root
        with patch.object(shutil,'disk_usage',return_value=NS(free=1024)):
            with self.assertRaisesRegex(c.PairError,'2 GiB'):prepare.prepare(self.args)
        self.assertFalse(self.root.exists())
        self.args.credentials_file=self.home/'missing'
        with self.assertRaisesRegex(c.PairError,'missing'):prepare.prepare(self.args)

    def test_modified_producer_and_unexpected_python_file_are_rejected(self):
        self.prepared();path=c.side_base(self.root,'baseline')/'unexpected.py';path.write_text('raise RuntimeError()')
        with self.assertRaisesRegex(c.PairError,'Unexpected'):c.workspace(self.root)
        path.unlink()  # One explicitly created temporary test file, no recursive deletion.
        field=c.side_base(self.root,'candidate')/'evaluation/bird/output_contract.py'
        field.write_text(field.read_text(encoding='utf-8')+'\n# changed')
        with self.assertRaisesRegex(c.PairError,'changed'):c.workspace(self.root)

    def test_config_path_metadata_change_is_detected(self):
        self.prepared();path=self.root/'workspace.json';row=c.read(path);row['model_config_file']='elsewhere'
        path.write_text(json.dumps(row))
        with self.assertRaisesRegex(c.PairError,'path/config'):c.workspace(self.root)

    def test_import_support_asset_is_bound_and_tampering_rejected(self):
        self.prepared()
        for side in c.SIDES:
            for name,value in c.SUPPORT_FILES.items():self.assertEqual(c.sha(c.side_base(self.root,side)/name),value)
        path=c.side_base(self.root,'baseline')/next(iter(c.SUPPORT_FILES))
        path.write_text('{}')
        with self.assertRaisesRegex(c.PairError,'_schema.json'):c.workspace(self.root)

    def test_real_prepared_import_and_static_context_without_database_or_models(self):
        self.prepared()
        code="from unittest.mock import patch; from scripts import m3_pair_side,m2_b_target; " \
            "\nwith patch.object(m2_b_target,'live_dependencies'): r=m3_pair_side.probe()" \
            "\nassert r['new_model_request_count']==0 and r['postgresql_connected'] is False; print('static_context_passed')"
        for side in c.SIDES:
            completed=subprocess.run([sys.executable,'-E','-s','-c',code],cwd=c.side_base(self.root,side),
                capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.assertIn('static_context_passed',completed.stdout)

    def test_traversal_and_windows_drive_paths_refused(self):
        for value in ('../private','/tmp/private','C:/private','a\\private'):
            with self.subTest(value=value),self.assertRaises(c.PairError):c.safe(self.home,value)

    def test_bundle_contains_no_private_config_or_data_dump(self):
        row=c.bundle(BUNDLE)
        self.assertEqual(len(row['payload']['sides']['baseline']['code_files']),96)
        self.assertEqual(len(row['payload']['sides']['candidate']['code_files']),97)
        for name in row['payload']['files']:
            self.assertFalse(name.endswith(('.env','.zip','.dump','.sql')))
            self.assertNotIn('credentials.json',name)


class PairFixture(PreparedTest):
    def setUp(self):
        super().setUp();self.row,self.payload=self.prepared()
        self.original=c.read(BASE/'evaluation/results/m2_public_intent_v4_development80_server.json')
        self.native=c.read(BASE/'evaluation/results/m2_public_intent_v4_development80_native_server.json')
        ids=set(self.payload['case_ids']);self.captures={};self.natives={};self.calls=[];self.fail=None
        for side in c.SIDES:
            capture=deepcopy(self.original)
            capture['cases']=[v for v in capture['cases'] if v['case_id'] in ids]
            capture['selected_case_ids']=self.payload['case_ids']
            capture['summary']['case_model_http_attempts']=sum(v['new_model_request_count'] for v in capture['cases'])
            if side=='candidate':capture['summary']['shared_index_http_attempts']=0
            for entry in capture['index_builds']:
                db=entry['identity']['source_identity']['logical_database_id']
                path=c.side_base(self.root,side)/'data/m3_indexes'/db/c.digest(entry['identity'])/'schema_index.json'
                entry['path']=str(path)
                if side=='baseline':
                    c.write_new(path,{'unit_metadata_only':db})
                    entry['sha256']=c.sha(path)
                else:
                    entry['sha256']=next(e['sha256'] for e in self.captures['baseline']['index_builds'] if e['identity']==entry['identity'])
                    entry['cache_hit']=True
            native=deepcopy(self.native)
            native['cases']=[v for v in native['cases'] if v['case_id'] in ids]
            native['selected_case_ids']=[v['case_id'] for v in native['cases']]
            native['source_case_count']=24
            self.captures[side]=capture;self.natives[side]=native

    def runner_args(self,*extra):
        return runner.parser().parse_args(['--workspace',str(self.root),*extra])

    def fake_check(self,root,side,mode,target,**kwargs):
        self.calls.append((side,mode))
        if mode=='probe':
            return dict(code_binding=dict(files=self.payload['sides'][side]['code_files'],sha256=side,python='unit',system='Linux'),
                model_configuration=self.payload['model_configuration'],source_binding=self.payload['source_binding'])
        if mode=='capture':
            path=kwargs['capture'];return dict(capture_sha256=c.sha(path))
        return dict(native_sha256=c.sha(kwargs['native']))

    def fake_child(self,root,side,module,options,log,report=None,output=None,phase=None):
        self.calls.append((side,module))
        if self.fail==phase:raise c.PairError('Injected child failure')
        path=Path(options[options.index('--output')+1])
        if module=='evaluation.bird.diagnostic_runner':c.write_new(path,self.captures[side])
        else:c.write_new(path,self.natives[side])

    def execute(self,*extra):
        with patch.object(runner.sys,'platform','linux'),patch.object(c,'exclusive',return_value=nullcontext()),\
                patch.object(runner,'side_check',side_effect=self.fake_check),patch.object(runner,'child',side_effect=self.fake_child):
            return runner.execute(self.runner_args(*extra))


class WorkflowTest(PairFixture):
    def test_check_only_has_no_attempt_generation_or_index_copy(self):
        report=self.execute('--check-only')
        self.assertEqual(report['run_status'],'complete');self.assertEqual(report['new_model_request_count'],0)
        self.assertEqual(self.calls,[('baseline','probe'),('candidate','probe')])
        self.assertFalse((self.root/'attempt').exists())
        self.assertFalse((c.side_base(self.root,'candidate')/'data/m3_indexes').exists())

    def test_generation_both_complete_before_native_and_exact_pair_outputs(self):
        report=self.execute()
        self.assertEqual(report['run_status'],'complete',report)
        actions=[mode for _,mode in self.calls]
        first_native=actions.index('scripts.rescore_m2_intent_candidate')
        self.assertEqual(actions[:first_native].count('evaluation.bird.diagnostic_runner'),2)
        self.assertTrue(report['both_captures_complete_before_gold_replay'])
        self.assertEqual(report['summary']['case_count'],24)
        self.assertEqual(report['summary']['baseline_match_count'],20)
        self.assertEqual(report['summary']['candidate_match_count'],20)
        self.assertFalse(report['summary']['automatic_screen_pass'])
        self.assertEqual(len(report['copied_validated_indexes']),8)

    def test_failed_generation_is_preserved_no_automatic_retry_or_scoring(self):
        self.fail='candidate_generation';report=self.execute()
        self.assertEqual(report['run_status'],'failed')
        self.assertTrue(runner.capture_path(self.root,'baseline').exists())
        self.assertFalse(any(mode=='scripts.rescore_m2_intent_candidate' for _,mode in self.calls))
        with self.assertRaisesRegex(c.PairError,'already has'):self.execute('--output',str(self.root/'reports/retry.json'))

    def test_replay_only_with_missing_candidate_never_generates(self):
        (self.root/'attempt').mkdir();c.write_new(self.root/'attempt/reservation.json',{'bundle_id':self.row['bundle_id']})
        c.write_new(runner.capture_path(self.root,'baseline'),self.captures['baseline'])
        report=self.execute('--replay-only')
        self.assertEqual(report['run_status'],'failed')
        self.assertFalse(any(mode=='evaluation.bird.diagnostic_runner' for _,mode in self.calls))

    def test_native_failure_can_recover_once_without_new_generation(self):
        self.fail='candidate_native_replay';first=self.execute()
        self.assertEqual(first['run_status'],'failed')
        self.fail=None;self.calls=[]
        report=self.execute('--replay-only')
        self.assertEqual(report['run_status'],'complete',report)
        self.assertEqual(report['new_model_request_count'],0)
        self.assertFalse(any(mode=='evaluation.bird.diagnostic_runner' for _,mode in self.calls))
        with self.assertRaisesRegex(c.PairError,'already reserved'):
            self.execute('--replay-only','--output',str(self.root/'reports/recovery2.json'))

    def test_explicit_failed_native_report_is_not_overwritten(self):
        self.fail='candidate_native_replay';self.execute()
        path,_=runner.native_path(self.root,'candidate',True)
        c.write_new(path,{'run_status':'failed','errors':[{'type':'unit'}]});before=path.read_bytes()
        self.fail=None;self.calls=[];report=self.execute('--replay-only')
        self.assertEqual(report['run_status'],'complete',report)
        self.assertEqual(path.read_bytes(),before)
        self.assertTrue(report['report_paths']['candidate_native']['path'].endswith('_native_recovery1_server.json'))

    def test_generation_flags_differ_only_by_output_treatment(self):
        old=runner._generation_options(self.row,self.root,'baseline')
        new=runner._generation_options(self.row,self.root,'candidate')
        self.assertNotIn('--output-contract',old);self.assertIn('--output-contract',new)
        for name in ('--schema-coverage','--intent-candidate','--save-snapshot'):self.assertIn(name,old);self.assertIn(name,new)

    def test_output_cannot_overwrite_workspace_config_or_side_capture(self):
        for path in (self.root/'workspace.json',runner.capture_path(self.root,'baseline')):
            with self.assertRaisesRegex(c.PairError,'within workspace/reports'):
                self.execute('--check-only','--output',str(path))

    def test_pair_refuses_different_dependencies_before_generation(self):
        def check(root,side,mode,*a,**k):
            value=self.fake_check(root,side,mode,*a,**k)
            if side=='candidate':value['code_binding']['python']='other'
            return value
        with patch.object(runner.sys,'platform','linux'),patch.object(c,'exclusive',return_value=nullcontext()),patch.object(runner,'side_check',side_effect=check):
            report=runner.execute(self.runner_args('--check-only'))
        self.assertEqual(report['run_status'],'failed')
        self.assertIn('dependencies',report['errors'][0]['message'])


class SideEvidenceTest(PairFixture):
    def test_errors_preserve_safe_locations_but_not_private_details(self):
        secret='PRIVATE_TEST_CREDENTIAL_VALUE'
        try:raise FileNotFoundError(2,secret,str(checker.BASE/'data/missing_public_metadata.json'))
        except FileNotFoundError as error:detail=checker.failure(error)
        self.assertNotIn(secret,json.dumps(detail))
        self.assertEqual(detail['missing_relative_path'],'data/missing_public_metadata.json')
        try:raise FileNotFoundError(2,secret,str(self.home/'private.json'))
        except FileNotFoundError as error:detail=checker.failure(error)
        self.assertNotIn(str(self.home),json.dumps(detail));self.assertNotIn(secret,json.dumps(detail))
        self.assertIn('private path omitted',detail['missing_path_scope'])
        from scripts.m2_b_common import PreparationError
        self.assertEqual(checker.failure(PreparationError('Public dependency pin differs'))['message'],'Public dependency pin differs')

    def test_real_baseline_capture_and_native_checks_and_tamper_rejection(self):
        from evaluation.bird import intent_replay
        capture=deepcopy(self.captures['baseline']);native=deepcopy(self.natives['baseline'])
        capture['case_list_sha256']=c.sha(c.side_base(self.root,'baseline')/c.CASE_LIST)
        path=runner.capture_path(self.root,'baseline');c.write_new(path,capture)
        native['source_report_sha256']=c.sha(path)
        summary=native['summary'];matches=sum(v['native_comparison']['matches_frozen_gold'] for v in native['cases'])
        summary.update(source_case_count=24,replayed_case_count=len(native['cases']),excluded_case_count=0,
            native_match_count=matches,native_mismatch_count=len(native['cases'])-matches,
            development_subset_case_count=24,development_subset_native_match_rate=matches/24)
        native['excluded_cases']=[]
        native_path=path.with_name('native.json');c.write_new(native_path,native)
        roles={v['database_id']:v['query_role'] for v in capture['cases']}
        evidence=NS(domain=lambda db:dict(query_role=roles[db]))
        binding=capture['code_binding']
        with patch.object(checker,'BASE',c.side_base(self.root,'baseline')),\
                patch.object(checker,'context',return_value=(self.row,self.payload,'baseline',binding,evidence)),\
                patch.object(intent_replay,'code_binding',return_value=binding),\
                patch.object(intent_replay,'source_binding',return_value=capture['source_binding']):
            self.assertEqual(len(checker.capture(path)[1]),24)
            self.assertEqual(checker.native(native_path,path)['summary']['native_match_count'],20)
            native['cases'][0]['generated_sql_sha256']='0'*64
            native_path.write_text(json.dumps(native),encoding='utf-8')
            with self.assertRaisesRegex(c.PairError,'per-case'):checker.native(native_path,path)
            capture['source_binding']={}
            path.write_text(json.dumps(capture),encoding='utf-8')
            with self.assertRaises(ValueError):checker.capture(path)

    def test_candidate_requires_real_public_contract_and_per_attempt_binding(self):
        from evaluation.bird import intent_replay
        from evaluation.bird.output_contract import policy,build_contract
        from evaluation.bird.evidence import public_cases
        capture=deepcopy(self.captures['candidate']);capture['public_output_contract_policy']=policy()
        capture['case_list_sha256']=c.sha(c.side_base(self.root,'candidate')/c.CASE_LIST)
        public={v['case_id']:v for v in public_cases('development80')}
        for case in capture['cases']:
            case['public_output_contract_policy']=policy()
            graph=case['development_diagnostics']['retrieval']['schema_graph']['value']
            contract=build_contract(public[case['case_id']],graph,case['intent_contract'])
            import hashlib
            case['public_output_contract_sha256']=hashlib.sha256(json.dumps(contract,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
            decisions=[v for v in case['development_diagnostics']['attempts'] if v['kind']=='model_decision' and v.get('action')=='query' and v['sql'].get('provided')]
            case['output_contract_observations']=[dict(sql_sha256=v['sql']['original_sha256']) for v in decisions]
        path=runner.capture_path(self.root,'candidate');c.write_new(path,capture)
        roles={v['database_id']:v['query_role'] for v in capture['cases']};binding=capture['code_binding']
        evidence=NS(domain=lambda db:dict(query_role=roles[db]))
        with patch.object(checker,'BASE',c.side_base(self.root,'candidate')),\
                patch.object(checker,'context',return_value=(self.row,self.payload,'candidate',binding,evidence)),\
                patch.object(intent_replay,'code_binding',return_value=binding),\
                patch.object(intent_replay,'source_binding',return_value=capture['source_binding']):
            self.assertEqual(len(checker.capture(path)[1]),24)
            capture['cases'][0]['output_contract_observations'][0]['sql_sha256']='0'*64
            path.write_text(json.dumps(capture),encoding='utf-8')
            with self.assertRaisesRegex(c.PairError,'observation binding'):checker.capture(path)


class IndexAndSummaryTest(PairFixture):
    def test_seed_copies_exact_validated_bytes_and_refuses_overwrite(self):
        result=c.seed_indexes(self.root,self.captures['baseline']);self.assertEqual(len(result),8)
        for entry in self.captures['candidate']['index_builds']:self.assertEqual(c.sha(Path(entry['path'])),entry['sha256'])
        with self.assertRaises(FileExistsError):c.seed_indexes(self.root,self.captures['baseline'])

    def test_seed_refuses_source_escape_or_digest_change(self):
        original=self.captures['baseline']['index_builds'][0]
        for mutation in ('path','sha256'):
            capture=deepcopy(self.captures['baseline'])
            capture['index_builds'][0][mutation]=str(self.home/'outside') if mutation=='path' else '0'*64
            with self.assertRaises(c.PairError):c.seed_indexes(self.root,capture)

    def test_fixed24_denominator_gain_and_success_retention_gate(self):
        for row in self.natives['candidate']['cases']:
            if row['case_id'] in c.PRIMARY:row['native_comparison']['matches_frozen_gold']=True
        report=c.compare_pair(self.payload,self.captures,self.natives)
        self.assertEqual((report['baseline_match_count'],report['candidate_match_count']),(20,23))
        self.assertTrue(report['automatic_screen_pass'])
        self.assertEqual(report['acceptance'],'manual_semantic_review_required')
        self.natives['candidate']['cases'][0]['native_comparison']['matches_frozen_gold']=False
        self.assertFalse(c.compare_pair(self.payload,self.captures,self.natives)['automatic_screen_pass'])

    def test_schema_changes_are_reported_as_a_confound_not_a_prompt_gain(self):
        self.captures['candidate']['cases'][0]['development_diagnostics']['retrieval']['schema_graph']['value']['fields'].reverse()
        report=c.compare_pair(self.payload,self.captures,self.natives)
        self.assertTrue(report['schema_context_changed_case_ids'])
        self.assertFalse(report['screening']['same_observed_schema_all_cases'])

    def test_unknown_usage_is_not_filled_as_zero(self):
        event=next(v for v in self.captures['candidate']['cases'][0]['budget']['model_events'] if v['kind']=='chat')
        event['usage']=None
        report=c.compare_pair(self.payload,self.captures,self.natives)
        self.assertIsNone(report['chat_total_tokens']['candidate'])
        self.assertFalse(report['screening']['cost_known'])

    def test_index_mismatch_refuses_comparison(self):
        self.captures['candidate']['index_builds'][0]['sha256']='0'*64
        with self.assertRaisesRegex(c.PairError,'index bytes'):c.compare_pair(self.payload,self.captures,self.natives)

    def test_no_answer_counts_zero_without_removing_denominator(self):
        self.natives['candidate']['cases']=self.natives['candidate']['cases'][1:]
        result=c.compare_pair(self.payload,self.captures,self.natives)
        self.assertEqual(result['case_count'],24)
        self.assertFalse(result['cases'][0]['candidate_correct'])


if __name__=='__main__':unittest.main()
