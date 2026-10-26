# M1 E PostgreSQL v4 三组验收报告审查

审查日期：2026-10-14。原始 JSON 保存在 `results/`，本文件只记录核对结论，不改写评分或原始报告。

## 1. 报告与身份

| 报告 | SHA-256 | 运行 ID | 执行/行为 | 宽松结果 | 严格结果 |
| --- | --- | --- | --- | --- | --- |
| `results/m1_e_postgres_live_classic_server_v4.json` | `71069c4ab43ef935c9e7ea16481c33a688684b952e3b0abdbe42248a9bc56735` | `c8659a8ae7d54366b324c47d35214111` | SQL 49/49 | 49/49 | 44/49 |
| `results/m1_e_postgres_live_phase83_server_v4.json` | `e001bfffb11b9037720e759efdb5f959b4ed42e04121c7d0f5d067736fd55025` | `ece685dafeaa456c87397e62d09b2932` | SQL 30/30 | 30/30 | 28/30 |
| `results/m1_e_postgres_e2e_behavior_server_v4.json` | `858d567ec09f3eef371025af1d0e4d44e65c3919f7f5c0068eaf641abf1fea99` | `3a80aa5cf56948b9ab9cec55873ed668` | 行为 8/8 | 有结果评分 2/2 | 有结果评分 2/2 |

三份报告均为 `complete`，`validate_report_identity` 通过。逐题运行 ID、题目顺序、正式题集选中内容的摘要、Gold 选择、评分策略和重算汇总均与 manifest 相符。实际来源均为 `short_video_ops_postgres`、`postgresql`、`postgres`、`askdata_ops`；数据版本 `882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1`，catalog 版本 `94a801805965a90aa6ae015f28af196f88f72c1d887319dd1896a2973eaaa288`，物理结构版本 `b12bffb567ee4aa3ca126d48154ddfb36c1721d1af7c6e8b65efc4780615a817` 一致。记录的在线校验为 41/41 表全量类型化行与只读表/列 ACL 匹配、722732 行。应用、评测器、评测代码版本在三份报告中一致；与 v3 相比，来源数据、Gold 选择、评测器保持一致，应用版本和 live 题集评分策略按本轮修正发生变化。

两组 live 共 79/79 SQL 成功、79/79 宽松结果正确、72/79 严格结果正确、0 超时、0 连接错误、0 模型重试。所有 79 条使用现场执行的 PostgreSQL Gold，`gold_result_source=execution`、`gold_selection_key=gold_sql_by_dialect.postgres`，约束校验均为 `PASS`，无 WARN、BLOCK 或逐题错误。classic schema recall/precision 为 0.929932/0.166049；扩展 30 题为 0.967222/0.229766。

## 2. 已修正问题

上一轮核对的 `CHANNEL_OPS-004`、`CHANNEL_OPS-005`、`GROWTH_OPS-100`、`CHANNEL_OPS-102` 均已严格通过，实际与 Gold 行数分别为 30/30、31/31、1/1、2/2。`CHANNEL_OPS-025` 也已在正式 30 题运行中执行：生成 SQL 使用 `s.stat_date < '2026-06-01'`，即“截至 2026-05”的含义；约束计划为 `month_on_or_before 2026-05`，校验 `PASS`，实际与 Gold 均为 5 行，宽松及严格评分均通过。

## 3. 仍未通过的 7 题严格评分

以下 7 题均 SQL 成功、Gold 现场执行、宽松结果正确、约束校验 `PASS`。v3 中这 7 题严格通过，v4 的生成 SQL 输出列名改变后未命中正式题集中的逐题别名。表中是**待独立重放核实**的候选映射，不在本报告中修改正式评分。

| 题目 | 行数 | v4 生成输出与期望列 | 差异 |
| --- | ---: | --- | --- |
| `CHANNEL_OPS-001` | 30 | `统计日期` → `stat_date`；`广告消耗` → `spend` | 日期和消耗表达式分别为 `stat_date` 与 `SUM(spend)`；已有别名只含 `ad_spend` |
| `CHANNEL_OPS-002` | 28 | 同上 | 日期和消耗表达式相同，月份为 2026-02 |
| `CHANNEL_OPS-067` | 1 | `转化类型` → `conversion_type`；`转化数` → `conversions`；`平均价值` → `avg_value` | 表达式分别为 `conversion_type`、`COUNT(*)`、`AVG(conversion_value)` |
| `CHANNEL_OPS-069` | 1 | 同上 | activation 转化事件汇总，与 Gold 指标口径一致 |
| `CHANNEL_OPS-070` | 1 | 同上 | registration 转化事件汇总，与 Gold 指标口径一致 |
| `CHANNEL_OPS-026` | 4 | `exposure_count` → `impressions`；`click_count` → `clicks` | 分别投影 `SUM(impressions)`、`SUM(clicks)`；点击率仍为汇总后相除 |
| `CHANNEL_OPS-136` | 4 | `target_gap` → `gap` | 投影实际 CPA 减目标 CPA；该题 `order_sensitive=false` |

现有 7 条输出没有保存完整实际行，仅有 SQL、行数和宽松评分。不能仅凭列名及宽松评分直接放宽正式评分；应复用保存的 v4 SQL 和当前 PostgreSQL Gold 独立重放，验证实际行、唯一列映射及严格评分变更，并保留复评分报告。v3 的生成 SQL 与 v4 不同：classic 49 中有 28 条变动、扩展 30 中有 22 条变动；因此 v4 的 7 条新增严格失败不能当作代码功能回退直接归因。

## 4. 服务入口 E2E 逐项检查

| 用例 | 状态与核对 |
| --- | --- |
| `GROWTH_OPS-001` | PostgreSQL 查询成功，2026 年 1 至 8 月 8 行，宽松及严格评分通过；回复正确说明 9 至 12 月无数据 |
| `E2E-ROUTE-DIRECT` | 直接回复，无 SQL |
| `E2E-ROUTE-QA` | 使用上轮查询上下文解释，无重复 SQL；不作结果评分 |
| `E2E-PERMISSION-READ` | 跨用户任务读取被拒绝，无 SQL |
| `E2E-CLARIFY-START` | 暂停查询，提供 3 个指标选项，无 SQL |
| `E2E-CLARIFY-RESUME` | 选中 `option_1`“转化事件数”；实际工具 SQL 用 `converted_at >= '2026-05-01' AND < '2026-06-01'`，按事件数降序返回 4 行；回复指出最高渠道 434 次 |
| `E2E-EMPTY-RESULT` | 用 `registered_at >= '1900-01-01' AND < '1900-01-02'` 查得 0 行，回复明确说明无匹配记录；宽松及严格评分通过 |
| `E2E-FAILURE-PREPROCESS` | 预期的 preprocess 注入故障，状态 `failed`，无 SQL |

八条行为检查均为真。三条真正完成的数据库查询均调用 `query_short_video_ops`，工具的来源身份与 manifest 一致；三条工具 SQL 约束校验均为 `PASS`、无警告。另两条数据库路由场景分别停在澄清与预期故障，不能把 8/8 行为解释为 8/8 SQL 成功。结果评分只覆盖基础查询与空结果两条，均通过；澄清恢复虽有 4 行结果，但本用例没有 Gold 结果评分。

## 5. 验收判断

PostgreSQL 执行、Gold 结果、来源隔离、日期上界与服务入口行为均通过本轮检查。**M1 E 尚未满足严格评分全通过的最终验收目标**：7 题是新的逐题列名映射候选，需独立 PostgreSQL 重放和审查后再更新正式题集，随后用新文件名重跑三组。v4 三份 JSON 保留为本轮原始证据。

## 6. 79 题逐题状态

下表由 v4 JSON 的逐题字段生成；`通过`/`失败` 分别对应布尔 `true`/`false`。

| 组别 | Case ID | SQL 执行 | 结果 | 严格结果 | 约束校验 |
| --- | --- | --- | --- | --- | --- |
| classic 49 | GROWTH_OPS-001 | 通过 | 通过 | 通过 | PASS |
| classic 49 | GROWTH_OPS-002 | 通过 | 通过 | 通过 | PASS |
| classic 49 | GROWTH_OPS-003 | 通过 | 通过 | 通过 | PASS |
| classic 49 | GROWTH_OPS-004 | 通过 | 通过 | 通过 | PASS |
| classic 49 | GROWTH_OPS-005 | 通过 | 通过 | 通过 | PASS |
| classic 49 | GROWTH_OPS-006 | 通过 | 通过 | 通过 | PASS |
| classic 49 | GROWTH_OPS-026 | 通过 | 通过 | 通过 | PASS |
| classic 49 | GROWTH_OPS-061 | 通过 | 通过 | 通过 | PASS |
| classic 49 | GROWTH_OPS-062 | 通过 | 通过 | 通过 | PASS |
| classic 49 | GROWTH_OPS-063 | 通过 | 通过 | 通过 | PASS |
| classic 49 | GROWTH_OPS-064 | 通过 | 通过 | 通过 | PASS |
| classic 49 | GROWTH_OPS-066 | 通过 | 通过 | 通过 | PASS |
| classic 49 | GROWTH_OPS-086 | 通过 | 通过 | 通过 | PASS |
| classic 49 | GROWTH_OPS-101 | 通过 | 通过 | 通过 | PASS |
| classic 49 | GROWTH_OPS-131 | 通过 | 通过 | 通过 | PASS |
| classic 49 | GROWTH_OPS-149 | 通过 | 通过 | 通过 | PASS |
| classic 49 | GROWTH_OPS-150 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CHANNEL_OPS-001 | 通过 | 通过 | 失败 | PASS |
| classic 49 | CHANNEL_OPS-002 | 通过 | 通过 | 失败 | PASS |
| classic 49 | CHANNEL_OPS-003 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CHANNEL_OPS-004 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CHANNEL_OPS-005 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CHANNEL_OPS-066 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CHANNEL_OPS-067 | 通过 | 通过 | 失败 | PASS |
| classic 49 | CHANNEL_OPS-068 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CHANNEL_OPS-069 | 通过 | 通过 | 失败 | PASS |
| classic 49 | CHANNEL_OPS-070 | 通过 | 通过 | 失败 | PASS |
| classic 49 | CHANNEL_OPS-076 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CHANNEL_OPS-077 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CHANNEL_OPS-078 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CHANNEL_OPS-079 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CHANNEL_OPS-101 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CHANNEL_OPS-141 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CONTENT_OPS-001 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CONTENT_OPS-029 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CONTENT_OPS-030 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CONTENT_OPS-031 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CONTENT_OPS-032 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CONTENT_OPS-033 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CONTENT_OPS-034 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CONTENT_OPS-035 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CONTENT_OPS-036 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CONTENT_OPS-051 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CONTENT_OPS-076 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CONTENT_OPS-121 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CONTENT_OPS-126 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CONTENT_OPS-136 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CONTENT_OPS-137 | 通过 | 通过 | 通过 | PASS |
| classic 49 | CONTENT_OPS-138 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | GROWTH_OPS-007 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | GROWTH_OPS-050 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | GROWTH_OPS-051 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | GROWTH_OPS-075 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | GROWTH_OPS-076 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | GROWTH_OPS-100 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | GROWTH_OPS-102 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | GROWTH_OPS-125 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | GROWTH_OPS-126 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | GROWTH_OPS-148 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CHANNEL_OPS-006 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CHANNEL_OPS-025 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CHANNEL_OPS-026 | 通过 | 通过 | 失败 | PASS |
| 扩展 30 | CHANNEL_OPS-050 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CHANNEL_OPS-051 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CHANNEL_OPS-080 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CHANNEL_OPS-100 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CHANNEL_OPS-102 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CHANNEL_OPS-126 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CHANNEL_OPS-136 | 通过 | 通过 | 失败 | PASS |
| 扩展 30 | CONTENT_OPS-002 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CONTENT_OPS-025 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CONTENT_OPS-026 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CONTENT_OPS-050 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CONTENT_OPS-052 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CONTENT_OPS-077 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CONTENT_OPS-100 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CONTENT_OPS-101 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CONTENT_OPS-125 | 通过 | 通过 | 通过 | PASS |
| 扩展 30 | CONTENT_OPS-150 | 通过 | 通过 | 通过 | PASS |
