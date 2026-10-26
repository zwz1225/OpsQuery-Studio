"""Trusted native replay of captured development SQL. No Agent/model/index access."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.normalize_identifiers import normalize_identifiers
from sqlglot.optimizer.scope import traverse_scope

from evaluation.bird_protocol import compare_ex_rows
from scripts.m2_b_common import digest_file,digest_json,require
from .budgets import Budget,hard_deadline
from .evidence import public_cases,scorer_gold
from .manifest import code_binding,source_binding
from .native import tagged,encoded
from .semantics import native_record

POLICY='bird_captured_development_native_replay_v1'
SOURCE_SHA='4f08270884badfe30d896d5c5ac55c84a7eee1c1060891c2846a452949a4512a'


def sql_sha(sql):return hashlib.sha256(sql.encode('utf-8')).hexdigest()


def load_capture(path:Path,evidence):
    require(digest_file(path)==SOURCE_SHA,'Use the accepted immutable 14-case Schema coverage diagnostic report')
    row=json.loads(path.read_bytes())
    require(row.get('run_status')=='complete' and row.get('mode')=='diagnostic'
            and row.get('split')=='development_diagnostic_subset' and row.get('formal_benchmark') is False
            and row.get('gold_executed') is False and row.get('holdout_live_allowed') is False
            and row.get('primary_ex') is None and row.get('errors')==[]
            and row.get('source_binding')==source_binding(evidence),'Captured diagnostic scope/source differs')
    binding=row['code_binding'];current=code_binding()
    require(binding['sha256']==digest_json({k:v for k,v in binding.items() if k!='sha256'}),'Producer code binding digest differs')
    for key in ('evaluation/bird/runtime.py','evaluation/bird/sql.py','evaluation/bird/native.py',
                'evaluation/bird/budgets.py','evaluation/bird_protocol.py'):
        require(binding['files'][key]==current['files'][key],'Replay execution/scoring policy changed: '+key)
    approved={c['case_id']:c for c in public_cases('development80')}
    cases=row['cases'];ids=[c['case_id'] for c in cases]
    require(len(cases)==len(set(ids))==14 and ids==row['selected_case_ids'] and set(ids)<=set(approved),
            'Captured cases must be the unique approved development subset')
    selected=[];excluded=[]
    for c in cases:
        require(c['database_id']==approved[c['case_id']]['database_id'] and c.get('mode')=='diagnostic'
                and c.get('ex_correct') is None and c.get('gold_sql_sha256') is None
                and c.get('runtime_closed') is True and c.get('errors')==[], 'Captured case identity/termination differs')
        if c['status']=='clarification':
            require(c['complete'] is False and not c.get('generated_sql') and not c.get('executions'),
                    'Excluded clarification unexpectedly contains executed SQL')
            excluded.append({'case_id':c['case_id'],'database_id':c['database_id'],'reason':'clarification_without_executed_sql'})
            continue
        require(c['status']=='diagnostic_answered' and c['complete'] is True and c['result']['complete'] is True
                and isinstance(c.get('generated_sql'),str) and len(c['executions'])==1
                and c['executions'][0]['success'] is True and c['executions'][0]['diagnostic']==c['result'],
                'Only complete captured SQL executions may enter replay')
        events=[v for v in c['development_diagnostics']['attempts'] if v['kind']=='execute']
        require(len(events)==1 and events[0]['success'] is True,'Captured execution event missing')
        record=events[0]['sql'];text=c['generated_sql']
        require(record['provided'] is True and record['truncated'] is False and record['redacted'] is False
                and record['text']==text and record['original_sha256']==sql_sha(text)
                and record['original_utf8_bytes']==len(text.encode('utf-8')),'Captured SQL bytes differ')
        selected.append(c)
    require(len(selected)==10 and len(excluded)==4,'Expected ten executed SQLs and four explicit exclusions')
    # Gold stays exclusively in this trusted replay process, after development scope is checked.
    gold=scorer_gold();pairs=[]
    for c in selected:
        g=gold[c['case_id']]
        require(g['case_id']==c['case_id'] and g['database_id']==c['database_id'] and g['dialect']=='postgres'
                and sql_sha(g['gold_sql'])==g['gold_sql_sha256'],'Frozen development Gold identity differs')
        pairs.append((c,g))
    return row,pairs,excluded


def structure(sql):
    try:trees=[t for t in sqlglot.parse(sql,read='postgres') if t is not None]
    except sqlglot.errors.SqlglotError:return {'available':False,'reason':'parse_failed'}
    if len(trees)!=1 or not isinstance(trees[0],exp.Query):return {'available':False,'reason':'not_single_query'}
    tree=normalize_identifiers(trees[0],dialect='postgres')
    projections=list(tree.selects)
    order=tree.args.get('order')
    tables=set()
    for scope in traverse_scope(tree):
        tables.update(t.name for t in scope.sources.values() if isinstance(t,exp.Table))
    return {'available':True,'projection_expression_count':len(projections),
        'projection_star':any(isinstance(v,exp.Star) or isinstance(v,exp.Column) and isinstance(v.this,exp.Star) for v in projections),
        'physical_tables':sorted(tables),
        'string_literals':sorted({v.this for v in tree.find_all(exp.Literal) if v.is_string}),
        'where_column_names':sorted({c.name for w in tree.find_all(exp.Where) for c in w.find_all(exp.Column)}),
        'root_order':[{'expression':o.this.sql(dialect='postgres'),'descending':bool(o.args.get('desc')),
                       'nulls_first':o.args.get('nulls_first')} for o in order.expressions] if order else []}


def reviewer_hints(predicted_sql,gold_sql):
    """Reference-based hypotheses for reviewers only; never an Agent repair API."""
    predicted=structure(predicted_sql);gold=structure(gold_sql);codes=[]
    if not predicted['available'] or not gold['available']:
        return {'scope':'trusted_reviewer_only_not_model_feedback','causes_confirmed':False,
                'codes':['structural_analysis_unavailable'],'prediction_structure':predicted,'reference_structure':gold}
    if predicted['projection_star'] and not gold['projection_star']:codes.append('projection_star_vs_reference_projection')
    if predicted['projection_expression_count']!=gold['projection_expression_count']:codes.append('projection_expression_count_differs')
    if predicted['physical_tables']!=gold['physical_tables']:codes.append('referenced_tables_differ')
    missing=sorted(set(gold['where_column_names'])-set(predicted['where_column_names']))
    if missing:codes.append('reference_where_columns_absent_from_prediction')
    missing_literals=sorted(set(gold['string_literals'])-set(predicted['string_literals']))
    if missing_literals:codes.append('reference_literals_absent_from_prediction')
    case_pairs=[{'prediction':a,'reference':b} for a in predicted['string_literals'] for b in gold['string_literals']
                if a!=b and a.casefold()==b.casefold()]
    if case_pairs:codes.append('case_only_literal_difference')
    po=predicted['root_order'];go=gold['root_order']
    if (po and len(po)==len(go) and [v['descending'] for v in po]==[v['descending'] for v in go]
            and [v['nulls_first'] for v in po]!=[v['nulls_first'] for v in go]):
        codes.append('root_order_null_policy_differs')
    return {'scope':'trusted_reviewer_only_not_model_feedback','causes_confirmed':False,'codes':codes,
        'prediction_structure':predicted,'reference_structure':gold,'missing_where_columns':missing,
        'missing_reference_literals':missing_literals,'case_only_literal_pairs':case_pairs,
        'meaning':'Structural differences are hypotheses, not automatic SQL rewrites or scoring overrides.'}


def native_difference(predicted,gold):
    matches=compare_ex_rows(predicted.rows,gold.rows,predicted_complete=predicted.complete,gold_complete=gold.complete)
    ps=set(predicted.rows);gs=set(gold.rows);codes=[]
    if not matches:
        if len(predicted.columns)!=len(gold.columns):codes.append('column_count_differs')
        if not ps and gs:codes.append('prediction_empty_gold_nonempty')
        elif ps and not gs:codes.append('prediction_nonempty_gold_empty')
        if ps-gs:codes.append('prediction_has_nonreference_tuples')
        if gs-ps:codes.append('prediction_missing_reference_tuples')
    def samples(rows,other):
        chosen=[];seen=set();size=0;omitted=0
        for row in rows:
            if row not in other and row not in seen:
                seen.add(row);value=[tagged(v) for v in row];n=len(encoded(value))
                if size+n>65536:omitted+=1;continue
                chosen.append(value);size+=n
                if len(chosen)==5:break
        return {'rows':chosen,'utf8_bytes':size,'oversized_rows_omitted':omitted,
                'preview_truncated':len(chosen)<len(set(rows)-other)}
    return {'matches_frozen_gold':matches,'difference_codes':codes,
        'prediction_row_count':len(predicted.rows),'gold_row_count':len(gold.rows),
        'prediction_column_count':len(predicted.columns),'gold_column_count':len(gold.columns),
        'prediction_unique_tuple_count':len(ps),'gold_unique_tuple_count':len(gs),
        'prediction_only_tuple_count':len(ps-gs),'gold_only_tuple_count':len(gs-ps),
        'prediction_only_preview':samples(predicted.rows,gs),'gold_only_preview':samples(gold.rows,ps),
        'preview_only':True,'difference_preview_row_limit':5,'difference_preview_utf8_byte_limit':65536,
        'native_type_sets_differ':predicted.diagnostic()['native_types']!=gold.diagnostic()['native_types'],
        'comparison_policy':'frozen native tuple-set predicate; names/order/duplicate multiplicity ignored; no rounding or coercion'}


def replay_case(runtime,case,gold,*,progress=None):
    require(case['case_id']==gold['case_id'] and case['database_id']==gold['database_id']==runtime.database_id
            and runtime.identity.public()==case['source_identity'],'Replay runtime/captured source differs')
    require(sql_sha(gold['gold_sql'])==gold['gold_sql_sha256'],'Frozen Gold bytes changed before replay')
    budget=Budget(total_limit=0,chat_limit=0);record=progress if progress is not None else {}
    queries={'captured_generated':case['generated_sql'],'frozen_gold':gold['gold_sql']};results={}
    record.update(case_id=case['case_id'],database_id=case['database_id'],status='running',source_identity=runtime.identity.public(),
        query_role=runtime.domain['query_role'],queries=queries,
        generated_sql_sha256=sql_sha(case['generated_sql']),gold_sql_sha256=gold['gold_sql_sha256'],
        gold_execution_attempted=False,gold_executed=False,execution_events=[],results={},
        new_model_request_count=0,replay_sql_call_limit=2,formal_benchmark=False,primary_ex=None)
    for name,sql in queries.items():
        budget.sql_call();event={'name':name,'sql_sha256':sql_sha(sql),'status':'running'};record['execution_events'].append(event)
        if name=='frozen_gold':record['gold_execution_attempted']=True
        try:
            results[name]=runtime.execute_native(sql,budget)
            require(results[name].complete is True,'Incomplete native replay result')
            event['status']='complete';record['results'][name]=native_record(results[name])
            if name=='frozen_gold':record['gold_executed']=True
        except Exception as error:
            from .runtime import fault
            event.update(status='failed',error=fault(error).public());record['status']='failed'
            raise
        finally:record['budget']=budget.public()
    predicted=results['captured_generated'];expected=results['frozen_gold']
    record.update(status='complete',native_comparison=native_difference(predicted,expected),
        recorded_prediction_diagnostic=case['result'],
        captured_native_diagnostic_preserved=predicted.diagnostic()==case['result'],
        reviewer_hypotheses=reviewer_hints(case['generated_sql'],gold['gold_sql']))
    return record


def run_replay(evidence,source_path,credentials_path,report,*,registry_factory=None,capture_loader=None):
    from .runtime import BirdRegistry
    source,selected,excluded=(capture_loader or load_capture)(source_path,evidence)
    report.update(mode='trusted_captured_sql_replay',policy=POLICY,formal_benchmark=False,primary_ex=None,
        holdout_live_allowed=False,gold_executed=False,new_model_request_count=0,
        source_report_sha256=digest_file(source_path),producer_code_sha256=source['code_binding']['sha256'],
        source_binding=source_binding(evidence),code_binding=code_binding(),source_case_count=len(source['cases']),
        selected_case_ids=[c['case_id'] for c,g in selected],excluded_cases=excluded,cases=[],source_receipts=[],pools_closed=False,
        replay_budget_scope='Independent trusted audit: 2 SELECT executions per selected case, 600 seconds, 0 model attempts. Original Agent budgets unchanged.')
    registry=(registry_factory or BirdRegistry)(evidence,credentials_path);seen=set()
    try:
        with registry:
            for case,gold in selected:
                runtime=registry.get(case['database_id']);report['postgresql_connected']=True
                if runtime.database_id not in seen:
                    receipt=runtime.receipt()
                    report['source_receipts'].append({k:v for k,v in receipt.items() if k not in ('catalog_content','content_guards','typed_tables')})
                    seen.add(runtime.database_id)
                row={};report['cases'].append(row)
                with hard_deadline(600,'native_replay_timeout'):replay_case(runtime,case,gold,progress=row)
                require(code_binding()==report['code_binding'],'Code changed during captured SQL replay')
        require(all(r.connections.closed for r in registry._runtimes.values()),'Replay pool did not close')
        actual=report['cases'];matches=sum(c['native_comparison']['matches_frozen_gold'] for c in actual)
        report['fixed_error_list']=[{'case_id':c['case_id'],'generated_sql_sha256':c['generated_sql_sha256'],'gold_sql_sha256':c['gold_sql_sha256'],
            'data_version':c['source_identity']['data_version'],'difference_codes':c['native_comparison']['difference_codes'],
            'reviewer_hypothesis_codes':c['reviewer_hypotheses']['codes'],'captured_native_diagnostic_preserved':c['captured_native_diagnostic_preserved']}
            for c in actual if not c['native_comparison']['matches_frozen_gold']]
        report.update(run_status='complete',target_data_verified=True,native_comparisons_complete=True,
            summary={'source_case_count':len(source['cases']),'replayed_case_count':len(actual),'excluded_case_count':len(excluded),
                'native_match_count':matches,'native_mismatch_count':len(actual)-matches,
                'captured_native_diagnostic_preserved_count':sum(c['captured_native_diagnostic_preserved'] for c in actual),
                'replay_sql_execution_count':sum(c['budget']['sql_tool_calls'] for c in actual),'new_model_request_count':0,
                'formal_ex_denominator':None,'meaning':'Native comparisons of saved SQL only; no new live generation or formal EX score.'})
    finally:
        report['gold_executed']=any(c.get('gold_execution_attempted') for c in report['cases'])
        registry.close();report['pools_closed']=all(r.connections.closed for r in registry._runtimes.values())
