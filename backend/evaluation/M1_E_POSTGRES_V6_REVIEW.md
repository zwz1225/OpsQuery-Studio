# M1 E PostgreSQL v6 三组验收核对

核对日期：2026-10-14。保留三份 v6 原始 JSON，不用修改原始报告或通配规则放宽评分。

## 报告与来源

| 报告 | SHA-256 | 运行 ID | 运行状态 |
| --- | --- | --- | --- |
| `results/m1_e_postgres_live_classic_server_v6.json` | `7a8c204f2ea28b87917ff3bb93835fe3c72287aef01b20bbc32a49b838939f9e` | `983ed2ffb4d044549db1f077b3d9519c` | complete |
| `results/m1_e_postgres_live_phase83_server_v6.json` | `f94431d045665ea56422ce820ee29cd8b53cab3666f95739e5d988ee63145373` | `23dfc6ec3fd041738643225afc18402a` | complete |
| `results/m1_e_postgres_e2e_behavior_server_v6.json` | `dfff792efb9d2569dda22e2983c7bfa3d63dbb2634abecf3a15e1194085224d7` | `7e32fcbfe51549f1aca2d298d214f350` | complete |

三个报告均通过 `validate_report_identity`；报告选题版本与本地正式题集重新计算的版本一致。正式题集 SHA-256 为 `08cf84a50f43eb2d176d96246e1210c398a13a89beec69a9d0db1b7361b7815a`。三个来源身份均为 `short_video_ops_postgres` / PostgreSQL / `askdata_ops`，数据版本 `882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1`，catalog 版本 `94a801805965a90aa6ae015f28af196f88f72c1d887319dd1896a2973eaaa288`，物理结构版本 `b12bffb567ee4aa3ca126d48154ddfb36c1721d1af7c6e8b65efc4780615a817`。现场核验为 41 张表、276 个字段、722732 行，41/41 完整类型化行摘要和只读权限通过。三份报告的应用、评测器和评测代码版本一致。

## Live 79 题

| 集合 | SQL 执行 | 宽松结果 | 严格结果 | Gold 来源 | 约束校验 |
| --- | ---: | ---: | ---: | --- | --- |
| classic 49 | 49/49 | 49/49 | **47/49** | 49 题均为 PostgreSQL execution | 49 PASS，0 WARN |
| phase83 30 | 30/30 | 30/30 | **30/30** | 30 题均为 PostgreSQL execution | 30 PASS，0 WARN |
| 合计 | **79/79** | **79/79** | **77/79** | 79 题均为 `gold_sql_by_dialect.postgres` | 79 PASS，0 WARN |

两组选题合计 79 个不重复 case ID，均有结果评分；0 次模型重试、超时或连接错误。v5 失败的 `CHANNEL_OPS-136` 本次首次 SQL 工具调用成功，宽松与严格结果均正确；`CONTENT_OPS-001` 本次中文输出列与已审查别名一致，31 行严格正确。`CHANNEL_OPS-025` 使用 `stat_date < '2026-06-01'` 表示“截至 2026-05”完整上界，约束为 `month_on_or_before`，PASS；`GROWTH_OPS-051` 也执行并严格通过。Schema precision 仍为 classic `0.166049`、扩展 `0.229766`，与此前检索质量问题一致。

classic 两处新严格差异均已执行并通过宽松结果比较，原始严格判定须保留：

1. `CHANNEL_OPS-066`：1 行实际与 Gold；生成 SQL 输出 `转化类型 = cce.conversion_type`、`转化数 = COUNT(*)`、`平均价值 = ROUND(AVG(cce.conversion_value::numeric), 2)`。Gold 期望列为 `conversion_type`、`conversions`、`avg_value`。正式题集已有 `conversion_count` 与 `avg_conversion_value` 英文别名，尚无这三个中文别名。首个严格错误为 `conversion_type` 缺失或映射不唯一。三项逐题候选：`conversion_type → 转化类型`、`conversions → 转化数`、`avg_value → 平均价值`。
2. `CONTENT_OPS-138`：12 行实际与 Gold；生成 SQL 输出 `content_category = cc.category_name`、`report_count = COUNT(cr.report_id)`。Gold 期望 `category_name`、`reports`。正式题集已有 `reports → report_count`，缺少 `category_name → content_category`，故严格错误为 `category_name` 缺失或映射不唯一。这里只需一项逐题候选别名。

v5 中这两题曾使用不同输出列名且严格通过。v6 的新差异来自模型输出列名变化，不涉及这两题的 SQL 执行失败或结果值错误。四项候选尚未写入正式题集，也不能未经 PostgreSQL 独立复评分即视为通过。

## 服务入口 E2E 8 条

汇总由逐题结果重新计算一致。8/8 行为通过；实际 SQL 成功执行 3 条，Gold 结果评分 2/2 且严格 2/2，其余 6 条按用例设计不做结果评分。直答、数据问答、跨用户拒绝、澄清开始、澄清继续、空结果和受控失败均符合对应行为检查。澄清继续保留 `option_1`“转化事件数”的语义，SQL 使用 `channel_conversion_events.converted_at >= '2026-05-01'` 且 `< '2026-06-01'`，返回 4 行；空结果查询 `1900-01-01` 左闭右开日范围，返回 0 行并明确回复无匹配记录。三次 SQL 工具调用的 SQL 与约束校验均为 PASS、warnings 为空。`sql_case_count=5` 是数据库查询路由计数，并非实际执行次数。

## 验收结论与下一步

**M1 E v6 尚未通过最终严格评分全通过目标**：79/79 执行和宽松结果、8/8 E2E 行为均已通过，但原始 live 严格结果为 77/79。下一步固定 v6 两份原始 live 报告和正式题集的 SHA-256，对上述两题四项显式别名进行 PostgreSQL 保存 SQL 与 Gold 独立重放；逐题确认实际/Gold 行、原严格失败及候选严格通过。审查独立报告后才更新正式题集，保留更新前副本。随后生成独立离线复评分记录；若以新 live 作为最终验收门槛，则再用新文件名运行 classic、phase83 和 E2E，核对新一轮来源与逐题结果。由于模型可能再次改变列名，独立复评分和新 live 报告必须分开标注。

## v6 两题独立重放与本地题集更新（2026-10-14）

服务器独立重放报告 `results/m1_e_v6_strict2_rescore_server.json` 的 SHA-256 为 `5423ba14dacea7b37be35df90f917d76de172ee3a6a4bb7b2cc898d762c258ad`；本地下载文件哈希一致，`validate_report_identity` 通过。来源为同一个 PostgreSQL、`askdata_ops`、数据版本、catalog 版本及物理结构版本，正式题集输入 SHA-256 为 `08cf84a50f43eb2d176d96246e1210c398a13a89beec69a9d0db1b7361b7815a`。报告记录 `formal_cases_modified=false`、`new_model_request_count=0`。

逐题重算保存的实际行、重新执行的 PostgreSQL Gold 行与原有评分规则：`CHANNEL_OPS-066` 为 1/1 行、`CONTENT_OPS-138` 为 12/12 行；两题宽松结果正确，原严格评分均失败，新增四项逐题显式别名后均严格通过。报告中的生成 SQL 哈希、SQL 投影表达式、Gold SQL、运行 ID、列名和行数均与 v6 原始报告对应。没有增加辅助列许可。下载报告在临时题集副本上的更新试运行也通过：只改两条记录，更新前备份与原文件逐字节相同，目标题集 SHA-256 为 `82761737b873c9d4e9daac852bb3bf30867adc01919d088289dc9ba03972ed33`。

本地已通过受控脚本更新正式题集并保留 `results/m1_e_all_cases_before_v6_strict2_20261014.jsonl`；本地应用记录为 `results/m1_e_v6_strict2_apply_local.json`。更新后全量单元回归为 509/509。服务器应用记录见下节，随后需用新文件名完成最终验收。**原始 v6 live 报告的严格成绩仍为 77/79；独立重放证明的是已保存 SQL 在候选评分规则下的 2/2。**

## 服务器应用记录核对（2026-10-14）

已下载 `results/m1_e_v6_strict2_apply_server.json`，文件 SHA-256 为 `c1b0f8b7466189da50ace967ed1598e53d55445ace69655364f1c3698d1ce782`。报告 `run_status=complete`、变更题目恰为 `CHANNEL_OPS-066` 和 `CONTENT_OPS-138`、新增别名数为 4、模型请求数为 0。更新前题集、更新后题集、v6 来源报告及独立重放报告的四项 SHA-256 全部与本地记录和固定证据一致；服务器与本地应用记录除时间戳外逐字段相同。报告记录的服务器正式题集目标哈希为 `82761737b873c9d4e9daac852bb3bf30867adc01919d088289dc9ba03972ed33`。

随后收到服务器独立检查输出：正式题集 SHA-256 为 `82761737b873c9d4e9daac852bb3bf30867adc01919d088289dc9ba03972ed33`，更新前备份为 `08cf84a50f43eb2d176d96246e1210c398a13a89beec69a9d0db1b7361b7815a`；`python -m unittest discover -s tests -q` 运行 509 项，结果 `OK`。服务器题集更新与回归门槛已满足，可以运行新文件名的最终三组验收。
