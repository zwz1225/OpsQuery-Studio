"""Standalone bounded DNS/HTTPS probe; no model requests or system changes.

Uses existing BIND dig for explicit resolver queries and verified HTTPS with the
original hostname. This is preparation evidence, never a paired experiment.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import ssl
import subprocess
import time
from urllib.parse import urlsplit
import uuid


POLICY = dict(policy_id='m3_e03_process_dns_https_probe_v1', rounds=3,
    resolver_queries_per_host_per_round=1, dns_query_type='A', dns_protocol='UDP',
    dig_timeout_seconds=3, dig_maximum_tries=1, dns_process_timeout_seconds=5,
    maximum_https_addresses_per_round=2, socket_timeout_seconds=10,
    round_delay_seconds=2, total_wall_seconds=120, port=443,
    http_method='HEAD', http_path='/', follow_redirects=False,
    authorization_sent=False, model_requests=0, system_dns_modified=False,
    global_socket_patched=False, fixed_service_ip=False,
    tls_certificate_and_hostname_verification=True, environment_proxy_used=False,
    address_cache='none; fresh DNS answer every round; reject expired answers')
URL_DEFAULTS = {'LLM_BASE_URL': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'EMBEDDING_BASE_URL': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'RERANK_BASE_URL': 'https://dashscope.aliyuncs.com/compatible-api/v1'}


class ProbeError(ValueError):
    pass


def require(value, category):
    if not value:
        raise ProbeError(category)


def now():
    return datetime.now(timezone.utc).isoformat()


def domain(value):
    name=value.lower().rstrip('.')
    require(len(name)<=253 and '.' in name and all(re.fullmatch(
        r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in name.split('.')),
        'invalid_hostname')
    try:
        ipaddress.ip_address(name)
    except ValueError:
        return name
    raise ProbeError('hostname_must_be_a_domain')


def configured_hosts(path):
    # Deliberately parse endpoint settings only; do not load or use any API key.
    values={}
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        key,sep,value=line.strip().partition('=')
        if sep and key in URL_DEFAULTS:
            values[key]=value.strip().strip('\"\'')
    for key in URL_DEFAULTS:
        if os.environ.get(key):
            values[key]=os.environ[key]
    chat=values.get('LLM_BASE_URL') or URL_DEFAULTS['LLM_BASE_URL']
    endpoints=(chat, values.get('EMBEDDING_BASE_URL') or chat,
        values.get('RERANK_BASE_URL') or URL_DEFAULTS['RERANK_BASE_URL'])
    hosts=[]
    for endpoint in endpoints:
        parsed=urlsplit(endpoint)
        require(parsed.scheme=='https' and parsed.hostname and not parsed.username
            and not parsed.password and not parsed.query and not parsed.fragment
            and parsed.port in (None,443), 'invalid_endpoint')
        hosts.append(domain(parsed.hostname))
    return sorted(set(hosts))


def error_detail(error):
    # Never retain exception strings, subprocess stdout/stderr or HTTP headers.
    result={'exception_type':type(error).__name__}
    if isinstance(error,ProbeError):
        result['category']=str(error)  # All ProbeError messages are fixed categories.
    elif isinstance(error,ssl.SSLCertVerificationError):
        result['category']='tls_certificate_verification_failed'
    elif isinstance(error,ssl.SSLError):
        result['category']='tls_failed'
    elif isinstance(error,subprocess.TimeoutExpired):
        result['category']='dns_process_timeout'
    elif isinstance(error,TimeoutError):
        result['category']='connection_timeout'
    else:
        result['category']='probe_operation_failed'
    if type(getattr(error,'errno',None)) is int:
        result['errno']=error.errno
    return result


def parse_answer(host, text):
    require(len(text.encode('utf-8'))<=65536,'dns_response_limit')
    statuses=re.findall(r'\bstatus: ([A-Z]+),',text)
    require(statuses==['NOERROR'],'dns_status_not_noerror')
    flags=re.findall(r';; flags: ([^;]+);',text)
    require(len(flags)==1 and 'qr' in flags[0].split()
        and 'tc' not in flags[0].split(),'dns_flags_invalid_or_truncated')
    records=[]
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith(';'):
            continue
        parts=line.split()
        require(len(parts)==5 and parts[1].isdigit() and parts[2]=='IN',
            'dns_answer_invalid')
        owner,ttl,_,kind,value=parts
        require(kind in ('A','CNAME') and 0<int(ttl)<=2**31-1,'dns_record_or_ttl_invalid')
        records.append((domain(owner),int(ttl),kind,value))
    require(0<len(records)<=64,'dns_answer_count_invalid')
    current=domain(host);seen=set();chain=[];ttls=[]
    for _ in range(9):
        require(current not in seen,'dns_cname_cycle')
        seen.add(current)
        owned=[row for row in records if row[0]==current]
        aliases=[row for row in owned if row[2]=='CNAME']
        addresses=[row for row in owned if row[2]=='A']
        if aliases:
            require(len(aliases)==1 and not addresses,'dns_cname_conflict')
            target=domain(aliases[0][3]);ttls.append(aliases[0][1])
            chain.append({'owner':current,'target':target,'ttl_seconds':aliases[0][1]})
            current=target
            continue
        require(addresses,'dns_no_reachable_ipv4_answer')
        found={}
        for _,ttl,_,address in addresses:
            ip=ipaddress.IPv4Address(address)
            require(ip.is_global,'dns_address_not_public')
            ttl=min([ttl,*ttls])
            found[str(ip)]=min(ttl,found.get(str(ip),ttl))
        return {'cname_chain':chain,'addresses':[
            {'address':ip,'ttl_seconds':found[ip]} for ip in sorted(found)]}
    raise ProbeError('dns_cname_depth_limit')


def remaining(deadline):
    value=deadline-time.monotonic()
    require(value>0,'probe_wall_timeout')
    return value


def resolve(dig, host, resolver, deadline):
    started=time.monotonic()
    # -r ignores ~/.digrc. Literal resolver/host are validated before use.
    command=[dig,'-r','@'+resolver,domain(host),'A','+time=3','+tries=1',
        '+noall','+comments','+answer','+notcp','+ignore']
    result=subprocess.run(command,capture_output=True,check=False,
        timeout=min(POLICY['dns_process_timeout_seconds'],remaining(deadline)))
    require(result.returncode==0,'dns_query_failed')
    received=time.monotonic()
    answer=parse_answer(host,result.stdout.decode('ascii',errors='strict'))
    answer.update(status='complete',resolver=resolver,query_type='A',
        received_at=now(),elapsed_seconds=round(received-started,3))
    # Internal monotonic timestamps do not become reusable address-map files.
    return answer,received


class ResolvedHTTPSConnection(http.client.HTTPSConnection):
    """Dial the DNS answer while TLS and HTTP retain the original hostname."""
    def __init__(self,host,address,timeout):
        self.address=str(ipaddress.IPv4Address(address))
        context=ssl.create_default_context()
        require(context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED,
            'tls_verification_not_enabled')
        context.set_alpn_protocols(['http/1.1'])
        super().__init__(domain(host),443,timeout=timeout,context=context)

    def connect(self):
        require(not self._tunnel_host,'https_tunnel_not_allowed')
        raw=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        try:
            raw.settimeout(self.timeout)
            raw.connect((self.address,443))
            self.sock=self._context.wrap_socket(raw,server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def https_head(host,record,received,deadline,event):
    require(time.monotonic()-received<record['ttl_seconds'],'dns_answer_expired')
    connection=ResolvedHTTPSConnection(host,record['address'],
        min(POLICY['socket_timeout_seconds'],remaining(deadline)))
    stamp=time.monotonic()
    try:
        connection.connect()
        event.update(tls_verified=True,tls_version=connection.sock.version(),
            sni_hostname=host,http_host=host)
        event['head_request_attempts']=1
        connection.request('HEAD','/',headers={'Host':host,'Connection':'close',
            'User-Agent':'AskData-E03-connectivity-probe/1'})
        response=connection.getresponse()
        try:
            require(200<=response.status<600,'http_status_invalid')
            event.update(status='complete',http_status=response.status,
                model_api_verified=False)
        finally:
            response.close()
    finally:
        event['elapsed_seconds']=round(time.monotonic()-stamp,3)
        connection.close()


@contextmanager
def wall_deadline():
    require(hasattr(signal,'setitimer'),'probe_requires_linux_timer')
    old=signal.getsignal(signal.SIGALRM)
    def expired(*args):
        raise ProbeError('probe_wall_timeout')
    signal.signal(signal.SIGALRM,expired)
    previous=signal.setitimer(signal.ITIMER_REAL,POLICY['total_wall_seconds'])
    started=time.monotonic()
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,old)
        if previous[0]:
            signal.setitimer(signal.ITIMER_REAL,max(.001,
                previous[0]-(time.monotonic()-started)),previous[1])


def checkpoint(path,report):
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temp.open('x',encoding='utf-8') as stream:
            json.dump(report,stream,ensure_ascii=False,indent=2,allow_nan=False)
            stream.write('\n')
        os.replace(temp,path)
    finally:
        if temp.exists():
            temp.unlink()


def run_probe(hosts,resolver,dig,report,save):
    deadline=time.monotonic()+POLICY['total_wall_seconds']
    for number in range(1,POLICY['rounds']+1):
        for host in hosts:
            entry={'round':number,'hostname':host,'passed':False,'https_checks':[]}
            report['checks'].append(entry)
            try:
                report['dns_query_attempts']+=1
                answer,received=resolve(dig,host,resolver,deadline)
                entry['dns']=answer
                for record in answer['addresses'][:POLICY['maximum_https_addresses_per_round']]:
                    remaining(deadline)
                    event={'address':record['address'],'status':'running',
                        'tls_verified':False,'head_request_attempts':0}
                    entry['https_checks'].append(event)
                    report['https_connection_attempts']+=1
                    try:
                        https_head(host,record,received,deadline,event)
                        entry['passed']=True
                    except Exception as error:
                        event.update(status='failed',error=error_detail(error))
                        if isinstance(error,ssl.SSLCertVerificationError):
                            break
                    finally:
                        report['head_request_attempts']+=event['head_request_attempts']
                    if entry['passed']:
                        break
            except Exception as error:
                entry['error']=error_detail(error)
            save()
            remaining(deadline)
        if number<POLICY['rounds']:
            time.sleep(min(POLICY['round_delay_seconds'],remaining(deadline)))
    report['all_rounds_passed']=len(report['checks'])==len(hosts)*POLICY['rounds'] and all(
        row['passed'] for row in report['checks'])
    report['run_status']='complete' if report['all_rounds_passed'] else 'failed'


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-config-file',type=Path,required=True)
    parser.add_argument('--resolver',default='114.114.114.114')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    source=Path(__file__).resolve();config=args.model_config_file.resolve()
    output=args.output.resolve()
    require(output.suffix=='.json' and output not in (source,config), 'invalid_output_path')
    require(not output.exists(),'choose_new_report_path')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:
        stream.write('{"run_status":"running"}\n')
    report=dict(stage='M3 E03 process-local resolver and verified HTTPS readiness',
        run_status='running',started_at=now(),policy=POLICY,checks=[],errors=[],
        script_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        formal_benchmark=False,paired_experiment=False,production_transport_changed=False,
        model_api_verified=False,new_model_request_count=0,postgresql_connected=False,
        generation_reserved=False,dns_query_attempts=0,https_connection_attempts=0,
        head_request_attempts=0,all_rounds_passed=False)
    started=time.monotonic()
    try:
        require(config.is_file(),'model_config_file_missing')
        resolver=str(ipaddress.IPv4Address(args.resolver))
        require(ipaddress.ip_address(resolver).is_global,'resolver_must_be_public_ipv4')
        hosts=configured_hosts(config)
        report.update(resolver=resolver,endpoint_hosts=hosts)
        dig=shutil.which('dig')
        require(dig,'dig_not_installed')
        with wall_deadline():
            version=subprocess.run([dig,'-r','-v'],capture_output=True,timeout=3,check=False)
            require(version.returncode==0,'dig_version_check_failed')
            text=version.stdout.decode('ascii',errors='replace').strip()
            match=re.fullmatch(r'DiG ([A-Za-z0-9.+:~_-]{1,100})',text)
            report['dig_version']=match[1] if match else 'unreported'
            run_probe(hosts,resolver,dig,report,lambda:checkpoint(output,report))
    except (Exception,KeyboardInterrupt) as error:
        report.update(run_status='failed',all_rounds_passed=False)
        report['errors'].append(error_detail(error))
    finally:
        report.update(finished_at=now(),elapsed_seconds=round(time.monotonic()-started,3))
        checkpoint(output,report)
    print(json.dumps({key:report.get(key) for key in ('run_status','all_rounds_passed',
        'endpoint_hosts','resolver','dns_query_attempts','https_connection_attempts',
        'head_request_attempts','new_model_request_count','errors')},ensure_ascii=False,indent=2))
    return 0 if report['run_status']=='complete' else 1


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (Exception,KeyboardInterrupt) as error:
        print(json.dumps({'run_status':'failed','error':error_detail(error)},ensure_ascii=False))
        raise SystemExit(1)
