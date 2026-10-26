# M0 澄清语义与单日约束服务器报告审查（2026-10-06）

## 来源与完整性

原始报告 `m0_e2e_behavior_semantics_server.json` 的 SHA256 为 `0dc5cd06475e6a412c2c31372b2cbce536651a2846460c4beed55163a3f441a8`，运行 ID 为 `2191b25340874ebea55e18db57adcaf2`，创建时间 `2026-10-06T09:28:44.126004Z`，状态为 `complete`。模式 `e2e/behavior`，模型 `qwen3.7-plus`，温度 0，时间字段补充关闭。

8 条 Case 的顺序、运行 ID 和 trace ID 均与清单相符，逐题行为标记与检查项相符。重新汇总逐题记录，结果与报告完全一致。使用报告配置及审查时本地文件重建清单，Case、数据、Schema、应用、评估器、评估代码和 fingerprint 全部匹配。两个参与结果评分的 Case 的 `gold_result_source` 都为 `execution`，符合本轮不使用 Gold 缓存的命令。

与首轮修正报告相比，Case 及顺序、数据、Schema、模型和角色配置保持一致，应用和评测代码有变更，基准日期由 2026-10-03 变为 2026-10-06。前一轮首次选项为“转化事件数”，本轮为“新增注册用户数”；这两次恢复题的具体查询含义不同，不能直接把其 SQL 结果当作同一指标的回归比较。本轮已核对选项含义与本轮查询一致。

## 汇总与逐题证据

行为通过 8/8（100%），宽松及严格结果通过 2/2，6 条不参与结果评分。最终完成且有 SQL 的题为 3 条；`sql_case_count=5` 按数据库查询路由计数，包含澄清起点和受控故障。trace 中共有 5 次数据库工具尝试，3 次成功，2 次首次执行失败后被修正；不能把最终 8/8 解释为所有工具首次执行都成功。

| Case | 最终结果 | 证据与边界 |
| --- | --- | --- |
| `GROWTH_OPS-001` | 通过；查询完成 | 月度查询返回 8 行，结果及列严格评分通过；现场 Gold 评分。本地重放与报告一致。 |
| `E2E-ROUTE-DIRECT` | 通过；直接回答 | 回复有正文，无 SQL、无工具调用。现有行为检查不评价能力介绍的产品措辞。 |
| `E2E-ROUTE-QA` | 通过；数据问答 | 根据已有结果解释趋势，无 SQL、无工具调用。业务解释及因果分析质量未自动评分。 |
| `E2E-PERMISSION-READ` | 通过；拒绝跨用户访问 | 实际抛出 `PermissionError`，覆盖任务读取隔离。 |
| `E2E-CLARIFY-START` | 通过；结构化暂停 | 给出新增注册用户数、渠道转化事件数、广告消耗金额三个选项，无 SQL。 |
| `E2E-CLARIFY-RESUME` | 通过；恢复并完成 | 相同任务 ID，选项含义进入查询和日志，按选定指标查出 10 个渠道。首次 SQL 前缀错误，第二次修正成功。未纳入官方结果准确率分母。 |
| `E2E-EMPTY-RESULT` | 通过；合法空结果 | 一天范围、0 行、最终完成，明确说明无匹配记录。单日强制约束已生成，校验 PASS。首次 SQL 前缀错误，第二次修正成功。 |
| `E2E-FAILURE-PREPROCESS` | 通过；受控失败 | `preprocess` 失败日志及 `failed_explicitly` 模式符合预期。该题验证错误处理，不代表真实模型故障率。 |

`behavior_checks.sql_present=true` 表示 SQL 存在与否满足该题预期；直接回答、数据问答和澄清起点并没有 SQL。

## 澄清语义传递已在服务器生效

起点与恢复题任务 ID 同为 `f47bd3ede4ab`。选择的 `option_1` 为“新增注册用户数”，说明为“统计2026年5月通过各渠道注册的新用户数量，数量最多者为表现最好。”恢复记录的完整选项与起点选项相同，`clarification_resolved` 日志保留 ID、标签、说明及原问题。

恢复后的 `standalone_query` 明确加入这项确认。实际成功 SQL 使用 `user_registrations` 与 `acquisition_channels`，按注册时间 `[2026-05-01, 2026-06-01)` 过滤，按渠道统计注册记录并降序排列。最终 `clarification=null`，状态 `completed`，没有再次暂停。

实际 SQL 返回 10 行，前两名为“自然推荐”275 人、“信息流广告”261 人，回复与结果一致。使用相同权限和匹配数据在本地重放，列及行与服务器记录完全一致；另用 `COUNT(DISTINCT ur.user_id)` 按渠道计算注册用户数作为独立参考，得到相同的全部 10 行及排序。这是审查时的额外语义核对，未修改 Case、报告或官方评分分母。

## 单日字段歧义已消除，强制校验已生成

实际 Schema 图同时召回 `users.registered_at` 和 `user_registrations.registered_at`，两个字段都标为“注册时间”。这为前一轮“无法唯一确定过滤时间字段”的 WARN 提供了具体证据。本轮依据实际 SQL 来源 `user_registrations` 将候选缩小，`time_field_resolution` 为：

```json
{
  "source": "validated_sql_sources_and_schema",
  "status": "resolved",
  "retrieval_candidates": [
    "user_registrations.registered_at",
    "users.registered_at"
  ],
  "selected_fields": ["user_registrations.registered_at"],
  "sql_source_tables": ["user_registrations"]
}
```

最终查询契约包含 `user_registrations.registered_at/day_equals/1900-01-01`，日期规划无警告，约束校验 `PASS`。成功 SQL 为：

```sql
SELECT user_id, registered_at
FROM user_registrations
WHERE registered_at >= '1900-01-01'
  AND registered_at < '1900-01-02'
LIMIT 20
```

工具返回 0 行，最终完成，校验原因“SQL执行成功，结果为空”，回复“查询已成功执行，当前条件下没有匹配记录。”本地重放与报告相符，现场执行 Gold 后严格评分通过。

用报告保存的完整 Schema 图及实际 SQL 重建约束规划，结果与服务器保存的计划完全一致。正确 SQL 校验为 `PASS`；仅将上界替换为 `1900-02-01` 后为 `BLOCK`。这是本地离线反例验证，不能表述为服务器本次模型生成过错误的一月 SQL。

## 本轮发现的后续改进项

### SQL 的数据库标识与实际 Schema 前缀混淆

澄清恢复题和空结果题第一次都生成了 `FROM short_video_ops.user_registrations`，但 DuckDB 中没有名为 `short_video_ops` 的 Schema，实际数据库工具已选定数据库，表应使用物理表名 `user_registrations`。两次都出现明确的 Catalog Error，SQL 调用前校验却为 `PASS`。智能体随后移除前缀，第二次执行成功，说明执行错误反馈与有上限的修正路径有效，同时揭示调用前校验没有覆盖 Schema 限定名。

后续应校准 SQL 生成提示和限定表名校验，在执行前检查真实允许的 catalog/schema/table 组合，避免把路由数据库标识当作 DuckDB Schema。应保留首次失败及修正记录，不删除失败调用来呈现无错误结果。

### 恢复题仍有月份规划 WARN

恢复题的指标规划记录“指标 new_users 在当前权限范围不可用”，月份约束规划记录“问题包含月份 2026-05，但没有可用指标时间字段可用于确定过滤列”；因此该题约束校验仍为 `WARN`。渠道运营的选项是新增注册用户数，实际 SQL 使用其可访问的注册事实表，月份条件正确，本地参考查询也一致。

这个 WARN 与空结果题的单日定位问题不同。后续需要区分标准日汇总 `new_users` 指标和注册事实计数语义，补充明确的注册计数时间来源，或把来源下的日期定位扩展到月份。不能通过放开角色访问标准日汇总表或删除警告来消除问题。当前证据只说明本次恢复题 SQL 的月份正确，未证明该路径已有月份强制校验。

### 回复内容的评分边界

直接回答仍自称“请求预处理器”，暴露了内部组件身份。数据问答把 `new_users` 描述成“新注册或新激活”，并提及营销及季节因素，但 trace 没有这些口径或因果证据。现有行为集只检查路由、状态和正文存在，这些内容问题需后续回复质量评估；没有将其计入本轮已定义的行为失败。

## 验收结论

本轮事先约定的行为 8/8、结果 2/2、真实澄清语义传播及单日约束生效均有证据，可以归档为本轮修复后的服务入口行为基线。首次和首轮修正报告分别保持 SHA256 `9ea896777e44fb416703fc9ab6d5e4df52a64db4a559ef9696bc9a084a75b4c1` 与 `d5cbd4bd9e7b4ce7096998fdef6d43510ed1dfdbeca6bd71d9bde89491b62975`，未覆盖；本报告也保持原样。

这是一次 8 条样例的服务器 live 验收，不证明全量质量、所有澄清选项稳定通过或全部指标/日期口径已被强制校验。下一步可整理 M0 基线与已知问题，优先处理表名限定校验及恢复题月份口径，再按项目里程碑决定后续改进范围。
