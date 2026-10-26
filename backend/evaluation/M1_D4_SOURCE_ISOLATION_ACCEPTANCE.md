# M1 D4：评测、缓存与报告来源隔离

## 1. 实施范围与状态

D1 已解决统一选择实际 Gold SQL、PostgreSQL manifest 使用经过实时验证的数据及 catalog 版本这两项基础接口。D4 在此基础上补齐缓存策略身份、索引身份、snapshot 身份、续跑拒绝和独立跨后端结果比较。

本轮状态：代码已实施；本地专项、完整回归和 DuckDB 79 题 Gold 的具体结果见第 3 节。2026-10-11 已下载并逐题核对服务器两份 Gold 和跨后端比较报告，独立复算全部通过；报告验收记录见 [D4服务器审查](M1_D4_SERVER_REPORTS_REVIEW.md)。本轮未提供服务器代码回归日志或 snapshot 原文件，其核对范围详见审查记录。D3 原始报告、冻结审查材料及原题集备份继续保留。首批仍为 classic 49 + 扩展 30；其余 351 题 PostgreSQL Gold 变体尚未制作，缺失时继续明确拒绝。

## 2. 已实现的约定

| 部分 | D4 约定 |
|---|---|
| Gold | 解析、执行、缓存与报告使用同一份 `select_gold_sql` 选择结果；PostgreSQL 缺少显式变体不回退 |
| manifest | 格式 v4；使用实际 runtime 的数据/catalog 版本，记录 PostgreSQL 实时来源校验及物理结构版本 |
| 结果策略 | v1；显式记录逐题列别名、辅助列、顺序、排序键、已批准的 Top-N 并列规则、数值比较与规范化版本、完整评分行上限 |
| Gold 缓存 | 格式 v3；身份包含完整来源、实际 SQL 选择、题目、权限、数据版本和结果策略；旧格式或身份不同重新执行 |
| Schema 索引 | 存储格式 v2；保存完整来源、文档策略版本、Embedding 模型及配置维度；身份不同重新构建 |
| snapshot | 自动继承并校验 manifest，拒绝冲突的来源、模式、题号或元数据；按 `snapshots/<source_id>/` 保存 |
| 续跑 | 校验已有题号唯一性、来源标签及 manifest 指纹；拒绝跨来源、跨版本或策略变化的 `--resume` |
| 同源回归 | 默认严格检查来源、数据/catalog/物理结构、题集、实际 Gold 选择、结果策略和评分器身份 |
| 跨后端比较 | 新增 `evaluation.compare_backends`；以 M1 B 已验收数据等价证据关联两种数据版本，生成独立报告 |

Gold 模式报告增加 `cases[].result_metrics.gold_result_evidence`，包含实际结果列、完整规范化结果行、来源、SQL、权限、结果策略和规范化内容 SHA256。仅存在 summary 或旧版缓存不能作为独立逐值比较证据。该证据只用于评测报告，不传给 live Agent。

跨后端比较先核对同一冻结题集、权限、应用/评分器代码版本、结果策略及 M1 B 目标身份，再逐题执行三项比较：PostgreSQL 对 DuckDB、DuckDB 对冻结预期、PostgreSQL 对冻结预期。复评分还必须与原报告严格评分一致。错误的实际结果不能由两份报告中的 `correct=True` 掩盖。

沿用现有业务数值容差、逐题显式别名、排序规则和已批准并列规则；未增加通配别名或放宽评分。`raw_rows_identical_count` 单独记录列名及行值相等的题数，采用 Python 值相等判断，等值整数/浮点数会视为相同，不能解释为 JSON 类型或字节完全相同；服务器审查另记录规范化 JSON 相同题数及类型差异。该指标不能替代严格比较；日期、NULL、舍入和 Top-N 并列差异会在实际结果行中复核。比较器不连接数据库、不请求模型。

`input_report_content_sha256` 为规范化 JSON 内容摘要；M1 B import/validation 摘要则为原文件字节 SHA256。缓存和证据摘要用于一致性检查，不是数字签名。

旧报告和旧缓存文件无需删除。新格式不会命中旧缓存；已有索引在下一次 live 构建时需要重新生成 Embedding。历史 D3 v3 报告继续作为原始验收材料，D4 使用独立新报告，不续跑覆盖历史结果。

## 3. 本地证据

- `tests/test_m1_d4_isolation.py`：28 项来源隔离检查，包含实际本地 DuckDB 索引和文件读写；PostgreSQL 使用明确测试替身。
- `results/m1_d4_regression_local.json`：469 项完整代码回归通过，失败/错误/跳过均为 0。
- `results/m1_d4_duckdb_gold79_local.json`：实际 DuckDB 79/79 SQL 执行和严格结果通过，含真实返回行和 v4 manifest。
- `results/m1_d4_local_acceptance.json`：79/79 实际结果证据和冻结预期独立复核通过，快照/同源回归/续跑身份一致；历史材料摘要保持不变，旧 D3 报告明确拒绝用于 D4 比较。

所有本地检查未访问远程 PostgreSQL、未调用模型 API。最终测试数和 Gold 结果以以上 JSON 为准。

## 4. 同步与代码回归

将项目根目录的 `M1_D4_评测来源隔离同步包_20261010.zip` 上传到服务器项目根目录，确认上传路径后执行：

```bash
cd ~/Python_work/askdata_studio_ops_release
ls -lh M1_D4_评测来源隔离同步包_20261010.zip
unzip -o M1_D4_评测来源隔离同步包_20261010.zip
cd backend

python -m unittest discover -s tests -p 'test_m1_d4_isolation.py' -v
python -m unittest discover -s tests -q
```

专项预期 28 项、完整回归预期 469 项通过。没有新增依赖；继续使用现有已固定版本。同步包包含实施文件、测试、79 题清单、正式题集及测试所需的公开冻结验收证据，不包含 `.env`、密码、CSV 数据、Schema 索引或 Gold 缓存。

## 5. 分别新跑两份 Gold 79 报告

在 backend 中执行。使用同一代码、题集和配置，建议在服务器同一天依次完成。命令级环境变量选择后端，不修改默认 `.env`。PostgreSQL 服务需运行，现有 PG 配置及验收证据路径需有效。

```bash
DATA_BACKEND=duckdb \
DATA_SOURCE_ID=short_video_ops_duckdb \
TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_benchmark \
  --mode gold --scope all --workers 1 \
  --case-list evaluation/cases/m1_d3_postgres_gold79.json \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_d4_duckdb_gold79_server.json
```

```bash
DATA_BACKEND=postgresql \
DATA_SOURCE_ID=short_video_ops_postgres \
TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_benchmark \
  --mode gold --scope all --workers 1 \
  --case-list evaluation/cases/m1_d3_postgres_gold79.json \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_d4_postgres_gold79_server.json
```

每份报告应有 complete、79/79 SQL 成功及严格结果通过、未评分 0、模型请求 0、实际来源正确、Gold 来源 execution、比较目标 expected_rows，以及每题完整 Gold 结果证据。PostgreSQL manifest 需包含匹配的实时校验和数据/物理结构/catalog 版本。

不要省略 `--case-list`；未覆盖的 351 题会导致 PostgreSQL 在运行前拒绝。若重跑，另用 `_v2.json` 文件名保留首次报告。Gold 命令现有行为会覆盖指定输出，因此先确认新文件名尚未使用。

## 6. 生成独立跨后端比较报告

两份 Gold 完成后执行：

```bash
python -u -m evaluation.compare_backends \
  --duckdb-report evaluation/results/m1_d4_duckdb_gold79_server.json \
  --postgres-report evaluation/results/m1_d4_postgres_gold79_server.json \
  --case-list evaluation/cases/m1_d3_postgres_gold79.json \
  --import-evidence evaluation/results/m1_b_postgres_import_server.json \
  --validation-evidence evaluation/results/m1_b_postgres_validation_server.json \
  --output evaluation/results/m1_d4_cross_backend_gold79_server.json
```

比较器拒绝覆盖已有输出。输入身份错误时直接拒绝；结果不同会保存 failed 报告并以退出码 1 结束，保留实际差异供分析。

验收要求：`comparison_status=passed`、`case_count=79`，`pair_pass_count`、两个 `*_expected_pass_count` 及 `reported_scores_match_replay_count` 全为 79；模型请求和比较器数据库连接数均为 0。该结果明确标记 `is_same_source_regression=false`。原始行相同数量单独检查，不以修改预期或放宽规则消除差异。

下载以下三份 JSON 到本地 `backend/evaluation/results/`，再核对完整来源、行数据及差异：

1. `m1_d4_duckdb_gold79_server.json`
2. `m1_d4_postgres_gold79_server.json`
3. `m1_d4_cross_backend_gold79_server.json`

D4 服务器验收通过后，再安排其余 PostgreSQL Gold 变体和后续 PostgreSQL live/E2E 验收；本次不表示整个 M1 已完成。
