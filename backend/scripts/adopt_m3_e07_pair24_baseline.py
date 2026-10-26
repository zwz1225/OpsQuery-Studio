"""Adopt a completed, policy-compatible baseline capture without regenerating it."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys

if __package__:
    from . import m3_e07_pair24_common as c
else:
    import m3_e07_pair24_common as c


def adopt(target_root,source_root):
    target_root=Path(target_root).resolve();source_root=Path(source_root).resolve()
    row,payload=c.workspace(target_root)
    c.require(not source_root.is_relative_to(target_root) and not target_root.is_relative_to(source_root),
        'Source and recovery workspaces must be separate')
    prior_module=source_root/'control/m3_e07_pair24_common.py'
    spec=importlib.util.spec_from_file_location('m3_e07_prior_common',prior_module)
    c.require(spec is not None and spec.loader is not None,'Prior control module is missing')
    prior_common=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior_common)
    source_row,source_payload=prior_common.workspace(source_root)
    c.require(source_row['bundle_id']==payload['recoverable_prior_bundle_id'],
        'Prior workspace is not the frozen recoverable attempt')
    prior=c.read(source_root/'reports/e07_pair24_server.json')
    c.require(prior.get('run_status')=='failed' and prior.get('phase')=='baseline_capture_integrity'
        and prior.get('generation_reserved') is True,
        'Prior attempt did not stop at baseline capture integrity')
    c.require(prior.get('child_exit_codes',{}).get('baseline_generation')==0
        and prior.get('child_exit_codes',{}).get('baseline_capture_integrity')==1
        and 'candidate_generation' not in prior.get('child_exit_codes',{}),
        'Prior attempt started another generation side')
    source_capture=source_root/'baseline/backend/evaluation/results/m3_e07_pair24_baseline_capture_server.json'
    capture=c.read(source_capture)
    recorded=(prior.get('generation_failure_evidence') or {}).get('baseline') or {}
    c.require(capture.get('run_status')=='complete' and capture.get('selected_case_ids')==payload['case_ids']
        and len(capture.get('cases',[]))==24 and capture.get('new_model_request_count')==128
        and recorded.get('run_status')=='complete' and recorded.get('sha256')==c.sha(source_capture),
        'Prior baseline capture is incomplete or has another fixed selection')
    c.require(capture.get('code_binding',{}).get('files')==payload['sides']['baseline']['code_files']
        and capture.get('intent_candidate_policy')==payload['intent_policies']['baseline']
        and capture.get('condition_relation_policy')==c.BASE_RELATION_POLICY
        and capture.get('model_configuration')==payload['model_configuration']
        and capture.get('source_binding')==payload['source_binding']
        and capture.get('case_list_sha256')==c.sha(c.side_base(target_root,'baseline')/c.CASE_LIST),
        'Baseline capture identity/policies differ from corrected candidate freeze')
    prior_lock=c.read(source_root/'transport_dependency_lock.json')
    target_lock=c.read(target_root/'transport_dependency_lock.json')
    c.require(prior_lock.get('bundle_id')==source_row['bundle_id']
        and prior_lock.get('binding')==target_lock.get('binding'),
        'Recorded process-DNS dependency differs across workspaces')
    old_receipt=c.read(source_root/'transport_model_probe_receipt.json')
    child_source=Path(old_receipt['child_report_path']).resolve()
    c.require(child_source.is_relative_to(source_root/'reports')
        and c.sha(child_source)==old_receipt.get('child_report_sha256'),
        'Prior bounded transport-probe evidence changed')
    child_report=c.read(child_source);probe=child_report.get('result') or {}
    c.require(old_receipt.get('bundle_id')==source_row['bundle_id'] and old_receipt.get('passed') is True
        and old_receipt.get('binding')==target_lock['binding']
        and old_receipt.get('model_configuration')==payload['model_configuration']
        and child_report.get('run_status')=='complete' and child_report.get('mode')=='model-probe'
        and probe.get('passed') is True and probe.get('transport_dependency_binding')==target_lock['binding'],
        'Prior bounded model probe is not reusable')
    target_capture=c.side_base(target_root,'baseline')/'evaluation/results/m3_e07_pair24_baseline_capture_server.json'
    c.require(not target_capture.exists() and not (target_root/'baseline_reuse_receipt.json').exists()
        and not (target_root/'transport_model_probe_receipt.json').exists(),
        'Recovery workspace already contains adopted evidence')
    c.copy_new(source_capture,target_capture,c.sha(source_capture))
    child_target=target_root/'reports/reused_transport_model_probe_server.json'
    c.copy_new(child_source,child_target,c.sha(child_source))
    c.write_new(target_root/'transport_model_probe_receipt.json',dict(bundle_id=row['bundle_id'],
        binding=target_lock['binding'],model_configuration=payload['model_configuration'],passed=True,
        adopted_from_bundle_id=source_row['bundle_id'],child_report_path=str(child_target),
        child_report_sha256=c.sha(child_target),new_model_request_count=0))
    result=dict(stage='M3 E07 baseline capture evidence adoption',run_status='complete',
        target_bundle_id=row['bundle_id'],source_bundle_id=source_row['bundle_id'],
        source_capture_sha256=c.sha(source_capture),baseline_capture_path=str(target_capture),
        source_probe_receipt_sha256=c.sha(source_root/'transport_model_probe_receipt.json'),
        source_probe_report_sha256=old_receipt['child_report_sha256'],
        adopted_probe_report_sha256=c.sha(child_target),baseline_generation_reused=True,
        prior_baseline_model_http_attempts=capture['new_model_request_count'],
        new_model_request_count=0,postgresql_connected=False,model_called=False)
    c.write_new(target_root/'baseline_reuse_receipt.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--source-workspace',type=Path,required=True)
    args=parser.parse_args()
    try:print(c.json.dumps(adopt(args.workspace,args.source_workspace),ensure_ascii=False,indent=2))
    except Exception as error:
        print(str(error) if isinstance(error,c.PairError) else 'Baseline adoption failed; preserve both workspaces',file=sys.stderr)
        raise SystemExit(1)


if __name__=='__main__':main()
