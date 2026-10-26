# M1 E PostgreSQL 首轮问题修正与复验

本文件记录首轮复验的原定步骤。三份 v2 诊断报告已下载并核对；最新结论、`GROWTH_OPS-051` 的新原因及别名应用状态见 [`M1_E_POSTGRES_DIAGNOSTIC_V2_REVIEW.md`](M1_E_POSTGRES_DIAGNOSTIC_V2_REVIEW.md)。后续服务器操作应按新结论执行。

2026-10-12。本次修正保留首轮三份服务端 JSON 不变。首轮审查记录见 `M1_E_POSTGRES_FIRST_RUN_REVIEW.md`，对应的逐题数据为 `results/m1_e_postgres_server_review_local.json`。首轮 classic 为执行 48/49、结果 47/49、严格 38/49；扩展集为执行 27/30、结果 25/30、严格 20/29；服务入口行为 8/8。

## 本地已完成

1. PostgreSQL 提示词指出两参数 `ROUND` 的**整个第一参数**必须转换成 `numeric`。SQL 校验器对能从真实字段类型确认的浮点参数提前 BLOCK；仅当 BLOCK 原因全部为这类错误时，智能体将整个第一参数转换成 `numeric` 并再次执行完整校验，同时在工具轨迹中保存修正前后 SQL。首轮 3 条 42883 SQL 的转换均通过本地校验。服务器仍须确认实际 SQL 可执行且结果正确。
2. `single_database_agent` 会在用尽三次候选机会后记录每次被拒的 SQL、指标校验和约束校验原因；`run_benchmark` 将其写入报告。首轮 `GROWTH_OPS-051` 没有候选 SQL，不能从旧报告判断模型错误还是误拦截。
3. 指标和约束校验增加激活计数人群、次日留存事实表、注册平台人均播放以及经澄清确认的渠道注册人数规则；月份字段根据确认的口径或已验证 SQL 定位。首轮错误 SQL 被拦截、相应 Gold SQL 通过、本轮 E2E 澄清 SQL 的指标与日期校验 PASS，已在本地回归测试验证。
4. 14 题、23 项候选列别名已逐题在本地数据上复算：原严格评分均失败、加候选别名后均通过，宽松值相同；这只是 **DuckDB 诊断**，记录于 `results/m1_e_postgres_alias_diagnostic_local.json`，不冒充 PostgreSQL 验收。正式题集当前仍未加入这些别名。
5. 旧正式题集已按字节冻结到 `results/m1_e_all_cases_before_aliases_20261012.jsonl`，SHA-256 为 `e1cb760a8ffa4f89e45ca73403c439975c51d2be47cd36800ee4c7c0ee1925f1`。历史 D3 Gold430 审计读取这份冻结题集；后续别名调整不会改写旧审计依据。

本地 `unittest discover -s tests -q` 已通过 489 项。服务器 PostgreSQL 复验尚未执行。

## 服务器执行顺序

先同步本次代码、两份诊断题目清单、逐题审查 JSON 和冻结题集。保持原有 `.env`、首轮三份报告和 PostgreSQL 数据不变。在 `backend` 目录运行；这些命令都使用新报告名。

### 1. 单独验证三个旧 SQL 执行失败题

```bash
DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_benchmark --mode live --scope all --workers 1 \
  --no-use-cached-gold --save-snapshot \
  --case-list evaluation/cases/m1_e_postgres_round3_diagnostic.json \
  --output evaluation/results/m1_e_round3_diagnostic_server_v2.json
```

预期是三个候选 SQL 均正常执行并得到正确结果；若仍失败，以新报告保存的 SQL/错误为准继续修正，不应因预校验挡住原 SQL 就宣布执行问题已解决。

### 2. 单独核实 GROWTH_OPS-051

```bash
DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_benchmark --mode live --scope all --workers 1 \
  --no-use-cached-gold --save-snapshot \
  --case-list evaluation/cases/m1_e_growth051_diagnostic.json \
  --output evaluation/results/m1_e_growth051_diagnostic_server_v2.json
```

若仍被拒，请检查该题 `errors.diagnostics.rejected_decisions` 的候选 SQL 和逐次校验原因；若通过，检查生成 SQL、实际结果和严格评分。旧报告的缺失证据无法反推。

### 3. 独立 PostgreSQL 别名复评分

```bash
DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m scripts.rescore_m1_e_postgres_aliases \
  --output evaluation/results/m1_e_postgres_alias_rescore_server_v2.json
```

脚本用首轮保存的 14 条生成 SQL 在经验证的 PostgreSQL 目标上重新执行，重新执行每题 PostgreSQL Gold，逐题比较原严格评分、加入显式别名后的严格评分及宽松结果。它核对首轮报告、原题集、运行来源、数据版本与摘要；不调用模型，不写正式题集。只有 14/14 新严格评分通过、23 项别名逐题匹配时才生成 `complete` 报告。请先下载并审查此报告。

### 4. 复评分审查通过后，加入正式题集

```bash
python -u -m scripts.apply_m1_e_postgres_aliases \
  --replay evaluation/results/m1_e_postgres_alias_rescore_server_v2.json \
  --output evaluation/results/m1_e_postgres_alias_apply_server_v2.json
```

该命令再次核对 14 题的 PostgreSQL 结果行、Gold 行、来源及文件摘要，仅给对应题添加 23 项显式 `column_aliases`。原题集冻结文件和首轮报告均保留。若复评分未通过，不运行此步；修正具体映射后重新审查。

### 5. 依次重跑三组正式验收

```bash
DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_benchmark --mode live --scope classic --workers 1 \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_e_postgres_live_classic_server_v2.json

DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_benchmark --mode live --scope all --workers 1 \
  --no-use-cached-gold --save-snapshot \
  --case-list evaluation/cases/phase83_validation.json \
  --output evaluation/results/m1_e_postgres_live_phase83_server_v2.json

DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_e2e \
  --case-list evaluation/cases/e2e_behavior_postgres.json \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_e_postgres_e2e_behavior_server_v2.json
```

下载这三份 v2 报告，以及前述三份诊断/别名报告后，核对来源身份、79 题实际 SQL 执行与结果、严格评分覆盖、051 候选证据、澄清日期 WARN 和 8 条服务行为。新旧模型运行不应直接解释为模型必然改进；以独立报告保留每次运行身份与 SQL 证据。
