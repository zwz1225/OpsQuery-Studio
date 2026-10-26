# M1 E PostgreSQL v7 三组验收核对

核对日期：2026-10-15。三份 v7 原始 JSON 保留，不覆盖、不改写原始严格评分。

## 报告与来源

| 报告 | SHA-256 | 运行 ID | 状态 |
| --- | --- | --- | --- |
| `results/m1_e_postgres_live_classic_server_v7.json` | `b3f0aef50b51665b3c665b6faa701d24c4401d34331742c310d001ff4c22ffde` | `11abb1018c0c4827ab1c49a74f01194e` | complete |
| `results/m1_e_postgres_live_phase83_server_v7.json` | `188c170d24128c1f347bf79ce1ebd4dd8f0616508b51f032ae02f202b4495f49` | `479cad5112c141e0a393282672663e90` | complete |
| `results/m1_e_postgres_e2e_behavior_server_v7.json` | `355b41794a876857bbf130c30f625d09d550412de3e112588d8475b277e79c46` | `3a75f233b6254caa82052bf20e383e91` | complete |

三个 `validate_report_identity` 均通过。正式题集 SHA-256 为 `82761737b873c9d4e9daac852bb3bf30867adc01919d088289dc9ba03972ed33`；两组 live 的选题版本均与本地正式题集逐题重算一致，49 + 30 个 case ID 无重复且与各自运行清单顺序一致。E2E 8 条与 `evaluation/cases/e2e_behavior_postgres.json` 的顺序一致。

三个来源身份完全相同：`short_video_ops_postgres` / PostgreSQL / `askdata_ops`，数据版本 `882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1`，catalog 版本 `94a801805965a90aa6ae015f28af196f88f72c1d887319dd1896a2973eaaa288`，物理结构版本 `b12bffb567ee4aa3ca126d48154ddfb36c1721d1af7c6e8b65efc4780615a817`。运行清单的应用、评测器和评测代码版本一致。实时目标核验为 41 张表、276 字段、722732 行；41/41 完整类型化行摘要、表级及字段级只读 ACL 均通过。

## Live 79 题

| 集合 | SQL 执行 | 宽松结果 | 原始 live 严格结果 | 约束校验 |
| --- | ---: | ---: | ---: | --- |
| classic 49 | 49/49 | 49/49 | **46/49** | 49 PASS，0 WARN |
| phase83 30 | 30/30 | 30/30 | **30/30** | 30 PASS，0 WARN |
| 合计 | **79/79** | **79/79** | **76/79** | 79 PASS，0 WARN |

两组 live 汇总均与逐题重新计算一致；79 题 Gold 均由 PostgreSQL `gold_sql_by_dialect.postgres` 执行取得，0 未评分、0 SQL 失败、0 模型重试、0 超时、0 连接错误。classic schema recall/precision 为 `0.929932/0.166049`；phase83 为 `0.967222/0.229766`。低精度仍是后续检索改进事项。`CHANNEL_OPS-025` 使用 `stat_date < DATE '2026-06-01'` 表示截至 2026-05，日期约束 PASS；`GROWTH_OPS-051`、`CONTENT_OPS-025` 和 `CONTENT_OPS-052` 均执行且严格通过。v6 的 `CHANNEL_OPS-066` 与 `CONTENT_OPS-138` 在 v7 严格通过。

classic 三处原始严格失败，均执行成功、宽松结果正确、Gold 来源及约束校验正确：

1. `GROWTH_OPS-066`：4/4 行。Gold 期望 `activation_rule`、`users`；生成 SQL 投影 `ua.activation_rule AS "激活规则"`、`COUNT(*) AS "用户数"`。正式题集已有 `users → user_count`，候选新增 `activation_rule → 激活规则`、`users → 用户数`。首个严格错误为 `activation_rule` 缺失或映射不唯一。
2. `CHANNEL_OPS-003`：31/31 行。Gold 期望 `stat_date`、`spend`；生成 SQL 投影 `ad_daily_stats.stat_date AS "统计日期"`、`SUM(ad_daily_stats.spend) AS "广告消耗"`。正式题集已有 `spend → ad_spend`，候选新增 `stat_date → 统计日期`、`spend → 广告消耗`。首个严格错误为 `stat_date` 缺失或映射不唯一。该题 2026-03 左闭右开日期范围正确，约束 PASS。
3. `CHANNEL_OPS-076`：1/1 行。Gold 期望 `status`、`campaigns`、`budget`；生成 SQL 投影 `ac.status AS "状态"`、`COUNT(*) AS "广告计划数"`、`SUM(ac.budget) AS "预算"`。正式题集已有 `campaigns → ad_campaign_count`、`budget → total_budget`，候选新增 `status → 状态`、`campaigns → 广告计划数`、`budget → 预算`。首个严格错误为 `status` 缺失或映射不唯一。

这些仅是 **7 项逐题候选别名**；目前尚未独立重放 PostgreSQL 保存 SQL 与 Gold，不能据此改动正式题集或把 v7 原始严格成绩写为 79/79。v6 中这三题使用其他列名且严格通过，v7 列名随模型输出变化。

## 服务入口 E2E 8 条

8/8 行为检查通过；2 条设计为结果评分的用例均宽松及严格通过。其余 6 条在用例中设为不评分。`sql_case_count=5` 是路由计数；执行日志显示实际 3 次 SQL 工具调用，均成功，SQL 校验和约束校验均为 PASS，所有 warnings 为空。

直答与已有结果的数据问答没有重复 SQL；跨用户读取被拒绝；澄清开始返回三个可选指标，澄清继续记录 `option_1=转化事件数`，SQL 从 `askdata_ops.channel_conversion_events` 按 `converted_at >= '2026-05-01'` 且 `< '2026-06-01'` 统计，返回 4 行并明确最优渠道。空结果用例查询 1900-01-01 左闭右开日范围，返回 0 行，最终分析明确表示无匹配记录。受控预处理失败停在预期阶段。

## 验收结论

M1 E v7 的执行、结果值、来源身份、服务入口行为和校验 WARN 门槛均通过；**原始 live 严格评分为 76/79，尚未满足此前的 79/79 目标，因此不能据此宣告 M1 最终验收完成。** 下一步保留 v7 原始证据，对三题七项候选逐题检查 SQL 投影含义，在同一已核验 PostgreSQL 数据上独立重放保存 SQL 和 Gold；复评分通过后再更新正式题集并保存独立记录。若最终门槛仍要求新 live 79/79，应以新文件名重跑并再次检查模型列名漂移。
