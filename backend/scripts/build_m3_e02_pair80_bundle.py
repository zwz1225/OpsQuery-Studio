"""Freeze the M2 v4 versus accepted E02 development80 pair with one transport."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[2]
BACKEND=ROOT/'backend'
OLD=BACKEND/'.downloads/m3_e01_pair24_bundle_20261021_v2'
ACCEPTED=BACKEND/'.downloads/m3_e02_pair24_bundle_20261022_v5'
TRANSPORT=BACKEND/'.downloads/m3_e03_pair24_process_dns_v1_20261023_r2'
NAME='m3_e02_pair80_process_dns_v1_20261024_r3'
OUT=BACKEND/'.downloads'/NAME
ZIP=ROOT/'M3_E02_pair80_process_dns_v1_20261024_r3.zip'
CONTROLS=('m3_e02_pair80_common.py','m3_e02_pair80_side.py',
          'prepare_m3_e02_pair80.py','run_m3_e02_pair80.py')
COMMON=('evaluation/bird/model.py','evaluation/bird/retrieval.py',
        'evaluation/bird/diagnostic_runner.py','evaluation/bird/process_dns.py')
CASE='evaluation/cases/bird_mini_dev/m2_pg_v1/development80.json'
SEMANTIC=('evaluation/bird/intent.py','evaluation/bird/retrieval.py',
          'evaluation/bird/case_worker.py','evaluation/bird/diagnostic_runner.py',
          'evaluation/bird/demand_relations.py','evaluation/bird/reviewed_relations.py')
HISTORY=BACKEND/'evaluation/results/m2_public_intent_v4_development80_native_server.json'
PARENT_IDS={
    OLD:'41ff1ccc6837664ef5a4a9d43e34d7bbd321c2e587d56d82013c6e60721304d8',
    TRANSPORT:'483c6a685bd96a5b5e495012ff37fc879011d4216b5fd40bb0abed2895759a2c',
}
HISTORY_SHA='1bbb278d0a5ffb99b3049faff6e1da2c482230284188e71e8d4fb44504c38774'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,
        separators=(',',':'),allow_nan=False).encode()).hexdigest()


def replace_once(text,before,after):
    if text.count(before)!=1:raise ValueError('Frozen common adaptation anchor differs')
    return text.replace(before,after,1)


def source(root,side,name,manifest):
    return root/manifest['payload']['sides'][side]['assets'][name]['bundle_path']


def verify(root,expected=None):
    row=json.loads((root/'bundle_manifest.json').read_bytes())
    if digest(row['payload'])!=row['bundle_id'] or (expected and row['bundle_id']!=expected):
        raise ValueError('Frozen source manifest identity differs')
    for name,value in row['payload']['files'].items():
        if sha(root/name)!=value:raise ValueError('Frozen source file differs: '+name)
    return row


def baseline_retrieval(old,shared):
    left=old.split('def index_identity(',1)[1].split('\ndef index_path(',1)[0]
    right=shared.split('def index_identity(',1)[1].split('\ndef index_path(',1)[0]
    right=right.replace(",'demand_relations.py','reviewed_relations.py'",'')
    if right==shared.split('def index_identity(',1)[1].split('\ndef index_path(',1)[0]:
        raise ValueError('Frozen candidate relation files absent from index identity')
    text=replace_once(old,'def index_identity('+left,'def index_identity('+right)
    before=old.split('def build_index(',1)[1].split('\ndef retrieve(',1)[0]
    after=shared.split('def build_index(',1)[1].split('\ndef retrieve(',1)[0]
    return replace_once(text,'def build_index('+before,'def build_index('+after)


def baseline_diagnostic(old,shared):
    text=replace_once(old,'from .model import ModelConfig\n',
                      'from .model import ModelConfig, TRANSPORT_POLICY,recorded_binding\n')
    head='            model_configuration=config.public(),workers=1,cases=[],index_builds=[])'
    added=shared[shared.index('            model_configuration=config.public()'):
                 shared.index("        report['sql_repair_policy']")].rstrip()
    text=replace_once(text,head,added)
    old_index=("                runtime=registry.get(db);report['postgresql_connected']=True\n"
               "                receipts[db]=runtime.receipt();index=build_index(runtime,config,args.index_root)")
    new_index=shared[shared.index("                attempt={'database_id':db"):shared.index("                report['index_builds'].append(index)")].rstrip()
    for left,right in (
        (old_index,new_index),
        ("            try:result=run_case_process(request,seconds=600)",
         "            report['new_model_request_count']=None\n            try:result=run_case_process(request,seconds=600)"),
        ("            report['cases'].append(result)",
         "            report['cases'].append(result)\n"
         "            counts=[c.get('new_model_request_count') for c in report['cases']]\n"
         "            report['new_model_request_count']=(report['preparation_model_http_attempts']+sum(counts)\n"
         "                if all(type(v) is int for v in counts) else None)"),
        ("new_model_request_count=None if unknown else attempts,",
         "new_model_request_count=None if unknown else attempts+report['preparation_model_http_attempts'],"),
    ):
        text=replace_once(text,left,right)
    if '--condition-relations' in text or '--output-contract' in text:
        raise ValueError('Baseline semantic flags leaked into M2 v4')
    return text


def main():
    if OUT.exists() or ZIP.exists() or Path(str(ZIP)+'.sha256').exists():
        raise SystemExit('Preserve existing delivery; choose a new version')
    old=verify(OLD,PARENT_IDS[OLD]);accepted=verify(ACCEPTED);transport=verify(TRANSPORT,PARENT_IDS[TRANSPORT])
    if sha(HISTORY)!=HISTORY_SHA:raise ValueError('Accepted M2 v4 native history changed')
    old_side=old['payload']['sides']['baseline']
    candidate_side=transport['payload']['sides']['baseline']
    accepted_side=accepted['payload']['sides']['candidate']
    for name in ('evaluation/bird/intent.py','evaluation/bird/case_worker.py',
                 'evaluation/bird/demand_relations.py','evaluation/bird/reviewed_relations.py'):
        if sha(source(TRANSPORT,'baseline',name,transport))!=sha(source(ACCEPTED,'candidate',name,accepted)):
            raise ValueError('Accepted E02 semantic source changed: '+name)
    history=json.loads(HISTORY.read_bytes())
    case=json.loads(source(OLD,'baseline',CASE,old).read_bytes())['case_ids']
    success=[r['case_id'] for r in history['cases'] if r['native_comparison']['matches_frozen_gold']]
    excluded={row['case_id'] for row in history['excluded_cases']}
    if (history['run_status']!='complete' or history['source_case_count']!=80
        or history['selected_case_ids']!=[cid for cid in case if cid not in excluded]
        or len(excluded)!=3 or history['summary']['native_match_count']!=50
        or len(success)!=50 or len(case)!=80):
        raise ValueError('Accepted historical success50 cohort differs')
    if old['payload']['source_binding']!=transport['payload']['source_binding']:
        raise ValueError('Pair source/protocol identity differs')
    from evaluation.bird.model import TRANSPORT_POLICY
    from scripts.m3_e02_pair80_common import DNS_READINESS_POLICY,bundle,CASE_LIST,REGRESSION,SUPPORT_FILES
    p=dict(experiment='m3_e02_accepted_semantics_development80',date='2026-10-24',
        source_bundles={'m2_v4':old['bundle_id'],'accepted_e02':accepted['bundle_id'],
                        'shared_transport':transport['bundle_id']},
        historical_success50_report_sha256=HISTORY_SHA,historical_success50_ids=success,
        case_ids=case,regression_ids=old['payload']['regression_ids'],
        primary_ids=['BIRD-PG-1479'],observed_ids=['BIRD-PG-0407','BIRD-PG-0085'],
        support_files=SUPPORT_FILES,source_binding=old['payload']['source_binding'],
        model_configuration=old['payload']['model_configuration'],
        schema_selection_policy=old['payload']['schema_selection_policy'],
        sql_repair_policy=old['payload']['sql_repair_policy'],
        intent_candidate_policy=old['payload']['intent_candidate_policy'],
        maximum_generated_cases=160,automatic_holdout=False,
        side_generation_order=['baseline','candidate'],scoring_after_both_captures=True,
        transport_policy=TRANSPORT_POLICY,dns_readiness_policy=DNS_READINESS_POLICY,
        common_adaptation=dict(policy_id='bird_process_dns_https_v1',files=list(COMMON),
            source_bundle_id=transport['bundle_id'],
            baseline_scope='M2 v4 semantic code with only shared transport and accounting changes',
            candidate_scope='Accepted E02 semantic code with identical shared transport'),
        index_policy='Each side builds and verifies its own source-bound index.',
        controllers={},files={},sides={})
    if p['case_ids']!=json.loads(source(TRANSPORT,'baseline',CASE,transport).read_bytes())['case_ids']:
        raise ValueError('Candidate development80 split differs')
    OUT.mkdir(parents=True)
    for name in CONTROLS:
        dst=OUT/'control'/name;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(BACKEND/'scripts'/name,dst)
        p['controllers'][name]=p['files']['control/'+name]=sha(dst)
    for side in ('baseline','candidate'):
        assets={};code=deepcopy(old_side['code_files'])
        for name,entry in old_side['assets'].items():
            src=OLD/entry['bundle_path'];dst=OUT/'payload'/side/name
            dst.parent.mkdir(parents=True,exist_ok=True)
            if side=='candidate' and name in SEMANTIC:
                src=source(TRANSPORT,'baseline',name,transport)
            if name=='evaluation/bird/model.py':src=source(TRANSPORT,'baseline',name,transport)
            if side=='baseline' and name=='evaluation/bird/retrieval.py':
                old_text=src.read_text(encoding='utf-8');shared=source(TRANSPORT,'baseline',name,transport).read_text(encoding='utf-8')
                dst.write_bytes(baseline_retrieval(old_text,shared).encode())
            elif side=='baseline' and name=='evaluation/bird/diagnostic_runner.py':
                old_text=src.read_text(encoding='utf-8');shared=source(TRANSPORT,'baseline',name,transport).read_text(encoding='utf-8')
                dst.write_bytes(baseline_diagnostic(old_text,shared).encode())
            else:shutil.copyfile(src,dst)
            assets[name]=dict(bundle_path=dst.relative_to(OUT).as_posix(),sha256=sha(dst))
            if name in code:code[name]=sha(dst)
            p['files'][assets[name]['bundle_path']]=sha(dst)
        for name in ('evaluation/bird/process_dns.py',):
            src=source(TRANSPORT,'baseline',name,transport);dst=OUT/'payload'/side/name
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
            assets[name]=dict(bundle_path=dst.relative_to(OUT).as_posix(),sha256=sha(dst))
            code[name]=sha(dst);p['files'][assets[name]['bundle_path']]=sha(dst)
        if side=='candidate':
            for name in ('evaluation/bird/demand_relations.py','evaluation/bird/reviewed_relations.py'):
                src=source(TRANSPORT,'baseline',name,transport);dst=OUT/'payload'/side/name
                dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
                assets[name]=dict(bundle_path=dst.relative_to(OUT).as_posix(),sha256=sha(dst))
                code[name]=sha(dst);p['files'][assets[name]['bundle_path']]=sha(dst)
        p['sides'][side]=dict(code_files=code,assets=assets)
    readme=OUT/'README.md'
    readme.write_text('M3 accepted E02 semantic development80 pair. No credentials, model outputs, or database dumps.\n',encoding='utf-8')
    p['files']['README.md']=sha(readme)
    row=dict(schema='m3_e02_pair80_bundle_v1',bundle_id=digest(p),payload=p)
    (OUT/'bundle_manifest.json').write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    bundle(OUT)
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name in ('bundle_manifest.json',*p['files']):
            archive.write(OUT/name,NAME+'/'+name)
    Path(str(ZIP)+'.sha256').write_text(f'{sha(ZIP)}  {ZIP.name}\n',encoding='ascii')
    print(json.dumps(dict(bundle_id=row['bundle_id'],zip=str(ZIP),sha256=sha(ZIP),
        baseline_code_files=len(p['sides']['baseline']['code_files']),
        candidate_code_files=len(p['sides']['candidate']['code_files']),
        fixed_cases=len(case),historical_successes=len(success)),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
