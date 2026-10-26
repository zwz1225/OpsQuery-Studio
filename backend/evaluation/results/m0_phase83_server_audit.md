# M0 30 题扩展集与 E2E 服务器报告审查（2026-09-29）

## 来源与版本

| 原始报告 | 状态 | 运行 ID | SHA256 |
| --- | --- | --- | --- |
| `m0_phase83_gold_server.json` | complete | `269fd27998bc4937845b06b54aefc0f9` | `00bf0ec8cd325e871999667858546c64a98af8ba356c045ee13406998d55fd15` |
| `m0_phase83_live_off_server.json` | complete | `c49cbc382ef648d3b3cc4094fa77e99c` | `bf372bd9ddbeddd6d0765170b7faf7e7fd00c3c0916f6f8b3c6fdf7aa891b2c0` |
| `m0_phase83_live_on_server.json` | complete | `d736e46bce3a4665902adfa557a8d06f` | `61dcfcc88162927e0ade862600dd048af84387e81e430b5d68b7db0eb61d4aa0` |
| `m0_e2e_smoke_server.json` | complete | `e77a01d281df485ca5058b61acb4791e` | `8345c8d7cc36c37dad9ec43073895ad2a27fbe8fd138faced57f4d6328a6c8e3` |

四份报告的运行清单均与本地当前 Case、数据和代码版本重新计算结果一致。Gold 与两份 live 的 30 个 Case ID、顺序和数据集版本 `d8b9832134cebdab2f270a03c78d4722b8e50f8b9cb18f44478fd43b410c5b59` 相同；数据、Schema、应用、评估器和评估代码版本一致。两份 live 配置仅 `time_field_supplement.enabled` 不同。E2E 是独立的 3 题数据集，不能与组件结果合并计分。

## 汇总

| 指标 | Gold | 补充关闭 | 补充开启 | E2E 小样本 |
| --- | ---: | ---: | ---: | ---: |
| 题数 | 30 | 30 | 30 | 3 |
| SQL 执行成功 | 30/30 | 30/30 | 30/30 | 3/3 |
| 宽松结果通过 | 30/30 | 28/30 | 28/30 | 3/3 |
| 严格结果通过 | 30/30 | 3/30 | 3/30 | 3/3 |
| 平均 Schema 召回 | 不适用 | 96.72% | 98.06% | 不适用 |
| 平均 Schema 精确率 | 不适用 | 22.98% | 23.09% | 不适用 |

所有运行均为完整状态，未评分数为 0。两次 live 的严格通过 Case 相同：`GROWTH_OPS-076`、`GROWTH_OPS-125`、`CHANNEL_OPS-051`。两次均有 25 题宽松通过但严格未通过，需逐题审查列语义；不能使用通配别名统一放宽。开启运行中的 `GROWTH_OPS-100` 返回 4 列，而 Gold 仅要求 2 列，即使核准列别名，也需单独判断多出的两列是否允许。

## 逐题变化与失败原因

- `GROWTH_OPS-148`：Schema 召回由 0.6 升为 1.0。开启运行补入 `user_registrations.registered_at` 和 `growth_targets.target_month` 两个 Gold 字段；两次 SQL 结果均通过。其余 29 题召回率不变。`GROWTH_OPS-051` 和 `GROWTH_OPS-125` 的缺失字段仍未补回。
- `GROWTH_OPS-100`：关闭运行用用户注册时间过滤 2026-05，得人均播放次数 481.5，未通过。开启运行补入 `user_daily_activity.activity_date`，生成 SQL 改用活动日期过滤，得 124.1399，与 Gold 124.14 匹配并通过。此题的 Gold 字段召回原本已是 1.0；新增时间字段改善了实际 SQL 的时间口径。本次只各运行一次，不能据此断言稳定提升。
- `CONTENT_OPS-052`：关闭运行未额外筛选状态，结果通过。开启运行在相同检索字段上多加 `content_status = 'published'`，内容数变为 1360，Gold 为 1383，结果未通过；这不是时间字段补充直接添加字段造成的差异。
- `CONTENT_OPS-025`：两次生成 SQL 均按播放量降序取 10 条，但未加 Gold 的内容标题次级排序。前 7 条播放量均为 9；截断位置有多条播放量为 8 的并列候选，两次结果与 Gold 的固定成员不同。因此现行宽松比较均判失败；需先确定 Top N 并列候选的业务评分规则，不能简单归为计算错误。

两次 live 有 18 题的生成 SQL 文本不同，其中不少题的检索字段完全相同。故结果转好与转差不能仅用开关汇总做因果归因，应结合逐题新增字段、SQL 与重复运行判断。两次宽松结果均为 28/30，没有净提升。

## 逐题列别名校准（原报告保留）

在两次原始 live 报告的 SQL 重放中，所有宽松通过、严格未通过的题均找到唯一的列值映射。结合问题与 SQL 投影，现已给 27 条非 classic Case 添加逐题 `column_aliases`，其中包含 `CONTENT_OPS-025` 已确认的 `plays → play_count`；该题的 Top N 并列结果差异仍保留。原始 30 题数据集版本为 `d8b9832134cebdab2f270a03c78d4722b8e50f8b9cb18f44478fd43b410c5b59`，别名标注后的版本为 `30c0650da8d830a2ff3dc0bba24a7fe05d274766da2f6aed7a78b0ddabb9c02c`。原 49 条 classic Case 的数据集版本未变。

完整逐题候选、实际列与两次 SQL 保存在 `m0_phase83_column_candidates.json`；添加别名前的 Case 源保存在 `m0_all_cases_before_phase83_aliases_20260929.jsonl`。未修改评分器，未添加通配别名或 `allowed_auxiliary_columns`，服务器原始 JSON 保持原样。

| 离线复评 | 原始严格通过 | 别名校准后严格通过 | 宽松通过 |
| --- | ---: | ---: | ---: |
| `m0_phase83_live_off_alias_rescore.json` | 3/30 | 28/30 | 28/30 |
| `m0_phase83_live_on_alias_rescore.json` | 3/30 | 27/30 | 28/30 |

关闭运行仍未严格通过的是 `GROWTH_OPS-100`（额外两列，且时间口径错误）和 `CONTENT_OPS-025`（Top N 截断成员不同）。开启运行还包括 `CONTENT_OPS-052`（多加 `published` 过滤导致结果值不同）。`GROWTH_OPS-100` 虽有确认等价的列名映射，但多余两列未获许可，因此开启运行依旧严格不通过。两份离线复评在匹配的数据上复现了原始逐题评分，再按新版 Case 别名重新评分；它们不是新的模型运行。

## E2E 范围

3 条服务入口 Case 分别属于增长、渠道和内容场景，均为 `database_query`、`completed`，行为与宽松/严格结果均为 3/3。它们从自然问题进入 `AskDataService.submit()`，没有组件评测传入的 Case `retrieval_terms`。这只覆盖数据问答冒烟；路由、权限拒绝、澄清与恢复、合法空结果和模型/工具失败仍需补充有明确预期的端到端 Case。

后续已新增独立的 8 条行为扩展集 `cases/e2e_behavior.json` 和运行说明 `E2E_BEHAVIOR_RUNBOOK.md`，覆盖上述服务入口行为，其中故障用例是受控工作流异常注入。它尚未取得服务器 live 结果，因此本节的 3/3 仍只代表原冒烟集。

## `CONTENT_OPS-025` 的 Top 10 并列截断校准

问题只要求按播放量从高到低返回最多 10 条，没有指定同播放量时按标题排序。对同一份数据执行不带 `LIMIT` 的 Gold 聚合 SQL，完整排行有 816 行：7 条播放量为 9，第 10 名的播放量为 8，共有 12 条播放量为 8 的真实候选。`scripts.audit_m0_topn_tie` 会重算并核对这些候选与当前 Case 标注。

仅此题增加 `top_n_tie_policy`：结果须恰好 10 行，前 7 条须是全部 9 次播放的内容，后 3 条可从 12 条已核实的 8 次播放候选中任取，不能重复；标题和播放量必须对应，且仍须按播放量降序。严格评分仍要求题目声明的两列及显式别名 `plays → play_count`，额外列仍不通过。其他题的固定成员比较规则不变。

添加规则前的 Case 源单独保存为 `m0_all_cases_before_topn_tie_20260929.jsonl`，SHA256 为 `36e65b72415c78199d6069559700a3abcc177dba860c92e49f9cafc6dfc31f5d`；添加后的源 SHA256 为 `0766d85d69794b8d8663e1f9d037f334c230da769ea55779bd00ae80a5559d36`。30 题数据集版本从别名校准后的 `30c0650da8d830a2ff3dc0bba24a7fe05d274766da2f6aed7a78b0ddabb9c02c` 变为 `de990ebc3e96da30b6dc9f687c6c308d531bb1ccd32c4ab7a05d06a977d14a77`。这属于评分定义变更，原始服务器结果和上一轮别名复评均保留。

`scripts.rescore_m0_topn_tie` 从两份别名复评报告读取已保存的 SQL，先重放并核对该题原有的宽松及严格失败，再应用新规则；未调用模型。新报告分别为 `m0_phase83_live_off_tie_rescore.json` 和 `m0_phase83_live_on_tie_rescore.json`：关闭组宽松／严格均为 29/30；开启组宽松 29/30、严格 28/30。`CONTENT_OPS-025` 在两组中均由失败变为通过。关闭组剩余 `GROWTH_OPS-100`；开启组剩余 `GROWTH_OPS-100` 严格多列问题和 `CONTENT_OPS-052` 值错误。当前服务入口的 3 条原始 E2E 结果未重新运行。
