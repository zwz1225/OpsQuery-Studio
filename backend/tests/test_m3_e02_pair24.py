"""Offline controls for the E02 paired experiment; never contact models or PostgreSQL."""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend/scripts'))
import m3_e02_pair_common as common
import run_m3_e02_pair24 as runner
import prepare_m3_e02_pair24 as preparer

BUNDLE=ROOT/'backend/.downloads/m3_e02_pair24_bundle_20261022_v5'

def reports():
    manifest=common.bundle(BUNDLE)['payload']
    ids=manifest['case_ids']; regression=set(manifest['regression_ids'])
    captures={}; natives={}
    for side in common.SIDES:
        cases=[]; answers=[]
        for case_id in ids:
            graph={'fields':[{'id':'t.f'}], 'joins':[]}
            if side=='candidate' and case_id=='BIRD-PG-1479':
                graph={'fields':[{'id':'customers.currency'},{'id':'yearmonth.customerid'}],
                       'joins':[{'id':'reviewed_customer_month_key'}]}
            cases.append(dict(case_id=case_id,database_id='debit_card_specializing',
                source_identity={'data_version':'same','catalog_version':'same'},
                query_role='read',status='complete',generated_sql='SELECT 1',case_wall_seconds=1.0,
                development_diagnostics={'retrieval':{'schema_graph':{'value':graph}}},
                budget={'model_http_attempts':1,'model_events':[{'kind':'chat','usage':{'total_tokens':10}}]}))
            correct=case_id in regression or (side=='candidate' and case_id=='BIRD-PG-1479')
            answers.append(dict(case_id=case_id,native_comparison={'matches_frozen_gold':correct}))
        indexes=[]
        for n in range(8):
            indexes.append(dict(identity={'source_identity':{'logical_database_id':f'domain{n}',
                'data_version':'same','catalog_version':'same'},
                'producer_code_sha256':side},sha256=side+str(n),path=f'/isolated/{side}/domain{n}/index.json',
                model_usage={'model_http_attempts':1,'model_events':[{'kind':'embedding','usage':{'total_tokens':10}}]}))
        captures[side]=dict(model_configuration={'chat_model':'same'},source_binding={'data_version':'same'},
            schema_selection_policy={'enabled':True},sql_repair_policy={'budget':3},intent_candidate_policy={'enabled':True},
            case_list_sha256='fixed',selected_case_ids=ids,cases=cases,index_builds=indexes)
        natives[side]=dict(cases=answers)
    return manifest,captures,natives

class E02BundleTest(unittest.TestCase):
    def test_bundle_freezes_24_case_selection_and_expected_code_delta(self):
        payload=common.bundle(BUNDLE)['payload']
        self.assertEqual(len(payload['case_ids']),24)
        self.assertEqual(payload['primary_ids'],['BIRD-PG-1479'])
        self.assertEqual(payload['observed_ids'],['BIRD-PG-0407'])
        self.assertEqual(len(payload['regression_ids']),20)
        self.assertEqual(len(payload['sides']['baseline']['code_files']),96)
        self.assertEqual(len(payload['sides']['candidate']['code_files']),98)

    def test_generation_modes_change_only_by_condition_relations(self):
        payload,_,_=reports()
        row=dict(data_root='/data',credentials_file='/private/credentials',model_config_file='/private/env')
        baseline=runner._generation_options(row,Path('/work'),'baseline')
        candidate=runner._generation_options(row,Path('/work'),'candidate')
        self.assertIn('--schema-coverage',baseline);self.assertIn('--intent-candidate',baseline)
        self.assertNotIn('--condition-relations',baseline);self.assertNotIn('--output-contract',baseline)
        self.assertIn('--condition-relations',candidate);self.assertNotIn('--output-contract',candidate)
        baseline_flags={v for v in baseline if isinstance(v,str) and v.startswith('--')}
        candidate_flags={v for v in candidate if isinstance(v,str) and v.startswith('--')}
        self.assertEqual(candidate_flags-baseline_flags,{'--condition-relations'})

    def test_prepare_materializes_separate_hash_verified_producers_without_copying_secrets(self):
        with tempfile.TemporaryDirectory(prefix='.m3e02_prepare_test_',dir=ROOT) as temp:
            root=Path(temp);data=root/'data';data.mkdir();model=root/'model.env';model.write_text('dummy')
            credentials=root/'credentials.json';credentials.write_text('{"dummy":true}')
            workspace=root/'workspace'
            args=preparer.parser().parse_args(['--bundle-root',str(BUNDLE),'--source-backend',str(ROOT/'backend'),
                '--workspace',str(workspace),'--data-root',str(data),'--model-config-file',str(model),
                '--credentials-file',str(credentials)])
            with patch.object(preparer.shutil,'disk_usage',return_value=type('Usage',(),{'free':3*1024**3})()):
                report=preparer.prepare(args)
            self.assertEqual(report['run_status'],'complete')
            self.assertFalse(report['secrets_copied']);self.assertFalse(report['secrets_read'])
            self.assertEqual(common.workspace(workspace)[1]['case_ids'],common.bundle(BUNDLE)['payload']['case_ids'])
            self.assertFalse((workspace/'baseline/backend/.env').exists())
            self.assertFalse((workspace/'candidate/backend/.local/share/askdata/m2_bird_credentials.json').exists())

    def test_comparison_accepts_independent_index_identity_and_gates_e02_target(self):
        payload,captures,natives=reports()
        result=common.compare_pair(payload,captures,natives)
        self.assertEqual(result['net_gain'],1)
        self.assertTrue(result['screening']['currency_target_native_correct'])
        self.assertTrue(result['screening']['candidate_schema_changed_on_target'])
        self.assertTrue(result['screening']['twenty_successes_retained'])
        self.assertTrue(result['automatic_screen_pass'])
        self.assertEqual(len(result['schema_context_changed_case_ids']),1)

    def test_shared_index_path_or_source_drift_is_rejected(self):
        payload,captures,natives=reports()
        captures['candidate']['index_builds'][0]['path']=captures['baseline']['index_builds'][0]['path']
        with self.assertRaisesRegex(common.PairError,'not isolated'):
            common.compare_pair(payload,captures,natives)
        _,captures,natives=reports()
        captures['candidate']['index_builds'][0]['identity']['source_identity']['data_version']='different'
        with self.assertRaisesRegex(common.PairError,'source identity'):
            common.compare_pair(payload,captures,natives)

    def test_regression_loss_unknown_usage_and_no_answer_fail_screen(self):
        payload,captures,natives=reports()
        natives['candidate']['cases'][0]['native_comparison']['matches_frozen_gold']=False
        result=common.compare_pair(payload,captures,natives)
        self.assertFalse(result['screening']['twenty_successes_retained'])
        _,captures,natives=reports()
        captures['candidate']['cases'][0]['budget']['model_events'][0]['usage']=None
        result=common.compare_pair(payload,captures,natives)
        self.assertIsNone(result['total_model_tokens_including_index_builds']['candidate'])
        self.assertFalse(result['screening']['cost_known'])

if __name__=='__main__':unittest.main()
