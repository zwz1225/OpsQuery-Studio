# M1 D3：首轮79题 PostgreSQL Gold 服务器报告核对

核对日期：2026-10-10。结论：**首轮79题的 PostgreSQL Gold 实际执行及报告一致性验收通过**。

## 1. 原始材料

- 原始报告：[m1_d3_postgres_gold79_server.json](results/m1_d3_postgres_gold79_server.json)，642649字节。
- Run ID：`e58c596bd7014a68b4f0143cc8602020`。
- 报告 SHA256：`269e0baf37301eb4dea93b3ce1b77e4c330dbf2642bd3dfab019a752732c28e6`。
- Manifest fingerprint：`ed227d11d48357160bb898862330aeb32928870df0b2e6c7d949a6bc736bc181`。
- 逐题核对记录：[m1_d3_postgres_gold79_server_review.json](results/m1_d3_postgres_gold79_server_review.json)。

原始报告、冻结原题集、逐题离线审查 JSON 及已有同步包均保持原值；本次独立保存服务器报告核对记录。离线审查中的 pending 状态属于制作时记录，实际执行验收进度以本文为准。

## 2. 范围与版本

79题顺序与交付的 `m1_d3_postgres_gold79.json` 完全一致，无缺题、重复或新增。组成是classic49 + 扩展30，业务分布为增长27、渠道26、内容26。`scope=all` 与传入79题清单一起生效，本次没有运行全部430题。

逐项重算并一致：

| 项目 | 核对结果 |
|---|---|
| 79题内容版本 | `461a75362007953da0d028fc44b35b4252891a558f6a26d909e711effd0266f4`，与本地79题结构化内容一致 |
| Gold选择版本/摘要 | version=1；摘要 `0a2af5e3834b4a7f1cdd6fcbf0420ef1b010c5f0fd23e15fa8085178327158d0`，79题显式选择全部一致 |
| 应用代码/Skill文件 | `ffedff687c45d6aadb55f64740f696b3f9733e02f2044ede8e58b587512e106e`，与本地交付代码一致 |
| 评分器核心文件 | `b2a09a38265d1499a53a0c4869de51c56b42d6b4503e3c758522b0daae617f9f`，与本地一致 |
| evaluation代码 | `843a89c9e3c63534201611b23e7c4adf8ce55e8994032432844fa74b1d0bd45c`，与本地一致 |
| 完整manifest指纹 | 从报告实际字段重算，完全一致 |

题集内容版本是选中79题的规范化 JSON 摘要；正式430题文件字节 SHA256 是 `16fe651be76e5eacde7eb30ac6b1880eb4fcb0d22eebb7b347142f26e488a34f`，两者对象不同。复核冻结题集后，原430题SQL和评分字段仍不变，351题未覆盖行字节仍不变。

## 3. 来源、执行与权限

| 来源项 | 报告实际值 |
|---|---|
| logical_database_id | short_video_ops |
| source_id | short_video_ops_postgres |
| backend / dialect | postgresql / postgres |
| prompt_dialect | PostgreSQL |
| physical_schema | askdata_ops |
| data_version | `882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1` |
| catalog_version | `94a801805965a90aa6ae015f28af196f88f72c1d887319dd1896a2973eaaa288` |
| physical_schema_version | `b12bffb567ee4aa3ca126d48154ddfb36c1721d1af7c6e8b65efc4780615a817` |

三个版本与已验收C3材料一致；79题 trace 中的 source_identity 均与 run_manifest 一致。配置记录 data_backend=postgresql、正确 source_id、workers=1、时间字段补充关闭。

逐题同时检查顶层指标、嵌套指标和 trace：

- 79题 `generated_sql` / `gold_sql` / trace SQL 与本地题集 PostgreSQL 变体全文一致。
- 79题 `gold_dialect=postgres`，选择键均为 `gold_sql_by_dialect.postgres`。
- 79题 `gold_result_source=execution`、`gold_result_generated=true`；缓存命中0、静态结果替代0、DuckDB回退0。
- 79题 `comparison_target=expected_rows`，由实际Gold结果对照冻结的独立预期行，而非把本次结果与自身比较。
- 每题SQL执行成功、宽松正确、严格正确、原始列名匹配均为true。三个位置的行数完全一致，并与冻结预期行数相同。
- 每题场景、问题、Gold字段、run_id、trace_id 一致；无错误对象或 trace 错误。
- 79题应用权限检查通过，demo_growth_ops / demo_channel_ops / demo_content_ops 与题目场景对应；无权限阻断。
- Gold缓存保存路径全部处于 `evaluation/cache/gold_results/short_video_ops_postgres/`，文件名与题号哈希一致。存在 cache_path 表示本次执行后保存缓存，不表示本次命中缓存。

该版本 `build_run_manifest` 要求 PostgreSQL runtime 的实时校验已通过且数据/catalog/物理结构版本一致，才能生成清单；核对到的应用和评分器版本与本地相同。本报告没有完整实时校验明细，本文没有重新连接数据库，也不把C3历史明细冒充本次实时明细。

## 4. 汇总复核

使用本地同版评分器的 `summarize()` 从全部79条记录重算，汇总对象与原报告逐字段一致。

| 指标 | 结果 |
|---|---:|
| SQL成功 | 79/79 |
| 宽松结果正确 | 79/79 |
| 严格结果正确 | 79/79 |
| 原始列名匹配 | 79/79 |
| 未评分/错误/超时/连接错误/澄清 | 全部0 |
| 模型请求/重试/模型超时/模型连接错误 | 全部0 |
| 平均execution_ms | 2653.773 |
| P95 execution_ms | 2750.066 |

schema_recall/precision 为 null、路由为空、工具调用计数0均符合Gold直接执行模式；这不是检索、模型Agent或MCP服务入口验收。执行时间覆盖执行器只读检查、受保护事务、查询、取数及结果归一化，不是 PostgreSQL 原生SQL耗时，不能直接用它判定数据库查询性能。

## 5. 重点边界核对

下表核对实际报告中的SQL、行数及严格通过记录。**完整结果行没有保存在这份报告中**，不能从报告直接读取返回的每个NULL、日期或标题。所述预期边界来自已冻结正式题集，而不是重新读取的服务器结果值。

| 题号 | 核对重点 | 实际报告行数 | 严格评分 |
|---|---|---:|---|
| GROWTH_OPS-051 | 一月注册cohort；注册ID分母、NULLIF、两处非零激活判断 | 10 | 通过 |
| GROWTH_OPS-075 | 五月cohort；激活数/注册数及固定月份 | 1 | 通过 |
| GROWTH_OPS-076 | 1日留存、数值标志与观测行分母 | 10 | 通过 |
| GROWTH_OPS-100 | 五月iOS人均播放；DISTINCT用户分母 | 1 | 通过 |
| GROWTH_OPS-126 | push送达/点击/召回率；各标志与共用分母 | 1 | 通过 |
| GROWTH_OPS-148/149/150 | 三/四/五月actual与同月目标；先减目标再舍入gap | 各10 | 全通过 |
| CHANNEL_OPS-025 | 五个月环比、LAG、零分母保护；预期一月mom为NULL | 5 | 通过 |
| CHANNEL_OPS-051 | 转化率/CPA不同分母及不同舍入精度 | 4 | 通过 |
| CHANNEL_OPS-136 | 一月CPA与目标gap，NULLIF及升序NULL末尾 | 4 | 通过 |
| CONTENT_OPS-036 | 一月有效互动，按DATE聚合；预期17日记录 | 17 | 通过 |
| CONTENT_OPS-025 | 体育标题Top 10，原边界值8和12项已批准候选 | 10 | 通过 |

全题SQL哈希、数据版本、冻结评分字段均一致，未通过修改别名/预期行/并列宽容度提高分数。上述结论基于服务器执行记录与同版严格评分；**本地没有使用服务器完整返回行独立重新评分**。

## 6. 验收结论与后续范围

本轮79题显式PostgreSQL Gold已实际执行，服务器报告一致性核对通过，可作为首轮D3正式基线留存。

后续跨后端逐值比较需要另取同次运行的Gold缓存结果，核对其来源/SQL/数据版本后再比较NULL、数值、日期和具体并列成员。无需仅为本次报告核对重新请求模型。

原始79题报告并未包含本次服务器14/441项单元测试日志；这些数字只引用已有本地测试结果，不能写成服务器441项测试已单独确认。

剩余351题变体、D4索引/缓存/报告来源隔离及独立跨后端比较、PostgreSQL live/E2E均未由本次79题Gold验收覆盖。接下来继续D3剩余题和D4工作，之后进入E阶段。
