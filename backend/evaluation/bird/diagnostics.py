"""Bounded, report-only development evidence. Never sent to Agent or indexer."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import re

POLICY = 'bird_development_observation_v1'
SQL_BYTES = 8192
REASON_BYTES = 2048
GRAPH_BYTES = 98304
TOTAL_BYTES = 393216
MAX_ATTEMPTS = 9


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def clipped(text, limit):
    raw=text.encode('utf-8')
    return raw[:limit].decode('utf-8',errors='ignore'), len(raw)>limit


def scrub(text, secrets=()):
    """Known credential values plus recognizable credential assignments/DSNs."""
    for secret in sorted({s for s in secrets if isinstance(s,str) and s},key=len,reverse=True):
        text=text.replace(secret,'[REDACTED]')
    text=re.sub(r'(?i)postgres(?:ql)?://[^\s<>"\']+', '[REDACTED_DSN]', text)
    text=re.sub(r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+', 'Bearer [REDACTED]', text)
    text=re.sub(r'''(?ix)\b(password|pg_password|llm_api_key|api[_\ -]?key|authorization|access[_\ -]?token|secret)\s*[:=]\s*(?:"[^"]*"|'[^']*'|[^\s,;]+)''',
                r'\1=[REDACTED]',text)
    text=re.sub(r'\bsk-[A-Za-z0-9_-]{12,}\b','[REDACTED_KEY]',text)
    return ''.join(c if c in '\n\t' or ord(c)>=32 else ' ' for c in text)


def text_record(value, limit=REASON_BYTES, secrets=()):
    if not isinstance(value,str):return {'text':None,'provided':False,'truncated':False,'redacted':False}
    safe=scrub(value,secrets);text,truncated=clipped(safe,limit)
    return {'text':text,'provided':True,'original_utf8_bytes':len(value.encode('utf-8')),
            'truncated':truncated,'redacted':safe!=value}


def sql_record(value, secrets=()):
    result=text_record(value,SQL_BYTES,secrets)
    result['original_sha256']=hashlib.sha256(value.encode('utf-8')).hexdigest() if isinstance(value,str) else None
    return result


def pg_error_fields(error):
    """Do not call str(error), or read detail/hint/context/internal query/DSN."""
    state=getattr(error,'sqlstate',None)
    if not isinstance(state,str) or not re.fullmatch(r'[A-Z0-9]{5}',state):return None
    names={'42703':'undefined_column','42P10':'invalid_column_reference','42P01':'undefined_table',
           '42601':'syntax_error','42803':'grouping_error','42883':'undefined_function','42804':'datatype_mismatch'}
    result={'sqlstate':state,'condition':names.get(state,'database_error')}
    diag=getattr(error,'diag',None)
    # Only parsing/analysis errors get a primary message; value errors can quote data.
    if state.startswith('42') and diag is not None:
        for key in ('message_primary','statement_position','schema_name','table_name','column_name'):
            value=getattr(diag,key,None)
            if not isinstance(value,str):continue
            # No prefix of an oversized message is retained before secret scrubbing.
            if len(value.encode('utf-8'))>8192:result[key]='[OMITTED_OVERSIZED]'
            else:result[key]=value
    return result


def retrieval_record(store,bm25,dense,candidates,fused,scores,selected,graph,*,selection=None):
    chosen={i for i,_ in selected}
    b={i:(rank,score) for rank,(i,score) in enumerate(bm25,1)}
    d={i:(rank,score) for rank,(i,score) in enumerate(dense,1)}
    ranked=sorted(((candidates[i],score) for i,score in scores.items()),key=lambda x:x[1],reverse=True)
    rerank_positions={i:rank for rank,(i,_) in enumerate(ranked,1)}
    by_index={candidates[i]:score for i,score in scores.items()}
    records=[]
    for rank,index in enumerate(candidates,1):
        score=by_index.get(index)
        reason=('selected' if index in chosen else 'rerank_not_returned' if score is None
                else 'below_threshold' if score<.55 else 'beyond_top20')
        records.append({'field_id':store.documents[index].doc_id,'rrf_rank':rank,'rrf_score':fused[index],
            'bm25_rank':b.get(index,(None,None))[0],'bm25_score':b.get(index,(None,None))[1],
            'dense_rank':d.get(index,(None,None))[0],'dense_score':d.get(index,(None,None))[1],
            'rerank_rank':rerank_positions.get(index),'rerank_score':score,'selected':index in chosen,'selection_reason':reason})
        if selection is not None:records[-1].update(selection['candidate_decisions'][index])
    selected_ids=[store.documents[i].doc_id for i,_ in selected]
    result={'candidate_count':len(candidates),'candidates':records[:40],
        'selection_policy':{'threshold':.55,'max_fields':20,'score_representation':'provider score clamped to [0,1] by existing broker'},
        'selected_field_ids':selected_ids,
        'schema_graph':deepcopy(graph),
        'relation_key_field_ids':[f['id'] for f in graph.get('fields',[]) if f.get('source')=='relation_key'],
        'added_relation_key_field_ids':[f['id'] for f in graph.get('fields',[]) if f['id'] not in set(selected_ids)]}
    if selection is not None:
        result['selection_policy'].update(selection['policy'])
        result.update(baseline_field_ids=selection['baseline_field_ids'],coverage_field_ids=selection['coverage_field_ids'],
                      anchored_table_ids=selection['anchored_table_ids'])
    return result


class Recorder:
    def __init__(self,secrets=()):
        self.secrets=tuple(secrets);self.events=[];self.retrieval=None
        self.last_clarification=None;self.omitted_events=0

    def _safe(self,value,depth=0):
        if depth>10:return '[DEPTH_LIMIT]'
        if isinstance(value,str):return clipped(scrub(value,self.secrets),2048)[0]
        if value is None or type(value) in (bool,int):return value
        if type(value) is float:return value if math.isfinite(value) else None
        if isinstance(value,list):return [self._safe(v,depth+1) for v in value[:256]]
        if isinstance(value,dict):return {str(k):self._safe(v,depth+1) for k,v in list(value.items())[:64]}
        return '[UNSUPPORTED_DIAGNOSTIC_VALUE]'

    def set_retrieval(self,value):
        if not isinstance(value,dict):return
        safe=self._safe(value);graph=safe.pop('schema_graph',{})
        raw=encoded(graph)
        original=value.get('schema_graph',{})
        complete=len(raw)<=GRAPH_BYTES and graph==original
        safe['schema_graph']={'value':graph if len(raw)<=GRAPH_BYTES else None,
            'complete':complete,'utf8_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'omission_reason':'graph_byte_limit' if len(raw)>GRAPH_BYTES else
                None if complete else 'metadata_redacted_or_truncated'}
        self.retrieval=safe

    def append(self,event):
        # At most 9 generation + 9 validation + 3 SQL events.
        if len(self.events)>=21:self.omitted_events+=1;return
        self.events.append(event)

    def model_decision(self,decision,sql_round):
        decision=decision if isinstance(decision,dict) else {}
        action=decision.get('action')
        event={'kind':'model_decision','sql_round':sql_round,
            'action':action if action in ('query','clarify') else 'invalid_model_output',
            'sql':sql_record(decision.get('sql'),self.secrets),
            'clarification_reason':text_record(decision.get('reason'),secrets=self.secrets)}
        self.append(event)
        if action=='clarify':self.last_clarification=event['clarification_reason']

    def operation(self,kind,sql_round,sql,*,valid=None,error=None,repair_feedback=None):
        event={'kind':kind,'sql_round':sql_round,'sql':sql_record(sql,self.secrets)}
        if valid is not None:event['success']=bool(valid)
        if error is not None:
            # Only the existing public error plus whitelisted PostgreSQL diagnostic fields.
            event['error']=error.public()
            detail=getattr(error,'_report_diagnostic',None)
            if detail:event['validation_reason']=self._safe(detail)
        if repair_feedback is not None:event['repair_feedback']=deepcopy(repair_feedback)
        self.append(event)

    def public(self):
        result={'policy':POLICY,'report_only':True,'limits':{'sql_text_utf8_bytes':SQL_BYTES,
            'reason_utf8_bytes':REASON_BYTES,'schema_graph_utf8_bytes':GRAPH_BYTES,'total_utf8_bytes':TOTAL_BYTES,
            'max_events':21},'retrieval':self.retrieval,'attempts':self.events,
            'clarification_reason':self.last_clarification,'omitted_events':self.omitted_events}
        if len(encoded(result))>TOTAL_BYTES:
            # Preserve bounded SQL events and an explicit flag rather than a partial graph.
            result['retrieval']={'omitted':'total_diagnostic_byte_limit'}
        if len(encoded(result))>TOTAL_BYTES:
            result['attempts']=[];result['omitted_events']=len(self.events)+self.omitted_events
        return result
