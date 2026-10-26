# M1 E PostgreSQL 三份 v2 诊断报告核对

核对日期：2026-10-12。三份下载文件均为 `complete`，使用 `short_video_ops_postgres`、PostgreSQL 方言、`askdata_ops` schema，数据版本 `882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1`，catalog 版本 `94a801805965a90aa6ae015f28af196f88f72c1d887319dd1896a2973eaaa288`，物理结构版本 `b12bffb567ee4aa3ca126d48154ddfb36c1721d1af7c6e8b65efc4780615a817`。实时来源校验均记录 41 表、276 字段、722732 行，41 表的完整类型化行校验及只读权限校验通过。

| 文件 | 运行 ID | SHA-256 | 核对结果 |
| --- | --- | --- | --- |
| `results/m1_e_round3_diagnostic_server_v2.json` | `bb7ab9b1428845abba453e0e7f222fd0` | `2a7300af19564eb4927dfdb7052f45ab08c4d0473308de88d01e136784736b0f` | 3/3 实际执行、宽松结果、严格结果通过 |
| `results/m1_e_growth051_diagnostic_server_v2.json` | `73da654adf5e4d8082b1e928e0b0b724` | `0168bac5ecb59c3290b03f0a91bae0e26df85d213c66b284f0c987bd1863d235` | 0/1 执行成功，SQLSTATE 42883 |
| `results/m1_e_postgres_alias_rescore_server_v2.json` | `b513bba262794105a9af381682b19679` | `ed5f79c1890128e279aa1a4d5d6dca87657fc60c7b6ef23daa6b02b28bec8ab0` | 14/14 PostgreSQL 独立别名复评分通过，23 项显式映射 |

## 三条执行失败题

`GROWTH_OPS-150`、`GROWTH_OPS-148`、`CHANNEL_OPS-136` 的新 SQL 均对两参数 `ROUND` 的整个第一参数做了 `numeric` 转换。三题各执行一次，结果与各自重新执行的 PostgreSQL Gold 一致，严格评分均通过；无模型重试、超时和连接错误。报告中的 `column_name_match_rate=0` 是**原始列名逐字匹配率**，不等于严格评分；逐题显式别名参与后的严格评分为 3/3。首轮 `SQLSTATE 42883` 故障在这三条新执行中未再出现。

## GROWTH_OPS-051

首轮报告缺失候选 SQL。本次保存了最终生成 SQL，因此能定位本次失败：SQL 中 `ua.is_activated = true`，而经验证的 PostgreSQL 物理字段 `user_activations.is_activated` 为 `bigint`。该题连续三次调用查询工具，三次均失败；最终返回 `PostgreSQL query_error (SQLSTATE 42883)`，实际结果和严格结果均失败。`error_count=0` 表示没有 benchmark 级异常，不能解释为查询成功。本次诊断是**数据库执行失败**，不是旧报告那种调用前指标校验拦截；由于两次模型生成可能不同，不能把新 SQL 当作旧轮被拒 SQL 的原文。

已在本地加入受控修正：仅在完整 catalog 确认该列为 `bigint` 且 SQL 写了 `= TRUE/FALSE` 时，改成 `<> 0` 或 `= 0`，再次通过 SQL、指标和约束校验后执行；保留修正前后 SQL。`<> 0` 对应既有 PostgreSQL Gold 的非零真值口径。新报告的原 SQL经该修正后，在本地 CSV 快照的 DuckDB 诊断执行中与冻结标准结果严格一致；这不代替服务器 PostgreSQL 实际验收。

## 14 题、23 项列别名

独立复评分脚本使用首轮报告保存的 14 条生成 SQL 和经验证的 PostgreSQL 目标，重新执行每题 PostgreSQL Gold。报告中的原严格评分为 0/14，候选别名后为 14/14，宽松结果 14/14，新增模型请求 0。审查重新计算了每题实际行、Gold 行、列别名后的严格结果，并核对首轮报告 SHA-256、原题集 SHA-256、来源身份、运行 manifest、逐题 SQL 与 Gold 变体。14 题、23 项均复现，未使用通配别名。

少数生成 SQL 的输出列名本身是乱码，但对应的投影表达式分别指向已确认的状态、计数、预算或比率字段；映射只对当前冻结题目和来源版本有效。`GROWTH_OPS-126` 等涉及 LEFT JOIN 与聚合的 SQL，其当前结果行与 Gold 一致；这个结论不证明未来数据分布下所有不同 SQL 都语义等价。

本地已根据该独立报告执行受证据约束的别名应用：仅 14 条正式题目发生变化，加入 23 项显式别名；旧题集按字节冻结于 `results/m1_e_all_cases_before_aliases_20261012.jsonl`，原 SHA-256 `e1cb760a8ffa4f89e45ca73403c439975c51d2be47cd36800ee4c7c0ee1925f1`；更新后正式题集 SHA-256 为 `2c72c23c00685ea2dca5247e50a9395ba8e3d885f64710059f86004d1f705c15`。应用记录见 `results/m1_e_postgres_alias_apply_local_20261012.json`。服务器正式题集仍需运行相同的应用脚本。

## 后续服务器步骤

1. 同步本次 `bigint` 比较修正代码及测试，保持服务器正式题集为旧 SHA-256，先运行 `scripts.apply_m1_e_postgres_aliases`，确认更新后 SHA-256 与本地一致。
2. 用新文件名单独重跑 `GROWTH_OPS-051`，确认**实际 PostgreSQL 执行成功**并取得严格结果；若失败，保存新 SQL 和错误继续修正。
3. 051 单题通过后，再以新文件名运行 classic 49、扩展 30 与服务入口 E2E 8 条，并核对严格评分覆盖、来源身份、日期 WARN 与服务回复。当前 M1 E 尚未完成最终验收。

本地全量回归在正式题集应用后通过 490 项；其中新增的 051 类型修正测试和本地数据值比较均通过。服务器上新代码及正式三组验收尚未执行。
