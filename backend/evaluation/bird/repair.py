"""Bounded SQL repair feedback from the current authorized catalog, never Gold."""
from __future__ import annotations

from copy import deepcopy
from difflib import SequenceMatcher
import hashlib
import json
import re

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.normalize_identifiers import normalize_identifiers
from sqlglot.optimizer.scope import traverse_scope

from .budgets import BirdFailure
from .diagnostics import clipped,encoded,scrub,sql_record,text_record

POLICY='bird_authorized_sql_repair_v2'
FEEDBACK_BYTES=8192
MAX_FIELDS=16
MAX_TABLES=4


def parsed(sql):
    if not isinstance(sql,str) or len(sql.encode('utf-8'))>98304:return None
    try:
        trees=[t for t in sqlglot.parse(sql,read='postgres') if t is not None]
        if len(trees)!=1 or not isinstance(trees[0],exp.Query):return None
        return normalize_identifiers(trees[0],dialect='postgres')
    except (sqlglot.errors.SqlglotError,TypeError,ValueError):return None


def fingerprint(sql):
    tree=parsed(sql)
    canonical=tree.sql(dialect='postgres',comments=False) if tree is not None else sql.strip()
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def position_record(error,sql,*,same_layout=True):
    detail=getattr(error,'_report_diagnostic',None) or {}
    raw=detail.get('statement_position');prefix=getattr(error,'_repair_statement_prefix',None)
    result={'raw_statement_position':int(raw) if isinstance(raw,str) and raw.isdigit() and len(raw)<10 else None,
            'origin':'explain' if prefix else 'original_sql' if prefix=='' else 'unknown',
            'sql_position':None,'line':None,'column':None,'available':False}
    if not same_layout:result['unavailable_reason']='previous_statement_layout_differs';return result
    if prefix is None or result['raw_statement_position'] is None:
        result['unavailable_reason']='statement_context_not_available';return result
    position=result['raw_statement_position']-len(prefix)
    if not 1<=position<=len(sql):result['unavailable_reason']='position_outside_generated_sql';return result
    before=sql[:position-1]
    result.update(sql_position=position,line=before.count('\n')+1,
                  column=len(before.rsplit('\n',1)[-1])+1,available=True)
    return result


def sources(tree,tables):
    if tree is None:return []
    found=[]
    for scope in traverse_scope(tree):
        for alias,source in scope.sources.items():
            if not isinstance(source,exp.Table):continue
            if source.catalog or source.db not in ('','public') or source.name not in tables:continue
            pair=(alias,source.name)
            if pair not in found:found.append(pair)
    return found


def unresolved(tree,message,position):
    if tree is None:return None
    columns=list(tree.find_all(exp.Column))
    if position.get('available'):
        offset=position['sql_position']-1
        for column in columns:
            parts=column.parts
            spans=[(p.meta.get('start'),p.meta.get('end')) for p in parts if isinstance(p,exp.Identifier)]
            spans=[(a,b) for a,b in spans if a is not None and b is not None]
            if spans and min(a for a,b in spans)<=offset<=max(b for a,b in spans):
                return {'name':column.name,'table_alias':column.table}
    # Compare only identifiers already present in the failed SQL; never mine arbitrary text.
    folded=message.lower()
    for column in columns:
        names=[column.sql(dialect='postgres').lower()]
        if any(('column '+name) in folded or ('column "'+name+'"') in folded for name in names):
            return {'name':column.name,'table_alias':column.table}
    return None


def quote(value):return '"'+value.replace('"','""')+'"'


class RepairSession:
    def __init__(self,runtime,secrets=(),public_input=None):
        self.runtime=runtime;self.secrets=tuple(secrets);self.failed={}
        public_input=public_input or {}
        text=str(public_input.get('question',''))+' '+str(public_input.get('evidence',''))
        stop={'the','a','an','is','are','of','in','on','and','or','to','for','with','what','which','name','names','all','list','show','please','it','its','their','that','this','from'}
        self.intent_words={w.rstrip('s') if len(w)>4 else w for w in re.findall(r'[a-z0-9]+',text.lower()) if w not in stop}
        catalog=getattr(runtime,'catalog',None)
        database_id=runtime.identity.public().get('logical_database_id')
        self.tables={t['name']:t for t in getattr(catalog,'tables',[])
                     if t.get('database')==database_id and t.get('id')==database_id+'.'+t['name']}

    def field_hints(self,tree,missing):
        refs=sources(tree,self.tables);groups=[]
        referenced={c.name for c in tree.find_all(exp.Column)} if tree is not None else set()
        target=(missing or {}).get('name','').lower()
        for alias,name in refs[:MAX_TABLES]:
            table=self.tables[name];candidates=[]
            for field in table['fields']:
                terms=[field['name'],field.get('label',''),field.get('description','')]
                similarity=max((SequenceMatcher(None,target,v.lower()).ratio() for v in terms if isinstance(v,str)),default=0) if target else 0
                words=set(re.findall(r'[a-z0-9]+',' '.join(str(v) for v in terms).lower()))
                if target and target in words:similarity=max(similarity,.95)
                intent={w.rstrip('s') if len(w)>4 else w for w in words}
                labels=set(re.findall(r'[a-z0-9]+',(str(field['name'])+' '+str(field.get('label',''))).lower()))
                labels={w.rstrip('s') if len(w)>4 else w for w in labels}
                native=set(re.findall(r'[a-z0-9]+',field['name'].lower()))
                native={w.rstrip('s') if len(w)>4 else w for w in native}
                score=(1 if field['name'] in referenced else 0)+similarity+4*min(1,len(native & self.intent_words))+min(2,len(labels & self.intent_words))+.2*min(2,len(intent & self.intent_words))
                candidates.append((score,field))
            candidates.sort(key=lambda item:item[0],reverse=True)
            groups.append((alias,table,candidates))
        # Balance suggestions across the actual referenced tables, without metadata queries.
        hints=[]
        for rank in range(MAX_FIELDS):
            for alias,table,candidates in groups:
                if rank>=len(candidates):continue
                field=candidates[rank][1]
                hints.append({'table_id':table['id'],'table_name':table['name'],'table_alias':alias,
                    'field_name':field['name'],'type':field.get('type',''),
                    'sql_reference':quote(alias)+'.'+quote(field['name']),
                    'source':'current_authorized_catalog'})
                if len(hints)>=MAX_FIELDS:break
            if len(hints)>=MAX_FIELDS:break
        return hints

    def _safe(self,value):
        if isinstance(value,str):return clipped(scrub(value,self.secrets),256)[0]
        if isinstance(value,list):return [self._safe(v) for v in value]
        if isinstance(value,dict):return {k:self._safe(v) for k,v in value.items()}
        return value

    def source_feedback(self,tree):
        """Explain local reference denial; never invent a PostgreSQL driver error."""
        references=[];seen=set();omitted=0
        if tree is not None:
            for scope in traverse_scope(tree):
                for source in scope.sources.values():
                    if not isinstance(source,exp.Table):continue
                    key=(source.catalog,source.db,source.name)
                    if key in seen:continue
                    seen.add(key)
                    reason=('catalog_qualification_denied' if source.catalog else
                            'physical_schema_denied' if source.db not in ('','public') else
                            'table_not_authorized' if source.name not in self.tables else None)
                    if reason is None:continue
                    if len(references)>=4:omitted+=1;continue
                    safe=lambda value:clipped(scrub(value,self.secrets),96)[0]
                    known=source.name in self.tables
                    references.append({'observed_catalog':safe(source.catalog),'observed_schema':safe(source.db),
                        'observed_table':safe(source.name),'reason':reason,'table_in_current_catalog':known,
                        'allowed_current_source_references':[quote(source.name),'"public".'+quote(source.name)] if known else []})
        value={'origin':'local_sql_policy','logical_database_id':self._safe(self.runtime.identity.public().get('logical_database_id')),
            'physical_schema':'public','allowed_reference_forms':['table','public.table'],
            'rules':['Logical database IDs group authorized tables; they are not physical schema names.',
                     'Use only unqualified tables or the public schema in the current authorized catalog; catalog-qualified references are denied.',
                     'An allowed spelling refers only to the current source; it does not grant access to another source.'],
            'denied_references':references,'omitted_reference_count':omitted}
        while len(encoded(value))>2048 and value['denied_references']:
            value['denied_references'].pop();value['omitted_reference_count']+=1
        return value

    def feedback(self,error,sql,*,duplicate=False,same_layout=True):
        detail=getattr(error,'_report_diagnostic',None) or {}
        message=detail.get('message_primary','')
        tree=parsed(sql);position=position_record(error,sql,same_layout=same_layout)
        missing=unresolved(tree,message,position) if error.sqlstate=='42703' else None
        hints=self.field_hints(tree,missing)
        actions=['Preserve the requested output columns, filters and question meaning. Use only authorized identifiers.']
        if error.sqlstate=='42703':actions.append('Resolve the unknown column using its owning table and authorized field names; do not guess a new name.')
        elif error.sqlstate=='42P10':actions.append('For DISTINCT, ORDER BY expressions must be selected. Restructure the query if needed while preserving the requested final output; do not add unrelated output columns.')
        elif error.sqlstate=='42803':actions.append('Check aggregate and GROUP BY scope while preserving the requested result shape.')
        if error.category=='sql_source_denied':
            actions.append('Fix the denied physical reference using source_policy. The logical database ID is not a schema. Preserve all predicates, joins and requested output meaning.')
        if duplicate:actions.append('This failed SQL was already validated. Stop this case; no further generation or database validation is allowed for this repeated statement.')
        result={'policy':POLICY,'category':error.category,'sqlstate':error.sqlstate,
            'condition':detail.get('condition',error.category),'server_reason':text_record(message,768,self.secrets),
            'failed_sql':sql_record(sql,self.secrets),'position':position,
            'unresolved_column':self._safe(missing),'authorized_fields':self._safe(hints),
            'catalog_scope':'Bounded subset of referenced physical tables in the current authorized runtime.',
            'source_identity':self._safe(self.runtime.identity.public()),
            'guidance':actions,'duplicate_failed_sql':duplicate,'retryable':not duplicate,
            'sql_fingerprint':fingerprint(sql),'feedback_utf8_byte_limit':FEEDBACK_BYTES,
            'omitted_authorized_fields':0}
        if error.category=='sql_source_denied':
            result['source_policy']=self.source_feedback(tree)
            result['local_reason']=text_record('Source reference denied by local SQL policy. Allowed physical schema: public; unqualified authorized tables are also allowed. See denied_references for the observed schema/catalog/table.',768,self.secrets)
        if getattr(error,'_intent_violations',None):
            from .intent import POLICY as INTENT_POLICY
            result['intent_policy']=INTENT_POLICY
            result['intent_violations']=self._safe(error._intent_violations)
            result['guidance'].append('Repair these public-intent constraints while preserving all other requested conditions and result shape.')
        # Keep original SQL hash/length while bounding the copy carried in the next prompt.
        text=result['failed_sql']['text']
        if text is not None:
            result['failed_sql']['text'],extra=clipped(text,2048)
            result['failed_sql']['truncated'] |= extra
        while len(encoded(result))>FEEDBACK_BYTES and result['authorized_fields']:
            result['authorized_fields'].pop();result['omitted_authorized_fields']+=1
        if 'intent_violations' in result:
            result['omitted_intent_violations']=0
            while len(encoded(result))>FEEDBACK_BYTES and result['intent_violations']:
                result['intent_violations'].pop();result['omitted_intent_violations']+=1
        return result

    def remember(self,error,sql):
        # Parser/analysis errors are deterministic under the verified read-only source.
        # Timeouts/connection failures are deliberately not memoized.
        policy_errors={'invalid_sql_input','sql_parse_error','readonly_query_required','forbidden_sql_operation',
            'sql_function_denied','sql_source_denied','qualified_function_denied','user_type_denied','table_function_denied','intent_contract_violation'}
        if error.sqlstate and error.sqlstate.startswith('42') or error.category in policy_errors:
            self.failed[fingerprint(sql)]=(error,sql)

    def repeated(self,sql):
        old=self.failed.get(fingerprint(sql))
        if old is None:return None
        error,previous=old
        failure=BirdFailure('repeated_invalid_sql',error.sqlstate)
        failure._report_diagnostic=deepcopy(getattr(error,'_report_diagnostic',None))
        failure._repair_statement_prefix=getattr(error,'_repair_statement_prefix',None)
        return failure,self.feedback(error,sql,duplicate=True,same_layout=sql==previous)
