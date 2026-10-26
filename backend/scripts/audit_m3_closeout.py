"""Read local M3 evidence and source ASTs; no model, database or app imports.

This is a closeout inventory, not a CI gate or an experiment runner.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
WORKSPACE = PROJECT.parent
EXPERIMENTS = [
    ('E01-24', 'm3_e01_pair24_20261021_v2', 'pair24_comparison_server.json',
     'output_contract', 'screened_out', 'One of three primary targets improved; p95 exceeded its frozen limit.'),
    ('E02-24', 'm3_e02_pair24_20261022_v5', 'e02_pair24_comparison_server.json',
     'condition_relation_coverage', 'passed_local_screen_superseded_by_80', '1479 currency and authorized relation use confirmed; not product acceptance.'),
    ('E02-80', 'm3_e02_pair80_process_dns_v1_20261024_r1', 'e02_pair80_comparison_server.json',
     'condition_relation_coverage', 'not_adopted', '1479 improves; 0092 regresses; no full-development net gain.'),
    ('E03-24', 'm3_e03_pair24_process_dns_v1_20261023_r2', 'e03_pair24_comparison_server.json',
     'incomplete_relation_output', 'not_adopted', '0407 target context and output not repaired; transport observation retained separately.'),
    ('E04-24', 'm3_e04_pair24_scalar_count_20261024_r2', 'e04_pair24_comparison_server.json',
     'scalar_count_shape', 'not_adopted', '0092 already succeeds on both sides; no measured added gain.'),
    ('E05-24', 'm3_e05_pair24_endpoint_scope_20261024_r1', 'e05_pair24_comparison_server.json',
     'explicit_endpoint_prompt', 'not_adopted', '0239 still widens to both endpoints; prompt did not cause a repair.'),
    ('E06-24', 'm3_e06_pair24_endpoint_feedback_v2_20261024_r1', 'e06_pair24_comparison_server.json',
     'explicit_endpoint_feedback', 'passed_local_screen_superseded_by_80', '0239 repair trace confirmed; legitimate 0206 union preserved.'),
    ('E06-80', 'm3_e06_pair80_endpoint_feedback_v2_20261024_r1', 'e06_pair80_comparison_server.json',
     'explicit_endpoint_feedback', 'not_adopted', 'Net gain zero, historical success regression and unknown baseline usage.'),
    ('E07-r5-24', 'm3_categorical_population_pair24_20261025_r5', 'e07_pair24_comparison_server.json',
     'categorical_population', 'not_adopted_reused_baseline', '1480 native match lacks monthly aggregation; 0050 regresses; baseline was reused.'),
    ('E07-r8-24', 'm3_categorical_population_pair24_20261025_r8', 'e07_pair24_comparison_server.json',
     'categorical_and_semantic_prompt', 'not_adopted_confounded_treatment', 'Category context and semantic prompt both changed; 1480 semantic grain fails; 0459 regresses.'),
    ('E07-r9-24', 'm3_categorical_population_pair24_20261025_r9', 'e07_pair24_comparison_server.json',
     'semantic_prompt_v1', 'not_adopted', '0050 improves; 1480 still ranks a row; chat-token cap exceeded.'),
    ('E07-r10-24', 'm3_categorical_population_pair24_20261025_r10', 'e07_pair24_comparison_server.json',
     'semantic_prompt_v2_compact', 'not_adopted', '1480 monthly SUM confirmed and 0050 improves; chat-token cap exceeded; stop this limited experiment.'),
]


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence(path):
    return dict(path=str(path.relative_to(WORKSPACE)).replace('\\', '/'), sha256=sha(path), bytes=path.stat().st_size)


def find_reference(root, reference):
    name = reference['path'].replace('\\', '/').split('/')[-1]
    found = [p for p in root.rglob(name) if p.is_file() and sha(p) == reference['sha256']]
    if not found:
        raise ValueError('Missing or changed referenced report: ' + str(root / name))
    return found[0]


def usage(capture):
    groups = [row['budget']['model_events'] for row in capture['cases']]
    groups.extend((row.get('model_usage') or {}).get('model_events', []) for row in capture.get('index_builds', []))
    events = [event for group in groups for event in group]
    chats = [event for event in events if event.get('kind') == 'chat']
    def tokens(rows):
        known = [e.get('usage', {}).get('total_tokens') if isinstance(e.get('usage'), dict) else None for e in rows]
        missing = sum(type(v) is not int for v in known)
        lower = sum(v for v in known if type(v) is int)
        return dict(total=None if missing else lower, known_lower_bound=lower, missing_usage_events=missing)
    return dict(chat=tokens(chats), all=tokens(events), chat_calls=len(chats),
                event_statuses=dict(Counter(e.get('status', 'unrecorded') for e in events)),
                recorded_model_http_attempts=capture.get('new_model_request_count'))


def import_names(tree):
    result = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            result.append('.' * node.level + (node.module or ''))
    return result


def source_audit():
    sources = ['app/main.py', 'app/api/routes.py', 'app/config.py', 'app/model_client.py',
               'app/services/askdata_service.py', 'app/workflows/query_graph.py',
               'app/querying/single_database_agent.py', 'app/retrieval/graph.py',
               'evaluation/run_bird_benchmark.py', 'evaluation/bird/runner.py',
               'evaluation/bird/diagnostic_runner.py', 'evaluation/bird/case_worker.py',
               'evaluation/bird/retrieval.py', 'evaluation/bird/model.py',
               'evaluation/bird/process_dns.py', 'evaluation/bird/intent.py',
               'evaluation/bird/isolated_agent.py', 'evaluation/bird/demand_relations.py',
               'evaluation/bird/endpoint_scope.py', 'evaluation/bird/endpoint_validation.py',
               'evaluation/bird/scalar_count_shape.py', 'scripts/run_m2_holdout30.py',
               'scripts/m2_holdout_control.py', 'scripts/m2_holdout_worker.py']
    trees = {p: ast.parse((BACKEND / p).read_text(encoding='utf-8-sig')) for p in sources}
    imported = {str(p.relative_to(BACKEND)).replace('\\', '/'): import_names(ast.parse(p.read_text(encoding='utf-8-sig')))
                for p in (BACKEND / 'app').rglob('*.py')}
    leaks = {p: names for p, names in imported.items() if any(n.startswith('evaluation.bird') or 'm3_' in n for n in names)}
    flags = {}
    for n in ast.walk(trees['evaluation/bird/diagnostic_runner.py']):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'add_argument' and n.args):
            continue
        if not isinstance(n.args[0], ast.Constant):
            continue
        kwargs = {k.arg: ast.literal_eval(k.value) for k in n.keywords if isinstance(k.value, ast.Constant)}
        if kwargs.get('action') == 'store_true':
            flags[n.args[0].value] = dict(default=False, source_line=n.lineno)
    keys = {}
    for n in ast.walk(trees['evaluation/bird/case_worker.py']):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == 'request' and n.func.attr == 'get' and len(n.args) == 2 and all(isinstance(x, ast.Constant) for x in n.args):
            name, default = [x.value for x in n.args]
            if name.endswith('_enabled'):
                keys[name] = dict(default=default, source_line=n.lineno)
    live_keys = set()
    for n in ast.walk(trees['evaluation/bird/runner.py']):
        if isinstance(n, ast.Dict):
            live_keys.update(k.value for k in n.keys if isinstance(k, ast.Constant) and isinstance(k.value, str) and k.value.endswith('_enabled'))
    dormant = ['scalar_count_shape', 'endpoint_scope', 'endpoint_validation']
    worker_imports = import_names(trees['evaluation/bird/case_worker.py'])
    def dictionary_constants(tree, name):
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == 'dict':
                    return {k.arg: ast.literal_eval(k.value) for k in node.value.keywords if isinstance(k.value, ast.Constant)}
        raise ValueError('Missing source policy: ' + name)
    dns = dictionary_constants(trees['evaluation/bird/process_dns.py'], 'DNS_POLICY')
    transport = dictionary_constants(trees['evaluation/bird/model.py'], 'TRANSPORT_POLICY')
    env_defaults = {n.args[0].value: n.args[1].value for n in ast.walk(trees['app/config.py'])
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'getenv'
                    and len(n.args) == 2 and all(isinstance(v, ast.Constant) for v in n.args)}
    holdout_keys = sorted({kw.arg for n in ast.walk(trees['scripts/m2_holdout_worker.py'])
                          if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                          and isinstance(n.func.value, ast.Name) and n.func.value.id == 'generation'
                          and n.func.attr == 'update' for kw in n.keywords if kw.arg.endswith('_enabled')})
    result = dict(audit_kind='static_source_only', local_environment_or_secrets_read=False,
        production_app_files_scanned=len(imported), production_app_imports_of_m3_or_bird=leaks,
        diagnostic_store_true_flags=flags, worker_feature_defaults=keys,
        normal_bird_runner_treatment_keys=sorted(live_keys),
        dormant_in_current_case_worker={n: not any(name.endswith('.'+n) for name in worker_imports) for n in dormant},
        bird_transport=dict(active=True, policy_id=transport['policy_id'],
            resolver=dns['resolver'], executable=dns['executable'], expected_version=dns['expected_version'],
            product_app_uses_it=False, system_dns_modified=dns['system_dns_modified'],
            paired_lock='m3_context.json and transport_dependency_lock.json',
            nonpaired_behavior='tool_binding required; no paired execution lock when m3_context.json absent'),
        product_declared_defaults=dict(data_backend=env_defaults['DATA_BACKEND'], data_source_id=env_defaults['DATA_SOURCE_ID']),
        frozen_m2_holdout_explicit_features=holdout_keys,
        remote_deployment_state_verified=False,
        source_files={p: dict(sha256=sha(BACKEND/p)) for p in sources})
    assert not leaks and not live_keys
    assert keys and all(v['default'] is False for v in keys.values())
    assert all(result['dormant_in_current_case_worker'].values())
    assert holdout_keys == ['intent_candidate_enabled', 'schema_coverage_enabled']
    return result


def audit():
    rows = []
    manifests = {}
    for f in (BACKEND / '.downloads').glob('*/bundle_manifest.json'):
        try:
            record = read(f)
        except (ValueError, OSError):
            continue
        if 'bundle_id' in record:
            manifests[record['bundle_id']] = f
    for rid, directory, filename, family, decision, reason in EXPERIMENTS:
        root = WORKSPACE / directory
        comparison_path = root / 'reports' / filename
        comparison = read(comparison_path)
        assert comparison['run_status'] == 'complete'
        refs = {name: find_reference(root, value) for name, value in comparison['source_reports'].items()}
        raw = {name: read(path) for name, path in refs.items()}
        outcomes = {}
        for side in ('baseline', 'candidate'):
            capture, native = raw[side+'_capture'], raw[side+'_native']
            ids = capture['selected_case_ids']
            assert len(ids) == len(set(ids)) == comparison['case_count']
            assert [v['case_id'] for v in capture['cases']] == ids
            assert native['source_report_sha256'] == sha(refs[side+'_capture'])
            assert native['run_status'] == capture['run_status'] == 'complete'
            assert native['native_comparisons_complete'] is True and native['new_model_request_count'] == 0
            outcomes[side] = {v['case_id']: v['native_comparison']['matches_frozen_gold'] for v in native['cases']}
            assert sum(outcomes[side].values()) == comparison[side+'_match_count']
            for v in native['cases']:
                saved = next(x for x in capture['cases'] if x['case_id'] == v['case_id'])
                assert hashlib.sha256(saved['generated_sql'].encode()).hexdigest() == v['generated_sql_sha256']
        assert raw['baseline_capture']['selected_case_ids'] == raw['candidate_capture']['selected_case_ids']
        ids = raw['baseline_capture']['selected_case_ids']
        improved = [i for i in ids if not outcomes['baseline'].get(i, False) and outcomes['candidate'].get(i, False)]
        regressed = [i for i in ids if outcomes['baseline'].get(i, False) and not outcomes['candidate'].get(i, False)]
        assert set(improved) == set(comparison['wrong_to_right'])
        assert set(regressed) == set(comparison['right_to_wrong'])
        manifest_path = manifests.get(comparison['bundle_id'])
        if manifest_path:
            manifest = read(manifest_path)
            for side in ('baseline', 'candidate'):
                files = manifest['payload']['sides'][side].get('code_files')
                if files:
                    assert raw[side+'_capture']['code_binding']['files'] == files
        rows.append(dict(experiment_id=rid, family=family, directory=directory,
            bundle_id=comparison['bundle_id'], case_count=comparison['case_count'],
            baseline_match_count=comparison['baseline_match_count'], candidate_match_count=comparison['candidate_match_count'],
            net_gain=comparison['net_gain'], improved_case_ids=improved, regressed_case_ids=regressed,
            same_round_field=comparison.get('strict_same_round'), baseline_reused_field=comparison.get('baseline_capture_reused'),
            schema_context_changed_case_ids=comparison.get('schema_context_changed_case_ids'),
            automatic_screen_pass=comparison.get('automatic_screen_pass'), screening=comparison.get('screening'),
            frozen_acceptance_field=comparison.get('acceptance'), closeout_disposition=decision,
            closeout_reason=reason, promoted_to_product=False,
            regression20_retained_count=comparison.get('regression20_retained_count', comparison.get('regression_retained_count')),
            cost={s: usage(raw[s+'_capture']) for s in ('baseline', 'candidate')},
            case_wall_p95_seconds=comparison.get('case_wall_p95_seconds'),
            comparison=evidence(comparison_path), sources={k: evidence(v) for k,v in refs.items()},
            bundle_manifest=evidence(manifest_path) if manifest_path else None,
            checks=dict(report_hash_chain=True, native_counts_recomputed=True,
                        changes_recomputed=True, saved_sql_hashes=True)))
    attempts = []
    compared = {v['directory'] for v in rows}
    for root in sorted(WORKSPACE.glob('m3*')):
        if not root.is_dir() or root.name in compared:
            continue
        for f in sorted((root/'reports').glob('*server.json')):
            try:
                record = read(f)
            except (ValueError, OSError):
                continue
            if record.get('run_status') == 'failed' and record.get('phase'):
                attempts.append(dict(directory=root.name, evidence=evidence(f), phase=record['phase'],
                    status='failed_non_scored_attempt', counted_as_benchmark=False,
                    new_model_request_count=record.get('new_model_request_count'),
                    error_types=[e.get('type') for e in record.get('errors', [])]))
    return dict(stage='M3 local evidence ledger and active-source audit', review_date='2026-10-26',
        run_status='complete', scope='M3 closeout only; M4 not started',
        new_model_request_count=0, postgresql_connected=False,
        experiments=rows, experiment_comparison_count=len(rows),
        full80_comparison_count=sum(v['case_count']==80 for v in rows),
        promoted_effect_candidates=[], failed_non_scored_attempts=attempts,
        runtime_source_audit=source_audit(),
        decision='Limited M3 research closed; broad-effect promotion acceptance not met.',
        score_scope='M2 development50/80 and formal observed holdout19/30 remain historical frozen results; do not aggregate repeated M3 subsets.',
        limitations=['Local source and downloaded reports only; no remote deployment or live runtime inspected.',
                     'Native matches are not universal semantic equivalence.',
                     'Old failed attempts listed only when downloaded records are available; not an exhaustive remote attempt inventory.',
                     'Unknown model usage remains null with a known lower bound.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise SystemExit('Preserve the previous audit; choose a new output path')
    report=audit()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as f:
        json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({k:report[k] for k in ('run_status','experiment_comparison_count','full80_comparison_count','promoted_effect_candidates','new_model_request_count','postgresql_connected')},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
