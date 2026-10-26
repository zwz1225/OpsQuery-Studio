# M0 行为扩展集修正后服务器报告审查（2026-10-06）

## 来源与完整性

审查文件为 `m0_e2e_behavior_after_fixes_server.json`，SHA256 为 `d5cbd4bd9e7b4ce7096998fdef6d43510ed1dfdbeca6bd71d9bde89491b62975`。报告保持原样，运行 ID 为 `d3c2ae87e8254d5f8ab9f90f06c26e45`，`run_status=complete`，运行清单的创建时间为 `2026-10-03T14:12:47.402547Z`。

8 条 Case 的顺序、运行 ID、trace ID 与清单一致；每题 `behavior_correct` 与其检查项一致，重新调用 `summarize_e2e()` 得到与原报告完全相同的汇总。使用报告配置与审查时的本地 Case 重建运行清单，`dataset`、`versions`、`config`、`fingerprint` 均一致，数据、Schema、应用、评估器及评估代码版本全部匹配。此核对发生在下面记录的第二轮修正实施之前；实施后该报告属于历史应用版本。

运行配置为 `e2e/behavior`，时间字段补充关闭，模型 `qwen3.7-plus`，温度 0。与首次行为报告相比，Case、数据和 Schema 相同，应用与评测代码有变更，基准日期从 2026-09-29 变为 2026-10-03。这是修正后的一次独立 live 运行，5/8 到 7/8 的变化应结合逐题记录解释，不能归因于单项改动或证明稳定通过。

## 逐题结果

行为通过 7/8（87.5%），宽松及严格结果均通过 2/2，6 条未参与结果评分。

| Case | 行为 | 核对结果 |
| --- | --- | --- |
| `GROWTH_OPS-001` | 通过 | 查询完成，返回 2026 年 1—8 月的 8 行结果，宽松与严格评分均通过。Gold 来源为匹配版本的缓存。 |
| `E2E-ROUTE-DIRECT` | 通过 | `direct_response/completed`，有回复正文，无 SQL 或工具调用。正文自称“请求预处理器”，属于后续回复质量改进项；现有检查不评价产品措辞。 |
| `E2E-ROUTE-QA` | 通过 | `data_qa/completed`，使用已有结果解释趋势，没有新 SQL 或工具调用。正文中对原因使用“可能”等表述；业务解释质量未自动评分。 |
| `E2E-PERMISSION-READ` | 通过 | 跨用户读取起点任务抛出 `PermissionError`；覆盖任务读取隔离。 |
| `E2E-CLARIFY-START` | 通过 | `database_query/waiting_clarification`，提供转化事件数、归因用户数、注册人数 3 个选项，无 SQL。 |
| `E2E-CLARIFY-RESUME` | 未通过 | 已选择 `option_1`，恢复后仍为 `waiting_clarification`，再次询问同一指标；没有 SQL 或工具调用。 |
| `E2E-EMPTY-RESULT` | 通过 | SQL 成功返回 0 行，最终 `completed`，明确说明无匹配记录；日期范围正确，宽松与严格评分通过。 |
| `E2E-FAILURE-PREPROCESS` | 通过 | 受控注入后 `failed`，`preprocess` 失败记录和 `failed_explicitly` 模式符合预期。 |

`behavior_checks.sql_present=true` 表示“SQL 是否存在符合该题预期”，直接回答、澄清起点和受控失败的预期均为没有 SQL。`sql_case_count=5` 按最终数据库查询路由计数，包含等待澄清与受控失败；实际完成且有 SQL 的题为 2 条。`result_accuracy=1.0` 仅覆盖这 2 条。

## 澄清恢复失败的证据与代码解释

第 5、6 题使用相同任务 ID `ead6e382093d`，恢复记录包含 `selected_clarification_option_id=option_1`。起点的第一项为“转化事件数”，说明为“按渠道在2026年5月产生的转化事件总数降序排列”。恢复后再次询问“表现最好”具体指哪个指标，生成了新的 3 个选项；路由检查通过，状态、SQL 存在和工具成功检查均失败。此次失败发生在恢复后的再次澄清，不再是首次报告中的“前一步未暂停”。

代码核对：`QueryWorkflow._human_clarification()` 只把 `parameter: option_id` 写入 `workspace.confirmed_parameters`，随后清空 `clarification`。选项的 label、description 没有进入确认参数，原 `standalone_query` 也未补入选择语义。`SingleDatabaseAgent.prepare()` 把这一确认参数传给模型，但参数值只有无业务含义的 `option_1`。这是当前代码可确认的信息缺失，结合本次重复提问，可以解释恢复后仍无法使用选定指标；报告未保存完整模型输入，因此这一解释来自报告和代码的联合分析。

后续应保留并传递所选项的 ID、标签及业务说明，让检索、指标规划和 SQL 生成都能使用确认语义；对同一已确认问题重复澄清增加检查。恢复题应继续要求完成且执行成功，不能通过允许再次等待来放宽评分。先做本地确认语义传播验证，再在服务器独立重跑澄清链和完整行为集。

## 空结果与日期约束的边界

实际 SQL 为：

```sql
SELECT user_id, registered_at
FROM user_registrations
WHERE registered_at >= '1900-01-01'
  AND registered_at < '1900-01-02'
LIMIT 20
```

该 SQL 正确限定一天。工具成功、返回 0 行，最终校验原因是“SQL执行成功，结果为空”，回复是“查询已成功执行，当前条件下没有匹配记录。”这次运行已验证合法空结果的状态修正。

但 trace 中 `constraint_plan.time_constraints=[]`，`constraint_validation.status=WARN`，警告为“问题包含日期 1900-01-01，但无法唯一确定过滤时间字段”。因此本次正确日期 SQL不能证明单日强制校验已在真实检索路径中生效。

本地用真实 Schema 的 `registered_at`（标签“注册时间”、类型“日期”）构建仅含该字段的 Schema 图时，规划器可生成 `user_registrations.registered_at/day_equals/1900-01-01`。服务器报告未保存完整检索图，无法确认 WARN 是字段缺失还是多个候选导致；修复应核对真实检索输入，而不是直接假定字段类型错误。后续需要让日期字段定位有明确依据，并验证错误的一月范围在实际路径中被拦截。

## 当前结论与下一步

报告诊断字段、澄清起点和合法空结果已有服务器证据；澄清恢复仍未通过，单日校验的真实路径仍有 WARN，M0 行为验收尚未完成。优先修复澄清选项语义传播，同时补齐日期字段定位的证据。首次报告与本次报告均保留，用新的文件名保存下一轮运行，继续独立记录行为通过率与结果评分分母。

## 第二轮本地修正实施（2026-10-06）

已保存确认选项的 ID、标签和业务说明，并把含义加入独立查询、检索词及模型确认参数；同一已确认参数的重复澄清进入有上限的输出修正，无法修正则显式失败，不继续重复暂停。恢复事件写入执行日志，等待及完成状态均保留该日志。

日期规划记录字段候选与选择依据。SQL 基础校验通过后，明细查询的单日字段按照实际来源表及这些已在可访问 Schema 图内的表的元数据重新定位；同名候选被缩小至实际来源后才建立单日约束。多个来源仍有歧义时继续保留 WARN，不按候选顺序选择。错误的一月 SQL 在本地智能体验证中先 BLOCK，修正为次日上界后才调用一次工具。

E2E 报告新增恢复后的 `standalone_query`、完整的 `selected_clarification_option` 与 `trace.schema_graph`。Case 预期及评分规则保持原定义。相关本地测试执行 76 项，75 项通过，完整 LangGraph 恢复测试因本地缺少 LangGraph/MCP 依赖跳过 1 项；服务器需补跑这一集成检查及模型驱动的 live 验收。下一份独立报告为 `m0_e2e_behavior_semantics_server.json`，当前尚未运行，命令与检查点见 `../E2E_BEHAVIOR_RUNBOOK.md`。
