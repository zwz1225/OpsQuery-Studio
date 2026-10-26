# M1 E v4 七题 PostgreSQL 独立复评分核对

核对日期：2026-10-14。原始复评分报告 `results/m1_e_v4_strict7_rescore_server.json` 保持原样，SHA-256 为 `7a400f6ce7835672a80e2f30fd8ac6147366b8f96c3a7983c05a771fd96fed92`，运行 ID `d339d67b544249d29a3b0fd903278117`，状态 `complete`。

## 来源与证据

- 复评分输入的正式题集 SHA-256 为 `22a7ee6f9d8d2309e79ceb5d831468b30f609c485a0a31ba5d1a0cbde3d9ba6b`，报告声明且实际保持未修改。
- classic v4 报告 SHA-256 `71069c4ab43ef935c9e7ea16481c33a688684b952e3b0abdbe42248a9bc56735`；phase83 v4 报告 SHA-256 `e001bfffb11b9037720e759efdb5f959b4ed42e04121c7d0f5d067736fd55025`，均与报告记录一致。
- `validate_report_identity`、复评分题目清单/摘要、Gold 选择与候选评分策略摘要均通过重新计算。七条保存 SQL 与各自 v4 原始报告逐字一致，SQL SHA-256、源运行 ID、原 Gold SQL 均吻合。
- 运行来源为 `short_video_ops_postgres`、`postgresql`、`askdata_ops`；数据版本 `882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1`，catalog 版本 `94a801805965a90aa6ae015f28af196f88f72c1d887319dd1896a2973eaaa288`，物理结构版本 `b12bffb567ee4aa3ca126d48154ddfb36c1721d1af7c6e8b65efc4780615a817`，与 v4 来源一致。现场验证记录 41/41 表的完整类型化行和只读权限匹配。
- PostgreSQL 执行器重新运行保存的 SQL 和 Gold；Gold 来源为现场执行，不使用缓存。七题 Gold 与冻结期望严格一致，实际/Gold 行数与 v4 报告一致。复评分未请求模型。

## 七题实际复评分

| 题目 | 实际/Gold 行数 | 显式列映射新增项 | 原严格 | 候选严格 | 宽松 |
| --- | ---: | --- | --- | --- | --- |
| `CHANNEL_OPS-001` | 30/30 | `统计日期 → stat_date`、`广告消耗 → spend` | 失败 | 通过 | 通过 |
| `CHANNEL_OPS-002` | 28/28 | 同上，限定在本题 | 失败 | 通过 | 通过 |
| `CHANNEL_OPS-067` | 1/1 | `转化类型 → conversion_type`、`转化数 → conversions`、`平均价值 → avg_value` | 失败 | 通过 | 通过 |
| `CHANNEL_OPS-069` | 1/1 | 同上，限定在本题 | 失败 | 通过 | 通过 |
| `CHANNEL_OPS-070` | 1/1 | 同上，限定在本题 | 失败 | 通过 | 通过 |
| `CHANNEL_OPS-026` | 4/4 | `exposure_count → impressions`、`click_count → clicks` | 失败 | 通过 | 通过 |
| `CHANNEL_OPS-136` | 4/4 | `target_gap → gap` | 失败 | 通过 | 通过 |

对报告保存的完整实际行及 Gold 行重新运行严格评分，得到原规则 0/7、候选规则 7/7、宽松 7/7；没有新增辅助列许可或通配映射。`CHANNEL_OPS-136` 的 PostgreSQL 行中，搜索广告 `actual_cpa=12.21`，与 Gold 的 12.21 一致，`target_gap=-137.66` 与 `gap=-137.66` 一致。本地 DuckDB 重放时该行曾为 12.22；这是跨数据库数值计算差异，本次 PostgreSQL 现场重放消除了这一疑点。

## 题集应用与剩余工作

本地已在上述证据通过后运行受保护的应用脚本。更新前题集保存为 `results/m1_e_all_cases_before_v4_strict7_20261014.jsonl`（SHA-256 `22a7ee6f9d8d2309e79ceb5d831468b30f609c485a0a31ba5d1a0cbde3d9ba6b`）；更新后正式 `cases/all_cases.jsonl` SHA-256 为 `ff5956e9f4aca878ee63e232bdea1fef3416a28eda72669f91a33546c70f3adc`。只改动上述七题的 16 项逐题显式别名，未改题意、Gold SQL、期望行或评分器。应用证据为 `results/m1_e_v4_strict7_apply_local.json`。本地完整回归 501 项通过。

服务器需使用同一份复评分报告运行受保护的应用脚本，并核对更新后题集 SHA-256 与本地一致。随后以新文件名重跑 PostgreSQL classic 49、扩展 30、服务入口 E2E 8 条；只有核对 v5 全部来源、结果及严格评分后，才能给出 M1 E 最终验收结论。
