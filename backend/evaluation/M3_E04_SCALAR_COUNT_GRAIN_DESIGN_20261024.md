# M3 E04：公开标量计数输出粒度的窄范围候选设计

日期：2026-10-24。状态：**扩充边界测试、无模型复查、独立 E04 候选包及服务器同轮实验均已完成；候选未通过效果筛选。**依据为已归档的 E02 development80 同轮报告、公开题目/evidence 和授权 SQL 结构；规则不使用 Gold 或原生得分选择触发题。服务器结果见 [E04 验收记录](M3_E04_PAIR24_ACCEPTANCE_REVIEW_20261024.md)，边界失败见 [0072/0239 离线语义审查](M3_E04_0072_0239_OFFLINE_SEMANTIC_REVIEW_20261024.md)。

## 1. 问题边界

E02 的 `BIRD-PG-0092` 公开问题要求“no. of districts”，意图是一个区县总数。基线 SQL 返回一个 `COUNT(DISTINCT district_id)`；候选首次 SQL 使用相同授权字段和关联，却在外层加入 `GROUP BY district_id, a11`，返回 69 行的分组计数。该 SQL 语法正确、只读、能执行；现有校验没有检查它与问题要求的**输出粒度**是否一致。原生复评记录为基线单行 `69` 匹配，候选 69 行值为 `1` 不匹配。

两侧 0092 的授权字段均为 `financial.district.a11`、`financial.client.gender`、`financial.client.district_id`，图中同有 `financial.district.district_id` 及声明外键；候选关系补齐没有新增字段或边。候选诊断只是多记录了已有字段的公开条件需求。**不能仅凭本轮证据证明额外诊断提示直接造成分组写法。**新设计只处理已观察到的输出形态缺口。

## 2. 拟议公共契约

只在公开问题可明确解释为**单个计数值**时启用。候选词形包括独立的 `how many ...`，或以 `list / list out / show / return / give / what is` 起始并紧接 `the number of / no. of / count of` 的问题。触发前必须排除：

- `how many more` 等差值问题；`average/highest/biggest number of` 等将“数量”作为平均或排序依据的问题；
- `per / for each / grouped by / breakdown by` 等明确分组输出；
- 一个问题中出现多个计数请求、第二问、明确要求名称/明细与计数并列输出，或其他不确定的输出形态。

契约只表达“最终输出应为单个标量计数”。校验只检查**最外层**查询的输出粒度：在明确的单值契约下，外层 `GROUP BY` 导致多组输出时给模型结构化反馈；允许内层 CTE/子查询先分组筛选、外层再计数。聚合函数可以是 `COUNT`、适当的 `SUM` 等，只要符合公开问题，不固定统计口径或实体去重方式。对复杂窗口、集合运算或不确定语义保留提示，不设硬拒绝。

反馈要说明“问题请求一个总数，当前最外层按字段分组可能返回多行；可先筛选合格区县，再在外层求总数”。不得提供 Gold SQL、目标数字 `69`、case ID、评分差异或强制改写后的 SQL。反馈消耗既有模型生成/校验预算，不增加重试上限。

## 3. 正反例与离线初筛

用冻结 development80 **公开题目**作词形初筛，明确可纳入进一步测试的题有 `0072`、`0356`、`0537`、`1505`、`1509`、`0092`、`0239`。这只是候选清单，不是正确性标签。已保存候选 SQL 中，这七题只有 0092 使用最外层 `GROUP BY`；其余六题最终均为单列表达式、无最外层分组。0072 使用 `SUM` 计算学生数，说明规则不能硬编码 `COUNT(*)`。

必须有下列负例测试，确保不误拒：

| 公开问题形态 | 预期 |
| --- | --- |
| “How many districts **per region**?” | 明确多组，允许外层分组 |
| “List each district and its number of clients” | 明确区县明细和局部计数，允许外层分组 |
| “Which district has the highest number of clients?” | 数量用于排名，不触发单值总数契约 |
| “What is the average number of crimes ...?” | 平均值请求，不触发计数契约 |
| “How many more SMEs ...?” | 差值请求，沿用已有差值契约 |
| “Give the full name and contact number ...” | `contact number` 不是计数请求 |
| 同一问题内 `How many ...? List the number of ...` | 多个输出请求，保持提示态 |
| `WITH eligible AS (SELECT district_id ... GROUP BY district_id HAVING ...) SELECT COUNT(*) FROM eligible` | 最外层为单个计数，允许 |

词形不能成为唯一判据：进一步测试须覆盖大小写、标点、同义表述、显式只要一个数字和显式多列输出，并验证不同 case ID 下行为相同。错误 SQL 仅在公开单值请求且外层输出形态明确不符时被拦截；字段所有权、筛选值、连接路径及去重口径仍由现有授权/业务约束处理。

## 4. 已完成的本地原型核查

独立规则位于 `backend/evaluation/bird/scalar_count_shape.py`。工作项目的正式 Agent 尚未接入；仅新冻结的 E04 候选副本在 `intent.py` 中调用。`backend/tests/test_m3_e04_scalar_count_shape.py` 已扩为 8 组正反例测试，涵盖 0092 的分组错误、正确的外层标量查询、内层分组后外层计数、同义问法、公开 evidence 显式分组、多输出请求、排序/平均/差值/联系方式误判，以及 case ID 不影响契约。

对冻结 development80 公开题目和本轮两侧已保存 SQL 做无模型扫描：67 题不适用、6 题仅提示、7 题满足严格标量候选。7 题 ID 为 `0072`、`0356`、`0537`、`1505`、`1509`、`0092`、`0239`（均带 `BIRD-PG-` 前缀）。在基线 80 题捕获中，原型没有标记 SQL；在候选 80 题捕获中，只标记 `BIRD-PG-0092` 的 `scalar_count_outer_group`。这一结果只证明已保存 SQL 的结构覆盖，不证明模型收到反馈后会修复，也不替代新一轮同轮实验。

## 5. 下一轮实验门槛

独立原型已满足初步离线门槛。正式候选接入前仍需扩充同义问法、嵌套查询和真实开发题正反例；若发现合法分组或多输出题误拒，先收窄规则，不启动服务器实验。

离线门槛已通过。现已冻结独立候选代码身份、相同来源与预算，先做包含 0092、三道边界题及既有成功20题的受控开发集 24 题同轮对照。原生结果、回归、模型调用、Token 和时延继续独立报告；保持 holdout 不再运行。只有真实模型生成修正了 0092，且没有新的成功题回归时，才考虑更大范围推广。

## 6. E04 独立候选交付

无模型审查报告为 `backend/evaluation/results/m3_e04_scalar_count_offline_audit_20261024.json`：公开输入中 67 题不适用、6 题提示态、7 题可严格检查；冻结 E02 基线捕获没有命中，冻结 E02 候选捕获只命中 `BIRD-PG-0092` 的 `scalar_count_outer_group`。该报告不表示新模型已改善 0092。

新包 `M3_E04_pair24_scalar_count_v2_20261024.zip` 的 bundle ID 为 `c57344fe558c72d03eb27da90a84a528987f8e84803205b9bed3d2b7c971019b`。两侧均以同一个已冻结 E02 候选为起点；候选侧只改变 `intent.py` 并新增 `scalar_count_shape.py`，基线侧维持原状。候选契约进入模型的 Schema/意图上下文，并在已有 SQL 校验轮次产生结构化错误；既有模型调用、SQL 校验和执行上限不增加。固定题单为 `m3_e04_scalar_count24.json`，20 道成功回归题加 0092、0072、0356、0239。两侧各自建索引，捕获均完成后才做无模型原生复评。

服务器准备、预检、模型连接检查、正式运行及报告下载清单见 `M3_E04_PAIR24_SERVER_RUNBOOK_20261024.md`。服务器同轮结果为基线与候选均 22/24，0092 两侧均正确、无候选修复增益；候选未通过效果筛选。九份原始证据、来源核对和后续处置已在验收记录中固定。
