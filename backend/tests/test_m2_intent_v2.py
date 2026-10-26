"""Real rejected trajectories plus generic negative boundaries for public intent v2."""
from contextlib import nullcontext
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from test_m2_intent_candidate import context,field,documents,public,codes,contract
from evaluation.bird.intent import (sample_conditions,expand_fields,build_contract,bound_public_conditions,policy,literal_requests,checked_tables,violations)
from evaluation.bird.relationships import build_graph,grain_contract
from evaluation.bird.first_sql_audit import first_captures,run_first_audit
from evaluation.bird.native import NativeResult
from evaluation.bird.budgets import BirdFailure
from evaluation.bird.evidence import Evidence,DEFAULT_DATA,public_cases
from scripts.m2_b_common import BASE
from scripts.m2_b_structure import expectations


class ConditionAuthorityTest(unittest.TestCase):
    def test_names_roles_and_arithmetic_numbers_are_not_conditions_or_coverage(self):
        r=context({'items':[field('last_name'),field('type'),field('external_id')]})
        ds=documents(r,{'last_name':[['text','Administrator']],'type':[['text','Budget']],'external_id':[['text','100']]})
        p=public('Administrators and budget','Percentage = quantity *100')
        self.assertEqual(sample_conditions(ds,p),[])
        self.assertEqual(expand_fields(r,ds,[],p)[1]['sample_condition_candidates'],[])

    def test_unique_sme_sample_retains_coverage_but_has_no_filter_authority(self):
        r=context({'customers':[field('currency'),field('segment')]});ds=documents(r,{'segment':[['text','SME']]})
        p=public('How many SMEs use CZK?');chosen,selection=expand_fields(r,ds,[(0,.9)],p)
        self.assertIn('db.customers.segment',selection['added_field_ids'])
        graph={'fields':[{'id':ds[i].doc_id} for i,s in chosen]}
        c=build_contract(r,p,graph,selection,{'matches':[]})
        self.assertEqual(c['required_profile_conditions'],[]);self.assertFalse(c['profile_coverage_hints'][0]['mandatory'])

    def test_explicit_operation_does_not_bind_same_value_in_type(self):
        r=context({'items':[field('operation'),field('type')]});p=public('Cash withdrawals',"operation='VYBER'")
        ds=documents(r,{'operation':[['text','VYBER']],'type':[['text','VYBER']]})
        self.assertEqual(sample_conditions(ds,p),[])
        conditions=bound_public_conditions(r,p,{'db.items.operation','db.items.type'},{'matches':[]})
        self.assertEqual([c['field'] for c in conditions],['operation'])

    def test_ambiguous_owner_or_or_negation_does_not_create_hard_condition(self):
        r=context({'a':[field('status')],'b':[field('status')]});ids={'db.a.status','db.b.status'}
        self.assertEqual(bound_public_conditions(r,public('Values',"status='Open'"),ids,{'matches':[]}),[])
        for evidence in ("a.status='Open' OR b.status='Closed'","not a.status='Open'","example: a.status='Open'"):
            self.assertEqual(bound_public_conditions(r,public('Values',evidence),ids,{'matches':[]}),[])
        self.assertEqual(bound_public_conditions(r,public('Values',"a.status='Open'"),ids,{'matches':[]})[0]['table_id'],'db.a')

    def test_entity_name_probe_respects_the_public_field_mapping(self):
        r=context({'event':[field('event_name')],'member':[field('first_name'),field('last_name')]})
        p=public("Did Maya attend 'Women's Soccer'?","full name refers to first_name, last_name; 'Women's Soccer' is an event_name")
        ids={t['id']+'.'+f['name'] for t in r.catalog.tables for f in t['fields']}
        self.assertEqual([v['field'] for v in literal_requests(p,checked_tables(r),ids)],['event_name'])

    def test_singleton_in_and_case_normalization_are_not_false_missing_filters(self):
        r=context({'items':[field('status')]});p=public('Open items',"status='Open'")
        for sql in ("SELECT status FROM items WHERE status IN ('Open')","SELECT status FROM items WHERE LOWER(status)='open'"):
            self.assertNotIn('missing_population_condition',codes(r,sql,p))


class GrainAndRoleTest(unittest.TestCase):
    def atomic(self):
        key=field('particle_id');key['role']='primary_key';bond=field('edge_id');bond['role']='primary_key'
        return context({'particle':[key,field('group_id'),field('element')],'edge':[bond,field('group_id')]})

    def test_nonunique_join_rejects_row_counts_but_accepts_distinct_entities(self):
        r=self.atomic();p=public('Percentage of unique particles','percentage=DIVIDE(SUM(element=\'c\'),COUNT(particle_id))')
        self.assertEqual(grain_contract(r,p)['primary_key'],'particle_id')
        bad="SELECT CAST(SUM(CASE WHEN p.element='c' THEN 1 ELSE 0 END) AS REAL)*100/COUNT(p.particle_id) FROM particle p JOIN edge e ON p.group_id=e.group_id"
        self.assertIn('entity_grain_fanout',codes(r,bad,p))
        good="SELECT CAST(COUNT(DISTINCT CASE WHEN p.element='c' THEN p.particle_id END) AS REAL)*100/COUNT(DISTINCT p.particle_id) FROM particle p JOIN edge e ON p.group_id=e.group_id"
        self.assertNotIn('entity_grain_fanout',codes(r,good,p))

    def test_no_join_and_semijoin_do_not_force_distinct(self):
        r=self.atomic();p=public('Percentage','COUNT(particle_id)')
        self.assertNotIn('entity_grain_fanout',codes(r,"SELECT CAST(COUNT(particle_id) AS REAL)/COUNT(particle_id) FROM particle",p))
        sql='SELECT CAST(COUNT(p.particle_id) AS REAL)/COUNT(p.particle_id) FROM particle p WHERE EXISTS(SELECT 1 FROM edge e WHERE e.group_id=p.group_id)'
        self.assertNotIn('entity_grain_fanout',codes(r,sql,p))

    def test_many_to_one_unique_target_does_not_trigger_fanout(self):
        r=self.atomic();r.catalog.tables[1]['fields'][1]['role']='primary_key';r.catalog.tables[1]['fields'][0]['role']='field'
        p=public('Percentage','COUNT(particle_id)')
        sql='SELECT CAST(COUNT(p.particle_id) AS REAL)/COUNT(p.particle_id) FROM particle p JOIN edge e ON p.group_id=e.group_id'
        self.assertNotIn('entity_grain_fanout',codes(r,sql,p))

    def test_role_graph_retains_actor_editor_owner_alternatives(self):
        relations=[dict(id='editor',left_table='db.users',left_field='id',right_table='db.posts',right_field='editor_id'),
                   dict(id='owner',left_table='db.users',left_field='id',right_table='db.posts',right_field='owner_id'),
                   dict(id='subject',left_table='db.posts',left_field='id',right_table='db.actions',right_field='post_id'),
                   dict(id='actor',left_table='db.users',left_field='id',right_table='db.actions',right_field='user_id')]
        r=context({'users':[field('id'),field('displayname')],'posts':[field('id'),field('title'),field('editor_id'),field('owner_id')],
                   'actions':[field('post_id'),field('user_id'),field('amount')]},relations)
        docs=documents(r);wanted={'db.users.displayname','db.posts.title','db.actions.amount'}
        hits=[{**d.public(),'score':.9,'source':'retrieval'} for d in docs if d.doc_id in wanted]
        graph=build_graph(r,hits,public('Which user added an amount to the post title?', 'amount=50; user refers to DisplayName; Title includes variance'))
        self.assertEqual({j['id'] for j in graph['joins']},{'editor','owner','subject','actor'})
        self.assertIn('db.actions.user_id',{f['id'] for f in graph['fields']})
        self.assertEqual([v['relation_id'] for v in graph['relation_role_context']['preferred_actor_relations']],['actor'])
        self.assertEqual(graph['relation_role_context']['context_output_groups'][0]['context_label'],'db.posts.title')
        self.assertTrue(graph['relation_role_context']['joins_are_alternatives'])

    def test_numeric_operation_order_alone_does_not_reject_a_real_ratio(self):
        r=context();p=public('Percentage','percentage=COUNT(id)/COUNT(id)*100')
        for sql in ('SELECT CAST(COUNT(id) AS REAL)/COUNT(id)*100 FROM items',
                    'SELECT CAST(COUNT(id) AS REAL)*100/COUNT(id) FROM items'):
            self.assertEqual(codes(r,sql,p),[])
        self.assertIn('percentage_numeric_path',codes(r,'SELECT COUNT(id)/COUNT(id)*100 FROM items',p))
        self.assertEqual(policy()['numeric_policy'],'floating_count_ratio_order_advisory_v3')


class CapturedTrajectoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path('E:/PythonLearn/datasets/bird_mini_dev') if Path('E:/PythonLearn/datasets/bird_mini_dev').exists() else DEFAULT_DATA
        cls.e=Evidence.load(root);cls.source=json.loads((BASE/'evaluation/results/m2_public_intent_diagnostics14_server.json').read_bytes())
        cls.public={p['case_id']:p for p in public_cases('development80')};cls.runtimes={}
        for db in {c['database_id'] for c in cls.source['cases']}:
            r=object.__new__(__import__('evaluation.bird.runtime',fromlist=['BirdRuntime']).BirdRuntime)
            r.evidence=cls.e;r.database_id=db;r.domain=cls.e.domain(db);r.tables=cls.e.tables(db);r.names=set(r.domain['tables']);r.expected=expectations(cls.e.manifest)
            r._descriptions,r.description_diagnostic=cls.e.descriptions(db)
            r.catalog=r._catalog({t['name']:cls.e.validation['structure']['verified_structure']['columns'][t['name']] for t in r.tables})
            identity=next(c['source_identity'] for c in cls.source['cases'] if c['database_id']==db);r.identity=NS(public=lambda identity=identity:identity)
            cls.runtimes[db]=r

    def test_four_real_first_sqls_no_longer_require_invented_filters(self):
        expected={'0036':'Administrator','0159':'VYBER','1405':'Budget','0368':'100'};seen=set()
        for c in self.source['cases']:
            suffix=c['case_id'][-4:]
            if suffix not in expected:continue
            r=self.runtimes[c['database_id']];p=self.public[c['case_id']]
            fields=[{'id':t['id']+'.'+f['name']} for t in r.catalog.tables for f in t['fields']]
            selection={'baseline_field_ids':c['retrieval']['intent_selection']['baseline_field_ids'],'sample_condition_candidates':c['intent_contract']['required_profile_conditions']}
            new=build_contract(r,p,{'fields':fields},selection,c['canonical_lookup'])
            first=next(a['sql']['text'] for a in c['development_diagnostics']['attempts'] if a['kind']=='model_decision')
            issues=violations(r,p,new,first)
            self.assertFalse(any(i['code']=='missing_population_condition' for i in issues),c['case_id'])
            self.assertEqual(issues,[],c['case_id'])
            self.assertNotIn(expected[suffix],[v['value'] for v in new['required_profile_conditions']] if suffix not in ('0159',) else [v['value'] for v in new['required_profile_conditions'] if v['field']=='type'])
            seen.add(suffix)
        self.assertEqual(seen,set(expected))

    def test_real_0201_grain_and_real_0586_voter_relationship(self):
        c=next(c for c in self.source['cases'] if c['case_id'].endswith('0201'));r=self.runtimes[c['database_id']];p=self.public[c['case_id']]
        fields=[{'id':t['id']+'.'+f['name']} for t in r.catalog.tables for f in t['fields']]
        c2=build_contract(r,p,{'fields':fields},{'baseline_field_ids':[f['id'] for f in fields],'sample_condition_candidates':[]},c['canonical_lookup'])
        c2['required_profile_conditions']=[];c2['entity_grain']=grain_contract(r,p)
        self.assertEqual(c2['entity_grain']['primary_key'],'atom_id');self.assertEqual(c2['entity_grain']['enforcement'],'advisory')
        self.assertNotIn('entity_grain_fanout',[i['code'] for i in violations(r,p,c2,c['generated_sql'])])
        c=next(c for c in self.source['cases'] if c['case_id'].endswith('0586'));r=self.runtimes[c['database_id']];p=self.public[c['case_id']]
        hits=[]
        for t in r.catalog.tables:
            for f in t['fields']:
                fid=t['id']+'.'+f['name']
                if fid in c['retrieval']['selected_field_ids']:
                    hits.append(dict(doc_id=fid,table_id=t['id'],field_name=f['name'],field_label=f['label'],field_type=f['type'],database_id=r.database_id,score=.9))
        graph=build_graph(r,hits,p)
        self.assertIn('votes_userid_fkey:userid',{v['id'] for v in graph['joins']})
        self.assertIn('votes_userid_fkey:userid',{v['relation_id'] for v in graph['relation_role_context']['preferred_actor_relations']})

    def test_first_capture_reads_exact_four_public_sqls_not_final_predictions(self):
        source,pairs=first_captures(BASE/'evaluation/results/m2_public_intent_diagnostics14_server.json',BASE/'evaluation/results/m2_public_intent_native14_server.json',self.e)
        self.assertEqual(len(pairs),4)
        for c,g in pairs:
            self.assertNotEqual(c['generated_sql'],c['previous_final_sql']);self.assertIsNone(c['result'])
            self.assertEqual(c['generated_sql'],c['rejected_initial_sql']['text'])

    def test_wrong_hash_never_loads_gold(self):
        with patch('evaluation.bird.first_sql_audit.digest_file',return_value='wrong'),patch('evaluation.bird.first_sql_audit.scorer_gold',side_effect=AssertionError('No Gold before provenance')):
            with self.assertRaises(ValueError):first_captures(None,None,None)

    def run_fake_audit(self,fail_second=False):
        owner=self;calls=[];made=[]
        class Registry:
            def __init__(self,*a):self._runtimes={};made.append(self)
            def get(self,db):
                if db not in self._runtimes:
                    original=owner.runtimes[db]
                    def execute(sql,budget):
                        calls.append(sql)
                        if fail_second and len(calls)==2:raise BirdFailure('sql_timeout')
                        return NativeResult(['id'],[(1,)],32)
                    self._runtimes[db]=NS(database_id=db,domain=original.domain,identity=original.identity,
                        connections=NS(closed=False),receipt=lambda:{'database_id':db},execute_native=execute)
                return self._runtimes[db]
            def close(self):
                for runtime in self._runtimes.values():runtime.connections.closed=True
            def __enter__(self):return self
            def __exit__(self,*a):self.close()
        report={}
        with patch('evaluation.bird.first_sql_audit.hard_deadline',side_effect=lambda *a:nullcontext()):
            if fail_second:
                with self.assertRaises(BirdFailure):
                    run_first_audit(self.e,BASE/'evaluation/results/m2_public_intent_diagnostics14_server.json',BASE/'evaluation/results/m2_public_intent_native14_server.json',None,report,registry_factory=Registry)
            else:run_first_audit(self.e,BASE/'evaluation/results/m2_public_intent_diagnostics14_server.json',BASE/'evaluation/results/m2_public_intent_native14_server.json',None,report,registry_factory=Registry)
        return report,calls,made[0]

    def test_audit_executes_eight_raw_queries_without_semantic_rewrite_or_models(self):
        report,calls,registry=self.run_fake_audit()
        self.assertEqual(len(calls),8);self.assertEqual(report['summary']['sql_execution_count'],8)
        self.assertEqual(report['new_model_request_count'],0);self.assertTrue(report['pools_closed'])
        for c in report['cases']:
            self.assertFalse(c['initial_sql_previously_executed']);self.assertNotIn('captured_native_diagnostic_preserved',c)
            self.assertEqual(c['budget']['sql_tool_calls'],2)
            self.assertNotEqual(c['generated_sql_sha256'],c['previous_final_sql_sha256'])

    def test_audit_failure_preserves_consumed_budget_and_closes_pools(self):
        report,calls,registry=self.run_fake_audit(fail_second=True)
        self.assertEqual(len(calls),2);self.assertEqual(report['cases'][0]['budget']['sql_tool_calls'],2)
        self.assertTrue(report['cases'][0]['gold_execution_attempted']);self.assertTrue(report['pools_closed'])


if __name__=='__main__':unittest.main()
