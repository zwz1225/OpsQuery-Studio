"""Development-only model observation run. Old evidence is provenance, not current readiness."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import tempfile
import time
import uuid

from scripts.m2_b_common import BASE, PROTOCOL_DIR, digest_file, require, write_new_json
from scripts.m2_b_target import DEFAULT_CREDENTIALS, journal, live_dependencies
from scripts.check_m2_c_bird_runtime import budget_checks
from .budgets import BirdFailure
from .evidence import Evidence, DEFAULT_DATA, DEFAULT_RESULTS, public_cases
from .manifest import code_binding, source_binding
from .model import ModelConfig, TRANSPORT_POLICY,recorded_binding
from .runtime import BirdRegistry, fault
from .retrieval import build_index
from .supervisor import isolation_probe, run_case_process
from .repair import POLICY as REPAIR_POLICY
from .coverage import contract as coverage_contract

ACCEPTED_BASELINE_SHA='7f59478b5d589a49d85027e965e8b3596416ac998df4618c655984841fc8c01d'
ACCEPTED_RUNTIME_SHA='ecaf50f6c7a17460dd6260a9dcf198f91fcf33e397e581c16aa82a55d7d63473'
ACCEPTED_GOLD_SHA='e87dc6e51833eaa22344c0882ac49109822cbd0bff6526eda05a361c7cf8ea03'
DEFAULT_CASES=BASE/'evaluation/cases/bird_mini_dev/m2_development_diagnostics14.json'


def prerequisites(baseline_path,runtime_path,gold_path,evidence):
    """Exact previously reviewed bytes; current live checks are performed separately."""
    for path,sha in ((baseline_path,ACCEPTED_BASELINE_SHA),(runtime_path,ACCEPTED_RUNTIME_SHA),(gold_path,ACCEPTED_GOLD_SHA)):
        require(digest_file(path)==sha,'Recorded diagnostic prerequisite differs from accepted bytes')
    baseline=json.loads(baseline_path.read_bytes());runtime=json.loads(runtime_path.read_bytes());gold=json.loads(gold_path.read_bytes())
    require(baseline['source_binding']==runtime['source_binding']==gold['source_binding']==source_binding(evidence),'Recorded source differs')
    require(baseline['code_binding']==runtime['code_binding']==gold['code_binding'],'Recorded prerequisite code chain differs')
    require(baseline['runtime_report_sha256']==ACCEPTED_RUNTIME_SHA and baseline['gold_readiness_report_sha256']==ACCEPTED_GOLD_SHA
            and baseline['split']=='development80' and len(baseline['cases'])==80,'Recorded baseline identity differs')
    return baseline


def select_development(path):
    payload=json.loads(path.read_bytes());ids=payload.get('case_ids')
    require(isinstance(ids,list) and 0<len(ids)<=80 and all(isinstance(cid,str) for cid in ids)
            and len(ids)==len(set(ids)),'Choose unique nonempty development case IDs')
    allowed={c['case_id']:c for c in public_cases('development80')}
    require(set(ids)<=set(allowed),'Diagnostic runner accepts development80 IDs only; holdout is refused')
    return [allowed[cid] for cid in ids]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=DEFAULT_DATA)
    parser.add_argument('--results-dir',type=Path,default=DEFAULT_RESULTS)
    parser.add_argument('--credentials-file',type=Path,default=DEFAULT_CREDENTIALS)
    parser.add_argument('--model-config-file',type=Path,default=BASE/'.env')
    parser.add_argument('--baseline-report',type=Path,default=DEFAULT_RESULTS/'m2_c_bird_development80_server.json')
    parser.add_argument('--runtime-report',type=Path,default=DEFAULT_RESULTS/'m2_c_bird_runtime_server.json')
    parser.add_argument('--gold-report',type=Path,default=DEFAULT_RESULTS/'m2_c_bird_gold110_server.json')
    parser.add_argument('--case-list',type=Path,default=DEFAULT_CASES)
    parser.add_argument('--index-root',type=Path,default=BASE/'data/bird_indexes/m2_bird_pg_v1')
    parser.add_argument('--save-snapshot',action='store_true')
    parser.add_argument('--schema-coverage',action='store_true',help='Enable versioned development-only authorized Schema coverage candidate')
    parser.add_argument('--intent-candidate',action='store_true',help='Development-only public intent, bounded field groups and canonical literals; consumes existing SQL budget')
    parser.add_argument('--semantic-planning',action='store_true',help='Development-only advisory aggregation-grain and requested-output-order guidance; requires --intent-candidate')
    parser.add_argument('--output-contract',action='store_true',help='M3 development-only public output hints and passive observations; requires --intent-candidate')
    parser.add_argument('--condition-relations',action='store_true',help='M3 E02 development-only condition/key closure; requires schema coverage and intent, excludes output contract')
    parser.add_argument('--relation-output',action='store_true',help='M3 E03 development-only incomplete relation and public output candidate; requires condition relations and output contract')
    parser.add_argument('--categorical-population',action='store_true',help='M3 development-only source-reviewed category/owner key closure; requires condition relations and excludes relation output')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output_contract and not args.intent_candidate:
        parser.error('--output-contract requires --intent-candidate')
    if args.semantic_planning and not args.intent_candidate:
        parser.error('--semantic-planning requires --intent-candidate')
    if args.condition_relations and (not args.schema_coverage or not args.intent_candidate or args.output_contract and not args.relation_output):
        parser.error('--condition-relations requires --schema-coverage --intent-candidate; --output-contract also requires --relation-output')
    if args.relation_output and (not args.condition_relations or not args.output_contract):
        parser.error('--relation-output requires --condition-relations --output-contract')
    if args.categorical_population and (not args.condition_relations or args.relation_output or args.output_contract):
        parser.error('--categorical-population requires --condition-relations and excludes output/relation-output')
    protected=[args.data_root,PROTOCOL_DIR,args.credentials_file,args.model_config_file,args.case_list,args.baseline_report,
        args.runtime_report,args.gold_report,args.index_root]+[args.results_dir/n for n in
        ('m2_b_postgres_validation_server.json','m2_b_postgres_import_server.json','m2_b_postgres_initialization_server.json')]
    stage='M3 E01 public output contract development diagnostics; not a formal EX benchmark' if args.output_contract else 'M2 development diagnostics; not a formal EX benchmark'
    if args.condition_relations:stage='M3 E02 public condition/relation development diagnostics; not a formal EX benchmark'
    if args.relation_output:stage='M3 E03 reviewed incomplete relation and public output development diagnostics; not a formal EX benchmark'
    if args.categorical_population:stage='M3 categorical population condition development diagnostics; not a formal EX benchmark'
    if args.semantic_planning:stage='M3 advisory query semantic planning diagnostics; not a formal EX benchmark'
    with journal(args.output,stage,protected=protected) as report:
        live_dependencies();evidence=Evidence.load(args.data_root,args.results_dir)
        require(not args.index_root.resolve().is_relative_to(args.data_root.resolve())
                and not args.index_root.resolve().is_relative_to(PROTOCOL_DIR.resolve()),'Index output overlaps protected source/protocol')
        baseline=prerequisites(args.baseline_report,args.runtime_report,args.gold_report,evidence)
        cases=select_development(args.case_list);config=ModelConfig.load(args.model_config_file)
        report.update(mode='diagnostic',split='development_diagnostic_subset',formal_benchmark=False,primary_ex=None,
            gold_executed=False,holdout_live_allowed=False,source_binding=source_binding(evidence),code_binding=code_binding(),
            baseline_report_sha256=digest_file(args.baseline_report),recorded_runtime_sha256=digest_file(args.runtime_report),
            recorded_gold_readiness_sha256=digest_file(args.gold_report),recorded_prerequisite_code_sha256=baseline['code_binding']['sha256'],
            prerequisite_scope='Accepted historical source evidence; not readiness for current code. Fresh checks below cover selected domains.',
            run_id=uuid.uuid4().hex,selected_case_ids=[c['case_id'] for c in cases],case_list_sha256=digest_file(args.case_list),
            model_configuration=config.public(),workers=1,cases=[],index_builds=[],
            transport_policy=TRANSPORT_POLICY,transport_dependency_binding=recorded_binding(),
            preparation_attempts=[],preparation_model_http_attempts=0,
            model_request_count_scope='All case and index HTTP attempts; failed index attempts retained')
        report['sql_repair_policy']=REPAIR_POLICY
        report['schema_selection_policy']=coverage_contract(args.schema_coverage)
        if args.condition_relations:
            from .demand_relations import policy as demand_policy
            report['condition_relation_policy']=demand_policy(args.relation_output,args.categorical_population)
        if args.intent_candidate:
            from .intent import policy
            report['intent_candidate_policy']=policy()
        if args.semantic_planning:
            from .intent import query_semantics_policy
            report['query_semantic_planning_policy']=query_semantics_policy()
        if args.output_contract:
            from .output_contract import policy as output_policy
            report['public_output_contract_policy']=output_policy()
        report['budget_counter_probes']=budget_checks()
        with tempfile.TemporaryDirectory(prefix='bird_diagnostic_probe_') as scratch:
            sentinel=Path(scratch)/'private';sentinel.write_bytes(b'private')
            report['current_isolation_probe']=isolation_probe([sentinel,PROTOCOL_DIR/'scorer/gold110.jsonl',
                args.data_root/evidence.manifest['question_relative_path'],args.credentials_file])
        try:run_case_process({'mode':'watchdog_probe'},seconds=1)
        except BirdFailure as error:require(error.category=='case_wall_timeout','Unexpected watchdog error')
        else:raise BirdFailure('watchdog_failed')
        report['current_timeout_probe']={'passed':True,'probe_seconds':1,'formal_case_timeout_seconds':600}
        receipts={};indexes={}
        with BirdRegistry(evidence,args.credentials_file) as registry:
            for db in sorted({c['database_id'] for c in cases}):
                attempt={'database_id':db,'stage':'source_verification','complete':False,
                         'model_usage':{'model_http_attempts':0,'model_events':[]}}
                report['preparation_attempts'].append(attempt)
                try:
                    runtime=registry.get(db);report['postgresql_connected']=True
                    receipts[db]=runtime.receipt();index=build_index(runtime,config,args.index_root,progress=attempt)
                finally:
                    report['preparation_model_http_attempts']=sum(a['model_usage']['model_http_attempts']
                        for a in report['preparation_attempts'])
                    report['new_model_request_count']=report['preparation_model_http_attempts']
                report['index_builds'].append(index);indexes[db]=index['path']
                print('diagnostic runtime/index ready: '+db,flush=True)
        registry.close();require(all(r.connections.closed for r in registry._runtimes.values()),'Preparation pools did not close')
        report['preparation_pools_closed']=True
        report['source_receipts']=[{k:v for k,v in receipts[db].items() if k not in ('catalog_content','content_guards','typed_tables')} for db in sorted(receipts)]
        baseline_cases={c['case_id']:c for c in baseline['cases']}
        for position,public in enumerate(cases,1):
            db=public['database_id'];started=time.monotonic()
            # No Gold SQL, result, score or previous model output enters this worker.
            request={'mode':'diagnostic','input':public,'receipt':receipts[db],'data_root':str(args.data_root.resolve()),
                'results_dir':str(args.results_dir.resolve()),'credentials_file':str(args.credentials_file.resolve()),
                'index_path':indexes[db],'code_sha256':report['code_binding']['sha256'],
                'model_config_private':{'api_key':config.api_key,'chat_base':config.chat_base,
                    'embedding_base':config.embedding_base,'rerank_base':config.rerank_base}}
            if args.schema_coverage:request['schema_coverage_enabled']=True
            if args.intent_candidate:request['intent_candidate_enabled']=True
            if args.semantic_planning:request['semantic_planning_enabled']=True
            if args.output_contract:request['output_contract_enabled']=True
            if args.condition_relations:request['condition_relations_enabled']=True
            if args.relation_output:request['relation_output_enabled']=True
            if args.categorical_population:request['categorical_population_enabled']=True
            report['new_model_request_count']=None
            try:result=run_case_process(request,seconds=600)
            except Exception as error:
                result={'case_id':public['case_id'],'database_id':db,'mode':'diagnostic','status':fault(error).category,
                    'complete':False,'ex_correct':None,'errors':[fault(error).public()],'new_model_request_count':None}
            require(result.get('case_id')==public['case_id'] and result.get('database_id')==db
                    and result.get('mode')=='diagnostic' and result.get('ex_correct') is None,'Diagnostic worker identity/scoring mismatch')
            result['case_wall_seconds']=round(time.monotonic()-started,3)
            # Historical status is appended by the trusted parent AFTER Agent/worker exit.
            old=baseline_cases[public['case_id']]
            result['historical_baseline']={'status':old['status'],'ex_correct':old['ex_correct']}
            report['cases'].append(result)
            counts=[c.get('new_model_request_count') for c in report['cases']]
            report['new_model_request_count']=(report['preparation_model_http_attempts']+sum(counts)
                if all(type(v) is int for v in counts) else None)
            print(f"[{position}/{len(cases)}] {public['case_id']} diagnostic_status={result['status']}",flush=True)
        actual=report['cases'];unknown=any(c.get('new_model_request_count') is None for c in actual)
        attempts=sum(c.get('new_model_request_count') or 0 for c in actual)
        report.update(run_status='complete',target_data_verified=True,new_model_request_count=None if unknown else attempts+report['preparation_model_http_attempts'],
            summary={'case_count':len(actual),'status_counts':dict(Counter(c['status'] for c in actual)),
                'diagnostics_recorded_count':sum('development_diagnostics' in c for c in actual),
                'runtime_closed_count':sum(c.get('runtime_closed') is True for c in actual),
                'repeated_sql_case_count':sum(c.get('status')=='repeated_sql' for c in actual),
                'database_validation_skipped_count':sum(v.get('database_validation_performed') is False for c in actual for v in c.get('validation_events',[])),
                'case_model_http_attempts':None if unknown else attempts,'observed_case_http_attempts':attempts,
                'shared_index_http_attempts':sum((i.get('model_usage') or {}).get('model_http_attempts',0) for i in report['index_builds']),
                'primary_ex':None,'formal_ex_denominator':None})
        require(code_binding()==report['code_binding'],'Code changed during diagnostic run')
        if args.save_snapshot:
            snapshot=args.results_dir/'snapshots/bird_diagnostics'/evidence.protocol['protocol_id']/report['run_id']/'report.json'
            write_new_json(snapshot,report);report['snapshot']={'path':str(snapshot),'sha256':digest_file(snapshot)}
    raise SystemExit(0 if report['run_status']=='complete' else 1)


if __name__=='__main__':main()
