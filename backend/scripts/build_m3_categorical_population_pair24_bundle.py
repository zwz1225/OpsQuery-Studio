"""Freeze an isolated baseline/candidate server bundle for categorical-population context."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[2]
BACKEND=ROOT/'backend'
SOURCE=BACKEND/'.downloads/m3_e06_pair24_endpoint_feedback_v2_20261024'
NAME='m3_categorical_population_pair24_v1_20261025_r10'
OUT=BACKEND/'.downloads'/NAME
ZIP=ROOT/(NAME+'.zip')
CASE_LIST='evaluation/cases/bird_mini_dev/m3_categorical_population_pair24.json'
REGRESSION='evaluation/cases/bird_mini_dev/m3_a_success_regression20.json'
CONTROL_FILES=('m3_e07_pair24_common.py','m3_e07_pair24_side.py',
    'prepare_m3_e07_pair24.py','run_m3_e07_pair24.py')
PRIMARY=['BIRD-PG-1480']
OBSERVED=['BIRD-PG-0050','BIRD-PG-0173','BIRD-PG-0459']


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,
        separators=(',',':'),allow_nan=False).encode()).hexdigest()

def code_paths():
    paths=list((BACKEND/'evaluation/bird').glob('*.py'))
    paths += [BACKEND/'evaluation/bird_protocol.py',BACKEND/'evaluation/run_bird_benchmark.py',
        BACKEND/'scripts/check_m2_c_bird_runtime.py']
    paths += [BACKEND/'scripts'/name for name in
        ('m2_b_common.py','m2_b_dump.py','m2_b_structure.py','m2_b_target.py','m2_b_typed_rows.py')]
    paths += list((BACKEND/'app').rglob('*.py'))
    return {p.relative_to(BACKEND).as_posix():p for p in paths}

def main():
    if OUT.exists() or ZIP.exists() or Path(str(ZIP)+'.sha256').exists():
        raise SystemExit('Preserve prior delivery; select a new bundle version')
    from scripts.m3_e06_pair24_common import bundle as old_bundle
    from evaluation.bird.demand_relations import policy
    from evaluation.bird.intent import policy as intent_policy
    from evaluation.bird.intent import query_semantics_policy
    old=old_bundle(SOURCE)['payload']
    selected=json.loads((BACKEND/CASE_LIST).read_bytes())['case_ids']
    regression=json.loads((BACKEND/REGRESSION).read_bytes())['case_ids']
    if len(selected)!=24 or len(set(selected))!=24 or len(regression)!=20:
        raise ValueError('Frozen development24 selection or success20 regression differs')
    if selected[:4] != PRIMARY+OBSERVED or set(selected) != set(regression+PRIMARY+OBSERVED):
        raise ValueError('Selection must contain target1480, observed controls, and exact success20')
    inventory=code_paths()
    if len(inventory)!=103:
        raise ValueError('Current executable inventory differs; review before freezing')
    payload=dict(experiment='m3_e07_population_grain_compact_prompt_development24',
        case_identity='m3_e07_population_grain_revision_development24_v2',date='2026-10-25',
        source_bundle_id=old['source_bundle_id'],prior_pair24_bundle_id=old_bundle(SOURCE)['bundle_id'],
        baseline_reuse_allowed=False,
        limited_revision=dict(previous_r9_bundle_id='f64ea94ac694f3b6b9c383f589a80d3a3ff1253f35cd2b29f37d0f3a6ede4f44',
            previous_r9_comparison_sha256='ee854f78b46b8bc3f8b8651b25e34b6c8712c6a8ec581a94c528b0cba63e2350',
            decision_record_sha256=sha(BACKEND/'evaluation/M3_E07_R9_DECISION_AND_R10_SCOPE_20261025.md'),
            previous_r9_disposition='valid_comparison_candidate_not_accepted',
            scope='population_period_additive_grain_and_compact_advisory_prompt',
            independent_backlog_ids=['BIRD-PG-0173'],chat_token_growth_cap=0.20),
        case_ids=selected,regression_ids=regression,primary_ids=PRIMARY,observed_ids=OBSERVED,
        index_database_ids=old['index_database_ids'],support_files=old['support_files'],
        source_binding=old['source_binding'],model_configuration=old['model_configuration'],
        schema_selection_policy=old['schema_selection_policy'],sql_repair_policy=old['sql_repair_policy'],
        intent_policies={'baseline':intent_policy(),'candidate':intent_policy()},
        semantic_planning_policies={'baseline':None,'candidate':query_semantics_policy()},
        endpoint_scope_policy=old['endpoint_scope_policy'],
        categorical_population_policy=policy(categorical_population=True),
        generation_features={'baseline':['--categorical-population'],
            'candidate':['--categorical-population','--semantic-planning']},
        maximum_generated_cases=48,automatic_holdout=False,
        side_generation_order=['baseline','candidate'],scoring_after_both_captures=True,
        transport_policy=old['transport_policy'],dns_readiness_policy=old['dns_readiness_policy'],
        common_adaptation=old['common_adaptation'],
        treatment='Both sides enable --categorical-population and receive the same categorical-population policy/context. Only candidate enables --semantic-planning. Both sides use identical producer code, source identity and independently built indexes, and are freshly generated in this same-round pair.',
        index_policy='Each side independently builds and verifies its own source-bound index.',
        controllers={},files={},sides={})
    OUT.mkdir(parents=True)
    for name in CONTROL_FILES:
        dst=OUT/'control'/name;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(BACKEND/'scripts'/name,dst)
        payload['controllers'][name]=payload['files']['control/'+name]=sha(dst)
    for side in ('baseline','candidate'):
        # Reuse only the accepted E06 support/evidence assets. Replace every
        # executable with the current source bytes on both sides.
        old_assets=old['sides']['candidate']['assets']
        assets={};copied=set()
        for name,entry in old_assets.items():
            if name==CASE_LIST or name=='evaluation/cases/bird_mini_dev/m3_e06_endpoint_scope24.json':
                continue
            src=BACKEND/name if name in inventory else SOURCE/entry['bundle_path']
            if name in inventory:copied.add(name)
            dst=OUT/'payload'/side/name;dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(src,dst);assets[name]={'bundle_path':dst.relative_to(OUT).as_posix(),'sha256':sha(dst)}
            payload['files'][assets[name]['bundle_path']]=assets[name]['sha256']
        if not set(inventory)<=copied:
            for name in sorted(set(inventory)-copied):
                src=inventory[name];dst=OUT/'payload'/side/name;dst.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(src,dst);assets[name]={'bundle_path':dst.relative_to(OUT).as_posix(),'sha256':sha(dst)}
                payload['files'][assets[name]['bundle_path']]=assets[name]['sha256']
        src=BACKEND/CASE_LIST;dst=OUT/'payload'/side/CASE_LIST;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src,dst);assets[CASE_LIST]={'bundle_path':dst.relative_to(OUT).as_posix(),'sha256':sha(dst)}
        payload['files'][assets[CASE_LIST]['bundle_path']]=assets[CASE_LIST]['sha256']
        code={name:sha(path) for name,path in inventory.items()}
        if set(code)!=set(n for n in assets if n in inventory) or any(assets[n]['sha256']!=value for n,value in code.items()):
            raise ValueError('Frozen executable bytes and inventory differ')
        payload['sides'][side]={'code_files':code,'assets':assets}
    readme=OUT/'README.md'
    readme.write_text('M3 E07 semantic-revision development24 pair. Both baseline and candidate enable --categorical-population and receive the same categorical-population policy/context. Only candidate enables --semantic-planning. Both sides use identical current producer files, source identity and isolated indexes. Baseline reuse is forbidden. The fixed list contains target 1480, observed controls 0050/0173/0459, and success regression20. No credentials or database dump is included.\n',encoding='utf-8')
    payload['files']['README.md']=sha(readme)
    manifest={'schema':'m3_e07_pair24_bundle_v2','bundle_id':digest(payload),'payload':payload}
    (OUT/'bundle_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    from scripts.m3_e07_pair24_common import bundle as verify_bundle
    verify_bundle(OUT)
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name in ('bundle_manifest.json',*payload['files']):archive.write(OUT/name,NAME+'/'+name)
    Path(str(ZIP)+'.sha256').write_text(f'{sha(ZIP)}  {ZIP.name}\n',encoding='ascii')
    print(json.dumps({'bundle_id':manifest['bundle_id'],'zip':str(ZIP),'sha256':sha(ZIP),
        'case_count':len(selected),'regression_count':len(regression),'baseline_code_files':len(payload['sides']['baseline']['code_files']),
        'candidate_code_files':len(payload['sides']['candidate']['code_files']),
        'baseline_candidate_code_identical':payload['sides']['baseline']['code_files']==payload['sides']['candidate']['code_files']},
        ensure_ascii=False,indent=2))

if __name__=='__main__':main()
