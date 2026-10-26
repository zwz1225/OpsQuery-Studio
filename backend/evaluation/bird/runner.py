"""External BIRD Gold110 readiness and gated development runner, workers=1."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import uuid
import time

from scripts.m2_b_common import BASE,PROTOCOL_DIR,digest_file,digest_json,require,write_new_json
from scripts.m2_b_target import DEFAULT_CREDENTIALS,journal,live_dependencies
from .budgets import BirdFailure
from .evidence import Evidence,DEFAULT_DATA,DEFAULT_RESULTS,public_cases,scorer_gold
from .manifest import code_binding,source_binding,require_runtime_report,require_gold_report
from .runtime import BirdRegistry,fault
from .supervisor import run_case_process
from .metrics import summarize


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('gold','live'),required=True)
    parser.add_argument('--split',choices=('smoke8','development80'))
    parser.add_argument('--data-root',type=Path,default=DEFAULT_DATA)
    parser.add_argument('--results-dir',type=Path,default=DEFAULT_RESULTS)
    parser.add_argument('--credentials-file',type=Path,default=DEFAULT_CREDENTIALS)
    parser.add_argument('--runtime-report',type=Path,default=DEFAULT_RESULTS/'m2_c_bird_runtime_server.json')
    parser.add_argument('--gold-report',type=Path)
    parser.add_argument('--model-config-file',type=Path,default=BASE/'.env')
    parser.add_argument('--index-root',type=Path,default=BASE/'data/bird_indexes/m2_bird_pg_v1')
    parser.add_argument('--save-snapshot',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    protected=[args.data_root,PROTOCOL_DIR,args.credentials_file,args.model_config_file,args.runtime_report,args.index_root,
        args.results_dir/'m2_b_postgres_validation_server.json',args.results_dir/'m2_b_postgres_import_server.json',
        args.results_dir/'m2_b_postgres_initialization_server.json']+([args.gold_report] if args.gold_report else [])
    with journal(args.output,'M2 C BIRD external benchmark',protected=protected) as report:
        live_dependencies();evidence=Evidence.load(args.data_root,args.results_dir)
        require(not args.index_root.resolve().is_relative_to(args.data_root.resolve())
            and not args.index_root.resolve().is_relative_to(PROTOCOL_DIR.resolve()),'Index output must be outside frozen sources/protocol')
        require_runtime_report(args.runtime_report,evidence)
        report.update(mode=args.mode,source_binding=source_binding(evidence),code_binding=code_binding(),run_id=uuid.uuid4().hex,
                      runtime_report_sha256=digest_file(args.runtime_report),workers=1,cases=[],index_builds=[])
        gold=scorer_gold()
        if args.mode=='gold':
            require(args.split is None,'Gold readiness always covers all 110 original SQLs; partial readiness is refused')
            inputs=public_cases('development80')+public_cases('holdout30');split='gold110'
        else:
            require(args.split is not None and args.gold_report is not None,'Live requires a frozen development split and successful --gold-report')
            require_gold_report(args.gold_report,evidence,args.runtime_report)
            inputs=public_cases(args.split);split=args.split
            report['gold_readiness_report_sha256']=digest_file(args.gold_report)
            from .model import ModelConfig
            config=ModelConfig.load(args.model_config_file)
            report['model_configuration']=config.public()
        require(len({r['case_id'] for r in inputs})==len(inputs),'Duplicate external case')
        require(all(r['case_id'] in gold and r['database_id']==gold[r['case_id']]['database_id'] for r in inputs),'Public/Gold source mapping differs')
        report.update(split=split,selected_case_ids=[r['case_id'] for r in inputs],
            selected_input_sha256=digest_json(inputs),selected_gold_sql_sha256=digest_json([gold[r['case_id']]['gold_sql_sha256'] for r in inputs]),
            primary_denominator=len(inputs),holdout_live_allowed=False,
            holdout_control='Holdout live requires a subsequent frozen candidate and one-attempt ledger. This entry admits development splits only.')
        # Prepare source receipts once per domain, outside formal per-case budgets.
        # Each case process rechecks metadata/ACL/content guards before querying.
        receipts={};indexes={}
        selection={}
        for name in ('development80','holdout30'):
            selection.update({x['case_id']:x for x in json.loads((PROTOCOL_DIR/(name+'.json')).read_bytes())['selection_metadata']})
        with BirdRegistry(evidence,args.credentials_file) as registry:
            for db in sorted({r['database_id'] for r in inputs}):
                runtime=registry.get(db);receipts[db]=runtime.receipt();report['postgresql_connected']=True
                print('verified runtime: '+db,flush=True)
                if args.mode=='live':
                    from .retrieval import build_index
                    index=build_index(runtime,config,args.index_root)
                    report['index_builds'].append(index);indexes[db]=index['path']
        report['source_receipts']=[{k:v for k,v in receipts[db].items() if k not in ('catalog_content','content_guards','typed_tables')} for db in sorted(receipts)]
        for i,public in enumerate(inputs,1):
            db=public['database_id'];g=gold[public['case_id']]
            request={'mode':args.mode,'gold':g,'receipt':receipts[db],
                'data_root':str(args.data_root.resolve()),'results_dir':str(args.results_dir.resolve()),
                'credentials_file':str(args.credentials_file.resolve()),'code_sha256':report['code_binding']['sha256']}
            if args.mode=='live':
                # Private parent-to-broker pipe only; neither report nor isolated
                # Agent receives these values. Supports environment-only keys
                # and freezes endpoint selection across all cases in this run.
                request.update(input=public,index_path=indexes[db],model_config_private={'api_key':config.api_key,
                    'chat_base':config.chat_base,'embedding_base':config.embedding_base,'rerank_base':config.rerank_base})
            case_started=time.monotonic()
            try:result=run_case_process(request,seconds=600)
            except Exception as error:
                failure=fault(error)
                result={'case_id':public['case_id'],'database_id':db,'mode':args.mode,'status':failure.category,
                    'complete':False,'ex_correct':False if args.mode=='live' else None,'gold_sql_sha256':g['gold_sql_sha256'],
                    'errors':[failure.public()],'new_model_request_count':0 if args.mode=='gold' else None,'usage_status':'unknown after forced termination'}
            if not (result.get('case_id')==public['case_id'] and result.get('database_id')==db
                    and result.get('gold_sql_sha256')==g['gold_sql_sha256']):
                result={'case_id':public['case_id'],'database_id':db,'mode':args.mode,'status':'case_worker_identity_mismatch',
                    'complete':False,'ex_correct':False if args.mode=='live' else None,'gold_sql_sha256':g['gold_sql_sha256'],
                    'errors':[{'category':'case_worker_identity_mismatch'}],'new_model_request_count':0 if args.mode=='gold' else None}
            result['case_wall_seconds']=round(time.monotonic()-case_started,3)
            report['cases'].append(result)
            print(f"[{i}/{len(inputs)}] {public['case_id']} status={result['status']} complete={result['complete']}",flush=True)
        report['target_data_verified']=True
        cases=report['cases'];complete=sum(c.get('complete') is True for c in cases)
        statuses=dict(Counter(c['status'] for c in cases))
        unknown=any(c.get('new_model_request_count') is None for c in cases)
        observed=sum(c.get('new_model_request_count') or 0 for c in cases)
        report['summary']={**summarize(cases,selection,args.mode),'case_count':len(cases),'complete_result_count':complete,'status_counts':statuses,
            'new_model_request_count':None if unknown else observed,'observed_model_http_attempts':observed,
            'model_attempt_count_incomplete':unknown,
            'shared_index_http_attempts':sum((x.get('model_usage') or {}).get('model_http_attempts',0) for x in report['index_builds'])}
        report['new_model_request_count']=report['summary']['new_model_request_count'] if not report['summary']['model_attempt_count_incomplete'] else None
        if args.mode=='gold':
            ready=len(cases)==110 and all(c.get('status')=='gold_ready' and c.get('complete') is True
                and not c.get('errors') and c.get('runtime_closed') is True for c in cases)
            report.update(gold110_ready=ready,run_status='complete' if ready else 'blocked')
            report['summary'].update(gold_ready_count=sum(c.get('status')=='gold_ready' and c.get('complete') is True for c in cases),
                                    original_gold_sql_count=110)
            report['gold_visibility']='Scorer-only SQL/hashability/complete-result checks. No SQL text, answer rows or Gold feedback passed to Agent/indexer.'
        else:
            correct=sum(c.get('ex_correct') is True and c.get('complete') is True and c.get('status')=='scored' and not c.get('errors') for c in cases)
            report.update(run_status='complete',summary={**report['summary'],'ex_pass_count':correct,'primary_ex':correct/len(inputs),
                'primary_denominator':len(inputs),'first_sql_execution_success_count':sum(c.get('first_sql_execution_success') is True for c in cases),
                'final_sql_execution_success_count':sum(c.get('final_sql_execution_success') is True for c in cases)})
        if args.save_snapshot:
            snapshot=DEFAULT_RESULTS/'snapshots/bird'/evidence.protocol['protocol_id']/evidence.validation['verified_data_version']/split/(report['run_id']+'.json')
            write_new_json(snapshot,report);report['snapshot']={'path':str(snapshot),'sha256':digest_file(snapshot)}
    raise SystemExit(0 if report['run_status']=='complete' else 1)


if __name__=='__main__':main()
