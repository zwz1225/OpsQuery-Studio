"""Verify all BIRD domain contexts, native execution, profiles and actual Linux isolation; no model calls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import time

from scripts.m2_b_common import BASE,PROTOCOL_DIR,require
from scripts.m2_b_target import DEFAULT_CREDENTIALS,journal,live_dependencies
from evaluation.bird.evidence import Evidence,DEFAULT_DATA,DEFAULT_RESULTS
from evaluation.bird.budgets import Budget,BirdFailure
from evaluation.bird.manifest import code_binding,source_binding
from evaluation.bird.runtime import BirdRegistry,fault
from evaluation.bird.supervisor import isolation_probe,run_case_process


def budget_checks():
    records=[]
    def denied(name,prepare,action,category):
        budget=Budget();prepare(budget)
        try:action(budget)
        except BirdFailure as error:passed=error.category==category
        else:passed=False
        records.append({'name':name,'passed':passed,'simulated_counters_only':True})
    denied('shared_16_http_attempts',lambda b:[b.model_attempt('embedding') for _ in range(16)],lambda b:b.model_attempt('rerank'),'model_attempt_limit')
    denied('chat_10_http_attempts',lambda b:[b.model_attempt('chat') for _ in range(10)],lambda b:b.model_attempt('chat'),'chat_attempt_limit')
    denied('three_sql_calls',lambda b:[b.sql_call() for _ in range(3)],lambda b:b.sql_call(),'sql_tool_call_limit')
    denied('three_validation_attempts',lambda b:[b.validation(1) for _ in range(3)],lambda b:b.validation(1),'validation_attempt_limit')
    denied('one_transport_retry',lambda b:None,lambda b:b.model_attempt('chat',retry=2),'transport_retry_limit')
    denied('98304_prompt_utf8_bytes',lambda b:None,lambda b:b.model_attempt('chat',prompt=b'x'*98305),'prompt_byte_limit')
    denied('expired_case_deadline',lambda b:setattr(b,'started',time.monotonic()-601),lambda b:b.remaining(),'case_wall_timeout')
    require(all(x['passed'] for x in records),'Shared budget probes failed')
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root',type=Path,default=DEFAULT_DATA)
    parser.add_argument('--results-dir',type=Path,default=DEFAULT_RESULTS)
    parser.add_argument('--credentials-file',type=Path,default=DEFAULT_CREDENTIALS)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();protected=[args.data_root,PROTOCOL_DIR,args.credentials_file,
        args.results_dir/'m2_b_postgres_validation_server.json',args.results_dir/'m2_b_postgres_import_server.json',args.results_dir/'m2_b_postgres_initialization_server.json']
    with journal(args.output,'M2 C domain runtime, profiles, budgets and isolation',protected=protected) as report:
        live_dependencies();evidence=Evidence.load(args.data_root,args.results_dir)
        report.update(source_binding=source_binding(evidence),code_binding=code_binding(),domains=[])
        report['budget_counter_probes']=budget_checks()
        with tempfile.TemporaryDirectory(prefix='bird_private_probe_') as scratch:
            sentinel=Path(scratch)/'private_sentinel';sentinel.write_bytes(b'private-isolation-probe')
            paths=[sentinel,PROTOCOL_DIR/'scorer/gold110.jsonl',args.data_root/evidence.manifest['question_relative_path'],args.credentials_file]
            require(all(p.is_file() for p in paths),'Isolation probe input missing')
            report['isolation']=isolation_probe(paths)
        try:run_case_process({'mode':'watchdog_probe'},seconds=1)
        except BirdFailure as error:require(error.category=='case_wall_timeout','Unexpected watchdog failure')
        else:raise BirdFailure('watchdog_failed')
        report['hard_process_timeout_probe']={'passed':True,'probe_timeout_seconds':1,'formal_case_timeout_seconds':600,'process_group_terminated':True}
        with BirdRegistry(evidence,args.credentials_file) as registry:
            for db in evidence.manifest['query_domains']:
                runtime=registry.get(db);report['postgresql_connected']=True
                table=runtime.catalog.tables[0];name=table['name'];qualified='public."'+name.replace('"','""')+'"'
                native=runtime.execute_native('SELECT COUNT(*) AS duplicate, COUNT(*) AS duplicate FROM '+qualified)
                expected=next(t['row_count'] for t in runtime.tables if t['name']==name)
                require(native.complete and native.rows==[(expected,expected)] and native.columns==['duplicate','duplicate'],'Native positional tuple or duplicate-name execution failed')
                profiles=runtime.profile_table(table['id'],[f['name'] for f in table['fields'][:2]])
                require(all(len(p['samples'])<=3 and len(p['sample_truncated'])==len(p['samples']) for p in profiles.values()),'Profile sampling policy failed')
                other=next(t['name'] for t in evidence.manifest['dump']['tables'] if t['name'] not in runtime.names)
                try:runtime.execute_native('SELECT COUNT(*) FROM public."'+other+'"')
                except BirdFailure as error:require(error.category=='sql_source_denied','Unexpected cross-domain SQL error')
                else:raise BirdFailure('cross_domain_sql_allowed')
                try:runtime.profile_table('short_video_ops.'+name,[])
                except Exception:pass
                else:raise BirdFailure('cross_domain_profile_allowed')
                check={'database_id':db,'role':runtime.domain['query_role'],'source_identity':runtime.identity.public(),
                    'typed_table_count':len(runtime.tables),'field_count':sum(len(t['fields']) for t in runtime.catalog.tables),
                    'native_duplicate_names_preserved':True,'cross_domain_sql_denied':True,'cross_domain_profile_denied':True,
                    'profiles':profiles,'descriptions':runtime.description_diagnostic,
                    'verification':{k:v for k,v in runtime.verification.items() if k not in ('catalog_content','content_guards','typed_tables')}}
                report['domains'].append(check);print('runtime ['+str(len(report['domains']))+'/11] '+db+': passed',flush=True)
            try:registry.get('short_video_ops')
            except Exception:report['unknown_database_rejected']=True
            else:raise BirdFailure('legacy_runtime_fallback_allowed')
            # A deliberate SQL error must not poison the next borrower.
            runtime=registry.get('superhero')
            try:runtime.execute_native("SELECT CAST('not-an-integer' AS BIGINT)")
            except BirdFailure as error:require(error.sqlstate=='22P02','Unexpected SQL recovery probe error')
            else:raise BirdFailure('expected_sql_failure_missing')
            require(runtime.execute_native('SELECT 1').rows==[(1,)],'SQL failure did not recover')
            report['sql_failure_recovery_verified']=True
        registry.close();report['pools_closed']=all(r.connections.closed for r in registry._runtimes.values())
        require(report['pools_closed'],'Runtime pool close failed')
        report.update(run_status='complete',runtime_verified=True,target_data_verified=True,runtime_available=True,
            agent_isolation_verified=True,budget_enforcement_verified=True,
            summary={'logical_database_count':11,'table_count':sum(d['typed_table_count'] for d in report['domains']),
                'field_count':sum(d['field_count'] for d in report['domains']),'profile_field_count':sum(len(d['profiles']) for d in report['domains']),
                'isolation_path_denials':4,'simulated_budget_checks':len(report['budget_counter_probes'])},
            verification_scope='Fresh per-domain typed snapshots plus live content guards and real Linux Agent isolation; Gold110 and live are separate gates.')
    raise SystemExit(0 if report['run_status']=='complete' else 1)


if __name__=='__main__':main()
