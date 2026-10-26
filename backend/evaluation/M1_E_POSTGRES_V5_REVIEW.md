# M1 E PostgreSQL v5 验收报告核对

核对日期：2026-10-14。本报告只记录三份服务器 v5 JSON 中已有的证据；三份原始报告保留在 `evaluation/results/`。

## 来源与完整性

| 报告 | SHA-256 | 运行 ID | 状态 |
| --- | --- | --- | --- |
| `m1_e_postgres_live_classic_server_v5.json` | `bd8d2a5fb01d0a87c34f43656ae228183b7f7e8efa3143519e862060fd8ef37e` | `4d173d09c42b468b992942c4e2a6cfb2` | complete |
| `m1_e_postgres_live_phase83_server_v5.json` | `41a2670f7dc5fd6cc490149d36d4fe9cd2f2b2c9239f278446b6c9560cf18af6` | `9102289c2003472dbbe2e39a2ef9996f` | complete |
| `m1_e_postgres_e2e_behavior_server_v5.json` | `a0a195fc3fa57668acff5d37c7304dce99a230bbb3a6ff1f8be33347b0bb6c76` | `c0b8473d46564741abe0293a5e3e53da` | complete |

三个报告均通过 `validate_report_identity`，并与本地正式题集重算的选题版本一致。正式题集 `evaluation/cases/all_cases.jsonl` 的 SHA-256 为 `ff5956e9f4aca878ee63e232bdea1fef3416a28eda72669f91a33546c70f3adc`。来源均为 `short_video_ops_postgres` / PostgreSQL / `askdata_ops`；数据版本 `882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1`，catalog 版本 `94a801805965a90aa6ae015f28af196f88f72c1d887319dd1896a2973eaaa288`，物理结构版本 `b12bffb567ee4aa3ca126d48154ddfb36c1721d1af7c6e8b65efc4780615a817`。实时验证记录包含 41 张表、276 个字段、722732 行，以及 41/41 完整类型化行摘要和只读权限校验。

## Classic 49 题

49/49 SQL 执行成功，49/49 宽松结果正确，48/49 严格结果正确；49 题约束校验均为 PASS，无约束 WARN。49 题均从 PostgreSQL Gold SQL 实时执行取结果。唯一严格失败为 `CONTENT_OPS-001`：本次生成 SQL 输出 `"指标日期"`、`"曝光量"`、`"播放量"`，Gold 列为 `metric_date`、`impressions`、`plays`；31 行数据宽松比较正确，但严格比较首先报告 `metric_date` 缺失或映射不唯一。v4 同题输出英文列名且严格通过。需要逐列确认三个中文列名与 Gold 列的语义对应，再独立复评分；不得把本次宽松正确当作严格通过。

## 扩展 30 题

29/30 SQL 执行成功，29/30 宽松结果正确，29/30 严格结果正确；30 题约束校验均为 PASS，无约束 WARN。失败题为 `CHANNEL_OPS-136`，三个 SQL 工具调用均失败，最终报 `PostgreSQL query_error (SQLSTATE 42703)`，未执行 Gold 比较。本次生成 SQL 使用 `ORDER BY ABS(target_gap) DESC`，而 `target_gap` 是同层 SELECT 输出别名；这是 `42703` 的主要嫌疑，具体数据库错误文本未写入报告，因此仍需用独立诊断核实。v4 同题 SQL 执行、宽松结果均通过，严格评分因缺少 `gap` 显式别名而失败；v5 的新失败不能用列别名复评分修复。

v4 审核出的七题中，`CHANNEL_OPS-001/002/067/069/070/026` 在 v5 均已严格通过；`CHANNEL_OPS-136` 因本次生成 SQL 执行失败而未通过。49 与 30 两组选题合计 79 个唯一 case ID；总体为 78/79 SQL 执行和宽松结果、77/79 严格结果。

## 服务入口 E2E 8 条

8/8 行为通过；3 条实际 SQL 执行成功，2 条有 Gold 结果评分且均严格通过，6 条按用例设计不做结果评分。入口路由、跨用户拒绝、澄清开始与继续、空结果、受控失败的行为状态均符合预期。澄清继续明确接收 `option_1`（转化事件数），SQL 使用 `channel_conversion_events.converted_at >= '2026-05-01'` 且 `< '2026-06-01'`，返回 4 行并按转化数降序；空结果 SQL 用 `registered_at >= '1900-01-01'` 且 `< '1900-01-02'`，返回 0 行，回复明确说明无匹配记录。三个实际 SQL 工具调用的 SQL 与约束校验均为 PASS，warnings 均为空。受控预处理失败被正确记录为预期行为。澄清继续属于行为评分，未做独立 Gold 结果评分。

## 结论与下一步

M1 E v5 **尚未达到完整验收条件**：79 题 live 中仍有一题 SQL 执行失败、一题严格评分失败。保留全部 v5 原始报告；先诊断 `CHANNEL_OPS-136` 的 `42703` 并修正 PostgreSQL SQL 生成/校验，再对 `CONTENT_OPS-001` 的三列做逐列语义审查和独立复评分。修正后以新文件名重新运行 classic、扩展集和 E2E，逐份核对来源身份与结果，再决定最终验收。
