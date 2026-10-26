# M1 D4：服务器三份报告核对

审查日期：2026-10-11。审查结论：**D4 首批 79 题 Gold 与跨后端结果报告验收通过。** 本地根据下载的实际结果行重新计算，未连接数据库、未调用模型。原始三份报告保持不变。

## 1. 原始材料

| 报告 | 文件字节 SHA256 |
|---|---|
| `results/m1_d4_duckdb_gold79_server.json` | `47fb82a3df7ac2effbda7b6428e6b3144475999739048f4e04b4afebf41aef33` |
| `results/m1_d4_postgres_gold79_server.json` | `d47752087a112666bd38d235576ccbde06d8ec6856747f7dcdd7007c7c517a15` |
| `results/m1_d4_cross_backend_gold79_server.json` | `69017eae4ec38e81c400f6d01844c03ea1e71e32f5d05d9292cba20c875499ec` |

DuckDB 运行 ID：`592a0f58d6c8455894f66fad758c9a75`。

PostgreSQL 运行 ID：`35b23e5432d04dcf8e73a107bb3373bd`。

独立复算：`results/m1_d4_cross_backend_gold79_replay_local.json`。

完整机器审查记录：`results/m1_d4_server_reports_review_local.json`，含 158 份证据逐题检查、类型差异明细、重点题实际结果及来源/版本记录。

## 2. 结果与汇总复算

| 检查 | DuckDB | PostgreSQL |
|---|---:|---:|
| 运行状态 | complete | complete |
| 固定题号、顺序、题集版本 | 79/79 一致 | 79/79 一致 |
| SQL 执行成功 | 79/79 | 79/79 |
| 宽松结果正确 | 79/79 | 79/79 |
| 严格结果正确 | 79/79 | 79/79 |
| 原始列名匹配 | 79/79 | 79/79 |
| 实际 Gold 来源为 execution | 79/79 | 79/79 |
| 比较目标为冻结 expected_rows | 79/79 | 79/79 |
| 完整结果行证据及摘要有效 | 79/79 | 79/79 |
| 未评分、错误、超时、连接错误 | 均 0 | 均 0 |
| 模型请求/重试 | 均 0 | 均 0 |
| 全部 summary 字段独立复算 | 一致 | 一致 |
| 平均执行时间 | 1786.900 ms | 2642.605 ms |
| P95 执行时间 | 2170.199 ms | 2676.193 ms |

这些执行时间包含执行器及来源保护等流程，不能据此单独评价数据库原生查询性能。

## 3. 来源、方言、版本与权限

- 两份 manifest 均为 v4，指纹正确。应用、评分器、评测代码版本既相互一致，也与本地已验证的 D4 代码一致；结果策略摘要一致。
- DuckDB：`short_video_ops_duckdb / duckdb / duckdb / main`。数据版本 `d23481ffef242c04bc2adcf1f5a7082ec65ce392d30a48b16e7ccb0b3a3809b8`，catalog 版本 `68bc24f95eef81021c03a8d8819b00c43fc04fbaf13fbbf295268ebd857e60c2`。
- PostgreSQL：`short_video_ops_postgres / postgresql / postgres / askdata_ops`。数据版本 `882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1`，catalog 版本 `94a801805965a90aa6ae015f28af196f88f72c1d887319dd1896a2973eaaa288`。
- PostgreSQL 物理结构版本 `b12bffb567ee4aa3ca126d48154ddfb36c1721d1af7c6e8b65efc4780615a817`；实时校验记录为 true，41 表、276 字段、722,732 行，完整类型行摘要和两类 ACL 核对均为 41 表通过。
- 重新验证 M1 B 导入与目标校验材料；跨后端报告使用的等价数据证据、材料 SHA256、来源与物理目标均匹配。
- 除后端和来源 ID，两份运行配置完全相同，使用相同的三个业务场景 demo 权限和评测日期。
- 每题执行 SQL 与本地正式题集中的对应 Gold 选择一致。DuckDB 使用原 SQL，PostgreSQL 使用显式 postgres 变体；全部权限 trace 为已检查、SQL 权限检查成功、未阻止。
- 每题执行 trace、证据来源、manifest、实际 SQL、返回行数均一致。报告记录的 Gold 缓存路径分别属于 `gold_results/short_video_ops_duckdb/` 和 `gold_results/short_video_ops_postgres/`；本轮执行不命中缓存。
- 直接将这两份真实报告送入续跑校验，两个方向均拒绝跨来源续跑；普通同源回归比较也拒绝将它们作为同一来源评分。

## 4. 独立跨后端复算

重新执行 `evaluation.compare_backends`，本地结果与服务器原比较报告除生成时间外所有字段完全一致，包括逐题理由、来源、输入内容摘要及材料身份。

| 项目 | 本地复算结果 |
|---|---:|
| PostgreSQL 与 DuckDB 严格比较 | 79/79 |
| DuckDB 与冻结预期严格比较 | 79/79 |
| PostgreSQL 与冻结预期严格比较 | 79/79 |
| 两份原报告严格评分与复算一致 | 79/79 |
| 比较状态 | passed |
| 比较器模型请求 / 数据库连接 | 0 / 0 |
| 是否标记为同源回归 | false |

### 数值类型的报告口径

服务器 `raw_rows_identical_count=79` 的实现使用 Python 列表/字典值相等判断，`1520 == 1520.0` 会成立。因此它表示列名、行顺序和行值相等，**不能解释为 JSON 数字类型或文件字节完全相同**。

进一步按规范化 JSON 内容核对：61 题列与行完全一致；18 题共有 257 个单元格为 DuckDB 整数、PostgreSQL 等值浮点数，例如 GROWTH_OPS-001 的 `1520` 与 `1520.0`。全部差异仅为这一类型表示差异，值相同；未发现布尔值混淆、日期差异、NULL 差异或数值精度丢失。现有严格比较允许等值数值，这不改变评分规则，也不影响本轮结果验收。完整差异清单已独立记录，原报告未修改。

## 5. 重点题核对

- **CHANNEL_OPS-025：**首月 `mom=null`，第二月 `1.7938`；5 行月份顺序一致，窗口函数、NULL 和舍入结果两种后端相同。
- **CONTENT_OPS-036：**17 行均为 2026 年 1 月的日期字符串，首行 `2026-01-02`；日期提取、过滤和顺序均一致。
- **CONTENT_OPS-025：**返回 10 行，前 7 行播放数 9、后 3 行播放数 8；两种后端标题及顺序一致，继续使用已批准的 Top-N 并列规则。
- **GROWTH_OPS-051/075/076/126：**真假条件、分母和小数结果已复核。例如 075 为注册 1603、激活 1212、比率 0.7561；126 为 push 触达 5207、送达率 0.9366、点击率 0.1755、召回率 0.102。
- **GROWTH_OPS-148/149/150：**实际比率、目标与 gap 一致，例如 148 首行 0.8372、0.6454、0.1918。
- **CHANNEL_OPS-051/136：**转化率、CPA、目标和 gap 结果一致，NULLIF 分母与 numeric 舍入保持原业务语义。

## 6. 验收边界与下一步

三份下载报告达到 D4 首批 79 题报告验收条件；已有本地 28 项专项、469 项完整回归证据。本轮未提供服务器专项/完整回归日志，不能将本地测试记录标为服务器测试记录。Schema 索引重建与隔离已有本地专项证据，本轮 Gold 不进行真实 Embedding 索引构建。下载的 snapshot 文件本轮未提供，快照来源隔离仍依据已有本地检查。

剩余 351 题 PostgreSQL Gold 变体、正式 PostgreSQL live、服务入口 E2E 尚待完成；本次结果不代表整个 M1 验收结束。下一步按既定路线补齐剩余变体，再进行正式 PostgreSQL 问数与服务行为验收。
