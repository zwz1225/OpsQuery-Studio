"""Trusted two-case development audit. Gold/results never enter Agent or indexer."""
from __future__ import annotations

import json
from pathlib import Path

from evaluation.bird_protocol import compare_ex_rows
from scripts.m2_b_common import BASE,digest_file,require
from .budgets import Budget
from .evidence import public_cases,scorer_gold
from .manifest import code_binding,source_binding

SOURCE_SHA='9167b9005fcbd2f899dda744f4c6a3258c24777e4625281d05a6b33ca8d57123'
CASE_IDS=('BIRD-PG-0050','BIRD-PG-0095')
POLICY='bird_trusted_development_semantics_v1'

PROBES={
    'BIRD-PG-0050': '''SELECT sc.cds, sc.avgscrmath, sc.sname, s.school, s.mailstreet
FROM public.satscores sc JOIN public.schools s ON sc.cds = s.cdscode
ORDER BY sc.avgscrmath DESC NULLS LAST LIMIT 1 OFFSET 6''',
    'BIRD-PG-0095': '''WITH youngest AS (
 SELECT client_id, birth_date, district_id FROM public.client
 ORDER BY birth_date DESC NULLS LAST LIMIT 1
), global_birth AS (SELECT MAX(birth_date) AS youngest_date FROM public.client),
global_salary AS (SELECT MAX(a11) AS maximum_salary FROM public.district)
SELECT y.client_id, y.birth_date, gb.youngest_date, a.account_id,
 cd.a11 AS client_district_salary, ad.a11 AS account_district_salary,
 gs.maximum_salary,
 CASE WHEN y.birth_date = gb.youngest_date AND cd.a11 = gs.maximum_salary THEN 1 ELSE 0 END AS generated_filters_keep_client
FROM youngest y JOIN public.disp d ON y.client_id = d.client_id
JOIN public.account a ON a.account_id = d.account_id
JOIN public.district cd ON cd.district_id = y.district_id
JOIN public.district ad ON ad.district_id = a.district_id
CROSS JOIN global_birth gb CROSS JOIN global_salary gs
ORDER BY a.account_id'''}


def load_cases(path:Path,evidence):
    require(digest_file(path)==SOURCE_SHA,'Use the accepted immutable three-case Schema coverage report')
    report=json.loads(path.read_bytes())
    require(report.get('run_status')=='complete' and report.get('mode')=='diagnostic' and report.get('gold_executed') is False
            and report.get('source_binding')==source_binding(evidence),'Diagnostic source evidence differs')
    current=code_binding()
    for name in ('runtime.py','sql.py','native.py','budgets.py'):
        key='evaluation/bird/'+name
        require(report['code_binding']['files'][key]==current['files'][key],'Execution policy changed since recorded SQL: '+name)
    approved={c['case_id']:c for c in public_cases('development80')};gold=scorer_gold()
    rows={c['case_id']:c for c in report['cases']}
    require(len(rows)==len(report['cases'])==3,'Source has duplicate or missing cases')
    result=[]
    for cid in CASE_IDS:
        row=rows[cid]
        require(cid in approved and row['database_id']==approved[cid]['database_id']==gold[cid]['database_id']
                and row['status']=='diagnostic_answered' and row['complete'] is True,'Only the selected frozen development cases may be audited')
        result.append((row,gold[cid]))
    return result


def native_record(result):
    preview=result.preview();preview['rows']=preview['rows'][:20]
    preview['preview_truncated']=len(preview['rows'])<len(result.rows)
    return {'diagnostic':result.diagnostic(),'preview':preview,'preview_row_limit':20}


def audit_case(runtime,case,gold,*,progress=None):
    cid=case['case_id']
    require(cid in CASE_IDS and case['database_id']==gold['database_id']==runtime.database_id
            and runtime.identity.public()==case['source_identity'],'Audit runtime source differs from captured case')
    budget=Budget(total_limit=0,chat_limit=0);results={};queries={'captured_generated':case['generated_sql'],
        'frozen_gold':gold['gold_sql'],'explanatory_probe':PROBES[cid]}
    record=progress if progress is not None else {}
    record.update(case_id=cid,database_id=case['database_id'],status='running',gold_execution_attempted=False,
                  gold_executed=False,execution_events=[],new_model_request_count=0)
    for name,sql in queries.items():
        budget.sql_call();event={'name':name,'status':'running'};record['execution_events'].append(event)
        if name=='frozen_gold':record['gold_execution_attempted']=True
        try:
            results[name]=runtime.execute_native(sql,budget)
            require(results[name].complete is True,'Incomplete semantic audit result')
            event['status']='complete'
            if name=='frozen_gold':record['gold_executed']=True
        except Exception as error:
            from .runtime import fault
            event.update(status='failed',error=fault(error).public());record['status']='failed'
            raise
        finally:record['budget']=budget.public()
    predicted=results['captured_generated'];expected=results['frozen_gold']
    # Native values are compared before any tagged JSON preview is produced.
    matches=compare_ex_rows(predicted.rows,expected.rows,predicted_complete=predicted.complete,gold_complete=expected.complete)
    details=({'name_pairs':[{'satscores_sname':row[2],'schools_school':row[3],'native_equal':row[2]==row[3]}
                            for row in results['explanatory_probe'].rows]}
             if cid=='BIRD-PG-0050' else
             {'probe_policy':'youngest client plus account/client district salaries and global maximum; no SQL repair or answer substitution'})
    if cid=='BIRD-PG-0050':
        from .native import tagged
        details['name_pairs']=[{k:tagged(v) if k!='native_equal' else v for k,v in pair.items()} for pair in details['name_pairs']]
    record.update({'status':'complete','case_id':cid,'database_id':case['database_id'],'source_identity':runtime.identity.public(),
        'query_role':runtime.domain['query_role'],'queries':queries,'frozen_gold_sql_sha256':gold['gold_sql_sha256'],
        'matches_frozen_gold':matches,'primary_ex':None,'formal_benchmark':False,
        'matches_recorded_ordered_native_digest':predicted.diagnostic()['ordered_native_diagnostic_sha256']==case['result']['ordered_native_diagnostic_sha256'],
        'results':{name:native_record(result) for name,result in results.items()},'details':details,
        'budget':budget.public(),'new_model_request_count':0,'audit_sql_call_limit':3})
    return record


def run_audit(evidence,source_path,credentials_path,report,*,registry_factory=None):
    from .runtime import BirdRegistry
    from .budgets import hard_deadline
    selected=load_cases(source_path,evidence)
    report.update(mode='trusted_development_semantics',formal_benchmark=False,primary_ex=None,gold_executed=False,
        holdout_live_allowed=False,policy=POLICY,source_report_sha256=digest_file(source_path),
        source_binding=source_binding(evidence),code_binding=code_binding(),cases=[],pools_closed=False,
        audit_budget_scope='Independent reviewer audit: at most 3 SELECT executions per case, 600 seconds per case, no model/Agent. Original generation budgets unchanged.')
    registry=(registry_factory or BirdRegistry)(evidence,credentials_path)
    try:
        with registry:
            for case,gold in selected:
                runtime=registry.get(case['database_id']);report['postgresql_connected']=True
                row={};report['cases'].append(row)
                with hard_deadline(600,'semantic_audit_timeout'):
                    audit_case(runtime,case,gold,progress=row)
                report['gold_executed']=True
                require(code_binding()==report['code_binding'],'Code changed during semantic audit')
        require(all(r.connections.closed for r in registry._runtimes.values()),'Audit pool did not close')
        report.update(run_status='complete',target_data_verified=True,
            summary={'case_count':len(selected),'matches_frozen_gold_count':sum(c['matches_frozen_gold'] for c in report['cases']),
                     'audit_sql_execution_count':sum(c['budget']['sql_tool_calls'] for c in report['cases']),
                     'new_model_request_count':0,'formal_ex_denominator':None,
                     'meaning':'complete means the audit finished; mismatching answers remain semantic failures, not a formal EX score'})
    finally:
        report['gold_executed']=any(c.get('gold_execution_attempted') for c in report['cases'])
        registry.close();report['pools_closed']=all(r.connections.closed for r in registry._runtimes.values())
