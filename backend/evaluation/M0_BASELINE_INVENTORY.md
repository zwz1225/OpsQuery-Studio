# M0 基线材料清单（更新于 2026-10-06）

本轮核心交付的验收范围、报告分数与留存问题见 [M0 验收记录](M0_ACCEPTANCE.md)。原方案预算明确后当前版本 430 条全量 live 仍待补；Gold 全量、离线重评分和服务入口行为各自独立归档。

## 当前基线和证据

| 材料 | 题数 | 用途与状态 |
| --- | ---: | --- |
| `results/m0_gold_server.json` | 430 | 服务器 Gold 基线；运行 ID `167eccf453974eafaaca285e0409ddc4`；执行成功、宽松结果和严格结果均为 430/430。原始文件保留。 |
| `results/m0_live_classic_server.json` | 49 | 服务器 classic live 基线；运行 ID `e9386862501a48f896e22e568e98cce7`；SQL 执行和宽松结果均为 49/49，原始严格结果为 7/49。原始文件保留。 |
| `results/m0_live_classic_column_audit.json` 和 `.md` | 42 | 原始 live 报告中严格未通过题目的列映射审查。逐题核对问题、Gold 列与生成 SQL 后，42 条等价别名已获确认。 |
| `results/m0_live_classic_alias_rescore.json` | 49 | 本地离线复评：重放原报告保存的 SQL，在匹配数据上复现原严格 7/49，再按逐题别名得到严格 49/49。独立报告，不是新 live 运行。 |
| `results/m0_live_classic_alias_rescore_server.json` | 49 | 服务器独立生成的离线复评；已下载核对来源哈希、数据和评估器版本、42 条别名及逐题重放信息，与本地复评结果一致。 |
| `results/m0_gold_phase83_local_check.json` | 30 | 30 条扩展题的本地 Gold SQL 实跑校验；SQL 执行、宽松和严格结果均为 30/30，未评分 0。 |
| `results/m0_phase83_gold_server.json` | 30 | 服务器 Gold 校验，SQL 执行、宽松和严格结果均为 30/30。 |
| `results/m0_phase83_live_off_server.json`、`m0_phase83_live_on_server.json` | 各 30 | 同一固定扩展集的补充关闭／开启对照；两次宽松结果均为 28/30、严格均为 3/30，平均 Schema 召回为 96.72%／98.06%。 |
| `results/m0_phase83_live_off_alias_rescore.json`、`m0_phase83_live_on_alias_rescore.json` | 各 30 | 27 条扩展题的逐题别名校准后离线复评；严格结果为 28/30、27/30。原始服务器报告保留。 |
| `results/m0_phase83_live_off_tie_rescore.json`、`m0_phase83_live_on_tie_rescore.json` | 各 30 | `CONTENT_OPS-025` 的并列截断规则校准后离线 SQL 复评；关闭组宽松／严格 29/30，开启组宽松 29/30、严格 28/30。不是新的模型运行。 |
| `results/m0_phase83_column_candidates.json` | 30 | 原始开关两组 SQL 在匹配数据上的重放、实际列及候选映射审查。 |
| `results/m0_all_cases_before_phase83_aliases_20260929.jsonl` | 430 | 本轮添加扩展题别名前的 Case 源备份，原有 42 条 classic 别名保留。 |
| `results/m0_all_cases_before_topn_tie_20260929.jsonl` | 430 | 添加 `CONTENT_OPS-025` 专用并列截断规则前的 Case 源备份，已含 69 条逐题列别名。 |
| `results/m0_e2e_smoke_server.json` | 3 | 服务入口自然问题小样本，行为、宽松及严格结果均为 3/3。 |
| `results/m0_phase83_server_audit.md` | — | 四份服务器报告的版本、逐题变化、失败原因、别名及 Top N 并列截断校准、覆盖边界审查。 |
| `cases/all_cases.jsonl` | 430 | 当前 Case 源，含 49 条 classic；已有 42 条 classic 和 27 条扩展题的逐题显式 `column_aliases`，以及 `CONTENT_OPS-025` 的专用 Top N 并列截断规则。 |
| `results/m0_all_cases_before_aliases_20260929.jsonl` | 430 | 添加别名前的 Case 源备份，便于复核原始运行所用定义。 |
| `cases/phase83_validation.json` | 30 | 固定非经典扩展题清单；本地与服务器 Gold、服务器开关对照及离线别名复评均已完成。 |
| `cases/e2e_smoke.json` | 3 | 服务入口的初始数据问答样例；服务器冒烟通过，但尚不能代表整体端到端质量。 |
| `cases/e2e_behavior.json` | 8 | 服务入口行为扩展集，覆盖直接回答、数据问答、跨用户任务拒绝、澄清与恢复、合法空结果和受控故障。 |
| `results/m0_e2e_behavior_server.json` | 8 | 服务器首次行为运行；完整状态，行为通过 5/8，仅 1 条结果可评分且通过。原始文件保留。 |
| `results/m0_e2e_behavior_server_audit.md` | — | 首次行为运行的逐题审查；记录澄清连锁失败、空结果状态、日期范围错误及本地修正。 |
| `results/m0_e2e_behavior_after_fixes_server.json` | 8 | 首轮修正后的独立服务器运行；运行 ID `d3c2ae87e8254d5f8ab9f90f06c26e45`；下载审查时清单与本地版本一致，行为 7/8，宽松与严格结果 2/2。澄清恢复仍重复提问，空结果 SQL 日期正确但约束规划仍为 WARN。第二轮代码修正后作为历史基线保留。 |
| `results/m0_e2e_behavior_after_fixes_server_audit.md` | — | 2026-10-06 审查；核对清单、汇总、澄清恢复语义缺失及日期约束的实际生效边界。 |
| `results/m0_e2e_behavior_semantics_server.json` | 8 | 已完成并审查的第二轮修正服务器运行；ID `2191b25340874ebea55e18db57adcaf2`；行为 8/8，现场 Gold 宽松及严格结果 2/2。澄清语义及单日约束已生效，3 条完成查询均在本地重放一致。恢复题和空结果题各有一次错误表名前缀的执行修正，恢复题月份规划仍为 WARN。作为本轮服务入口行为基线保留。 |
| `results/m0_e2e_behavior_semantics_server_audit.md` | — | 第二轮修正报告的清单、逐题结果、澄清语义、单日约束和本地反例验证；记录 Schema 前缀校验、月份口径及回复内容的后续改进项。 |
| `E2E_BEHAVIOR_RUNBOOK.md` | — | 行为扩展集的逐题预期、评分口径、运行命令与报告审查方法。 |

服务器 Gold 与 classic live 报告的运行清单中，数据、Schema、应用、评估器和评估代码版本相互一致。两份报告对应添加别名前的 classic 数据集版本 `82187bbb03cbbff2d34ae7b10ce7ab62cf83b48c29a20d5f30f15b8952faf70e`。逐题别名添加后，当前 classic 数据集版本为 `1969cf734968afeea2f70d9e4133fed2067c0e24b3723209c357069d215c4fe5`。因此原始报告是历史基线，不能直接当作新 Case 版本的评分。

## 本轮列别名审查的边界

42 条原始严格未通过的 Case 均保持 Gold SQL、问题、预期列与行、排序标注不变；每条只允许审查确认的实际列名映射到该题的预期列名。未添加通配规则，未修改评分器。其余 388 条 Case 没有新增别名。

`m0_live_classic_server.json` 中的严格 7/49 是原始评分。本地和服务器离线复评均已单独保存，严格评分变为 49/49；`column_name_match_rate` 仍是原始列名完全一致的 7/49。两份复评的 49 题列映射、逐题判定和汇总一致。离线复评没有调用模型，不代表一次新的 live 运行；两份服务器原始 JSON 保留不变。

## 其他历史材料

| 材料 | 题数 | 限制 |
| --- | ---: | --- |
| `results/benchmark_live_smoke_curated.json` | 49 | 旧组件结果，缺少完整运行清单，只供历史参考。 |
| `results/benchmark_live_all_curated.json` | 430 | 旧组件结果，缺少完整运行清单；旧宽松结果准确率 0.825581，只供历史参考。 |
| `results/m0_gold_smoke.json` | 1 | 单题 Gold 冒烟验证。 |
| `results/m0_gold_all_20260928.json` | 430 | 本地离线 Gold 校验；最终报告使用匹配数据版本的缓存，其执行耗时不能代表 SQL 性能。 |

此前 Case 排序审查已给 180 条明确要求升序或按指标高低展示的 Case 标注主排序列。并列主指标允许组内互换。`CONTENT_OPS-025` 已逐题核实 Top N 截断线的 12 条并列候选，并单独标注允许的成员；其余题仍按 Gold SQL 固定成员集合评分。详细依据与新旧分数见 `results/m0_phase83_server_audit.md`。

## 比较规则

- 比较前核对 Case 内容与顺序、数据与 Schema、评估器、运行模式、角色和基准日期；应用或模型变化应在结论中注明。
- `result_accuracy` 为宽松比较，`strict_result_accuracy` 使用列名及逐题明确别名；两者都应列出可评分题数。
- Gold 或评分出错不能当作 SQL 结果错误。旧报告可用 `--allow-incompatible` 观察差异，但版本不一致时不能据此作正式回归结论。
- 服务入口、路由、权限拒绝、澄清、恢复、合法空结果以及模型或工具失败，需要后续有人工确认的预期行为和运行结果。
