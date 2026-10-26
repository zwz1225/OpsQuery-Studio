"""One registered formal holdout30 attempt for the frozen v4 candidate."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import tempfile
import time

from scripts.m2_b_common import BASE, PROTOCOL_DIR, digest_file, digest_json, require, safe_error, write_new_json
from scripts.m2_b_target import DEFAULT_CREDENTIALS, journal, live_dependencies
from scripts.check_m2_c_bird_runtime import budget_checks
from scripts.run_m2_v4_development80 import checkpoint
from scripts import m2_holdout_control as control
from scripts.m2_holdout_worker import run_process
from evaluation.bird.budgets import BirdFailure
from evaluation.bird.evidence import DEFAULT_DATA, DEFAULT_RESULTS, public_cases, scorer_gold
from evaluation.bird.model import ModelConfig
from evaluation.bird.manifest import source_binding
from evaluation.bird.runtime import BirdRegistry, fault
from evaluation.bird.retrieval import build_index
from evaluation.bird.supervisor import isolation_probe, run_case_process
from evaluation.bird.metrics import summarize


def report_paths(args):
    require(args.output is not None, '--output is required for checks and execution')
    output = args.output.resolve()
    protected = [PROTOCOL_DIR, args.data_root, args.credentials_file, args.model_config_file,
                 args.index_root, control.CANDIDATE_PATH, control.LEDGER_ROOT]
    protected += [DEFAULT_RESULTS/name for name in (control.DEVELOPMENT, control.DEVELOPMENT_NATIVE,
        'm2_b_postgres_validation_server.json', 'm2_b_postgres_import_server.json',
        'm2_b_postgres_initialization_server.json', 'm2_c_bird_development80_server.json',
        'm2_c_bird_runtime_server.json', 'm2_c_bird_gold110_server.json')]
    require(output.suffix == '.json' and output.is_relative_to(DEFAULT_RESULTS.resolve()),
            'Holdout report must be a JSON within the canonical results directory')
    require(not any(output == p.resolve() or output.is_relative_to(p.resolve()) for p in protected),
            'Report overlaps protected evidence or ledger')
    require(not output.exists(), 'Choose a new report path; preserve previous evidence')
    require(not args.index_root.resolve().is_relative_to(PROTOCOL_DIR.resolve())
        and not args.index_root.resolve().is_relative_to(args.data_root.resolve()), 'Index overlaps frozen inputs')
    return protected


def preflight(args):
    live_dependencies()
    frozen = control.candidate()
    config = ModelConfig.load(args.model_config_file)
    evidence = control.evidence_preflight(frozen, args.data_root, DEFAULT_RESULTS, config)
    # Static checks do not register an attempt, access PG passwords, or invoke a model.
    require(args.credentials_file.is_file(), 'M2 role credential file is missing')
    require(not (control.LEDGER_ROOT/frozen['candidate_id']).exists(),
            'Candidate attempt is already reserved; inspect --status, do not repeat generation')
    return frozen, evidence, config


def gold_ready(case, public, gold):
    return (case.get('case_id') == public['case_id'] and case.get('database_id') == public['database_id']
        and case.get('mode') == 'gold' and case.get('gold_sql_sha256') == gold['gold_sql_sha256']
        and case.get('status') == 'gold_ready' and case.get('complete') is True
        and case.get('runtime_closed') is True and case.get('new_model_request_count') == 0
        and case.get('errors') == [] and all(case.get('result', {}).get(k) is True
            for k in ('complete', 'within_row_limit', 'within_payload_limit', 'native_hashable')))


def finish_summary(report, metadata):
    cases = report['cases']
    require(len(cases) == 30 and [c['case_id'] for c in cases] == report['selected_case_ids'],
            'Holdout must account for all30 in frozen order')
    unknown = any(c.get('new_model_request_count') is None for c in cases)
    observed = sum(c.get('new_model_request_count') or 0 for c in cases)
    gold_calls = sum(c.get('gold_execution_attempted') is True for c in cases)
    summary = summarize(cases, metadata, 'live')
    summary.update(new_model_request_count=None if unknown else observed, observed_case_http_attempts=observed,
        model_attempt_count_incomplete=unknown,
        shared_index_http_attempts=sum((i['model_usage'] or {}).get('model_http_attempts', 0) for i in report['index_builds']),
        generation_sql_tool_calls=sum(c.get('budget', {}).get('sql_tool_calls', 0) for c in cases),
        trusted_case_gold_execution_attempts=gold_calls,
        gold_readiness_sql_count=len(report['gold_readiness_cases']),
        usage_scope='Readiness and case Gold are recorded separately; unknown killed-worker usage is not zero.')
    report.update(summary=summary, primary_ex=summary['primary_ex'], primary_denominator=30,
                  new_model_request_count=None if unknown else observed)


def registered_run(args, frozen, evidence, config, attempt, report):
    inputs = public_cases('holdout30')
    selected = control.read(PROTOCOL_DIR/'holdout30.json')
    require(len(inputs) == 30 and [v['case_id'] for v in inputs] == selected['case_ids'], 'Frozen holdout selection differs')
    metadata = {v['case_id']: v for v in selected['selection_metadata']}
    gold = scorer_gold()
    report.update(mode='live', split='holdout30', formal_benchmark=True,
        official_leaderboard_score=False, benchmark_scope=frozen['payload']['scope'],
        holdout_live_allowed=True, candidate_id=frozen['candidate_id'], candidate_sha256=frozen['candidate_sha256'],
        candidate_file_sha256=digest_file(control.CANDIDATE_PATH), attempt_id=attempt.id,
        attempt_ledger=str(attempt.path), code_binding=frozen['payload']['producer_binding'],
        controller_files=frozen['payload']['controller_files'], source_binding=source_binding(evidence),
        model_configuration=config.public(), selected_case_ids=[v['case_id'] for v in inputs],
        selected_input_sha256=digest_json(inputs), primary_denominator=30, primary_ex=None,
        cases=[], index_builds=[], source_receipts=[], gold_readiness_cases=[], new_model_request_count=None,
        generation_worker_policy=frozen['payload']['intent_candidate_policy'],
        scoring_contract=frozen['payload']['scoring'], workers=1,
        holdout_usage='First registered attempt; partial/failed runs are preserved and cannot silently restart.')
    checkpoint(args.output, report, 'isolation_and_budget_probes')
    report['budget_counter_probes'] = budget_checks()
    with tempfile.TemporaryDirectory(prefix='bird_holdout_probe_') as directory:
        private = Path(directory)/'private'
        private.write_bytes(b'private')
        report['current_isolation_probe'] = isolation_probe([private, PROTOCOL_DIR/'scorer/gold110.jsonl',
            args.data_root/evidence.manifest['question_relative_path'], args.credentials_file])
    try:
        run_case_process({'mode': 'watchdog_probe'}, seconds=1)
    except BirdFailure as error:
        require(error.category == 'case_wall_timeout', 'Unexpected watchdog probe result')
    else:
        require(False, 'Hard timeout probe did not terminate')
    report['current_timeout_probe'] = dict(passed=True, formal_case_timeout_seconds=600)
    attempt.event('probes_passed')
    receipts, indexes = {}, {}
    checkpoint(args.output, report, 'live_source_verification')
    with BirdRegistry(evidence, args.credentials_file) as registry:
        for db in sorted({v['database_id'] for v in inputs}):
            receipts[db] = registry.get(db).receipt()
            report['postgresql_connected'] = True
            print('Verified holdout source: '+db, flush=True)
        report['source_receipts'] = [{k: v for k, v in receipts[db].items()
            if k not in ('catalog_content', 'content_guards', 'typed_tables')} for db in sorted(receipts)]
        checkpoint(args.output, report, 'fresh_gold30_readiness')
        # No model/index requests until every original holdout Gold is ready.
        for position, public in enumerate(inputs, 1):
            g = gold[public['case_id']]
            request = dict(mode='gold', gold=g, receipt=receipts[public['database_id']],
                data_root=str(args.data_root), results_dir=str(DEFAULT_RESULTS),
                credentials_file=str(args.credentials_file), code_sha256=report['code_binding']['sha256'])
            try:
                result = run_case_process(request, seconds=600)
            except Exception as error:
                failure = fault(error)
                result = dict(case_id=public['case_id'], database_id=public['database_id'], mode='gold',
                    status=failure.category, complete=False, errors=[failure.public()], new_model_request_count=0)
            if result.get('case_id') != public['case_id']:
                result = dict(case_id=public['case_id'], database_id=public['database_id'], mode='gold',
                    status='gold_readiness_identity_mismatch', complete=False, worker_report=result,
                    errors=[{'category': 'gold_readiness_identity_mismatch'}], new_model_request_count=0)
            # A malformed/crashed readiness worker is not acceptable environment evidence.
            report['gold_readiness_cases'].append(result)
            attempt.gold(result)
            checkpoint(args.output, report, 'fresh_gold30_readiness')
            require(gold_ready(result, public, g), 'Fresh holdout Gold readiness failed; no Agent will start')
            print(f'Gold readiness [{position}/30] {public["case_id"]}', flush=True)
        report['fresh_gold30_ready'] = True
        attempt.event('all_gold_ready', case_count=30)
        checkpoint(args.output, report, 'authorized_index_preparation')
        for db in sorted(receipts):
            item = build_index(registry.get(db), config, args.index_root)
            report['index_builds'].append(item)
            indexes[db] = item['path']
            attempt.event('index_ready', database_id=db, index_sha256=item['sha256'], cache_hit=item['cache_hit'],
                          model_usage=item['model_usage'])
            checkpoint(args.output, report, 'authorized_index_preparation')
    require(all(r.connections.closed for r in registry._runtimes.values()), 'Preparation pools did not close')
    report['preparation_pools_closed'] = True
    checkpoint(args.output, report, 'holdout_generation_and_scoring')
    for position, public in enumerate(inputs, 1):
        require(control.candidate()['candidate_sha256'] == frozen['candidate_sha256'], 'Candidate changed before case')
        g = gold[public['case_id']]
        attempt.event('case_started', case_id=public['case_id'])
        started = time.monotonic()
        request = dict(input=public, gold=g, candidate_sha256=frozen['candidate_sha256'],
            receipt=receipts[public['database_id']], data_root=str(args.data_root), results_dir=str(DEFAULT_RESULTS),
            credentials_file=str(args.credentials_file), index_path=indexes[public['database_id']],
            code_sha256=report['code_binding']['sha256'],
            model_config_private=dict(api_key=config.api_key, chat_base=config.chat_base,
                embedding_base=config.embedding_base, rerank_base=config.rerank_base))
        try:
            case = run_process(request, seconds=600)
            require(case.get('case_id') == public['case_id'] and case.get('database_id') == public['database_id']
                and case.get('mode') == 'live' and case.get('gold_sql_sha256') == g['gold_sql_sha256'],
                'Holdout worker identity differs')
        except Exception as error:
            failure = fault(error)
            case = dict(case_id=public['case_id'], database_id=public['database_id'], mode='live',
                status=failure.category, complete=False, ex_correct=False, gold_sql_sha256=g['gold_sql_sha256'],
                errors=[failure.public()], new_model_request_count=None, runtime_closed=None,
                usage_status='Unknown after worker termination; never represented as zero')
        require(control.candidate()['candidate_sha256'] == frozen['candidate_sha256'], 'Candidate changed during case')
        case['case_wall_seconds'] = round(time.monotonic()-started, 3)
        report['cases'].append(case)
        attempt.case(case)
        checkpoint(args.output, report, 'holdout_generation_and_scoring')
        print(f'[{position}/30] {public["case_id"]} status={case["status"]} EX={case.get("ex_correct")}', flush=True)
    finish_summary(report, metadata)
    report.update(run_status='complete', target_data_verified=True)
    checkpoint(args.output, report, 'complete')
    snapshot = DEFAULT_RESULTS/'snapshots/bird_holdout'/frozen['candidate_id']/attempt.id/'report.json'
    write_new_json(snapshot, report)
    report['snapshot'] = dict(path=str(snapshot), sha256=digest_file(snapshot))
    attempt.event('completed', case_count=30, primary_ex=report['primary_ex'],
        report_content_sha256=digest_json(report), hash_scope='root report excluding journal finished_at')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-only', action='store_true')
    mode.add_argument('--execute', action='store_true')
    mode.add_argument('--status', action='store_true')
    parser.add_argument('--data-root', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--credentials-file', type=Path, default=DEFAULT_CREDENTIALS)
    parser.add_argument('--model-config-file', type=Path, default=BASE/'.env')
    parser.add_argument('--index-root', type=Path, default=BASE/'data/bird_indexes/m2_bird_pg_v1')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.status:
        rows = []
        if control.LEDGER_ROOT.exists():
            for path in sorted(control.LEDGER_ROOT.iterdir()):
                if path.is_dir():
                    try:
                        rows.append(dict(candidate=path.name, **control.verify_ledger(path)))
                    except Exception:
                        rows.append(dict(candidate=path.name, state='interrupted_or_changed; retry remains forbidden'))
        print(json.dumps(dict(registered_attempts=rows), ensure_ascii=False, indent=2))
        return
    for key in ('data_root', 'credentials_file', 'model_config_file', 'index_root', 'output'):
        if getattr(args, key) is not None:
            setattr(args, key, getattr(args, key).resolve())
    protected = report_paths(args)
    with journal(args.output, 'M2 frozen v4 holdout30 controlled attempt', protected=protected) as report:
        frozen, evidence, config = preflight(args)
        if args.check_only:
            report.update(run_status='complete', phase='static_preflight_only', candidate_id=frozen['candidate_id'],
                candidate_sha256=frozen['candidate_sha256'], new_model_request_count=0,
                attempt_registered=False, live_readiness_verified=False)
        else:
            attempt = control.reserve(frozen)
            try:
                registered_run(args, frozen, evidence, config, attempt, report)
            except BaseException as error:
                attempt.event('failed_or_interrupted', error=safe_error(error),
                              saved_case_count=len(report.get('cases', [])))
                raise
    raise SystemExit(0 if report['run_status'] == 'complete' else 1)


if __name__ == '__main__':
    main()
