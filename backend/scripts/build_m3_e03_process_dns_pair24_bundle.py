"""Derive a fresh E03 pair from immutable r3 with identical explicit DNS transport."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import shutil
import zipfile

from .build_m3_e03_transport_pair24_bundle import sha,digest,replace_once,ROOT,BACKEND,CONTROLS

SOURCE=BACKEND/'.downloads/m3_e03_pair24_transport_v2_20261023_r3'
NAME='m3_e03_pair24_process_dns_v1_20261023_r2'
OUT=BACKEND/'.downloads'/NAME
ZIP=ROOT/'M3_E03_pair24_process_dns_v1_20261023_r2.zip'
COMMON=('evaluation/bird/model.py','evaluation/bird/retrieval.py',
    'evaluation/bird/diagnostic_runner.py','evaluation/bird/process_dns.py')


def shared_source(name,frozen,old_candidate):
    current=(BACKEND/name).read_text(encoding='utf-8')
    if name.endswith('/model.py'):
        if frozen!=old_candidate:raise ValueError('Frozen r3 model sides differ')
        return current
    if name.endswith('/retrieval.py'):
        before=old_candidate.split('def index_identity(',1)[1].split('\ndef index_path(',1)[0]
        after=current.split('def index_identity(',1)[1].split('\ndef index_path(',1)[0]
        return replace_once(frozen,'def index_identity('+before,'def index_identity('+after)
    result=replace_once(frozen,'from .model import ModelConfig, TRANSPORT_POLICY\n',
        'from .model import ModelConfig, TRANSPORT_POLICY,recorded_binding\n')
    result=replace_once(result,
        'transport_policy=TRANSPORT_POLICY,preparation_attempts=[],preparation_model_http_attempts=0,',
        'transport_policy=TRANSPORT_POLICY,transport_dependency_binding=recorded_binding(),\n'
        '            preparation_attempts=[],preparation_model_http_attempts=0,')
    return result


def main():
    if OUT.exists() or ZIP.exists() or Path(str(ZIP)+'.sha256').exists():
        raise SystemExit('Preserve existing delivery; choose a new revision')
    old=json.loads((SOURCE/'bundle_manifest.json').read_bytes())
    if old['bundle_id']!='07e8263e43700091c3c71787d5344648a6b1e9febb145ea25b6ffb24a9c846db' or digest(old['payload'])!=old['bundle_id']:
        raise ValueError('Immutable r3 source differs')
    for name,value in old['payload']['files'].items():
        if sha(SOURCE/name)!=value:raise ValueError('Frozen r3 inventory differs')
    from evaluation.bird.model import TRANSPORT_POLICY
    from .m3_e03_pair_common import DNS_READINESS_POLICY,bundle
    p=deepcopy(old['payload'])
    p.update(date='2026-10-23',transport_policy=TRANSPORT_POLICY,dns_readiness_policy=DNS_READINESS_POLICY,
        common_adaptation=dict(policy_id='bird_process_dns_https_v1',source_bundle_id=old['bundle_id'],
            files=list(COMMON),added_files=['evaluation/bird/process_dns.py'],
            baseline_scope='Frozen E02 semantics plus explicit DNS and verified HTTPS',
            candidate_scope='Frozen E03 semantics plus identical explicit DNS and verified HTTPS'))
    p['files']={};p['controllers']={};OUT.mkdir(parents=True)
    for name in CONTROLS:
        path=OUT/'control'/name;path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(BACKEND/'scripts'/name,path)
        p['controllers'][name]=p['files']['control/'+name]=sha(path)
    for side,info in p['sides'].items():
        for name,entry in info['assets'].items():
            source=SOURCE/old['payload']['sides'][side]['assets'][name]['bundle_path']
            path=OUT/'payload'/side/name;path.parent.mkdir(parents=True,exist_ok=True)
            if name in COMMON:
                candidate=SOURCE/old['payload']['sides']['candidate']['assets'][name]['bundle_path']
                text=shared_source(name,source.read_text(encoding='utf-8'),candidate.read_text(encoding='utf-8'))
                path.write_bytes(text.encode('utf-8'));info['code_files'][name]=sha(path)
            else:shutil.copyfile(source,path)
            entry.update(bundle_path=path.relative_to(OUT).as_posix(),sha256=sha(path))
            p['files'][entry['bundle_path']]=entry['sha256']
        name='evaluation/bird/process_dns.py';path=OUT/'payload'/side/name
        shutil.copyfile(BACKEND/name,path)
        entry=dict(bundle_path=path.relative_to(OUT).as_posix(),sha256=sha(path))
        info['assets'][name]=entry;info['code_files'][name]=entry['sha256']
        p['files'][entry['bundle_path']]=entry['sha256']
    readme=OUT/'README.md'
    readme.write_bytes(b'E03 process DNS v1: immutable semantic sides plus identical explicit resolver/TLS; see server runbook.\n')
    p['files']['README.md']=sha(readme)
    row=dict(schema='m3_e03_pair24_bundle_v3',bundle_id=digest(p),payload=p)
    (OUT/'bundle_manifest.json').write_bytes((json.dumps(row,ensure_ascii=False,indent=2)+'\n').encode())
    bundle(OUT)
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ['bundle_manifest.json',*p['files']]:archive.write(OUT/name,NAME+'/'+name)
    Path(str(ZIP)+'.sha256').write_bytes(f'{sha(ZIP)}  {ZIP.name}\n'.encode('ascii'))
    print(json.dumps(dict(bundle_id=row['bundle_id'],zip=str(ZIP),sha256=sha(ZIP),
        baseline_files=len(p['sides']['baseline']['code_files']),candidate_files=len(p['sides']['candidate']['code_files'])),indent=2))


if __name__=='__main__':main()
