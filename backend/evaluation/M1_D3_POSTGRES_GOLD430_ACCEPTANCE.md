# M1 D3：补齐剩余 351 题 PostgreSQL Gold

**2026-10-12验收更新：**服务器两份完整430题Gold已下载核对，均430/430执行及严格结果通过；本地读取860份实际结果证据，独立跨后端及两份冻结预期复评分均430/430。全量Gold报告验收完成，见 [服务器审查记录](M1_D3_POSTGRES_GOLD430_SERVER_REVIEW.md)。独立比较报告已在本地生成：`results/m1_d3_cross_backend_gold430_local.json`。下一步按第6节执行正式PostgreSQL live及服务E2E。

## 1. 本轮交付与边界

2026-10-12 已为剩余 351 题保存显式 `gold_sql_by_dialect.postgres`。正式题集共 430 题全部覆盖：增长 145、渠道 140、内容 145；新增分别为 118、114、119。

430 题原 DuckDB SQL、预期列/行、显式别名、顺序及已批准并列规则保持不变。首批 79 题行字节和原逐题审查记录保持不变；新增 SQL 经过受控只读校验、完整 276 字段类型解析、业务角色检查及逐题结构/语义核对。未增加运行时转译或缺失变体回退。

新增只允许延用首批已验收的五类差异：月份格式、整数非零真假条件、显式浮点除法、二参数 ROUND 的 numeric 输入、原有 NULL 排序。新增 78 处整数真假判断、136 处分子浮点转换、235 处 numeric 舍入；不修改过滤窗口、连接关系、聚合粒度、分子/分母、窗口函数、输出列或 LIMIT。

离线审查与本地 DuckDB 兼容性诊断不能证明真实 PostgreSQL 执行通过。服务器全量 Gold 与独立跨后端比较验收通过后，才进入正式 PostgreSQL live/E2E。

## 2. 文件和本地验收材料

| 材料 | 用途 |
|---|---|
| `cases/all_cases.jsonl` | 全量 430 题显式 PostgreSQL SQL |
| `cases/m1_d3_postgres_gold430.json` | 430 题固定顺序清单 |
| `cases/m1_d3_postgres_gold351.json` | 与首批 79 题互补的新增 351 题清单 |
| `cases/m1_d3_postgres_gold351_review.json` | 逐题 SQL 摘要、过滤/连接/分组/排序、输出及修改记录 |
| `M1_D3_POSTGRES_GOLD351_REVIEW.md` | 可阅读的逐题审查和新增 SQL |
| `results/m1_all_cases_before_postgres_gold430_20261012.jsonl` | 本轮修改前的完整题集字节，SHA256 为 `16fe651be76e5eacde7eb30ac6b1880eb4fcb0d22eebb7b347142f26e488a34f` |
| `results/m1_d3_gold430_audit_local.json` | 430 题离线审查；351 新增、79 原行字节保留、430 原评分不变 |
| `results/m1_d3_gold430_duckdb_compatibility_local.json` | 原 SQL/诊断渲染 SQL/两者结果逐题对照，实际后端均为 DuckDB |
| `results/m1_d3_gold430_regression_local.json` | 本地完整代码回归 |

本地新增 14 项专项全部通过，覆盖全量选择、缺失变体拒绝、月份/真假条件/LIMIT/NULL 排序篡改拒绝、原评分不可修改、CTE gap/窗口分母保留及 PostgreSQL E2E 显式 Gold。483 项完整回归全部通过，错误/失败/跳过均为 0。430 题原 SQL、诊断渲染 SQL 及两者严格结果对照均 430/430 通过；实际诊断后端为 DuckDB，模型请求 0、未连接远程 PostgreSQL。

旧的 `audit_m1_d3_gold79` 在新冻结快照存在时审查该快照，报告明确标记 `Frozen first79 preparation snapshot`；原 79 题测试和兼容性诊断继续复现历史材料。当前正式题集必须使用新的全量审查脚本。

另准备了 `cases/e2e_behavior_postgres.json`：与原八条行为用例相同，仅为空结果样例保存显式 PostgreSQL Gold；原 `e2e_behavior.json` 完全保留。它是后续 E2E 验收输入，目前尚无真实 PostgreSQL E2E 结果。

## 3. 服务器同步和代码回归

上传 `M1_D3_Gold430同步包_20261012.zip` 到服务器项目根目录，确认文件存在后执行：

```bash
conda activate py311
cd ~/Python_work/askdata_studio_ops_release
ls -lh M1_D3_Gold430同步包_20261012.zip
unzip -o M1_D3_Gold430同步包_20261012.zip
cd backend

python -m unittest discover -s tests -p 'test_m1_d3_gold430.py' -v
python -m unittest discover -s tests -q

python -u -m scripts.audit_m1_d3_gold430 \
  --output evaluation/results/m1_d3_gold430_audit_server.json
```

专项预期 14 项、完整回归预期 483 项通过；审查预期 430 题通过、新增 351、首批 79 字节保留、原 SQL/评分 430 不变。无新增依赖；不会修改服务器 `.env`。`prepare_m1_d3_gold430` 只用于本地一次性准备，服务器直接使用包中的正式题集，不重复运行准备脚本。

以下输出均使用新名字，重跑时另用 `_v2` 并同步修改比较命令中的输入路径。保留全部 D3/D4 历史报告，不对旧报告续跑。

## 4. 新跑全量 430 题 Gold

先完成代码回归；随后在 backend 目录、同一代码和冻结题集下，依次运行两种后端。Gold 不请求模型。PostgreSQL runtime 会再次核对实际来源、权限及数据版本。

```bash
DATA_BACKEND=duckdb \
DATA_SOURCE_ID=short_video_ops_duckdb \
TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_benchmark \
  --mode gold --scope all --workers 1 \
  --case-list evaluation/cases/m1_d3_postgres_gold430.json \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_d3_duckdb_gold430_server.json
```

```bash
DATA_BACKEND=postgresql \
DATA_SOURCE_ID=short_video_ops_postgres \
TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_benchmark \
  --mode gold --scope all --workers 1 \
  --case-list evaluation/cases/m1_d3_postgres_gold430.json \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_d3_postgres_gold430_server.json
```

每份报告预期：430/430 执行、宽松/严格评分通过，未评分/错误/模型请求为 0，Gold 来源 execution，每题含完整结果证据。不能仅以 complete 判定通过。

## 5. 独立比较两份 430 题实际结果

```bash
python -u -m evaluation.compare_backends \
  --duckdb-report evaluation/results/m1_d3_duckdb_gold430_server.json \
  --postgres-report evaluation/results/m1_d3_postgres_gold430_server.json \
  --case-list evaluation/cases/m1_d3_postgres_gold430.json \
  --import-evidence evaluation/results/m1_b_postgres_import_server.json \
  --validation-evidence evaluation/results/m1_b_postgres_validation_server.json \
  --output evaluation/results/m1_d3_cross_backend_gold430_server.json
```

预期比较 passed，跨后端及两份冻结预期复评分均 430/430，原报告评分与复算一致。`raw_rows_identical_count` 使用 Python 值相等，等值整数/浮点表示会视为相同；逐值比较和 JSON 表示差异需分别核对，沿用 D4 报告口径说明。

下载以下四份到本地 `backend/evaluation/results/`，并发送两段测试汇总：

1. `m1_d3_gold430_audit_server.json`
2. `m1_d3_duckdb_gold430_server.json`
3. `m1_d3_postgres_gold430_server.json`
4. `m1_d3_cross_backend_gold430_server.json`

若全量失败，保留报告，逐题分析类型、数值、日期、NULL 或排序原因，不修改冻结预期、不增加通配别名、不放宽评分。修正后另存重跑报告。

## 6. 全量 Gold 验收后的 PostgreSQL live/E2E 安排

这部分需要模型调用。服务器483项回归及离线审查汇总已核对、两份完整Gold与本地独立比较已验收，可以按顺序执行。第一轮仍采用首批 79 题分成 classic49 和扩展30，时间字段补充关闭，避免将后端切换与补充开关混入同一次对照。

```bash
DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres \
TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_benchmark \
  --mode live --scope classic --workers 1 \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_e_postgres_live_classic_server.json
```

```bash
DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres \
TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_benchmark \
  --mode live --scope all --workers 1 \
  --case-list evaluation/cases/phase83_validation.json \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_e_postgres_live_phase83_server.json
```

```bash
DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres \
TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_e2e \
  --case-list evaluation/cases/e2e_behavior_postgres.json \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_e_postgres_e2e_behavior_server.json
```

live 逐题核对真实 SQL 方言、来源、执行及严格结果；E2E 核对 8 种服务行为，尤其澄清选项到 SQL、日期范围、空结果回复、权限拒绝和校验 WARN。未评分的非结果行为按行为标准验收。发现别名差异须独立语义审查；不自动根据模型输出扩充别名。

这三份是正式 PostgreSQL 首轮问数/服务基线。之后仍需依据结果决定是否补齐 430 题全量 live；Gold 430 通过不能替代模型生成 SQL 的全量评测。
