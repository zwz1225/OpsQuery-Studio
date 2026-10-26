# M1 E PostgreSQL v3 正式复验核对

核对日期：2026-10-13。原始报告保留在 `results/`，本文件只记录审核结论，不改变原始 JSON 或评分规则。

| 报告 | SHA-256 | 运行 ID | 结论 |
| --- | --- | --- | --- |
| `results/m1_e_postgres_live_classic_server_v3.json` | `ad6eaf3b8b4647a38ea70aa3c3cb11278231746dd12de7370e0aa97254cf7ca2` | `41347c0a292942d1b4b0f45c7b9ff0d7` | 49/49 执行，49/49 普通结果，47/49 严格结果 |
| `results/m1_e_postgres_live_phase83_server_v3.json` | `408e7052fe3c4251832526087cf1c254004788b34a18adf95e9ddd3fa4a20a43` | `853f3db4df48422c9d25eb605b0bebc2` | 29/30 执行，29/30 普通结果，27/29 已评分题严格结果 |
| `results/m1_e_postgres_e2e_behavior_server_v3.json` | `75e015a4794df39496184a6597e02294499751c4bc6b851867f2807c0eefdd55` | `7e95f20d46bf4816ba874cc2f4189898` | 8/8 行为，2/2 有结果评分的题严格通过 |

三份报告均为 `complete`，运行清单指纹、逐题运行 ID、来源身份、Gold 选择摘要、评分策略摘要与逐题重算的 summary 一致。49 题和 30 题的选中题目摘要与当前本地正式题集逐题重算结果一致。来源统一为 `short_video_ops_postgres`、`postgres`、`askdata_ops`；数据版本 `882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1`，catalog 版本 `94a801805965a90aa6ae015f28af196f88f72c1d887319dd1896a2973eaaa288`，物理结构版本 `b12bffb567ee4aa3ca126d48154ddfb36c1721d1af7c6e8b65efc4780615a817`。实时校验记录 41 表、276 字段、722732 行，以及 41 表的完整类型化行和只读权限匹配。应用、评测器、评测代码摘要在三份报告中一致。所有 78 条执行成功的 live 题使用 PostgreSQL Gold 的重新执行结果评分，未命中缓存。

## 阻碍与评分差异

1. `CHANNEL_OPS-025`：扩展集唯一没有执行 SQL 的题。问题要求“截至 2026-05 各月”，Gold 用 `TO_CHAR(stat_date, 'YYYY-MM') <= '2026-05'`。模型三次给出相同候选，条件为 `stat_date < DATE '2026-06-01'`，表达了相同的截至上界；但日期约束被规划成 `month_equals 2026-05`，三次在调用数据库前被判定为缺少月份条件，最终 `error_stage=single_database_agent`。候选 SQL 的字段校验另有 CTE 列 `month`、`total_spend` 来源可能不唯一的 WARN；这一 WARN 需要单独检查，但直接阻断是日期约束 `BLOCK`。本题没有生成的执行结果，不能把它算作严格评分失败或通过。
2. `CHANNEL_OPS-004`、`CHANNEL_OPS-005`：分别返回 2026 年 4 月 30 行、5 月 31 行，普通结果与 PostgreSQL Gold 一致，约束校验 `PASS`。生成 SQL 用 `ad_daily_stats.stat_date` 投影为乱码引号列名，现有逐题别名未将其映射至 `stat_date`，故严格评分失败。`SUM(spend)` 与 Gold 的两位小数舍入在当前冻结数据上结果一致；未来数据仍需独立审查。
3. `GROWTH_OPS-100`：返回 1 行，普通结果正确、约束校验 `PASS`。生成列 `avg_plays_per_user` 未映射至 `plays_per_user`，且返回了 `total_play_count`、`distinct_user_count` 两个未声明的辅助列；仅添加比率列别名仍不能满足现行严格评分。
4. `CHANNEL_OPS-102`：返回 2 行，普通结果正确、约束校验 `PASS`。生成的创意状态列名未映射至 `creative_status`；数量列也采用另一输出名。生成 SQL 的 `COUNT(*)` 与 Gold 的 `COUNT(creative_id)` 在当前数据上相同，存在未来空值分布下的口径差异，需要在决定是否添加别名前审查。

`GROWTH_OPS-051` 在扩展集内实际执行成功、普通和严格结果均通过，解决了此前的 `bigint = true` 失败；日期条件为注册时间在 2026 年 1 月的左闭右开区间。其余 77 条成功执行题的查询契约均为 `PASS`，没有约束 WARN。classic 49 题全部执行成功。扩展集中 `CHANNEL_OPS-025` 以外的 29 题全部执行成功且普通结果正确。

## E2E 行为核对

| 题目 | 核对结果 |
| --- | --- |
| `GROWTH_OPS-001` | PostgreSQL 查询完成，8 行，普通与严格评分均通过；实际月份为 2026 年 1–8 月，回复反映了这一范围。 |
| `E2E-ROUTE-DIRECT` | 直接回复，未发 SQL。 |
| `E2E-ROUTE-QA` | 使用上一条查询上下文解释结果，未重复查询。 |
| `E2E-PERMISSION-READ` | 跨用户读取任务被拒绝。 |
| `E2E-CLARIFY-START` | 暂停查询，给出三个澄清选项，未发 SQL。 |
| `E2E-CLARIFY-RESUME` | 选中的 `option_1` 是“转化事件数量”；工具 SQL 使用 `channel_conversion_events.converted_at >= 2026-05-01` 且 `< 2026-06-01`，按渠道计数降序返回 4 行，回复正确引用最高值 434。该题未要求结果评分，顶层 `generated_sql` 为空，但真实 SQL 保存在 `trace.tool_calls[0].sql`。 |
| `E2E-EMPTY-RESULT` | PostgreSQL 查询成功，1900-01-01 至 1900-01-02 左闭右开区间返回 0 行；回复明确说明当前条件没有匹配记录，普通与严格评分通过。 |
| `E2E-FAILURE-PREPROCESS` | 注入的预处理故障进入预期的 `failed_explicitly` 状态，未发 SQL。 |

E2E 报告的 8 条行为检查全部通过；五条数据库相关场景中，实际完成 SQL 的是基础查询、澄清恢复和空结果三条，两条分别停在澄清和预期受控失败。E2E 记录中没有 `WARN` 或 `BLOCK` 校验状态。此报告只对基础查询和空结果两条做结果评分，不能将 8/8 行为通过解释为 8/8 结果准确。

## 验收判断

**M1 E 暂不通过最终验收。** 49 题与 30 题合计 79 题中，78 题执行成功且普通结果正确，74/78 已评分题严格通过；仍有一题未执行、四题严格列结构失败。E2E 8/8 行为通过，可保留为这一版服务入口验收证据。继续处理 `CHANNEL_OPS-025` 的“截至某月”上界校验，再逐题审查四题输出列及辅助列；保留本次 v3 报告作为修正前基线。修正后的独立报告必须使用新文件名，并再次核对全部三组运行身份与结果。

## 逐题状态

下表由三份原始 JSON 的逐题字段生成。`—` 表示该项未评分；`是`/`否` 分别对应 JSON 的 `true`/`false`。

### Classic 49

| Case ID | SQL executed | Result correct | Strict correct | Exception |
| --- | --- | --- | --- | --- |
| GROWTH_OPS-001 | 是 | 是 | 是 |  |
| GROWTH_OPS-002 | 是 | 是 | 是 |  |
| GROWTH_OPS-003 | 是 | 是 | 是 |  |
| GROWTH_OPS-004 | 是 | 是 | 是 |  |
| GROWTH_OPS-005 | 是 | 是 | 是 |  |
| GROWTH_OPS-006 | 是 | 是 | 是 |  |
| GROWTH_OPS-026 | 是 | 是 | 是 |  |
| GROWTH_OPS-061 | 是 | 是 | 是 |  |
| GROWTH_OPS-062 | 是 | 是 | 是 |  |
| GROWTH_OPS-063 | 是 | 是 | 是 |  |
| GROWTH_OPS-064 | 是 | 是 | 是 |  |
| GROWTH_OPS-066 | 是 | 是 | 是 |  |
| GROWTH_OPS-086 | 是 | 是 | 是 |  |
| GROWTH_OPS-101 | 是 | 是 | 是 |  |
| GROWTH_OPS-131 | 是 | 是 | 是 |  |
| GROWTH_OPS-149 | 是 | 是 | 是 |  |
| GROWTH_OPS-150 | 是 | 是 | 是 |  |
| CHANNEL_OPS-001 | 是 | 是 | 是 |  |
| CHANNEL_OPS-002 | 是 | 是 | 是 |  |
| CHANNEL_OPS-003 | 是 | 是 | 是 |  |
| CHANNEL_OPS-004 | 是 | 是 | 否 | 列 stat_date 缺失或映射不唯一 |
| CHANNEL_OPS-005 | 是 | 是 | 否 | 列 stat_date 缺失或映射不唯一 |
| CHANNEL_OPS-066 | 是 | 是 | 是 |  |
| CHANNEL_OPS-067 | 是 | 是 | 是 |  |
| CHANNEL_OPS-068 | 是 | 是 | 是 |  |
| CHANNEL_OPS-069 | 是 | 是 | 是 |  |
| CHANNEL_OPS-070 | 是 | 是 | 是 |  |
| CHANNEL_OPS-076 | 是 | 是 | 是 |  |
| CHANNEL_OPS-077 | 是 | 是 | 是 |  |
| CHANNEL_OPS-078 | 是 | 是 | 是 |  |
| CHANNEL_OPS-079 | 是 | 是 | 是 |  |
| CHANNEL_OPS-101 | 是 | 是 | 是 |  |
| CHANNEL_OPS-141 | 是 | 是 | 是 |  |
| CONTENT_OPS-001 | 是 | 是 | 是 |  |
| CONTENT_OPS-029 | 是 | 是 | 是 |  |
| CONTENT_OPS-030 | 是 | 是 | 是 |  |
| CONTENT_OPS-031 | 是 | 是 | 是 |  |
| CONTENT_OPS-032 | 是 | 是 | 是 |  |
| CONTENT_OPS-033 | 是 | 是 | 是 |  |
| CONTENT_OPS-034 | 是 | 是 | 是 |  |
| CONTENT_OPS-035 | 是 | 是 | 是 |  |
| CONTENT_OPS-036 | 是 | 是 | 是 |  |
| CONTENT_OPS-051 | 是 | 是 | 是 |  |
| CONTENT_OPS-076 | 是 | 是 | 是 |  |
| CONTENT_OPS-121 | 是 | 是 | 是 |  |
| CONTENT_OPS-126 | 是 | 是 | 是 |  |
| CONTENT_OPS-136 | 是 | 是 | 是 |  |
| CONTENT_OPS-137 | 是 | 是 | 是 |  |
| CONTENT_OPS-138 | 是 | 是 | 是 |  |

### Phase83 30

| Case ID | SQL executed | Result correct | Strict correct | Exception |
| --- | --- | --- | --- | --- |
| GROWTH_OPS-007 | 是 | 是 | 是 |  |
| GROWTH_OPS-050 | 是 | 是 | 是 |  |
| GROWTH_OPS-051 | 是 | 是 | 是 |  |
| GROWTH_OPS-075 | 是 | 是 | 是 |  |
| GROWTH_OPS-076 | 是 | 是 | 是 |  |
| GROWTH_OPS-100 | 是 | 是 | 否 | 列 plays_per_user 缺失或映射不唯一 |
| GROWTH_OPS-102 | 是 | 是 | 是 |  |
| GROWTH_OPS-125 | 是 | 是 | 是 |  |
| GROWTH_OPS-126 | 是 | 是 | 是 |  |
| GROWTH_OPS-148 | 是 | 是 | 是 |  |
| CHANNEL_OPS-006 | 是 | 是 | 是 |  |
| CHANNEL_OPS-025 | 否 | 否 | — | date constraint BLOCK before SQL; 3 rejected candidates |
| CHANNEL_OPS-026 | 是 | 是 | 是 |  |
| CHANNEL_OPS-050 | 是 | 是 | 是 |  |
| CHANNEL_OPS-051 | 是 | 是 | 是 |  |
| CHANNEL_OPS-080 | 是 | 是 | 是 |  |
| CHANNEL_OPS-100 | 是 | 是 | 是 |  |
| CHANNEL_OPS-102 | 是 | 是 | 否 | 列 creative_status 缺失或映射不唯一 |
| CHANNEL_OPS-126 | 是 | 是 | 是 |  |
| CHANNEL_OPS-136 | 是 | 是 | 是 |  |
| CONTENT_OPS-002 | 是 | 是 | 是 |  |
| CONTENT_OPS-025 | 是 | 是 | 是 |  |
| CONTENT_OPS-026 | 是 | 是 | 是 |  |
| CONTENT_OPS-050 | 是 | 是 | 是 |  |
| CONTENT_OPS-052 | 是 | 是 | 是 |  |
| CONTENT_OPS-077 | 是 | 是 | 是 |  |
| CONTENT_OPS-100 | 是 | 是 | 是 |  |
| CONTENT_OPS-101 | 是 | 是 | 是 |  |
| CONTENT_OPS-125 | 是 | 是 | 是 |  |
| CONTENT_OPS-150 | 是 | 是 | 是 |  |

