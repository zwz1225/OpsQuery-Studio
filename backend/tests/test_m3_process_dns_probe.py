"""Offline positive/negative checks for the standalone DNS/verified HTTPS probe."""
from contextlib import nullcontext, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import MagicMock, patch


SOURCE=Path(__file__).resolve().parents[2]/'probe_m3_e03_process_dns.py'
spec=importlib.util.spec_from_file_location('process_dns_probe',SOURCE)
probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
HOST='dashscope.aliyuncs.com'
ANSWER=''';; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 123
;; flags: qr rd ra; QUERY: 1, ANSWER: 3, AUTHORITY: 0, ADDITIONAL: 0
dashscope.aliyuncs.com. 300 IN CNAME gateway.example.com.
gateway.example.com. 33 IN A 8.8.4.4
gateway.example.com. 45 IN A 8.8.8.8
'''


class AnswerTest(unittest.TestCase):
    def test_cname_ttl_and_addresses_are_reachable_and_public(self):
        answer=probe.parse_answer(HOST,ANSWER.replace('300 IN CNAME','20 IN CNAME'))
        self.assertEqual([row['ttl_seconds'] for row in answer['addresses']],[20,20])
        self.assertEqual(answer['cname_chain'][0]['target'],'gateway.example.com')

    def test_unrelated_address_cannot_supply_the_connection_target(self):
        text=ANSWER.replace('gateway.example.com. 33 IN A','unrelated.example.com. 33 IN A')
        result=probe.parse_answer(HOST,text)
        self.assertEqual([row['address'] for row in result['addresses']],['8.8.8.8'])
        with self.assertRaises(probe.ProbeError):
            probe.parse_answer(HOST,text.replace('gateway.example.com. 45 IN A','unrelated.example.com. 45 IN A'))

    def test_rejects_nxdomain_truncation_private_addresses_and_zero_ttl(self):
        for text in (ANSWER.replace('NOERROR','NXDOMAIN'),ANSWER.replace('qr rd ra','qr tc rd ra'),
                ANSWER.replace('8.8.4.4','127.0.0.1'),ANSWER.replace('33 IN A','0 IN A')):
            with self.subTest(text=text),self.assertRaises(probe.ProbeError):
                probe.parse_answer(HOST,text)

    def test_rejects_cname_cycles_and_conflicting_owner_types(self):
        for text in (ANSWER.replace('gateway.example.com. 33 IN A 8.8.4.4',
                'gateway.example.com. 33 IN CNAME dashscope.aliyuncs.com.'),
                ANSWER+'dashscope.aliyuncs.com. 10 IN A 8.8.4.4\n'):
            with self.assertRaises(probe.ProbeError):probe.parse_answer(HOST,text)

    def test_configuration_uses_only_endpoint_settings_and_deduplicates_hosts(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'config'
            path.write_text('LLM_API_KEY=SECRET\nLLM_BASE_URL=https://'+HOST+'/v1\n')
            with patch.dict(probe.os.environ,{},clear=True):hosts=probe.configured_hosts(path)
        self.assertEqual(hosts,[HOST]);self.assertNotIn('SECRET',json.dumps(hosts))

    def test_rejects_credentials_and_non_https_endpoints_without_echoing_them(self):
        for url in ('http://example.com','https://SECRET@example.com',
                'https://example.com/?key=SECRET','https://example.com:444'):
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'config';path.write_text('LLM_BASE_URL='+url)
                with patch.dict(probe.os.environ,{},clear=True),self.assertRaises(probe.ProbeError) as caught:
                    probe.configured_hosts(path)
            self.assertNotIn('SECRET',str(caught.exception))

    def test_dig_has_explicit_resolver_one_attempt_and_no_user_rc(self):
        result=NS(returncode=0,stdout=ANSWER.encode())
        with patch.object(probe.subprocess,'run',return_value=result) as call:
            answer,stamp=probe.resolve('/usr/bin/dig',HOST,'114.114.114.114',probe.time.monotonic()+30)
        command=call.call_args.args[0]
        self.assertEqual(command[:3],['/usr/bin/dig','-r','@114.114.114.114'])
        self.assertIn('+tries=1',command);self.assertIn('+ignore',command)
        self.assertEqual(call.call_args.kwargs['timeout'],5)
        self.assertNotIn('shell',call.call_args.kwargs)
        self.assertEqual(answer['status'],'complete')

    def test_timeout_details_do_not_echo_raw_subprocess_or_exception_data(self):
        error=subprocess.TimeoutExpired(['dig','SECRET'],5,output=b'SECRET_BODY')
        detail=probe.error_detail(error)
        self.assertEqual(detail['category'],'dns_process_timeout')
        self.assertNotIn('SECRET',json.dumps(detail))


class HTTPSTest(unittest.TestCase):
    def test_numeric_dial_retains_hostname_for_certificate_verification_and_sni(self):
        context=MagicMock(check_hostname=True,verify_mode=ssl.CERT_REQUIRED)
        raw=MagicMock()
        with patch.object(probe.ssl,'create_default_context',return_value=context),\
            patch.object(probe.socket,'socket',return_value=raw),\
            patch.object(probe.socket,'getaddrinfo',side_effect=AssertionError('No system DNS')):
            connection=probe.ResolvedHTTPSConnection(HOST,'8.8.4.4',10)
            connection.connect()
        raw.connect.assert_called_once_with(('8.8.4.4',443))
        context.wrap_socket.assert_called_once_with(raw,server_hostname=HOST)
        context.set_alpn_protocols.assert_called_once_with(['http/1.1'])
        self.assertIs(connection.sock,context.wrap_socket.return_value)

    def test_rejects_disabled_certificate_or_hostname_verification(self):
        for context in (NS(check_hostname=False,verify_mode=ssl.CERT_REQUIRED),
                NS(check_hostname=True,verify_mode=ssl.CERT_NONE)):
            with patch.object(probe.ssl,'create_default_context',return_value=context),\
                self.assertRaises(probe.ProbeError):
                probe.ResolvedHTTPSConnection(HOST,'8.8.4.4',10)

    def test_certificate_failure_closes_raw_socket(self):
        context=MagicMock(check_hostname=True,verify_mode=ssl.CERT_REQUIRED)
        context.wrap_socket.side_effect=ssl.SSLCertVerificationError(1,'SECRET_CERT')
        raw=MagicMock()
        with patch.object(probe.ssl,'create_default_context',return_value=context),\
            patch.object(probe.socket,'socket',return_value=raw):
            connection=probe.ResolvedHTTPSConnection(HOST,'8.8.4.4',10)
            with self.assertRaises(ssl.SSLCertVerificationError):connection.connect()
        raw.close.assert_called_once()

    def test_head_has_original_host_no_credentials_no_body_and_no_redirect_following(self):
        connection=MagicMock();response=connection.getresponse.return_value
        response.status=302;event={'head_request_attempts':0}
        with patch.object(probe,'ResolvedHTTPSConnection',return_value=connection):
            probe.https_head(HOST,{'address':'8.8.4.4','ttl_seconds':30},
                probe.time.monotonic(),probe.time.monotonic()+60,event)
        connection.request.assert_called_once_with('HEAD','/',headers={
            'Host':HOST,'Connection':'close','User-Agent':'AskData-E03-connectivity-probe/1'})
        self.assertEqual(event['http_status'],302)
        self.assertFalse(event['model_api_verified'])
        response.read.assert_not_called();connection.close.assert_called_once()

    def test_expired_dns_answer_does_not_open_https_connection(self):
        with patch.object(probe,'ResolvedHTTPSConnection') as connection,self.assertRaises(probe.ProbeError):
            probe.https_head(HOST,{'address':'8.8.4.4','ttl_seconds':1},
                probe.time.monotonic()-2,probe.time.monotonic()+60,{})
        connection.assert_not_called()

    def test_http_unauthorized_proves_connectivity_without_claiming_model_success(self):
        connection=MagicMock();connection.getresponse.return_value.status=401;event={}
        with patch.object(probe,'ResolvedHTTPSConnection',return_value=connection):
            probe.https_head(HOST,{'address':'8.8.4.4','ttl_seconds':30},
                probe.time.monotonic(),probe.time.monotonic()+60,event)
        self.assertTrue(event['tls_verified']);self.assertEqual(event['status'],'complete')
        self.assertFalse(event['model_api_verified'])


class WorkflowTest(unittest.TestCase):
    def report(self):
        return dict(checks=[],dns_query_attempts=0,https_connection_attempts=0,head_request_attempts=0)

    def test_three_rounds_resolve_fresh_and_stop_after_first_successful_address(self):
        report=self.report();answer=probe.parse_answer(HOST,ANSWER)
        def success(*args):args[-1].update(status='complete',head_request_attempts=1)
        with patch.object(probe,'resolve',side_effect=lambda *a:(answer,probe.time.monotonic())) as resolve,\
            patch.object(probe,'https_head',side_effect=success) as head,patch.object(probe.time,'sleep'):
            probe.run_probe([HOST],'114.114.114.114','dig',report,lambda:None)
        self.assertEqual(resolve.call_count,3);self.assertEqual(head.call_count,3)
        self.assertTrue(report['all_rounds_passed']);self.assertEqual(report['head_request_attempts'],3)

    def test_no_dns_answer_never_opens_https_or_model_requests(self):
        report=self.report()
        with patch.object(probe,'resolve',side_effect=probe.ProbeError('dns_query_failed')),\
            patch.object(probe,'https_head') as head,patch.object(probe.time,'sleep'):
            probe.run_probe([HOST],'114.114.114.114','dig',report,lambda:None)
        self.assertEqual(report['run_status'],'failed');head.assert_not_called()
        self.assertEqual(report['dns_query_attempts'],3)
        self.assertEqual(report['head_request_attempts'],0)

    def test_tls_failure_does_not_try_second_address_or_expose_exception_message(self):
        report=self.report();answer=probe.parse_answer(HOST,ANSWER)
        with patch.object(probe,'resolve',return_value=(answer,probe.time.monotonic())),\
            patch.object(probe,'https_head',side_effect=ssl.SSLCertVerificationError(1,'SECRET')) as head,\
            patch.object(probe.time,'sleep'):
            probe.run_probe([HOST],'114.114.114.114','dig',report,lambda:None)
        self.assertEqual(head.call_count,3)
        self.assertEqual(report['head_request_attempts'],0)
        self.assertNotIn('SECRET',json.dumps(report))

    def test_failed_connections_cannot_exceed_two_addresses_per_round(self):
        report=self.report();answer=probe.parse_answer(HOST,ANSWER)
        answer['addresses'].append({'address':'1.1.1.1','ttl_seconds':30})
        with patch.object(probe,'resolve',return_value=(answer,probe.time.monotonic())),\
            patch.object(probe,'https_head',side_effect=TimeoutError('SECRET')) as head,\
            patch.object(probe.time,'sleep'):
            probe.run_probe([HOST],'114.114.114.114','dig',report,lambda:None)
        self.assertEqual(head.call_count,6);self.assertFalse(report['all_rounds_passed'])

    def test_complete_report_preserves_zero_model_and_production_unchanged_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            config=Path(directory)/'config';config.write_text('LLM_API_KEY=SECRET\n')
            output=Path(directory)/'report.json'
            answer=probe.parse_answer(HOST,ANSWER)
            def success(*args):args[-1].update(status='complete',head_request_attempts=1)
            with patch.dict(probe.os.environ,{},clear=True),\
                patch.object(probe.shutil,'which',return_value='/usr/bin/dig'),\
                patch.object(probe.subprocess,'run',return_value=NS(returncode=0,stdout=b'DiG 9.18.39')),\
                patch.object(probe,'wall_deadline',side_effect=lambda:nullcontext()),\
                patch.object(probe,'resolve',side_effect=lambda *a:(answer,probe.time.monotonic())),\
                patch.object(probe,'https_head',side_effect=success),patch.object(probe.time,'sleep'),\
                redirect_stdout(io.StringIO()):
                code=probe.main(['--model-config-file',str(config),'--output',str(output)])
            report=json.loads(output.read_bytes())
            self.assertEqual(code,0);self.assertEqual(report['new_model_request_count'],0)
            self.assertFalse(report['production_transport_changed'])
            self.assertFalse(report['model_api_verified']);self.assertFalse(report['generation_reserved'])
            self.assertNotIn('SECRET',output.read_text())
            with self.assertRaises(probe.ProbeError):
                probe.main(['--model-config-file',str(config),'--output',str(output)])


if __name__=='__main__':unittest.main()
