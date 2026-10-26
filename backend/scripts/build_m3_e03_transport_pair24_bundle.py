"""Freeze the same bounded transport/report adaptation on both preserved E03 sides."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / 'backend'
SOURCE = BACKEND / '.downloads/m3_e03_pair24_bundle_20261023'
NAME = 'm3_e03_pair24_transport_v2_20261023_r3'
OUT = BACKEND / '.downloads' / NAME
ZIP = ROOT / 'M3_E03_pair24_transport_v2_20261023_r3.zip'
CONTROLS = ('m3_e03_pair_common.py', 'm3_e03_pair_side.py',
            'prepare_m3_e03_pair24.py', 'run_m3_e03_pair24.py')
COMMON = ('evaluation/bird/model.py', 'evaluation/bird/retrieval.py',
          'evaluation/bird/diagnostic_runner.py')


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('Shared adaptation does not match the frozen source')
    return text.replace(before, after, 1)


def shared_source(name, frozen, old_candidate):
    current = (BACKEND / name).read_text(encoding='utf-8')
    if name.endswith('/model.py'):
        if frozen != old_candidate: raise ValueError('Original model sides differ')
        return current
    if name.endswith('/retrieval.py'):
        before = old_candidate.split('def build_index(', 1)[1].split('\ndef retrieve(', 1)[0]
        after = current.split('def build_index(', 1)[1].split('\ndef retrieve(', 1)[0]
        return replace_once(frozen, 'def build_index(' + before, 'def build_index(' + after)
    # Only reporting changes are shared. Preserve each side's original candidate flags.
    result = replace_once(frozen, 'from .model import ModelConfig\n',
                         'from .model import ModelConfig, TRANSPORT_POLICY\n')
    for left, right in (
        ('            model_configuration=config.public(),workers=1,cases=[],index_builds=[])',
         current[current.index('            model_configuration=config.public()'):current.index("        report['sql_repair_policy']")].rstrip()),
        ("                runtime=registry.get(db);report['postgresql_connected']=True\n"
         "                receipts[db]=runtime.receipt();index=build_index(runtime,config,args.index_root)",
         current[current.index("                attempt={'database_id':db"):current.index("                report['index_builds'].append(index)")].rstrip()),
        ("new_model_request_count=None if unknown else attempts,",
         "new_model_request_count=None if unknown else attempts+report['preparation_model_http_attempts'],"),
        ('            try:result=run_case_process(request,seconds=600)',
         "            report['new_model_request_count']=None\n            try:result=run_case_process(request,seconds=600)"),
        ("            report['cases'].append(result)",
         "            report['cases'].append(result)\n"
         "            counts=[c.get('new_model_request_count') for c in report['cases']]\n"
         "            report['new_model_request_count']=(report['preparation_model_http_attempts']+sum(counts)\n"
         "                if all(type(v) is int for v in counts) else None)"),
    ):
        result = replace_once(result, left, right)
    return result


def main():
    if OUT.exists() or ZIP.exists() or Path(str(ZIP)+'.sha256').exists():
        raise SystemExit('Preserve existing bundle; choose a new version')
    old = json.loads((SOURCE / 'bundle_manifest.json').read_bytes())
    if old['bundle_id'] != digest(old['payload']): raise ValueError('Original manifest differs')
    for name, value in old['payload']['files'].items():
        if sha(SOURCE/name) != value: raise ValueError('Original inventory changed: '+name)
    p = deepcopy(old['payload'])
    p.update(date='2026-10-23', common_adaptation=dict(
        policy_id='bird_bounded_dns_recovery_v1', source_bundle_id=old['bundle_id'],
        files=list(COMMON), baseline_scope='Frozen E02 candidate plus shared transport and usage reporting',
        candidate_scope='Frozen E03 candidate plus identical shared transport and usage reporting'),
        transport_policy=__import__('evaluation.bird.model', fromlist=['TRANSPORT_POLICY']).TRANSPORT_POLICY,
        dns_readiness_policy=dict(__import__('scripts.m3_e03_pair_common',
            fromlist=['DNS_READINESS_POLICY']).DNS_READINESS_POLICY))
    p['files'] = {}
    p['controllers'] = {}
    OUT.mkdir(parents=True)
    for name in CONTROLS:
        path = OUT/'control'/name; path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(BACKEND/'scripts'/name,path)
        p['controllers'][name] = sha(path)
        p['files']['control/'+name] = sha(path)
    for side, info in p['sides'].items():
        for name, entry in info['assets'].items():
            original = SOURCE/old['payload']['sides'][side]['assets'][name]['bundle_path']
            path = OUT/'payload'/side/name; path.parent.mkdir(parents=True,exist_ok=True)
            if name in COMMON:
                candidate_entry=old['payload']['sides']['candidate']['assets'][name]
                text=shared_source(name, original.read_text(encoding='utf-8'),
                    (SOURCE/candidate_entry['bundle_path']).read_text(encoding='utf-8'))
                path.write_bytes(text.encode('utf-8'))
                info['code_files'][name] = sha(path)
            else: shutil.copyfile(original,path)
            entry.update(bundle_path=path.relative_to(OUT).as_posix(),sha256=sha(path))
            p['files'][entry['bundle_path']] = entry['sha256']
    readme=OUT/'README.md'
    readme.write_bytes(b'M3 E03 transport v2: both sides share bounded DNS recovery and failed-index usage recording. See server runbook.\n')
    p['files']['README.md']=sha(readme)
    row=dict(schema='m3_e03_pair24_bundle_v2',payload=p,bundle_id=digest(p))
    (OUT/'bundle_manifest.json').write_bytes((json.dumps(row,ensure_ascii=False,indent=2)+'\n').encode())
    # Validate all code/asset/target constraints before exporting.
    from scripts.m3_e03_pair_common import bundle
    bundle(OUT)
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ['bundle_manifest.json',*p['files']]:
            archive.write(OUT/name,NAME+'/'+name)
    Path(str(ZIP)+'.sha256').write_bytes(f'{sha(ZIP)}  {ZIP.name}\n'.encode('ascii'))
    print(json.dumps(dict(bundle_id=row['bundle_id'],zip=str(ZIP),sha256=sha(ZIP),
        baseline_files=len(p['sides']['baseline']['code_files']),
        candidate_files=len(p['sides']['candidate']['code_files'])),indent=2))


if __name__ == '__main__':main()
