"""Public-only grain, contradictory evidence and explicit precision boundaries."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

from test_m2_intent_candidate import context, field, public, contract, codes
from evaluation.bird.intent import public_condition_evidence, bound_public_conditions, build_contract, violations, policy
from evaluation.bird.relationships import grain_contract
from evaluation.bird.units_output import precision_contract, unit_contract
from evaluation.bird.evidence import Evidence, DEFAULT_DATA, public_cases
from scripts.m2_b_common import BASE
from scripts.m2_b_structure import expectations


def atomic():
    p=field('particle_id');p['role']='primary_key'
    e=field('edge_id');e['role']='primary_key'
    return context({'particle':[p,field('group_id'),field('element')], 'edge':[e,field('group_id')]})


JOIN=" FROM particle p JOIN edge e ON p.group_id=e.group_id"
WEIGHTED="SELECT CAST(SUM(CASE WHEN p.element='c' THEN 1 ELSE 0 END) AS REAL)*100/COUNT(p.particle_id)"+JOIN
DISTINCT="SELECT CAST(COUNT(DISTINCT CASE WHEN p.element='c' THEN p.particle_id END) AS REAL)*100/COUNT(DISTINCT p.particle_id)"+JOIN


class GrainAuthorityTest(unittest.TestCase):
    def test_primary_key_count_and_fanout_are_advisory(self):
        r=atomic();p=public('Percentage of particles',"SUM(element='c')/COUNT(particle_id)")
        c=grain_contract(r,p)
        self.assertEqual(c['enforcement'],'advisory');self.assertEqual(c['grain'],'unspecified')
        self.assertNotIn('entity_grain_fanout',codes(r,WEIGHTED,p))

    def test_explicit_count_distinct_preserves_hard_fanout_check(self):
        r=atomic();p=public('Percentage of particles','percentage=COUNT(DISTINCT particle_id)/COUNT(DISTINCT particle_id)')
        self.assertEqual(grain_contract(r,p)['enforcement'],'hard')
        self.assertIn('entity_grain_fanout',codes(r,WEIGHTED,p))
        self.assertNotIn('entity_grain_fanout',codes(r,DISTINCT,p))

    def test_unique_entity_request_has_bound_public_basis(self):
        r=atomic()
        for question in ('Percentage of unique particles','Percentage of different particles','Percentage counting each particle once'):
            p=public(question,'COUNT(particle_id)');g=grain_contract(r,p)
            self.assertEqual(g['enforcement'],'hard',question)
            self.assertTrue(g['public_basis']);self.assertIn('entity_grain_fanout',codes(r,WEIGHTED,p))

    def test_unique_other_entity_or_values_cannot_force_particle_deduplication(self):
        r=atomic()
        for question in ('Percentage of particles connected to unique edges','Percentage of distinct values'):
            self.assertEqual(grain_contract(r,public(question,'COUNT(particle_id)'))['enforcement'],'advisory')

    def test_explicit_joined_row_weighting_is_preserved(self):
        r=atomic();p=public('Percentage over all joined records','COUNT(particle_id)')
        g=grain_contract(r,p);self.assertEqual(g['grain'],'joined_rows');self.assertEqual(g['enforcement'],'advisory')
        self.assertNotIn('entity_grain_fanout',codes(r,WEIGHTED,p))

    def test_ambiguous_identifier_owner_has_no_hard_grain(self):
        r=atomic();r.catalog.tables[1]['fields'].append({**field('particle_id'),'role':'primary_key'})
        r.catalog.tables[1]['fields'][0]['role']='field'
        self.assertEqual(grain_contract(r,public('Percentage','COUNT(DISTINCT particle_id)')),{})

    def test_single_table_and_semijoin_are_not_fanout(self):
        r=atomic();p=public('Percentage of unique particles','COUNT(particle_id)')
        self.assertNotIn('entity_grain_fanout',codes(r,"SELECT CAST(COUNT(particle_id) AS REAL)*100/COUNT(particle_id) FROM particle",p))
        sql="SELECT CAST(SUM(CASE WHEN p.element='c' THEN 1 ELSE 0 END) AS REAL)*100/COUNT(p.particle_id) FROM particle p WHERE EXISTS(SELECT 1 FROM edge e WHERE p.group_id=e.group_id)"
        self.assertNotIn('entity_grain_fanout',codes(r,sql,p))

    def test_repeated_count_mentions_cannot_erase_explicit_distinct(self):
        r=atomic();p=public('Percentage','COUNT(DISTINCT particle_id); COUNT(particle_id)')
        self.assertEqual(grain_contract(r,p)['enforcement'],'hard')

    def test_case_ids_do_not_select_grain_policy(self):
        r=atomic();p=public('Percentage of particles','COUNT(particle_id)');old=grain_contract(r,p)
        p['case_id']='BIRD-PG-0001';self.assertEqual(old,grain_contract(r,p))


class EvidenceRoleTest(unittest.TestCase):
    def runtime(self):return context({'particle':[field('element'),field('label'),field('particle_id')]})

    def conditions(self,p):
        r=self.runtime();ids={t['id']+'.'+f['name'] for t in r.catalog.tables for f in t['fields']}
        return bound_public_conditions(r,p,ids,{'matches':[]})

    def test_definition_formula_conflict_is_recorded_without_forced_conjunction(self):
        p=public('Percentage of chlorine',"chlorine means element='cl'; percentage=DIVIDE(SUM(element='pb');COUNT(particle_id)) where label='+'")
        record=public_condition_evidence(p)
        self.assertEqual(len(record['conflicts']),1)
        self.assertEqual(record['conflicts'][0]['values'],['cl','pb'])
        self.assertEqual([v['field'] for v in self.conditions(p)],['label'])

    def test_numerator_denominator_different_values_are_legitimate_scopes(self):
        p=public('Ratio',"ratio=DIVIDE(SUM(element='cl'),SUM(element='pb'))")
        record=public_condition_evidence(p)
        self.assertEqual(record['conflicts'],[])
        self.assertEqual([v['role'] for v in record['conditions']],['numerator_condition','denominator_condition'])
        self.assertEqual([v['value'] for v in self.conditions(p)],['cl','pb'])

    def test_same_field_and_value_repetition_is_not_a_conflict(self):
        p=public('Percentage',"chlorine means element='cl'; percentage=DIVIDE(SUM(element='cl'),COUNT(particle_id))")
        self.assertEqual(public_condition_evidence(p)['conflicts'],[])
        self.assertTrue(self.conditions(p))

    def test_independent_field_conditions_remain_mandatory(self):
        p=public('Items',"element='cl'; label='+'")
        self.assertEqual({v['field'] for v in self.conditions(p)},{'element','label'})
        self.assertTrue(all(v['mandatory'] for v in self.conditions(p)))

    def test_conflicting_same_scope_values_remain_advisory(self):
        p=public('Items',"element='cl'; element='pb'")
        self.assertEqual(self.conditions(p),[]);self.assertTrue(public_condition_evidence(p)['conflicts'])

    def test_qualified_different_owners_are_not_a_conflict(self):
        p=public('Items',"a.element='cl'; b.element='pb'")
        self.assertFalse(public_condition_evidence(p)['conflicts'])

    def test_existing_or_negation_uncertainty_remain_conservative(self):
        for evidence in ("element='cl' OR element='pb'","not element='cl'","example element='cl'"):
            self.assertEqual(self.conditions(public('Items',evidence)),[])

    def test_literal_parentheses_and_commas_do_not_fake_aggregate_scopes(self):
        p=public('Items',"label='SUM(,('; element='cl'")
        self.assertEqual([v['role'] for v in public_condition_evidence(p)['conditions']],['definition','definition'])

    def test_span_preserves_original_public_evidence_and_escaped_quote(self):
        p=public('Items',"label='O''Brien'")
        v=public_condition_evidence(p)['conditions'][0];a,b=v['evidence_span']
        self.assertEqual(v['value'],"O'Brien");self.assertEqual(p['evidence'][a:b],"label='O''Brien'")

    def test_private_inputs_rejected_and_case_ids_do_not_choose_conflicts(self):
        p=public('Items',"element='cl'; element='pb'");old=public_condition_evidence(p)
        p['case_id']='BIRD-PG-9998';self.assertEqual(old,public_condition_evidence(p))
        with self.assertRaises(ValueError):public_condition_evidence({**p,'gold_sql':'private'})


class PrecisionTest(unittest.TestCase):
    def test_words_digits_and_zero_decimal_places(self):
        for phrase,value in [('five decimal places',5),('5 decimal places',5),('zero decimal places',0),('two decimal places',2)]:
            p=public('Percentage with '+phrase);c=precision_contract(p)
            self.assertEqual(c['decimal_places'],value);self.assertEqual(c['enforcement'],'hard_for_simple_numeric_output')
            self.assertEqual(c['requests'][0]['source'],'question')

    def test_conflicting_or_unsupported_precision_is_advisory(self):
        for p in (public('Percentage with five decimal places','Round to two decimal places'),public('Percentage with 99 decimal places')):
            c=precision_contract(p);self.assertEqual(c['enforcement'],'advisory');self.assertIsNone(c['decimal_places'])

    def test_no_precision_or_significant_figures_are_not_decimal_places(self):
        for q in ('Percentage rounded appropriately','Percentage with five significant figures','List names'):
            self.assertIsNone(precision_contract(public(q))['decimal_places'])

    def test_explicit_do_not_round_does_not_create_precision_gate(self):
        c=precision_contract(public('Do not round the answer','The column uses five decimal places'))
        self.assertEqual(c['enforcement'],'advisory');self.assertTrue(c['conflict'])

    def test_correct_outer_round_and_numeric_scale_pass(self):
        r=context();p=public('Percentage with five decimal places')
        for sql in ('SELECT ROUND(CAST(COUNT(*) AS NUMERIC)*100/COUNT(id),5) FROM items',
                    'SELECT CAST(CAST(COUNT(*) AS NUMERIC)*100/COUNT(id) AS NUMERIC(20,5)) FROM items'):
            self.assertNotIn('requested_decimal_precision',codes(r,sql,p))

    def test_missing_or_wrong_round_scale_gets_specific_feedback(self):
        r=context();p=public('Percentage with five decimal places')
        for sql in ('SELECT CAST(COUNT(*) AS DOUBLE PRECISION)*100/COUNT(id) FROM items',
                    'SELECT ROUND(CAST(COUNT(*) AS NUMERIC)*100/COUNT(id),4) FROM items'):
            issues=violations(r,p,contract(r,p),sql)
            issue=next(v for v in issues if v['code']=='requested_decimal_precision')
            self.assertEqual(issue['expected_decimal_places'],5)

    def test_round_inside_aggregate_or_unrelated_filter_is_not_final_precision(self):
        r=context();p=public('Average with five decimal places')
        for sql in ('SELECT AVG(ROUND(score,5)) FROM items','SELECT AVG(score) FROM items WHERE ROUND(score,5)>0'):
            self.assertIn('requested_decimal_precision',codes(r,sql,p))

    def test_scale_and_precision_both_preserved(self):
        r=context();p=public('Percentage with five decimal places')
        sql='SELECT ROUND(CAST(COUNT(*) AS NUMERIC)/COUNT(id),5) FROM items'
        self.assertNotIn('requested_decimal_precision',codes(r,sql,p));self.assertIn('percentage_output_unit',codes(r,sql,p))

    def test_complex_cte_and_multiple_outputs_do_not_get_fabricated_precision(self):
        r=context();p=public('Percentage with five decimal places')
        for sql in ('WITH q AS (SELECT ROUND(AVG(score),5) AS v FROM items) SELECT v FROM q',
                    'SELECT name,AVG(score) FROM items GROUP BY name'):
            self.assertNotIn('requested_decimal_precision',codes(r,sql,p))

    def test_generic_rounding_without_places_and_case_id_invariance(self):
        p=public('Percentage with five decimal places');old=unit_contract(p);p['case_id']='BIRD-PG-0001'
        self.assertEqual(old,unit_contract(p));self.assertEqual(policy()['policy_id'],'bird_public_intent_candidate_v4')


class CapturedSixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path('E:/PythonLearn/datasets/bird_mini_dev') if Path('E:/PythonLearn/datasets/bird_mini_dev').exists() else DEFAULT_DATA
        e=Evidence.load(root);cls.runtimes={};cls.public={p['case_id']:p for p in public_cases('development80')}
        cls.cases={c['case_id']:c for c in json.loads((BASE/'evaluation/results/m2_public_intent_v3_development80_server_rerun_v2.json').read_bytes())['cases']}
        for db in ('toxicology','card_games','codebase_community'):
            r=object.__new__(__import__('evaluation.bird.runtime',fromlist=['BirdRuntime']).BirdRuntime)
            r.evidence=e;r.database_id=db;r.domain=e.domain(db);r.tables=e.tables(db);r.names=set(r.domain['tables']);r.expected=expectations(e.manifest)
            r._descriptions,r.description_diagnostic=e.descriptions(db)
            r.catalog=r._catalog({t['name']:e.validation['structure']['verified_structure']['columns'][t['name']] for t in r.tables})
            identity=next(c['source_identity'] for c in cls.cases.values() if c['database_id']==db);r.identity=NS(public=lambda identity=identity:identity)
            cls.runtimes[db]=r

    def rebuilt(self,cid):
        c=self.cases[cid];r=self.runtimes[c['database_id']];p=self.public[cid]
        return r,p,build_contract(r,p,c['development_diagnostics']['retrieval']['schema_graph']['value'],
                                 c['retrieval']['intent_selection'],c['canonical_lookup'])

    def test_0263_and_0201_ambiguous_first_queries_are_both_advisory(self):
        for cid in ('BIRD-PG-0263','BIRD-PG-0201'):
            r,p,c=self.rebuilt(cid);sql=self.cases[cid]['development_diagnostics']['attempts'][0]['sql']['text']
            self.assertEqual(c['entity_grain']['enforcement'],'advisory')
            self.assertNotIn('entity_grain_fanout',[v['code'] for v in violations(r,p,c,sql)])

    def test_0273_conflict_is_visible_and_first_query_has_no_invented_pb_filter(self):
        cid='BIRD-PG-0273';r,p,c=self.rebuilt(cid)
        self.assertEqual(c['public_evidence']['conflicts'][0]['values'],['cl','pb'])
        self.assertEqual([v['field'] for v in c['required_profile_conditions']],['label'])
        sql=self.cases[cid]['development_diagnostics']['attempts'][0]['sql']['text']
        self.assertEqual(violations(r,p,c,sql),[])

    def test_0226_captured_unrounded_sql_is_rejected_with_five_place_reason(self):
        cid='BIRD-PG-0226';r,p,c=self.rebuilt(cid)
        issues=violations(r,p,c,self.cases[cid]['generated_sql'])
        self.assertEqual([v['code'] for v in issues],['requested_decimal_precision'])
        self.assertEqual(issues[0]['expected_decimal_places'],5)

    def test_successful_saved_controls_keep_validity_and_private_fields_are_absent(self):
        for cid in ('BIRD-PG-0201','BIRD-PG-0368','BIRD-PG-0586'):
            r,p,c=self.rebuilt(cid)
            self.assertEqual(violations(r,p,c,self.cases[cid]['generated_sql']),[],cid)
            self.assertNotIn('gold_sql',json.dumps(c));self.assertNotIn('native_comparison',json.dumps(c))


if __name__=='__main__':unittest.main()
