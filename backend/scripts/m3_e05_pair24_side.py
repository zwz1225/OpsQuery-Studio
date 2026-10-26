"""Trusted static/capture/native checks executed inside one exact producer directory."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import sys

from . import m3_e05_pair24_common as c

BASE=Path(__file__).resolve().parents[1]


def failure(error):
    """Only controlled messages/producer frame locations, never locals or input values."""
    controlled=isinstance(error,c.PairError) or (type(error).__name__=='PreparationError'
        and type(error).__module__=='scripts.m2_b_common')
    result=dict(type=type(error).__name__,message=str(error) if controlled else 'Side check failed; raw private details omitted')
    category=getattr(error,'category',None)
    if isinstance(category,str) and re.fullmatch('[a-z0-9_]{1,80}',category):result['category']=category
    detail=getattr(error,'_transport_dependency',None)
    if isinstance(detail,dict):result['transport_dependency']=detail
    frames=[];tb=error.__traceback__
    while tb is not None:
        path=Path(tb.tb_frame.f_code.co_filename).resolve()
        if path.is_relative_to(BASE):
            frames.append(dict(file=path.relative_to(BASE).as_posix(),line=tb.tb_lineno,function=tb.tb_frame.f_code.co_name))
        tb=tb.tb_next
    if frames:result['producer_frames']=frames
    if isinstance(error,FileNotFoundError):
        result['missing_input']=True
        raw=getattr(error,'filename',None)
        if raw:
            path=Path(raw).resolve()
            if path.is_relative_to(BASE):result['missing_relative_path']=path.relative_to(BASE).as_posix()
            else:result['missing_path_scope']='outside_producer_directory; private path omitted'
    return result


def context():
    side_context=c.read(BASE/'m3_context.json');root=Path(side_context['workspace'])
    row,payload=c.workspace(root);side=side_context['side']
    c.require(BASE==c.side_base(root,side).resolve(),'Wrong side working directory')
    from evaluation.bird.manifest import code_binding,source_binding
    from evaluation.bird.evidence import Evidence
    from evaluation.bird.diagnostic_runner import prerequisites,select_development
    from scripts.m2_b_target import live_dependencies
    from importlib.metadata import version
    live_dependencies();c.require(version('sqlglot')=='30.17.0','SQLGlot pin differs')
    binding=code_binding();c.require(binding['files']==payload['sides'][side]['code_files'],'Actual producer inventory differs')
    evidence=Evidence.load(Path(row['data_root']),BASE/'evaluation/results')
    c.require(source_binding(evidence)==payload['source_binding'],'Source/protocol/permission/budget identity differs')
    prerequisites(*[BASE/'evaluation/results'/name for name in
        ('m2_c_bird_development80_server.json','m2_c_bird_runtime_server.json','m2_c_bird_gold110_server.json')],evidence)
    ids=[r['case_id'] for r in select_development(BASE/c.CASE_LIST)]
    c.require(ids==payload['case_ids'] and len(ids)==24,'Selected development24 order differs')
    c.require(Path(row['credentials_file']).is_file(),'M2 credential file is missing')
    return row,payload,side,binding,evidence


def probe(native_only=False):
    row,payload,side,binding,evidence=context()
    model=payload['model_configuration']
    if not native_only:
        from evaluation.bird.model import ModelConfig
        model=ModelConfig.load(Path(row['model_config_file'])).public()
        c.require(model==payload['model_configuration'],'Public model configuration differs')
    from evaluation.bird.model import TRANSPORT_POLICY
    c.require(TRANSPORT_POLICY==payload['transport_policy'],'Transport policy differs')
    from evaluation.bird.process_dns import tool_binding
    dependency=tool_binding()
    return dict(side=side,code_binding=binding,source_binding=payload['source_binding'],
        model_configuration=model,model_configuration_checked=not native_only,
        selected_case_ids=payload['case_ids'],transport_policy=TRANSPORT_POLICY,transport_dependency_binding=dependency,
        new_model_request_count=0,postgresql_connected=False,
        live_target_verified=False,scope='Static identities only; fresh runtime/ACL/content and isolation checks precede generation')


def capture(path):
    row,payload,side,binding,evidence=context()
    from evaluation.bird.intent_replay import load_candidate_capture
    report,pairs,excluded=load_candidate_capture(path,evidence,c.sha(path))
    c.require(report['selected_case_ids']==payload['case_ids'] and len(report['cases'])==24
        and report['case_list_sha256']==c.sha(BASE/c.CASE_LIST),'Capture does not cover exact development24')
    for key in ('model_configuration','schema_selection_policy','sql_repair_policy'):
        c.require(report[key]==payload[key],'Capture configuration differs: '+key)
    c.require(report['intent_candidate_policy']==payload['intent_policies'][side],
        'Capture E05 intent policy differs')
    c.require(report.get('workers')==1,'Worker count differs')
    c.require(report.get('transport_policy')==payload['transport_policy'],'Capture transport policy differs')
    from evaluation.bird.process_dns import recorded_binding
    dependency=recorded_binding()
    c.require(dependency and report.get('transport_dependency_binding')==dependency,'Capture dependency binding differs')
    c.require(len(report.get('preparation_attempts',[]))==8 and all(a.get('complete') is True
        for a in report['preparation_attempts']),'Index preparation attempt records incomplete')
    prep=sum(a['model_usage']['model_http_attempts'] for a in report['preparation_attempts'])
    cases=sum(case['budget']['model_http_attempts'] for case in report['cases'])
    groups=[a['model_usage']['model_events'] for a in report['preparation_attempts']]
    groups.extend(case['budget']['model_events'] for case in report['cases'])
    for events in groups:
        c.require(all(event.get('transport_dependency_binding')==dependency and 'process_dns' in event
            for event in events),'Model events lack the locked explicit DNS identity')
    c.require(all(i['identity'].get('transport_identity',{}).get('dependency')==dependency
        for i in report['index_builds']),'Index transport identity differs')
    c.require(report.get('preparation_model_http_attempts')==prep
        and report['summary']['shared_index_http_attempts']==prep
        and report.get('new_model_request_count')==prep+cases,'Capture total model attempts differ')
    c.require('public_output_contract_policy' not in report
        and all('public_output_contract_policy' not in r for r in report['cases']),
        'E03 output treatment must be absent from both sides')
    from evaluation.bird.demand_relations import policy as relation_policy
    expected=relation_policy()
    c.require(report.get('condition_relation_policy')==expected,
        'Both sides must retain the same accepted E02 condition/relation policy')
    for case in report['cases']:
        if not case.get('agent_started'):continue
        c.require(case.get('condition_relation_policy')==expected
            and 'public_output_contract_policy' not in case,
            'Per-case E02 treatment missing or E03 treatment leaked')
        record=case['development_diagnostics']['retrieval']['schema_graph']
        c.require(record['complete'] is True,'Schema diagnostic incomplete')
        graph=record['value']
        c.require(isinstance(graph.get('condition_relation_context'),dict),
            'Graph lacks E02 condition/relation context')
        intent=case.get('intent_contract') or {}
        if side=='candidate':
            c.require((intent.get('explicit_endpoint_scope') or {}).get('policy')==payload['endpoint_scope_policy'],
                'Candidate E05 endpoint policy missing')
            if case['case_id']=='BIRD-PG-0239':
                endpoint=intent['explicit_endpoint_scope']
                c.require(endpoint['basis']=='public_evidence_explicit_like_endpoint_and_metric'
                    and endpoint['predicate_field_id']=='toxicology.connected.atom_id'
                    and endpoint['metric_field_id']=='toxicology.connected.bond_id'
                    and endpoint['enforcement']=='advisory_only',
                    'Target 0239 public endpoint contract missing')
        else:
            c.require('explicit_endpoint_scope' not in intent,'Baseline was contaminated with E05 treatment')
    c.require(len(pairs)+len(excluded)==24,'Native denominator differs')
    return report,pairs,excluded


def native(path,capture_path):
    row,payload,side,binding,evidence=context()
    source,pairs,excluded=capture(capture_path);report=c.read(path)
    ids=[case['case_id'] for case,gold in pairs];summary=report.get('summary') or {}
    c.require(report.get('run_status')=='complete' and report.get('errors')==[]
        and report.get('native_comparisons_complete') is True and report.get('pools_closed') is True
        and report.get('target_data_verified') is True and report.get('source_report_sha256')==c.sha(capture_path)
        and report.get('code_binding')==binding and report.get('source_binding')==payload['source_binding']
        and report.get('new_model_request_count')==0 and report.get('formal_benchmark') is False
        and report.get('primary_ex') is None and report.get('holdout_live_allowed') is False,'Native identity/termination differs')
    c.require(report['selected_case_ids']==ids and [r['case_id'] for r in report['cases']]==ids
        and report['excluded_cases']==excluded and report['source_case_count']==24,'Native cases omitted, duplicated or reordered')
    c.require(summary['source_case_count']==summary['development_subset_case_count']==24
        and summary['replayed_case_count']==len(pairs) and summary['excluded_case_count']==len(excluded)
        and summary['new_model_request_count']==0,'Native denominator/model budget differs')
    matches=0
    for case,(saved,gold) in zip(report['cases'],pairs):
        c.require(case['source_identity']==saved['source_identity'] and case['query_role']==saved['query_role']
            and case['generated_sql_sha256']==hashlib.sha256(saved['generated_sql'].encode()).hexdigest()
            and case['gold_sql_sha256']==gold['gold_sql_sha256'] and case['captured_native_diagnostic_preserved'] is True
            and case['new_model_request_count']==0 and case['budget']['sql_tool_calls']==2,'Native per-case source/result evidence differs')
        c.require(type(case['native_comparison']['matches_frozen_gold']) is bool,'Invalid native outcome')
        matches+=case['native_comparison']['matches_frozen_gold']
    c.require(summary['native_match_count']==matches and summary['native_mismatch_count']==len(pairs)-matches
        and summary['development_subset_native_match_rate']==matches/24,'Native summary differs')
    return report


def connection_probe():
    row,payload,side,binding,evidence=context()
    from evaluation.bird.model import ModelConfig
    from evaluation.bird.process_dns import readiness
    from evaluation.bird.budgets import hard_deadline
    configuration=ModelConfig.load(Path(row['model_config_file'])).public()
    c.require(configuration==payload['model_configuration'],'Public model configuration differs')
    with hard_deadline(60,'transport_preflight_timeout'):
        result=readiness(configuration)
    result['side']=side
    return result


def model_probe():
    row,payload,side,binding,evidence=context()
    from evaluation.bird.model import Models,ModelConfig
    from evaluation.bird.process_dns import recorded_binding
    from evaluation.bird.budgets import Budget
    c.require(side=='baseline','Transport smoke uses baseline shared code only')
    config=ModelConfig.load(Path(row['model_config_file']))
    c.require(config.public()==payload['model_configuration'],'Model smoke configuration differs')
    dependency=recorded_binding();budget=Budget(wall_seconds=180,total_limit=2,chat_limit=0)
    producer_context=c.read(BASE/'m3_context.json')
    reservation=Path(producer_context['workspace'])/'transport_model_probe_attempt.json'
    c.write_new(reservation,dict(bundle_id=producer_context['bundle_id'],
        started_at=c.now(),maximum_model_http_attempts=2,question_data_used=False,generation_reserved=False))
    result=dict(side=side,new_model_request_count=0,postgresql_connected=False,
        generation_reserved=False,question_data_used=False,transport_dependency_binding=dependency)
    try:
        vectors=Models(config,budget).embed(['Authorized schema field connectivity probe '+str(i) for i in range(10)])
        result.update(passed=len(vectors)==10 and all(len(v)==1024 for v in vectors),vector_count=len(vectors),
            dimensions=sorted({len(v) for v in vectors}))
    except Exception as error:
        result.update(passed=False,error=failure(error))
    finally:
        result.update(new_model_request_count=budget.total_attempts,budget=budget.public())
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['probe','capture','native','connection','model-probe'],required=True)
    p.add_argument('--native-only',action='store_true')
    p.add_argument('--capture',type=Path)
    p.add_argument('--native',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    try:
        if args.mode=='probe':result=probe(args.native_only)
        elif args.mode=='connection':result=connection_probe()
        elif args.mode=='model-probe':result=model_probe()
        elif args.mode=='capture':
            report,pairs,excluded=capture(args.capture)
            result=dict(case_count=24,answered_count=len(pairs),nonanswer_count=len(excluded),capture_sha256=c.sha(args.capture))
        else:
            report=native(args.native,args.capture);result=dict(summary=report['summary'],native_sha256=c.sha(args.native))
        c.write_new(args.output,dict(run_status='complete',mode=args.mode,result=result,
            new_model_request_count=result.get('new_model_request_count',0),postgresql_connected=False))
    except (Exception,KeyboardInterrupt) as error:
        detail=failure(error)
        c.write_new(args.output,dict(run_status='failed',mode=args.mode,
            new_model_request_count=None if args.mode=='model-probe' else 0,postgresql_connected=False,
            errors=[detail]))
        print(json.dumps(detail,ensure_ascii=False),file=sys.stderr)
        raise SystemExit(1)


if __name__=='__main__':main()
