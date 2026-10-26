"""Trusted, version-bound native audit of NEW public-intent development captures."""
from __future__ import annotations

import json
import re

from scripts.m2_b_common import digest_file, require
from .evidence import public_cases, scorer_gold
from .intent import policy
from .manifest import code_binding, source_binding
from .replay import sql_sha


def load_candidate_capture(path, evidence, expected_sha256):
    require(isinstance(expected_sha256,str) and re.fullmatch('[a-f0-9]{64}',expected_sha256)
            and digest_file(path)==expected_sha256,'Candidate source hash differs')
    row=json.loads(path.read_bytes())
    require(row.get('run_status')=='complete' and row.get('mode')=='diagnostic'
            and row.get('split')=='development_diagnostic_subset' and row.get('formal_benchmark') is False
            and row.get('gold_executed') is False and row.get('holdout_live_allowed') is False
            and row.get('primary_ex') is None and row.get('errors')==[]
            and row.get('source_binding')==source_binding(evidence)
            and row.get('code_binding')==code_binding() and row.get('intent_candidate_policy')==policy()
            and row.get('target_data_verified') is True and row.get('preparation_pools_closed') is True,
            'Current candidate source/code/termination differs')
    isolation=row.get('current_isolation_probe',{});probes=isolation.get('probes',{})
    require(isolation.get('passed') is True and probes.get('read_denials')==[True]*4
            and all(probes.get(k) is True for k in ('network_socket_denied','process_creation_denied','secret_environment_absent'))
            and row.get('current_timeout_probe',{}).get('passed') is True
            and len(row.get('budget_counter_probes',[]))==7
            and all(c.get('passed') is True for c in row['budget_counter_probes']), 'Candidate isolation/budget probes missing')
    approved={c['case_id']:c for c in public_cases('development80')}
    cases=row.get('cases',[]);ids=[c['case_id'] for c in cases]
    require(0<len(ids)<=80 and len(ids)==len(set(ids)) and ids==row.get('selected_case_ids') and set(ids)<=set(approved),
            'Candidate replay requires a unique development-only subset; holdout is refused')
    receipts={v['database_id']:v for v in row['source_receipts']}
    require(len(receipts)==len(row['source_receipts']) and set(receipts)=={c['database_id'] for c in cases},'Candidate receipts differ')
    selected=[];excluded=[]
    for c in cases:
        db=c['database_id'];identity=c.get('source_identity',{});receipt=receipts[db]
        require(db==approved[c['case_id']]['database_id'] and c.get('mode')=='diagnostic'
                and c.get('ex_correct') is None and c.get('gold_sql_sha256') is None and c.get('runtime_closed') is True
                and c.get('intent_candidate_policy')==policy()
                and identity.get('logical_database_id')==db and identity.get('source_id')=='bird_mini_dev_postgres_'+db
                and identity.get('backend')=='postgresql' and identity.get('dialect')=='postgres'
                and identity.get('physical_schema')=='public' and receipt.get('live_target_verified') is True
                and identity.get('data_version')==receipt.get('authorized_data_version')
                and identity.get('catalog_version')==receipt.get('authorized_catalog_version')
                and c.get('query_role')==receipt.get('role')==evidence.domain(db)['query_role'], 'Candidate case source differs')
        usage=c.get('budget',{});lookup=c.get('canonical_lookup',{})
        require(0<=usage.get('model_http_attempts',99)<=16 and 0<=usage.get('chat_http_attempts',99)<=10
                and 0<=usage.get('sql_tool_calls',99)<=3
                and all(0<int(k)<=3 and type(v) is int and 0<v<=3 for k,v in usage.get('validation_attempts',{}).items())
                and all(0<int(k)<=3 and type(v) is int and 0<v<=3 for k,v in usage.get('generation_attempts',{}).items())
                and lookup.get('sql_tool_calls') in (0,1) and 0<=lookup.get('probe_count',99)<=4
                and usage['sql_tool_calls']>=lookup['sql_tool_calls']+len(c.get('executions',[])), 'Candidate case budget differs')
        agent=c.get('agent_isolation',{})
        require(type(c.get('agent_started')) is bool,'Candidate Agent lifecycle missing')
        if c['agent_started']:
            require(all(agent.get(k) is False for k in ('project_read_access','environment_credentials','direct_database_access')),
                    'Candidate Agent isolation missing')
        else:
            require(c.get('status') not in ('diagnostic_answered','clarification') and c.get('errors'),
                    'Candidate without Agent must record a preparation failure')
        if c.get('status')!='diagnostic_answered':
            excluded.append({'case_id':c['case_id'],'database_id':db,'reason':c.get('status'),
                             'errors':c.get('errors',[]),'counted_as_success':False})
            continue
        executions=c.get('executions',[])
        require(c.get('complete') is True and c.get('errors')==[] and c.get('result',{}).get('complete') is True
                and executions and executions[-1].get('success') is True and executions[-1]['diagnostic']==c['result'],
                'Candidate final native execution missing')
        events=[v for v in c['development_diagnostics']['attempts'] if v['kind']=='execute' and v.get('success') is True]
        require(events,'Candidate SQL capture missing')
        record=events[-1]['sql'];text=c.get('generated_sql')
        require(isinstance(text,str) and record.get('provided') is True and record.get('truncated') is False
                and record.get('redacted') is False and record.get('text')==text
                and record.get('original_sha256')==sql_sha(text)
                and record.get('original_utf8_bytes')==len(text.encode()), 'Candidate captured SQL bytes differ')
        selected.append(c)
    # Trusted Gold is loaded only after all source, budget and development checks.
    gold=scorer_gold();pairs=[]
    for c in selected:
        g=gold[c['case_id']]
        require(g['database_id']==c['database_id'] and g['dialect']=='postgres' and sql_sha(g['gold_sql'])==g['gold_sql_sha256'],
                'Frozen candidate Gold identity differs')
        pairs.append((c,g))
    return row,pairs,excluded
