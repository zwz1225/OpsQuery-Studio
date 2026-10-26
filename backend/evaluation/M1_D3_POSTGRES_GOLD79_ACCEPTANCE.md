# M1 D3：79题 PostgreSQL Gold 变体验收

日期：2026-10-10。状态：首轮服务器79题PostgreSQL Gold执行及报告一致性核对通过。详见 [服务器核对记录](M1_D3_POSTGRES_GOLD79_SERVER_REVIEW.md)。

## 1. 交付与边界

- 正式 `cases/all_cases.jsonl` 为 classic 49 + 扩展30逐题保存 `gold_sql_by_dialect.postgres`。原430题 DuckDB SQL、预期结果与评分标注不变；351题缺失变体继续明确拒绝。
- [逐题审查](M1_D3_POSTGRES_GOLD79_REVIEW.md)及 `cases/m1_d3_postgres_gold79_review.json` 包含每题业务口径、SQL、真实字段类型和哈希。原完整题集独立保存在 `results/m1_all_cases_before_postgres_gold79_20261010.jsonl`。
- `scripts.audit_m1_d3_gold79` 复核范围、逐题显式选择、冻结题集、允许的方言变化、276字段作用域、各场景应用权限和审查哈希。它只读取已验收 C3 快照，不能证明当前 PostgreSQL 状态或 SQL 可执行。
- 修复 `sql_policy.py` 把 SQLGlot 的 AND/OR/NOT 操作符误当数据库函数的误拦截。仍遍历全部子节点检查函数、禁止写入/schema/权限越界；未扩大数据库函数白名单。
- 默认应用配置仍为 DuckDB。本次验收通过命令级环境变量受控选择 PostgreSQL，使用服务器已配置的 askdata_readonly 与原 PG_* 参数；不需要新模型密钥。

## 2. 已完成的本地证据

| 检查 | 结果 | 材料 |
|---|---|---|
| D3专项 | 14项全部通过，包括真假类型、除法/舍入、NULL/并列、冻结评分、别名、过滤篡改拒绝及复合条件下危险函数仍拒绝 | `tests/test_m1_d3_gold79.py` |
| 全量代码回归 | 441项通过，0 failure/error/skip | `results/m1_d3_regression_local.json` |
| 最终离线审查 | 79题通过；430原 SQL 选择不变、351未覆盖行字节不变 | `results/m1_d3_gold79_audit_local_v2.json` |
| 本地结果诊断 | 原79题严格79/79；变体重新渲染为 DuckDB 后严格79/79，与原查询逐题对照79/79 | `results/m1_d3_duckdb_compatibility_local.json` |

最后一项实际后端是 DuckDB。诊断中的无精度 NUMERIC 用 DECIMAL(38,15) 在 DuckDB 模拟，避免其默认 DECIMAL(18,3) 过早截断；这不能证明 PostgreSQL 的数值转换、舍入及执行行为。正式 PostgreSQL SQL 未因诊断改变。所有本地检查均未请求模型、未连接远程 PostgreSQL。

原始离线审查 `m1_d3_gold79_audit_local.json` 也保留；v2补充各场景应用权限核对。它们都不是服务器执行报告。

## 3. 同步与服务器测试

将项目根目录的 `M1_D3_PostgreSQL_Gold79同步包_20261010.zip` 上传到远程项目根目录后执行：

```bash
cd ~/Python_work/askdata_studio_ops_release
ls -lh M1_D3_PostgreSQL_Gold79同步包_20261010.zip
unzip -o M1_D3_PostgreSQL_Gold79同步包_20261010.zip
cd backend

python -m unittest discover -s tests -p 'test_m1_d3_gold79.py' -v
python -m unittest discover -s tests -q

python -u -m scripts.audit_m1_d3_gold79 \
  --output evaluation/results/m1_d3_gold79_audit_server.json
```

专项预期14项、全量441项通过，离线审查预期79题通过。依赖沿用 `requirements.txt` 中已固定的 sqlglot==30.17.0；本次没有增加依赖。审查输出使用独立文件且拒绝覆盖，重跑时另用 `_v2` 文件名。

同步包包含冻结原题集与已验收 C3 报告的完整字节，供离线哈希核对；不包含 .env、密码、源 CSV 或 Gold 缓存。保留此前服务器其他报告。正式题集 SHA256 因新增显式变体而变化，不能把新评测作为旧运行继续 resume。

## 4. 实际执行 PostgreSQL 79题 Gold

上面测试通过、用户目录下的 PostgreSQL 服务运行后，在 backend 目录执行：

```bash
DATA_BACKEND=postgresql \
DATA_SOURCE_ID=short_video_ops_postgres \
TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_benchmark \
  --mode gold --scope all --workers 1 \
  --case-list evaluation/cases/m1_d3_postgres_gold79.json \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_d3_postgres_gold79_server.json
```

必须传入这份79题清单；当前 `--scope all` 不加清单会触及351题未审查变体并在运行前拒绝。运行前由真实 runtime 重新核对实时41表结构、权限、数据版本并装配 catalog。Gold 模式执行显式 PostgreSQL SQL，与原独立 expected_rows 严格比较，不调用模型。

首次使用独立输出文件；需要重跑时改为 `_v2.json`，避免覆盖基线。命令级环境变量只影响该命令，不编辑服务器 .env。

## 5. 验收条件和回传文件

下载 `evaluation/results/m1_d3_postgres_gold79_server.json` 到本地同名 evaluation/results 目录，再逐项核对：

- run_status=complete，题号清单与79题固定顺序一致；不能仅凭 complete 判断全部通过。
- 来源为 short_video_ops_postgres / postgresql / postgres / askdata_ops，数据版本与已验收目标一致，真实实时校验成功。
- 79/79 SQL 执行成功，79题全部可评分，宽松与严格结果均79/79，错误/未评分0；模型请求0。
- 每题 generated_sql、Gold选择键与题集 postgres 变体一致；gold_result_source=execution，comparison_target=expected_rows；不读取 DuckDB 缓存或借原SQL回退。
- 重点复核 GROWTH_OPS-051/075/076/126/148～150 的比率与真假值，CHANNEL_OPS-025 首月 NULL 和环比，CHANNEL_OPS-051/136 分母及 gap，CONTENT_OPS-036 日期，CONTENT_OPS-025 并列与 Top 10。

若执行或严格结果失败，保留该报告，逐题分析 PostgreSQL 错误/值/排序原因；不放宽评分、不改预期结果掩盖差异。修正后另存重跑报告。

79题PostgreSQL真实报告已下载并逐题核对：运行ID `e58c596bd7014a68b4f0143cc8602020`，79题执行/宽松/严格/列名匹配均通过；来源和应用/评分器版本一致，汇总重算一致。此次报告未嵌入完整返回行，尚未进行本地单元格级独立复评分；重点NULL、日期、并列的核对范围是SQL、行数和已记录严格评分。原始报告和冻结审查记录保持不变。

本轮D3首批79题报告验收完成。其余351题、D4跨来源索引/缓存/独立比较、正式PostgreSQL live与E2E仍需后续执行；本步结果不表示M1全阶段完成。
