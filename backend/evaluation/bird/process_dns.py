"""Explicit, bounded BIRD HTTPS transport; no global DNS/socket mutation."""
from __future__ import annotations
from functools import lru_cache
import hashlib
from datetime import datetime, timezone
import http.client
import ipaddress
import json
from pathlib import Path
import re
import socket
import ssl
import subprocess
import time
import urllib.error
from urllib.parse import urlsplit
from .budgets import BirdFailure

POLICY=dict(dns_process_timeout_seconds=5,socket_timeout_seconds=10)
DNS_POLICY=dict(policy_id='bird_process_dns_https_v1',resolver='114.114.114.114',
    executable='/usr/bin/dig',expected_version='9.18.39-0ubuntu0.22.04.7-Ubuntu',
    query_type='A',protocol='UDP',queries_per_http_attempt=1,dig_timeout_seconds=3,
    dig_tries=1,process_timeout_seconds=5,maximum_address_connections_per_attempt=1,
    maximum_cname_depth=8,cache='none; fresh answer each HTTP attempt',
    reject_expired_answers=True,redirects=False,environment_proxy=False,
    tls_certificate_and_hostname_verification=True,system_dns_modified=False,
    global_socket_patched=False,workspace_dependency_lock_required=True)
BASE=Path(__file__).resolve().parents[2]

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
    if statuses==['NXDOMAIN']:raise socket.gaierror(socket.EAI_NONAME,'explicit_resolver_nxdomain')
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


@lru_cache(maxsize=4)
def _tool_binding(path,size,mtime_ns,content_sha):
    source=Path(path)
    result=subprocess.run([path,'-r','-v'],capture_output=True,timeout=3,check=False)
    if result.returncode!=0:raise BirdFailure('process_dns_dependency_unavailable')
    # Ubuntu dig may append an Extended Support Version suffix.
    found=re.search(r'\bDiG\s+([0-9][A-Za-z0-9.+:~_-]*)',
        result.stdout.decode('ascii',errors='replace')+'\n'+result.stderr.decode('ascii',errors='replace'))
    if not found or found[1]!=DNS_POLICY['expected_version']:
        failure=BirdFailure('process_dns_dependency_version_mismatch')
        failure._transport_dependency={'expected_version':DNS_POLICY['expected_version'],
            'actual_version':found[1] if found else 'unreported'}
        raise failure
    return dict(executable=path,version=found[1],sha256=content_sha,
        policy=DNS_POLICY)


def tool_binding():
    try:
        path=Path(DNS_POLICY['executable']).resolve(strict=True);st=path.stat()
        return _tool_binding(str(path),st.st_size,st.st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest())
    except (OSError,subprocess.TimeoutExpired):
        raise BirdFailure('process_dns_dependency_unavailable') from None


def recorded_binding():
    """Require the same binary/version lock in every prepared M3 producer."""
    context=BASE/'m3_context.json'
    if not context.exists():return None  # Non-paired callers have no execution lock.
    try:
        identity=json.loads(context.read_bytes())
        lock=json.loads((Path(identity['workspace'])/'transport_dependency_lock.json').read_bytes())
        if lock['bundle_id']!=identity['bundle_id'] or lock['binding']!=tool_binding():
            raise BirdFailure('process_dns_dependency_lock_mismatch')
        return lock['binding']
    except (KeyError,ValueError,OSError) as error:
        if isinstance(error,BirdFailure):raise
        raise BirdFailure('process_dns_dependency_lock_missing') from None


def request_binding():
    return recorded_binding() or tool_binding()


class Response:
    def __init__(self,connection,response):
        self.connection=connection;self.response=response;self.status=response.status
    def read(self,limit):return self.response.read(limit)
    def close(self):
        try:self.response.close()
        finally:self.connection.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()


def open_url(request,*,timeout,event,allowed_hosts,binding=None):
    """One DNS query, one numeric connection, one HTTP request; no hidden retries."""
    parsed=urlsplit(request.full_url)
    if (parsed.scheme!='https' or parsed.hostname not in allowed_hosts
        or parsed.port not in (None,443) or parsed.username or parsed.password
        or parsed.query or parsed.fragment):raise BirdFailure('process_dns_endpoint_denied')
    host=domain(parsed.hostname);binding=binding or request_binding()
    if binding['policy']!=DNS_POLICY:raise BirdFailure('process_dns_policy_mismatch')
    event['transport_dependency_binding']=binding
    deadline=time.monotonic()+timeout;connection=None
    dns_event={'hostname':host,'resolver':DNS_POLICY['resolver'],'status':'running'}
    event['process_dns']=dns_event
    try:
        try:
            answer,received=resolve(binding['executable'],host,DNS_POLICY['resolver'],deadline)
            dns_event.update(answer)
        except (ProbeError,OSError,ValueError,subprocess.TimeoutExpired) as error:
            detail=error_detail(error);dns_event.update(status='failed',error=detail)
            # Permanent format/security faults do not consume another model attempt.
            permanent=isinstance(error,socket.gaierror) and error.errno==socket.EAI_NONAME or isinstance(error,ProbeError) and str(error) in (
                'dns_flags_invalid_or_truncated','dns_cname_cycle','dns_cname_conflict',
                'dns_address_not_public','dns_record_or_ttl_invalid','dns_answer_invalid')
            raise socket.gaierror(socket.EAI_NONAME if permanent else socket.EAI_AGAIN,
                'explicit_resolver_failed') from None
        records=answer['addresses']
        record=records[event.get('retry',0)%len(records)]
        if time.monotonic()-received>=record['ttl_seconds']:
            raise socket.gaierror(socket.EAI_AGAIN,'explicit_resolver_answer_expired')
        event['selected_address']=record['address']
        connection=ResolvedHTTPSConnection(host,record['address'],
            min(POLICY['socket_timeout_seconds'],remaining(deadline)))
        connection.connect()
        event.update(tls_verified=True,tls_hostname=host,tls_version=connection.sock.version())
        # Connection establishment has its own bound; model response retains its
        # original remaining request allowance (embedding may need >10 seconds).
        connection.sock.settimeout(remaining(deadline))
        path=parsed.path or '/'
        headers=dict(request.header_items());headers['Host']=host;headers['Connection']='close'
        event['http_request_attempted']=True
        connection.request(request.get_method(),path,body=request.data,headers=headers)
        response=connection.getresponse();event['http_status']=response.status
        if 300<=response.status<400 or response.status>=400:
            status=response.status;response.close();connection.close();connection=None
            raise urllib.error.HTTPError(request.full_url,status,'http_error',{},None)
        return Response(connection,response)
    except BaseException:
        if connection is not None:connection.close()
        raise


def readiness(configuration):
    """No credentials or model request: same parser/TLS/HTTP implementation."""
    import urllib.request
    binding=tool_binding()
    hosts=sorted({urlsplit(configuration[key]).hostname for key in ('chat_base','embedding_base','rerank_base')})
    checks=[]
    for host in hosts:
        event={'hostname':host,'retry':0};stamp=time.monotonic()
        try:
            request=urllib.request.Request('https://'+domain(host)+'/',method='HEAD')
            try:
                with open_url(request,timeout=20,event=event,allowed_hosts=hosts,binding=binding):pass
            except urllib.error.HTTPError as error:
                # The root path may be 404. Only TLS plus a valid HTTP response
                # establishes this readiness observation; no model API claim.
                if not (event.get('tls_verified') is True and 200<=error.code<600):raise
            event['passed']=event.get('tls_verified') is True and type(event.get('http_status')) is int
        except Exception as error:
            event.update(passed=False,error=error_detail(error))
        event['elapsed_seconds']=round(time.monotonic()-stamp,3);checks.append(event)
    return dict(passed=bool(checks) and all(c['passed'] for c in checks),checks=checks,
        binding=binding,new_model_request_count=0,model_api_verified=False)


