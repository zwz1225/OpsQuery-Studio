"""Trusted-only audit of four FIRST SQLs rejected by the old population validator.

This module is never imported by the Agent/retriever. Frozen Gold remains local
to the trusted audit, after exact provenance and development checks.
"""
from __future__ import annotations

import json
from .evidence import public_cases,scorer_gold
from .manifest import code_binding,source_binding
from .replay import replay_case,sql_sha
from .budgets import hard_deadline
from .runtime import BirdRegistry
from scripts.m2_b_common import digest_file,digest_json,require

SOURCE_SHA='db2255b9cae7af1a30b24cb9b160c41c7da159bb5ec9b1d9d4fa1dd04e17f246'
NATIVE_SHA='a8e5cb6602277ccde09dcaf0bbb3303dd76339995984e3b4d7f4a9598d30610f'


def first_captures(source_path,native_path,evidence):
    require(digest_file(source_path)==SOURCE_SHA and digest_file(native_path)==NATIVE_SHA,'Use the two accepted immutable public-intent v1 reports')
    source=json.loads(source_path.read_bytes());native=json.loads(native_path.read_bytes())
    require(source['source_binding']==native['source_binding']==source_binding(evidence) and native['source_report_sha256']==SOURCE_SHA
            and source['run_status']==native['run_status']=='complete' and not source['errors'] and not native['errors']
            and source['gold_executed'] is False and source['holdout_live_allowed'] is False
            and native['code_binding']==source['code_binding'],'Recorded first-SQL source chain differs')
    binding=source['code_binding'];current=code_binding()
    require(binding['sha256']==digest_json({k:v for k,v in binding.items() if k!='sha256'}),'Producer binding digest differs')
    # Different generation/feedback candidate is intentional. Execution, native
    # scoring, permissions, dataset readers and application libraries must match.
    changed_generation={'evaluation/bird/intent.py','evaluation/bird/retrieval.py','evaluation/bird/repair.py'}
    require(all(current['files'].get(k)==v for k,v in binding['files'].items() if k not in changed_generation),
            'Execution/scoring/source code changed since captured first SQLs')
    approved={c['case_id']:c for c in public_cases('development80')};original={c['case_id']:c for c in native['cases']}
    require(len(source['cases'])==len(original)==14 and source['selected_case_ids']==[c['case_id'] for c in source['cases']]
            and set(source['selected_case_ids'])<=set(approved),'Captured set is not the accepted development-only subset')
    captures=[]
    for c in source['cases']:
        require(c['database_id']==approved[c['case_id']]['database_id'] and c['ex_correct'] is None and c['gold_sql_sha256'] is None
                and c['source_identity']==original[c['case_id']]['source_identity'],'Captured source identity differs')
        events=c['development_diagnostics']['attempts'];decisions=[a for a in events if a['kind']=='model_decision']
        blocked=[a for a in events if a['kind']=='validate' and not a['success'] and
                 any(v['code']=='missing_population_condition' for v in a.get('repair_feedback',{}).get('intent_violations',[]))]
        if not blocked:continue
        require(len(blocked)==1 and len(decisions)==2 and blocked[0]['sql']==decisions[0]['sql'],'Initial rejection capture differs')
        sql=decisions[0]['sql'];require(sql['provided'] is True and not sql['truncated'] and not sql['redacted'] and sql['original_sha256']==sql_sha(sql['text']),
                                      'Initial SQL bytes are missing or truncated')
        require(decisions[-1]['sql']['text']==original[c['case_id']]['queries']['captured_generated']==c['generated_sql'],
                'Previously executed final SQL chain differs')
        captures.append(dict(c,generated_sql=sql['text'],result=None,previous_final_sql=c['generated_sql'],
                             rejected_initial_sql=sql,previous_rejection=blocked[0]['repair_feedback']))
    require(len(captures)==4,'Expected the four recorded population-rule rejections')
    gold=scorer_gold();pairs=[]
    for c in captures:
        g=gold[c['case_id']]
        require(g['database_id']==c['database_id'] and g['gold_sql_sha256']==original[c['case_id']]['gold_sql_sha256'],
                'Frozen development Gold differs')
        pairs.append((c,g))
    return source,pairs


def run_first_audit(evidence,source_path,native_path,credentials_path,report,*,registry_factory=None):
    source,pairs=first_captures(source_path,native_path,evidence)
    report.update(mode='trusted_rejected_first_sql_audit',policy='bird_rejected_first_sql_native_audit_v1',
        source_report_sha256=SOURCE_SHA,previous_native_report_sha256=NATIVE_SHA,producer_code_sha256=source['code_binding']['sha256'],
        code_binding=code_binding(),source_binding=source_binding(evidence),selected_case_ids=[c['case_id'] for c,g in pairs],
        formal_benchmark=False,primary_ex=None,holdout_live_allowed=False,new_model_request_count=0,
        source_scope='First generated SQL captured before validator rejection; not a previously executed native result.',
        cases=[],source_receipts=[],pools_closed=False,gold_executed=False)
    registry=(registry_factory or BirdRegistry)(evidence,credentials_path);seen=set()
    try:
        with registry:
            for c,g in pairs:
                runtime=registry.get(c['database_id']);report['postgresql_connected']=True
                if runtime.database_id not in seen:
                    report['source_receipts'].append({k:v for k,v in runtime.receipt().items() if k not in ('catalog_content','content_guards','typed_tables')});seen.add(runtime.database_id)
                record={};report['cases'].append(record)
                try:
                    with hard_deadline(600,'first_sql_native_audit_timeout'):replay_case(runtime,c,g,progress=record)
                finally:
                    record.pop('recorded_prediction_diagnostic',None);record.pop('captured_native_diagnostic_preserved',None)
                    record.update(initial_sql_previously_executed=False,initial_sql_capture_sha256=c['rejected_initial_sql']['original_sha256'],
                                  previous_final_sql_sha256=sql_sha(c['previous_final_sql']),previous_rejection=c['previous_rejection'])
                require(code_binding()==report['code_binding'],'Code changed during first-SQL audit')
                print(c['case_id']+' first_sql_native_match='+str(record['native_comparison']['matches_frozen_gold']),flush=True)
        matches=sum(c['native_comparison']['matches_frozen_gold'] for c in report['cases'])
        report.update(run_status='complete',target_data_verified=True,native_comparisons_complete=True,
            summary=dict(case_count=4,native_match_count=matches,native_mismatch_count=4-matches,
                         sql_execution_count=sum(c['budget']['sql_tool_calls'] for c in report['cases']),new_model_request_count=0,formal_ex_denominator=None))
    finally:
        report['gold_executed']=any(c.get('gold_execution_attempted') for c in report['cases'])
        registry.close();report['pools_closed']=all(r.connections.closed for r in registry._runtimes.values())
