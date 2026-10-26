# M2 来源拒绝反馈、两题原生语义核验与 14 题开发诊断

日期：2026-10-17。本轮在 Schema 覆盖候选上继续实施。

## 一、本地实现

### 来源拒绝反馈 v2

`repair.py` 策略升级为 `bird_authorized_sql_repair_v2`。遇到 `sql_source_denied`，反馈新增：

- `local_reason`：明确这是本地 SQL 策略拒绝，保留空的服务器原因和空 SQLSTATE，不伪造 PostgreSQL 错误或位置。
- `source_policy`：逻辑 database_id、物理 schema、允许的引用形式、被拒绝的实际 schema/catalog/table 及原因。
- 仅当表名确实存在于当前授权 catalog 时，提供该表的无前缀写法和 `public` 限定写法。未知表不提供替代目标，也不列出整个 catalog。
- 提醒逻辑 ID 是分组标签，并非物理 schema；要求保留筛选条件、关联和输出语义。反馈不自动改写 SQL。
- 最多列 4 个拒绝引用；该部分最多 2,048 UTF-8 字节，整个反馈仍最多 8,192 字节；继续脱敏并记录省略数量。
- 重复错误阻断及既定生成次数、校验次数、模型请求、超时和权限上限保持原约定。

已用实际 0095 首次 SQL 离线重建：`financial.client`、`financial.district`、`financial.disp` 均可得到 `physical_schema_denied`，允许的当前来源写法分别为 `client/public.client`、`district/public.district`、`disp/public.disp`。

### 独立原生语义核验

新增 `evaluation/bird/semantics.py` 与入口 `scripts/check_m2_development_semantics.py`。

输入固定绑定已审查的 `m2_schema_coverage_validation3_server.json`，SHA-256：

```text
9167b9005fcbd2f899dda744f4c6a3258c24777e4625281d05a6b33ca8d57123
```

仅选取冻结开发题 0050 和 0095，不选择 holdout。不调用模型，不构建索引，不变更数据，不传递审查结果给 Agent。

每题使用对应的只读角色，重新验证当前结构、权限、数据版本和内容守卫，然后执行 3 次审查 SELECT（另含运行时原有 EXPLAIN 和来源验证）：

1. 原样重放已下载报告中的最终预测 SQL。
2. 原样执行该题冻结 Gold SQL。
3. 执行解释查询：0050 显示第七名对应的 `satscores.sname`、`schools.school` 和邮寄地址；0095 显示最年轻客户、账号、客户地区工资、账号地区工资、全库最高工资及新增筛选条件能否保留该客户。

原生值先按原有 tuple-set 比较规则比较，再生成带类型的 JSON 预览。没有列别名放宽、类型转换、近似数值比较或 Gold 修改。报告记录完整结果摘要、最多 20 行有类型预览、真实匹配结果及查询预算。

这是独立审查预算：每题最多 3 次业务 SELECT、600 秒、单 SQL 仍最多 30 秒、完整结果仍最多 100,000 行/64 MiB，模型预算为 0。它不消耗也不扩大 Agent 原有生成预算。

`run_status=complete` 表示审查操作完成；`matches_frozen_gold=false` 表示该条预测结果不匹配。两者可以同时出现。报告没有正式 EX 分母，不应将两题匹配比例当作新的基准成绩。

如果中间查询失败，会保留已尝试的查询、Gold 尝试状态和预算，连接池仍执行关闭。

### 14 题诊断准备

继续使用原有 `m2_development_diagnostics14.json`，14 题、8 个开发域，题号与分组保持原字节。显式启用已有 Schema 覆盖策略，结合修复反馈 v2；输出使用新文件名。

诊断 runner 不执行 Gold，原始问题/evidence、授权索引、隔离和预算保持既定规则；不把前一步原生审查值或 Gold 放进新模型输入。

## 二、本地验证结果

- 完整 M2 回归：148 项，145 项通过；3 项 Linux 专属检查留给服务器执行。
- 新测试涵盖错误 schema、catalog 限定、未知表、CTE、带引号大小写、脱敏与字节上限、重复阻断，以及实际来源校验反馈进入第二轮模型请求。
- 原生核验测试包含名称值不等、空结果与非空 Gold 不匹配、列名不影响原生比较、错误来源拒绝、部分失败保留预算及异常关闭连接池。
- 两题共 6 条计划查询均通过当前只读 SQL 策略离线检查。
- 核验资料：`evaluation/results/m2_source_semantics_preparation_local_20261017.json`。
- 本地回归：`evaluation/results/m2_source_semantics_tests_local_20261017.json`。

本地测试使用模拟连接和原生类型测试值；**真实 PostgreSQL 名称值、两题原生匹配结果和新 14 题模型结果均待下面服务器命令生成**。

## 三、服务器命令

将 `M2_source_semantics_sync_20261017.zip` 上传到项目根目录。这是在上一轮 Schema 覆盖版本上的增量包。

### 1. 同步并测试

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M2_source_semantics_sync_20261017.zip
cd backend

python -m unittest discover -s tests -p 'test_m2_*.py' -v
```

### 2. 运行两题原生语义审查，无模型调用

```bash
python -u -m scripts.check_m2_development_semantics \
  --source-report evaluation/results/m2_schema_coverage_validation3_server.json \
  --output evaluation/results/m2_development_semantics2_server.json
```

使用已有私有 PostgreSQL 凭据文件，不需要读取模型 `.env`。先确认 `run_status=complete`、无连接/数据版本错误。两题匹配与否都会如实保留，不会阻止报告保存。

### 3. 运行一次 14 题开发诊断

```bash
python -u -m evaluation.bird.diagnostic_runner \
  --baseline-report evaluation/results/m2_c_bird_development80_server.json \
  --runtime-report evaluation/results/m2_c_bird_runtime_server.json \
  --gold-report evaluation/results/m2_c_bird_gold110_server.json \
  --case-list evaluation/cases/bird_mini_dev/m2_development_diagnostics14.json \
  --model-config-file .env \
  --schema-coverage \
  --save-snapshot \
  --output evaluation/results/m2_schema_coverage_diagnostics14_server.json
```

此步会调用模型。若上一轮三域索引仍完整，预计复用三域索引，其余五域无重试时新建索引约 31 个 embedding 批次；以实际 `cache_hit` 和模型事件记录为准。题目调用另计，原有每题上限保持。

输出文件须尚不存在；保留旧报告，重跑选新文件名。

## 四、下载与核对

下载以下两份报告至本地 `backend/evaluation/results/`：

1. `m2_development_semantics2_server.json`
2. `m2_schema_coverage_diagnostics14_server.json`

审查重点：

- 0050：sname 与 school 在被排序命中的真实行中是否相同，哪列为 NULL，预测与 Gold 的原生 tuple 是否一致。
- 0095：预测是否仍为空；额外“全库最大工资”条件与客户/账号地区关联路径对结果的影响；保留冻结 Gold。
- 14 题：来源反馈 v2 是否准确、补充字段是否进入初始图、首次 SQL、修复次数、重复阻断、澄清理由及预算。
- 没有基线入选表、低于覆盖下限或需要新表的缺口，继续如实记录，不能称作本轮覆盖策略已经解决。
- 本轮不同模型输出之间的变化是开发观察，不构成严格因果对照。正式 EX、完整开发集及 holdout 仍遵循独立的候选冻结与就绪流程。
