"""Build a hash-bound E02 server bundle from the preserved M2 v4 baseline."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[2]
BACKEND=ROOT/'backend'
SOURCE=BACKEND/'.downloads/m3_e01_pair24_bundle_20261021_v2'
OUT=BACKEND/'.downloads/m3_e02_pair24_bundle_20261022_v5'
ZIP=ROOT/'M3_E02_pair24_sync_20261022_v5.zip'
CONTROLS=('m3_e02_pair_common.py','m3_e02_pair_side.py','prepare_m3_e02_pair24.py','run_m3_e02_pair24.py')
OVERLAY=('evaluation/bird/intent.py','evaluation/bird/retrieval.py','evaluation/bird/case_worker.py',
         'evaluation/bird/diagnostic_runner.py','evaluation/bird/demand_relations.py','evaluation/bird/reviewed_relations.py')
CASE='evaluation/cases/bird_mini_dev/m3_e02_condition_relation24.json'

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(value): return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def write(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def copy(source,target):
    Path(target).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)

def main():
    if OUT.exists() or ZIP.exists() or Path(str(ZIP)+'.sha256').exists():
        raise SystemExit('E02 bundle output already exists; preserve it and choose a new dated target')
    old=json.loads((SOURCE/'bundle_manifest.json').read_bytes())['payload']
    case=json.loads((BACKEND/CASE).read_bytes())
    ids=case['case_ids']; regression=old['regression_ids']
    if ids!=old['case_ids'] or len(ids)!=24 or len(set(ids))!=24:
        raise SystemExit('The fixed E02 case IDs/order must match the reviewed E01 development24 list')
    OUT.mkdir(parents=True)
    for name in CONTROLS: copy(BACKEND/'scripts'/name,OUT/'control'/name)
    copy(BACKEND/CASE,OUT/'payload/shared'/CASE)
    payload=dict(experiment='m3_e02_condition_relation_currency_semantics',date='2026-10-22',
        files={},controllers={n:sha(OUT/'control'/n) for n in CONTROLS},case_ids=ids,
        regression_ids=regression,primary_ids=['BIRD-PG-1479'],observed_ids=['BIRD-PG-0407'],
        other_development_ids=[v for v in ids if v not in regression],support_files=old['support_files'],
        model_configuration=old['model_configuration'],source_binding=old['source_binding'],
        schema_selection_policy=old['schema_selection_policy'],sql_repair_policy=old['sql_repair_policy'],
        intent_candidate_policy=old['intent_candidate_policy'],side_generation_order=['baseline','candidate'],
        scoring_after_both_captures=True,shared_inputs_policy='Same server data, protocol, credentials path and public model configuration; secrets and database data are not copied.',
        index_policy='Independent indexes per side; each index identity binds its own producer code. Same live source identity is required; index byte/hash equality and cache hits are not required.',
        maximum_generated_cases=48,automatic_holdout=False,automatic_development80=False)
    sides={}
    for side in ('baseline','candidate'):
        assets={}
        # Both sides start from the same preserved M2 v4 baseline snapshot.
        for name,entry in old['sides']['baseline']['assets'].items():
            src=SOURCE/entry['bundle_path'];target=OUT/f'payload/{side}/{name}'
            copy(src,target);assets[name]={'bundle_path':target.relative_to(OUT).as_posix(),'sha256':sha(target)}
        # Same frozen case-list bytes and path in both isolated producers.
        target=OUT/f'payload/{side}/{CASE}';copy(BACKEND/CASE,target)
        assets[CASE]={'bundle_path':target.relative_to(OUT).as_posix(),'sha256':sha(target)}
        code={n:v for n,v in old['sides']['baseline']['code_files'].items()}
        if side=='candidate':
            for name in OVERLAY:
                src=BACKEND/name;target=OUT/f'payload/{side}/{name}';copy(src,target)
                code[name]=sha(target);assets[name]={'bundle_path':target.relative_to(OUT).as_posix(),'sha256':sha(target)}
            for name in ('evaluation/bird/demand_relations.py','evaluation/bird/reviewed_relations.py'):
                code[name]=sha(OUT/f'payload/{side}/{name}')
        sides[side]={'code_files':code,'assets':assets}
    payload['sides']=sides
    files={'README.md':None}
    (OUT/'README.md').write_text('# M3 E02 pair24 bundle\n\nSee the E02 server runbook. No credentials or database dump are included.\n',encoding='utf-8')
    files['README.md']=sha(OUT/'README.md')
    for name in CONTROLS: files[f'control/{name}']=sha(OUT/'control'/name)
    for side,info in sides.items():
        for name,entry in info['assets'].items():files[entry['bundle_path']]=entry['sha256']
    payload['files']=files
    manifest={'schema':'m3_e02_pair24_bundle_v1','payload':payload,'bundle_id':digest(payload)}
    write(OUT/'bundle_manifest.json',manifest)
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.write(OUT/'bundle_manifest.json','m3_e02_pair24_bundle_20261022_v5/bundle_manifest.json')
        for rel in files:
            z.write(OUT/rel,f'm3_e02_pair24_bundle_20261022_v5/{rel}')
    value=sha(ZIP)
    Path(str(ZIP)+'.sha256').write_text(f'{value}  {ZIP.name}\n',encoding='ascii')
    print(json.dumps({'bundle_root':str(OUT),'zip':str(ZIP),'sha256':value,'case_count':len(ids),
        'baseline_code_files':len(sides['baseline']['code_files']),'candidate_code_files':len(sides['candidate']['code_files']),
        'changed_existing_files':[n for n in sides['baseline']['code_files'] if sides['baseline']['code_files'][n]!=sides['candidate']['code_files'].get(n)],
        'added_candidate_files':sorted(set(sides['candidate']['code_files'])-set(sides['baseline']['code_files']))},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
