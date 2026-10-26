"""Public-unit/output boundaries and captured-query regressions; no live DB/model."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

import sqlglot
from sqlglot import exp
from test_m2_intent_candidate import context,field,public,contract,codes
from evaluation.bird.intent import build_contract,policy,violations
from evaluation.bird.units_output import unit_contract,count_ratio_scale,participant_output_contract
from evaluation.bird.retrieval import index_identity
from evaluation.bird.evidence import Evidence,DEFAULT_DATA,public_cases
from scripts.m2_b_common import BASE
from scripts.m2_b_structure import expectations


class PublicUnitTest(unittest.TestCase):
    def test_percentage_formula_missing_scale_is_explicitly_recorded(self):
        p=public('What is the percentage of active items?','percentage=DIVIDE(SUM(active=1),COUNT(id))')
        u=unit_contract(p)
        self.assertEqual(u['ratio_multiplier'],100);self.assertEqual(u['output_unit'],'percent_0_100')
        self.assertTrue(u['question_formula_scale_conflict']);self.assertTrue(u['resolution_is_development_convention'])

    def test_scaled_formula_has_no_omitted_scale_conflict(self):
        u=unit_contract(public('What percentage is active?','percentage=COUNT(active)*100/COUNT(id)'))
        self.assertEqual(u['ratio_multiplier'],100);self.assertFalse(u['question_formula_scale_conflict'])

    def test_explicit_fraction_and_exact_formula_override_percentage(self):
        for q,e in [('What percentage is active? Return a fraction.',''),('What percentage is active?','Return ratio in 0-1'),
                    ('What percentage is active? Express as a ratio.','')]:
            u=unit_contract(public(q,e));self.assertEqual(u['ratio_multiplier'],1)
        u=unit_contract(public('What percentage is active? Follow the formula exactly.','percentage=COUNT(active)/COUNT(id)'))
        self.assertIsNone(u['ratio_multiplier']);self.assertEqual(u['output_unit'],'formula_defined')

    def test_ratio_and_nonunit_questions_do_not_gain_percent_scale(self):
        self.assertEqual(unit_contract(public('What is the ratio of active items?'))['ratio_multiplier'],1)
        self.assertIsNone(unit_contract(public('List item names'))['ratio_multiplier'])

    def test_explicit_decimal_and_rounding_requests_are_preserved(self):
        p=public('What percentage is active? Use NUMERIC arithmetic.')
        self.assertFalse(contract(context(),p)['percentage_real_arithmetic'])
        self.assertNotIn('percentage_numeric_path',codes(context(),'SELECT COUNT(*)*100.0/COUNT(id) FROM items',p))
        for q in ('Percentage rounded to two decimal places','Percentage with decimal places'):
            self.assertFalse(contract(context(),public(q))['percentage_real_arithmetic'])

    def test_unscaled_simple_count_ratio_gets_specific_unit_feedback(self):
        r=context();p=public('What percentage is active?')
        issues=violations(r,p,contract(r,p),'SELECT CAST(COUNT(*) AS REAL)/NULLIF(COUNT(id),0) FROM items')
        issue=next(v for v in issues if v['code']=='percentage_output_unit')
        self.assertEqual(issue['expected_multiplier'],'100');self.assertEqual(issue['observed_multiplier'],'1')

    def test_both_scaled_orders_and_float_types_are_allowed(self):
        r=context();p=public('What percentage is active?')
        for cast in ('REAL','DOUBLE PRECISION'):
            for expression in (f'CAST(COUNT(*) AS {cast})*100/NULLIF(COUNT(id),0)',f'CAST(COUNT(*) AS {cast})/NULLIF(COUNT(id),0)*100'):
                self.assertEqual(codes(r,'SELECT '+expression+' FROM items',p),[])

    def test_filter_case_and_count_argument_constants_do_not_supply_scale(self):
        r=context();p=public('What percentage is active?')
        for expression in ('CAST(COUNT(id*100) AS REAL)/COUNT(id)',
                           'CAST(SUM(CASE WHEN score>100 THEN 1 ELSE 0 END) AS REAL)/COUNT(id)',
                           'CAST(COUNT(*) FILTER(WHERE score=100) AS REAL)/COUNT(id)'):
            # FILTER is outside this conservative count-ratio recognizer; the
            # other forms must not mistake a business literal for output scale.
            scale=count_ratio_scale(sqlglot.parse_one('SELECT '+expression,read='postgres').selects[0])
            self.assertIn(scale,(None,1));self.assertNotEqual(scale,100)
        self.assertIn('percentage_output_unit',codes(r,'SELECT CAST(COUNT(*) AS REAL)/COUNT(id) FROM items WHERE score=100',p))

    def test_complex_and_rounded_outputs_are_advisory(self):
        r=context();p=public('Percentage rounded to two decimal places')
        self.assertNotIn('percentage_output_unit',codes(r,'SELECT ROUND(AVG(score),2) FROM items',p))
        self.assertNotIn('percentage_output_unit',codes(r,'SELECT AVG(score) FROM items',public('Percentage of scores')))

    def test_fraction_scale_and_double_scaling_are_not_silently_accepted(self):
        r=context();ratio=public('Return the active ratio as a fraction')
        self.assertIn('percentage_output_unit',codes(r,'SELECT CAST(COUNT(*) AS REAL)*100/COUNT(id) FROM items',ratio))
        self.assertIn('percentage_output_unit',codes(r,'SELECT CAST(COUNT(*) AS REAL)*10000/COUNT(id) FROM items',public('Percentage active')))

    def test_units_are_case_id_invariant_and_private_input_is_rejected(self):
        p=public('Percentage active');u=unit_contract(p);p['case_id']='BIRD-PG-0000'
        self.assertEqual(unit_contract(p),u)
        with self.assertRaises(ValueError):unit_contract({**p,'gold_sql':'private'})


def output_fixture(question='Which user added a credit to the article title mentioning noise?'):
    relations=[dict(id='actor',left_table='db.users',left_field='id',right_table='db.actions',right_field='userid'),
               dict(id='target',left_table='db.articles',left_field='id',right_table='db.actions',right_field='articleid')]
    r=context({'users':[field('id'),field('displayname')],'articles':[field('id'),field('title')],
               'actions':[field('userid'),field('articleid'),field('credit')]},relations)
    roles=dict(context_output_groups=[dict(actor_label='db.users.displayname',context_label='db.articles.title')],
        preferred_actor_relations=[dict(relation_id='actor')],
        roles=[dict(relation_id='actor',parent_table='db.users',parent_field='id',child_table='db.actions',child_field='userid')])
    graph=dict(fields=[dict(id=t['id']+'.'+f['name']) for t in r.catalog.tables for f in t['fields']],relation_role_context=roles)
    p=public(question,'user refers to displayname; credit=7; title includes noise')
    selection=dict(baseline_field_ids=[f['id'] for f in graph['fields']],sample_condition_candidates=[])
    c=build_contract(r,p,graph,selection,{'matches':[]})
    return r,p,graph,c


class OutputGroupTest(unittest.TestCase):
    def test_unique_actor_action_target_gets_visible_required_pair(self):
        r,p,g,c=output_fixture();pair=c['participant_output']['required_groups'][0]
        self.assertEqual(pair['fields'],['db.users.displayname','db.articles.title'])
        self.assertEqual(pair['authority'],'versioned_public_action_target_output_convention')

    def test_missing_context_used_only_in_filter_is_reported(self):
        r,p,g,c=output_fixture()
        sql="SELECT u.displayname FROM users u JOIN articles a ON a.title=u.displayname WHERE a.title LIKE '%noise%'"
        self.assertIn('incomplete_participant_context_output',codes(r,sql,p,c))
        self.assertNotIn('incomplete_participant_context_output',codes(r,sql.replace('SELECT u.displayname','SELECT u.displayname,a.title'),p,c))

    def test_aliases_and_pair_order_are_checked(self):
        r,p,g,c=output_fixture()
        self.assertEqual(codes(r,'SELECT u.displayname AS actor,a.title AS target FROM users u JOIN articles a ON a.title=u.displayname',p,c),[])
        self.assertIn('participant_context_output_order',codes(r,'SELECT a.title,u.displayname FROM users u JOIN articles a ON a.title=u.displayname',p,c))

    def test_only_names_and_explicit_exclusions_override_pair(self):
        for tail in (' Return only user names.',' Return names only.',' Do not include titles.',' Without the title.'):
            r,p,g,c=output_fixture('Which user added a credit to the article title mentioning noise?'+tail)
            self.assertEqual(c['participant_output']['required_groups'],[])

    def test_where_context_and_counts_do_not_become_output_pairs(self):
        for q in ('Which user added a credit where the article title mentions noise?',
                  'Which user added a credit on articles where title mentions noise?',
                  'How many users added a credit to the article title mentioning noise?',
                  'List article titles added by users to the article title mentioning noise?'):
            r,p,g,c=output_fixture(q);self.assertEqual(c['participant_output']['required_groups'],[],q)

    def test_ambiguous_role_context_or_unselected_fields_remain_advisory(self):
        for change in ('role','group','missing','foreign'):
            r,p,g,c=output_fixture()
            if change=='role':g['relation_role_context']['preferred_actor_relations'].append(dict(relation_id='other'))
            if change=='group':g['relation_role_context']['context_output_groups']*=2
            if change=='missing':g['fields']=[f for f in g['fields'] if f['id']!='db.articles.title']
            if change=='foreign':g['relation_role_context']['context_output_groups'][0]['context_label']='foreign.private.title'
            self.assertEqual(participant_output_contract(p,g,{t['id']:t for t in r.catalog.tables},r.catalog.relations)['required_groups'],[])

    def test_fabricated_or_ambiguous_target_fk_cannot_mandate_projection(self):
        for relations in ('missing','ambiguous'):
            r,p,g,c=output_fixture();edges=deepcopy(r.catalog.relations)
            if relations=='missing':edges=[]
            else:edges.append({**edges[1],'id':'other_target','right_field':'other_articleid'})
            self.assertEqual(participant_output_contract(p,g,{t['id']:t for t in r.catalog.tables},edges)['required_groups'],[])

    def test_unresolved_cte_output_is_not_a_false_missing_field(self):
        r,p,g,c=output_fixture()
        sql='WITH q AS (SELECT u.displayname,a.title FROM users u JOIN articles a ON a.title=u.displayname) SELECT displayname,title FROM q'
        self.assertNotIn('incomplete_participant_context_output',codes(r,sql,p,c))

    def test_case_ids_and_filter_operator_do_not_control_output_policy(self):
        r,p,g,c=output_fixture();a=c['participant_output'];p['case_id']='BIRD-PG-0002'
        self.assertEqual(participant_output_contract(p,g,{t['id']:t for t in r.catalog.tables},r.catalog.relations),a)
        for operator in ('LIKE','ILIKE'):
            sql=f"SELECT u.displayname,a.title FROM users u JOIN articles a ON a.title=u.displayname WHERE a.title {operator} '%noise%'"
            self.assertEqual(codes(r,sql,p,c),[])


class CapturedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d=json.loads((BASE/'evaluation/results/m2_public_intent_v2_diagnostics14_server.json').read_bytes())
        cls.n=json.loads((BASE/'evaluation/results/m2_public_intent_v2_native14_server.json').read_bytes())
        cls.probe=json.loads((BASE/'evaluation/results/m2_units_context_probe2_server.json').read_bytes())
        root=Path('E:/PythonLearn/datasets/bird_mini_dev') if Path('E:/PythonLearn/datasets/bird_mini_dev').exists() else DEFAULT_DATA
        cls.e=Evidence.load(root);cls.public={p['case_id']:p for p in public_cases('development80')};cls.runtime={}
        for db in {c['database_id'] for c in cls.d['cases']}:
            from evaluation.bird.runtime import BirdRuntime
            r=object.__new__(BirdRuntime);r.evidence=cls.e;r.database_id=db;r.domain=cls.e.domain(db);r.tables=cls.e.tables(db)
            r.names=set(r.domain['tables']);r.expected=expectations(cls.e.manifest);r._descriptions,r.description_diagnostic=cls.e.descriptions(db)
            r.catalog=r._catalog({t['name']:cls.e.validation['structure']['verified_structure']['columns'][t['name']] for t in r.tables})
            cls.runtime[db]=r

    def current(self,c):
        p=self.public[c['case_id']];r=self.runtime[c['database_id']]
        graph=c['development_diagnostics']['retrieval']['schema_graph']['value']
        contract=build_contract(r,p,graph,c['retrieval']['intent_selection'],c['canonical_lookup'])
        return r,p,contract

    def test_previous_eleven_correct_queries_not_newly_rejected(self):
        matched={c['case_id'] for c in self.n['cases'] if c['native_comparison']['matches_frozen_gold']}
        self.assertEqual(len(matched),11)
        for c in self.d['cases']:
            if c['case_id'] in matched:
                r,p,contract=self.current(c);self.assertEqual(violations(r,p,contract,c['generated_sql']),[],c['case_id'])

    def test_two_actual_failures_get_specific_public_contract_feedback(self):
        expected={'BIRD-PG-0201':'percentage_output_unit','BIRD-PG-0586':'incomplete_participant_context_output'}
        for c in self.d['cases']:
            if c['case_id'] not in expected:continue
            r,p,contract=self.current(c)
            self.assertIn(expected[c['case_id']],[v['code'] for v in violations(r,p,contract,c['generated_sql'])])

    def test_native_matching_probe_variants_survive_current_constraints(self):
        captures={c['case_id']:c for c in self.d['cases']}
        for c in self.probe['cases']:
            r,p,contract=self.current(captures[c['case_id']])
            for name,comparison in c['native_comparisons'].items():
                if comparison['matches_frozen_gold']:
                    self.assertEqual(violations(r,p,contract,c['queries'][name]),[],c['case_id']+':'+name)

    def test_reference_shape_case_remains_unmodified(self):
        c=next(c for c in self.d['cases'] if c['case_id'].endswith('1399'));r,p,contract=self.current(c)
        self.assertEqual(violations(r,p,contract,c['generated_sql']),[])
        self.assertEqual(contract['participant_output']['required_groups'],[])
        self.assertEqual(contract['output_units']['output_unit'],'unspecified')

    def test_new_helper_is_bound_to_index_identity(self):
        r=self.runtime['toxicology'];r.identity=NS(public=lambda:{'logical_database_id':'toxicology'})
        identity=index_identity(r,NS(public=lambda:{}))
        self.assertIn('units_output.py',identity['code_sha256'])
        self.assertEqual(policy()['policy_id'],'bird_public_intent_candidate_v4')


if __name__=='__main__':unittest.main()
