"""Frozen candidate validation and durable, one-attempt holdout registration.

No model/database calls occur in this module. Ledger entries are never reset.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import uuid

from scripts.m2_b_common import BASE, PROTOCOL_DIR, digest_file, digest_json, now, require
from evaluation.bird.manifest import code_binding, source_binding
from evaluation.bird.intent import policy
from evaluation.bird.evidence import Evidence, DEFAULT_RESULTS
from evaluation.bird.intent_replay import load_candidate_capture
from scripts.run_m2_v4_development80 import complete_capture, complete_native

CANDIDATE_PATH = BASE/'evaluation/candidates/m2_v4_holdout30_candidate_20261019.json'
LEDGER_ROOT = DEFAULT_RESULTS/'holdout_attempts/m2_bird_pg_v1'
DEVELOPMENT = 'm2_public_intent_v4_development80_server.json'
DEVELOPMENT_NATIVE = 'm2_public_intent_v4_development80_native_server.json'
DEVELOPMENT_SHA = 'e19e9eb40db7bc72c9bbf88ecbb31eb126aa28432c183669f4ff08ff4d8c25ef'
DEVELOPMENT_NATIVE_SHA = '1bbb278d0a5ffb99b3049faff6e1da2c482230284188e71e8d4fb44504c38774'
CONTROL_FILES = ('scripts/m2_holdout_control.py', 'scripts/m2_holdout_worker.py',
    'scripts/run_m2_holdout30.py', 'scripts/run_m2_v4_development80.py',
    'scripts/rescore_m2_intent_candidate.py')
SCORING = dict(policy='frozen_native_tuple_set_v1', primary_denominator=30,
    nonanswers='contribute_zero_without_removal', preview_scoring=False,
    worker_mode='unchanged_v4_diagnostic', scorer='trusted_after_agent_exit',
    native_prediction='same_complete_native_object_retained_by_passive_observer',
    case_deadline_seconds=600, separate_scoring_time_budget=False,
    gold_sql_calls_per_answer=1, gold_readiness='fresh_all30_before_index_or_agent',
    gold_visibility='no_gold_or_score_in_agent_context_or_repair_feedback')


def read(path):
    return json.loads(path.read_bytes())


def build_candidate():
    """Local freeze uses already reviewed server evidence; never loads a secret."""
    require(not LEDGER_ROOT.exists() or not any(LEDGER_ROOT.iterdir()),
            'Holdout attempts already exist; a later freeze must explicitly disclose reuse')
    capture = read(DEFAULT_RESULTS/DEVELOPMENT)
    native = read(DEFAULT_RESULTS/DEVELOPMENT_NATIVE)
    require(digest_file(DEFAULT_RESULTS/DEVELOPMENT) == DEVELOPMENT_SHA
        and digest_file(DEFAULT_RESULTS/DEVELOPMENT_NATIVE) == DEVELOPMENT_NATIVE_SHA,
        'Accepted development evidence changed')
    require(capture['code_binding']['files'] == code_binding()['files'], 'Candidate execution bytes changed')
    require(capture['code_binding'] == native['code_binding']
        and native['source_report_sha256'] == DEVELOPMENT_SHA
        and capture['run_status'] == native['run_status'] == 'complete'
        and capture['errors'] == native['errors'] == []
        and native['summary']['development_subset_case_count'] == 80
        and native['summary']['native_match_count'] == 50, 'Development acceptance differs')
    protocol = read(PROTOCOL_DIR/'protocol.json')
    payload = dict(schema='m2_v4_holdout_candidate_v1', frozen_at='2026-10-19',
        producer_binding=capture['code_binding'], source_binding=capture['source_binding'],
        model_configuration=capture['model_configuration'], intent_candidate_policy=policy(),
        schema_selection_policy=capture['schema_selection_policy'], sql_repair_policy=capture['sql_repair_policy'],
        protocol_files={'protocol.json': digest_file(PROTOCOL_DIR/'protocol.json'), **protocol['artifact_sha256']},
        budgets=protocol['budgets'], scoring=dict(SCORING),
        controller_files={name: digest_file(BASE/name) for name in CONTROL_FILES},
        development_evidence={DEVELOPMENT: DEVELOPMENT_SHA, DEVELOPMENT_NATIVE: DEVELOPMENT_NATIVE_SHA},
        holdout_split='holdout30', holdout_case_count=30,
        attempt_policy='one_registered_attempt_per_candidate; failures/interruption consume attempt; no automatic retry',
        scope='Project frozen evidence-provided Mini-Dev subset; not official leaderboard score',
        known_development_failures=30, holdout_results_observed_before_freeze=False)
    sha = digest_json(payload)
    return dict(candidate_id='m2_v4_'+sha, candidate_sha256=sha, payload=payload)


def candidate(path=CANDIDATE_PATH):
    row = read(path)
    payload = row['payload']
    require(row['candidate_sha256'] == digest_json(payload)
        and row['candidate_id'] == 'm2_v4_'+row['candidate_sha256'], 'Frozen candidate digest differs')
    require(payload.get('schema') == 'm2_v4_holdout_candidate_v1'
        and payload.get('holdout_split') == 'holdout30' and payload.get('holdout_case_count') == 30
        and payload.get('scoring') == SCORING and payload.get('intent_candidate_policy') == policy()
        and payload.get('development_evidence') == {DEVELOPMENT: DEVELOPMENT_SHA, DEVELOPMENT_NATIVE: DEVELOPMENT_NATIVE_SHA},
        'Frozen candidate contract differs')
    require(payload['producer_binding'] == code_binding(), 'Frozen producer/dependency/host identity differs')
    require(set(payload['controller_files']) == set(CONTROL_FILES), 'Controller inventory differs')
    for name, sha in payload['controller_files'].items():
        require(digest_file(BASE/name) == sha, 'Frozen controller differs: '+name)
    for name, sha in payload['protocol_files'].items():
        target = (PROTOCOL_DIR/name).resolve()
        require(target.is_relative_to(PROTOCOL_DIR.resolve()) and digest_file(target) == sha,
                'Frozen protocol artifact differs: '+name)
    protocol = read(PROTOCOL_DIR/'protocol.json')
    require(payload['budgets'] == protocol['budgets']
        and payload['protocol_files'] == {'protocol.json': digest_file(PROTOCOL_DIR/'protocol.json'), **protocol['artifact_sha256']},
        'Frozen protocol/budget inventory differs')
    return row


def evidence_preflight(row, data_root, results_dir, config):
    payload = row['payload']
    evidence = Evidence.load(data_root, results_dir)
    require(payload['source_binding'] == source_binding(evidence), 'Frozen source differs')
    require(payload['model_configuration'] == config.public(), 'Frozen public model configuration differs')
    for name, sha in payload['development_evidence'].items():
        require(digest_file(results_dir/name) == sha, 'Development source evidence differs: '+name)
    ids = read(PROTOCOL_DIR/'development80.json')['case_ids']
    accepted = read(results_dir/DEVELOPMENT)
    sha, pairs, excluded = complete_capture(results_dir/DEVELOPMENT, evidence, ids, accepted)
    complete_native(results_dir/DEVELOPMENT_NATIVE, sha, pairs, excluded, evidence)
    require(accepted['schema_selection_policy'] == payload['schema_selection_policy']
        and accepted['sql_repair_policy'] == payload['sql_repair_policy'], 'Frozen runtime switches differ')
    # A historical all110 readiness proof remains provenance, never current live readiness.
    from evaluation.bird.diagnostic_runner import prerequisites
    prerequisites(results_dir/'m2_c_bird_development80_server.json',
        results_dir/'m2_c_bird_runtime_server.json', results_dir/'m2_c_bird_gold110_server.json', evidence)
    return evidence


def durable_new(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(row, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)


def sync_directory(path):
    if os.name == 'posix':
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


class Attempt:
    def __init__(self, root, row):
        self.path = root/row['candidate_id']
        # mkdir is the atomic reservation. An empty directory after a crash still blocks retry.
        try:
            self.path.mkdir(parents=False, exist_ok=False)
        except FileExistsError:
            require(False, 'This candidate already has a registered attempt; preserve it and do not rerun')
        sync_directory(root)
        self.id = uuid.uuid4().hex
        self.sequence = 0
        self.previous = None
        self.event('reserved', candidate_id=row['candidate_id'], candidate_sha256=row['candidate_sha256'],
                   process_id=os.getpid(), hostname=__import__('platform').node())

    def event(self, kind, **fields):
        self.sequence += 1
        row = dict(attempt_id=self.id, sequence=self.sequence, previous_event_sha256=self.previous,
                   kind=kind, recorded_at=now(), **fields)
        path = self.path/f'{self.sequence:04}_{kind}.json'
        durable_new(path, row)
        self.previous = digest_file(path)
        return row

    def case(self, result):
        name = result['case_id']
        require(name.startswith('BIRD-PG-') and name[8:].isdigit(), 'Invalid case artifact name')
        path = self.path/'cases'/(name+'.json')
        durable_new(path, result)
        self.event('case_saved', case_id=name, status=result['status'], case_sha256=digest_file(path))

    def gold(self, result):
        name = result['case_id']
        require(name.startswith('BIRD-PG-') and name[8:].isdigit(), 'Invalid Gold artifact name')
        path = self.path/'gold_readiness'/(name+'.json')
        durable_new(path, result)
        self.event('gold_ready', case_id=name, artifact_sha256=digest_file(path))


def reserve(row, root=None):
    root = LEDGER_ROOT if root is None else root  # root override is used by isolated unit tests only.
    root.mkdir(parents=True, exist_ok=True)
    for path in (root, root.parent, root.parent.parent):
        sync_directory(path)
    return Attempt(root, row)


def verify_ledger(path):
    files = sorted(path.glob('[0-9][0-9][0-9][0-9]_*.json'))
    require(files, 'Attempt reservation has no durable event; treat as interrupted, not unused')
    previous = None
    attempt_id = None
    for sequence, file in enumerate(files, 1):
        event = read(file)
        require(event['sequence'] == sequence and event['previous_event_sha256'] == previous,
                'Attempt event chain differs')
        if attempt_id is None:
            attempt_id = event['attempt_id']
            require(event['kind'] == 'reserved', 'First attempt event must reserve the run')
        require(event['attempt_id'] == attempt_id, 'Attempt identity differs')
        if event['kind'] == 'case_saved':
            require(digest_file(path/'cases'/(event['case_id']+'.json')) == event['case_sha256'],
                    'Attempt case artifact changed')
        if event['kind'] == 'gold_ready':
            require(digest_file(path/'gold_readiness'/(event['case_id']+'.json')) == event['artifact_sha256'],
                    'Attempt Gold readiness artifact changed')
        previous = digest_file(file)
    return dict(attempt_id=attempt_id, event_count=len(files), last_event=read(files[-1])['kind'],
                last_event_sha256=previous)
