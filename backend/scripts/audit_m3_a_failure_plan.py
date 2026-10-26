"""Build M3 A reviewer-only artifacts from saved M2 evidence, without imports of runners."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RESULTS = BASE / 'evaluation/results'
PROTOCOL = BASE / 'evaluation/cases/bird_mini_dev/m2_pg_v1'
DEFINITION = BASE / 'evaluation/m3_a_review_definition_20261021.json'
SOURCE_NAMES = [
    'm2_public_intent_v4_development80_server.json',
    'm2_public_intent_v4_development80_native_server.json',
    'm2_public_intent_v4_development80_triage_local_20261019.json',
    'm2_v4_holdout30_server.json',
    'm2_v4_holdout30_review_local_20261019.json',
]
ACCEPTED_SHA = {
    SOURCE_NAMES[0]: 'e19e9eb40db7bc72c9bbf88ecbb31eb126aa28432c183669f4ff08ff4d8c25ef',
    SOURCE_NAMES[1]: '1bbb278d0a5ffb99b3049faff6e1da2c482230284188e71e8d4fb44504c38774',
    SOURCE_NAMES[3]: '9c8afa202a10ac9bf7f396d37d7efa4a739fe6d7f3de5bc25414ec04a0a5b008',
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def keyed(rows):
    result = {r['case_id']: r for r in rows}
    require(len(result) == len(rows), 'Duplicate case IDs')
    return result


def cid(short):
    return 'BIRD-PG-' + short


def new_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')


def field_trace(case, field):
    full = case['database_id'] + '.' + field
    retrieval = case['development_diagnostics']['retrieval']
    candidate = next((r for r in retrieval['candidates'] if r['field_id'].casefold() == full.casefold()), None)
    fields = retrieval['schema_graph']['value']['fields']
    graph_field = next((f for f in fields if f['id'].casefold() == full.casefold()), None)
    return dict(field_id=full, in_recorded_candidates=candidate is not None,
                rerank_score=None if candidate is None else candidate.get('rerank_score'),
                selection_reason=None if candidate is None else candidate.get('selection_reason'),
                selected=any(v.casefold() == full.casefold() for v in retrieval['selected_field_ids']),
                in_final_graph=graph_field is not None,
                graph_field_type=None if graph_field is None else graph_field['type'],
                graph_field_source=None if graph_field is None else graph_field.get('source'),
                absent_candidate_meaning='Not in saved candidate list; does not prove absence from authorized catalog')


def case_evidence(case, native, public, gold, review, index, native_index):
    rid = case['case_id']
    graph = case['development_diagnostics']['retrieval']['schema_graph']
    require(graph['complete'] is True and graph['value'] is not None, 'Missing full schema graph: ' + rid)
    if native:
        require(case['generated_sql'] == native['queries']['captured_generated'], 'Saved SQL differs: ' + rid)
        require(native['queries']['frozen_gold'] == gold['gold_sql'], 'Recorded Gold differs: ' + rid)
        require(case['source_identity'] == native['source_identity'], 'Case source identity differs: ' + rid)
        require(native['captured_native_diagnostic_preserved'] is True, 'Prediction diagnostic differs: ' + rid)
    attempts = case['development_diagnostics']['attempts']
    return dict(case_id=rid, database_id=case['database_id'], status=case['status'],
        public_input=public, classification=review,
        causal_status='Observed differences confirmed from saved evidence; no new counterfactual execution',
        earliest_supported_stage=('retrieval_or_schema_context' if review['primary'] == 'retrieval_relation_coverage'
                                  else 'reference_contract_review' if review['primary'] == 'reference_or_public_ambiguity'
                                  else 'generation_or_repair'),
        source_identity=case['source_identity'], query_role=case['query_role'],
        source_pointers={'generation': SOURCE_NAMES[0] + '#/cases/' + str(index),
                         'native': None if native is None else SOURCE_NAMES[1] + '#/cases/' + str(native_index),
                         'gold': 'scorer/gold110.jsonl:case_id=' + rid},
        generated_sql=case.get('generated_sql'),
        reference_sql_reviewer_only=gold['gold_sql'],
        native_comparison=None if native is None else native['native_comparison'],
        results=None if native is None else native['results'],
        retrieval_field_trace=[field_trace(case, field) for field in review['fields']],
        selected_field_ids=case['development_diagnostics']['retrieval']['selected_field_ids'],
        final_graph_field_ids=[f['id'] for f in graph['value']['fields']],
        final_graph_joins=graph['value']['joins'],
        graph_sha256=graph['sha256'],
        decision_and_validation_attempts=attempts,
        clarification_reason=case['development_diagnostics']['clarification_reason'],
        validation_events=case['validation_events'], executions=case.get('executions', []),
        canonical_lookup=case.get('canonical_lookup'), budget=case['budget'])


def markdown(report):
    labels = report['category_labels']
    lines = ['# M3 A：逐题失败归因与首轮目标', '', '整理日期：2026-10-21（Asia/Shanghai）。', '',
        '**A阶段完成：已核对开发80题，归档30个失败、选择20个成功回归题，并确定首轮公开输出契约实验。尚未修改运行链路或启动模型实验。**', '',
        '## 1. 材料和审查边界', '',
        '- M2 v4开发基线50/80：27题原生不匹配，3题未回答；全部保留固定80题分母。',
        '- 开发50个成功题全部登记；其中20题组成首轮回归集，覆盖全部8个开发域。',
        '- 保留11个失败仅作已观察补充诊断，不进入本轮24题生成清单，不称为新的未见测试。',
        '- 本次0模型调用、未连接数据库、未重新执行SQL、未修改题库/Gold/评分器/冻结产物。',
        '- 每题主分类互斥，伴随标签可重叠。分类是排查组织方式，不表示单一根因已经由反事实实验证明。',
        '- SQL和公开输入的差异、字段是否进入图可直接核实；完整EX沿用已验收服务器原生比较。截断预览不作完整复评，也不用于证明全部差异的原因。',
        '- JSON含参考SQL和审查判断，仅供可信审查；Agent只接收既定五字段公开输入及授权元数据。', '',
        '历史v4开发核对文件中“尚未开启holdout”是当时状态；最终M2状态以[M2最终验收](M2_FINAL_ACCEPTANCE_20261019.md)为准。', '',
        '## 2. 开发集失败主分类', '', '| 主分类 | 题数 | 题号 |', '| --- | ---: | --- |']
    for category, count in report['failure_counts_by_primary'].items():
        ids = [r['case_id'][-4:] for r in report['development_failures'] if r['classification']['primary'] == category]
        lines.append(f"| {labels[category]} | {count} | {', '.join(ids)} |")
    lines += ['', '这30题中没有最终仍执行报错的回答题；1533曾除零后恢复，但答案仍错。3题未回答为0639重复终止、1524和0152澄清。', '',
        '## 3. 逐题审查', '']
    for row in report['development_failures']:
        review = row['classification']
        lines += [f"### {row['case_id']} · {row['database_id']}", '',
            f"- **主分类**：{labels[review['primary']]}；状态：`{row['status']}`。",
            f"- **问题**：{row['public_input']['question']}",
            f"- **公开evidence**：{row['public_input']['evidence']}",
            '- **已观察差异**：' + review['observed'], '- **归因依据**：' + review['attribution'],
            '- **仍待核实**：' + review['uncertainty'], '- **后续方向**：' + review['next'], '',
            '| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |', '| --- | ---: | --- | --- |']
        for field in row['retrieval_field_trace']:
            lines.append('| `{}` | {} | {} | {} |'.format(field['field_id'],
                '未在候选记录出现' if field['rerank_score'] is None else f"{field['rerank_score']:.6f}",
                field['selection_reason'] or '无候选筛选记录', '是' if field['in_final_graph'] else '否'))
        lines += ['', '保存的最终SQL：', '', '```sql', row['generated_sql'] or '-- 未生成最终可执行SQL；见JSON中的尝试与澄清记录。', '```', '',
            '参考SQL仅供可信审查：', '', '```sql', row['reference_sql_reviewer_only'], '```', '']
    lines += ['## 4. 成功回归集：从50题中选择20题', '',
        '以下均在v4原生通过；属于开发回归，不是新保留集。未选的30个成功题仍保留在JSON的完整成功清单，后续development80全部参与。', '',
        '| 题号 | 数据库域 | 主要保护点 |', '| --- | --- | --- |']
    for row in report['successful_cases']:
        if row['selected_for_first_regression']:
            lines.append(f"| {row['case_id']} | {row['database_id']} | {row['regression_reason']} |")
    lines += ['', '## 5. 已观察保留集补充（不进入首轮生成）', '', '| 题号 | 分类 | 审查结论 |', '| --- | --- | --- |']
    for row in report['observed_holdout_failures']:
        lines.append(f"| {row['case_id']} | {row['category']} | {row['note']} |")
    lines += ['', '## 6. 首轮选择与下一步', '',
        '**选择SQL生成语义分支：公开输出需求的有序覆盖。** 主目标0050、0085、0407；1479是混合观察题；加20个成功回归题，共24题。', '',
        '三道主目标的相关字段已进入最终Schema，公开请求可支持检查输出顺序、遗漏计算项或字段组；因此首轮无需同时改检索、关联或模型。1479还缺币种上下文，不能因去掉多余列碰巧通过就宣称业务修复。', '',
        '检索是下一优先候选：9题归入上下文覆盖主类，0604/1479/1480可定位到表未锚定过滤，0152有明确开户日期缺口；但关联缺声明、实体角色和参考歧义需分开处理。', '',
        '不在首轮追求全部30题通过，也不放宽EX、添加题号特例或重跑正式holdout30。范围、预算、通过与停止条件见[M3首轮实验计划](M3_A_FIRST_EXPERIMENT_PLAN_20261021.md)。', '',
        '## 7. 审计', '',
        f"- 独立核对冻结交付{report['verification']['frozen_delivery_file_count']}个文件，摘要均保持不变。",
        '- 原始报告和协议文件前后SHA-256一致；新运行时必须使用新候选身份，不能修改M2冻结摘要来绕过版本检查。',
        '- 逐题完整证据、50题成功登记、11题补充材料、代码/来源身份和检查项见[机器报告](results/m3_a_failure_attribution_local_20261021.json)。', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--markdown', type=Path, required=True)
    parser.add_argument('--pilot-case-list', type=Path, required=True)
    parser.add_argument('--regression-case-list', type=Path, required=True)
    args = parser.parse_args()
    outputs = [p.resolve() for p in (args.output, args.markdown, args.pilot_case_list, args.regression_case_list)]
    require(len(set(outputs)) == 4 and all(not p.exists() for p in outputs), 'Choose four new distinct output paths')
    forbidden = [PROTOCOL.resolve(), (BASE / 'evaluation/results/holdout_attempts').resolve()]
    require(all(not any(p == root or root in p.parents for root in forbidden) for p in outputs), 'Output overlaps frozen protocol or attempt ledger')
    delivery_path = BASE / 'evaluation/m2_v4_holdout30_delivery_20261019.json'
    delivery = read(delivery_path)
    frozen_bad = [name for name, value in delivery['expected_files'].items()
                  if not (BASE / name).is_file() or sha(BASE / name) != value]
    require(not frozen_bad, 'Frozen delivery differs: ' + str(frozen_bad))
    source_paths = [RESULTS / name for name in SOURCE_NAMES] + [
        PROTOCOL / 'inputs/development80.jsonl', PROTOCOL / 'scorer/gold110.jsonl',
        PROTOCOL / 'development80.json', PROTOCOL / 'holdout30.json', PROTOCOL / 'protocol.json',
        BASE / 'evaluation/M2_FINAL_ACCEPTANCE_20261019.md', BASE / 'evaluation/M2_REMAINING_ITEMS_20261019.md',
        BASE / 'evaluation/candidates/m2_v4_holdout30_candidate_20261019.json', delivery_path, DEFINITION]
    protected_hashes = {str(p.relative_to(BASE)).replace('\\', '/'): sha(p) for p in source_paths}
    require(not set(outputs).intersection(p.resolve() for p in source_paths), 'Output overlaps source evidence')
    for name, expected in ACCEPTED_SHA.items():
        require(sha(RESULTS / name) == expected, 'Accepted report SHA differs: ' + name)
    definition = read(DEFINITION)
    capture, replay, _, holdout, hold_review = [read(RESULTS / name) for name in SOURCE_NAMES]
    require(all(r['run_status'] == 'complete' and r.get('errors', []) == [] for r in (capture, replay, holdout)), 'Source report incomplete')
    require(replay['source_report_sha256'] == sha(RESULTS / SOURCE_NAMES[0]), 'Replay source SHA differs')
    require(capture['source_binding'] == replay['source_binding'] and capture['code_binding'] == replay['code_binding'], 'Development source/code chain differs')
    require(capture['gold_executed'] is False and replay['new_model_request_count'] == 0 and replay['native_comparisons_complete'] is True, 'Generation/scoring boundary differs')
    cases = keyed(capture['cases']); natives = keyed(replay['cases'])
    native_positions = {c['case_id']: i for i, c in enumerate(replay['cases'])}
    publics = keyed([json.loads(s) for s in (PROTOCOL / 'inputs/development80.jsonl').read_text(encoding='utf-8').splitlines()])
    golds = keyed([json.loads(s) for s in (PROTOCOL / 'scorer/gold110.jsonl').read_text(encoding='utf-8').splitlines()])
    require(list(cases) == read(PROTOCOL / 'development80.json')['case_ids'] and set(cases) == set(publics) and len(cases) == 80, 'Development set/order differs')
    successes = {rid for rid, row in natives.items() if row['native_comparison']['matches_frozen_gold'] is True}
    failures = set(cases) - successes
    mismatch = {rid for rid, row in natives.items() if row['native_comparison']['matches_frozen_gold'] is False}
    nonanswers = set(cases) - set(natives)
    require((len(successes), len(mismatch), len(nonanswers)) == (50, 27, 3), 'Frozen outcomes differ')
    require({r['case_id'] for r in replay['excluded_cases']} == nonanswers, 'Nonanswer list differs')
    reviews = {cid(row['id']): row for row in definition['failures']}
    require(len(reviews) == len(definition['failures']) == 30 and set(reviews) == failures, 'Failure attribution incomplete or duplicate')
    regression = {cid(row['id']): row['protects'] for row in definition['success_regression']}
    require(len(regression) == len(definition['success_regression']) == 20 and set(regression) <= successes, 'Regression list includes non-success or duplicate')
    require(len({cases[rid]['database_id'] for rid in regression}) == 8, 'Regression domains incomplete')
    experiment = definition['experiment']
    targets = [cid(short) for short in experiment['primary_target_ids']]
    mixed = [cid(short) for short in experiment['mixed_observation_ids']]
    require(all(reviews[rid]['primary'] == 'explicit_output_contract' for rid in targets) and len(targets) == 3, 'Primary output targets differ')
    for rid in targets:
        require(all(field_trace(cases[rid], field)['in_final_graph'] for field in reviews[rid]['fields']), 'Primary target field missing from graph: ' + rid)
    chosen = set(targets + mixed) | set(regression)
    pilot = [rid for rid in cases if rid in chosen]
    held = set(read(PROTOCOL / 'holdout30.json')['case_ids'])
    require(len(pilot) == 24 and len(chosen) == 24 and not set(pilot) & held, 'Pilot size or holdout isolation differs')
    supplements = {cid(row['id']): row for row in definition['holdout_observed_supplement']}
    require(set(supplements) == set(hold_review['failed_case_ids']) and len(supplements) == 11, 'Observed holdout failure list differs')
    held_cases = keyed(holdout['cases'])
    require(all(held_cases[rid]['ex_correct'] is False for rid in supplements), 'Holdout supplement includes success')
    report = dict(stage=definition['stage'], date=definition['date'], run_status='complete',
        scope='trusted_reviewer_only_not_agent_input', formal_benchmark=False, new_model_request_count=0,
        postgresql_connected=False, sql_executed=False, scoring_policy_changed=False,
        application_or_candidate_code_modified=False, holdout_regenerated=False,
        source_sha256=protected_hashes,
        baseline=dict(development_cases=80, native_match_count=50, native_mismatch_count=27,
                      nonanswer_count=3, native_rate=0.625, holdout_match_count=19, holdout_cases=30),
        category_labels=definition['category_labels'],
        failure_counts_by_primary=dict(Counter(reviews[rid]['primary'] for rid in cases if rid in failures)),
        development_failures=[case_evidence(c, natives.get(rid), publics[rid], golds[rid], reviews[rid], i,
                              native_positions.get(rid)) for i, (rid, c) in enumerate(cases.items()) if rid in failures],
        successful_cases=[dict(case_id=rid, database_id=c['database_id'],
            native_match=True, selected_for_first_regression=rid in regression,
            regression_reason=regression.get(rid), public_input=publics[rid],
            generated_sql=c['generated_sql'], source_identity=c['source_identity'], budget=c['budget'])
            for rid, c in cases.items() if rid in successes],
        observed_holdout_failures=[dict(case_id=rid, database_id=held_cases[rid]['database_id'],
            category=row['category'], note=row['note'], observed=True, included_in_pilot=False,
            source='m2_v4_holdout30_review_local_20261019.json:case_id=' + rid) for rid, row in supplements.items()],
        experiment=experiment,
        verification=dict(frozen_delivery_file_count=len(delivery['expected_files']), frozen_files_changed=[],
            failure_coverage_complete=True, all_successes_registered=True, regression_all_baseline_success=True,
            primary_target_fields_in_final_graph=True, regression_domain_count=8, pilot_case_count=24,
            primary_target_count=3, mixed_observation_count=1, regression_count=20, pilot_contains_holdout=False,
            source_reports_unchanged=True),
        limitations=['Saved evidence review, no new causal counterfactual queries.',
                    'Native outcomes follow accepted full server comparisons; bounded previews are not complete replay.',
                    'Reference/public ambiguities remain failures under original EX; not automatically model errors.',
                    'Observed holdout feedback is disclosed; no unseen-generalization claim.'])
    require(all(sha(BASE / name) == expected for name, expected in protected_hashes.items()), 'Source changed during audit')
    common = dict(protocol_id='m2_bird_pg_v1', development_only=True, holdout_allowed=False,
                  purpose='M3 A predeclared development selection; IDs only, no reference answers',
                  date='2026-10-21')
    new_json(args.pilot_case_list, dict(common, case_ids=pilot))
    new_json(args.regression_case_list, dict(common, case_ids=[rid for rid in cases if rid in regression]))
    new_json(args.output, report)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    with args.markdown.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(markdown(report))
    print(json.dumps(dict(run_status='complete', failures=len(failures), successes=len(successes),
        primary_categories=report['failure_counts_by_primary'], regression_count=20, pilot_count=24,
        observed_holdout_supplement_count=11, frozen_files_checked=len(delivery['expected_files']),
        new_model_request_count=0, postgresql_connected=False), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
