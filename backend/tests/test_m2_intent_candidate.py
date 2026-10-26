"""Generic public-intent contracts, authorized coverage and actual broker/Agent loop."""
from copy import deepcopy
from dataclasses import asdict
import importlib.util
import importlib
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
import sys
import tempfile
from unittest.mock import patch

from app.retrieval.store import FieldDocument
from evaluation.bird.budgets import Budget, BirdFailure
from evaluation.bird.intent import (build_contract, canonical_lookup, checked_tables, expand_fields,
                                   literal_requests, name_groups, policy, violations)
from evaluation.bird.native import NativeResult
from evaluation.bird.repair import RepairSession, FEEDBACK_BYTES
from evaluation.bird.sql import validate_sql
from scripts.m2_b_common import digest_json,digest_file


def public(question='Which entity has the highest score?', evidence='', db='db'):
    return dict(case_id='BIRD-PG-9999', database_id=db, dialect='postgres', question=question, evidence=evidence)


def field(name, label=None, kind='text', **kw):
    return dict(name=name, label=label or name, type=kind, description='', nullable=True, role='field', **kw)


def context(definitions=None, relations=None):
    definitions=definitions or {'items':[field('id',kind='bigint'),field('score',kind='bigint'),field('name')]}
    tables=[dict(id='db.'+n,name=n,label=n,description='official',database='db',physical_schema='public',fields=fields) for n,fields in definitions.items()]
    return NS(database_id='db',domain={'query_role':'ro'},identity=NS(public=lambda:{'logical_database_id':'db','source_id':'unit',
              'backend':'postgresql','dialect':'postgres','prompt_dialect':'PostgreSQL','physical_schema':'public'}),
              catalog=NS(tables=tables,relations=relations or []))


def documents(runtime, samples=None):
    samples=samples or {};result=[]
    for t in runtime.catalog.tables:
        for f in t['fields']:
            document=FieldDocument(doc_id=t['id']+'.'+f['name'],database_id='db',table_id=t['id'],table_label=t['name'],
                field_name=f['name'],field_label=f['label'],field_type=f['type'],field_description=f['description'],field_role=f['role'],
                aliases=[],samples=samples.get(f['name'],[]),profile='',keyword_text='',semantic_text='',rerank_text='',
                dense_vector=[0.0]*1024,schema_version='unit',content_hash='unit')
            raw=asdict(document)
            for key in ('dense_vector','schema_version','content_hash','active'):raw.pop(key)
            document.content_hash=digest_json(raw);result.append(document)
    return result


def contract(runtime, p=None, *, conditions=None, groups=None, matches=None, semantic_planning=False):
    p=p or public()
    graph={'fields':[{'id':t['id']+'.'+f['name']} for t in runtime.catalog.tables for f in t['fields']]}
    selection={'baseline_field_ids':[f['id'] for f in graph['fields']],'sample_condition_candidates':conditions or []}
    result=build_contract(runtime,p,graph,selection,{'matches':matches or []},
                          semantic_planning=semantic_planning)
    if conditions is not None:
        result['required_profile_conditions']=[{**c,'mandatory':True,'authority':'unique_public_field_value_binding'} for c in conditions]
    if groups is not None:result['name_groups']=groups
    return result


def codes(runtime,sql,p=None,c=None):
    p=p or public();return [i['code'] for i in violations(runtime,p,c or contract(runtime,p),sql)]


class RankingAndShapeTest(unittest.TestCase):
    def test_nullable_desc_abs_alias_and_ordinal_are_checked(self):
        r=context()
        for sql in ('SELECT id FROM items ORDER BY score DESC LIMIT 1',
                    'SELECT id FROM items ORDER BY ABS(score) DESC LIMIT 1',
                    'SELECT ABS(score) AS rankval FROM items ORDER BY rankval DESC LIMIT 1',
                    'SELECT score FROM items ORDER BY 1 DESC LIMIT 1'):
            self.assertIn('nullable_order_nulls_first',codes(r,sql))
            self.assertNotIn('nullable_order_nulls_first',codes(r,sql.replace('DESC','DESC NULLS LAST')))

    def test_count_nonnullable_asc_and_explicit_missing_first_not_blocked(self):
        r=context()
        self.assertEqual(codes(r,'SELECT COUNT(*) FROM items ORDER BY COUNT(*) DESC'),[])
        self.assertEqual(codes(r,'SELECT id FROM items ORDER BY score ASC'),[])
        r.catalog.tables[0]['fields'][1]['nullable']=False
        self.assertEqual(codes(r,'SELECT id FROM items ORDER BY score DESC'),[])
        self.assertEqual(codes(context(),'SELECT id FROM items ORDER BY score DESC',public('Rank missing values first')) ,[])

    def test_ordinal_offset_is_derived_from_public_text(self):
        r=context();p=public('Entity with the 4th highest score')
        self.assertIn('ordinal_topn',codes(r,'SELECT id FROM items ORDER BY score DESC NULLS LAST',p))
        self.assertIn('ordinal_offset',codes(r,'SELECT id FROM items ORDER BY score DESC NULLS LAST LIMIT 1 OFFSET 4',p))
        self.assertEqual(codes(r,'SELECT id FROM items ORDER BY score DESC NULLS LAST LIMIT 1 OFFSET 3',p),[])

    def test_projection_star_is_not_count_star_or_explicit_all_columns(self):
        r=context()
        self.assertIn('unrequested_projection_star',codes(r,'SELECT t.* FROM items t'))
        self.assertNotIn('unrequested_projection_star',codes(r,'SELECT COUNT(*) FROM items'))
        self.assertNotIn('unrequested_projection_star',codes(r,'SELECT * FROM items',public('Show all columns')))

    def test_explicit_topn_and_ordinal_direction_are_preserved(self):
        r=context();p=public('Show top 4 items by score')
        self.assertIn('topn_size',codes(r,'SELECT id FROM items LIMIT 1',p))
        self.assertEqual(codes(r,'SELECT id FROM items ORDER BY score DESC NULLS LAST LIMIT 4',p),[])
        p=public('Entity with the 4th lowest score')
        self.assertIn('ordinal_direction',codes(r,'SELECT id FROM items ORDER BY score DESC NULLS LAST LIMIT 1 OFFSET 3',p))

    def test_numbered_name_groups_are_ordered_and_email_excluded(self):
        r=context({'people':[field('firstname1','person first name'),field('lastname1','person last name'),field('email1'),
                            field('firstname2'),field('lastname2'),field('firstname3'),field('lastname3')]})
        self.assertEqual(name_groups(r.catalog.tables[0]),[['firstname1','lastname1','firstname2','lastname2','firstname3','lastname3']])
        p=public('List their full names','There are three people in each row')
        self.assertIn('incomplete_output_name_group',codes(r,'SELECT firstname1,lastname1 FROM people',p))
        self.assertEqual(codes(r,'SELECT firstname1,lastname1,firstname2,lastname2,firstname3,lastname3 FROM people',p),[])

    def test_cte_and_unknown_identifiers_do_not_fabricate_column_ownership(self):
        r=context()
        self.assertEqual(codes(r,'WITH q AS (SELECT id FROM items) SELECT id FROM q'),[])
        self.assertEqual(codes(r,'SELECT absent FROM nonexistent ORDER BY absent DESC'),[])
        self.assertEqual(codes(r,'nonsense'),[])


class NumericAndConditionsTest(unittest.TestCase):
    def test_independent_quantity_comparison_uses_signed_single_output_convention(self):
        r=context();p=public('Is it true A is more than B? If so, how many more?','Quantity = COUNT(A) - COUNT(B)')
        self.assertTrue(contract(r,p)['quantity_difference_scalar'])
        self.assertIn('difference_output_shape',codes(r,"SELECT 'Yes',COUNT(id) FROM items",p))
        self.assertIn('difference_sign',codes(r,'SELECT ABS(COUNT(id)-1) FROM items',p))
        self.assertEqual(codes(r,'SELECT COUNT(id)-1 FROM items',p),[])


class QuerySemanticPlanningPromptTest(unittest.TestCase):
    def test_period_aggregate_and_individual_record_boundary_are_explicit_and_advisory(self):
        r=context({'usage':[field('month'),field('consumption',kind='numeric'),field('customer_id',kind='bigint')]})
        aggregate=contract(r,public('Which month has the greatest total consumption across customers?'),
                           semantic_planning=True)
        guidance=' '.join(aggregate['query_semantic_planning_guidance']).casefold()
        self.assertIn('aggregate qualifying rows at that grain using sum before ranking',guidance)
        self.assertIn('even without the word total',guidance)
        self.assertIn('never replace a group total with the highest source row',guidance)
        self.assertFalse(aggregate['query_semantic_planning_policy']['hard_rejection'])
        self.assertFalse(aggregate['query_semantic_planning_policy']['sql_rewriting'])
        individual=contract(r,public('Which individual record has the largest consumption value?'),
                            semantic_planning=True)
        individual_guidance=' '.join(individual['query_semantic_planning_guidance']).casefold()
        self.assertIn('individual-record extrema, rank records without grouping',individual_guidance)
        self.assertIn('respect explicit averages, rates and formulas',individual_guidance)
        self.assertIn('do not sum nonadditive measures',individual_guidance)
        self.assertNotIn('BIRD-PG-',json.dumps(individual['query_semantic_planning_guidance']))
        baseline=contract(r,public('Which month has the greatest total consumption across customers?'))
        self.assertNotIn('query_semantic_planning_guidance',baseline)

    def test_requested_projection_sequence_and_explicit_exclusion_boundary(self):
        r=context({'schools':[field('mailstreet','mailing street'),field('school','school name'),
                              field('math_average','math average',kind='numeric')]})
        q=public("What is the postal street address for the school? Indicate the school's name.",
                 'Postal street and mailing street are synonyms.')
        candidate=contract(r,q,semantic_planning=True)
        guidance=' '.join(candidate['query_semantic_planning_guidance']).casefold()
        self.assertIn('only requested attributes in question order',guidance)
        self.assertIn('follow-up requests',guidance)
        self.assertIn('ranking/filter/join helpers are not outputs unless requested',guidance)
        excluded=contract(r,public('List only the school name; do not include its address.'),semantic_planning=True)
        excluded_guidance=' '.join(excluded['query_semantic_planning_guidance']).casefold()
        self.assertIn('explicit exclusions',excluded_guidance)
        self.assertFalse(candidate['query_semantic_planning_policy']['hard_rejection'])
        self.assertFalse(candidate['query_semantic_planning_policy']['sql_rewriting'])

    def test_rank_only_measure_is_not_projected_but_explicitly_requested_measure_is(self):
        r=context({'cards':[field('name','card name'),field('convertedmanacost','converted mana cost',kind='numeric')]})
        ranking=contract(r,public('Which card costs more, Serra Angel or Shrine Keeper?'),semantic_planning=True)
        guidance=' '.join(ranking['query_semantic_planning_guidance']).casefold()
        self.assertIn('only requested attributes',guidance)
        self.assertIn('helpers are not outputs unless requested',guidance)
        self.assertFalse(ranking['query_semantic_planning_policy']['hard_rejection'])
        explicit=contract(r,public('Which card costs more, Serra Angel or Shrine Keeper, and what is its converted mana cost?'),semantic_planning=True)
        self.assertEqual(ranking['query_semantic_planning_guidance'],explicit['query_semantic_planning_guidance'])

    def test_population_peak_and_individual_or_average_inputs_preserve_advisory_boundary(self):
        r=context({'usage':[field('month'),field('consumption',kind='numeric'),field('customer_id',kind='bigint')]})
        examples=[
            ('What was the peak month of consumption for business customers?',
             'SELECT month FROM usage GROUP BY month ORDER BY SUM(consumption) DESC NULLS LAST LIMIT 1'),
            ('Which individual record has the largest consumption?',
             'SELECT month FROM usage ORDER BY consumption DESC NULLS LAST LIMIT 1'),
            ('Which month has the highest average consumption?',
             'SELECT month FROM usage GROUP BY month ORDER BY AVG(consumption) DESC NULLS LAST LIMIT 1'),
        ]
        for question,sql in examples:
            with self.subTest(question=question):
                p=public(question);baseline=contract(r,p);candidate=contract(r,p,semantic_planning=True)
                shared={k:v for k,v in candidate.items() if not k.startswith('query_semantic_planning_')}
                self.assertEqual(shared,baseline)
                self.assertEqual(codes(r,sql,p,candidate),codes(r,sql,p,baseline))
                self.assertFalse(candidate['query_semantic_planning_policy']['hard_rejection'])

    def test_compact_guidance_is_bounded_against_frozen_r9(self):
        import ast
        from evaluation.bird.intent import QUERY_SEMANTICS_GUIDANCE
        frozen=Path(__file__).resolve().parents[1]/'.downloads/m3_categorical_population_pair24_v1_20261025_r9/payload/candidate/evaluation/bird/intent.py'
        values={n.targets[0].id:ast.literal_eval(n.value) for n in ast.parse(frozen.read_text(encoding='utf-8')).body
                if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name)
                and n.targets[0].id=='QUERY_SEMANTICS_GUIDANCE'}
        old='\n'.join(values['QUERY_SEMANTICS_GUIDANCE']).encode('utf-8')
        new='\n'.join(QUERY_SEMANTICS_GUIDANCE).encode('utf-8')
        self.assertLessEqual(len(new),len(old)*0.60)

    def test_entity_list_default_uses_own_primary_key_not_names_or_all_columns(self):
        key=field('transaction_id','transaction id',kind='bigint');key['role']='primary_key'
        r=context({'transactions':[key,field('amount'),field('name')]});p=public('List all the transactions that someone made')
        self.assertEqual(contract(r,p)['entity_identifier_output'],{'table_id':'db.transactions','field':'transaction_id'})
        self.assertIn('entity_identifier_projection',codes(r,'SELECT amount FROM transactions',p))
        self.assertIn('entity_identifier_projection',codes(r,'SELECT COUNT(transaction_id) FROM transactions',p))
        self.assertEqual(codes(r,'SELECT transaction_id FROM transactions',p),[])
        self.assertIsNone(contract(r,public('List all transaction names'))['entity_identifier_output'])

    def test_population_condition_cannot_be_dropped(self):
        r=context({'customers':[field('segment'),field('currency')]});p=public('Difference of SMEs using CZK and EUR')
        condition={'field_id':'db.customers.segment','table_id':'db.customers','field':'segment','value':'SME'}
        c=contract(r,p,conditions=[condition])
        self.assertIn('missing_population_condition',codes(r,'SELECT COUNT(*) FROM customers',p,c))
        self.assertIn('missing_population_condition',codes(r,'SELECT COUNT(*) FILTER(WHERE currency=\'CZK\') FROM customers',p,c))
        self.assertEqual(codes(r,"SELECT COUNT(*) FROM customers WHERE segment='SME'",p,c),[])
        self.assertEqual(codes(r,"SELECT SUM(CASE WHEN segment='SME' THEN 1 ELSE 0 END) FROM customers",p,c),[])

    def test_plain_output_reference_is_not_a_business_filter(self):
        r=context({'items':[field('segment')]});p=public()
        c=contract(r,p,conditions=[dict(field_id='db.items.segment',table_id='db.items',field='segment',value='SME')])
        self.assertIn('missing_population_condition',codes(r,'SELECT segment FROM items',p,c))

    def test_percentage_decimal_path_and_final_cast_rejected_real_numerator_passes(self):
        r=context();p=public('What percentage of items have score above zero?')
        self.assertIn('percentage_numeric_path',codes(r,'SELECT COUNT(*)*100.0/COUNT(id) FROM items',p))
        self.assertIn('percentage_numeric_path',codes(r,'SELECT CAST(COUNT(*)*100.0/COUNT(id) AS REAL) FROM items',p))
        self.assertNotIn('percentage_numeric_path',codes(r,'SELECT CAST(COUNT(*) AS DOUBLE PRECISION)*100/COUNT(id) FROM items',p))
        self.assertEqual(codes(r,'SELECT CAST(SUM(CASE WHEN score>0 THEN 1 ELSE 0 END) AS REAL)*100/NULLIF(COUNT(id),0) FROM items',p),[])
        self.assertNotIn('percentage_numeric_path',codes(r,'SELECT COUNT(*)*100.0/COUNT(id) FROM items',public('Calculate the ratio')))

    def test_explicit_rounding_request_does_not_force_new_numeric_convention(self):
        r=context();p=public('Percentage rounded to two decimal places')
        self.assertFalse(contract(r,p)['percentage_real_arithmetic'])


class CoverageTest(unittest.TestCase):
    def test_empty_baseline_seeds_only_explicit_fields_not_entire_table(self):
        r=context({'events':[field('event_name'),field('event_date'),field('status'),field('type'),field('private_note')]})
        ds=documents(r);p=public('Closed game events','event_name, event_date; status = \'Closed\'; type = \'Game\'')
        chosen,detail=expand_fields(r,ds,[],p)
        self.assertEqual({ds[i].field_name for i,s in chosen},{'event_name','event_date','status','type'})
        self.assertEqual(detail['policy']['max_related_hops'],2)

    def test_authorized_related_name_field_and_real_join_keys(self):
        relation={'left_table':'db.entity','left_field':'id','right_table':'db.items','right_field':'entity_id'}
        r=context({'items':[field('amount'),field('entity_id')],'entity':[field('id'),field('event_name')]},[relation])
        ds=documents(r);p=public("Budget for 'Spring Party'", "'Spring Party' is an event name")
        chosen,detail=expand_fields(r,ds,[(0,.9)],p)
        self.assertIn('db.entity.event_name',detail['added_field_ids'])

    def test_profile_category_matches_plural_public_token_without_synonym_map(self):
        r=context({'customers':[field('currency'),field('segment')]});ds=documents(r,{'segment':[['text','SME']]})
        chosen,detail=expand_fields(r,ds,[(0,.9)],public('Difference between SMEs using CZK and EUR'))
        self.assertEqual(detail['added_field_ids'],['db.customers.segment'])
        self.assertEqual(detail['sample_condition_candidates'][0]['value'],'SME')

    def test_truncated_samples_never_become_exact_population_conditions(self):
        r=context({'customers':[field('currency'),field('segment')]});ds=documents(r,{'segment':[['text','SME']]})
        ds[1].profile=json.dumps({'sample_truncated':[True]})
        self.assertEqual(expand_fields(r,ds,[(0,.9)],public('SMEs using CZK'))[1]['sample_condition_candidates'],[])

    def test_shared_type_and_id_do_not_add_unrelated_owner_fields(self):
        r=context({'event':[field('event_name'),field('type'),field('id')],'other':[field('type'),field('id')]})
        ds=documents(r);chosen,detail=expand_fields(r,ds,[],public('Event names','event_name and type'))
        self.assertIn('db.event.type',detail['added_field_ids']);self.assertNotIn('db.other.type',detail['added_field_ids'])
        self.assertNotIn('db.other.id',detail['added_field_ids'])

    def test_empty_seed_does_not_admit_unrelated_sample_only_tables(self):
        r=context({'event':[field('event_name'),field('status')],'budget':[field('state')]})
        ds=documents(r,{'state':[['text','Closed']]})
        chosen,detail=expand_fields(r,ds,[],public('Closed event names','event_name where status is Closed'))
        self.assertNotIn('db.budget.state',detail['added_field_ids'])

    def test_no_foreign_no_disconnected_no_inferred_relation(self):
        r=context({'items':[field('id')],'unrelated':[field('event_name')]});ds=documents(r)
        self.assertEqual(expand_fields(r,ds,[(0,.9)],public('List event_name'))[0],[(0,.9)])
        ds[1].database_id='foreign'
        with self.assertRaises(BirdFailure):expand_fields(r,ds,[(0,.9)],public('event_name'))
        r=context();r.catalog.relations=[dict(left_table='db.items',left_field='id',right_table='foreign.secret',right_field='id')]
        with self.assertRaises(BirdFailure):checked_tables(r)

    def test_baseline_and_caps_preserved_and_case_id_does_not_affect_output(self):
        r=context({'items':[field('field_'+str(i)) for i in range(25)]});ds=documents(r)
        p=public(' '.join(d.field_name for d in ds));selected=[(i,.9) for i in range(18)]
        a,detail=expand_fields(r,ds,selected,p);p['case_id']='BIRD-PG-0001'
        self.assertEqual((a,detail),expand_fields(r,ds,selected,p));self.assertEqual(a[:18],selected);self.assertEqual(len(a),20)
        self.assertEqual(len(expand_fields(r,ds,[],p)[0]),8)


class CanonicalAndRoleTest(unittest.TestCase):
    def test_one_bounded_lookup_uses_existing_budget_and_escapes_literals(self):
        r=context({'attrs':[field('attribute_name')]});calls=[];budget=Budget()
        def execute(sql,b):
            validate_sql(sql,{'attrs'});calls.append(sql);return NativeResult(['probe_id','value'],[(0,'Strength')],64)
        r.execute_native=execute;p=public('Highest strength',"attribute_name = 'strength'")
        record=canonical_lookup(r,p,['db.attrs.attribute_name'],budget)
        self.assertEqual(record['matches'][0]['values'],['Strength']);self.assertEqual(budget.sql_calls,1)
        self.assertEqual(len(calls),1);self.assertIn('LIMIT 3',calls[0]);self.assertIn('LOWER',calls[0])
        c=contract(r,p,matches=record['matches'])
        self.assertIn('noncanonical_literal',codes(r,"SELECT attribute_name FROM attrs WHERE attribute_name='strength'",p,c))
        self.assertEqual(codes(r,"SELECT attribute_name FROM attrs WHERE attribute_name='Strength'",p,c),[])

    def test_apostrophe_in_name_is_preserved_in_literal_and_sql(self):
        r=context({'events':[field('event_name')]});p=public("Did someone attend the 'Women's Soccer' event?",'event_name is event name')
        probes=literal_requests(p,checked_tables(r),{'db.events.event_name'})
        self.assertEqual(probes[0]['requested'],"Women's Soccer")
        calls=[];r.execute_native=lambda sql,b:(calls.append(sql) or NativeResult(['i','v'],[],1))
        record=canonical_lookup(r,p,['db.events.event_name'],Budget())
        self.assertIn("Women''s Soccer",calls[0]);self.assertEqual(record['matches'][0]['resolution'],'not_found')

    def test_ambiguous_missing_and_lookup_failure_do_not_invent_canonical_value(self):
        r=context({'attrs':[field('attribute_name')]});p=public('strength',"attribute_name='strength'")
        r.execute_native=lambda *a:NativeResult(['i','v'],[(0,'Strength'),(0,'STRENGTH')],64)
        self.assertEqual(canonical_lookup(r,p,['db.attrs.attribute_name'],Budget())['matches'][0]['resolution'],'ambiguous')
        def fail(*a):raise BirdFailure('sql_timeout')
        r.execute_native=fail;progress={};b=Budget()
        with self.assertRaises(BirdFailure):canonical_lookup(r,p,['db.attrs.attribute_name'],b,progress=progress)
        self.assertEqual(progress['sql_tool_calls'],1);self.assertFalse(progress['executed']);self.assertEqual(b.sql_calls,1)

    def test_no_probe_needs_no_sql_or_extra_capability(self):
        r=context();b=Budget()
        self.assertEqual(canonical_lookup(r,public(),[],b)['probe_count'],0);self.assertEqual(b.sql_calls,0)
        with self.assertRaises(ValueError):canonical_lookup(r,{**public(),'gold_sql':'private'},[],b)

    def test_probe_cap_and_sql_budget_exhaustion_apply_before_database(self):
        r=context({'attrs':[field('value_'+str(i)) for i in range(8)]});p=public('Values',"; ".join("value_"+str(i)+"='x'" for i in range(8)))
        ids={'db.attrs.value_'+str(i) for i in range(8)}
        self.assertEqual(len(literal_requests(p,checked_tables(r),ids)),4)
        b=Budget();b.sql_calls=3;r.execute_native=lambda *a:self.fail('Budget must deny before database')
        with self.assertRaises(BirdFailure):canonical_lookup(r,p,ids,b)

    def test_foreign_key_human_name_guard_preserves_explicit_id_filters(self):
        rel=dict(left_table='db.events',left_field='id',right_table='db.items',right_field='event_id')
        r=context({'events':[field('id'),field('event_name')],'items':[field('amount'),field('event_id')]},[rel])
        p=public("Budget for 'Spring Party' event", "'Spring Party' is an event name")
        self.assertIn('name_compared_to_foreign_key',codes(r,"SELECT amount FROM items WHERE event_id='Spring Party'",p))
        p=public("List event names for event id 'ABC'",'event_name is the name')
        self.assertNotIn('name_compared_to_foreign_key',codes(r,"SELECT amount FROM items WHERE event_id='ABC'",p))

    def test_intent_repeat_feedback_is_bounded_scrubbed_and_local(self):
        r=context();s=RepairSession(r,('PRIVATE_SECRET',));sql='SELECT id FROM items'
        error=BirdFailure('intent_contract_violation');error._intent_violations=[dict(code='x',reason='PRIVATE_SECRET')]
        s.remember(error,sql);failure,feedback=s.repeated(sql)
        self.assertEqual(failure.category,'repeated_invalid_sql');self.assertFalse(feedback['retryable'])
        self.assertNotIn('PRIVATE_SECRET',json.dumps(feedback));self.assertIsNone(feedback['sqlstate'])
        self.assertEqual(feedback['intent_violations'][0]['code'],'x');self.assertLessEqual(len(json.dumps(feedback).encode()),FEEDBACK_BYTES)

    def test_oversized_intent_feedback_is_explicitly_bounded(self):
        r=context();s=RepairSession(r);error=BirdFailure('intent_contract_violation')
        error._intent_violations=[dict(code='x',reason='r'*1000,fields=['n'*1000]*20) for i in range(8)]
        feedback=s.feedback(error,'SELECT id FROM items')
        self.assertLessEqual(len(json.dumps(feedback,separators=(',',':')).encode()),FEEDBACK_BYTES)
        self.assertGreater(feedback['omitted_intent_violations'],0)


class CandidateGateAndLoopTest(unittest.TestCase):
    def test_real_retrieval_graph_and_rerank_records_include_new_low_score_fields(self):
        from evaluation.bird.retrieval import retrieve,index_identity
        from evaluation.bird.model import ModelConfig
        runtime=context({'events':[field('event_name'),field('event_date'),field('status')]});ds=documents(runtime);calls=[]
        class Store:
            embedding_source='text-embedding-v4'
            def __init__(self,*a):self.documents=ds
            def load(self,*a,**kw):return True
            def bm25_search(self,*a):return [(0,.9),(1,.8),(2,.7)]
            def dense_search(self,*a):return [(0,.9),(1,.8),(2,.7)]
        class Models:
            config=ModelConfig('fake')
            def embed(self,*a):calls.append('embed');return [[0.0]*1024]
            def rerank(self,*a):calls.append('rerank');return {0:.45,1:.43,2:.51}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'index.json';path.write_text('{}')
            with patch('evaluation.bird.retrieval.LocalSchemaStore',Store):
                result=retrieve(runtime,Models(),path,public('Events','event_name and event_date where status is Closed'),intent_candidate=True)
        self.assertEqual(calls,['embed','rerank']);self.assertEqual(result['retrieval']['selected_count'],3)
        self.assertEqual({f['source'] for f in result['graph']['fields']},{'intent_coverage'})
        for row in result['_report_diagnostics']['candidates']:
            self.assertTrue(row['selected']);self.assertEqual(row['selection_reason'],'selected_intent_coverage')
        self.assertEqual([r['rerank_score'] for r in result['_report_diagnostics']['candidates']],[.45,.43,.51])
        self.assertEqual({f['name']:f['score'] for f in result['graph']['fields']},{'event_date':.43,'event_name':.45,'status':.51})
        self.assertIn('intent.py',index_identity(runtime,Models.config)['code_sha256'])

    def test_preparation_lookup_reduces_available_rounds_without_expanding_budget(self):
        with patch.dict(sys.modules,{'resource':NS()}):agent=importlib.import_module('evaluation.bird.isolated_agent')
        calls=[]
        def rpc(op,**m):
            calls.append(op)
            if op=='chat':return dict(action='query',sql='SELECT id FROM items')
            if op=='validate':return {'valid':True}
            return dict(success=False,error={'category':'sql_timeout'})
        with patch.object(agent,'rpc',side_effect=rpc):
            result=agent.answer({'input':public(),'schema':{'intent_contract':{'remaining_sql_execution_rounds':2}}})
        self.assertEqual(result['status'],'sql_failed');self.assertEqual(calls.count('sql'),2);self.assertEqual(calls.count('chat'),2)

    def test_formal_live_refuses_candidate_before_runtime_or_gold_execution(self):
        from evaluation.bird.case_worker import execute
        request=dict(mode='live',gold=dict(case_id='BIRD-PG-9999',database_id='db',gold_sql_sha256='unit'),
                     intent_candidate_enabled=True,code_sha256='unit')
        with patch('evaluation.bird.case_worker.code_binding',return_value={'sha256':'unit'}):r=execute(request)
        self.assertEqual(r['errors'][0]['category'],'intent_candidate_development_only')

    def test_actual_worker_and_agent_loop_repairs_null_order_with_original_budgets(self):
        from evaluation.bird.case_worker import execute
        with patch.dict(sys.modules,{'resource':NS()}):agent=importlib.import_module('evaluation.bird.isolated_agent')
        runtime=context();runtime.catalog.tables[0]['fields'].append(field('attribute_name'))
        sql="SELECT id FROM items WHERE attribute_name='strength' ORDER BY score DESC LIMIT 1"
        fixed=sql.replace('DESC','DESC NULLS LAST').replace("'strength'","'Strength'")
        calls=[];prompts=[];left=[dict(action='query',sql=sql),dict(action='query',sql=fixed)]
        runtime.close=lambda:None
        def execute_native(text,budget,validate_only=False):
            calls.append((text,validate_only))
            if 'canonical_value' in text:return NativeResult(['probe_id','value'],[(0,'Strength')],64)
            return {'valid':True} if validate_only else NativeResult(['id'],[(7,)],64)
        runtime.execute_native=execute_native
        class Models:
            def __init__(self,config,budget):self.budget=budget
            def chat(self,system,user):
                self.budget.model_attempt('chat',prompt=(system+user).encode())
                prompts.append({'system':system,'user':json.loads(user)});return left.pop(0)
        class Agent:
            isolation={'unit':'fake'}
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def run(self,ctx,handler,*a):
                with patch.object(agent,'rpc',side_effect=lambda op,**m:handler(op,m)):return agent.answer(ctx)
        ids=['db.items.id','db.items.score','db.items.attribute_name'];selection=dict(baseline_field_ids=ids,sample_condition_candidates=[])
        schema=dict(graph={'fields':[{'id':fid} for fid in ids]},retrieval={'selected_field_ids':ids},
                    index_sha256='unit',_intent_selection=selection)
        request=dict(mode='diagnostic',input=public('Highest strength',"attribute_name='strength'"),intent_candidate_enabled=True,
                     semantic_planning_enabled=True,code_sha256='unit',
                     data_root='.',results_dir='.',credentials_file='private',receipt={},index_path='index',model_config_private={'api_key':'SECRET_API_KEY'})
        evidence=NS(domain=lambda db:{'query_role':'ro'},validation={'initialization_id':'unit'},manifest={})
        with patch('evaluation.bird.case_worker.code_binding',return_value={'sha256':'unit'}),\
             patch('evaluation.bird.case_worker.Evidence.load',return_value=evidence),\
             patch('evaluation.bird.case_worker.load_credentials',return_value={'passwords':{'ro':'SECRET_PASSWORD'}}),\
             patch('evaluation.bird.case_worker.BirdRuntime',return_value=runtime),\
             patch('evaluation.bird.case_worker.IsolatedAgent',Agent),patch('evaluation.bird.model.Models',Models),\
             patch('evaluation.bird.retrieval.retrieve',return_value=deepcopy(schema)):
            result=execute(request)
        self.assertEqual(result['status'],'diagnostic_answered');self.assertEqual(result['generated_sql'],fixed)
        self.assertEqual(calls[1:],[(sql,True),(fixed,True),(fixed,False)]);self.assertIn('canonical_value',calls[0][0])
        self.assertEqual(result['budget']['generation_attempts'],{1:2});self.assertEqual(result['budget']['sql_tool_calls'],2)
        self.assertTrue(result['validation_events'][0]['database_validation_performed'])
        feedback=prompts[1]['user']['validation_error']['repair_feedback'];self.assertEqual(feedback['intent_violations'][0]['code'],'nullable_order_nulls_first')
        self.assertIsNone(feedback['sqlstate']);self.assertNotIn('gold_sql',json.dumps(prompts));self.assertNotIn('SECRET_PASSWORD',json.dumps(prompts))
        self.assertEqual(result['canonical_lookup']['sql_tool_calls'],1)
        self.assertEqual(result['intent_contract']['remaining_sql_execution_rounds'],2)
        self.assertEqual(result['query_semantic_planning_policy']['policy_id'],'bird_public_query_semantics_prompt_v2')
        self.assertIn('aggregation grain',prompts[0]['system'])
        self.assertIn('query_semantic_planning_guidance',prompts[0]['user']['schema']['intent_contract'])
        self.assertEqual({i['code'] for i in feedback['intent_violations']},{'nullable_order_nulls_first','noncanonical_literal'})


class CandidateNativeCaptureTest(unittest.TestCase):
    def fixture(self):
        sql='SELECT id FROM items';p=public();result=NativeResult(['id'],[(7,)],64).diagnostic()
        identity=dict(logical_database_id='db',source_id='bird_mini_dev_postgres_db',backend='postgresql',dialect='postgres',
                      physical_schema='public',catalog_version='catalog',data_version='data')
        from evaluation.bird.diagnostics import sql_record
        case=dict(case_id=p['case_id'],database_id='db',mode='diagnostic',status='diagnostic_answered',complete=True,
                  gold_sql_sha256=None,ex_correct=None,runtime_closed=True,errors=[],intent_candidate_policy=policy(),agent_started=True,
                  source_identity=identity,query_role='ro',result=result,generated_sql=sql,
                  executions=[dict(success=True,diagnostic=result)],budget=dict(model_http_attempts=3,chat_http_attempts=1,
                  sql_tool_calls=2,generation_attempts={'1':1},validation_attempts={'1':1}),
                  canonical_lookup=dict(sql_tool_calls=1,probe_count=1),
                  agent_isolation=dict(project_read_access=False,environment_credentials=False,direct_database_access=False),
                  development_diagnostics={'attempts':[dict(kind='execute',success=True,sql=sql_record(sql))]})
        row=dict(run_status='complete',mode='diagnostic',split='development_diagnostic_subset',formal_benchmark=False,
                 gold_executed=False,holdout_live_allowed=False,primary_ex=None,errors=[],source_binding={'unit':1},
                 code_binding={'sha256':'current'},intent_candidate_policy=policy(),target_data_verified=True,
                 preparation_pools_closed=True,current_isolation_probe={'passed':True,'probes':dict(read_denials=[True]*4,
                 network_socket_denied=True,process_creation_denied=True,secret_environment_absent=True)},
                 current_timeout_probe={'passed':True},budget_counter_probes=[{'passed':True}]*7,
                 source_receipts=[dict(database_id='db',role='ro',authorized_catalog_version='catalog',authorized_data_version='data',live_target_verified=True)],
                 selected_case_ids=[p['case_id']],cases=[case])
        return p,row

    def load(self,row,publics):
        from evaluation.bird.intent_replay import load_candidate_capture
        from evaluation.bird.replay import sql_sha
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.json';path.write_text(json.dumps(row))
            gold={p['case_id']:dict(database_id='db',dialect='postgres',gold_sql='SELECT id FROM items',gold_sql_sha256=sql_sha('SELECT id FROM items')) for p in publics}
            with patch('evaluation.bird.intent_replay.public_cases',return_value=publics),\
                 patch('evaluation.bird.intent_replay.code_binding',return_value={'sha256':'current'}),\
                 patch('evaluation.bird.intent_replay.source_binding',return_value={'unit':1}),\
                 patch('evaluation.bird.intent_replay.scorer_gold',return_value=gold) as scorer:
                value=load_candidate_capture(path,NS(domain=lambda db:{'query_role':'ro'}),digest_file(path))
                return value,scorer.call_count

    def test_current_development_capture_loads_native_gold_only_after_checks(self):
        p,row=self.fixture();(source,pairs,excluded),calls=self.load(row,[p])
        self.assertEqual(len(pairs),1);self.assertEqual(excluded,[]);self.assertEqual(calls,1)

    def test_wrong_hash_never_reads_gold(self):
        from evaluation.bird.intent_replay import load_candidate_capture
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.json';path.write_text('{}')
            with patch('evaluation.bird.intent_replay.scorer_gold',side_effect=AssertionError('No Gold')):
                with self.assertRaises(ValueError):load_candidate_capture(path,None,'0'*64)

    def test_holdout_and_old_code_are_refused(self):
        p,row=self.fixture();row['cases'][0]['case_id']='HOLDOUT';row['selected_case_ids']=['HOLDOUT']
        with self.assertRaises(ValueError):self.load(row,[p])
        p,row=self.fixture();row['code_binding']={'sha256':'old'}
        with self.assertRaises(ValueError):self.load(row,[p])

    def test_missing_probe_and_underrecorded_lookup_budget_are_refused(self):
        p,row=self.fixture();row['current_isolation_probe']['passed']=False
        with self.assertRaises(ValueError):self.load(row,[p])
        p,row=self.fixture();row['cases'][0]['budget']['sql_tool_calls']=1
        with self.assertRaises(ValueError):self.load(row,[p])

    def test_nonanswer_is_explicitly_excluded_without_becoming_a_pass(self):
        p,row=self.fixture();second=deepcopy(row['cases'][0]);second.update(case_id='BIRD-PG-9998',status='clarification',complete=False)
        second.pop('generated_sql');second['executions']=[]
        row['cases'].append(second);row['selected_case_ids'].append(second['case_id'])
        p2={**p,'case_id':second['case_id']};(source,pairs,excluded),calls=self.load(row,[p,p2])
        self.assertEqual(len(pairs),1);self.assertEqual(len(excluded),1);self.assertFalse(excluded[0]['counted_as_success'])

    def test_changed_captured_sql_bytes_are_refused(self):
        p,row=self.fixture();row['cases'][0]['generated_sql']='SELECT 1'
        with self.assertRaises(ValueError):self.load(row,[p])


if __name__=='__main__':unittest.main()
