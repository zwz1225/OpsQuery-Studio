# M1 E PostgreSQL 首轮 live 与服务入口报告审查

审查日期：2026-10-12。结论：三份报告完整、来源身份一致，**首轮 M1 E 尚未通过验收**。原始报告保留；本文件和 [`m1_e_postgres_server_review_local.json`](results/m1_e_postgres_server_review_local.json) 是独立审查记录，未修改正式题集、评分规则或服务器报告。

## 1. 报告与来源

| 报告 | 运行 ID | SHA-256 | 状态 |
| --- | --- | --- | --- |
| [`m1_e_postgres_live_classic_server.json`](results/m1_e_postgres_live_classic_server.json) | `95c65d26c28a45feb6bada7a74fa6025` | `6676a38ec3cd823d4030214088e13c37a2d5c2c37c93ce86de09bb1793efb6d4` | complete |
| [`m1_e_postgres_live_phase83_server.json`](results/m1_e_postgres_live_phase83_server.json) | `fdbb8f5cf9c548c5a6b79c8071c8bf7c` | `db5b1b2305c4bd2aae2e12afa72e026259319301c7587306348a0a9e02c1e801` | complete |
| [`m1_e_postgres_e2e_behavior_server.json`](results/m1_e_postgres_e2e_behavior_server.json) | `0a4f591587224b1989151dbfaab9e5ac` | `7c4a7993c2cd9414b3438e7c2f3e39e5b431a1b7e2c08d25643c1ae29b60825d` | complete |

三份均为 manifest v4，`source_id=short_video_ops_postgres`，`backend=postgresql`，`dialect=postgres`，物理库 `askdata_m1_test`、schema `askdata_ops`。数据版本 `882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1`，catalog 版本 `94a801805965a90aa6ae015f28af196f88f72c1d887319dd1896a2973eaaa288`，物理结构版本 `b12bffb567ee4aa3ca126d48154ddfb36c1721d1af7c6e8b65efc4780615a817`，与 M1 C3/D3 验收版本相同。三次 manifest 均记录实时来源核验：41 表、276 字段、722732 行，41 表的类型化数据、表权限与列权限核对通过。时间字段补充均关闭。

独立检查通过：报告 manifest 指纹、逐题 ID 顺序、题集摘要、选中 PostgreSQL Gold SQL 摘要、评分策略摘要、应用与评测代码摘要，以及用当前汇总函数重算的 summary。79 条 live 题目互不重复；已执行的 live 题记录的 Gold SQL 与正式题集中的 PostgreSQL 变体一致。上述检查说明报告可作为本轮基线，不代表生成 SQL 的结果已通过验收。

## 2. 结果与统计口径

| 运行 | SQL 执行 | 宽松结果 | 严格结果 | Schema 召回 / 精确率 | 模型请求尝试 |
| --- | ---: | ---: | ---: | ---: | ---: |
| classic 49 | 48/49 | 47/49 | 38/49 | 0.929932 / 0.166049 | 160 |
| 扩展 30 | 27/30 | 25/30 | 20/29 | 0.974713 / 0.232516 | 104 |
| 合计 | 75/79 | 72/79 | 58/78 | 不跨集平均 | 264 |
| E2E 行为 | 实际执行 SQL 3 次 | 结果题 2/2 | 结果题 2/2；行为 8/8 | 不适用 | — |

扩展集 `GROWTH_OPS-051` 的严格结果为 `null`，因此严格评分分母为 29；报告 `unscored_count=0` 对应宽松评分，不能解释为 30 题均完成严格评分。classic 的 `error_count=0` 只表示没有 `benchmark_error`，但 `GROWTH_OPS-150` 实际 SQL 执行失败。E2E 的 `sql_case_count=5` 按路由计数，其中澄清开始与受控失败未执行 SQL；工具执行日志里实际 SQL 执行 3 次。

## 3. 需要修复的执行和业务口径问题

### PostgreSQL 表达式失败：3 题

- `GROWTH_OPS-150`、`GROWTH_OPS-148`：实际激活率与 `growth_targets.activation_rate_target` 相减后，以两参数 `ROUND(..., 4)` 四舍五入；两题均返回 `SQLSTATE 42883`。
- `CHANNEL_OPS-136`：`ad_daily_stats.spend` 与 `channel_targets.target_cpa` 参与的两个 CPA 四舍五入表达式返回 `SQLSTATE 42883`。

M1 C3 的真实字段类型证明这些目标率、目标 CPA 和广告消耗列为 `double precision`。结合报告 SQL，可推断混合运算使整个表达式为浮点类型，而 PostgreSQL 的两参数 `round` 需要 `numeric`；仅转换分子或分母不足以保证最终表达式类型。服务器报告仅保留了脱敏 `query_error (SQLSTATE 42883)`，没有原始函数签名，因此这里是**有类型证据支持的原因推断**，修复后仍须在 PostgreSQL 实际执行确认。[PostgreSQL 16 数学函数](https://www.postgresql.org/docs/16/functions-math.html)、[错误码 42883](https://www.postgresql.org/docs/16/errcodes-appendix.html)。

### 指标校验阻断：1 题

`GROWTH_OPS-051` 在 `single_database_agent` 阶段报“指标 activation_rate 的分子必须统计 user_activations.is_activated 为真的注册记录”，没有保存被拒绝的生成 SQL，也没有执行 SQL。当前证据不能判断是模型生成错误，还是校验器误拦截；先补充受控诊断证据，再决定修正位置。它是严格评分未覆盖的那一题。

### SQL 成功但业务结果错误：3 题

- `GROWTH_OPS-066`：生成 SQL 额外加入 `is_activated = 1`，正式口径按 `user_activations` 的全部激活记录统计规则；报告显示行数不一致。不能作为别名问题处理。
- `GROWTH_OPS-076`：用 `growth_daily_metrics.day1_retained_users / COUNT(*)` 的“天数”计算留存率；正式口径是 `user_retention` 中 `retention_day=1` 的观察用户及留存用户。严格评分首先报缺少 `observed_users`，但 SQL 的分母和来源表均不同。
- `GROWTH_OPS-100`：生成 SQL 对 `users.registered_at` 限定 2026-05 注册队列，正式 SQL 对 `user_daily_activity.activity_date` 限定 2026-05 活动月份；还额外返回两个未声明辅助列，并使用不同的结果精度。严格评分的“辅助列”提示遮蔽了真实日期口径及数值差异。

## 4. 待审查的逐题显式列别名

另有 **14 题**满足 SQL 执行成功、宽松结果正确、严格结果失败，全部因缺少逐题列映射；合计 **23 项候选映射**。以下只登记候选，不代表自动批准加入正式题集。逐题确认语义、结果、排序和并列规则后，再按原有流程添加显式别名并单独复评分。

| 题目 | 缺少的期望列 → 实际列 |
| --- | --- |
| `CHANNEL_OPS-079` | `status→状态`，`campaigns→广告计划数`，`budget→预算` |
| `CONTENT_OPS-031/032/033/034` | 各题 `interactions→interaction_count` |
| `CONTENT_OPS-036` | `interaction_date→interact_date` |
| `CONTENT_OPS-051` | `avg_duration_seconds→avg_duration` |
| `CONTENT_OPS-076` | `creator_status→创作者状态`，`creators→创作者数量` |
| `CONTENT_OPS-138` | `reports→report_count` |
| `GROWTH_OPS-050` | `registrations→register_user_count` |
| `GROWTH_OPS-102` | `users→user_count` |
| `GROWTH_OPS-126` | `touch_channel→触达方式`，`touches→触达数量`，`delivery_rate→送达率`，`click_rate→点击率`，`recall_rate→召回率` |
| `CHANNEL_OPS-025` | `month→月份`，`spend→广告消耗`，`mom→环比变化率` |
| `CHANNEL_OPS-051` | `conversions→conversion_count` |

这些题的报告只记录比较结论和 SQL，未嵌入 live 执行结果行；本地不能从三份文件重新逐值计算 14 题。`GROWTH_OPS-126` 的 `LEFT JOIN` 与 Gold 的 `JOIN` 也应核对无匹配记录的处理。不得为 `GROWTH_OPS-066/076/100` 等真实口径错误题添加宽松别名或辅助列白名单。

## 5. 八条服务入口行为

| 用例 | 审查结果 |
| --- | --- |
| `GROWTH_OPS-001` | PostgreSQL 实际返回 2026-01 至 08 的 8 行新用户数，严格结果通过；回复中 5 月最高 1603、8 月最低 1344 与执行行相符。 |
| `E2E-ROUTE-DIRECT` | 路由、无 SQL、回复均符合行为检查；最终文案却自称“请求预处理器”，暴露实现角色，应作为回复质量问题记录。 |
| `E2E-ROUTE-QA` | 使用前一题结果回答，未重复查库；数值趋势一致，但把 `new_users` 解释成“新注册或新激活”，混淆指标含义，营销/季节原因仅属猜测。 |
| `E2E-PERMISSION-READ` | 跨用户读取被 `PermissionError` 拒绝，符合预期。 |
| `E2E-CLARIFY-START` | 等待澄清，给出“新增用户数 / 转化事件数 / 广告消耗金额”三项，尚未执行 SQL。 |
| `E2E-CLARIFY-RESUME` | 选项 `option_1` 的标签与描述写入续问；SQL 对 `user_registrations.registered_at` 取 `[2026-05-01, 2026-06-01)`，按注册人数排序，实际返回“自然推荐”275 人，回复一致。SQL 校验 PASS，但指标规划称 `new_users` 不可用，日期约束校验 WARN 称无可用时间字段；与已执行且正确的注册时间过滤不一致，需修复替代来源上的规划/校验。 |
| `E2E-EMPTY-RESULT` | 1900-01-01 的注册日期范围查询成功、0 行，回复明确“没有匹配记录”；日期字段定位与约束校验 PASS。 |
| `E2E-FAILURE-PREPROCESS` | 人为注入的预处理失败按预期受控结束，无 SQL 执行；这是预期故障用例。 |

E2E 两条结果题的评分为 2/2；其中 `GROWTH_OPS-001` 的工具日志含完整 PostgreSQL 实际行，按正式题集列别名、结果行重新严格比较也通过。澄清恢复的 SQL 工具日志含实际 1 行；该行为题没有独立 Gold 结果分数，不能把它算进 2/2。权限拒绝、直接回复、问答、澄清开始和受控失败属于行为评分，不是 SQL 结果未完成。

## 6. 验收判断与顺序

保留这三份文件作为 **M1 E 修正前基线**，状态记为“首轮审查完成，待修正”。优先处理 3 条 PostgreSQL 表达式执行错误，补出 `GROWTH_OPS-051` 被拦截的 SQL 诊断证据；随后修复 3 条业务口径错误和澄清恢复的替代时间字段 WARN。14 条列名候选逐题审查后才写入正式题集，另存离线复评分记录。修正后分别用新文件名重跑 classic 49、扩展 30 与 E2E 8，并再次核对来源身份、真实 SQL、严格评分覆盖率和服务回复。

本轮报告本身不包含 live 逐题实际结果行，也没有 `SQLSTATE 42883` 的完整服务器错误文本。这限制了本地独立复算与具体函数签名的最终确认；相关结论已按报告原文、SQL 和经核验的表类型标明证据等级。
