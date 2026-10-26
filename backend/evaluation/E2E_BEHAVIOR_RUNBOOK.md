# M0 服务入口行为扩展集

`cases/e2e_behavior.json` 是独立的 8 条有序用例集；原有 `e2e_smoke.json` 的 3 条服务器基线保持不变。全部自然问题都经 `AskDataService.submit()`，恢复步骤经 `AskDataService.clarify()`，权限步骤经 `AskDataService.get_task()`。运行器不会向服务传入 Case 的 `retrieval_terms`。

| 用例 | 检查点 | SQL 结果评分 |
| --- | --- | --- |
| `GROWTH_OPS-001` | 问数完成，并给后续数据问答及权限用例建立真实任务 | 是 |
| `E2E-ROUTE-DIRECT` | 普通问候走直接回答，有文字回答，无 SQL | 否 |
| `E2E-ROUTE-QA` | 同一会话解释上一轮结果，走数据问答，有文字回答，无新 SQL | 否 |
| `E2E-PERMISSION-READ` | 内容运营身份读取增长运营任务，被 `PermissionError` 拒绝 | 否 |
| `E2E-CLARIFY-START` | 模糊的“表现最好”指标触发数据库问数澄清，至少两个选项 | 否 |
| `E2E-CLARIFY-RESUME` | 从上一步返回的真实选项中选择第一个，恢复并完成 SQL 查询 | 否 |
| `E2E-EMPTY-RESULT` | 1900-01-01 注册用户查询成功，SQL 含起止日期 1900-01-01／1900-01-02，返回零行 | 是 |
| `E2E-FAILURE-PREPROCESS` | 对该用例临时注入 `PipelineStageError`，服务返回显式失败及阶段日志 | 否 |

空结果题的 Gold SQL 已在本地数据上执行，结果为零行；该题和澄清恢复题还要求看到成功的工具调用。受控故障只验证服务入口处理工作流异常的行为，不代表真实模型或工具的故障率。权限用例依赖第一条用例创建的任务；澄清恢复依赖前一条实际产生的 `waiting_clarification` 和选项。如果前置用例失败，后续用例会明确记录失败，不会伪造任务或选项。

行为判定逐项记录在 `behavior_checks`，并按 `behavior_type` 汇总。`result_accuracy` 与 `strict_result_accuracy` 只统计有 Gold 结果的问数和空结果题；其余行为用例保持未评分，不把无 SQL 的正常行为当作 SQL 错误。路由和澄清涉及模型决策，当前只是预先确定的业务预期；首次服务器结果需要逐题审查后才能作为稳定基线。

修正前服务器报告为 `results/m0_e2e_behavior_server.json`。首轮修正报告 `results/m0_e2e_behavior_after_fixes_server.json` 已完成并审查：行为通过 7/8，恢复题重复澄清，空结果 SQL 正确但日期约束仍为 WARN。两份报告均作为历史基线保留。

2026-10-06 修正补齐所选项标签和说明，把确认语义加入独立查询与检索词，并保留恢复日志。日期校验在 SQL 基础校验通过后，使用实际来源表及其 Schema 元数据定位显式日期字段；仍有歧义时记录候选，不根据排序猜选。报告现在保存 `standalone_query`、`selected_clarification_option` 和 `trace.schema_graph`，便于复核。

同步本次代码后，先在服务器 `backend` 目录执行不调用模型的针对性测试（服务器应安装项目依赖，工作流恢复测试不应被跳过）：

```bash
python -m unittest tests.test_clarification_recovery tests.test_explicit_day_constraint tests.test_run_e2e
```

测试通过后，从 `backend` 目录另存完整 8 题 live 运行。两个有 Gold 的题使用现场执行结果评分：

```bash
TIME_FIELD_SUPPLEMENT_ENABLED=false python -u -m evaluation.run_e2e \
  --case-list evaluation/cases/e2e_behavior.json \
  --no-use-cached-gold \
  --save-snapshot \
  --output evaluation/results/m0_e2e_behavior_semantics_server.json
```

保存并下载 `evaluation/results/m0_e2e_behavior_semantics_server.json`。审查时先看每条 `behavior_checks`、`route`、`status`、`response_message`、`response_analysis`、`route_reason`、`direct_response_type`、`result_validation_reason`、`trace.clarification` 和 `comparison_reason`，再看两条有 Gold 的 `result_correct` 与 `strict_result_correct`。不要把这份行为集与 30 题组件集或旧 3 条 E2E 冒烟集直接合并计分。

本轮额外验收依据：

- 恢复题沿用起点任务 ID；`selected_clarification_option` 与起点选项一致；恢复后的 `standalone_query` 和 `clarification_resolved` 日志包含选定标签、业务说明；最终 `completed` 且有成功工具调用，不能通过允许再次等待放宽预期。
- 空结果 SQL 的实际日期范围为一天；最终工具 trace 的 `query_contract.constraint_plan` 包含 `registered_at/day_equals/1900-01-01`，`time_field_resolution` 记录来源表、候选与所选字段；`constraint_validation` 通过，无该日期的字段定位 WARN。
- 汇总目标仍为行为 8/8、宽松及严格结果 2/2。一次运行通过后仍按小样本证据记录，不据此宣称整体系统质量。

2026-10-06 的 `results/m0_e2e_behavior_semantics_server.json` 已下载并审查，本轮上述额外验收依据通过，审查见 `results/m0_e2e_behavior_semantics_server_audit.md`。该输出现在属于已归档基线。后续应用或提示变更应选择新的输出文件名，并保留首次及首轮修正报告。当前已知改进项为限定表名调用前校验、恢复题的月份规划 WARN 和回复内容质量。
