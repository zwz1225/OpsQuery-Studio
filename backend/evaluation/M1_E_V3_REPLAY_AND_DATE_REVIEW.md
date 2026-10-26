# M1 E v3 四题复评分与 CHANNEL_OPS-025 日期修复核对

核对日期：2026-10-13。两份服务器报告均为 `complete`，运行身份校验通过。

## 证据与来源

| 报告 | SHA-256 | 运行 ID |
| --- | --- | --- |
| `results/m1_e_v3_strict4_rescore_server_v2.json` | `0210c51ac0c07da62c854a9ff1c024cf3d629cf16aba480625047e0def049297` | `7d8185ab4cda47e39f972e55f0c9c93a` |
| `results/m1_e_channel025_diagnostic_server_v4.json` | `7eeffbceb86e213b4f20183f320349884a2922545a472b4c1f1d6f1d38abdf4b` | `c5128d8784ec4164ab1d3e39a894dcbe` |

两份报告的 `source_id=short_video_ops_postgres`、PostgreSQL 方言、`askdata_ops` 物理 schema、数据版本 `882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1`、catalog 版本 `94a801805965a90aa6ae015f28af196f88f72c1d887319dd1896a2973eaaa288`、物理 schema 版本 `b12bffb567ee4aa3ca126d48154ddfb36c1721d1af7c6e8b65efc4780615a817` 均一致。两次均记录了 41/41 表的完整类型化行校验和只读权限校验。复评分引用的 v3 classic、phase83 报告 SHA-256 与本地原始报告逐字节相符。

## 四题实际结果

| 题目 | 当前结果与 Gold | 审查后的逐题规则 | 原严格 → 新严格 |
| --- | --- | --- | --- |
| `CHANNEL_OPS-004` | 30 对 30 行，首行日期及广告消耗一致 | `统计日期 → stat_date`；`广告消耗 → spend` | 失败 → 通过 |
| `CHANNEL_OPS-005` | 31 对 31 行，首行日期及广告消耗在现有数值容差内一致 | 同上 | 失败 → 通过 |
| `GROWTH_OPS-100` | 1 对 1 行，iOS 人均播放量 124.14 一致 | `avg_plays_per_user → plays_per_user`；仅允许 `total_play_count`、`distinct_user_count` 两个辅助列 | 失败 → 通过 |
| `CHANNEL_OPS-102` | 2 对 2 行，创意状态及数量一致 | `创意状态 → creative_status`；`创意数量 → creatives` | 失败 → 通过 |

四题保存的 SQL 哈希均吻合；重新对报告中的实际行与 Gold 行执行严格评分，结果为原规则 0/4、候选规则 4/4，宽松评分 4/4。独立脚本记录 `new_model_request_count=0`，并重新执行 PostgreSQL SQL 与 Gold，且确认 Gold 与冻结期望一致。评分规则是逐题显式别名，共新增 7 项别名及 2 个确切辅助列，没有添加通配规则。

## CHANNEL_OPS-025

问题中的“截至2026-05各月”被规划为 `month_on_or_before`，字段是 `ad_daily_stats.stat_date`。生成 SQL 的 `s.stat_date < '2026-06-01'` 包含 2026-05 及此前月份，与 Gold 的 `TO_CHAR(stat_date, 'YYYY-MM') <= '2026-05'` 上界一致；没有加入排除更早月份的下界。约束校验 `PASS`，`missing_constraints=[]`、`unsupported_constraints=[]`、`warnings=[]`；工具调用一次成功，SQL 执行成功，生成与 Gold 均为 5 行，结果评分及严格评分均通过。报告内未发现 `WARN` 或 `BLOCK`。原始列名匹配率为 0，但逐题既有列映射使严格评分通过。

## 本地应用与待完成验收

依据已核实的独立复评分报告，本地正式题集只改动上述四题的显式评分规则。更新前题集保存为 `results/m1_e_all_cases_before_v3_strict4_20261013.jsonl`，SHA-256 为 `2c72c23c00685ea2dca5247e50a9395ba8e3d885f64710059f86004d1f705c15`；更新后 `cases/all_cases.jsonl` SHA-256 为 `22a7ee6f9d8d2309e79ceb5d831468b30f609c485a0a31ba5d1a0cbde3d9ba6b`。本地应用记录是 `results/m1_e_v3_strict4_apply_local.json`。完整本地回归 497 项通过。

服务器仍需使用 `m1_e_v3_strict4_rescore_server_v2.json` 运行受保护的应用脚本，并确认更新后题集 SHA-256 与本地一致；随后以新文件名重跑 PostgreSQL classic 49、phase83 30 和服务入口 E2E 8 条，核对最终报告后再判断 M1 E 整体验收。
