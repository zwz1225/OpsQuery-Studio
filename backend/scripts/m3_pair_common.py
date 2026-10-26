"""Stdlib controls for the version-bound M3 E01 development24 pair."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil
import uuid

SIDES=('baseline','candidate')
CONTROLS=('m3_pair_common.py','m3_pair_side.py','prepare_m3_e01_pair24.py','run_m3_e01_pair24.py')
CASE_LIST='evaluation/cases/bird_mini_dev/m3_a_output_contract24.json'
REGRESSION='evaluation/cases/bird_mini_dev/m3_a_success_regression20.json'
PRIMARY=['BIRD-PG-0050','BIRD-PG-0085','BIRD-PG-0407']
MIXED=['BIRD-PG-1479']
SUPPORT_FILES={'data/databases/short_video_ops/_schema.json':'8f5f97512879342a95da5df4973cf9c3b622b9d3bd8e7dec2c3b9ef7a2641ede'}
INDEX_FILES=('retrieval.py','model.py','runtime.py','native.py','coverage.py','intent.py','relationships.py','units_output.py')


class PairError(ValueError):pass


def require(value,message):
    if not value:raise PairError(message)


def now():return datetime.now(timezone.utc).isoformat()
def read(path):return json.loads(Path(path).read_bytes())


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def safe(root,relative):
    p=PurePosixPath(relative)
    require(isinstance(relative,str) and '\\' not in relative and ':' not in relative and not p.is_absolute()
            and bool(p.parts) and all(v not in ('..','.') for v in p.parts),'Invalid relative inventory path')
    root=Path(root).resolve();path=root.joinpath(*p.parts)
    require(path.resolve().is_relative_to(root),'Inventory path escapes root')
    require(not any(q.is_symlink() for q in [path,*list(path.parents)[:len(p.parts)-1]]),'Symlink in controlled inventory')
    return path


def verify_files(root,inventory):
    for name,expected in inventory.items():
        path=safe(root,name)
        require(path.is_file() and sha(path)==expected,'Controlled file missing or changed: '+name)


def write_new(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    data=(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    with path.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())


def checkpoint(path,value):
    value['updated_at']=now();path=Path(path)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    write_new(temporary,value);os.replace(temporary,path)


def copy_new(source,target,expected):
    require(sha(source)==expected,'Copy source differs')
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    with Path(source).open('rb') as src,target.open('xb') as dst:shutil.copyfileobj(src,dst)
    require(sha(target)==expected,'Copied bytes differ')


def bundle(root):
    root=Path(root).resolve();row=read(root/'bundle_manifest.json')
    require(row.get('schema')=='m3_e01_pair24_bundle_v2' and row.get('bundle_id')==digest(row['payload']),'Bundle identity differs')
    p=row['payload'];require(p['primary_ids']==PRIMARY and p['mixed_ids']==MIXED,'Experiment targets differ')
    require(p.get('support_files')==SUPPORT_FILES,'Import support asset inventory differs')
    require(len(p['case_ids'])==len(set(p['case_ids']))==24 and len(p['regression_ids'])==20
            and set(p['regression_ids'])|set(PRIMARY+MIXED)==set(p['case_ids']),'Fixed development24 selection differs')
    require(set(p['controllers'])==set(CONTROLS),'Controller inventory differs')
    verify_files(root,p['files'])
    for side in SIDES:
        info=p['sides'][side]
        require(len(info['code_files'])==96+(side=='candidate'),'Producer inventory size differs')
        for name,entry in info['assets'].items():
            safe(root,name);require(p['files'].get(entry['bundle_path'])==entry['sha256'],'Side asset binding differs')
        require(all(info['assets'].get(n,{}).get('sha256')==value for n,value in info['code_files'].items()),'Producer/asset inventory differs')
        require(all(info['assets'].get(n,{}).get('sha256')==value for n,value in SUPPORT_FILES.items()),'Import support asset binding differs')
        selection=read(safe(root,info['assets'][CASE_LIST]['bundle_path']))
        regression=read(safe(root,info['assets'][REGRESSION]['bundle_path']))
        development=read(safe(root,info['assets']['evaluation/cases/bird_mini_dev/m2_pg_v1/development80.json']['bundle_path']))
        require(selection['case_ids']==p['case_ids'] and regression['case_ids']==p['regression_ids']
            and set(p['case_ids'])<=set(development['case_ids']),'Selection is not the fixed development-only subset')
    old=p['sides']['baseline']['code_files'];new=p['sides']['candidate']['code_files']
    require(set(new)-set(old)=={'evaluation/bird/output_contract.py'} and not set(old)-set(new),'Candidate addition differs')
    require({n for n in old if old[n]!=new[n]}=={'evaluation/bird/case_worker.py','evaluation/bird/diagnostic_runner.py'},'Candidate variable differs')
    for name in INDEX_FILES:
        key='evaluation/bird/'+name;require(old[key]==new[key],'Index-producing code differs')
    return row


def workspace(root):
    root=Path(root).resolve();row=read(root/'workspace.json');manifest=read(root/'control/bundle_manifest.json')
    require(row.get('schema')=='m3_e01_pair24_workspace_v1' and row['bundle_id']==manifest['bundle_id']
            and row['manifest_sha256']==sha(root/'control/bundle_manifest.json'),'Workspace identity differs')
    preparation=read(root/'preparation.json')
    require(preparation.get('workspace_sha256')==sha(root/'workspace.json') and preparation['bundle_id']==row['bundle_id'],'Prepared path/config identity differs')
    p=manifest['payload'];require(digest(p)==manifest['bundle_id'],'Workspace manifest digest differs')
    verify_files(root/'control',p['controllers'])
    for side in SIDES:
        base=root/side/'backend';assets={k:v['sha256'] for k,v in p['sides'][side]['assets'].items()}
        assets.update({'scripts/'+n:p['controllers'][n] for n in ('m3_pair_common.py','m3_pair_side.py')})
        verify_files(base,assets)
        require(read(base/'m3_context.json')==dict(side=side,workspace=str(root),bundle_id=row['bundle_id']),'Side context differs')
        expected={n for n in assets if n.endswith('.py')}
        actual={str(f.relative_to(base)).replace('\\','/') for f in base.rglob('*.py')}
        require(actual==expected,'Unexpected or missing Python source in side directory')
    return row,p


def side_base(root,side):
    require(side in SIDES,'Unknown pair side');return Path(root)/side/'backend'


def private_stats(row):
    result={}
    for key in ('model_config_file','credentials_file'):
        path=Path(row[key]);require(path.is_file(),'Configured private file is missing')
        st=path.stat();result[key]=(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)
    return result


@contextmanager
def exclusive(root):
    require(os.name=='posix','Pair execution requires Linux')
    import fcntl
    with (Path(root)/'.pair24.lock').open('a') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise PairError('Another pair workflow is active') from None
        try:yield
        finally:fcntl.flock(stream,fcntl.LOCK_UN)


def seed_indexes(root,capture):
    """Copy exact, independently validated index bytes; never force an identity hit."""
    baseline=side_base(root,'baseline')/'data/m3_indexes'
    candidate=side_base(root,'candidate')/'data/m3_indexes';copied=[]
    for entry in capture['index_builds']:
        source=Path(entry['path']).resolve();require(source.is_relative_to(baseline.resolve()),'Index source escapes baseline')
        relative=str(source.relative_to(baseline.resolve())).replace('\\','/')
        parts=PurePosixPath(relative).parts
        require(len(parts)==3 and parts[-1]=='schema_index.json' and parts[1]==digest(entry['identity']),'Index path/identity differs')
        require(entry['identity']['source_identity']['logical_database_id']==parts[0],'Index domain differs')
        target=safe(candidate,relative)
        copy_new(source,target,entry['sha256'])
        copied.append(dict(database_id=parts[0],sha256=entry['sha256'],identity=entry['identity']))
    require(len(copied)==len({v['database_id'] for v in copied})==8,'Expected exactly eight development domain indexes')
    return copied


def _tokens(capture):
    total=0
    for case in capture['cases']:
        events=case.get('budget',{}).get('model_events')
        if events is None:return None
        for event in events:
            if event['kind']!='chat':continue
            value=(event.get('usage') or {}).get('total_tokens')
            if type(value) is not int:return None
            total+=value
    return total


def _p95(capture):
    values=[c.get('case_wall_seconds') for c in capture['cases']]
    if not all(type(v) in (int,float) and v>=0 for v in values):return None
    return sorted(values)[math.ceil(.95*len(values))-1]


def compare_pair(payload,captures,natives):
    """Summarize already verified reports; no scoring changes or model feedback."""
    a,b=(captures[s] for s in SIDES)
    for key in ('model_configuration','source_binding','schema_selection_policy','sql_repair_policy','intent_candidate_policy','case_list_sha256'):
        require(a[key]==b[key],'Pair comparability differs: '+key)
    for capture in (a,b):
        require(capture['selected_case_ids']==payload['case_ids'] and len(capture['cases'])==24,'Pair case order differs')
    ai={i['identity']['source_identity']['logical_database_id']:i for i in a['index_builds']}
    bi={i['identity']['source_identity']['logical_database_id']:i for i in b['index_builds']}
    require(set(ai)==set(bi) and len(ai)==8,'Pair index domains differ')
    require(all(ai[db]['identity']==bi[db]['identity'] and ai[db]['sha256']==bi[db]['sha256'] and bi[db]['cache_hit'] is True for db in ai),'Pair index bytes/identity differ')
    outcome={s:{v['case_id']:v['native_comparison']['matches_frozen_gold'] for v in natives[s]['cases']} for s in SIDES}
    rows=[]
    for i,rid in enumerate(payload['case_ids']):
        left,right=a['cases'][i],b['cases'][i]
        require(left['source_identity']==right['source_identity'] and left['query_role']==right['query_role'],'Pair per-case source differs')
        gl=left['development_diagnostics']['retrieval']['schema_graph']['value']
        gr=right['development_diagnostics']['retrieval']['schema_graph']['value']
        same_schema=([f['id'] for f in gl['fields']]==[f['id'] for f in gr['fields']] and gl['joins']==gr['joins'])
        rows.append(dict(case_id=rid,database_id=left['database_id'],same_authorized_schema=same_schema,
            baseline_correct=outcome['baseline'].get(rid,False),candidate_correct=outcome['candidate'].get(rid,False),
            baseline_status=left['status'],candidate_status=right['status'],
            baseline_generated_sql=left.get('generated_sql'),candidate_generated_sql=right.get('generated_sql'),
            baseline_budget=left.get('budget'),candidate_budget=right.get('budget')))
    bm=sum(v['baseline_correct'] for v in rows);cm=sum(v['candidate_correct'] for v in rows)
    primary=sum(v['candidate_correct'] for v in rows if v['case_id'] in PRIMARY)
    retained=sum(v['candidate_correct'] for v in rows if v['case_id'] in payload['regression_ids'])
    tokens={s:_tokens(captures[s]) for s in SIDES};latency={s:_p95(captures[s]) for s in SIDES}
    costs_known=all(v is not None for v in [*tokens.values(),*latency.values()])
    cost_pass=costs_known and tokens['candidate']<=tokens['baseline']*1.2 and latency['candidate']<=latency['baseline']*1.2
    checks=dict(primary_at_least_two=primary>=2,net_gain_at_least_one=cm-bm>=1,
        twenty_successes_retained=retained==20,baseline_not_already_all_primary_correct=
        sum(v['baseline_correct'] for v in rows if v['case_id'] in PRIMARY)<3,cost_known=costs_known,cost_within_screen=cost_pass,
        same_observed_schema_all_cases=all(v['same_authorized_schema'] for v in rows))
    return dict(case_count=24,baseline_match_count=bm,candidate_match_count=cm,net_gain=cm-bm,
        wrong_to_right=[v['case_id'] for v in rows if not v['baseline_correct'] and v['candidate_correct']],
        right_to_wrong=[v['case_id'] for v in rows if v['baseline_correct'] and not v['candidate_correct']],
        schema_context_changed_case_ids=[v['case_id'] for v in rows if not v['same_authorized_schema']],
        primary_candidate_match_count=primary,regression_retained_count=retained,
        chat_total_tokens=tokens,case_wall_p95_seconds=latency,
        index_policy='Identical validated bytes copied into separate directories; candidate validates its own source/model/index identity',
        screening=checks,automatic_screen_pass=all(checks.values()),business_review_required=['BIRD-PG-1479','BIRD-PG-0407'],
        acceptance='manual_semantic_review_required',formal_benchmark=False,holdout_run=False,
        by_database={db:{s:sum(v[s+'_correct'] for v in rows if v['database_id']==db) for s in SIDES}
                     for db in sorted({v['database_id'] for v in rows})},cases=rows,
        meaning='One controlled development comparison, not statistical significance or unseen holdout accuracy.')
