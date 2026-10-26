"""Trusted holdout scorer around the byte-frozen v4 generation worker.

The observer retains the final full native result without modifying it. Agent
generation finishes and its runtime closes before any Gold SQL is executed.
Gold uses the original case Budget and the same outer 600-second deadline.
"""
from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from scripts.m2_b_common import BASE, require
from scripts.m2_holdout_control import candidate
from evaluation.bird import case_worker
from evaluation.bird.budgets import BirdFailure, hard_deadline
from evaluation.bird.evidence import public_cases, scorer_gold
from evaluation.bird.native import NativeResult
from evaluation.bird.replay import native_difference
from evaluation.bird.semantics import native_record
from evaluation.bird.runtime import fault
from evaluation.bird.supervisor import Channel, MAX_FRAME


def checked_request(request):
    frozen = candidate()
    require(request.get('candidate_sha256') == frozen['candidate_sha256'], 'Worker candidate differs')
    public = request['input']
    allowed = {c['case_id']: c for c in public_cases('holdout30')}
    require(public == allowed.get(public.get('case_id')), 'Only exact frozen holdout inputs are admitted')
    gold = scorer_gold()[public['case_id']]
    require(gold == request['gold'] and gold['database_id'] == public['database_id'], 'Scorer Gold identity differs')
    require(request['code_sha256'] == frozen['payload']['producer_binding']['sha256'], 'Producer identity differs')
    return frozen, gold


def execute(request):
    frozen, gold = checked_request(request)
    # Construct a new whitelist request: no Gold, difficulty, score, previous
    # cases or holdout-side hints are passed to the unchanged generation worker.
    generation = {key: request[key] for key in ('input', 'receipt', 'data_root', 'results_dir',
        'credentials_file', 'index_path', 'code_sha256', 'model_config_private')}
    generation.update(mode='diagnostic', schema_coverage_enabled=True, intent_candidate_enabled=True)
    state = {}
    original = case_worker.BirdRuntime

    class ObservedRuntime(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            state['runtime'] = self

        def execute_native(self, sql, budget=None, *, validate_only=False):
            result = super().execute_native(sql, budget, validate_only=validate_only)
            if not validate_only:
                state.update(last_sql=sql, prediction=result, budget=budget)
            return result

    report = None
    scorer = None
    try:
        case_worker.BirdRuntime = ObservedRuntime
        try:
            report = case_worker.execute(generation)
        finally:
            case_worker.BirdRuntime = original
        report.update(mode='live', generation_worker_mode='diagnostic', ex_correct=False,
            gold_sql_sha256=gold['gold_sql_sha256'], gold_execution_attempted=False, gold_executed=False,
            generation_status=report['status'], scoring_scope='trusted_after_agent_exit_with_original_case_deadline',
            formal_benchmark=True, candidate_sha256=frozen['candidate_sha256'])
        if report['status'] != 'diagnostic_answered':
            report['scoring_not_attempted'] = 'No complete final answer; contributes zero to fixed denominator'
            return report
        predicted = state.get('prediction')
        budget = state.get('budget')
        runtime = state.get('runtime')
        require(report.get('runtime_closed') is True and predicted is not None
            and predicted.complete is True and isinstance(predicted, NativeResult)
            and state.get('last_sql') == report['generated_sql']
            and predicted.diagnostic() == report['result'], 'Complete predicted native object is missing')
        require(runtime.connections.closed and budget is not None, 'Generation runtime did not close')
        budget.remaining()
        # Same role, receipt, source guards and original budget; no second model
        # generation, prediction re-execution, or extra 600-second scoring window.
        from scripts.m2_b_target import load_credentials
        credentials = load_credentials(Path(request['credentials_file']), runtime.evidence.manifest,
                                       runtime.evidence.validation['initialization_id'])
        role = runtime.domain['query_role']
        with hard_deadline(budget.remaining(), 'case_wall_timeout'):
            scorer = original(runtime.evidence, gold['database_id'], credentials['passwords'][role],
                              receipt=request['receipt'])
            require(scorer.identity.public() == report['source_identity'], 'Scorer source differs')
            report['gold_execution_attempted'] = True
            expected = scorer.execute_native(gold['gold_sql'], budget)
            require(expected.complete is True, 'Gold result is incomplete')
            report['gold_executed'] = True
            comparison = native_difference(predicted, expected)
            report.update(status='scored', complete=True, ex_correct=comparison['matches_frozen_gold'],
                native_comparison=comparison,
                native_results={'prediction': native_record(predicted), 'reference': native_record(expected)},
                result_diagnostics={'ordered_rows_match': predicted.rows == expected.rows,
                    'row_multiset_match': Counter(predicted.rows) == Counter(expected.rows),
                    'column_count_match': len(predicted.columns) == len(expected.columns)})
            budget.remaining()
    except BaseException as error:
        failure = BirdFailure('interrupted') if isinstance(error, KeyboardInterrupt) else fault(error)
        report = report or dict(case_id=request['input']['case_id'], database_id=request['input']['database_id'],
            mode='live', errors=[], new_model_request_count=None, gold_sql_sha256=gold['gold_sql_sha256'])
        report.update(status=failure.category, complete=False, ex_correct=False)
        report['errors'].append(failure.public())
    finally:
        case_worker.BirdRuntime = original
        if report is not None:
            if scorer is not None:
                try:
                    scorer.close()
                    require(scorer.connections.closed, 'Scorer pool did not close')
                    report['scorer_runtime_closed'] = True
                except BaseException as error:
                    report.update(status='scorer_close_failed', complete=False, ex_correct=False,
                                  scorer_runtime_closed=False)
                    report['errors'].append(fault(error).public())
            else:
                report['scorer_runtime_closed'] = None
            if 'budget' in state:
                report['budget'] = state['budget'].public()
                report['new_model_request_count'] = state['budget'].total_attempts
            try:
                require(candidate()['candidate_sha256'] == frozen['candidate_sha256'], 'Frozen candidate changed during case')
            except BaseException:
                report.update(status='candidate_changed_during_case', complete=False, ex_correct=False)
                report['errors'].append({'category': 'candidate_changed_during_case'})
    return report


def run_process(request, *, seconds=600):
    """Use the existing bounded pipe/session supervisor design for this scorer."""
    if sys.platform != 'linux':
        raise BirdFailure('linux_supervisor_required')
    require(0 < seconds <= 600, 'Invalid holdout case deadline')
    deadline = time.monotonic()+seconds
    completed = False
    environment = {'LANG': 'C.UTF-8', 'TZ': 'UTC'}
    if os.getenv('LD_LIBRARY_PATH'):
        environment['LD_LIBRARY_PATH'] = os.environ['LD_LIBRARY_PATH']
    process = subprocess.Popen([sys.executable, '-m', 'scripts.m2_holdout_worker'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        cwd=BASE, env=environment, start_new_session=True, close_fds=True, bufsize=0)
    try:
        channel = Channel(process)
        channel.send(request, deadline)
        result = channel.receive(deadline)
        try:
            process.wait(timeout=max(.001, min(5, deadline-time.monotonic())))
        except subprocess.TimeoutExpired:
            raise BirdFailure('case_wall_timeout') from None
        if process.returncode != 0:
            raise BirdFailure('case_worker_failed')
        completed = True
        return result
    finally:
        if not completed:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait(timeout=5)
        for stream in (process.stdin, process.stdout):
            if stream:
                stream.close()


def main():
    try:
        raw = sys.stdin.buffer.readline(MAX_FRAME+1)
        if not raw or len(raw) > MAX_FRAME or not raw.endswith(b'\n'):
            raise BirdFailure('invalid_worker_frame')
        request = json.loads(raw)
        with hard_deadline(600, 'case_wall_timeout'):
            result = execute(request)
    except BaseException as error:
        result = dict(status=fault(error).category, complete=False, ex_correct=False,
                      errors=[fault(error).public()], new_model_request_count=None)
    sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(',', ':'))+'\n')
    sys.stdout.flush()


if __name__ == '__main__':
    main()
