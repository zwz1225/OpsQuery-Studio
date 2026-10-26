"""Trusted, immutable three-case audit of captured grain-rule rejections.

Reviewer entry only: no model, retrieval, SQL rewriting or candidate score update.
New audit code stays outside evaluation/bird so its installation cannot change
the producer/index code binding of the accepted v3 development80 capture.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.m2_b_common import digest_file, require
from evaluation.bird.budgets import Budget, hard_deadline
from evaluation.bird.evidence import public_cases, scorer_gold
from evaluation.bird.intent import violations
from evaluation.bird.intent_replay import load_candidate_capture
from evaluation.bird.manifest import code_binding, source_binding
from evaluation.bird.replay import native_difference, sql_sha
from evaluation.bird.runtime import BirdRegistry, fault
from evaluation.bird.semantics import native_record
from evaluation.bird.sql import validate_sql

SOURCE_SHA = '8823926748c359d43ae011e94a1bed8fe5cf592599170c831840d51325ad398b'
NATIVE_SHA = 'a6b2cadaff7bf20e47ab210182c05029c98ab61b4adef803a5d9450fd832a551'
CASE_IDS = ('BIRD-PG-0263', 'BIRD-PG-0273', 'BIRD-PG-0201')
FIRST_SQL_SHA = {
    'BIRD-PG-0263': '6fcec9046c5f086570367b6a035e534855db26b77f7574e462300202de36cf2a',
    'BIRD-PG-0273': '870ad5ada6442f164706a9b854ba021678eec9b2b4f84e8fbfd448b6d8312a40',
    'BIRD-PG-0201': 'ee1f6ae3964acea89ec6842895f48d6f199405da433ce68c8e37d370c95bd044',
}
POLICY = 'bird_captured_grain_rejection_audit_v1'
SQL_LIMITS = {'BIRD-PG-0263': 3, 'BIRD-PG-0273': 2, 'BIRD-PG-0201': 3}


def audit_code():
    return {name: digest_file(Path(__file__).with_name(name)) for name in
            ('m2_grain_diagnostics.py', 'check_m2_grain_diagnostics.py')}


def captured_first(case):
    """Select the exact first decision and its original rejection; never synthesize SQL."""
    cid = case['case_id']
    require(cid in CASE_IDS, 'Only the fixed three development captures are admitted')
    events = case['development_diagnostics']['attempts']
    decisions = [v for v in events if v['kind'] == 'model_decision']
    validations = [v for v in events if v['kind'] == 'validate']
    require(decisions and validations and decisions[0]['action'] == 'query', 'First query capture is missing')
    decision, validation = decisions[0], validations[0]
    sql = decision['sql']
    require(validation['sql'] == sql and events.index(decision) < events.index(validation)
            and not any(v['kind'] == 'execute' for v in events[:events.index(validation)]),
            'First rejection must precede native SQL execution')
    require(sql.get('provided') is True and sql.get('truncated') is False and sql.get('redacted') is False
            and isinstance(sql.get('text'), str) and sql['original_sha256'] == sql_sha(sql['text']) == FIRST_SQL_SHA[cid]
            and sql['original_utf8_bytes'] == len(sql['text'].encode('utf-8')), 'First SQL bytes differ')
    feedback = validation.get('repair_feedback', {})
    expected = ['entity_grain_fanout'] if cid != 'BIRD-PG-0273' else ['missing_population_condition', 'entity_grain_fanout']
    require(validation['success'] is False and validation['error'] == dict(category='intent_contract_violation', sqlstate=None)
            and feedback.get('failed_sql') == sql and feedback.get('source_identity') == case['source_identity']
            and [v['code'] for v in feedback.get('intent_violations', [])] == expected,
            'Recorded first grain rejection differs')
    return sql, validation


def query_plan(case, gold):
    cid = case['case_id']
    require(cid in CASE_IDS and gold['case_id'] == cid and case['database_id'] == gold['database_id'] == 'toxicology'
            and gold['dialect'] == 'postgres' and sql_sha(gold['gold_sql']) == gold['gold_sql_sha256'],
            'Fixed development case/Gold identity differs')
    first, _ = captured_first(case)
    plan = {'captured_first_rejected': first['text']}
    final = case.get('generated_sql')
    if cid == 'BIRD-PG-0273':
        require(case['status'] == 'validation_failed' and final is None and case['executions'] == [],
                '0273 must remain an originally unexecuted validation failure')
    else:
        require(case['status'] == 'diagnostic_answered' and isinstance(final, str), 'Captured final SQL is missing')
        plan['captured_final'] = final
    plan['frozen_gold'] = gold['gold_sql']
    require(len(plan) == SQL_LIMITS[cid] <= 3, 'Fixed diagnostic SQL limit differs')
    return plan


def load_cases(source_path, native_path, evidence):
    require(digest_file(source_path) == SOURCE_SHA and digest_file(native_path) == NATIVE_SHA,
            'Use the accepted immutable v3 development80 rerun_v2 diagnostic/native reports')
    source = json.loads(source_path.read_bytes())
    native = json.loads(native_path.read_bytes())
    require(source.get('code_binding') == native.get('code_binding') == code_binding()
            and native.get('producer_code_sha256') == source['code_binding']['sha256']
            and native.get('source_binding') == source.get('source_binding') == source_binding(evidence)
            and native.get('source_report_sha256') == SOURCE_SHA
            and native.get('run_status') == 'complete' and native.get('errors') == []
            and native.get('formal_benchmark') is False and native.get('primary_ex') is None
            and native.get('holdout_live_allowed') is False and native.get('new_model_request_count') == 0
            and native.get('native_comparisons_complete') is True and native.get('pools_closed') is True
            and native.get('target_data_verified') is True and native.get('gold_executed') is True,
            'Accepted producer/source/environment or native termination differs')
    # Existing capture loader checks all 80 case lifecycles, identities, budgets,
    # exact final SQL captures and development-only scope before a DB is opened.
    checked, pairs, excluded = load_candidate_capture(source_path, evidence, SOURCE_SHA)
    require(len(checked['cases']) == 80 and checked['selected_case_ids'] == [c['case_id'] for c in public_cases('development80')]
            and len(pairs) == 76 and len(excluded) == 4 and native['excluded_cases'] == excluded
            and native['selected_case_ids'] == [c['case_id'] for c, g in pairs], 'Expected the exact development80/76 chain')
    recorded = {c['case_id']: c for c in native['cases']}
    require(len(recorded) == len(native['cases']) == 76 and set(recorded) == set(native['selected_case_ids']),
            'Native replay case inventory differs')
    for case, gold in pairs:
        old = recorded[case['case_id']]
        require(old['status'] == 'complete' and old['source_identity'] == case['source_identity']
                and old['query_role'] == case['query_role'] and old['queries'] == {
                    'captured_generated': case['generated_sql'], 'frozen_gold': gold['gold_sql']}
                and old['generated_sql_sha256'] == sql_sha(case['generated_sql'])
                and old['gold_sql_sha256'] == gold['gold_sql_sha256']
                and old['captured_native_diagnostic_preserved'] is True
                and old['results']['captured_generated']['diagnostic'] == case['result'],
                'Accepted native SQL/results chain differs')
    all_cases = {c['case_id']: c for c in checked['cases']}
    # 0273 had no executed result and was excluded from the previous native audit.
    # Load its frozen Gold only here, inside this trusted development-only review.
    golds = scorer_gold()
    selected = []
    for cid in CASE_IDS:
        case, gold = all_cases[cid], golds[cid]
        plan = query_plan(case, gold)
        for sql in plan.values():
            validate_sql(sql, set(evidence.domain(case['database_id'])['tables']))
        require((cid in recorded) == (cid != 'BIRD-PG-0273'), 'First-only/control provenance differs')
        selected.append((case, gold, recorded.get(cid)))
    return source, selected


def audit_case(runtime, case, gold, recorded, *, progress=None):
    require(runtime.database_id == case['database_id'] == 'toxicology'
            and runtime.identity.public() == case['source_identity']
            and runtime.domain['query_role'] == case['query_role'], 'Live diagnostic source or query role differs')
    first, rejection = captured_first(case)
    plan = query_plan(case, gold)
    for sql in plan.values():
        validate_sql(sql, runtime.names)
    budget = Budget(total_limit=0, chat_limit=0)
    row = progress if progress is not None else {}
    row.update(case_id=case['case_id'], database_id=case['database_id'], status='running',
               source_identity=runtime.identity.public(), query_role=runtime.domain['query_role'],
               original_status=case['status'], first_sql_previously_executed=False,
               queries=plan, query_sha256={k: sql_sha(v) for k, v in plan.items()},
               captured_first_sql=first, recorded_rejection=rejection,
               formal_benchmark=False, primary_ex=None, new_model_request_count=0,
               sql_call_limit=len(plan), case_wall_timeout_seconds=600,
               gold_execution_attempted=False, gold_executed=False, execution_events=[], results={},
               budget_scope='Trusted reviewer audit only: <=3 SELECTs, 0 models, one 600-second case deadline; Agent budgets unchanged.')
    results = {}
    try:
        # Reconstruct the recorded business rejection as evidence. It is not
        # used as an execution gate in this reviewer audit; all existing SQL
        # source/read-only/function/role/timeout protections still apply.
        public = next(c for c in public_cases('development80') if c['case_id'] == case['case_id'])
        current_reasons = violations(runtime, public, case['intent_contract'], first['text'])
        row['reconstructed_intent_violations'] = current_reasons
        require(current_reasons == rejection['repair_feedback']['intent_violations'], 'Recorded intent rejection cannot be reproduced')
        for name, sql in plan.items():
            budget.sql_call()
            event = dict(name=name, sql_sha256=sql_sha(sql), status='running')
            row['execution_events'].append(event)
            if name == 'frozen_gold': row['gold_execution_attempted'] = True
            try:
                result = runtime.execute_native(sql, budget)
                budget.remaining()
                require(result.complete is True, 'Partial result cannot enter grain diagnostics')
                results[name] = result
                row['results'][name] = native_record(result)
                event['status'] = 'complete'
                if name == 'frozen_gold': row['gold_executed'] = True
            except Exception as error:
                event.update(status='failed', error=fault(error).public())
                raise
            finally:
                row['budget'] = budget.public()
        if recorded is not None:
            final_preserved = results['captured_final'].diagnostic() == case['result'] == recorded['results']['captured_generated']['diagnostic']
            gold_preserved = results['frozen_gold'].diagnostic() == recorded['results']['frozen_gold']['diagnostic']
            row.update(previous_final_diagnostic_preserved=final_preserved, previous_gold_diagnostic_preserved=gold_preserved)
            require(final_preserved and gold_preserved, 'Previously executed final/Gold results changed')
        else:
            row.update(previous_final_diagnostic_preserved=None, previous_gold_diagnostic_preserved=None)
        reference = results['frozen_gold']
        comparisons = {'first_vs_gold': native_difference(results['captured_first_rejected'], reference)}
        if 'captured_final' in results:
            comparisons['final_vs_gold'] = native_difference(results['captured_final'], reference)
            comparisons['first_vs_final'] = native_difference(results['captured_first_rejected'], results['captured_final'])
            require(comparisons['final_vs_gold'] == recorded['native_comparison'], 'Previous native final comparison changed')
        row.update(native_comparisons=comparisons, status='complete',
                   interpretation='First-SQL matches are reviewer evidence about a recorded rejection, not new Agent successes or changes to the development80 score.')
        return row
    except BaseException:
        row['status'] = 'failed'
        raise
    finally:
        row['budget'] = budget.public()


def run_audit(evidence, source_path, native_path, credentials_path, report, *, registry_factory=None):
    print('Checking immutable development80 capture/native provenance; no model calls.', flush=True)
    source, selected = load_cases(source_path, native_path, evidence)
    report.update(mode='trusted_captured_grain_rejection_audit', policy=POLICY,
                  formal_benchmark=False, primary_ex=None, holdout_live_allowed=False,
                  source_report_sha256=SOURCE_SHA, previous_native_report_sha256=NATIVE_SHA,
                  producer_code_sha256=source['code_binding']['sha256'], code_binding=code_binding(), audit_code_sha256=audit_code(),
                  source_binding=source_binding(evidence), selected_case_ids=list(CASE_IDS),
                  cases=[], source_receipts=[], pools_closed=False, gold_executed=False, new_model_request_count=0,
                  audit_sql_call_limit=8, candidate_score_unchanged=True,
                  scope='Immutable rejected first SQL and saved final controls; no SQL variants, model, Agent, retrieval or index build.')
    registry = (registry_factory or BirdRegistry)(evidence, credentials_path)
    try:
        with registry:
            print('Verifying toxicology live data/catalog/ACL before the fixed 8-query audit.', flush=True)
            runtime = registry.get('toxicology')
            report['postgresql_connected'] = True
            report['source_receipts'].append({k:v for k,v in runtime.receipt().items()
                                             if k not in ('catalog_content','content_guards','typed_tables')})
            for case, gold, recorded in selected:
                row = {}
                report['cases'].append(row)
                with hard_deadline(600, 'grain_diagnostic_timeout'):
                    audit_case(runtime, case, gold, recorded, progress=row)
                require(code_binding() == report['code_binding'] and audit_code() == report['audit_code_sha256']
                        and digest_file(source_path) == SOURCE_SHA and digest_file(native_path) == NATIVE_SHA,
                        'Code or immutable evidence changed during grain diagnostics')
                print(case['case_id'] + ' first_match=' + str(row['native_comparisons']['first_vs_gold']['matches_frozen_gold'])
                      + ' final_match=' + str(row['native_comparisons'].get('final_vs_gold', {}).get('matches_frozen_gold')), flush=True)
        report.update(run_status='complete', target_data_verified=True, diagnostic_comparisons_complete=True,
                      summary=dict(case_count=len(report['cases']), sql_execution_count=sum(c['budget']['sql_tool_calls'] for c in report['cases']),
                          new_model_request_count=0, formal_ex_denominator=None,
                          first_matches_reference_case_ids=[c['case_id'] for c in report['cases']
                              if c['native_comparisons']['first_vs_gold']['matches_frozen_gold']],
                          first_and_final_outcomes={c['case_id']:dict(first_matches=c['native_comparisons']['first_vs_gold']['matches_frozen_gold'],
                              final_matches=c['native_comparisons'].get('final_vs_gold', {}).get('matches_frozen_gold'),
                              original_status=c['original_status']) for c in report['cases']},
                          meaning='Complete means the fixed audit finished; observed matches neither alter development80 accuracy nor imply every grain rejection is wrong.'))
    finally:
        report['gold_executed'] = any(c.get('gold_execution_attempted') for c in report['cases'])
        registry.close()
        report['pools_closed'] = all(r.connections.closed for r in registry._runtimes.values())
