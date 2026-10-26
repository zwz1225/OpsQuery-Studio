"""No live HTTP/DNS/SQL: recovered faults, budget ceilings, and failed-index evidence."""
from contextlib import nullcontext, ExitStack, redirect_stdout
import io
import json
from pathlib import Path
import socket
import ssl
from types import SimpleNamespace as NS
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from evaluation.bird import model, retrieval
from evaluation.bird.budgets import Budget, BirdFailure


class Reply(io.BytesIO):
    status=200
    def __init__(self):
        super().__init__(json.dumps({'data':[{'index':0,'embedding':[1.0]*1024}],
                                    'usage':{'total_tokens':3}}).encode())


def dns_error(code=socket.EAI_AGAIN):
    return urllib.error.URLError(socket.gaierror(code,'SECRET_PROVIDER_TEXT'))


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.deadline=patch.object(model,'hard_deadline',side_effect=lambda *a:nullcontext())
        self.deadline.start();self.addCleanup(self.deadline.stop)
        self.sleep=patch.object(model.time,'sleep').start();self.addCleanup(patch.stopall)
        self.budget=Budget()
        self.client=model.Models(model.ModelConfig('SECRET_API_KEY'),self.budget)

    def test_transient_dns_recovers_with_one_shared_budget_retry(self):
        with patch.object(model,'open_url',side_effect=[dns_error(),Reply()]) as send:
            vectors=self.client.embed(['public metadata'])
        self.assertEqual(len(vectors[0]),1024)
        self.assertEqual(send.call_count,self.budget.total_attempts)
        self.assertEqual(self.budget.total_attempts,2)
        self.sleep.assert_called_once_with(2)
        self.assertEqual(self.budget.events[0]['transport_diagnostic']['category'],'dns_temporary')
        self.assertEqual(self.budget.events[1]['http_status'],200)
        self.assertIsNone(self.budget.events[0]['usage'])
        self.assertNotIn('SECRET',json.dumps(self.budget.public()))

    def test_two_dns_failures_stop_and_are_not_unknown_transport(self):
        with patch.object(model,'open_url',side_effect=dns_error()) as send:
            with self.assertRaises(BirdFailure) as caught:self.client.embed(['x'])
        self.assertEqual(caught.exception.category,'model_dns_error')
        self.assertEqual(send.call_count,2)
        self.sleep.assert_called_once_with(2)
        self.assertNotIn('SECRET',json.dumps(self.budget.public()))

    def test_permanent_dns_error_does_not_retry(self):
        with patch.object(model,'open_url',side_effect=dns_error(socket.EAI_NONAME)) as send:
            with self.assertRaises(BirdFailure):self.client.embed(['x'])
        self.assertEqual(send.call_count,1);self.sleep.assert_not_called()

    def test_certificate_failure_stops_without_disabling_verification(self):
        error=urllib.error.URLError(ssl.SSLCertVerificationError(1,'SECRET_CERT_TEXT'))
        with patch.object(model,'open_url',side_effect=error) as send:
            with self.assertRaises(BirdFailure):self.client.embed(['x'])
        self.assertEqual(send.call_count,1);self.sleep.assert_not_called()
        self.assertEqual(self.budget.events[0]['transport_diagnostic']['category'],'tls_certificate')

    def test_auth_error_has_no_retry(self):
        error=urllib.error.HTTPError('https://example.invalid',401,'SECRET_BODY',{},None)
        with patch.object(model,'open_url',side_effect=error) as send:
            with self.assertRaises(BirdFailure) as caught:self.client.embed(['x'])
        self.assertEqual(send.call_count,1);self.sleep.assert_not_called()
        self.assertEqual(caught.exception.category,'model_http_error')

    def test_invalid_json_has_distinct_safe_diagnostic(self):
        with patch.object(model,'open_url',side_effect=[io.BytesIO(b'SECRET_HTML'),Reply()]):
            self.client.embed(['x'])
        self.assertEqual(self.budget.events[0]['transport_diagnostic']['category'],'json_decode')
        self.assertNotIn('SECRET',json.dumps(self.budget.public()))

    def test_request_deadline_keeps_original_two_attempt_ceiling(self):
        with patch.object(model,'open_url',side_effect=BirdFailure('model_request_timeout')) as send:
            with self.assertRaises(BirdFailure) as caught:self.client.embed(['x'])
        self.assertEqual(send.call_count,2)
        self.assertEqual(self.budget.total_attempts,2)
        self.assertEqual(caught.exception.category,'model_request_timeout')
        self.sleep.assert_not_called()

    def test_wall_budget_cannot_be_extended_by_backoff(self):
        with patch.object(self.budget,'remaining',return_value=1),patch.object(model,'open_url',side_effect=dns_error()) as send:
            with self.assertRaises(BirdFailure) as caught:self.client.embed(['x'])
        self.assertEqual(caught.exception.category,'case_wall_timeout')
        self.assertEqual(send.call_count,1);self.sleep.assert_not_called()

    def test_retry_cannot_bypass_total_http_budget(self):
        self.budget.total_limit=1
        with patch.object(model,'open_url',side_effect=dns_error()) as send:
            with self.assertRaises(BirdFailure) as caught:self.client.embed(['x'])
        self.assertEqual(caught.exception.category,'model_attempt_limit')
        self.assertEqual(send.call_count,1);self.assertEqual(self.budget.total_attempts,1)

    def test_failed_index_preserves_real_attempts_without_writing_cache(self):
        progress={};store=NS(load=lambda *a,**kw:False)
        with tempfile.TemporaryDirectory() as root,patch.object(retrieval,'index_identity',return_value={}),\
            patch.object(retrieval,'index_path',return_value=Path(root)/'index.json'),\
            patch.object(retrieval,'LocalSchemaStore',return_value=store),\
            patch.object(retrieval,'raw_documents',return_value=[{'semantic_text':'x'}]),\
            patch.object(model,'open_url',side_effect=dns_error()):
            with self.assertRaises(BirdFailure):retrieval.build_index(NS(),self.client.config,Path(root),progress=progress)
            self.assertFalse((Path(root)/'index.json').exists())
        self.assertFalse(progress['complete'])
        self.assertEqual(progress['stage'],'embedding')
        self.assertEqual(progress['model_usage']['model_http_attempts'],2)
        self.assertEqual(len(progress['model_usage']['model_events']),2)


class WorkflowTest(unittest.TestCase):
    def test_capture_checker_supports_frozen_e02_no_argument_policy(self):
        from scripts import m3_e03_pair_side as side
        from evaluation.bird import demand_relations, intent_replay
        ids=[str(i) for i in range(24)]
        payload={k:{} for k in ('model_configuration','schema_selection_policy','sql_repair_policy','intent_candidate_policy')}
        payload.update(case_ids=ids,transport_policy=model.TRANSPORT_POLICY)
        report={k:payload[k] for k in ('model_configuration','schema_selection_policy','sql_repair_policy','intent_candidate_policy')}
        expected={'frozen_e02':'no-arguments'}
        report.update(selected_case_ids=ids,cases=[{'budget':{'model_http_attempts':0,'model_events':[]}} for _ in ids],
            transport_dependency_binding={'test':'dependency'},index_builds=[],
            case_list_sha256=side.c.sha(side.BASE/side.c.CASE_LIST),workers=1,
            condition_relation_policy=expected,transport_policy=model.TRANSPORT_POLICY,
            preparation_attempts=[{'complete':True,'model_usage':{'model_http_attempts':0,'model_events':[]}} for _ in range(8)],
            preparation_model_http_attempts=0,new_model_request_count=0,summary={'shared_index_http_attempts':0})
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'capture';path.write_text('{}')
            with patch.object(side,'context',return_value=({},payload,'baseline',{},None)),\
                patch.object(intent_replay,'load_candidate_capture',return_value=(report,[None]*24,[])),\
                patch.object(demand_relations,'policy',lambda:expected),\
                patch('evaluation.bird.process_dns.recorded_binding',return_value={'test':'dependency'}):
                result,pairs,excluded=side.capture(path)
            self.assertIs(result,report);self.assertEqual(len(pairs),24)

    def test_new_bundle_prepares_two_exact_sides_without_copying_secrets(self):
        from scripts.build_m3_e03_process_dns_pair24_bundle import OUT,BACKEND
        from scripts.prepare_m3_e03_pair24 import prepare
        from scripts.m3_e03_pair_common import workspace
        if not OUT.exists():self.skipTest('Local transport bundle is not installed')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=root/'data';data.mkdir()
            config=root/'config';config.write_text('SECRET_CONFIGURATION')
            credentials=root/'credentials';credentials.write_text('SECRET_PASSWORD')
            target=root/'workspace'
            result=prepare(NS(bundle_root=OUT,source_backend=BACKEND,workspace=target,
                data_root=data,model_config_file=config,credentials_file=credentials))
            row,payload=workspace(target)
            self.assertEqual(result['run_status'],'complete')
            self.assertFalse(result['secrets_copied'])
            self.assertEqual(len(payload['sides']['baseline']['code_files']),99)
            self.assertEqual(len(payload['sides']['candidate']['code_files']),100)
            self.assertFalse((target/'baseline/backend/.env').exists())
            self.assertNotIn('SECRET_',json.dumps(row))

    def test_new_bundle_keeps_old_evidence_and_changes_only_shared_infrastructure(self):
        from scripts.build_m3_e03_process_dns_pair24_bundle import OUT,SOURCE,COMMON
        from scripts.m3_e03_pair_common import bundle
        if not OUT.exists() or not SOURCE.exists():self.skipTest('Local preserved bundles are not installed')
        new=bundle(OUT)['payload'];old=json.loads((SOURCE/'bundle_manifest.json').read_bytes())['payload']
        self.assertEqual(new['source_binding'],old['source_binding'])
        self.assertEqual(new['model_configuration'],old['model_configuration'])
        self.assertEqual(new['case_ids'],old['case_ids'])
        for side in ('baseline','candidate'):
            before=old['sides'][side]['code_files'];after=new['sides'][side]['code_files']
            self.assertEqual(set(after)-set(before),{'evaluation/bird/process_dns.py'})
            self.assertEqual({n for n in before if before[n]!=after[n]},set(COMMON)-{'evaluation/bird/process_dns.py'})
        name='evaluation/bird/model.py'
        self.assertEqual(new['sides']['baseline']['code_files'][name],new['sides']['candidate']['code_files'][name])

    def test_failed_runner_keeps_index_attempt_count_in_saved_report(self):
        from evaluation.bird import diagnostic_runner as runner
        import sys
        class Registry:
            def __init__(self,*a):self._runtimes={}
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def get(self,db):return NS(receipt=lambda:{'database_id':db})
        def fail_index(*a,progress,**kw):
            progress.update(stage='embedding',model_usage={'model_http_attempts':2,'model_events':[]})
            raise BirdFailure('model_dns_error')
        evidence=NS(manifest={'question_relative_path':'public'},protocol={'protocol_id':'unit'})
        baseline={'code_binding':{'sha256':'old'},'cases':[]}
        with tempfile.TemporaryDirectory() as tmp,ExitStack() as stack:
            root=Path(tmp);old=root/'old';old.write_text('{}');output=root/'report.json'
            args=['runner','--output',str(output),'--baseline-report',str(old),
                  '--runtime-report',str(old),'--gold-report',str(old),'--index-root',str(root/'index')]
            stack.enter_context(patch.object(sys,'argv',args))
            for owner,name,value in (
                (runner,'live_dependencies',lambda:None),
                (runner.Evidence,'load',lambda *a:evidence),
                (runner,'prerequisites',lambda *a:baseline),
                (runner,'select_development',lambda *a:[{'case_id':'BIRD-PG-0050','database_id':'california_schools'}]),
                (runner.ModelConfig,'load',lambda *a:model.ModelConfig('SECRET')),
                (runner,'source_binding',lambda *a:{}),(runner,'code_binding',lambda:{'sha256':'unit'}),
                (runner,'budget_checks',lambda:[]),(runner,'isolation_probe',lambda *a:{'passed':True}),
                (runner,'BirdRegistry',Registry),(runner,'build_index',fail_index)):
                stack.enter_context(patch.object(owner,name,value))
            stack.enter_context(patch.object(runner,'run_case_process',side_effect=BirdFailure('case_wall_timeout')))
            stack.enter_context(redirect_stdout(io.StringIO()))
            with self.assertRaises(SystemExit) as caught:runner.main()
            report=json.loads(output.read_bytes())
        self.assertEqual(caught.exception.code,1)
        self.assertEqual(report['new_model_request_count'],2)
        self.assertEqual(report['preparation_model_http_attempts'],2)
        self.assertEqual(report['errors'][0]['message'],'model_dns_error')
        self.assertEqual(report['cases'],[])
        self.assertEqual(report['preparation_attempts'][0]['stage'],'embedding')

    def test_shared_adaptation_preserves_candidate_exactly(self):
        from scripts.build_m3_e03_process_dns_pair24_bundle import SOURCE,BACKEND,COMMON,shared_source
        if not SOURCE.exists():self.skipTest('Local preserved source bundle is not installed')
        manifest=json.loads((SOURCE/'bundle_manifest.json').read_bytes())['payload']
        for name in set(COMMON)-{'evaluation/bird/process_dns.py'}:
            old=(SOURCE/manifest['sides']['candidate']['assets'][name]['bundle_path']).read_text(encoding='utf-8')
            self.assertEqual(shared_source(name,old,old),(BACKEND/name).read_text(encoding='utf-8'))

    def test_dns_gate_failure_is_before_generation_reservation(self):
        from scripts import run_m3_e03_pair24 as run
        from scripts import m3_e03_pair_common as c
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'preparation.json').write_text('{"run_status":"complete"}')
            payload=dict(controllers={'run_m3_e03_pair24.py':c.sha(Path(run.__file__))},case_ids=['fixed'],
                model_configuration={},source_binding={},transport_policy={})
            probe=dict(code_binding={'files':{},'sha256':'side'},model_configuration={},source_binding={},
                transport_dependency_binding={'test':'dependency'})
            def check(*a,**kw):return probe if a[2]=='probe' else {'passed':False,'checks':[]}
            args=NS(workspace=root,output=None,check_only=False,replay_only=False)
            with patch.object(run.sys,'platform','linux'),patch.object(c,'workspace',return_value=({'bundle_id':'unit'},payload)),\
                patch.object(c,'exclusive',side_effect=lambda *a:nullcontext()),patch.object(run,'side_check',side_effect=check),\
                patch.object(run,'child') as child:
                report=run.execute(args)
            self.assertEqual(report['run_status'],'failed')
            self.assertFalse(report['dns_readiness']['passed'])
            self.assertEqual(report['new_model_request_count'],0)
            self.assertFalse((root/'attempt').exists());child.assert_not_called()


if __name__=='__main__':unittest.main()
