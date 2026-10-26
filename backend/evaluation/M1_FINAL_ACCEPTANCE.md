# M1 最终验收记录（有条件收尾）

整理日期：2026-10-15。验收对象是隔离测试环境中的 DuckDB 与 PostgreSQL 双后端改造；本记录依据已归档的服务器报告和本地逐题核对，不代表生产环境验收。

## 结论

**建议按已知偏差有条件结束 M1 实施，进入后续改进。** PostgreSQL 的数据准备、只读执行、方言与来源隔离、430 题 Gold、79 题 live 的 SQL 执行和结果值、8 条服务入口行为均已有通过证据。**原定“新一轮原始 live 严格评分 79/79”门槛未通过：v7 为 76/79。** 因而不能把 M1 E 或整个 M1 记为“全部指标无例外通过”，也不能把离线 Gold 或宽松结果替代原始 live 严格成绩。

有条件收尾的偏差是三道 classic 题的输出列名与正式题集的显式别名尚未对齐。它们的 SQL、结果值、来源和约束校验在 v7 均通过；七项候选别名仍未完成独立 PostgreSQL 复评分，未写入正式题集。若项目必须坚持原定严格门槛，则 M1 的**形式验收仍未完成**，详见[遗留项清单](M1_OPEN_ISSUES.md)。

## 阶段证据

| 阶段 | 已完成范围和结果 | 主要记录 |
| --- | --- | --- |
| M1 A | 现有 DuckDB 接入统一运行上下文；服务器 Gold 79/79；classic 原始严格 41/49，经逐题显式别名独立校准为 49/49；8/8 E2E。 | [A 最终验收](M1_A_FINAL_ACCEPTANCE.md) |
| M1 B | 在隔离库 `askdata_m1_test.askdata_ops` 导入并独立验证 41 表、276 字段、722,732 行；完整类型化行摘要和只读权限检查通过。 | [B 最终验收](M1_B_FINAL_ACCEPTANCE.md) |
| M1 C | 完成受控连接池、只读事务、实时元数据与来源核验、PostgreSQL 执行器及 runtime；C3 服务器 24 项检查通过。 | [C3 核对](M1_C3_SERVER_REVIEW.md) |
| M1 D | 统一方言和 Gold 选择，隔离缓存、manifest、snapshot 与跨来源续跑；DuckDB 和 PostgreSQL 的 430 题 Gold 各为 430/430 执行及严格正确，独立跨后端比较 430/430 通过。 | [D1](M1_D1_CONTRACT_ACCEPTANCE.md)、[D2](M1_D2_SQL_RUNTIME_ACCEPTANCE.md)、[D3 Gold430](M1_D3_POSTGRES_GOLD430_SERVER_REVIEW.md)、[D4](M1_D4_SERVER_REPORTS_REVIEW.md) |
| M1 E | v7 PostgreSQL classic 49/49、扩展 30/30 SQL 执行和宽松结果正确；原始严格分别为 46/49、30/30。8/8 服务入口行为通过。 | [v7 逐题核对](M1_E_POSTGRES_V7_REVIEW.md) |

430 题 Gold 是**已编写 SQL**的执行与跨后端结果验收，不是 430 题模型 live。D3 Gold430 报告使用当时题集摘要 `e1cb760a8ffa4f89e45ca73403c439975c51d2be47cd36800ee4c7c0ee1925f1`；后续正式题集增加逐题评分别名，v7 题集文件 SHA-256 为 `82761737b873c9d4e9daac852bb3bf30867adc01919d088289dc9ba03972ed33`。不能把 D3 原报告描述成在 v7 题集版本上重新运行的 Gold430。

## 最终 PostgreSQL 来源与 v7 结果

v7 三组报告均为 `complete`，并通过来源身份校验；来源一致为 `short_video_ops_postgres` / `postgresql` / `askdata_ops`。数据版本为 `882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1`，catalog 版本为 `94a801805965a90aa6ae015f28af196f88f72c1d887319dd1896a2973eaaa288`，物理结构版本为 `b12bffb567ee4aa3ca126d48154ddfb36c1721d1af7c6e8b65efc4780615a817`。实时核验记录了 41/41 表的完整行摘要及只读 ACL。PostgreSQL 是显式选择的后端；此前默认 DuckDB 路径并未被本次验收改成 PostgreSQL 默认。

| 原始服务器报告 | 文件 SHA-256 | 结果 |
| --- | --- | --- |
| [classic v7](results/m1_e_postgres_live_classic_server_v7.json) | `b3f0aef50b51665b3c665b6faa701d24c4401d34331742c310d001ff4c22ffde` | SQL 49/49；结果值 49/49；**原始严格 46/49**；49 PASS、0 WARN |
| [phase83 v7](results/m1_e_postgres_live_phase83_server_v7.json) | `188c170d24128c1f347bf79ce1ebd4dd8f0616508b51f032ae02f202b4495f49` | SQL 30/30；结果值 30/30；原始严格 30/30；30 PASS、0 WARN |
| [E2E v7](results/m1_e_postgres_e2e_behavior_server_v7.json) | `355b41794a876857bbf130c30f625d09d550412de3e112588d8475b277e79c46` | 行为 8/8；设计为结果评分的 2/2 宽松及严格正确；其余 6 条按用例设计不评分 |

79 题合计 SQL **79/79**、宽松结果 **79/79**、原始严格 **76/79**，0 未评分、0 SQL 错误、0 模型重试、0 超时和连接错误。三道严格失败为 `GROWTH_OPS-066`、`CHANNEL_OPS-003`、`CHANNEL_OPS-076`，均在 classic 组。E2E 实际执行的三次 SQL 工具调用均成功，校验 PASS、warnings 为空；澄清选项语义、五月日期范围、空结果回复、跨用户拒绝和受控失败按[逐题核对](M1_E_POSTGRES_V7_REVIEW.md)通过。E2E 是进程内服务入口验证，不能扩展解释为 HTTP 或生产环境验收。

v7 已验证此前的具体修复：`CHANNEL_OPS-025` 的“截至某月”使用下一月首日作为上界且约束 PASS；`CHANNEL_OPS-136` 在 v5 的 PostgreSQL `42703` 错误经独立复现、改写和后续回归后已消失；`GROWTH_OPS-051`、`CONTENT_OPS-025`、`CONTENT_OPS-052` 执行且严格通过。服务器在 v6 题集更新后完成 509/509 单元回归；该记录见[v6 核对](M1_E_POSTGRES_V6_REVIEW.md)，不把它冒充为 v7 后又执行的一轮新测试。

## 判定边界与收尾处理

1. 保存各轮原始 JSON、独立诊断和题集修改记录；不得覆盖旧报告、改写 v7 的 76/79 或用通配别名放宽评分。
2. M1 功能改造可按上述例外归档；原始严格评分 79/79 标记为**未达到**，在[遗留项清单](M1_OPEN_ISSUES.md)持续跟踪。
3. 不再为了追逐一次 79/79 而重复全量 live。若要关闭严格评分差异，先为三题保存 SQL 与 Gold 做同源独立复评分、逐列确认七项候选别名，再决定题集或生成输出契约的改动。复评分只能证明保存 SQL 在新规则下的结果；若仍以“新 live 79/79”为强制门槛，必须另起文件名运行并据新报告判定。
4. 后续目标若变更 PostgreSQL 数据、schema、权限、模型、题集或评分策略，应按新的来源/版本重新建立证据；本记录只证明上述固定版本和隔离测试环境。
