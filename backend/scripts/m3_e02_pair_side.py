"""Trusted static/capture/native checks executed inside one exact producer directory."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from . import m3_e02_pair_common as c

BASE=Path(__file__).resolve().parents[1]


def failure(error):
    """Only controlled messages/producer frame locations, never locals or input values."""
    controlled=isinstance(error,c.PairError) or (type(error).__name__=='PreparationError'
        and type(error).__module__=='scripts.m2_b_common')
    result=dict(type=type(error).__name__,message=str(error) if controlled else 'Side check failed; raw private details omitted')
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
    c.require(ids==payload['case_ids'],'Selected development24 order differs')
    c.require(Path(row['credentials_file']).is_file(),'M2 credential file is missing')
    return row,payload,side,binding,evidence


def probe(native_only=False):
    row,payload,side,binding,evidence=context()
    model=payload['model_configuration']
    if not native_only:
        from evaluation.bird.model import ModelConfig
        model=ModelConfig.load(Path(row['model_config_file'])).public()
        c.require(model==payload['model_configuration'],'Public model configuration differs')
    return dict(side=side,code_binding=binding,source_binding=payload['source_binding'],
        model_configuration=model,model_configuration_checked=not native_only,
        selected_case_ids=payload['case_ids'],new_model_request_count=0,postgresql_connected=False,
        live_target_verified=False,scope='Static identities only; fresh runtime/ACL/content and isolation checks precede generation')


def capture(path):
    row,payload,side,binding,evidence=context()
    from evaluation.bird.intent_replay import load_candidate_capture
    report,pairs,excluded=load_candidate_capture(path,evidence,c.sha(path))
    c.require(report['selected_case_ids']==payload['case_ids'] and len(report['cases'])==24
        and report['case_list_sha256']==c.sha(BASE/c.CASE_LIST),'Capture does not cover exact development24')
    for key in ('model_configuration','schema_selection_policy','sql_repair_policy','intent_candidate_policy'):
        c.require(report[key]==payload[key],'Capture configuration differs: '+key)
    c.require(report.get('workers')==1,'Worker count differs')
    c.require('public_output_contract_policy' not in report
        and all('public_output_contract_policy' not in r for r in report['cases']),
        'Output contract must be disabled on both sides')
    if side=='baseline':
        c.require('condition_relation_policy' not in report
            and all('condition_relation_policy' not in r for r in report['cases']),
            'Baseline must not contain E02 condition/relation treatment')
    else:
        from evaluation.bird.demand_relations import policy
        expected=policy();c.require(report.get('condition_relation_policy')==expected,'Candidate condition/relation policy missing')
        for case in report['cases']:
            if not case.get('agent_started'):continue
            c.require(case.get('condition_relation_policy')==expected,'Candidate per-case E02 treatment missing')
            record=case['development_diagnostics']['retrieval']['schema_graph']
            c.require(record['complete'] is True,'Candidate Schema diagnostic incomplete')
            graph=record['value']
            c.require(isinstance(graph.get('condition_relation_context'),dict),
                'Candidate graph lacks E02 condition/relation context')
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


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['probe','capture','native'],required=True)
    p.add_argument('--native-only',action='store_true')
    p.add_argument('--capture',type=Path)
    p.add_argument('--native',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    try:
        if args.mode=='probe':result=probe(args.native_only)
        elif args.mode=='capture':
            report,pairs,excluded=capture(args.capture)
            result=dict(case_count=24,answered_count=len(pairs),nonanswer_count=len(excluded),capture_sha256=c.sha(args.capture))
        else:
            report=native(args.native,args.capture);result=dict(summary=report['summary'],native_sha256=c.sha(args.native))
        c.write_new(args.output,dict(run_status='complete',mode=args.mode,result=result,new_model_request_count=0,postgresql_connected=False))
    except (Exception,KeyboardInterrupt) as error:
        detail=failure(error)
        c.write_new(args.output,dict(run_status='failed',mode=args.mode,new_model_request_count=0,postgresql_connected=False,
            errors=[detail]))
        print(json.dumps(detail,ensure_ascii=False),file=sys.stderr)
        raise SystemExit(1)


if __name__=='__main__':main()
