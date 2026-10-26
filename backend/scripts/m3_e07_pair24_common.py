"""Stdlib controls for the version-bound M3 categorical-population development24 pair."""
from __future__ import annotations

from contextlib import contextmanager
import ast
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import time
from urllib.parse import urlsplit
import uuid

SIDES=('baseline','candidate')
DNS_READINESS_POLICY=dict(policy_id='bird_process_dns_preflight_v1',
    implementation='producer evaluation.bird.process_dns.readiness',
    queries_per_host_per_side=1,https_head_per_host_per_side=1,
    timeout_seconds=20,before_generation_reservation=True,model_requests=0,system_dns_modified=False)
BASE_CONTROLS=('m3_e07_pair24_common.py','m3_e07_pair24_side.py','prepare_m3_e07_pair24.py',
    'run_m3_e07_pair24.py')
RECOVERY_CONTROL='adopt_m3_e07_pair24_baseline.py'
CASE_LIST='evaluation/cases/bird_mini_dev/m3_categorical_population_pair24.json'
REGRESSION='evaluation/cases/bird_mini_dev/m3_a_success_regression20.json'
PRIMARY=['BIRD-PG-1480']
OBSERVED=['BIRD-PG-0050','BIRD-PG-0173','BIRD-PG-0459']
SUPPORT_FILES={'data/databases/short_video_ops/_schema.json':'8f5f97512879342a95da5df4973cf9c3b622b9d3bd8e7dec2c3b9ef7a2641ede'}
INDEX_FILES=('retrieval.py','model.py','process_dns.py','runtime.py','native.py','coverage.py','intent.py','relationships.py','units_output.py')
CATEGORICAL_POLICY={'policy_id':'bird_public_categorical_population_context_v1',
    'development_candidate':True,'formal_protocol_override':False,'baseline_preserved':True,
    'max_fields':20,'max_intent_additions':8,'max_hops':2,
    'authority':'declared_fk_or_separately_reviewed_source_bound_candidate',
    'samples_are_predicates':False,'automatic_join_type':None,'sql_rewriting':False,
    'numeric_policy_changed':False,'native_ex_unchanged':True}
BASE_RELATION_POLICY={**CATEGORICAL_POLICY,'policy_id':'bird_public_condition_relation_context_v1'}


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


def frozen_semantics_policy(root,payload):
    """Read verified literal prompt constants without importing the server project."""
    entry=payload['sides']['candidate']['assets']['evaluation/bird/intent.py']
    path=safe(root,entry['bundle_path'])
    require(sha(path)==entry['sha256'],'Frozen semantic prompt bytes differ')
    names={'QUERY_SEMANTICS_POLICY','QUERY_SEMANTICS_GUIDANCE'};values={}
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            name=node.targets[0].id
            if name in names:
                require(name not in values,'Duplicate frozen semantic prompt constant')
                values[name]=ast.literal_eval(node.value)
    require(set(values)==names and isinstance(values['QUERY_SEMANTICS_POLICY'],str)
        and isinstance(values['QUERY_SEMANTICS_GUIDANCE'],list)
        and len(values['QUERY_SEMANTICS_GUIDANCE'])==2
        and all(isinstance(v,str) and v for v in values['QUERY_SEMANTICS_GUIDANCE']),
        'Malformed frozen semantic prompt constants')
    return dict(policy_id=values['QUERY_SEMANTICS_POLICY'],development_candidate=True,
        scope='advisory_prompt_only',hard_rejection=False,sql_rewriting=False,scoring_policy_changed=False,
        guidance_sha256=hashlib.sha256('\n'.join(values['QUERY_SEMANTICS_GUIDANCE']).encode('utf-8')).hexdigest())


def bundle(root):
    root=Path(root).resolve();row=read(root/'bundle_manifest.json')
    require(row.get('schema')=='m3_e07_pair24_bundle_v2' and row.get('bundle_id')==digest(row['payload']),'Bundle identity differs')
    p=row['payload'];require(p['primary_ids']==PRIMARY and p['observed_ids']==OBSERVED,'Experiment targets differ')
    require(p.get('baseline_reuse_allowed') is False,'This candidate requires a clean, newly generated baseline')
    require(set(p['controllers'])==set(BASE_CONTROLS),'Controller inventory differs')
    require(p.get('categorical_population_policy')==CATEGORICAL_POLICY,
        'Frozen categorical-population policy differs')
    require(p.get('generation_features')=={'baseline':['--categorical-population'],
        'candidate':['--categorical-population','--semantic-planning']},
        'Baseline/candidate generation features differ from the single-variable treatment')
    require(p.get('support_files')==SUPPORT_FILES,'Import support asset inventory differs')
    require(len(p['case_ids'])==len(set(p['case_ids']))==24 and len(p['regression_ids'])==20
            and set(p['regression_ids'])<=set(p['case_ids'])
            and set(p['case_ids'])==set(p['regression_ids']+PRIMARY+OBSERVED)
            and p['maximum_generated_cases']==48 and p['automatic_holdout'] is False,
            'Fixed development24 selection or budget differs')
    verify_files(root,p['files'])
    for side in SIDES:
        info=p['sides'][side]
        require(len(info['code_files'])==103,'Producer inventory size differs')
        for name,entry in info['assets'].items():
            safe(root,name);require(p['files'].get(entry['bundle_path'])==entry['sha256'],'Side asset binding differs')
        require(all(info['assets'].get(n,{}).get('sha256')==value for n,value in info['code_files'].items()),'Producer/asset inventory differs')
        require(all(info['assets'].get(n,{}).get('sha256')==value for n,value in SUPPORT_FILES.items()),'Import support asset binding differs')
        selection=read(safe(root,info['assets'][CASE_LIST]['bundle_path']))
        regression=read(safe(root,info['assets'][REGRESSION]['bundle_path']))
        development=read(safe(root,info['assets']['evaluation/cases/bird_mini_dev/m2_pg_v1/development80.json']['bundle_path']))
        require(selection['case_ids']==p['case_ids'] and set(selection['case_ids'])<=set(development['case_ids'])
            and regression['case_ids']==p['regression_ids'],
            'Selection is not the exact fixed development24 subset')
    old=p['sides']['baseline']['code_files'];new=p['sides']['candidate']['code_files']
    require(p.get('transport_policy',{}).get('policy_id')=='bird_process_dns_transport_v1'
        and p.get('common_adaptation',{}).get('files')==['evaluation/bird/model.py',
            'evaluation/bird/retrieval.py','evaluation/bird/diagnostic_runner.py','evaluation/bird/process_dns.py']
        and all(old[name]==new[name] for name in ('evaluation/bird/model.py','evaluation/bird/process_dns.py')),
        'Common transport adaptation differs')
    require(p.get('dns_readiness_policy')==DNS_READINESS_POLICY,
        'DNS readiness policy differs')
    require(p.get('semantic_planning_policies')=={'baseline':None,'candidate':frozen_semantics_policy(root,p)},
        'Baseline/candidate query-semantic prompt treatment differs')
    require(p.get('case_identity')=='m3_e07_population_grain_revision_development24_v2',
        'Semantic-revision candidate identity differs')
    require(old==new,'Producer code must be byte-identical across the pair')
    require(p['intent_policies']['baseline']==p['intent_policies']['candidate'],
        'Both sides must retain the same E05 advisory intent policy')
    require(all(old[n]==new[n] for n in ('evaluation/bird/model.py','evaluation/bird/process_dns.py')),
        'Common transport code differs')
    return row


def workspace(root):
    root=Path(root).resolve();row=read(root/'workspace.json');manifest=read(root/'control/bundle_manifest.json')
    require(row.get('schema')=='m3_e07_pair24_workspace_v2' and row['bundle_id']==manifest['bundle_id']
            and row['manifest_sha256']==sha(root/'control/bundle_manifest.json'),'Workspace identity differs')
    preparation=read(root/'preparation.json')
    require(preparation.get('workspace_sha256')==sha(root/'workspace.json') and preparation['bundle_id']==row['bundle_id'],'Prepared path/config identity differs')
    p=manifest['payload'];require(digest(p)==manifest['bundle_id'],'Workspace manifest digest differs')
    verify_files(root/'control',p['controllers'])
    for side in SIDES:
        base=root/side/'backend';assets={k:v['sha256'] for k,v in p['sides'][side]['assets'].items()}
        assets.update({'scripts/'+n:p['controllers'][n] for n in ('m3_e07_pair24_common.py','m3_e07_pair24_side.py')})
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
    require(len(copied)==len({v['database_id'] for v in copied}), 'Duplicate development domain indexes')
    return copied


def _tokens(capture):
    total=0
    event_groups=[case.get('budget',{}).get('model_events') for case in capture['cases']]
    event_groups.extend((item.get('model_usage') or {}).get('model_events') for item in capture['index_builds'])
    for events in event_groups:
        if events is None:return None
        for event in events:
            value=(event.get('usage') or {}).get('total_tokens')
            if type(value) is not int:return None
            total+=value
    return total


def _chat_tokens(capture):
    total=0
    for case in capture['cases']:
        events=(case.get('budget') or {}).get('model_events')
        if events is None:return None
        for event in events:
            if event.get('kind')!='chat':continue
            value=(event.get('usage') or {}).get('total_tokens')
            if type(value) is not int:return None
            total+=value
    return total


def _model_requests(capture):
    total=0
    for case in capture['cases']:
        value=(case.get('budget') or {}).get('model_http_attempts')
        if type(value) is not int:return None
        total+=value
    for index in capture['index_builds']:
        usage=index.get('model_usage')
        if usage is None:
            if index.get('cache_hit') is True:continue
            return None
        value=usage.get('model_http_attempts')
        if type(value) is not int:return None
        total+=value
    return total


def _p95(capture):
    values=[c.get('case_wall_seconds') for c in capture['cases']]
    if not all(type(v) in (int,float) and v>=0 for v in values):return None
    return sorted(values)[math.ceil(.95*len(values))-1]


def aggregation_shape(sql):
    """Reviewer-only necessary shape checks; never feedback, scoring or SQL rewriting."""
    try:
        from sqlglot import exp,parse_one
        tree=parse_one(sql,read='postgres')
        return dict(parseable=True,
            group_by_present=any(v.args.get('group') is not None for v in tree.find_all(exp.Select)),
            sum_present=any(True for _ in tree.find_all(exp.Sum)))
    except Exception:
        return dict(parseable=False,group_by_present=False,sum_present=False)


def compare_pair(payload,captures,natives):
    """Compare the complete frozen development split; keep nonanswers in the denominator."""
    a,b=(captures[s] for s in SIDES)
    for key in ('model_configuration','source_binding','schema_selection_policy','sql_repair_policy',
                'case_list_sha256','transport_policy','transport_dependency_binding'):
        require(a[key]==b[key],'Pair comparability differs: '+key)
    require(a['condition_relation_policy']==CATEGORICAL_POLICY
        and b['condition_relation_policy']==CATEGORICAL_POLICY,
        'Both sides must use the same categorical-population policy')
    require(a['intent_candidate_policy']==b['intent_candidate_policy']==payload['intent_policies']['baseline'],
        'Intent policies differ across the pair')
    require(a.get('query_semantic_planning_policy') is None
        and b.get('query_semantic_planning_policy')==payload['semantic_planning_policies']['candidate'],
        'Baseline/candidate query-semantic prompt policy differs')
    for capture in (a,b):
        require(capture['selected_case_ids']==payload['case_ids'] and len(capture['cases'])==24,
                'Pair case order differs')
    ai={i['identity']['source_identity']['logical_database_id']:i for i in a['index_builds']}
    bi={i['identity']['source_identity']['logical_database_id']:i for i in b['index_builds']}
    require(set(ai)==set(bi) and len(ai)==len(payload['index_database_ids']),'Pair index domains differ')
    for db in ai:
        require(ai[db]['identity']['source_identity']==bi[db]['identity']['source_identity'],
                'Index source identity differs: '+db)
        require(Path(ai[db]['path']).resolve()!=Path(bi[db]['path']).resolve(),
                'Baseline/candidate indexes are not isolated: '+db)
    outcome={s:{v['case_id']:v['native_comparison']['matches_frozen_gold'] for v in natives[s]['cases']}
             for s in SIDES}
    rows=[]
    for i,rid in enumerate(payload['case_ids']):
        left,right=a['cases'][i],b['cases'][i]
        require(left['case_id']==right['case_id']==rid and left['database_id']==right['database_id'],
                'Pair per-case identity differs')
        if left.get('source_identity') is not None and right.get('source_identity') is not None:
            require(left['source_identity']==right['source_identity'],'Pair per-case source differs')
        if left.get('query_role') is not None and right.get('query_role') is not None:
            require(left['query_role']==right['query_role'],'Pair per-case role differs')
        require(left.get('query_semantic_planning_policy') is None
            and right.get('query_semantic_planning_policy')==payload['semantic_planning_policies']['candidate'],
            'Per-case semantic-planning treatment differs')
        lrec=(left.get('development_diagnostics') or {}).get('retrieval') or {}
        rrec=(right.get('development_diagnostics') or {}).get('retrieval') or {}
        gl=(lrec.get('schema_graph') or {}).get('value') or {}
        gr=(rrec.get('schema_graph') or {}).get('value') or {}
        same_schema=(gl.get('fields') is not None and gr.get('fields') is not None
            and [f['id'] for f in gl['fields']]==[f['id'] for f in gr['fields']]
            and gl.get('joins')==gr.get('joins')
            and gl.get('condition_relation_context')==gr.get('condition_relation_context'))
        candidate_fields={f['id'] for f in gr.get('fields',[])}
        baseline_fields={f['id'] for f in gl.get('fields',[])}
        admitted=(gr.get('condition_relation_context') or {}).get('admitted_public_conditions',[])
        left_admitted=(gl.get('condition_relation_context') or {}).get('admitted_public_conditions',[])
        baseline_category=next((v for v in left_admitted if v.get('role')=='public_categorical_population_condition'),None)
        category_condition=next((v for v in admitted if v.get('role')=='public_categorical_population_condition'),None)
        rows.append(dict(case_id=rid,database_id=left['database_id'],same_authorized_schema=same_schema,
            baseline_field_ids=sorted(baseline_fields),candidate_field_ids=sorted(candidate_fields),
            candidate_added_field_ids=sorted(candidate_fields-baseline_fields),
            baseline_correct=outcome['baseline'].get(rid,False),candidate_correct=outcome['candidate'].get(rid,False),
            baseline_status=left['status'],candidate_status=right['status'],
            baseline_generated_sql=left.get('generated_sql'),candidate_generated_sql=right.get('generated_sql'),
            candidate_aggregation_shape=aggregation_shape(right.get('generated_sql') or ''),
            candidate_intent_contract=right.get('intent_contract'),
            baseline_categorical_condition=baseline_category,
            candidate_categorical_condition=category_condition,
            candidate_validation_events=right.get('validation_events',[]),
            baseline_budget=left.get('budget'),candidate_budget=right.get('budget')))
    bm=sum(v['baseline_correct'] for v in rows);cm=sum(v['candidate_correct'] for v in rows)
    regression20=set(payload['regression_ids'])
    retained20=sum(v['candidate_correct'] for v in rows if v['case_id'] in regression20)
    regression_ids=[v['case_id'] for v in rows if v['case_id'] in regression20 and not v['candidate_correct']]
    tokens={s:_tokens(captures[s]) for s in SIDES}
    chat_tokens={s:_chat_tokens(captures[s]) for s in SIDES}
    requests={s:_model_requests(captures[s]) for s in SIDES}
    latency={s:_p95(captures[s]) for s in SIDES}
    costs_known=all(v is not None for v in [*tokens.values(),*chat_tokens.values(),*requests.values(),*latency.values()])
    chat_within_20=costs_known and chat_tokens['candidate']<=chat_tokens['baseline']*1.2
    p95_within_20=costs_known and latency['candidate']<=latency['baseline']*1.2
    target=next(v for v in rows if v['case_id']=='BIRD-PG-1480')
    observed={v['case_id']:v for v in rows if v['case_id'] in OBSERVED}
    controls_unchanged=all(observed[cid]['same_authorized_schema']
        and observed[cid]['baseline_categorical_condition']==observed[cid]['candidate_categorical_condition']
        for cid in OBSERVED)
    expected_added={'debit_card_specializing.customers.customerid','debit_card_specializing.customers.segment'}
    observed_condition=target.get('candidate_categorical_condition') or {}
    baseline_condition=target.get('baseline_categorical_condition') or {}
    target_has_fields=(expected_added<=set(target['baseline_field_ids'])
        and expected_added<=set(target['candidate_field_ids']))
    target_condition=(observed_condition.get('field_id')=='debit_card_specializing.customers.segment'
        and observed_condition.get('value')=='SME' and observed_condition.get('mandatory') is False)
    baseline_target_condition=(baseline_condition.get('field_id')=='debit_card_specializing.customers.segment'
        and baseline_condition.get('value')=='SME' and baseline_condition.get('mandatory') is False)
    candidate_sql=(target.get('candidate_generated_sql') or '').lower()
    checks=dict(target_1480_native_correct=target['candidate_correct'],
        target_1480_authorized_context_available_both_sides=target_has_fields and target_condition and baseline_target_condition,
        semantic_treatment_isolated=all(v['same_authorized_schema'] for v in rows),
        target_1480_sql_mentions_category_field='segment' in candidate_sql,
        target_1480_group_and_sum_present=target['candidate_aggregation_shape']['group_by_present']
            and target['candidate_aggregation_shape']['sum_present'],
        observed_controls_recorded=set(observed)==set(OBSERVED),
        observed_controls_context_unchanged=controls_unchanged,
        no_observed_control_regression=all(not observed[cid]['baseline_correct'] or observed[cid]['candidate_correct'] for cid in OBSERVED),
        regression20_retained=retained20==20,
        cost_known=costs_known,chat_tokens_within_20_percent=chat_within_20,
        case_p95_within_20_percent=p95_within_20)
    by_database={db:{s:sum(v[s+'_correct'] for v in rows if v['database_id']==db) for s in SIDES}
                 for db in sorted({v['database_id'] for v in rows})}
    return dict(case_count=24,fixed_denominator=24,baseline_match_count=bm,candidate_match_count=cm,
        net_gain=cm-bm,
        wrong_to_right=[v['case_id'] for v in rows if not v['baseline_correct'] and v['candidate_correct']],
        right_to_wrong=[v['case_id'] for v in rows if v['baseline_correct'] and not v['candidate_correct']],
        regression20_failed_ids=regression_ids,
        regression20_retained_count=retained20,
        schema_context_changed_case_ids=[v['case_id'] for v in rows if not v['same_authorized_schema']],
        primary_target_ids=PRIMARY,observed_diagnostic_ids=OBSERVED,
        total_model_tokens_including_index_builds=tokens,chat_tokens=chat_tokens,
        model_http_attempts_including_index_builds=requests,case_wall_p95_seconds=latency,
        index_policy='Each side builds and validates its own source-bound index; no cross-side cache sharing.',
        screening=checks,automatic_screen_pass=all(checks.values()),
        acceptance='manual_semantic_review_required',business_review_required=sorted(set(PRIMARY+OBSERVED+regression_ids)),
        categorical_population_case_ids=PRIMARY,observed_control_ids=OBSERVED,
        generation_features=payload['generation_features'],
        formal_benchmark=False,holdout_run=False,by_database=by_database,cases=rows,
        meaning='One controlled development24 screening comparison. Nonanswers count as failures; no formal or unseen holdout claim.')
