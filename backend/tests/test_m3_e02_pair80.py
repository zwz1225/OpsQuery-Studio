"""Offline contract checks for the final development80 same-round pair."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from scripts import m3_e02_pair80_common as common
from scripts import run_m3_e02_pair80 as driver
from scripts import prepare_m3_e02_pair80 as prepare_module
from scripts.build_m3_e02_pair80_bundle import OUT,OLD,TRANSPORT,BACKEND


class Pair80Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload=common.bundle(OUT)['payload']

    def test_frozen_semantic_provenance_and_exact_development_split(self):
        p=self.payload
        self.assertEqual(len(p['case_ids']),80)
        self.assertEqual(len(p['historical_success50_ids']),50)
        self.assertEqual(len(p['regression_ids']),20)
        self.assertTrue(set(p['regression_ids'])<=set(p['historical_success50_ids']))
        self.assertEqual(len(p['sides']['baseline']['code_files']),97)
        self.assertEqual(len(p['sides']['candidate']['code_files']),99)
        self.assertEqual(p['maximum_generated_cases'],160)
        self.assertFalse(p['automatic_holdout'])
        self.assertEqual(p['source_bundles']['m2_v4'],common.read(OLD/'bundle_manifest.json')['bundle_id'])
        self.assertEqual(p['source_bundles']['shared_transport'],common.read(TRANSPORT/'bundle_manifest.json')['bundle_id'])

    def test_common_transport_and_e02_only_semantic_delta(self):
        p=self.payload;before=p['sides']['baseline']['code_files'];after=p['sides']['candidate']['code_files']
        self.assertEqual({name for name in before if before[name]!=after[name]},
            {'evaluation/bird/intent.py','evaluation/bird/retrieval.py',
             'evaluation/bird/case_worker.py','evaluation/bird/diagnostic_runner.py'})
        self.assertEqual(set(after)-set(before),
            {'evaluation/bird/demand_relations.py','evaluation/bird/reviewed_relations.py'})
        for name in ('evaluation/bird/model.py','evaluation/bird/process_dns.py'):
            self.assertEqual(before[name],after[name])
        self.assertNotIn('evaluation/bird/output_contract.py',after)
        old=common.read(OLD/'bundle_manifest.json')['payload']['sides']['baseline']['code_files']
        self.assertEqual(before['evaluation/bird/case_worker.py'],old['evaluation/bird/case_worker.py'])
        self.assertEqual(before['evaluation/bird/intent.py'],old['evaluation/bird/intent.py'])
        candidate=common.read(TRANSPORT/'bundle_manifest.json')['payload']['sides']['baseline']['code_files']
        for name in ('evaluation/bird/model.py','evaluation/bird/process_dns.py',
                     'evaluation/bird/retrieval.py','evaluation/bird/diagnostic_runner.py'):
            self.assertEqual(after[name],candidate[name])

    def test_generation_uses_fixed_flags_and_separate_indexes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);row={'data_root':'/data','credentials_file':'/private/roles',
                                'model_config_file':'/private/model'}
            left=driver._generation_options(row,root,'baseline')
            right=driver._generation_options(row,root,'candidate')
        for options in (left,right):
            self.assertIn('--schema-coverage',options)
            self.assertIn('--intent-candidate',options)
            self.assertNotIn('--output-contract',options)
            self.assertNotIn('--relation-output',options)
            self.assertEqual(Path(options[options.index('--case-list')+1]).as_posix().split('/backend/',1)[1],
                             common.CASE_LIST)
        self.assertNotIn('--condition-relations',left)
        self.assertIn('--condition-relations',right)
        self.assertNotEqual(left[left.index('--index-root')+1],right[right.index('--index-root')+1])

    def test_prepare_exact_sides_without_reading_private_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=root/'data';data.mkdir()
            model=root/'model';model.write_text('SECRET_MODEL')
            roles=root/'roles';roles.write_text('SECRET_ROLES')
            workspace=root/'workspace'
            args=SimpleNamespace(bundle_root=OUT,source_backend=BACKEND,workspace=workspace,
                data_root=data,model_config_file=model,credentials_file=roles)
            with patch.object(prepare_module.shutil,'disk_usage',return_value=SimpleNamespace(free=3*1024**3)):
                result=prepare_module.prepare(args)
            row,payload=common.workspace(workspace)
            self.assertEqual(result['run_status'],'complete')
            self.assertFalse(result['secrets_read'])
            self.assertFalse(result['secrets_copied'])
            self.assertFalse((workspace/'baseline/backend/.env').exists())
            self.assertNotIn('SECRET_',json.dumps(row))
            self.assertEqual(payload['case_ids'],self.payload['case_ids'])
            with self.assertRaises(common.PairError):prepare_module.prepare(args)

    def _synthetic(self,baseline_ids,candidate_ids,chat_scale=1.1):
        p=self.payload;captures={};natives={}
        shared=dict(model_configuration=p['model_configuration'],source_binding=p['source_binding'],
            schema_selection_policy=p['schema_selection_policy'],sql_repair_policy=p['sql_repair_policy'],
            intent_candidate_policy=p['intent_candidate_policy'],case_list_sha256='same-case-list',
            transport_policy=p['transport_policy'],transport_dependency_binding={'binary':'same'})
        for side,answered in (('baseline',baseline_ids),('candidate',candidate_ids)):
            events=[{'kind':'chat','usage':{'total_tokens':110 if side=='candidate' and chat_scale==1.1 else 100}}]
            cases=[]
            for cid in p['case_ids']:
                cases.append(dict(case_id=cid,database_id='db',source_identity={'id':'same'},query_role='readonly',
                    status='complete' if cid in answered else 'no_answer',case_wall_seconds=10,
                    generated_sql='SELECT 1' if cid in answered else None,
                    budget={'model_http_attempts':1,'model_events':events},
                    development_diagnostics={'retrieval':{'schema_graph':{'value':{'fields':[],'joins':[]}}}}))
            indexes=[dict(identity={'source_identity':{'logical_database_id':str(i)}},
                          path=f'/isolated/{side}/{i}/index.json',cache_hit=False,
                          model_usage={'model_http_attempts':0,'model_events':[]}) for i in range(8)]
            captures[side]=dict(shared,selected_case_ids=p['case_ids'],cases=cases,index_builds=indexes)
            natives[side]={'cases':[{'case_id':cid,'native_comparison':{'matches_frozen_gold':True}}
                                    for cid in p['case_ids'] if cid in answered]}
        return captures,natives

    def test_nonanswers_stay_in_80_denominator_and_historical_regression_blocks(self):
        p=self.payload;history=set(p['historical_success50_ids']);other=[cid for cid in p['case_ids'] if cid not in history]
        baseline=set(history);candidate=(history-{p['historical_success50_ids'][0]})|set(other[:2])
        captures,natives=self._synthetic(baseline,candidate)
        result=common.compare_pair(p,captures,natives)
        self.assertEqual((result['case_count'],result['baseline_match_count'],result['candidate_match_count']),
                         (80,50,51))
        self.assertEqual(len(result['historical_success50_regressed_ids']),1)
        self.assertFalse(result['automatic_screen_pass'])
        self.assertFalse(result['screening']['historical_success50_retained'])
        self.assertEqual(len(result['cases']),80)

    def test_complete_gain_with_retained_50_and_known_cost_is_screened(self):
        p=self.payload;history=set(p['historical_success50_ids']);new=next(cid for cid in p['case_ids'] if cid not in history)
        captures,natives=self._synthetic(history,history|{new})
        result=common.compare_pair(p,captures,natives)
        self.assertEqual(result['candidate_match_count'],51)
        self.assertEqual(result['historical_success50_retained_count'],50)
        self.assertEqual(result['regression20_retained_count'],20)
        self.assertTrue(result['automatic_screen_pass'])
        self.assertEqual(result['acceptance'],'manual_semantic_review_required')

    def test_unknown_model_usage_cannot_pass_cost_screen(self):
        p=self.payload;history=set(p['historical_success50_ids']);new=next(cid for cid in p['case_ids'] if cid not in history)
        captures,natives=self._synthetic(history,history|{new})
        captures['candidate']['cases'][0]['budget']['model_events'][0]['usage']=None
        result=common.compare_pair(p,captures,natives)
        self.assertIsNone(result['chat_tokens']['candidate'])
        self.assertFalse(result['screening']['cost_known'])
        self.assertFalse(result['automatic_screen_pass'])

    def test_nonanswer_without_per_case_source_metadata_is_counted(self):
        p=self.payload;history=set(p['historical_success50_ids'])
        captures,natives=self._synthetic(history,history)
        missed=next(cid for cid in p['case_ids'] if cid not in history)
        for side in ('baseline','candidate'):
            row=next(v for v in captures[side]['cases'] if v['case_id']==missed)
            row.pop('source_identity');row.pop('query_role')
        result=common.compare_pair(p,captures,natives)
        self.assertEqual(result['fixed_denominator'],80)
        self.assertEqual((result['baseline_match_count'],result['candidate_match_count']),(50,50))
        self.assertFalse(result['automatic_screen_pass'])


if __name__=='__main__':unittest.main()
