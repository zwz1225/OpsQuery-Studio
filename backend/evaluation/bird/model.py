"""Frozen external model configuration and shared, bounded HTTP transport."""
from __future__ import annotations

from dataclasses import dataclass,field
import json
import math
import os
from pathlib import Path
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from .budgets import Budget,BirdFailure,hard_deadline
from .process_dns import DNS_POLICY,open_url,recorded_binding

TRANSPORT_POLICY = dict(policy_id='bird_process_dns_transport_v1', max_http_attempts=2,
    temporary_dns_retry_delay_seconds=2, delay_counts_toward_wall_budget=True,
    system_dns_modified=False, ip_pinning=False, tls_verification='stdlib_default',
    embedding_batch_size=10, extra_dns_probes=False,process_dns=DNS_POLICY)


def transport_diagnostic(error):
    """Only types/codes, never exception strings, URLs, headers or response bodies."""
    reason = error.reason if isinstance(error, urllib.error.URLError) else error
    result = dict(exception_type=type(error).__name__, reason_type=type(reason).__name__)
    code = getattr(reason, 'errno', None)
    if type(code) is int: result['errno'] = code
    if isinstance(reason, socket.gaierror):
        result['category'] = 'dns_temporary' if code == socket.EAI_AGAIN else 'dns_permanent'
    elif isinstance(reason, ssl.SSLCertVerificationError): result['category'] = 'tls_certificate'
    elif isinstance(reason, ssl.SSLError): result['category'] = 'tls'
    elif isinstance(reason, TimeoutError): result['category'] = 'timeout'
    elif isinstance(reason, json.JSONDecodeError): result['category'] = 'json_decode'
    else: result['category'] = 'transport_other'
    return result


def dns_retry_pause(budget, event):
    delay = TRANSPORT_POLICY['temporary_dns_retry_delay_seconds']
    if budget.remaining() <= delay: raise BirdFailure('case_wall_timeout')
    event['retry_delay_seconds'] = delay
    with hard_deadline(min(delay + 0.1, budget.remaining()), 'case_wall_timeout'):
        time.sleep(delay)
    budget.remaining()


@dataclass(frozen=True)
class ModelConfig:
    api_key: str=field(repr=False)
    chat_base: str='https://dashscope.aliyuncs.com/compatible-mode/v1'
    embedding_base: str='https://dashscope.aliyuncs.com/compatible-mode/v1'
    rerank_base: str='https://dashscope.aliyuncs.com/compatible-api/v1'
    @classmethod
    def load(cls,path: Path):
        allowed={'LLM_API_KEY','LLM_BASE_URL','EMBEDDING_BASE_URL','RERANK_BASE_URL'}
        values={}
        if path.is_file():
            for line in path.read_text(encoding='utf-8-sig').splitlines():
                key,sep,value=line.strip().partition('=')
                if sep and key in allowed:values[key]=value.strip().strip('"\'')
        for key in allowed:
            if os.getenv(key):values[key]=os.environ[key]
        if not values.get('LLM_API_KEY'):raise BirdFailure('model_credentials_missing')
        chat=values.get('LLM_BASE_URL') or cls.chat_base
        config=cls(values['LLM_API_KEY'],chat,values.get('EMBEDDING_BASE_URL') or chat,values.get('RERANK_BASE_URL') or cls.rerank_base)
        for url in (config.chat_base,config.embedding_base,config.rerank_base):
            parsed=urllib.parse.urlsplit(url)
            if parsed.scheme!='https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise BirdFailure('model_endpoint_invalid')
            if config.api_key in urllib.parse.unquote(url):raise BirdFailure('model_endpoint_contains_credentials')
        return config
    def public(self):
        return {'chat_model':'qwen3.7-plus','embedding_model':'text-embedding-v4','embedding_dimensions':1024,
                'rerank_model':'qwen3-rerank','temperature':0,'enable_thinking':False,
                'chat_base':self.chat_base.rstrip('/'),'embedding_base':self.embedding_base.rstrip('/'),
                'rerank_base':self.rerank_base.rstrip('/')}


class Models:
    def __init__(self,config: ModelConfig,budget: Budget):self.config=config;self.budget=budget
    def post(self,kind,url,payload):
        body=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()
        # Do not log request headers, response error bodies or driver strings.
        for retry in range(2):
            prompt='\n'.join(m['content'] for m in payload['messages']).encode() if kind=='chat' else body
            timeout=self.budget.model_attempt(kind,retry=retry,prompt=prompt)
            event=self.budget.events[-1];event['endpoint_kind']=kind
            hostname=urllib.parse.urlsplit(url).hostname
            event.update(transport_policy_id=TRANSPORT_POLICY['policy_id'],
                         hostname='<redacted>' if self.config.api_key in (hostname or '') else hostname)
            started=time.monotonic()
            try:
                with hard_deadline(timeout,'model_request_timeout'):
                    request=urllib.request.Request(url,data=body,method='POST',headers={
                        'Authorization':'Bearer '+self.config.api_key,'Content-Type':'application/json'})
                    # Environment proxy settings are intentionally not inherited by case workers.
                    allowed={urllib.parse.urlsplit(u).hostname for u in
                        (self.config.chat_base,self.config.embedding_base,self.config.rerank_base)}
                    with open_url(request,timeout=timeout,event=event,allowed_hosts=allowed) as response:
                        status=getattr(response,'status',None)
                        if type(status) is int:event['http_status']=status
                        raw=response.read(16*1024*1024+1)
                    if len(raw)>16*1024*1024:raise BirdFailure('model_response_byte_limit')
                    result=json.loads(raw)
                event['usage']=result.get('usage');event['returned_model']=result.get('model')
                event['status']='complete';self.budget.remaining();return result
            except urllib.error.HTTPError as error:
                event.update(status='http_error',http_status=error.code)
                status=error.code
                try:error.close()
                except Exception:pass  # Preserve the HTTP fault if a broken response cannot close.
                if retry or (status<500 and status!=429):raise BirdFailure('model_http_error') from None
            except (urllib.error.URLError,TimeoutError,json.JSONDecodeError,OSError) as error:
                event['status']='transport_error'
                detail=transport_diagnostic(error);event['transport_diagnostic']=detail
                dns=detail['category'].startswith('dns_')
                if retry or detail['category'] in ('dns_permanent','tls_certificate'):
                    raise BirdFailure('model_dns_error' if dns else 'model_transport_error') from None
                if detail['category']=='dns_temporary':dns_retry_pause(self.budget,event)
            except BirdFailure as error:
                event['status']=error.category
                if retry or error.category!='model_request_timeout':raise
            finally:
                event['attempt_wall_seconds']=round(time.monotonic()-started,3)
        raise BirdFailure('model_transport_error')
    def chat(self,system,user):
        result=self.post('chat',self.config.chat_base.rstrip('/')+'/chat/completions',{
            'model':'qwen3.7-plus','messages':[{'role':'system','content':system},{'role':'user','content':user}],
            'temperature':0,'stream':False,'enable_thinking':False,'max_tokens':4096,'response_format':{'type':'json_object'}})
        usage=result.get('usage') or {}
        if isinstance(usage,dict) and any(type(usage.get(k)) in (int,float) and usage[k]>4096 for k in ('completion_tokens','output_tokens')):
            raise BirdFailure('chat_output_token_limit')
        try:
            raw=result['choices'][0]['message']['content'];value=json.loads(raw)
            if not isinstance(value,dict):raise ValueError()
            return value
        except (KeyError,IndexError,TypeError,ValueError):return {'action':'invalid_model_output'}
    def embed(self,texts):
        vectors=[]
        for start in range(0,len(texts),10):
            batch=texts[start:start+10]
            result=self.post('embedding',self.config.embedding_base.rstrip('/')+'/embeddings',{
                'model':'text-embedding-v4','input':batch,'dimensions':1024,'encoding_format':'float'})
            try:
                items=sorted(result['data'],key=lambda x:x['index'])
                if [x['index'] for x in items]!=list(range(len(batch))):raise ValueError()
                for item in items:
                    vector=item['embedding']
                    if len(vector)!=1024 or not all(type(x) in (int,float) and math.isfinite(x) for x in vector):raise ValueError()
                    norm=math.sqrt(sum(x*x for x in vector)) or 1
                    vectors.append([x/norm for x in vector])
            except (TypeError,KeyError,ValueError):raise BirdFailure('embedding_response_invalid') from None
        return vectors
    def rerank(self,query,texts):
        result=self.post('rerank',self.config.rerank_base.rstrip('/')+'/reranks',{
            'model':'qwen3-rerank','query':query,'documents':texts,'top_n':len(texts),
            'instruct':"Rank database schema fields by relevance to the user's analytics query."})
        try:
            scores={}
            for item in result['results']:
                index=item['index'];score=float(item.get('relevance_score',item.get('score')))
                if type(index) is not int or not 0<=index<len(texts) or index in scores or not math.isfinite(score):raise ValueError()
                scores[index]=max(0,min(1,score))
            if not scores:raise ValueError()
            return scores
        except (KeyError,TypeError,ValueError):raise BirdFailure('rerank_response_invalid') from None
