from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from types import SimpleNamespace

from scripts.m3_e07_pair24_common import aggregation_shape,bundle,compare_pair
from scripts.prepare_m3_e07_pair24 import prepare

ROOT=Path(__file__).resolve().parents[1]
DELIVERY=ROOT/'.downloads/m3_categorical_population_pair24_v1_20261025_r10'


class CategoricalPopulationPair24Test(unittest.TestCase):
    def test_frozen_pair_has_exact_selection_and_identical_code(self):
        payload=bundle(DELIVERY)['payload']
        self.assertEqual(payload['case_ids'][:4],[
            'BIRD-PG-1480','BIRD-PG-0050','BIRD-PG-0173','BIRD-PG-0459'])
        self.assertEqual(len(payload['case_ids']),24)
        self.assertEqual(len(payload['regression_ids']),20)
        self.assertEqual(payload['sides']['baseline']['code_files'],
                         payload['sides']['candidate']['code_files'])
        from evaluation.bird.intent import policy as intent_policy,query_semantics_policy
        self.assertEqual(payload['intent_policies']['baseline'],intent_policy())
        self.assertEqual(payload['intent_policies']['candidate'],intent_policy())
        self.assertFalse(payload['baseline_reuse_allowed'])
        self.assertEqual(payload['semantic_planning_policies'],
            {'baseline':None,'candidate':query_semantics_policy()})
        self.assertEqual(payload['generation_features'],{'baseline':['--categorical-population'],
            'candidate':['--categorical-population','--semantic-planning']})
        self.assertEqual(len(payload['sides']['baseline']['code_files']),103)
        archive=ROOT.parent/'m3_categorical_population_pair24_v1_20261025_r10.zip'
        with zipfile.ZipFile(archive) as zipped:
            self.assertIsNone(zipped.testzip())
        driver=(DELIVERY/'control/run_m3_e07_pair24.py').read_text(encoding='utf-8')
        self.assertIn("options.append('--categorical-population')",driver)
        self.assertIn("if side=='candidate':options.append('--semantic-planning')",driver)
        self.assertIn('requires a fresh same-round baseline and candidate',driver)

    def test_prepare_keeps_private_inputs_out_of_both_sides(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'evaluation/results') as temporary:
            parent=Path(temporary);source=parent/'source';data=parent/'data';private=parent/'private'
            for path in (source,data,private):path.mkdir()
            model=private/'.env';credentials=private/'credentials.json'
            model.write_text('placeholder',encoding='utf-8');credentials.write_text('placeholder',encoding='utf-8')
            workspace=parent/'workspace'
            result=prepare(SimpleNamespace(bundle_root=DELIVERY,source_backend=source,workspace=workspace,
                data_root=data,model_config_file=model,credentials_file=credentials))
            self.assertEqual(result['run_status'],'complete')
            self.assertTrue((workspace/'candidate/backend/evaluation/bird/demand_relations.py').is_file())
            self.assertFalse((workspace/'candidate/backend/.env').exists())
            self.assertFalse((workspace/'baseline/backend/.local/share/askdata/m2_bird_credentials.json').exists())

    def test_prepare_cli_uses_bundle_policy_without_project_import_or_pythonpath(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'evaluation/results') as temporary:
            parent=Path(temporary).resolve();source=parent/'source';data=parent/'data'
            source.mkdir();data.mkdir();model=parent/'.env';credentials=parent/'credentials.json'
            model.write_text('placeholder',encoding='utf-8');credentials.write_text('{}',encoding='utf-8')
            workspace=parent/'workspace';env=dict(os.environ,PYTHONPATH=str(parent/'missing'))
            result=subprocess.run([sys.executable,'-E','-s',str(DELIVERY/'control/prepare_m3_e07_pair24.py'),
                '--bundle-root',str(DELIVERY),'--source-backend',str(source),'--workspace',str(workspace),
                '--data-root',str(data),'--model-config-file',str(model),'--credentials-file',str(credentials)],
                cwd=parent,env=env,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            report=json.loads((workspace/'preparation.json').read_bytes())
            self.assertEqual(report['run_status'],'complete')
            self.assertEqual(report['new_model_request_count'],0)
            self.assertFalse(report['postgresql_connected'])

    def test_grouped_sum_diagnostic_catches_native_matching_wrong_shape(self):
        row_rank="SELECT SUBSTRING(date FROM 5 FOR 2) FROM usage ORDER BY consumption DESC NULLS LAST LIMIT 1"
        population="SELECT SUBSTRING(date FROM 5 FOR 2) FROM usage GROUP BY SUBSTRING(date FROM 5 FOR 2) ORDER BY SUM(consumption) DESC NULLS LAST LIMIT 1"
        average="SELECT month FROM usage GROUP BY month ORDER BY AVG(consumption) DESC NULLS LAST LIMIT 1"
        self.assertEqual(aggregation_shape(row_rank),dict(parseable=True,group_by_present=False,sum_present=False))
        self.assertEqual(aggregation_shape(population),dict(parseable=True,group_by_present=True,sum_present=True))
        self.assertEqual(aggregation_shape(average),dict(parseable=True,group_by_present=True,sum_present=False))

    def test_comparison_reports_target_context_and_regression_without_conflating_formal_ex(self):
        payload=bundle(DELIVERY)['payload'];ids=payload['case_ids'];source={'source_id':'same-live-source'}
        captures={};natives={}
        from evaluation.bird.demand_relations import policy
        for side in ('baseline','candidate'):
            candidate=side=='candidate';cases=[]
            for cid in ids:
                fields=[];joins=[];conditions=[]
                if cid=='BIRD-PG-1480':
                    fields=[{'id':'debit_card_specializing.customers.customerid'},
                            {'id':'debit_card_specializing.customers.segment'}]
                    joins=[{'relation_type':'reviewed_candidate','declared_foreign_key':False,
                            'join_type':None,'mandatory':False}]
                    conditions=[{'role':'public_categorical_population_condition',
                        'field_id':'debit_card_specializing.customers.segment','value':'SME','mandatory':False}]
                cases.append({'case_id':cid,'database_id':'debit_card_specializing' if cid=='BIRD-PG-1480' else 'financial',
                    'source_identity':source,'query_role':'readonly','status':'complete','generated_sql':
                    "SELECT ... WHERE segment = 'SME'" if cid=='BIRD-PG-1480' and candidate else 'SELECT 1',
                    'development_diagnostics':{'retrieval':{'schema_graph':{'value':{
                        'fields':fields,'joins':joins,'condition_relation_context':{
                            'admitted_public_conditions':conditions}}}}},
                    'budget':{'model_events':[{'kind':'chat','usage':{'total_tokens':10}}],
                              'model_http_attempts':1},'case_wall_seconds':1.0})
            index_builds=[{'identity':{'source_identity':{'logical_database_id':db}},
                'path':f'/{side}/{db}/schema_index.json','model_usage':{'model_events':[],
                    'model_http_attempts':1}} for db in payload['index_database_ids']]
            semantic_policy=payload['semantic_planning_policies'][side]
            for case in cases:
                case['query_semantic_planning_policy']=semantic_policy
                if candidate:case['intent_contract']={'query_semantic_planning_policy':semantic_policy,
                    'query_semantic_planning_guidance':['aggregate at requested grain','preserve requested output order']}
            captures[side]={'model_configuration':{},'source_binding':{},'schema_selection_policy':{},
                'sql_repair_policy':{},'case_list_sha256':'same','transport_policy':{},
                'transport_dependency_binding':{},'condition_relation_policy':policy(categorical_population=True),
                'query_semantic_planning_policy':semantic_policy,
                'intent_candidate_policy':payload['intent_policies'][side],'selected_case_ids':ids,
                'cases':cases,'index_builds':index_builds}
            natives[side]={'cases':[{'case_id':cid,'native_comparison':{'matches_frozen_gold':
                ((cid in payload['regression_ids'])
                 or (cid=='BIRD-PG-1480' and candidate)
                 or (cid=='BIRD-PG-0459' and not candidate))}} for cid in ids]}
        report=compare_pair(payload,captures,natives)
        self.assertEqual(report['case_count'],24)
        self.assertEqual(report['regression20_retained_count'],20)
        self.assertTrue(report['screening']['target_1480_authorized_context_available_both_sides'])
        self.assertTrue(report['screening']['semantic_treatment_isolated'])
        self.assertTrue(report['screening']['target_1480_sql_mentions_category_field'])
        self.assertTrue(report['screening']['target_1480_native_correct'])
        self.assertIn('BIRD-PG-0459',report['right_to_wrong'])
        self.assertFalse(report['screening']['no_observed_control_regression'])
        self.assertFalse(report['automatic_screen_pass'])
        self.assertFalse(report['formal_benchmark'])
        self.assertFalse(report['holdout_run'])
        # A native match alone must not pass the population-period shape gate.
        next(v for v in natives['candidate']['cases'] if v['case_id']=='BIRD-PG-0459')['native_comparison']['matches_frozen_gold']=True
        target=next(v for v in captures['candidate']['cases'] if v['case_id']=='BIRD-PG-1480')
        target['generated_sql']="SELECT month FROM usage WHERE segment='SME' ORDER BY consumption DESC NULLS LAST LIMIT 1"
        ungrouped=compare_pair(payload,captures,natives)
        self.assertTrue(ungrouped['screening']['target_1480_native_correct'])
        self.assertTrue(ungrouped['screening']['no_observed_control_regression'])
        self.assertFalse(ungrouped['screening']['target_1480_group_and_sum_present'])
        self.assertFalse(ungrouped['automatic_screen_pass'])
        target['generated_sql']="SELECT month FROM usage WHERE segment='SME' GROUP BY month ORDER BY SUM(consumption) DESC NULLS LAST LIMIT 1"
        grouped=compare_pair(payload,captures,natives)
        self.assertTrue(grouped['screening']['target_1480_group_and_sum_present'])
        self.assertTrue(grouped['automatic_screen_pass'])
        self.assertEqual(grouped['acceptance'],'manual_semantic_review_required')


if __name__=='__main__':unittest.main()
