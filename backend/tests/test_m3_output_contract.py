"""Public output grammar, conservative observations and real Agent-loop parity."""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from evaluation.bird.output_contract import build_contract, observe, observation, policy, MAX_BYTES
from evaluation.bird.budgets import BirdFailure
from evaluation.bird.native import NativeResult
from scripts.m2_b_common import BASE


def public(question, evidence=''):
    return dict(case_id='BIRD-PG-9001',database_id='demo',dialect='postgres',question=question,evidence=evidence)


def graph(extra=()):
    names = [('mailstreet','Mailing street'),('street','Street'),('name','Name'),
             ('district_code','District code'),('numerator','Numerator'),('denominator','Denominator'),
             ('subtypes','Subtypes'),('supertypes','Supertypes'),('phone','Phone'),
             ('first_name','First name'),('last_name','Last name'),('cost','Cost'),('id','ID')]
    fields = [dict(id='demo.items.'+name,table_id='demo.items',table_name='items',name=name,label=label,
                   description=label,type='text',source='retrieval') for name,label in names]
    return dict(database='demo',fields=fields+list(extra),tables=[dict(id='demo.items',name='items')],joins=[])


def codes(value):
    return [v['code'] for v in value['issues']]


class PublicOutputGrammarTest(unittest.TestCase):
    def contract(self,q,e='',g=None,existing=None):
        return build_contract(public(q,e),g or graph(),existing)

    def test_address_then_name_with_public_synonym_and_source_offsets(self):
        p=public("What is the postal street address for the item? Indicate its name.",
                 'Postal street and mailing street are synonyms.')
        c=build_contract(p,graph())
        self.assertEqual(c['items'][0]['field_ids'],['demo.items.mailstreet'])
        # Possessive/pronoun ownership not uniquely parsed: retain the public role.
        self.assertEqual(len(c['items']),2)
        for item in c['items']:
            for s in [item['public_request']]+item['evidence']:
                self.assertEqual(p[s['source']][slice(*s['span'])],s['text'])

    def test_synonym_is_not_invented_from_reference_or_field_similarity(self):
        c=self.contract('What is the postal street address?')
        self.assertFalse(c['items'][0]['binding_complete'])
        self.assertEqual(c['items'][0]['field_ids'],[])

    def test_formula_is_not_lost_when_later_sentence_requests_code(self):
        c=self.contract('What is the rate in the region? List the district code.',
                        'rate = `numerator` / `denominator` * 100')
        self.assertEqual([i['kind'] for i in c['items']],['formula','field'])
        self.assertEqual(c['items'][0]['field_ids'],['demo.items.numerator','demo.items.denominator'])
        self.assertEqual(c['items'][1]['field_ids'],['demo.items.district_code'])

    def test_explicit_group_order_and_filter_mentions_stay_separate(self):
        c=self.contract('Lists all types of items in German.',
                        'German refers to language; all types refer to subtypes, supertypes; subtypes is not null')
        self.assertEqual(c['items'][0]['field_ids'],['demo.items.subtypes','demo.items.supertypes'])
        self.assertEqual(len(c['items']),1)
        self.assertNotIn('German',json.dumps(c['items']))

    def test_group_requires_all_authorized_members_no_full_catalog_expansion(self):
        g=graph();g['fields']=[f for f in g['fields'] if f['name']!='supertypes']
        c=self.contract('List all types.','all types refer to subtypes, supertypes',g)
        self.assertFalse(c['items'][0]['binding_complete'])
        self.assertNotIn('demo.items.supertypes',json.dumps(c))

    def test_conflicting_group_and_formula_definitions_remain_unresolved(self):
        for evidence in ('types refer to subtypes, supertypes; types refer to name, id',
                         'rate = numerator / denominator; rate = denominator / numerator'):
            term='types' if evidence.startswith('types') else 'rate'
            c=self.contract('List '+term+'.',evidence)
            self.assertEqual(c['items'][0]['authority'],'conflicting_public_definitions')
            self.assertFalse(c['items'][0]['binding_complete'])

    def test_ambiguous_unqualified_formula_column_is_not_unique(self):
        other=dict(id='demo.other.id',table_id='demo.other',name='id',label='ID',type='bigint')
        c=self.contract('What is the rate?','rate = COUNT(id) / COUNT(id)',graph([other]))
        self.assertFalse(c['items'][0]['binding_complete'])

    def test_reuse_existing_full_name_group_without_new_field_selection(self):
        existing={'name_groups':[dict(table_id='demo.items',fields=['first_name','last_name'])]}
        c=self.contract('Give the full name and phone of members.',existing=existing)
        self.assertEqual(c['items'][0]['field_ids'],['demo.items.first_name','demo.items.last_name'])
        self.assertEqual(c['items'][0]['authority'],'existing_public_name_group')
        self.assertEqual(c['items'][1]['field_ids'],['demo.items.phone'])

    def test_explicit_only_exclusion_never_adds_excluded_phone(self):
        c=self.contract('List only name, not phone.')
        self.assertEqual([i['field_ids'] for i in c['items']],[['demo.items.name']])
        self.assertIn('explicit_restriction_preserved_in_original_request',c['ambiguities'])

    def test_filter_and_order_attributes_are_not_implicitly_projected(self):
        c=self.contract('List name for items with cost over 10 ordered by cost.')
        self.assertEqual([i['field_ids'] for i in c['items']],[['demo.items.name']])

    def test_multiple_same_named_authorized_fields_are_alternatives(self):
        other=dict(id='demo.other.name',table_id='demo.other',name='name',label='Name',type='text')
        c=self.contract('List name.',g=graph([other]))
        self.assertEqual(c['items'][0]['kind'],'alternatives')
        self.assertFalse(c['parse_complete'])

    def test_rank_boolean_and_unrecognized_frames_never_infer_answer_shape(self):
        for q in ('Rank items by cost.','Did the member attend?','Is the item available?','Compare the data.'):
            self.assertFalse(self.contract(q)['parse_complete'])
            self.assertEqual(self.contract(q)['items'],[])

    def test_no_input_mutation_no_case_id_rules_no_private_input(self):
        p=public('List name.');g=graph();before=deepcopy((p,g))
        a=build_contract(p,g)
        self.assertEqual((p,g),before)
        p['case_id']='BIRD-PG-9999';self.assertEqual(a,build_contract(p,g))
        with self.assertRaises(ValueError):build_contract({**p,'gold_sql':'SECRET'},g)

    def test_foreign_graph_fields_and_identity_rejected(self):
        for change in ('database','field','identity'):
            g=graph()
            if change=='database':g['database']='foreign'
            if change=='field':g['fields'][0]['id']='foreign.items.mailstreet'
            if change=='identity':g['source_identity']={'logical_database_id':'foreign','physical_schema':'public'}
            with self.subTest(change=change),self.assertRaises(ValueError):build_contract(public('List name.'),g)

    def test_bounded_contract_and_no_files_model_or_database_dependencies(self):
        with patch('builtins.open',side_effect=AssertionError('No files allowed')):
            c=self.contract('List name. '*10000)
        self.assertLessEqual(len(json.dumps(c,ensure_ascii=False).encode()),MAX_BYTES)
        self.assertEqual(c['items'],[])
        self.assertIn('input_outside_bounded_grammar',c['ambiguities'])
        self.assertFalse(policy()['hard_rejection']);self.assertEqual(policy()['new_model_calls'],0)


class PassiveObservationTest(unittest.TestCase):
    def setUp(self):
        self.g=graph()
        self.c=build_contract(public('List name and district code.'),self.g)

    def test_aliases_and_quoted_projection_order(self):
        self.assertEqual(codes(observe(self.c,self.g,'SELECT i.name AS n, i.district_code AS code FROM public.items i')),[])
        r=observe(self.c,self.g,'SELECT district_code,name FROM items')
        self.assertIn('requested_output_order_differs',codes(r))

    def test_where_order_and_join_presence_do_not_count_as_output(self):
        r=observe(self.c,self.g,"SELECT name FROM items WHERE district_code='x' ORDER BY district_code")
        self.assertIn('requested_output_not_observed',codes(r))

    def test_observed_alternative_role_can_locate_order_without_choosing_owner(self):
        other=dict(id='demo.other.name',table_id='demo.other',name='name',label='Name',type='text')
        g=graph([other]);c=build_contract(public('List district code and name.'),g)
        self.assertFalse(c['items'][1]['binding_complete'])
        r=observe(c,g,'SELECT name,district_code FROM items')
        self.assertIn('requested_output_order_differs',codes(r))
        self.assertEqual(c['items'][1]['kind'],'alternatives')

    def test_formula_accepts_cast_round_case_and_expression_alias_without_value_claim(self):
        c=build_contract(public('List rate and district code.','rate = `numerator` / `denominator` * 100'),self.g)
        for sql in ('SELECT ROUND(numerator::NUMERIC/NULLIF(denominator,0)*100,5) AS r,district_code FROM items',
                    'SELECT CASE WHEN denominator=0 THEN NULL ELSE numerator/denominator END,district_code FROM items'):
            self.assertEqual(codes(observe(c,self.g,sql)),[])
        self.assertIn('does not establish',observe(c,self.g,sql)['meaning'])

    def test_formula_fields_only_in_filter_or_as_separate_columns_do_not_count(self):
        c=build_contract(public('List rate.','rate = `numerator` / `denominator`'),self.g)
        for sql in ('SELECT name FROM items WHERE numerator/denominator>0','SELECT numerator,denominator FROM items'):
            self.assertIn('requested_output_not_observed',codes(observe(c,self.g,sql)))

    def test_additional_column_is_observation_only_and_sql_is_not_rewritten(self):
        sql='SELECT name,district_code,cost FROM items';before=deepcopy((self.c,self.g,sql))
        r=observe(self.c,self.g,sql)
        self.assertIn('additional_projection_observed',codes(r));self.assertTrue(r['report_only'])
        self.assertNotIn('valid',r);self.assertNotIn('correct',r);self.assertEqual((self.c,self.g,sql),before)

    def test_complex_ownership_and_foreign_sources_remain_inconclusive(self):
        for sql in ('WITH q AS (SELECT name,district_code FROM items) SELECT * FROM q',
                    'SELECT name FROM items UNION SELECT name FROM items',
                    "SELECT name||district_code FROM items",'SELECT * FROM items',
                    'SELECT name,RANK() OVER(ORDER BY cost) FROM items',
                    'SELECT name FROM private.items','SELECT missing FROM items'):
            r=observe(self.c,self.g,sql)
            self.assertEqual(r['status'],'not_evaluated',sql)

    def test_unparseable_sql_and_observer_failure_never_leak_exception_text(self):
        self.assertEqual(observe(self.c,self.g,'SELECT (')['status'],'not_evaluated')
        with patch('evaluation.bird.output_contract.observe',side_effect=RuntimeError('SECRET_PASSWORD')):
            r=observation(self.c,self.g,'SELECT name FROM items')
        self.assertNotIn('SECRET_PASSWORD',json.dumps(r));self.assertEqual(r['status'],'not_evaluated')


class SavedPublicCaptureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture=json.loads((BASE/'evaluation/results/m2_public_intent_v4_development80_server.json').read_bytes())
        cls.inputs={c['case_id']:c for c in map(json.loads,(BASE/'evaluation/cases/bird_mini_dev/m2_pg_v1/inputs/development80.jsonl').read_text(encoding='utf-8').splitlines())}
        cls.regression=set(json.loads((BASE/'evaluation/cases/bird_mini_dev/m3_a_success_regression20.json').read_bytes())['case_ids'])

    def rebuild(self,c):
        g=c['development_diagnostics']['retrieval']['schema_graph']['value']
        return g,build_contract(self.inputs[c['case_id']],g,c['intent_contract'])

    def test_three_public_targets_have_source_bound_ordered_requests(self):
        wanted={'BIRD-PG-0050':('field','alternatives'),'BIRD-PG-0085':('formula','field'),'BIRD-PG-0407':('field_group',)}
        for row in self.capture['cases']:
            if row['case_id'] not in wanted:continue
            g,c=self.rebuild(row)
            self.assertEqual(tuple(i['kind'] for i in c['items']),wanted[row['case_id']])
            self.assertIn('requested_output_not_observed',codes(observe(c,g,row['generated_sql'])))
            self.assertNotIn('gold_sql',json.dumps(c))

    def test_twenty_saved_successes_get_no_fabricated_missing_output_observation(self):
        for row in self.capture['cases']:
            if row['case_id'] not in self.regression:continue
            g,c=self.rebuild(row);r=observe(c,g,row['generated_sql'])
            self.assertEqual(r['issues'],[],row['case_id'])
        # This is passive projection replay, not a new native EX/model evaluation.


class WorkerParityTest(unittest.TestCase):
    def run_worker(self,enabled,decisions,observer_error=False):
        from evaluation.bird import case_worker as worker
        with patch.dict(sys.modules,{'resource':NS()}):
            agent_module=importlib.import_module('evaluation.bird.isolated_agent')
        decisions=deepcopy(decisions);calls=[];prompts=[];g=graph()
        identity=NS(public=lambda:dict(logical_database_id='demo',physical_schema='public'))
        table=dict(id='demo.items',name='items',database='demo',physical_schema='public',fields=[dict(name=f['name'],type=f['type'],label=f['label']) for f in g['fields']])
        class Runtime:
            catalog=NS(tables=[table],relations=[])
            def __init__(self,*a,**kw):self.identity=identity;self.database_id='demo'
            def execute_native(self,sql,budget,**kw):
                calls.append((sql,kw.get('validate_only',False)))
                if 'missing' in sql:raise BirdFailure('undefined_column','42703')
                if kw.get('validate_only'):return {'valid':True}
                return NativeResult(['name'],[('a',)],32)
            def close(self):pass
        class Models:
            def __init__(self,config,budget):self.budget=budget
            def chat(self,system,user):
                self.budget.model_attempt('chat',prompt=(system+user).encode())
                prompts.append(dict(system=system,user=json.loads(user)))
                return decisions.pop(0)
        class Agent:
            isolation={'unit':'fake'}
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def run(self,context,handler,*a):
                with patch.object(agent_module,'rpc',side_effect=lambda op,**msg:handler(op,msg)):
                    return agent_module.answer(context)
        schema=dict(graph=g,retrieval={'selected_field_ids':[f['id'] for f in g['fields']]},index_sha256='unit',_intent_selection={})
        request=dict(mode='diagnostic',input=public('List name and district code.'),code_sha256='unit',data_root='unused',results_dir='unused',credentials_file='unused',receipt={},index_path='unused',model_config_private={'api_key':'SECRET_KEY'},intent_candidate_enabled=True)
        if enabled:request['output_contract_enabled']=True
        with patch.multiple(worker,code_binding=Mock(return_value={'sha256':'unit'}),BirdRuntime=Runtime,IsolatedAgent=Agent,load_credentials=Mock(return_value={'passwords':{'ro':'SECRET_PASSWORD'}})):
            with patch.object(worker.Evidence,'load',return_value=NS(domain=lambda db:{'query_role':'ro'},manifest={},validation={'initialization_id':'unit'})):
                with patch('evaluation.bird.model.Models',Models),patch('evaluation.bird.retrieval.retrieve',return_value=deepcopy(schema)):
                    with patch('evaluation.bird.intent.canonical_lookup',return_value={'matches':[]}),patch('evaluation.bird.intent.build_contract',return_value={'remaining_sql_execution_rounds':3}),patch('evaluation.bird.intent.violations',return_value=[]):
                        if observer_error:
                            with patch('evaluation.bird.output_contract.observe',side_effect=RuntimeError('SECRET')):r=worker.execute(request)
                        else:r=worker.execute(request)
        return r,calls,prompts

    def test_missing_output_is_report_only_same_sql_calls_and_budget(self):
        sql='SELECT name FROM items';decisions=[dict(action='query',sql=sql)]
        old,oldcalls,oldprompts=self.run_worker(False,decisions)
        new,newcalls,newprompts=self.run_worker(True,decisions)
        self.assertEqual(old['status'],new['status']);self.assertEqual(new['status'],'diagnostic_answered')
        self.assertEqual(new['generated_sql'],sql);self.assertEqual(oldcalls,newcalls)
        for key in ('model_http_attempts','chat_http_attempts','sql_tool_calls','validation_attempts','generation_attempts'):
            self.assertEqual(old['budget'][key],new['budget'][key],key)
        self.assertIn('requested_output_not_observed',codes(new['output_contract_observations'][0]['diagnostic']))
        self.assertEqual(new['output_contract_observations'][0]['sql_sha256'],hashlib.sha256(sql.encode()).hexdigest())
        self.assertNotIn('public_output_contract',old)
        prompt=deepcopy(newprompts[0]);prompt['user']['schema'].pop('public_output_contract')
        self.assertEqual(prompt,oldprompts[0])
        self.assertNotIn('SECRET_PASSWORD',json.dumps(new['public_output_contract']))

    def test_existing_repair_loop_and_feedback_remain_unchanged(self):
        decisions=[dict(action='query',sql='SELECT missing FROM items'),dict(action='query',sql='SELECT name FROM items')]
        old,oldcalls,oldprompts=self.run_worker(False,decisions)
        new,newcalls,newprompts=self.run_worker(True,decisions)
        self.assertEqual(new['status'],'diagnostic_answered');self.assertEqual(oldcalls,newcalls)
        self.assertEqual(new['budget']['generation_attempts'],{1:2})
        self.assertEqual(new['budget']['sql_tool_calls'],1)
        self.assertEqual(newprompts[1]['user']['validation_error'],oldprompts[1]['user']['validation_error'])
        self.assertEqual(len(new['output_contract_observations']),2)

    def test_clarification_and_observer_failure_do_not_create_retry(self):
        r,calls,_=self.run_worker(True,[dict(action='clarify',reason='Missing role')])
        self.assertEqual(r['status'],'clarification');self.assertEqual(calls,[]);self.assertEqual(r['output_contract_observations'],[])
        r,calls,_=self.run_worker(True,[dict(action='query',sql='SELECT name FROM items')],observer_error=True)
        self.assertEqual(r['status'],'diagnostic_answered');self.assertEqual(r['budget']['chat_http_attempts'],1)
        self.assertEqual(r['output_contract_observations'][0]['diagnostic']['status'],'not_evaluated')

    def test_development_only_and_invalid_flags_fail_before_credentials(self):
        from evaluation.bird import case_worker as worker
        for mode,intent,flag in [('live',True,True),('gold',True,True),('diagnostic',False,True),('diagnostic',True,'true')]:
            p=public('List name.')
            request=dict(mode=mode,input=p,gold={**p,'gold_sql_sha256':'unit'},code_sha256='unit',intent_candidate_enabled=intent,output_contract_enabled=flag)
            with patch.object(worker,'code_binding',return_value={'sha256':'unit'}),patch.object(worker,'load_credentials') as credentials:
                r=worker.execute(request)
            self.assertFalse(r['complete']);credentials.assert_not_called()
        request=dict(mode='diagnostic',input=public('List name.'),code_sha256='unit',
                     semantic_planning_enabled=True)
        with patch.object(worker,'code_binding',return_value={'sha256':'unit'}),patch.object(worker,'load_credentials') as credentials:
            r=worker.execute(request)
        self.assertFalse(r['complete']);self.assertEqual(r['errors'][0]['category'],
            'query_semantic_planning_development_only_requires_intent');credentials.assert_not_called()

    def test_cli_requires_intent_before_outputs_or_reading_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'not_created.json'
            result=subprocess.run([sys.executable,'-m','evaluation.bird.diagnostic_runner','--output-contract','--output',str(target)],cwd=BASE,capture_output=True,text=True)
            self.assertEqual(result.returncode,2,result.stderr)
            self.assertIn('--output-contract requires --intent-candidate',result.stderr)
            self.assertFalse(target.exists())
            result=subprocess.run([sys.executable,'-m','evaluation.bird.diagnostic_runner','--semantic-planning','--output',str(target)],cwd=BASE,capture_output=True,text=True)
            self.assertEqual(result.returncode,2,result.stderr)
            self.assertIn('--semantic-planning requires --intent-candidate',result.stderr)
            self.assertFalse(target.exists())

    def test_new_code_cannot_be_refrozen_as_original_m2_candidate(self):
        from scripts import m2_holdout_control as control
        with tempfile.TemporaryDirectory() as tmp,patch.object(control,'LEDGER_ROOT',Path(tmp)/'empty'):
            with self.assertRaisesRegex(ValueError,'Candidate execution bytes changed'):
                control.build_candidate()


if __name__=='__main__':unittest.main()
