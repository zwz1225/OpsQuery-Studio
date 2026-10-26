# M1 E v5 两题独立诊断复核

核对日期：2026-10-14。两份服务器报告与原始 v5 报告及更新前正式题集关联。运行时来源均为 `short_video_ops_postgres` / PostgreSQL / `askdata_ops`，数据版本 `882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1`，catalog 版本 `94a801805965a90aa6ae015f28af196f88f72c1d887319dd1896a2973eaaa288`，物理结构版本 `b12bffb567ee4aa3ca126d48154ddfb36c1721d1af7c6e8b65efc4780615a817`。实时来源验证仍显示 41 张表、276 个字段、722732 行及 41/41 行摘要和只读权限校验。

## CHANNEL_OPS-136

原始 v5 扩展集报告 SHA-256 为 `41a2670f7dc5fd6cc490149d36d4fe9cd2f2b2c9239f278446b6c9560cf18af6`，运行 ID 为 `9102289c2003472dbbe2e39a2ef9996f`。独立诊断文件 `evaluation/results/m1_e_v5_channel136_diagnostic_server.json` SHA-256 为 `2658739e7f6f64aaf3e0840d88e111b0113c1653cbb4cb753f1a103fe450ac0f`；诊断运行 ID 为 `545c7a1022da4ade9f8411b8a71e4a2f`，清单指纹及选题、Gold、结果策略版本重算均正确。

原 SQL SHA-256 `e8c07dd1a966eb9181d576f03b8b377ad6a5be11b1a2dcd0439a6289614becbd`，其中 `ORDER BY ABS(target_gap)` 在函数内引用同层 `SELECT` 别名。服务器重新执行该 SQL，复现 `SQLSTATE 42703`；新校验器将其标为 BLOCK。确定性改写后的 SQL SHA-256 `9348d96ffe2d0bab179c20ea8743205fc6768c9732b7c5cff73381df7e36f2ff`，将别名展开为原始 `ROUND(...)` 表达式，校验 PASS 且实际执行成功。重新执行 PostgreSQL Gold 后，4 行实际与 Gold 宽松、严格评分均通过；例如搜索广告的 `actual_cpa=12.21`、`gap=-137.66` 两边一致。无新模型请求，题集未被诊断脚本修改。

## CONTENT_OPS-001

原始 v5 classic 报告 SHA-256 为 `bd8d2a5fb01d0a87c34f43656ae228183b7f7e8efa3143519e862060fd8ef37e`，运行 ID 为 `4d173d09c42b468b992942c4e2a6cfb2`。独立复评分文件 `evaluation/results/m1_e_v5_content001_rescore_server.json` SHA-256 为 `333a4b6ba7aa9aef2cee4efb90aa389aaf576eb154727b80fa6ff2a3aecbd3e4`；复评分运行 ID 为 `ba06424761384d52837571dd9b014a27`，通过完整报告身份校验。

保存的生成 SQL SHA-256 `2da9406a2084936de17c7f397766ca9712049f3a476c7fb722252f36fdb76174`。三个输出列逐列核对为：

| Gold 列 | 实际列 | SQL 表达式 |
| --- | --- | --- |
| `metric_date` | `指标日期` | `cdm.metric_date` |
| `impressions` | `曝光量` | `SUM(cdm.impressions)` |
| `plays` | `播放量` | `SUM(cdm.play_count)` |

服务器重新执行保存的 SQL 和 PostgreSQL Gold，各返回 31 行。原始严格评分 false，逐题添加这三项候选别名后为 true，宽松结果仍为 true。复评分报告中的每行实际和 Gold 数据重新计算得到相同结论；没有辅助列放行和新模型请求。

## 正式题集及后续

原始正式题集 SHA-256 为 `ff5956e9f4aca878ee63e232bdea1fef3416a28eda72669f91a33546c70f3adc`。本地已通过受保护的应用脚本，只对 `CONTENT_OPS-001` 新增三项显式别名；更新后 SHA-256 为 `08cf84a50f43eb2d176d96246e1210c398a13a89beec69a9d0db1b7361b7815a`。原始题集副本保存在 `evaluation/results/m1_e_all_cases_before_v5_content001_20261014.jsonl`，应用报告为 `evaluation/results/m1_e_v5_content001_apply_local.json`。服务器尚须使用相同复评分 SHA-256 执行应用脚本，再分别用新文件名运行三组 v6 验收。独立诊断和复评分通过不等同于 v6 全量验收通过。
