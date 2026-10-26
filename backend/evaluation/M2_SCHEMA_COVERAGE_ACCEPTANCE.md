# M2 授权 Schema 关键字段覆盖：实现与服务器验证

日期：2026-10-17。候选策略：`bird_authorized_schema_coverage_v1`。

## 本次改造

新增 `evaluation/bird/coverage.py`，在既有 BM25/dense → RRF → rerank 之后选择字段。

默认仍按得分至少 0.55、最多 20 个检索字段筛选。开发诊断显式使用 `--schema-coverage` 时，才启用以下候选策略：

1. 保留基线已选字段及其顺序，不挤占或替换基线字段。
2. 补充范围只限原有最多 40 个 RRF 候选，且其所属表必须已经有基线入选字段。
3. 补充字段的 rerank 分数必须在 `[0.50, 0.55)`；未返回分数、非有限分数或其他来源不能获得补充资格。
4. 使用原始 question/evidence 的英文词项，与真实字段名或官方字段标签匹配。进行大小写、分词和简单复数归一化，排除常见功能词、泛指 name/id；不用样本值或描述正文匹配。
5. 匹配词须在同表已选字段中尚未覆盖。每次补充后更新覆盖集合，避免重复补充具有同一意图词的字段。
6. 按原 rerank 得分顺序最多补 4 个字段，检索入选字段总计最多 20。原有物理 FK 关联键补充另按图构建规则执行；不得把它们误称为检索 20 字段上限内的项目。

该策略不包含题号、数据库名、字段名白名单或逐题 SQL 替换规则。它只补充候选字段，不自动改写 SQL，也不保证所有业务必要字段都已覆盖。

没有任何基线入选字段、需要引入另一张未入选表、缺少 rerank 分数、或字段分数低于 0.50 时，本策略不会补充。这些问题应作为独立召回缺口诊断。

## 版本、权限与记录

- 冻结协议文件 `m2_pg_v1` 和正式默认筛选规则保留。新策略是开发候选，不宣称遵循基线的单一 0.55 筛选规则。
- 只接受开发诊断显式启用；正式 `live`/`gold` worker 拒绝 `schema_coverage_enabled=true`。要推广到正式评测，须另行冻结候选及其检索配置、明确协议版本并生成对应 runtime/Gold 就绪材料。
- 候选字段首先经过原有当前 runtime/index 授权集合校验，再核对 database/table/field 身份。没有新增数据库账号、授权表或运行能力。
- `coverage.py` 纳入索引代码身份，代码变更会产生新的索引分区；运行 manifest 原有代码绑定也自动覆盖新模块。
- 报告根节点、逐题和检索结果标明 `schema_selection_policy`。诊断中保存基线字段、补充字段、锚定表、真实 rerank 分数、匹配词、未覆盖词及筛选原因。
- 最终图中补充字段的 `source=schema_coverage`；物理关联键仍使用 `relation_key`。
- SQL 修复反馈、生成次数、请求预算、超时、Linux 隔离和原生 EX 算法保持原约定。补充操作本身不发起新模型或数据库调用。

补充或拒绝原因包括 `selected_coverage`、`below_coverage_floor`、`coverage_table_not_anchored`、`coverage_no_intent_match`、`coverage_intent_already_covered`、`coverage_total_field_cap`、`coverage_addition_cap`，以及原有未返回分数/超出 top20 原因。

## 本地验证

- 新增边界测试覆盖分数下限、同表范围、词项来源、覆盖增益、最多 4 个补充、总数 20、稳定排序、错误来源和坏分数拒绝。
- 通过真实 `retrieve` → 图构建 → schema 文本 → 诊断记录路径验证补充字段进入模型可见 Schema，同时保持一次 embedding 和一次 rerank。
- 验证默认筛选结果与旧实现一致；验证开发开关传入 worker，正式 worker 不接受开发候选。
- 对历史 14 条诊断及最新 3 条修复诊断，共 17 条记录使用已记录分数回放；原有基线字段和顺序全部保留。
- 两份历史报告中，0050 均补入 `california_schools.satscores.sname`，1473 均补入 `debit_card_specializing.yearmonth.date`；最新 0095 没有额外补入字段，作为修复逻辑对照。
- 最终回放：`evaluation/results/m2_schema_coverage_replay_local_20261017_v2.json`。
- 最终本地 M2 回归：`evaluation/results/m2_schema_coverage_tests_local_20261017_v2.json`。

回放只重用旧分数和授权元数据，没有重新检索向量、调用模型、连接 PostgreSQL 或执行 Gold，因此不构成新模型效果或 EX 成绩。

## 服务器步骤

将 `M2_schema_coverage_sync_20261017.zip` 上传至服务器项目根目录。该包是在已验收 SQL 修复版本上的增量包。

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M2_schema_coverage_sync_20261017.zip
cd backend

python -m unittest discover -s tests -p 'test_m2_*.py' -v
```

通过后执行三题定向诊断：

```bash
python -u -m evaluation.bird.diagnostic_runner \
  --baseline-report evaluation/results/m2_c_bird_development80_server.json \
  --runtime-report evaluation/results/m2_c_bird_runtime_server.json \
  --gold-report evaluation/results/m2_c_bird_gold110_server.json \
  --case-list evaluation/cases/bird_mini_dev/m2_schema_coverage_validation3.json \
  --model-config-file .env \
  --schema-coverage \
  --save-snapshot \
  --output evaluation/results/m2_schema_coverage_validation3_server.json
```

需要模型密钥并产生调用费用。代码身份变更后，首次三域索引预计 18 个 embedding 批次（9+6+3，无重试时）；题目请求另计。旧索引及原始报告均保留。

若输出文件已存在，选择尚不存在的新文件名，不覆盖。下载 `m2_schema_coverage_validation3_server.json` 到本地 `backend/evaluation/results/` 核对。

## 核对重点

1. 根节点和逐题标明正确候选策略、开发诊断、`gold_executed=false`、`primary_ex=null`、holdout 未开放。
2. 三域来源、查询账号、版本、索引、实际隔离探针和运行上下文关闭记录正确。
3. 0050 的 sname、1473 的 date 若仍在原有候选且满足规则，应出现在初始图和 schema 文本，补充原因可重建；若新得分使其直接按基线入选，也属于覆盖到位，不要求必须标为补充。
4. 观察首次 SQL 是否使用真实字段、校验修复次数是否减少；0095 作为修复回归对照。不得只凭可执行断言答案正确。
5. 所有调用、校验、执行、重复阻断及预算记录完整；不得以扩大预算解释改进。

模型输出有波动，此次与旧报告比较属于开发诊断，不是同一版本、同一输入条件下的严格因果对照。三题通过后再评估是否扩展 14 条诊断；正式 EX 及完整开发集复验需在候选与协议配置冻结之后进行。
