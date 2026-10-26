"""Coverage candidate boundaries and full retrieval-to-Schema integration (offline)."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from app.retrieval.store import FieldDocument
from evaluation.bird.budgets import BirdFailure
from evaluation.bird.coverage import select_fields,contract,POLICY
from evaluation.bird.model import ModelConfig
from scripts.m2_b_common import digest_json


def document(name,label=None,table='t',db='db'):
    raw={'doc_id':db+'.'+table+'.'+name,'database_id':db,'table_id':db+'.'+table,
        'table_label':table,'field_name':name,'field_label':label or name,'field_type':'text',
        'field_description':'official','field_role':'field','aliases':[],'samples':[],
        'profile':'','keyword_text':'metadata','semantic_text':'metadata','rerank_text':name,'relation_ids':[]}
    return FieldDocument(**raw,dense_vector=[0.0]*1024,schema_version='unit',content_hash=digest_json(raw))


def public(question='School postal street address',evidence='Indicate school name.'):
    return {'case_id':'BIRD-PG-0000','database_id':'db','dialect':'postgres','question':question,'evidence':evidence}


def select(docs,scores,p=None,enabled=True):
    return select_fields(docs,list(range(len(docs))),scores,p or public(),enabled=enabled)


class CoverageSelectionTest(unittest.TestCase):
    def test_school_name_is_rescued_without_globally_lowering_threshold(self):
        docs=[document('avgscrmath'),document('sname','school name'),document('unrelated','unrelated')]
        selected,detail=select(docs,{0:.9,1:.5479438051904237,2:.54})
        self.assertEqual([i for i,_ in selected],[0,1])
        self.assertEqual(detail['coverage_field_ids'],['db.t.sname'])
        self.assertEqual(detail['candidate_decisions'][1]['matched_intent_terms'],['school'])
        self.assertEqual(detail['candidate_decisions'][2]['selection_reason'],'coverage_no_intent_match')

    def test_date_uses_official_evidence_not_a_case_id_rule(self):
        docs=[document('consumption'),document('date')]
        p=public('Average monthly consumption in 2013','First four strings of the Date represent year')
        selected,detail=select(docs,{0:.9,1:.513904057769749},p)
        self.assertEqual([i for i,_ in selected],[0,1])
        p['case_id']='BIRD-PG-9999'
        self.assertEqual(select(docs,{0:.9,1:.513904057769749},p),(selected,detail))

    def test_floor_inclusive_and_missing_rerank_are_distinct(self):
        docs=[document('id'),document('school'),document('school_low'),document('school_missing')]
        selected,d=select(docs,{0:.9,1:.5,2:.499999})
        self.assertEqual([i for i,_ in selected],[0,1])
        self.assertEqual(d['candidate_decisions'][2]['selection_reason'],'below_coverage_floor')
        self.assertEqual(d['candidate_decisions'][3]['selection_reason'],'rerank_not_returned')

    def test_never_expands_into_unanchored_tables_or_empty_baseline(self):
        docs=[document('id'),document('school',table='other')]
        chosen,d=select(docs,{0:.9,1:.54})
        self.assertEqual(chosen,[(0,.9)])
        self.assertEqual(d['candidate_decisions'][1]['selection_reason'],'coverage_table_not_anchored')
        self.assertEqual(select(docs,{0:.54,1:.54})[0],[])

    def test_does_not_mine_samples_descriptions_or_table_names_for_intent(self):
        docs=[document('id'),document('opaque','Opaque')]
        docs[1].samples=['school'];docs[1].field_description='school'
        self.assertEqual(select(docs,{0:.9,1:.54})[0],[(0,.9)])
        self.assertEqual(select(docs,{0:.9,1:.54},public('Generic question',''))[0],[(0,.9)])

    def test_four_additions_maximum_with_stable_ties(self):
        words=['school','address','date','segment','gender','salary','balance']
        docs=[document('id')]+[document(w) for w in words]
        chosen,d=select(docs,{i:.9 if i==0 else .54 for i in range(len(docs))},public(' '.join(words),''))
        self.assertEqual([i for i,_ in chosen],list(range(5)))
        self.assertEqual(len(d['coverage_field_ids']),4)
        self.assertEqual(d['candidate_decisions'][5]['selection_reason'],'coverage_addition_cap')

    def test_total_twenty_cap_preserves_all_baseline_fields(self):
        docs=[document('f'+str(i)) for i in range(19)]+[document('school'),document('address')]
        chosen,d=select(docs,{i:.9 if i<19 else .54 for i in range(21)})
        self.assertEqual([i for i,_ in chosen],list(range(20)))
        self.assertEqual(d['candidate_decisions'][20]['selection_reason'],'coverage_total_field_cap')
        chosen,_=select(docs,{i:.9 if i<20 else .54 for i in range(21)})
        self.assertEqual([i for i,_ in chosen],list(range(20)))

    def test_coverage_requires_new_intent_gain_and_avoids_redundant_fields(self):
        docs=[document('mailstreet','mailing street'),document('avgscrmath','average math'),
              document('sname','school name'),document('mailcity','mailing city'),document('avgscrwrite','average writing')]
        chosen,d=select(docs,{0:.9,1:.9,2:.54794,3:.52,4:.503},public('School postal address and Math average','Mailing street'))
        self.assertEqual([i for i,_ in chosen],[0,1,2])
        for i in (3,4):self.assertEqual(d['candidate_decisions'][i]['selection_reason'],'coverage_intent_already_covered')

    def test_default_frozen_selection_is_byte_equivalent_for_same_inputs(self):
        docs=[document('f'+str(i)) for i in range(30)]
        scores={i:.9-i*.01 for i in range(30)};scores[28]=.54
        want=sorted(((i,s) for i,s in scores.items() if s>=.55),key=lambda x:x[1],reverse=True)[:20]
        chosen,d=select(docs,scores,enabled=False)
        self.assertEqual(chosen,want);self.assertEqual(d['coverage_field_ids'],[])
        self.assertFalse(contract()['development_candidate']);self.assertTrue(contract(True)['development_candidate'])

    def test_foreign_source_and_malformed_rerank_fail_closed(self):
        docs=[document('id'),document('school',db='foreign')]
        with self.assertRaises(BirdFailure):select(docs,{0:.9,1:.1})
        for scores in ({0:float('nan')},{0:float('inf')},{0:-1},{0:1.1},{9:.9},{True:.9}):
            with self.subTest(scores=scores),self.assertRaises(BirdFailure):select([document('id')],scores)
        with self.assertRaises(ValueError):select([document('id')],{0:.9},{**public(),'gold_sql':'PRIVATE'})


class CoverageIntegrationTest(unittest.TestCase):
    def test_real_retrieval_graph_and_report_include_coverage_with_no_extra_calls(self):
        from evaluation.bird.retrieval import retrieve,index_identity
        docs=[document('consumption'),document('date')]
        table={'id':'db.t','name':'public.t','database':'db','label':'t','description':'official',
            'fields':[{'name':d.field_name,'label':d.field_label,'type':'text','description':'official','role':'field'} for d in docs]}
        identity={'logical_database_id':'db','source_id':'unit','backend':'postgresql','dialect':'postgres','prompt_dialect':'PostgreSQL','physical_schema':'public'}
        runtime=SimpleNamespace(database_id='db',domain={'query_role':'ro'},identity=SimpleNamespace(public=lambda:identity),
            catalog=SimpleNamespace(tables=[table],relations=[]))
        calls=[]
        class Store:
            embedding_source='text-embedding-v4'
            def __init__(self,*a):self.documents=docs
            def load(self,*a,**k):return True
            def bm25_search(self,*a):return [(0,.9),(1,.8)]
            def dense_search(self,*a):return [(0,.9),(1,.8)]
        class Models:
            config=ModelConfig('fake')
            def embed(self,texts):calls.append('embedding');return [[0.0]*1024]
            def rerank(self,*a):calls.append('rerank');return {0:.9,1:.513904057769749}
        p=public('Average consumption','Date represents year')
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'index.json';path.write_text('{}')
            with patch('evaluation.bird.retrieval.LocalSchemaStore',Store):
                frozen=retrieve(runtime,Models(),path,p)
                candidate=retrieve(runtime,Models(),path,p,schema_coverage=True)
        self.assertEqual(calls,['embedding','rerank']*2)
        self.assertEqual(frozen['retrieval']['selected_field_ids'],['db.t.consumption'])
        self.assertEqual(candidate['retrieval']['coverage_field_ids'],['db.t.date'])
        fields={f['id']:f for f in candidate['graph']['fields']}
        self.assertEqual(fields['db.t.date']['source'],'schema_coverage')
        self.assertIn('date',candidate['schema_text'])
        d=candidate['_report_diagnostics']
        self.assertEqual(d['selection_policy']['policy_id'],POLICY)
        self.assertEqual(d['candidates'][1]['selection_reason'],'selected_coverage')
        self.assertEqual(d['candidates'][1]['matched_intent_terms'],['date'])
        self.assertEqual(d['schema_graph'],candidate['graph'])
        self.assertIn('coverage.py',index_identity(runtime,Models.config)['code_sha256'])
        self.assertNotIn('dense_vector',json.dumps(d))

    def test_formal_live_cannot_silently_enable_development_candidate(self):
        from evaluation.bird.case_worker import execute
        request={'mode':'live','input':{'database_id':'db','case_id':'BIRD-PG-0000'},
            'gold':{'database_id':'db','case_id':'BIRD-PG-0000','gold_sql_sha256':'unit'},
            'code_sha256':'unit','schema_coverage_enabled':True}
        with patch('evaluation.bird.case_worker.code_binding',return_value={'sha256':'unit'}):result=execute(request)
        self.assertEqual(result['errors'],[{'category':'schema_coverage_development_only','sqlstate':None}])


if __name__=='__main__':unittest.main()
