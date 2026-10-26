"""No live DNS/model/SQL: bound resolver, HTTPS identity, lock and driver gates."""
from contextlib import nullcontext
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import ssl
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import MagicMock,patch
import urllib.request

from evaluation.bird import process_dns as dns,model
from evaluation.bird.budgets import Budget,BirdFailure

HOST='dashscope.aliyuncs.com'
DEPENDENCY={'executable':'/usr/bin/dig','version':dns.DNS_POLICY['expected_version'],
    'sha256':'a'*64,'policy':dns.DNS_POLICY}
ANSWER={'addresses':[{'address':'8.8.4.4','ttl_seconds':30},
    {'address':'8.8.8.8','ttl_seconds':30}],'status':'complete','cname_chain':[]}


class Reply(io.BytesIO):
    def __init__(self,status=200):
        super().__init__(json.dumps({'data':[{'index':0,'embedding':[1.0]*1024}],
            'usage':{'total_tokens':4}}).encode());self.status=status


class TransportTest(unittest.TestCase):
    def setUp(self):
        self.deadline=patch.object(model,'hard_deadline',side_effect=lambda *a:nullcontext()).start()
        self.addCleanup(patch.stopall)
        self.sleep=patch.object(model.time,'sleep').start()
        self.binding=patch.object(dns,'request_binding',return_value=DEPENDENCY).start()
        self.resolver=patch.object(dns,'resolve',side_effect=lambda *a:(ANSWER,dns.time.monotonic())).start()
        self.connection=MagicMock();self.connection.getresponse.return_value=Reply()
        self.connection.sock.version.return_value='TLSv1.3'
        self.connect=patch.object(dns,'ResolvedHTTPSConnection',return_value=self.connection).start()
        self.budget=Budget();self.client=model.Models(model.ModelConfig('SECRET_KEY'),self.budget)

    def test_full_embedding_uses_explicit_dns_original_host_and_existing_budget(self):
        vectors=self.client.embed(['public field'])
        self.assertEqual(len(vectors[0]),1024);self.assertEqual(self.budget.total_attempts,1)
        self.assertEqual(self.resolver.call_count,1);self.assertEqual(self.connect.call_count,1)
        request=self.connection.request.call_args
        self.assertEqual(request.args[:2],('POST','/compatible-mode/v1/embeddings'))
        self.assertEqual(request.kwargs['headers']['Host'],HOST)
        self.assertEqual(request.kwargs['headers']['Authorization'],'Bearer SECRET_KEY')
        event=self.budget.events[0]
        self.assertEqual(event['transport_dependency_binding'],DEPENDENCY)
        self.assertTrue(event['tls_verified']);self.assertEqual(event['tls_hostname'],HOST)
        self.assertNotIn('SECRET',json.dumps(self.budget.public()))
        self.assertGreater(self.connection.sock.settimeout.call_args.args[0],10)

    def test_each_retry_has_one_dns_query_and_one_connection(self):
        self.connection.getresponse.side_effect=[Reply(503),Reply()]
        self.client.embed(['x'])
        self.assertEqual(self.budget.total_attempts,2)
        self.assertEqual(self.resolver.call_count,2);self.assertEqual(self.connect.call_count,2)
        self.assertEqual([c.args[1] for c in self.connect.call_args_list],['8.8.4.4','8.8.8.8'])

    def test_dns_failures_use_only_two_existing_model_attempts(self):
        self.resolver.side_effect=dns.ProbeError('dns_query_failed')
        with self.assertRaises(BirdFailure) as caught:self.client.embed(['x'])
        self.assertEqual(caught.exception.category,'model_dns_error')
        self.assertEqual(self.resolver.call_count,2);self.connect.assert_not_called()
        self.assertEqual(self.budget.total_attempts,2);self.sleep.assert_called_once_with(2)

    def test_permanent_nxdomain_stops_after_one_attempt(self):
        self.resolver.side_effect=socket.gaierror(socket.EAI_NONAME,'SECRET')
        with self.assertRaises(BirdFailure):self.client.embed(['x'])
        self.assertEqual(self.resolver.call_count,1);self.sleep.assert_not_called()
        self.assertNotIn('SECRET',json.dumps(self.budget.public()))

    def test_expired_answer_never_opens_socket(self):
        self.resolver.side_effect=lambda *a:(ANSWER,dns.time.monotonic()-31)
        with self.assertRaises(BirdFailure):self.client.embed(['x'])
        self.connect.assert_not_called();self.assertEqual(self.budget.total_attempts,2)

    def test_redirect_and_unauthorized_never_follow_or_retry(self):
        for status in (302,401):
            self.budget=Budget();self.client=model.Models(model.ModelConfig('SECRET_KEY'),self.budget)
            self.resolver.reset_mock();self.connection.getresponse.side_effect=None
            self.connection.getresponse.return_value=Reply(status)
            with self.assertRaises(BirdFailure):self.client.embed(['x'])
            self.assertEqual(self.resolver.call_count,1);self.assertEqual(self.budget.total_attempts,1)

    def test_certificate_failure_is_not_retried(self):
        self.connection.connect.side_effect=ssl.SSLCertVerificationError(1,'SECRET_CERT')
        with self.assertRaises(BirdFailure):self.client.embed(['x'])
        self.assertEqual(self.connect.call_count,1);self.connection.close.assert_called()
        self.connection.request.assert_not_called()
        self.assertNotIn('SECRET',json.dumps(self.budget.public()))

    def test_endpoint_not_in_config_never_resolves_or_sends_credentials(self):
        request=urllib.request.Request('https://other.example.com/x',headers={'Authorization':'SECRET'})
        with self.assertRaises(BirdFailure):
            dns.open_url(request,timeout=30,event={},allowed_hosts={HOST})
        self.resolver.assert_not_called();self.connect.assert_not_called()

    def test_missing_or_wrong_lock_stops_before_dns(self):
        self.binding.side_effect=BirdFailure('process_dns_dependency_lock_mismatch')
        with self.assertRaises(BirdFailure) as caught:self.client.embed(['x'])
        self.assertEqual(caught.exception.category,'process_dns_dependency_lock_mismatch')
        self.resolver.assert_not_called();self.assertEqual(self.budget.total_attempts,1)

    def test_total_budget_can_prevent_second_network_attempt(self):
        self.budget.total_limit=1;self.resolver.side_effect=dns.ProbeError('dns_query_failed')
        with self.assertRaises(BirdFailure):self.client.embed(['x'])
        self.assertEqual(self.resolver.call_count,1)


class DependencyTest(unittest.TestCase):
    def test_extended_support_suffix_version_is_captured(self):
        dns._tool_binding.cache_clear()
        output=b'DiG 9.18.39-0ubuntu0.22.04.7-Ubuntu (Extended Support Version)\n'
        with patch.object(dns.subprocess,'run',return_value=NS(returncode=0,stdout=output,stderr=b'')):
            result=dns._tool_binding('/usr/bin/dig',1,1,'b'*64)
        self.assertEqual(result['version'],dns.DNS_POLICY['expected_version'])
        self.assertEqual(result['sha256'],'b'*64)

    def test_wrong_version_fails_closed_with_safe_actual_version(self):
        dns._tool_binding.cache_clear()
        with patch.object(dns.subprocess,'run',return_value=NS(returncode=0,stdout=b'DiG 9.18.40',stderr=b'')):
            with self.assertRaises(BirdFailure) as caught:dns._tool_binding('/usr/bin/dig',1,1,'c'*64)
        self.assertEqual(caught.exception._transport_dependency['actual_version'],'9.18.40')

    def test_binary_change_is_detected_even_with_preserved_size_and_mtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'dig';path.write_bytes(b'AAA');st=path.stat()
            with patch.dict(dns.DNS_POLICY,executable=str(path)),patch.object(dns,'_tool_binding',side_effect=lambda p,s,m,h:{'sha256':h}):
                a=dns.tool_binding();path.write_bytes(b'BBB');os.utime(path,ns=(st.st_atime_ns,st.st_mtime_ns))
                b=dns.tool_binding()
        self.assertNotEqual(a,b)

    def test_workspace_lock_requires_bundle_and_exact_binary_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)/'baseline/backend';base.mkdir(parents=True)
            (base/'m3_context.json').write_text(json.dumps({'workspace':tmp,'bundle_id':'unit'}))
            lock=Path(tmp)/'transport_dependency_lock.json'
            with patch.object(dns,'BASE',base),patch.object(dns,'tool_binding',return_value=DEPENDENCY):
                with self.assertRaises(BirdFailure):dns.recorded_binding()
                lock.write_text(json.dumps({'bundle_id':'unit','binding':DEPENDENCY}))
                self.assertEqual(dns.recorded_binding(),DEPENDENCY)
                lock.write_text(json.dumps({'bundle_id':'other','binding':DEPENDENCY}))
                with self.assertRaises(BirdFailure):dns.recorded_binding()

    def test_preflight_and_model_use_same_open_url(self):
        config={key:'https://'+HOST+'/v1' for key in ('chat_base','embedding_base','rerank_base')}
        def fail_root(request,**kw):
            self.assertEqual(request.get_method(),'HEAD');self.assertIsNone(request.data)
            self.assertNotIn('Authorization',dict(request.header_items()))
            kw['event'].update(tls_verified=True,http_status=404)
            raise model.urllib.error.HTTPError(request.full_url,404,'ignored',{},None)
        with patch.object(dns,'tool_binding',return_value=DEPENDENCY),patch.object(dns,'open_url',side_effect=fail_root) as opened:
            result=dns.readiness(config)
        self.assertTrue(result['passed']);self.assertEqual(opened.call_count,1)
        self.assertEqual(result['new_model_request_count'],0)

    def test_low_level_tls_dials_numeric_address_with_original_sni(self):
        context=MagicMock(check_hostname=True,verify_mode=ssl.CERT_REQUIRED);raw=MagicMock()
        with patch.object(dns.ssl,'create_default_context',return_value=context),\
            patch.object(dns.socket,'socket',return_value=raw),\
            patch.object(dns.socket,'getaddrinfo',side_effect=AssertionError('system DNS forbidden')):
            connection=dns.ResolvedHTTPSConnection(HOST,'8.8.4.4',10);connection.connect()
        raw.connect.assert_called_once_with(('8.8.4.4',443))
        context.wrap_socket.assert_called_once_with(raw,server_hostname=HOST)


class DriverTest(unittest.TestCase):
    def execute(self,root,*,check_only=False,model_probe=False,connection_pass=True):
        from scripts import run_m3_e03_pair24 as run,m3_e03_pair_common as c
        preparation=root/'preparation.json'
        if not preparation.exists():preparation.write_text('{"run_status":"complete"}')
        payload=dict(controllers={'run_m3_e03_pair24.py':c.sha(Path(run.__file__))},case_ids=['unit'],
            model_configuration={},source_binding={},transport_policy={})
        static=dict(code_binding={'files':{},'sha256':'side'},model_configuration={},source_binding={},
            transport_dependency_binding=DEPENDENCY)
        def side_check(*args,**kw):
            mode=args[2]
            if mode=='probe':return static
            if mode=='connection':return dict(passed=connection_pass,binding=DEPENDENCY)
            if mode=='model-probe':
                result=dict(passed=True,new_model_request_count=1,transport_dependency_binding=DEPENDENCY)
                c.write_new(args[3],{'result':result});return result
            raise AssertionError('Generation must not start')
        args=NS(workspace=root,output=None,check_only=check_only,replay_only=False,model_probe=model_probe)
        with patch.object(run.sys,'platform','linux'),patch.object(c,'workspace',return_value=({'bundle_id':'unit'},payload)),\
            patch.object(c,'exclusive',side_effect=lambda *a:nullcontext()),patch.object(run,'side_check',side_effect=side_check):
            return run.execute(args)

    def test_preflight_writes_lock_without_model_or_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);report=self.execute(root,check_only=True)
            self.assertEqual(report['run_status'],'complete');self.assertEqual(report['new_model_request_count'],0)
            self.assertTrue((root/'transport_dependency_lock.json').exists());self.assertFalse((root/'attempt').exists())

    def test_connection_failure_never_locks_or_reserves_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);report=self.execute(root,connection_pass=False)
            self.assertEqual(report['run_status'],'failed');self.assertEqual(report['new_model_request_count'],0)
            self.assertFalse((root/'transport_dependency_lock.json').exists());self.assertFalse((root/'attempt').exists())

    def test_formal_generation_requires_successful_model_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);report=self.execute(root)
            self.assertEqual(report['run_status'],'failed');self.assertFalse((root/'attempt').exists())

    def test_model_smoke_has_separate_receipt_and_real_attempt_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);report=self.execute(root,model_probe=True)
            self.assertEqual(report['run_status'],'complete');self.assertEqual(report['new_model_request_count'],1)
            receipt=json.loads((root/'transport_model_probe_receipt.json').read_bytes())
            self.assertEqual(hashlib.sha256(Path(receipt['child_report_path']).read_bytes()).hexdigest(),receipt['child_report_sha256'])
            self.assertFalse((root/'attempt').exists())

    def test_changed_dependency_lock_stops_without_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'transport_dependency_lock.json').write_text('{"bundle_id":"different","binding":{}}')
            report=self.execute(root,check_only=True)
            self.assertEqual(report['run_status'],'failed');self.assertFalse((root/'attempt').exists())


class RealModelProbeEntryTest(unittest.TestCase):
    def test_frozen_r1_reproduces_missing_workspace_before_any_model_call(self):
        old=Path(__file__).resolve().parents[1]/'.downloads/m3_e03_pair24_process_dns_v1_20261023_r1/control/m3_e03_pair_side.py'
        if not old.is_file():self.skipTest('Preserved r1 bundle unavailable')
        spec=importlib.util.spec_from_file_location('scripts._frozen_r1_model_probe',old)
        frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
        config=model.ModelConfig('SECRET_KEY')
        from evaluation.bird import process_dns
        with patch.object(frozen,'context',return_value=({'model_config_file':'unused'},
                {'model_configuration':config.public()},'baseline',{},None)),\
            patch.object(model.ModelConfig,'load',return_value=config),\
            patch.object(process_dns,'recorded_binding',return_value=DEPENDENCY),\
            patch.object(model,'Models') as client:
            with self.assertRaises(KeyError) as caught:frozen.model_probe()
        self.assertEqual(caught.exception.args,('workspace',));client.assert_not_called()

    def exercise(self,root,operation):
        from scripts import m3_e03_pair_side as side
        from evaluation.bird import process_dns
        base=root/'baseline/backend';base.mkdir(parents=True,exist_ok=True)
        config=model.ModelConfig('SECRET_KEY')
        # This is the actual prepared workspace shape: workspace.json has no
        # workspace key; the path belongs to the producer's m3_context.json.
        row=dict(bundle_id='unit',model_config_file=str(root/'private_config'))
        (base/'m3_context.json').write_text(json.dumps(dict(
            workspace=str(root),bundle_id='unit',side='baseline')))
        class ProbeModels:
            def __init__(self,configuration,budget):self.budget=budget
            def embed(self,texts):
                return operation(self.budget,texts)
        with patch.object(side,'BASE',base),patch.object(side,'context',return_value=(
                row,{'model_configuration':config.public()},'baseline',{},None)),\
            patch.object(model.ModelConfig,'load',return_value=config),\
            patch.object(process_dns,'recorded_binding',return_value=DEPENDENCY),\
            patch.object(model,'Models',ProbeModels):
            return side.model_probe()

    def test_actual_model_probe_uses_producer_context_path_and_preserves_one_attempt(self):
        def success(budget,texts):
            self.assertEqual(len(texts),10)
            self.assertTrue(all('connectivity probe' in text for text in texts))
            budget.model_attempt('embedding')
            return [[0.0]*1024 for _ in texts]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);report=self.exercise(root,success)
            self.assertTrue(report['passed']);self.assertEqual(report['new_model_request_count'],1)
            self.assertEqual(report['vector_count'],10);self.assertEqual(report['dimensions'],[1024])
            reservation=json.loads((root/'transport_model_probe_attempt.json').read_bytes())
            self.assertEqual(reservation['bundle_id'],'unit')
            self.assertFalse(reservation['generation_reserved']);self.assertFalse((root/'attempt').exists())

    def test_actual_model_probe_failure_preserves_budget_and_prevents_a_second_probe(self):
        calls=[]
        def fail(budget,texts):
            calls.append(1);budget.model_attempt('embedding')
            raise BirdFailure('model_dns_error')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);report=self.exercise(root,fail)
            self.assertFalse(report['passed']);self.assertEqual(report['new_model_request_count'],1)
            self.assertEqual(report['error']['category'],'model_dns_error')
            with self.assertRaises(FileExistsError):self.exercise(root,fail)
            self.assertEqual(len(calls),1);self.assertFalse((root/'attempt').exists())


if __name__=='__main__':unittest.main()
