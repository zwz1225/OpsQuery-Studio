"""M3 E02 public requirements, source-bound candidates and safe field closure."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

from app.retrieval.store import FieldDocument,LocalSchemaStore
from evaluation.bird.budgets import BirdFailure
from evaluation.bird.demand_relations import (annotate_graph, demands, expand_context,
    relation_candidates, validate_options)
from evaluation.bird.evidence import ACCEPTED_VALIDATION_SHA
from evaluation.bird.reviewed_relations import REVIEWED_RELATIONS
from evaluation.bird.retrieval import index_identity,retrieve
from evaluation.bird.diagnostics import Recorder
from scripts.m2_b_common import digest_json


def fixture(which='debit_card_specializing', *, extra=0):
    row=deepcopy(next(x for x in REVIEWED_RELATIONS if x['source_identity']['logical_database_id']==which))
    db=which
    if which=='debit_card_specializing':
        specs={'yearmonth':[('date','text',[]),('consumption','bigint',[]),('customerid','bigint',[])],
            'customers':[('currency','text',['CZK']),('customerid','bigint',[])]}
        question='Which year recorded the most consumption of gas paid in CZK?'
        evidence='The first 4 strings of the Date values in the yearmonth table can represent year.'
        selected_names=('yearmonth.date','yearmonth.consumption')
    else:
        specs={'cards':[('uuid','text',[]),('subtypes','text',[]),('supertypes','text',[])],
            'foreign_data':[('uuid','text',[]),('language','text',['German'])]}
        question='Lists all types of cards in German.'
        evidence='German refer to language; all types refer to the subtypes, supertypes; subtypes is not null AND supertypes is not null'
        selected_names=('cards.subtypes','cards.supertypes','foreign_data.language')
    specs[next(iter(specs))]+=[(f'filler{i}','text',[]) for i in range(extra)]
    tables=[];docs=[]
    for name,fields in specs.items():
        tid=db+'.'+name;definitions=[]
        for field,kind,samples in fields:
            definitions.append(dict(name=field,label=field,type=kind,role='primary_key' if field=='customerid' and name=='customers' else 'field'))
            docs.append(NS(doc_id=tid+'.'+field,database_id=db,table_id=tid,field_name=field,
                field_label=field,field_type=kind,field_role='field',profile='',
                samples=[['text',v] for v in samples]))
        tables.append(dict(id=tid,name=name,label=name,description='authorized test table',
            database=db,physical_schema='public',fields=definitions))
    identity=row['source_identity']
    runtime=NS(database_id=db,identity=NS(public=lambda:identity),domain=dict(query_role=row['query_role']),
        catalog=NS(version=identity['catalog_version'],tables=tables,relations=[]),
        verification=dict(live_target_verified=True,role=row['query_role'],
            accepted_validation_sha256=ACCEPTED_VALIDATION_SHA,
            authorized_data_version=identity['data_version'],authorized_catalog_version=identity['catalog_version']))
    p=dict(case_id='BIRD-PG-9000',database_id=db,dialect='postgres',question=question,evidence=evidence)
    selected=[(i,.8) for i,d in enumerate(docs) if d.doc_id.split(db+'.',1)[1] in selected_names]
    return runtime,docs,selected,p,row


def population_fixture(*, extra=0):
    runtime,docs,selected,public,row=fixture(extra=extra)
    table=next(t for t in runtime.catalog.tables if t['name']=='customers')
    table['fields'].append(dict(name='segment',label='client segment',type='text',role='field'))
    docs.append(NS(doc_id='debit_card_specializing.customers.segment',
        database_id=runtime.database_id,table_id=table['id'],field_name='segment',
        field_label='client segment',field_type='text',field_role='field',profile='',
        samples=[['text','SME']]))
    selected.append((next(i for i,d in enumerate(docs) if d.doc_id=='debit_card_specializing.yearmonth.customerid'),.8))
    public['question']='What was the gas consumption peak month for SME customers in 2013?'
    public['evidence']='Year 2013 can be presented as Between 201301 And 201312; the 5th and 6th string of date can refer to month.'
    return runtime,docs,selected,public,row


class ConditionAndRelationTest(unittest.TestCase):
    def test_public_category_closes_1480_field_and_keys_only_when_enabled(self):
        r,docs,selected,p,_=population_fixture()
        old,old_trace=expand_context(r,docs,selected,p)
        self.assertEqual(old,selected)
        self.assertEqual(old_trace['sample_hint_decisions'][0]['field_id'],
                         'debit_card_specializing.customers.segment')
        new,trace=expand_context(r,docs,selected,p,categorical_population=True)
        self.assertEqual({docs[i].doc_id for i,_ in new}-{docs[i].doc_id for i,_ in selected},
            {'debit_card_specializing.customers.segment','debit_card_specializing.customers.customerid'})
        self.assertEqual(trace['decisions'][0]['decision_reason'],
                         'public_population_and_keys_admitted_atomically')
        self.assertEqual(trace['decisions'][0]['text'],'SME customers')
        self.assertEqual(trace['policy']['policy_id'],'bird_public_categorical_population_context_v1')
        graph=annotate_graph(r,dict(tables=[],fields=[],joins=[]),trace)
        self.assertEqual(graph['joins'][0]['relation_type'],'reviewed_candidate')
        self.assertFalse(graph['joins'][0]['declared_foreign_key'])
        self.assertIsNone(graph['joins'][0]['join_type'])
        condition=graph['condition_relation_context']['admitted_public_conditions'][0]
        self.assertEqual(condition['field_id'],'debit_card_specializing.customers.segment')
        self.assertFalse(condition['mandatory'])

    def test_public_category_requires_explicit_unambiguous_entity_scope(self):
        r,docs,selected,p,_=population_fixture()
        for question in ('What was the peak month for customers in 2013?',
                         'SME plan peak month for customers in 2013?',
                         'What was the peak month for not SME customers?',
                         'What was the peak month for SME customers or others?',
                         'For example SME customers: what was the peak month?'):
            p['question']=question
            result,trace=expand_context(r,docs,selected,p,categorical_population=True)
            self.assertEqual(result,selected,question)
            self.assertFalse(any(d['selected'] for d in trace['decisions']),question)
        p['question']='What was the peak month for SME customers in 2013?'
        p['case_id']='BIRD-PG-9999'
        self.assertEqual(len(expand_context(r,docs,selected,p,categorical_population=True)[0]),5)

    def test_public_category_unique_owner_and_source_binding_required(self):
        r,docs,selected,p,row=population_fixture()
        other=deepcopy(next(d for d in docs if d.field_name=='segment'))
        other.table_id='debit_card_specializing.gasstations';other.doc_id=other.table_id+'.segment'
        docs.append(other)
        r.catalog.tables.append(dict(id=other.table_id,name='gasstations',label='gasstations',
            description='authorized test table',database=r.database_id,physical_schema='public',
            fields=[dict(name='segment',label='chain segment',type='text',role='field')]))
        self.assertEqual(expand_context(r,docs,selected,p,categorical_population=True)[0],selected)
        docs.pop();r.catalog.tables.pop()
        for change in ('identity','role','catalog','data','verification'):
            bad=deepcopy(r);bad.identity=NS(public=lambda:dict(r.identity.public()))
            if change=='identity':bad.identity.public=lambda:{**r.identity.public(),'source_id':'other'}
            if change=='role':bad.domain['query_role']='other'
            if change=='catalog':bad.catalog.version='other'
            if change=='data':bad.verification['authorized_data_version']='other'
            if change=='verification':bad.verification['live_target_verified']=False
            self.assertEqual(expand_context(bad,docs,selected,p,categorical_population=True)[0],selected,change)
        reviewed=deepcopy(row);reviewed['orphan_rows']=1
        self.assertEqual(expand_context(r,docs,selected,p,reviewed=[reviewed],categorical_population=True)[0],selected)

    def test_public_category_caps_and_invalid_switches(self):
        r,docs,selected,p,_=population_fixture(extra=18)
        selected += [(i,.8) for i,d in enumerate(docs) if d.field_name.startswith('filler')][:17]
        self.assertEqual(len(selected),20)
        result,trace=expand_context(r,docs,selected,p,categorical_population=True)
        self.assertEqual(result,selected)
        self.assertEqual(trace['decisions'][0]['decision_reason'],'context_field_cap')
        r,docs,selected,p,_=population_fixture()
        result,trace=expand_context(r,docs,selected,p,intent_added_count=7,categorical_population=True)
        self.assertEqual(result,selected)
        self.assertEqual(trace['decisions'][0]['decision_reason'],'intent_addition_cap')
        for kw in (dict(diagnostic=False,coverage=True,intent=True,output=False),
                   dict(diagnostic=True,coverage=False,intent=True,output=False),
                   dict(diagnostic=True,coverage=True,intent=True,output=True),
                   dict(diagnostic=True,coverage=True,intent=True,output=False,relation_output=True)):
            with self.assertRaises(BirdFailure):validate_options(True,categorical_population=True,**kw)
        validate_options(True,diagnostic=True,coverage=True,intent=True,output=False,
                         categorical_population=True)

    def test_retrieval_opt_in_builds_authorized_graph_without_model_or_db(self):
        r,small_docs,_,p,_=fixture()
        documents=[]
        for d in small_docs:
            row=FieldDocument(doc_id=d.doc_id,database_id=d.database_id,table_id=d.table_id,
                table_label=d.table_id.split('.')[-1],field_name=d.field_name,field_label=d.field_label,
                field_type=d.field_type,field_description='',field_role=d.field_role,
                aliases=[],samples=d.samples,profile='',keyword_text=d.doc_id,
                semantic_text=d.doc_id,rerank_text=d.doc_id,dense_vector=[0.0]*1024,
                schema_version='offline',content_hash='')
            raw=asdict(row)
            for key in ('dense_vector','schema_version','content_hash','active'):raw.pop(key)
            row.content_hash=digest_json(raw);documents.append(row)
        config=NS(public=lambda:{'name':'offline_only'})
        class Models:
            def __init__(self):self.config=config;self.calls=[]
            def embed(self,strings):self.calls.append('embed');return [[0.0]*1024]
            def rerank(self,text,strings):
                self.calls.append('rerank')
                score={'yearmonth.date':.8,'yearmonth.consumption':.79,
                       'customers.currency':.503,'yearmonth.customerid':.512,
                       'customers.customerid':.338}
                return {i:score[s.split('debit_card_specializing.',1)[1]] for i,s in enumerate(strings)}
        identity=index_identity(r,config)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'.downloads') as temp:
            path=Path(temp)/'schema_index.json'
            LocalSchemaStore(path).replace_all(digest_json(identity),documents,'text-embedding-v4',cache_identity=identity)
            baseline_models=Models();baseline=retrieve(r,baseline_models,path,p,schema_coverage=True,intent_candidate=True)
            candidate_models=Models();candidate=retrieve(r,candidate_models,path,p,
                schema_coverage=True,intent_candidate=True,condition_relations=True)
        self.assertEqual(baseline['retrieval']['selected_count'],2)
        self.assertEqual(candidate['retrieval']['selected_count'],5)
        self.assertEqual(len(candidate['graph']['joins']),1)
        self.assertEqual(candidate['graph']['joins'][0]['relation_type'],'reviewed_candidate')
        self.assertEqual(candidate_models.calls,['embed','rerank'])
        self.assertEqual(baseline_models.calls,['embed','rerank'])
        trace=candidate['_report_diagnostics']['condition_relation_context']
        self.assertEqual(trace['prior_intent_sample_decisions'][0]['gate_reasons'],
            ['condition_owner_outside_anchor_seed_or_named_scope','no_declared_fk_path_within_two_hops'])
        self.assertIn('customers.currency',candidate['schema_text'])
        recorder=Recorder()
        recorder.set_retrieval(candidate['_report_diagnostics'])
        saved=recorder.public()['retrieval']
        self.assertTrue(saved['schema_graph']['complete'])
        self.assertEqual(saved['condition_relation_context']['added_field_ids'],trace['added_field_ids'])
        self.assertFalse(saved['condition_relation_context']['relation_candidates'][0]['declared_foreign_key'])

    def test_1479_condition_keys_admitted_atomically_and_annotated(self):
        r,docs,selected,p,_=fixture()
        result,trace=expand_context(r,docs,selected,p)
        self.assertEqual({docs[i].doc_id for i,_ in result}-{docs[i].doc_id for i,_ in selected},
            {'debit_card_specializing.customers.currency','debit_card_specializing.customers.customerid',
             'debit_card_specializing.yearmonth.customerid'})
        self.assertEqual(trace['decisions'][0]['decision_reason'],'condition_and_keys_admitted_atomically')
        self.assertEqual(trace['decisions'][0]['text'],'paid in CZK')
        self.assertEqual(trace['decisions'][0]['source'],'question')
        self.assertEqual(len(trace['admitted_relations']),1)
        self.assertTrue(trace['sample_hint_decisions'][0]['selected_after_context'])
        graph=dict(tables=[],fields=[],joins=[])
        annotated=annotate_graph(r,graph,trace)
        self.assertEqual(annotated['joins'][0]['relation_type'],'reviewed_candidate')
        self.assertIsNone(annotated['joins'][0]['join_type'])
        self.assertFalse(annotated['joins'][0]['declared_foreign_key'])
        self.assertFalse(annotated['condition_relation_context']['admitted_public_conditions'][0]['mandatory'])

    def test_0407_missing_key_group_and_orphans_are_diagnostic_only(self):
        r,docs,selected,p,_=fixture('card_games',extra=18)
        selected=[(i,.8) for i,d in enumerate(docs) if d.field_name not in ('uuid','filler16')]
        self.assertEqual(len(selected),20)
        result,trace=expand_context(r,docs,selected,p)
        self.assertEqual(result,selected)
        self.assertFalse(trace['relation_candidates'][0]['eligible'])
        self.assertEqual(trace['relation_candidates'][0]['orphan_rows'],16)
        self.assertEqual(trace['missing_relation_key_groups'][0]['missing_field_ids'],
            ['card_games.cards.uuid','card_games.foreign_data.uuid'])
        self.assertFalse(trace['missing_relation_key_groups'][0]['automatic_completion'])
        self.assertTrue(any(x['role']=='evidence_field_group' for x in trace['requirements']))

    def test_declared_fk_path_can_supply_two_key_ends_without_duplicate_candidate(self):
        r,docs,selected,p,_=fixture()
        r.catalog.relations=[dict(id='declared',left_table='debit_card_specializing.customers',
            left_field='customerid',right_table='debit_card_specializing.yearmonth',right_field='customerid')]
        result,trace=expand_context(r,docs,selected,p)
        self.assertEqual(len(result),5)
        self.assertEqual([x['authority'] for x in trace['admitted_relations']],['declared_foreign_key'])

    def test_full_composite_key_required(self):
        r,docs,selected,p,row=fixture()
        row.update(parent_fields=['customerid','currency'],child_fields=['customerid','date'],
            key_types=['bigint','text'],unique_keys=[['customerid']],orphan_rows=0)
        self.assertEqual(relation_candidates(r,[row])[0]['decision_reason'],'whole_parent_key_not_unique')
        row['unique_keys']=[['customerid','currency']]
        self.assertTrue(relation_candidates(r,[row])[0]['eligible'])
        result,trace=expand_context(r,docs,selected,p,reviewed=[row])
        self.assertEqual(len(result),5)
        self.assertEqual(trace['admitted_relations'][0]['parent_fields'],['customerid','currency'])

    def test_no_public_role_or_ambiguous_owner_does_not_promote_sample(self):
        r,docs,selected,p,_=fixture()
        p['question']='Which year recorded the most gas consumption in 2013?'
        self.assertEqual(expand_context(r,docs,selected,p)[1]['decisions'],[])
        p['question']='Which year recorded the most gas paid in CZK?'
        extra=deepcopy(next(d for d in docs if d.field_name=='currency'))
        extra.table_id='debit_card_specializing.yearmonth';extra.doc_id=extra.table_id+'.currency'
        docs.append(extra);r.catalog.tables[0]['fields'].append(dict(name='currency',label='currency',type='text',role='field'))
        trace=expand_context(r,docs,selected,p)[1]
        self.assertFalse(trace['decisions'][0]['selected'])
        self.assertIn(trace['decisions'][0]['decision_reason'],('ambiguous_or_unmatched_currency_owner','sample_owner_not_unique'))

    def test_uncertain_or_conflicting_public_conditions_are_advisory(self):
        r,docs,selected,p,_=fixture()
        for wording in ('not paid in CZK','paid in CZK or EUR','for example paid in CZK'):
            p['question']=wording
            self.assertFalse(expand_context(r,docs,selected,p)[1]['decisions'][0]['selected'])
        p['question']='paid in CZK or paid in EUR'
        self.assertEqual(len(expand_context(r,docs,selected,p)[0]),len(selected))

    def test_caps_reject_whole_group(self):
        r,docs,_,p,_=fixture(extra=18)
        selected=[(i,.8) for i,d in enumerate(docs) if d.table_id.endswith('.yearmonth') and d.field_name!='customerid']
        self.assertEqual(len(selected),20)
        result,trace=expand_context(r,docs,selected,p)
        self.assertEqual(result,selected)
        self.assertEqual(trace['decisions'][0]['decision_reason'],'context_field_cap')
        r,docs,selected,p,_=fixture()
        result,trace=expand_context(r,docs,selected,p,intent_added_count=6)
        self.assertEqual(result,selected)
        self.assertEqual(trace['decisions'][0]['decision_reason'],'intent_addition_cap')

    def test_source_role_catalog_data_and_verification_binding(self):
        r,docs,selected,p,row=fixture()
        for change in ('identity','role','catalog','data','verification'):
            bad=deepcopy(r);bad.identity=NS(public=lambda:dict(r.identity.public()))
            if change=='identity':bad.identity.public=lambda:{**r.identity.public(),'source_id':'other'}
            if change=='role':bad.domain['query_role']='other'
            if change=='catalog':bad.catalog.version='other'
            if change=='data':bad.verification['authorized_data_version']='other'
            if change=='verification':bad.verification['live_target_verified']=False
            self.assertFalse(relation_candidates(bad)[0]['eligible'],change)
            self.assertEqual(expand_context(bad,docs,selected,p)[0],selected,change)
        row['child_table']='foreign_domain.yearmonth'
        self.assertEqual(relation_candidates(r,[row])[0]['decision_reason'],'unauthorized_relation_endpoint')

    def test_nonunique_incompatible_or_orphan_relation_rejected(self):
        r,_,_,_,row=fixture()
        for key,value,reason in [('unique_keys',[],'whole_parent_key_not_unique'),
            ('orphan_rows',1,'incomplete_child_key_coverage'),('null_child_rows',1,'incomplete_child_key_coverage'),
            ('key_types',['text'],'incompatible_key_types'),('ownership_basis',None,'ownership_not_reviewed')]:
            candidate=deepcopy(row);candidate[key]=value
            self.assertEqual(relation_candidates(r,[candidate])[0]['decision_reason'],reason)

    def test_case_id_does_not_control_admission_and_unsupported_switch_rejected(self):
        r,docs,selected,p,_=fixture()
        p['case_id']='BIRD-PG-9999'
        self.assertEqual(len(expand_context(r,docs,selected,p)[0]),5)
        p['question']='Which year recorded the most consumption of gas paid in CZK?'
        self.assertEqual(len(expand_context(r,docs,selected,p)[0]),5)
        for kw in (dict(diagnostic=False,coverage=True,intent=True,output=False),
                   dict(diagnostic=True,coverage=False,intent=True,output=False),
                   dict(diagnostic=True,coverage=True,intent=True,output=True)):
            with self.assertRaises(BirdFailure):validate_options(True,**kw)
        validate_options(True,diagnostic=True,coverage=True,intent=True,output=False)


if __name__=='__main__':unittest.main()
