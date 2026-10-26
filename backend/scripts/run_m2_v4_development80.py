"""Run the frozen v4 development80 capture, then independently replay saved SQL.

This orchestration lives outside the candidate's executable inventory. It does
not change Agent inputs, budgets, SQL, scoring, or the closed holdout split.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from scripts.m2_b_common import BASE, PROTOCOL_DIR, digest_file, now, require
from scripts.m2_b_target import DEFAULT_CREDENTIALS, journal, live_dependencies
from evaluation.bird.diagnostic_runner import prerequisites, select_development
from evaluation.bird.evidence import DEFAULT_DATA, DEFAULT_RESULTS, Evidence
from evaluation.bird.intent import policy
from evaluation.bird.intent_replay import load_candidate_capture
from evaluation.bird.manifest import code_binding, source_binding
from evaluation.bird.model import ModelConfig

ACCEPTED_CAPTURE = 'm2_public_intent_v4_diagnostics6_server.json'
ACCEPTED_NATIVE = 'm2_public_intent_v4_native6_server.json'
CAPTURE_SHA = '20ab65e3b05fb59767a67478ea9d8b5ed426ec9001bb660df9390c2b3023e712'
NATIVE_SHA = '1f7e9f974d678ae118007591b0d2c78d8d8495e4043321077e10627a6895c90a'
DELIVERY = BASE/'evaluation/m2_public_intent_v4_delivery_files_20261018.json'
DELIVERY_SHA = '72f5bea41dc2201c12a11aefd36c8052193316b39129a02b6a08cd0786f0bbec'
CASE_LIST = PROTOCOL_DIR/'development80.json'
CASE_LIST_SHA = '237b6f09f8b7ee9965f9e18b3ab2195a79b5ad949e55e6d56868a3266df29b10'


def read(path):
    return json.loads(path.read_bytes())


def paths(args):
    """Fail before generation if outputs collide with evidence or each other."""
    outputs = [args.output.resolve(), args.diagnostic_output.resolve(), args.native_output.resolve()]
    require(len(set(outputs)) == 3, 'Use three distinct report paths')
    protected = [args.data_root, PROTOCOL_DIR, args.credentials_file, args.model_config_file,
                 args.index_root, DELIVERY, Path(__file__)]
    protected += [args.results_dir/n for n in (ACCEPTED_CAPTURE, ACCEPTED_NATIVE,
        'm2_c_bird_development80_server.json', 'm2_c_bird_runtime_server.json',
        'm2_c_bird_gold110_server.json', 'm2_b_postgres_validation_server.json',
        'm2_b_postgres_import_server.json', 'm2_b_postgres_initialization_server.json')]
    for path in outputs:
        require(path.suffix == '.json' and path.is_relative_to(args.results_dir.resolve()),
                'All reports must be JSON paths within results-dir')
        require(not any(path == p.resolve() or path.is_relative_to(p.resolve()) for p in protected),
                'Report path overlaps protected inputs')
        require(not any(path.is_relative_to(other) for other in outputs if path != other),
                'Report paths overlap')
        if path == args.diagnostic_output.resolve() and args.replay_only:
            require(path.is_file(), 'Replay-only requires an existing complete diagnostic report')
        else:
            require(not path.exists(), 'Choose new output paths; preserve previous evidence')
    return protected


def preflight(args):
    """Static checks only: no connection, isolation worker, or model request."""
    live_dependencies()
    require(digest_file(DELIVERY) == DELIVERY_SHA, 'Reviewed v4 delivery manifest differs')
    delivery = read(DELIVERY)
    for name, sha in delivery['expected_files'].items():
        path = (BASE/name).resolve()
        require(path.is_relative_to(BASE) and path.is_file() and digest_file(path) == sha,
                'Reviewed v4 file differs: '+name)
    binding = code_binding()
    require(binding['files'] == delivery['expected_code_files'], 'Candidate executable inventory differs')
    require(digest_file(CASE_LIST) == CASE_LIST_SHA, 'Frozen development80 list differs')
    ids = [c['case_id'] for c in select_development(CASE_LIST)]
    require(len(ids) == 80, 'Exactly development80 is required')
    evidence = Evidence.load(args.data_root, args.results_dir)
    baseline = prerequisites(args.results_dir/'m2_c_bird_development80_server.json',
        args.results_dir/'m2_c_bird_runtime_server.json',
        args.results_dir/'m2_c_bird_gold110_server.json', evidence)
    require(ids == [c['case_id'] for c in baseline['cases']], 'Development order differs from baseline')
    capture = args.results_dir/ACCEPTED_CAPTURE
    accepted, _, _ = load_candidate_capture(capture, evidence, CAPTURE_SHA)
    require(accepted['schema_selection_policy'].get('coverage_enabled') is True,
            'Reviewed v4 Schema coverage is not enabled')
    require(digest_file(args.results_dir/ACCEPTED_NATIVE) == NATIVE_SHA,
            'Reviewed six-case native evidence differs')
    native = read(args.results_dir/ACCEPTED_NATIVE)
    require(native.get('run_status') == 'complete' and native.get('errors') == []
            and native.get('source_report_sha256') == CAPTURE_SHA
            and native.get('native_comparisons_complete') is True and native.get('pools_closed') is True
            and native.get('code_binding') == binding and native.get('source_binding') == source_binding(evidence),
            'Reviewed v4 native provenance differs')
    require(accepted['model_configuration'] == baseline['model_configuration'],
            'Reviewed v4 model differs from baseline')
    # Native-only recovery does not need an API key or read the model config.
    if not args.replay_only:
        require(ModelConfig.load(args.model_config_file).public() == accepted['model_configuration'],
                'Current public model configuration differs from reviewed v4')
    require(args.credentials_file.is_file(), 'M2 PostgreSQL credential file is missing')
    return evidence, ids, accepted


def complete_capture(path, evidence, ids, accepted):
    """Use the existing strict native-loader gates before launching any replay."""
    sha = digest_file(path)
    row, pairs, excluded = load_candidate_capture(path, evidence, sha)
    require(row['selected_case_ids'] == ids and len(row['cases']) == 80
            and row.get('case_list_sha256') == CASE_LIST_SHA,
            'Capture is not the exact frozen development80')
    require(row.get('model_configuration') == accepted['model_configuration']
            and row.get('schema_selection_policy') == accepted['schema_selection_policy']
            and row.get('sql_repair_policy') == accepted['sql_repair_policy']
            and row.get('workers') == 1, 'Capture model/coverage/repair/worker configuration differs')
    require(row['intent_candidate_policy'] == policy(), 'Capture candidate policy differs')
    require(len(pairs)+len(excluded) == 80, 'Capture denominator differs')
    return sha, pairs, excluded


def complete_native(path, capture_sha, pairs, excluded, evidence):
    row = read(path)
    ids = [c['case_id'] for c, _ in pairs]
    summary = row.get('summary') or {}
    require(row.get('run_status') == 'complete' and row.get('errors') == []
            and row.get('native_comparisons_complete') is True and row.get('pools_closed') is True
            and row.get('target_data_verified') is True
            and row.get('source_report_sha256') == capture_sha
            and row.get('code_binding') == code_binding() and row.get('source_binding') == source_binding(evidence)
            and row.get('formal_benchmark') is False and row.get('primary_ex') is None
            and row.get('holdout_live_allowed') is False and row.get('new_model_request_count') == 0,
            'Native report is incomplete or has conflicting provenance')
    require(row.get('selected_case_ids') == ids and [c['case_id'] for c in row.get('cases', [])] == ids
            and row.get('excluded_cases') == excluded and row.get('source_case_count') == 80,
            'Native replay omitted or duplicated cases')
    require(summary.get('source_case_count') == summary.get('development_subset_case_count') == 80
            and summary.get('replayed_case_count') == len(pairs)
            and summary.get('excluded_case_count') == len(excluded)
            and summary.get('new_model_request_count') == 0,
            'Native denominator or model budget differs')
    matches = sum(c['native_comparison']['matches_frozen_gold'] is True for c in row['cases'])
    require(summary.get('native_match_count') == matches
            and summary.get('native_mismatch_count') == len(pairs)-matches
            and summary.get('development_subset_native_match_rate') == matches/80,
            'Native summary does not match per-case results')
    return summary


def checkpoint(path, report, phase):
    report['phase'] = phase
    report['updated_at'] = now()
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


@contextmanager
def exclusive_run(results):
    """Nonblocking host lock, released automatically even after process death."""
    import fcntl
    with (results/'.m2_v4_development80.lock').open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            require(False, 'Another v4 development80 workflow is active')
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def child(args, module, options, report, stage):
    command = [sys.executable, '-u', '-m', module,
        '--data-root', str(args.data_root), '--results-dir', str(args.results_dir),
        '--credentials-file', str(args.credentials_file), *map(str, options)]
    checkpoint(args.output, report, stage)
    print('Starting '+stage, flush=True)
    result = subprocess.run(command, cwd=BASE, check=False)
    report.setdefault('child_exit_codes', {})[stage] = result.returncode
    require(result.returncode == 0, stage+' failed; preserve child report and inspect log')


def run(args, report):
    evidence, ids, accepted = preflight(args)
    report.update(preflight_passed=True, formal_benchmark=False, holdout_live_allowed=False,
        candidate_policy=policy(), candidate_code_sha256=accepted['code_binding']['sha256'],
        workflow_sha256=digest_file(Path(__file__)), case_list_sha256=CASE_LIST_SHA,
        selected_case_count=80, model_configuration=accepted['model_configuration'],
        diagnostic_report=str(args.diagnostic_output), native_report=str(args.native_output),
        replay_only=args.replay_only, check_only=args.check_only,
        new_model_request_count=None,
        usage_scope='Child reports own all model/SQL usage; this report records orchestration only.')
    if args.check_only:
        report.update(run_status='complete', phase='preflight_only',
                      new_model_request_count=0, live_readiness_verified=False)
        return
    with exclusive_run(args.results_dir):
        if not args.replay_only:
            child(args, 'evaluation.bird.diagnostic_runner', [
                '--case-list', CASE_LIST, '--model-config-file', args.model_config_file,
                '--index-root', args.index_root, '--schema-coverage', '--intent-candidate',
                '--save-snapshot', '--output', args.diagnostic_output], report, 'generation')
        checkpoint(args.output, report, 'checking_complete_capture')
        sha, pairs, excluded = complete_capture(args.diagnostic_output, evidence, ids, accepted)
        report.update(diagnostic_report_sha256=sha, answered_case_count=len(pairs),
                      nonanswer_case_count=len(excluded))
        child(args, 'scripts.rescore_m2_intent_candidate', [
            '--source-report', args.diagnostic_output, '--source-sha256', sha,
            '--output', args.native_output], report, 'native_replay')
        checkpoint(args.output, report, 'checking_complete_native')
        require(digest_file(args.diagnostic_output) == sha, 'Diagnostic report changed during replay')
        report['summary'] = complete_native(args.native_output, sha, pairs, excluded, evidence)
        report.update(native_report_sha256=digest_file(args.native_output),
                      phase='complete', run_status='complete')


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--data-root', type=Path, default=DEFAULT_DATA)
    result.add_argument('--results-dir', type=Path, default=DEFAULT_RESULTS)
    result.add_argument('--credentials-file', type=Path, default=DEFAULT_CREDENTIALS)
    result.add_argument('--model-config-file', type=Path, default=BASE/'.env')
    result.add_argument('--index-root', type=Path, default=BASE/'data/bird_indexes/m2_bird_pg_v1')
    result.add_argument('--diagnostic-output', type=Path,
        default=DEFAULT_RESULTS/'m2_public_intent_v4_development80_server.json')
    result.add_argument('--native-output', type=Path,
        default=DEFAULT_RESULTS/'m2_public_intent_v4_development80_native_server.json')
    result.add_argument('--output', type=Path, required=True, help='Separate workflow status JSON')
    modes = result.add_mutually_exclusive_group()
    modes.add_argument('--check-only', action='store_true', help='Static checks; no model or database calls')
    modes.add_argument('--replay-only', action='store_true', help='Replay existing complete80; no model config read')
    return result


def main():
    args = parser().parse_args()
    for name in ('data_root', 'results_dir', 'credentials_file', 'model_config_file',
                 'index_root', 'diagnostic_output', 'native_output', 'output'):
        setattr(args, name, getattr(args, name).resolve())
    protected = paths(args)
    with journal(args.output, 'M2 v4 development80 orchestration; not formal EX',
                 protected=protected+[args.diagnostic_output, args.native_output]) as report:
        run(args, report)
    raise SystemExit(0 if report['run_status'] == 'complete' else 1)


if __name__ == '__main__':
    main()
