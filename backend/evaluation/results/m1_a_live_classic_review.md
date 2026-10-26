# M1 A：classic live 完整报告审查

审查日期：2026-10-07。原始服务器报告：`m1_a_live_classic_server.json`。

## 1. 原始运行与版本核验

- 状态 complete，classic 49 题齐全、无重复；逐题记录重新汇总后与原始 summary 一致。
- 运行 ID：`cce91d72155a44b4b7dfaf7c1c6248e8`。
- 原始文件 SHA256：`219d182d48314ee41eccedc6915db8dd1c8ac57565407b859226f1796785f2a2`。
- 源身份：short_video_ops / short_video_ops_duckdb / DuckDB / main。
- 源身份、classic 数据集以及数据、Schema、应用、评分器、evaluation 代码摘要与本地核对一致。
- 时间字段补充关闭、workers=1、qwen3.7-plus、temperature=0。

| 指标 | 原始服务器报告 |
| --- | --- |
| SQL 最终执行成功 | 49/49 |
| 宽松结果正确 | 49/49 |
| 严格结果正确 | 41/49（83.6735%） |
| 原始列名直接匹配 | 6/49（12.2449%） |
| Schema recall / precision | 0.929932 / 0.166049 |
| 最终错误、超时、连接错误 | 均为 0 |
| 模型请求 / 模型重试 | 183 / 0 |
| SQL 平均执行 / P95 | 1700.720 ms / 1836.925 ms |

执行耗时统计为 SQL 执行，不是完整服务请求耗时。

## 2. 8 题列映射复核

下面是新增候选别名，方向为 Gold 标准列 → 本次实际返回列。原有逐题别名保留。

| 用例 | 新增显式映射 | 实际/Gold 行数 | 候选严格核对 |
| --- | --- | --- | --- |
| CHANNEL_OPS-069 | `avg_value → avg_conversion_value` | 1 | 通过 |
| CHANNEL_OPS-101 | `creatives → creative_count` | 2 | 通过 |
| CONTENT_OPS-029 | `category_name → content_category` | 1 | 通过 |
| CONTENT_OPS-035 | `category_name → 内容分类`；`interactions → 互动数` | 12 | 通过 |
| CONTENT_OPS-036 | `interaction_date → interacted_date` | 17 | 通过 |
| CONTENT_OPS-051 | `category_name → content_category`；`contents → content_count`；`avg_duration_seconds → avg_video_duration` | 1 | 通过 |
| CONTENT_OPS-136 | `category_name → 内容分类`；`reports → 举报数量` | 12 | 通过 |
| CONTENT_OPS-137 | `category_name → 内容分类`；`reports → 举报数量` | 12 | 通过 |

共 8 题、13 项映射。独立结果包含每题 SQL、Gold SQL、真实返回列和行、Gold 列和行、原别名、候选别名。

### 数值、计数与排序证据

- CONTENT_OPS-029：平均观看时长 60.46368843069874 对应 Gold 60.46，平均完成率 0.6463797250859094 对应 0.6464；按现有两位/四位小数精度规则均通过。
- CONTENT_OPS-051：平均时长 96.7610953729934 对应 Gold 96.76，按现有精度规则通过。
- CHANNEL_OPS-069：两份结果均为 activation、4104 次、平均值 1。
- CONTENT_OPS-036：interaction_id 非空行数 6443，与全表 6443 行一致；valid_interaction 没有空值或 0/1 之外的值，interacted_at 类型 TIMESTAMP。当前固定数据下 COUNT(*) 与 COUNT(interaction_id) 等价，半开月份区间与 Gold 一月份筛选等价；17 行日期升序按现有顺序敏感规则通过。未来数据允许计数字段为空时需重新审查该等价关系。
- 其余映射已逐题检查过滤条件、连接键、分组与统计表达式，并通过原严格评分器对实际列、全部结果行的核对。

## 3. 独立离线核对结果与边界

- 离线执行保存的 49 条最终 SQL，运行上下文数据与代码版本均匹配。
- Gold 来自 49 份通过源身份、数据、SQL、问题及权限校验的本地缓存。
- 原始严格结果成功复现 41/49；加入候选显式映射后 49/49；宽松 49/49。
- 新模型请求 0；评分器、精度、排序、权限和模型均未修改。
- 原始 JSON、正式 `all_cases.jsonl` 未修改。候选别名尚未写入正式题集。
- 原始服务器报告不含完整结果行，因此本次是同版本本地 SQL 重放证据，不能冒充新的服务器 live 运行，也不能声称逐值对照了原始服务器结果行。
- 原始列名直接匹配率仍按原报告记录 6/49；接受显式别名不等于列名直接相同。

文件：`m1_a_classic_alias_review_local.json`；脚本：`python -m scripts.audit_m1_a_classic`（backend 目录）。

## 4. 需保留的运行问题

- 72 次工具调用中有 23 次失败，23 题第二次修正后成功；最终 error_count=0 不代表没有中间失败。修正说明均指向移除 schema 前缀，但报告没有保存失败 SQL 和具体工具错误，无法独立验证全部失败根因。
- M0 原始 classic 报告有 77 次工具调用、28 次失败后修正成功；此现象在 M0 已存在。应用、数据集校准条件不同，这里仅作历史观察，不能作为正式归因或性能回归结论。
- 7 题保留月份字段定位 WARN：CHANNEL_OPS-001～005、CONTENT_OPS-001、CONTENT_OPS-036。它们最终 SQL/结果通过，时间约束校验覆盖仍有缺口。
- Schema precision 约 16.60%，recall 约 92.99%，均与 M0 汇总一致；检索噪声和漏召回仍存在。

## 5. 后续验收

本次支持“classic 49 题未发现最终 SQL 结果回归；8 题严格评分差异可由逐题显式别名解释”的结论。M1 A 整体验收还需要检查本次 M1 的 8 条 E2E 独立报告，并将已通过的服务器 Gold 79 题结果一起归档。

建议下一步将审查通过的 13 项映射写入 8 题正式定义，备份原题集、记录新数据集版本，保存独立复评分结果；原始服务器报告继续作为校准前记录。
