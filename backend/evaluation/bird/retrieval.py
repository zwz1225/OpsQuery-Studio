"""Domain-only schema index. Inputs are metadata/profile, never question banks or Gold."""
from __future__ import annotations

from dataclasses import asdict
import json
import math
from pathlib import Path
import time

from app.retrieval.store import FieldDocument,LocalSchemaStore
from app.retrieval.graph import SchemaGraphBuilder
from scripts.m2_b_common import digest_file,digest_json,PROTOCOL_SHA256
from .budgets import BirdFailure,Budget
from .coverage import select_fields

INDEX_POLICY='bird_authorized_fields_profiles_v1'


def index_identity(runtime,config):
    from .process_dns import recorded_binding,DNS_POLICY
    return {'policy':INDEX_POLICY,'protocol_sha256':PROTOCOL_SHA256,'source_identity':runtime.identity.public(),
        'query_role':runtime.domain['query_role'],'model':config.public(),
        'code_sha256':{n:digest_file(Path(__file__).with_name(n)) for n in ('retrieval.py','model.py','process_dns.py','runtime.py','native.py','coverage.py','intent.py','relationships.py','units_output.py','demand_relations.py','reviewed_relations.py')},
        'transport_identity':{'policy':DNS_POLICY,'dependency':recorded_binding()},
        'sample_policy':{'distinct':3,'text_characters':64,'order':'native ASC NULLS LAST'}}


def index_path(root,runtime,config):
    return root/runtime.database_id/digest_json(index_identity(runtime,config))/'schema_index.json'


def raw_documents(runtime):
    from .supervisor import IsolatedAgent
    tables=runtime.catalog.tables
    profiles={table['id']:runtime.profile_table(table['id'],[f['name'] for f in table['fields']]) for table in tables}
    with IsolatedAgent() as indexer:
        output=indexer.run({'mode':'index','database_id':runtime.database_id,'tables':tables,'profiles':profiles},
            lambda *a:(_ for _ in ()).throw(BirdFailure('indexer_rpc_denied')),time.monotonic()+60)
    allowed={t['id']+'.'+f['name']:(t['id'],f['name']) for t in tables for f in t['fields']}
    if len(output)!=len(allowed) or {d['doc_id'] for d in output}!=set(allowed):raise BirdFailure('indexer_document_set_mismatch')
    for document in output:
        if document['database_id']!=runtime.database_id or (document['table_id'],document['field_name'])!=allowed[document['doc_id']]:raise BirdFailure('indexer_source_mismatch')
        document['keyword_text']=document['semantic_text'];document['rerank_text']=document['semantic_text']
    return output


def validate_store(store,runtime):
    if store.embedding_source!='text-embedding-v4':raise BirdFailure('index_embedding_source_mismatch')
    allowed={t['id']+'.'+f['name']:(t['id'],f['name']) for t in runtime.catalog.tables for f in t['fields']}
    if len(store.documents)!=len(allowed) or {d.doc_id for d in store.documents}!=set(allowed):raise BirdFailure('index_document_set_mismatch')
    for d in store.documents:
        if not d.active or d.database_id!=runtime.database_id or (d.table_id,d.field_name)!=allowed[d.doc_id] or len(d.dense_vector)!=1024 or not all(type(x) in (int,float) and math.isfinite(x) for x in d.dense_vector):
            raise BirdFailure('index_source_mismatch')
        raw=asdict(d)
        for key in ('dense_vector','schema_version','content_hash','active'):raw.pop(key)
        if digest_json(raw)!=d.content_hash:raise BirdFailure('index_document_digest_mismatch')


def build_index(runtime,config,root,*,progress=None):
    from .model import Models
    if progress is None:progress={}
    progress.update(stage='index_lookup',complete=False,cache_hit=False,
                    model_usage={'model_http_attempts':0,'model_events':[]})
    identity=index_identity(runtime,config);signature=digest_json(identity);path=index_path(root,runtime,config)
    store=LocalSchemaStore(path)
    if store.load(signature,expected_identity=identity):
        validate_store(store,runtime)
        progress.update(stage='complete',complete=True,cache_hit=True)
        return {'path':str(path),'sha256':digest_file(path),'identity':identity,'cache_hit':True,'model_usage':None}
    progress['stage']='authorized_profiles'
    raw=raw_documents(runtime)
    budget=Budget(wall_seconds=3600,total_limit=2*math.ceil(len(raw)/10),chat_limit=0)
    progress['stage']='embedding'
    try:
        vectors=Models(config,budget).embed([d['semantic_text'] for d in raw])
    finally:
        progress['model_usage']=budget.public()
    progress['stage']='index_write'
    documents=[FieldDocument(**r,dense_vector=v,schema_version=signature,content_hash=digest_json(r)) for r,v in zip(raw,vectors)]
    store.replace_all(signature,documents,'text-embedding-v4',cache_identity=identity);validate_store(store,runtime)
    progress.update(stage='complete',complete=True)
    return {'path':str(path),'sha256':digest_file(path),'identity':identity,'cache_hit':False,'model_usage':budget.public()}


def retrieve(runtime,models,path,public_input,*,schema_coverage=False,intent_candidate=False,
             condition_relations=False,relation_output=False,categorical_population=False):
    from evaluation.bird_protocol import validate_agent_input
    validate_agent_input(public_input)
    if condition_relations and (not schema_coverage or not intent_candidate):
        raise BirdFailure('condition_relations_requires_coverage_and_intent')
    if relation_output and not condition_relations:
        raise BirdFailure('relation_output_requires_condition_relations')
    if categorical_population and (not condition_relations or relation_output):
        raise BirdFailure('categorical_population_requires_condition_relations_without_output')
    if public_input['database_id']!=runtime.database_id:raise BirdFailure('retrieval_source_mismatch')
    identity=index_identity(runtime,models.config);store=LocalSchemaStore(path)
    if not store.load(digest_json(identity),expected_identity=identity):raise BirdFailure('prebuilt_index_required')
    validate_store(store,runtime)
    text=public_input['question']+'\n'+public_input['evidence']
    allowed={d.doc_id for d in store.documents};bm25=store.bm25_search(text,30,allowed)
    vector=models.embed([text])[0];dense=store.dense_search(vector,30,allowed)
    fused={}
    for ranked in (bm25,dense):
        for rank,(index,_) in enumerate(ranked,1):fused[index]=fused.get(index,0)+1/(60+rank)
    candidate=sorted(fused,key=lambda i:fused[i],reverse=True)[:40]
    if not candidate:raise BirdFailure('empty_schema_retrieval')
    scores=models.rerank(text,[store.documents[i].rerank_text for i in candidate])
    selected,selection=select_fields(store.documents,candidate,scores,public_input,enabled=schema_coverage)
    intent_selection=None
    if intent_candidate:
        from .intent import expand_fields
        options={'diagnose_rejections':True} if condition_relations else {}
        selected,intent_selection=expand_fields(runtime,store.documents,selected,public_input,**options)
        provider_scores={candidate[p]:s for p,s in scores.items()}
        selected=[(i,provider_scores.get(i,s)) for i,s in selected]
        by_id={d.doc_id:i for i,d in enumerate(store.documents)}
        for decision in intent_selection['decisions']:
            decision['rerank_score']=provider_scores.get(by_id[decision['field_id']])
            decision['score_source']='provider_rerank' if decision['rerank_score'] is not None else 'unranked_authorized_metadata'
    demand_context=None
    if condition_relations:
        from .demand_relations import expand_context
        selected,demand_context=expand_context(runtime,store.documents,selected,public_input,
            intent_added_count=len(intent_selection['added_field_ids']),relation_output=relation_output,
            categorical_population=categorical_population)
    covered=set(selection['coverage_field_ids'])
    intent_added=set(intent_selection['added_field_ids']) if intent_selection else set()
    hits=[{**store.documents[i].public(),'score':score,
           'source':'condition_relation_coverage' if demand_context and store.documents[i].doc_id in demand_context['added_field_ids'] else
                    'intent_coverage' if store.documents[i].doc_id in intent_added else
                    'schema_coverage' if store.documents[i].doc_id in covered else 'retrieval'} for i,score in selected]
    if intent_candidate:
        from .relationships import build_graph
        graph=build_graph(runtime,hits,public_input)
    else:graph=SchemaGraphBuilder(runtime=runtime).build(hits)
    if demand_context is not None:
        from .demand_relations import annotate_graph
        graph=annotate_graph(runtime,graph,demand_context)
    from .diagnostics import retrieval_record
    diagnostics=retrieval_record(store,bm25,dense,candidate,fused,scores,selected,graph,
                                 selection=selection if schema_coverage else None)
    schema_text=SchemaGraphBuilder.context_text(graph)
    if demand_context is not None:
        for condition in graph['condition_relation_context']['admitted_public_conditions']:
            schema_text+='\n公开条件字段候选: '+condition['field_id']+' = '+condition['value']+'；按问题语义使用，样本本身不构成强制谓词。'
        if demand_context['unresolved_required_roles']:
            schema_text+='\n未解决的条件或关联依据: '+', '.join(demand_context['unresolved_required_roles'][:8])+'；不要静默省略业务条件。'
    result={'graph':graph,'schema_text':schema_text,
            'retrieval':{'bm25_count':len(bm25),'dense_count':len(dense),'rrf_count':len(candidate),'selected_count':len(hits),
                'selected_field_ids':[h['doc_id'] for h in hits],'source_identity':runtime.identity.public()},
            'index_sha256':digest_file(path),'_report_diagnostics':diagnostics}
    if schema_coverage:
        result['retrieval'].update(schema_selection_policy=selection['policy'],baseline_field_ids=selection['baseline_field_ids'],
                                   coverage_field_ids=selection['coverage_field_ids'])
    if intent_selection is not None:
        diagnostics['intent_selection']=intent_selection
        # A 0.0 graph score is only a placeholder for metadata outside rerank.
        # A null rerank_score and explicit score_source record that distinction.
        for record in diagnostics['candidates']:
            if record['field_id'] in intent_added:
                record.update(selected=True,selection_reason='selected_intent_coverage')
        diagnostics['selected_field_ids']=[h['doc_id'] for h in hits]
        diagnostics['added_relation_key_field_ids']=[f['id'] for f in graph['fields'] if f['id'] not in set(diagnostics['selected_field_ids'])]
        result['retrieval']['intent_selection']=intent_selection
        result['_intent_selection']=intent_selection
    if demand_context is not None:
        provider_scores={candidate[p]:s for p,s in scores.items()}
        added=set(demand_context['added_field_ids'])
        evicted={v['field_id'] for d in demand_context['decisions']
                 for v in d.get('evicted_fields',[])}
        for decision in demand_context['decisions']:
            decision['field_rerank_scores']={fid:provider_scores.get(by_id[fid])
                                          for fid in decision['added_field_ids']}
        for record in diagnostics['candidates']:
            if record['field_id'] in added:record.update(selected=True,selection_reason='selected_condition_relation_coverage')
            if record['field_id'] in evicted:record.update(selected=False,selection_reason='evicted_for_reviewed_relation_keys')
        demand_context['prior_intent_sample_decisions']=intent_selection['sample_condition_decisions']
        diagnostics['condition_relation_context']=demand_context
        result['retrieval']['condition_relation_policy']=demand_context['policy']
        # Keep raw samples and rejected evidence report-only. The graph carries
        # admitted fields and explicitly annotated candidate equalities only.
    return result
