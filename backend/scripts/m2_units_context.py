"""Trusted reviewer probes of two immutable development captures; no Agent calls.

The case scope belongs to this audit only. No probe or reference information is
imported by the candidate generation, retrieval, repair or native scorer.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

import sqlglot
from sqlglot import exp

from scripts.m2_b_common import digest_file, require
from evaluation.bird.budgets import Budget, hard_deadline
from evaluation.bird.intent_replay import load_candidate_capture
from evaluation.bird.manifest import code_binding, source_binding
from evaluation.bird.native import NativeResult, encoded, tagged
from evaluation.bird.replay import native_difference, sql_sha
from evaluation.bird.runtime import BirdRegistry, fault
from evaluation.bird.semantics import native_record
from evaluation.bird.sql import validate_sql

SOURCE_SHA='4743a1b3234f358a51684278c093b31baaea26de3bfc3c3b4c110c2863f6ee52'
NATIVE_SHA='f0170d51cbcef805c13befc590c101678f5277fe6ef50b76dc7c2667500d7c08'
CASE_IDS=('BIRD-PG-0201','BIRD-PG-0586')
POLICY='bird_trusted_units_context_probe_v1'
MAX_QUERIES={'BIRD-PG-0201':9,'BIRD-PG-0586':6}


def audit_code():
    return {name:digest_file(Path(__file__).with_name(name)) for name in
            ('m2_units_context.py','check_m2_units_context.py')}


def load_cases(source_path, native_path, evidence):
    require(digest_file(source_path)==SOURCE_SHA and digest_file(native_path)==NATIVE_SHA,
            'Use the two accepted immutable public-intent v2 diagnostic/native reports')
    source=json.loads(source_path.read_bytes());native=json.loads(native_path.read_bytes())
    require(native.get('run_status')=='complete' and native.get('errors')==[]
            and native.get('source_report_sha256')==SOURCE_SHA and native.get('source_binding')==source_binding(evidence)
            and native.get('code_binding')==source.get('code_binding')==code_binding()
            and native.get('producer_code_sha256')==source['code_binding']['sha256']
            and native.get('formal_benchmark') is False and native.get('primary_ex') is None
            and native.get('holdout_live_allowed') is False and native.get('pools_closed') is True
            and native.get('new_model_request_count')==0 and native.get('native_comparisons_complete') is True
            and native.get('target_data_verified') is True and native.get('gold_executed') is True,
            'Accepted native provenance or execution/scoring environment differs')
    # Both input hashes and native provenance are checked before the existing
    # loader may read private Gold, and before any database connection is opened.
    checked,pairs,excluded=load_candidate_capture(source_path,evidence,SOURCE_SHA)
    recorded={c['case_id']:c for c in native['cases']}
    require(not excluded and len(recorded)==len(native['cases'])==len(pairs)==14
            and native['selected_case_ids']==checked['selected_case_ids'], 'Expected all 14 captured development SQLs')
    for case,gold in pairs:
        old=recorded[case['case_id']]
        require(old['source_identity']==case['source_identity'] and old['queries']=={
            'captured_generated':case['generated_sql'],'frozen_gold':gold['gold_sql']}
            and old['captured_native_diagnostic_preserved'] is True
            and old['results']['captured_generated']['diagnostic']==case['result']
            and old['generated_sql_sha256']==sql_sha(case['generated_sql'])
            and old['gold_sql_sha256']==gold['gold_sql_sha256'], 'Captured/native SQL or result chain differs')
    selected={c['case_id']:(c,g) for c,g in pairs if c['case_id'] in CASE_IDS}
    require(set(selected)==set(CASE_IDS), 'Only the two approved development cases may be probed')
    return source,[(selected[cid][0],selected[cid][1],recorded[cid]) for cid in CASE_IDS]


def captured_tree(sql):
    trees=[t for t in sqlglot.parse(sql,read='postgres') if t is not None]
    require(len(trees)==1 and isinstance(trees[0],exp.Select) and len(trees[0].expressions)==1,
            'Probe expects a captured single SELECT projection')
    return trees[0]


def numeric_variants(sql):
    """Keep captured population/semijoin; vary only the visible numeric projection."""
    tree=captured_tree(sql)
    projection=tree.expressions[0].unalias()
    require(isinstance(projection,exp.Div) and isinstance(projection.left,exp.Cast),
            'Expected a REAL numerator divided by a guarded denominator')
    require(str(projection.left.args['to']).upper() in ('FLOAT','REAL')
            and isinstance(projection.right,exp.Nullif), 'Captured numeric expression shape differs')
    numerator=projection.left.this;denominator=projection.right
    require(numerator.find(exp.Sum) is not None and denominator.find(exp.Count) is not None
            and tree.find(exp.Exists) is not None and not tree.args.get('joins'), 'Expected the verified semijoin aggregate')

    def cast(kind):return exp.Cast(this=numerator.copy(),to=exp.DataType.build(kind,dialect='postgres'))
    def divide(left):
        # Preserve PostgreSQL's typed division flag. A fresh dialect-neutral Div
        # may make sqlglot insert an unintended DOUBLE cast when rendering SQL.
        node=projection.copy();node.set('this',left);node.set('expression',denominator.copy())
        return node
    def scale(value):return exp.Mul(this=value,expression=exp.Literal.number(100))
    def query(expression):
        copy=tree.copy();copy.set('expressions',[exp.alias_(expression,'percentage',quoted=False)])
        return copy.sql(dialect='postgres')
    variants={
        'real_scaled_before':query(divide(scale(cast('REAL')))),
        'real_scaled_after':query(scale(divide(cast('REAL')))),
        'double_scaled_before':query(divide(scale(cast('DOUBLE PRECISION')))),
        'double_scaled_after':query(scale(divide(cast('DOUBLE PRECISION')))),
        'numeric_scaled_before':query(divide(scale(cast('NUMERIC')))),
        'numeric_unscaled':query(divide(cast('NUMERIC'))),
    }
    counts=tree.copy();counts.set('expressions',[
        exp.alias_(numerator.copy(),'conditional_entity_count',quoted=False),
        exp.alias_(denominator.copy(),'denominator_nonzero_count',quoted=False)])
    # Insert the count probe before the arithmetic variants in the bounded plan.
    return {'captured_counts':counts.sql(dialect='postgres'),**variants}


def context_variants(sql):
    """Reuse the captured actor/FK and title predicate; expose one factor at a time."""
    tree=captured_tree(sql)
    patterns=list(tree.find_all(exp.ILike))
    require(len(patterns)==1 and isinstance(patterns[0].this,exp.Column)
            and patterns[0].this.name=='title' and isinstance(patterns[0].expression,exp.Literal)
            and patterns[0].expression.is_string and tree.args.get('distinct') is not None,
            'Expected one captured title ILIKE predicate and DISTINCT actor projection')
    require(isinstance(tree.expressions[0],exp.Column), 'Expected a direct actor label projection')
    variants={}
    for use_like in (False,True):
        for distinct in (True,False):
            copy=tree.copy();title=next(copy.find_all(exp.ILike)).this.copy()
            copy.set('expressions',[copy.expressions[0].copy(),title])
            if use_like:
                node=next(copy.find_all(exp.ILike))
                node.replace(exp.Like(this=node.this.copy(),expression=node.expression.copy()))
            if not distinct:copy.set('distinct',None)
            name='context_'+('like' if use_like else 'ilike')+'_'+('distinct' if distinct else 'all')
            variants[name]=copy.sql(dialect='postgres')
    return variants


def query_plan(case,gold):
    require(case['case_id'] in CASE_IDS and case['case_id']==gold['case_id']
            and case['database_id']==gold['database_id'] and sql_sha(gold['gold_sql'])==gold['gold_sql_sha256'],
            'Probe case/Gold identity differs')
    variants=(numeric_variants if case['case_id']==CASE_IDS[0] else context_variants)(case['generated_sql'])
    plan={'captured_generated':case['generated_sql'],'frozen_gold':gold['gold_sql'],**variants}
    require(len(plan)==MAX_QUERIES[case['case_id']], 'Fixed audit query count differs')
    return plan


def projected(result,indices):
    columns=[result.columns[i] for i in indices];rows=[tuple(row[i] for i in indices) for row in result.rows]
    size=len(encoded({'columns':columns}))+sum(len(encoded([tagged(v) for v in row]))+1 for row in rows)
    return NativeResult(columns,rows,size)


def audit_case(runtime,case,gold,recorded,*,progress=None):
    started=time.monotonic()
    require(runtime.database_id==case['database_id']==gold['database_id']
            and runtime.identity.public()==case['source_identity']==recorded['source_identity'],
            'Live probe runtime differs from the accepted captured source')
    queries=query_plan(case,gold)
    # Fail the whole plan before any SELECT if a variant violates the existing
    # read-only/source/function policy. No function allowlist expansion is used.
    for sql in queries.values():validate_sql(sql,runtime.names)
    row=progress if progress is not None else {}
    row.update(case_id=case['case_id'],database_id=case['database_id'],status='running',
        source_identity=runtime.identity.public(),query_role=runtime.domain['query_role'],queries=queries,
        query_sha256={n:sql_sha(s) for n,s in queries.items()},results={},execution_events=[],batches=[],
        gold_execution_attempted=False,gold_executed=False,new_model_request_count=0,
        formal_benchmark=False,primary_ex=None,audit_sql_call_limit=len(queries),
        case_wall_timeout_seconds=600,per_batch_sql_limit=3,
        budget_scope='Trusted fixed-plan audit only. Each batch has <=3 SQL calls and 0 models; all batches share one 600-second case deadline. Agent budgets unchanged.')
    results={};budget=None
    for position,(name,sql) in enumerate(queries.items()):
        if position%3==0:
            # New counters do not grant more time: every batch uses the same
            # monotonic start, including nested executor deadlines.
            budget=Budget(total_limit=0,chat_limit=0,started=started)
            row['batches'].append(dict(batch_number=position//3+1,query_names=[],budget=budget.public()))
        batch=row['batches'][-1];batch['query_names'].append(name)
        budget.sql_call();event=dict(name=name,sql_sha256=sql_sha(sql),batch_number=batch['batch_number'],status='running')
        row['execution_events'].append(event)
        if name=='frozen_gold':row['gold_execution_attempted']=True
        try:
            result=runtime.execute_native(sql,budget)
            budget.remaining()
            require(result.complete is True, 'Incomplete result cannot enter native probe comparison')
            results[name]=result;row['results'][name]=native_record(result);event['status']='complete'
            if name=='frozen_gold':row['gold_executed']=True
        except Exception as error:
            event.update(status='failed',error=fault(error).public());row['status']='failed'
            raise
        finally:
            batch['budget']=budget.public()
            row['sql_execution_count']=sum(b['budget']['sql_tool_calls'] for b in row['batches'])
    predicted=results['captured_generated'];reference=results['frozen_gold']
    preserved=predicted.diagnostic()==case['result']==recorded['results']['captured_generated']['diagnostic']
    gold_preserved=reference.diagnostic()==recorded['results']['frozen_gold']['diagnostic']
    row.update(captured_native_diagnostic_preserved=preserved,frozen_native_diagnostic_preserved=gold_preserved)
    if not (preserved and gold_preserved):row['status']='failed'
    require(preserved and gold_preserved,'Captured/Gold results changed since accepted v2 native execution')
    row['native_comparisons']={name:native_difference(result,reference) for name,result in results.items()
                               if name not in ('frozen_gold','captured_counts')}
    if case['case_id']==CASE_IDS[1]:
        row['factor_comparisons']={
            'ilike_vs_like_distinct':native_difference(results['context_ilike_distinct'],results['context_like_distinct']),
            'ilike_vs_like_all':native_difference(results['context_ilike_all'],results['context_like_all']),
            'distinct_vs_all_ilike':native_difference(results['context_ilike_distinct'],results['context_ilike_all']),
            'distinct_vs_all_like':native_difference(results['context_like_distinct'],results['context_like_all']),
            'captured_user_vs_gold_user':native_difference(predicted,projected(reference,[0])),
        }
    row.update(status='complete',elapsed_seconds=round(time.monotonic()-started,3),
        interpretation='Probe variants are reviewer hypotheses only. Matches do not replace the captured prediction or change its score.')
    return row


def run_audit(evidence,source_path,native_path,credentials_path,report,*,registry_factory=None):
    source,selected=load_cases(source_path,native_path,evidence)
    report.update(mode='trusted_units_context_probe',policy=POLICY,formal_benchmark=False,primary_ex=None,
        holdout_live_allowed=False,new_model_request_count=0,gold_executed=False,
        source_report_sha256=SOURCE_SHA,previous_native_report_sha256=NATIVE_SHA,
        producer_code_sha256=source['code_binding']['sha256'],code_binding=code_binding(),audit_code_sha256=audit_code(),
        source_binding=source_binding(evidence),selected_case_ids=list(CASE_IDS),cases=[],source_receipts=[],pools_closed=False,
        audit_sql_call_limit=15,scope='Read-only reviewer counterfactual probes. No model, Agent, retrieval or index build. Original candidate scores remain unchanged.')
    registry=(registry_factory or BirdRegistry)(evidence,credentials_path)
    try:
        with registry:
            for case,gold,recorded in selected:
                runtime=registry.get(case['database_id']);report['postgresql_connected']=True
                report['source_receipts'].append({k:v for k,v in runtime.receipt().items() if k not in ('catalog_content','content_guards','typed_tables')})
                row={};report['cases'].append(row)
                with hard_deadline(600,'units_context_audit_timeout'):
                    audit_case(runtime,case,gold,recorded,progress=row)
                require(code_binding()==report['code_binding'] and audit_code()==report['audit_code_sha256'],
                        'Code changed during trusted units/context audit')
                print(case['case_id']+' probe_queries='+str(row['sql_execution_count']),flush=True)
        report.update(run_status='complete',target_data_verified=True,probe_comparisons_complete=True,
            summary=dict(case_count=2,sql_execution_count=sum(c['sql_execution_count'] for c in report['cases']),
                captured_native_diagnostic_preserved_count=sum(c['captured_native_diagnostic_preserved'] for c in report['cases']),
                matching_variant_names={c['case_id']:[name for name,result in c['native_comparisons'].items()
                    if result['matches_frozen_gold']] for c in report['cases']},new_model_request_count=0,formal_ex_denominator=None,
                meaning='Complete means the probe plan finished. Matching hypothetical variants are not new model successes.'))
    finally:
        report['gold_executed']=any(c.get('gold_execution_attempted') for c in report['cases'])
        registry.close();report['pools_closed']=all(r.connections.closed for r in registry._runtimes.values())
