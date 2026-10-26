"""Offline checks for 0407 source authority and public output evidence.

These tests do not run SQL, read Gold, call a model, or connect to PostgreSQL.
Hypothetical relation variants test gate behavior; they do not revise the
recorded BIRD source facts.
"""
from copy import deepcopy
from types import SimpleNamespace as NS
import unittest

from evaluation.bird.demand_relations import relation_candidates
from evaluation.bird.evidence import ACCEPTED_VALIDATION_SHA
from evaluation.bird.output_contract import build_contract, observe
from evaluation.bird.reviewed_relations import REVIEWED_RELATIONS
from test_m3_condition_relations import fixture
from evaluation.bird.demand_relations import expand_context, annotate_graph, validate_options


ROW = next(row for row in REVIEWED_RELATIONS
           if row['source_identity']['logical_database_id'] == 'card_games')
PUBLIC = dict(
    case_id='BIRD-PG-9000', database_id='card_games', dialect='postgres',
    question='Lists all types of cards in German.',
    evidence=('German refer to language; all types refer to the subtypes, '
              'supertypes; subtypes is not null AND supertypes is not null'),
)


def runtime():
    identity=deepcopy(ROW['source_identity'])
    tables=[dict(id='card_games.cards',name='cards',database='card_games',
                 physical_schema='public',fields=[dict(name='uuid',type='text')]),
            dict(id='card_games.foreign_data',name='foreign_data',database='card_games',
                 physical_schema='public',fields=[dict(name='uuid',type='text')])]
    return NS(database_id='card_games',identity=NS(public=lambda:identity),
              domain=dict(query_role=ROW['query_role']),
              catalog=NS(version=identity['catalog_version'],tables=tables,relations=[]),
              verification=dict(live_target_verified=True,role=ROW['query_role'],
                  accepted_validation_sha256=ACCEPTED_VALIDATION_SHA,
                  authorized_data_version=identity['data_version'],
                  authorized_catalog_version=identity['catalog_version']))


def graph():
    specs=(('cards','subtypes'),('cards','supertypes'),
           ('foreign_data','language'),('foreign_data','type'))
    fields=[dict(id='card_games.'+table+'.'+name,
                 table_id='card_games.'+table,table_name=table,
                 name=name,label=name,type='text',source='retrieval')
            for table,name in specs]
    return dict(database='card_games',source_identity=deepcopy(ROW['source_identity']),
                tables=[dict(id='card_games.cards',name='cards'),
                        dict(id='card_games.foreign_data',name='foreign_data')],
                fields=fields,joins=[])


class RelationAuthorityTest(unittest.TestCase):
    def candidate(self,row=None,rt=None):
        return relation_candidates(rt or runtime(),[deepcopy(row or ROW)])[0]

    def test_recorded_source_is_diagnostic_only(self):
        actual=self.candidate()
        self.assertEqual(actual['orphan_rows'],16)
        self.assertIn('dev_tables.json',actual['ownership_basis'])
        self.assertFalse(actual['declared_foreign_key'])
        self.assertTrue(actual['source_bound'])
        self.assertFalse(actual['eligible'])
        self.assertEqual(actual['decision_reason'],'incomplete_child_key_coverage')

    def test_ownership_claim_does_not_hide_orphans(self):
        row=deepcopy(ROW)
        row['ownership_basis']='Synthetic test-only independent ownership review'
        actual=self.candidate(row)
        self.assertFalse(actual['eligible'])
        self.assertEqual(actual['decision_reason'],'incomplete_child_key_coverage')

    def test_hypothetical_full_coverage_does_not_supply_missing_ownership(self):
        row=deepcopy(ROW)
        row['orphan_rows']=0
        row['matching_child_rows']=row['child_nonnull_rows']
        row['ownership_basis']=None
        actual=self.candidate(row)
        self.assertFalse(actual['eligible'])
        self.assertEqual(actual['decision_reason'],'ownership_not_reviewed')

    def test_only_hypothetical_both_gates_pass(self):
        row=deepcopy(ROW)
        row['orphan_rows']=0
        row['matching_child_rows']=row['child_nonnull_rows']
        row['ownership_basis']='Synthetic test-only independent ownership review'
        actual=self.candidate(row)
        self.assertTrue(actual['eligible'])
        self.assertFalse(actual['declared_foreign_key'])
        self.assertIsNone(actual['join_type'])

    def test_mismatched_source_rejected_before_any_candidate_use(self):
        row=deepcopy(ROW)
        row['source_identity']['data_version']='different_version'
        actual=self.candidate(row)
        self.assertFalse(actual['source_bound'])
        self.assertFalse(actual['eligible'])
        self.assertEqual(actual['decision_reason'],'source_identity_mismatch')


class PublicOutputTest(unittest.TestCase):
    def test_exact_public_evidence_resolves_two_ordered_authorized_fields(self):
        contract=build_contract(PUBLIC,graph())
        self.assertTrue(contract['parse_complete'])
        self.assertEqual(len(contract['items']),1)
        self.assertEqual(contract['items'][0]['kind'],'field_group')
        self.assertEqual(contract['items'][0]['field_ids'],
                         ['card_games.cards.subtypes','card_games.cards.supertypes'])
        self.assertEqual(contract['items'][0]['authority'],'explicit_public_definition')

    def test_saved_wrong_projection_detected_without_scoring_or_sql_rewrite(self):
        contract=build_contract(PUBLIC,graph())
        sql="SELECT DISTINCT fd.type FROM foreign_data fd WHERE fd.language = 'German' AND fd.type IS NOT NULL"
        observed=observe(contract,graph(),sql)
        self.assertTrue(observed['report_only'])
        self.assertIn('requested_output_not_observed',
                      [issue['code'] for issue in observed['issues']])
        self.assertNotIn('correct',observed)

    def test_projection_observation_alone_does_not_prove_language_or_join(self):
        contract=build_contract(PUBLIC,graph())
        observed=observe(contract,graph(),'SELECT c.subtypes, c.supertypes FROM cards c')
        self.assertEqual(observed['issues'],[])
        self.assertIn('does not establish SQL correctness',observed['meaning'])

    def test_missing_or_conflicting_member_stays_unresolved(self):
        g=graph()
        g['fields']=[f for f in g['fields'] if f['name']!='supertypes']
        missing=build_contract(PUBLIC,g)
        self.assertFalse(missing['parse_complete'])
        self.assertEqual(missing['items'][0]['authority'],'incomplete_public_definition')
        self.assertEqual(missing['items'][0]['field_ids'],[])
        conflicting=dict(PUBLIC,evidence='all types refer to subtypes, supertypes; all types refer to language, type')
        self.assertFalse(build_contract(conflicting,graph())['parse_complete'])


class IncompleteCandidateContextTest(unittest.TestCase):
    def source(self):
        r,docs,_,public,_=fixture('card_games',extra=18)
        selected=[(i,.8-i*.001) for i,d in enumerate(docs)
                  if d.field_name not in ('uuid','filler16')]
        self.assertEqual(len(selected),20)
        return r,docs,selected,public

    def test_bounded_keys_and_public_output_are_admitted_together(self):
        r,docs,selected,public=self.source()
        chosen,trace=expand_context(r,docs,selected,public,relation_output=True)
        self.assertEqual(len(chosen),20)
        decision=trace['decisions'][-1]
        self.assertTrue(decision['selected'])
        self.assertEqual(decision['added_field_ids'],
            ['card_games.cards.uuid','card_games.foreign_data.uuid'])
        self.assertEqual(len(decision['evicted_fields']),2)
        self.assertEqual(decision['output_field_ids'],
            ['card_games.cards.subtypes','card_games.cards.supertypes'])
        self.assertEqual(decision['filter_field_ids'],['card_games.foreign_data.language'])
        ids={docs[i].doc_id for i,_ in chosen}
        self.assertTrue(set(decision['output_field_ids']+decision['filter_field_ids']+decision['added_field_ids'])<=ids)
        joined=annotate_graph(r,dict(tables=[],fields=[],joins=[]),trace)['joins'][0]
        self.assertFalse(joined['declared_foreign_key'])
        self.assertIsNone(joined['join_type'])
        self.assertIn('16 child orphan rows',joined['description'])

    def test_wrong_source_and_missing_authority_cannot_admit_relation(self):
        r,docs,selected,public=self.source()
        r.verification['authorized_data_version']='other'
        self.assertFalse(expand_context(r,docs,selected,public,relation_output=True)[1]['decisions'][-1]['selected'])
        r,docs,selected,public=self.source()
        row=deepcopy(ROW);row['source_review_sha256']=None
        self.assertFalse(expand_context(r,docs,selected,public,reviewed=[row],relation_output=True)[1]['decisions'][-1]['selected'])

    def test_incomplete_public_request_or_no_safe_slots_stays_unresolved(self):
        r,docs,selected,public=self.source()
        public['evidence']='German refer to language; all types refer to subtypes; supertypes is not null'
        self.assertFalse(expand_context(r,docs,selected,public,relation_output=True)[1]['decisions'][-1]['selected'])
        r,docs,selected,public=self.source()
        selected=[(i,0.0 if d.field_name.startswith('filler') else .8) for i,d in enumerate(docs)
                  if d.field_name not in ('uuid','filler16')]
        chosen,trace=expand_context(r,docs,selected,public,relation_output=True)
        self.assertEqual(chosen,selected)
        self.assertEqual(trace['decisions'][-1]['decision_reason'],'context_field_cap')

    def test_e02_policy_remains_separate(self):
        r,docs,selected,public=self.source()
        self.assertEqual(expand_context(r,docs,selected,public)[0],selected)
        with self.assertRaises(Exception):
            validate_options(True,diagnostic=True,coverage=True,intent=True,output=True)
        validate_options(True,diagnostic=True,coverage=True,intent=True,output=True,relation_output=True)

    def test_1479_condition_path_survives_e03_without_output_relation(self):
        r,docs,selected,public,_=fixture()
        chosen,trace=expand_context(r,docs,selected,public,relation_output=True)
        self.assertEqual(len(chosen),5)
        self.assertEqual(trace['decisions'][0]['decision_reason'],'condition_and_keys_admitted_atomically')
        self.assertEqual(trace['decisions'][-1]['decision_reason'],'unresolved_output_group_or_filter')
        self.assertEqual(len(trace['admitted_relations']),1)


if __name__=='__main__':
    unittest.main()
