# M1 A 最终功能验收结论

日期：2026-10-07。

## 1. 结论与范围

**M1 A「现有 DuckDB 接入统一运行上下文」验收及资料归档已完成，已知问题留存。classic 8 题的 13 项显式别名已写入正式题集并在服务器同步验证，独立离线复评分严格通过 49/49。服务器 79 题 Gold 原始报告已归档，源/代码/题集版本与逐题结果核查通过。两项收尾均已闭环，可进入 M1 B。**

本结论针对同一 DuckDB 数据版本上的装配、Service／Workflow／SchemaGraph／MCP 与评分执行路径。PostgreSQL adapter、隔离数据导入和跨后端方言验收属于后续 B／C／D。

## 2. 证据汇总

| 验证 | 结果 | 证据边界 |
| --- | --- | --- |
| 本地完整单元／集成回归 | 272 项通过、无跳过 | 本地日志和运行记录已留存 |
| 服务器回归 | 用户提供输出为 272 项通过 | 本地未归档服务器完整测试日志 |
| 本地 79 题 Gold | 79/79 执行、宽松、严格通过 | 原始 JSON 已留存 |
| 服务器 79 题 Gold | 79/79 执行、宽松、严格通过；0 未评分、0 模型请求 | 原始 JSON 已归档；全部用例、Gold SQL、行数、源/版本及汇总已核查 |
| 服务器 classic49 原始运行 | SQL、宽松 49/49；严格 41/49 | 原始报告保留，不改写 |
| classic 候选别名独立核对 | 原规则复现 41/49；候选 49/49 | 相同数据/代码，原评分器，0 次新模型请求；正式题集未改 |
| classic 正式题集别名校准收尾 | 原规则复现 41/49；正式校准后 49/49 | 本地与服务器均通过；49 题实际/Gold 完整行逐项相同；8 题、13 项追加别名和原文件备份可追溯 |
| 服务器 E2E8 | 行为 8/8；宽松/严格结果各 2/2 | 已逐题审核完整报告 |
| E2E 最终 SQL 离线复核 | 3 条执行成功，列与完整结果行均与服务器一致 | 普通查询、澄清恢复、空结果；2 条 Gold 评分再次通过 |

classic 原始严格结果不能写成 100%。候选别名结果属于独立离线审查，不是一次新 live 运行。E2E 的 6 条未评分行为用例按题集设计不参与 SQL 正确率。sql_case_count=5 是 database_query 路由计数。

## 3. 源身份与版本核对

- 逻辑数据库：short_video_ops；source_id：short_video_ops_duckdb。
- backend/dialect：duckdb；prompt_dialect：DuckDB；physical_schema：main。
- catalog_version：`68bc24f95eef81021c03a8d8819b00c43fc04fbaf13fbbf295268ebd857e60c2`。
- data_version：`d23481ffef242c04bc2adcf1f5a7082ec65ce392d30a48b16e7ccb0b3a3809b8`。
- E2E 运行 ID：`6f84aa1ac88d44479b08f62160402b2a`，状态 complete。
- E2E 数据集、应用、评分器、evaluation 代码、CSV、Schema 与当前本地完全匹配；应用和源版本也与本次 classic 报告匹配。
- 4 条具备数据库图的记录（查询、澄清发起、澄清恢复、空结果），图内 source_identity 全部一致。直接回复、问答、拒绝读取及预处理受控失败路径没有数据库图，不能声称这些记录各自含有图内源身份。
- 本地 Gold 和本地原始验证记录的 source_identity 一致。不同题集的 dataset version 本来不同，不要求 Gold/classic/E2E 的题集摘要相同。

## 4. 逐题 E2E 审核

| 用例 | 审查证据与结论 |
| --- | --- |
| GROWTH_OPS-001 | completed，SUM(new_users)，metric_date 筛选 2026 全年，按月份升序；8 行与 Gold 及离线重放一致。回复 5 月 1603 最高、8 月 1344 最低与真实行一致。 |
| E2E-ROUTE-DIRECT | direct_response、completed、有回复、无数据库工具调用；回复质量事项见下。 |
| E2E-ROUTE-QA | data_qa、completed，延续前一个会话结果、无重复数据库查询；峰谷数值正确，但指标解释及原因推测需要改进。 |
| E2E-PERMISSION-READ | 内容运营用户读取增长运营任务被拒绝，实际异常 PermissionError，status=denied。验收范围为跨用户任务读取。 |
| E2E-CLARIFY-START | waiting_clarification、无 SQL 执行，给出转化事件数、归因用户数、平均置信度评分 3 项。 |
| E2E-CLARIFY-RESUME | 同任务恢复，选项语义进入问题及 SQL，最终 completed；4 行结果与服务器及离线重放相同。仍有月份 WARN，首次限定来源错误后修正成功。 |
| E2E-EMPTY-RESULT | 正确定位 user_registrations.registered_at，单日半开区间、LIMIT 20，成功零行；明确回复没有匹配记录，校验 PASS。 |
| E2E-FAILURE-PREPROCESS | 在 preprocess 受控注入失败，返回 failed、failed_explicitly、无 SQL 执行；这条预期失败属于行为通过。 |

behavior_checks 中 sql_present=true 表示“SQL 存在/不存在符合用例预期”，不代表直接回复和澄清发起真的执行了 SQL。

### 4.1 澄清选项 → SQL → 最终回复

- 发起/恢复 task_id 同为 `a83f11258593`；source_case_id 指向 E2E-CLARIFY-START。
- 选中 option_1：转化事件数；说明为“按渠道产生的转化事件总数量从高到低排序”。恢复后的 standalone_query 与 clarification_resolved 日志同时保留 label 和 description。
- 最终查询以 channel_conversion_events 为事实来源，按 channel_id 关联 acquisition_channels 获取渠道名称，COUNT(*) 统计事件数，按渠道汇总并降序排列。
- 时间条件明确使用 converted_at >= '2026-05-01' AND converted_at < '2026-06-01'。
- 实际行：信息流广告 434、达人推广 339、搜索广告 303、品牌广告 198；回复中的最高渠道与数值全部匹配。
- 本次仅验证第一个选项。恢复用例不计入正式 Gold 正确率；手工语义审查和同版本重放是补充证据，不能宣称所有指标选项已覆盖。

### 4.2 日期与空结果

- 普通查询：metric_date >= '2026-01-01' AND metric_date < '2027-01-01'。
- 澄清恢复：converted_at >= '2026-05-01' AND converted_at < '2026-06-01'。
- 空结果：registered_at >= '1900-01-01' AND registered_at < '1900-01-02'，覆盖整天且不包含次日。
- 空结果定位记录的 source=validated_sql_sources_and_schema、status=resolved，selected_fields=user_registrations.registered_at，未误用 users.registered_at。
- status=completed、success=true、row_count=0、truncated=false。回复“查询已成功执行，当前条件下没有匹配记录。”；result_validation_reason 为“SQL执行成功，结果为空”。
- 零行 Gold 对照不能单独证明所有日期边界与排序行为；本次结合 SQL 和时间定位记录核对。实际 SQL 未含 ORDER BY，但用户未要求排序，空集也无法提供非空排序证据。

## 5. 保留事项

### 5.1 月份字段定位 WARN

E2E 本次只有澄清恢复用例保留唯一 WARN：“问题包含月份 2026-05，但没有可用指标时间字段可用于确定过滤列”。两次工具尝试均带此 WARN。最终 SQL 的 converted_at 条件正确；自动规划器 time_constraints 和 time_field_resolution 仍为空，metric_plan 也为空。因此执行结果通过不代表自动时间/指标校验覆盖完整。classic 原报告的 7 个月份 WARN 也继续保留。

### 5.2 schema 前缀的失败与修正

澄清恢复首次使用 short_video_ops.channel_conversion_events 等限定名，执行器返回“SQL引用了不允许的schema或catalog限定来源”；第二次移除逻辑数据库前缀后成功。物理 schema 是 main，不能将逻辑库 ID 当物理 schema。该安全校验按预期工作，但生成阶段尚未完全遵守命名约定，增加了一次修正调用。业务 SQL 校验曾显示 PASS，执行器仍拒绝限定来源，两层覆盖不同；后续方言/生成约束工作需记录此差异。

trace.tool_calls 只保留成功调用，execution_log 保存了失败尝试；本审查依据后者记录真实失败历史。M0/classic 已存在同类现象，不归因为 M1 A 新增回归。

### 5.3 回复与校验文案

1. 直接回复自称“请求预处理器”，暴露内部组件角色，应改为面向使用者的系统能力说明。
2. 数据问答将 new_users 解释为“新注册或新激活”，与独立 activated_users 指标的区分不足；关于营销活动、季节、投放减少的推测没有当前结果证据。应区分结果事实与需要进一步数据验证的假设。
3. 普通查询的校验文案因为只有 1～8 月就判为“部分回答”。本地同版本数据已核实增长日指标只有 2026-01-01～2026-08-28、2400 行；返回 8 月份与固定数据和 Gold 一致，缺少 9～12 月本身不意味着 SQL 漏查。应说明数据覆盖范围，不将正常覆盖不足误判为查询不完整。

这些事项不否定本次运行上下文、路由及 SQL 结果验收，但不能声称回复质量已经全部通过。当前自动行为检查仅检查部分回复字段存在，不验证完整业务解释质量。

## 6. 验收边界与收尾

- 本次是调用 Service 的进程内 E2E，不是 HTTP、浏览器或生产部署验收。
- 两条正式结果评分均通过，不等于 8 条都有 Gold 评分，也不等于 430 题全部 live 验证。
- E2E 审查已核验 3 条最终 SQL 的服务器完整行；当时没有修改原始 JSON、正式题集或评分器。后续 classic 收尾只向正式题集的 8 题追加 13 项已审核别名，0 次新模型请求；原始报告和评分器仍未改写。
- 历史本地验证 JSON、原始 ZIP/变更清单继续作为当时版本记录，不改写其“待服务器验证”的历史状态；当前状态以本文及独立最终验收 JSON 为准。

收尾顺序：

1. **已完成并在服务器验证**：13 项显式别名追加到 classic 8 题正式定义；原题集完整备份保留。本地与服务器复评分严格/宽松均 49/49、0 条未评分、0 新模型请求；49 题实际/Gold 行逐项完全相同，题集文件 SHA256、评分条件指纹和数据集版本也完全相同。独立服务器记录为 m1_a_live_classic_alias_rescore_server.json，详见 [收尾记录](M1_A_CLASSIC_ALIAS_CALIBRATION.md)。
2. **已完成**：m1_a_duckdb_gold_server.json 原始文件已归档，79 个用例无重复、49 classic＋30 扩展，均使用预期 Gold SQL，执行/宽松/严格结果全部通过，与本地对应结果行数一致，全部 Gold 来源为实际执行。该报告没有完整行，未宣称逐值对照了 Gold 服务器原始结果。
3. **资料已闭环**：可进入 M1 B 的隔离 PostgreSQL 数据准备；已知 WARN、schema 前缀和回复质量事项继续跟踪。

Gold 在追加别名前执行，其 79 题旧摘要 ca6d148c3e54b6306a9759242d0bca81199b0ff949932ce447592e75f7c0f756 与保留原题集及本地原 Gold 一致。当前 79 题定义摘要为 715855558de02ca9aa84b76c6418ed4080feaf066bbad9edc68bc78d09b2e0f0；差异只来自上述 13 项别名追加，Gold SQL、问题、数据、应用和评分规则未改变。旧 Gold 报告按原题集版本归档，不改写成新版本运行。

服务器 Gold 平均 SQL 执行 1748.224 ms、P95 1972.648 ms；此为 SQL 执行耗时，不是完整服务请求耗时。Gold 使用固定标准 SQL，不评估模型生成正确率。

## 7. 文件索引

- [原始 E2E 报告](results/m1_a_e2e_behavior_server.json)
- [独立 E2E 核对 JSON](results/m1_a_e2e_review_local.json)
- [最终验收结构化记录](results/m1_a_final_acceptance.json)
- [classic 列映射审查](results/m1_a_live_classic_review.md)
- [classic 独立候选核对](results/m1_a_classic_alias_review_local.json)
- [正式题集独立复评分](results/m1_a_live_classic_alias_rescore_local.json)
- [服务器正式题集独立复评分](results/m1_a_live_classic_alias_rescore_server.json)
- [服务器 Gold 原始报告](results/m1_a_duckdb_gold_server.json)
- [服务器归档逐题核查记录](results/m1_a_server_archive_review.json)
- [校准前完整题集备份](results/m1_all_cases_before_classic_aliases_20261007.jsonl)
- [本地 Gold](results/m1_a_duckdb_gold_local.json)
- 复核脚本：`python -m scripts.audit_m1_a_e2e`（backend 目录，同版本数据/题集）。
