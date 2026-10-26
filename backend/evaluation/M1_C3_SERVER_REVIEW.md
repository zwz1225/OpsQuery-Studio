# M1 C3 服务器报告审查与验收结论

审查日期：2026-10-10。

## 1. 结论与材料

**M1 C3：受控实时元数据、来源校验、PostgreSQL 执行器、动态 profile 和统一 runtime 的隔离验收通过。**

- 原始报告：[m1_c3_postgres_runtime_server_v2.json](results/m1_c3_postgres_runtime_server_v2.json)，81,217 字节，保留原始内容。
- 独立审查记录：[m1_c3_postgres_server_archive_review.json](results/m1_c3_postgres_server_archive_review.json)，36 项本地材料审查全部通过。
- 原始报告 SHA256：`2cd9a7b9ad94300b36a9494b22a76e28db2d64a91c8d23835c96e982e6ea7166`。
- 服务器运行：2026-10-10 14:11:46 至 14:12:30（北京时间），43.715036 秒。
- 本地审查未连接远程数据库、未请求模型、未改变原始报告。

此结论适用于当前 `askdata_m1_test.askdata_ops` 隔离数据源。默认应用仍为 DuckDB。M1 D 的模型提示词方言、PostgreSQL Gold SQL 变体、评测与缓存来源隔离、正式 live/E2E 回归尚未验收。

## 2. 来源与结构

| 核对内容 | 结果 |
|---|---|
| run_status / errors | complete / [] |
| 服务器检查 | 24 项全部通过，名称无重复或缺失 |
| 来源 | short_video_ops_postgres；logical_database_id=short_video_ops |
| 后端与方言 | postgresql / postgres / PostgreSQL |
| 物理位置与账号 | askdata_m1_test / askdata_ops / askdata_readonly |
| 实际连接 | PostgreSQL 16.15，UTF8，UTC，身份校验通过 |
| 表、字段、行与业务关系 | 41 / 276 / 722732 / 53 |
| 全量类型化行匹配 | 报告记录 41 张表全部匹配 |
| 表级 / 列级只读权限校验 | 报告记录 41 / 41 |
| 数据库与 schema 权限 | CONNECT、受控 schema USAGE 允许；数据库 CREATE/TEMP、schema CREATE、public CREATE 禁止 |
| 默认应用 | duckdb / short_video_ops_duckdb |
| 新模型请求 | 0 |

完整比较了报告中 41 张表的表名、全部字段名称/顺序、PostgreSQL 类型、not_null、identity/generated、默认值标记和主键，与已验收 M1 B 验证材料一致。

目标数据版本与配置、M1 B、实时验证、SourceIdentity 一致：

```text
882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1
```

从报告的完整表结构重新计算物理结构摘要，结果一致：

```text
b12bffb567ee4aa3ca126d48154ddfb36c1721d1af7c6e8b65efc4780615a817
```

使用已验收业务标注和报告中的 PostgreSQL 字段结构，重新装配 catalog；核对 53 条关系的字段端点，版本与顶层、实时验证和 SourceIdentity 三处一致：

```text
94a801805965a90aa6ae015f28af196f88f72c1d887319dd1896a2973eaaa288
```

核对 M1 B 原始导入/验证文件 SHA256，分别匹配报告中的历史证据引用。C3 配置与已验收 C1/C2 配置一致：连接超时 10 秒，statement_timeout 120000 ms，lock_timeout 5000 ms，池容量 1..4，等待 10 秒，最多 16 个等待请求。

## 3. 24 项服务器检查

| 序号 | 检查 | 审查结果 |
|---|---|---|
| 1 | qualified_table_count | 限定 schema 的 COUNT 查询成功 |
| 2 | cte_query | 只读 CTE 成功 |
| 3 | postgres_month_format | PostgreSQL 月份函数成功，8 行 |
| 4 | date_and_null_normalization | 日期、NULL、NUMERIC 输出断言通过 |
| 5 | empty_result | 成功返回 0 行，保留 user_id 列，无错误、无截断 |
| 6 | preview_200_limit | 返回 200 行，truncated=true |
| 7 | scoring_10000_limit | 返回 10000 行，truncated=true |
| 8 | sql_failure_redaction | 预期除零失败，只暴露安全错误与 SQLSTATE 22012 |
| 9 | query_recovery | 除零后查询恢复 |
| 10 | wrong_schema | 跨 schema 查询按预期拒绝 |
| 11 | unknown_table | 未知表按预期拒绝 |
| 12 | projection_star | SELECT * 按预期拒绝 |
| 13 | multiple_statements | 多语句按预期拒绝 |
| 14 | write_statement | DELETE 按预期拒绝 |
| 15 | write_cte | 写入 CTE 按预期拒绝 |
| 16 | select_into | SELECT INTO 按预期拒绝 |
| 17 | locking_select | FOR UPDATE 按预期拒绝 |
| 18 | side_effect_function | set_config 按预期拒绝 |
| 19 | server_file_function | pg_read_file 按预期拒绝 |
| 20 | application_role_denied | 应用角色无权访问 contents，按预期拒绝 |
| 21 | injected_content_guard_mismatch | 预期指纹不匹配时返回 source_content_changed |
| 22 | guard_restore_recovery | 恢复预期指纹后查询成功 |
| 23 | verified_live_profile | 日期、文本、数值 profile 校验通过 |
| 24 | runtime_owner_closes_shared_pool | runtime 所有者关闭共享连接池 |

所有 SQL 项目的 expected_success 与 actual_success 一致。负向检查中的错误属于预期行为，不能作为 C3 执行失败计数。

最后两项未打印独立进度行，但已存在于原始 JSON 的 checks 中。第 21 项仅注入进程内预期指纹差异，报告明确 `target_data_modified=false`；本次未进行数据库数据修改实验。

## 4. profile 独立核对

本地 CSV 的完整 source_data_version 与已验收 M1 B 快照匹配；据此独立读取参考 CSV，比较 profile 样本和统计值。

| 字段 | 报告及本地参考结果 |
|---|---|
| user_registrations.registered_at | 5 个 ISO 时间样本一致；范围 2026-01-01 00:02:15 至 2026-08-28 23:59:05 |
| user_registrations.user_id | 样本 U0000001 至 U0000005 一致；12000 个不同值 |
| contents.duration_seconds | 样本 8、9、10、11、12 一致；最小 8、最大 180、平均 94.10 秒 |

## 5. 生命周期与耗时

- 最终连接管理器 `state=closed`。
- active_operation_count、requests_waiting、pool_available 均为 0。
- 依赖版本 Psycopg 3.2.13、psycopg-pool 3.2.8，与 C2 一致。
- 池请求次数 14，与一次启动验证、11 次进入数据库的 SQL 操作、两次 profile 操作一致；其他策略拒绝项在连接前拒绝。
- `pool_size=1` 为关闭后保留的池计数，结合 state=closed 阅读，不表示仍有一个可用连接。
- 11 次进入数据库的 SQL 操作耗时 2613.956–2732.202 ms，平均 2638.415 ms；包括每次全表结构/ACL/内容核查，属于执行器阶段耗时，不是模型耗时或端到端响应时间。

recorded_source 和 manager_final 中的 live_target_verified/runtime_available=false 表示这两个模块不负责完整 runtime 验证；顶层和 live_verification 的 true 表示本次命令中已成功验证并装配。命令结束后池已关闭。

## 6. 报告补丁与证据边界

本报告没有 `report_write_status`，与补丁前的报告格式一致；仅凭 JSON 无法证明服务器具体脚本版本或补丁部署状态。原始文件本次有效保存、解析完整、24 项通过，因此该收尾项不阻断 C3 runtime 验收。应核实服务器的报告写入修复补丁是否同步，并补齐 8 项存储异常测试；无需只为缺少该字段重复全量 C3 验证。

报告未保存逐表实时行摘要、原始 ACL/索引查询结果或业务 SQL 的实际行值。这些内容由服务器脚本的断言验证；本地材料审查可重算结构和 catalog 摘要，核对已记录检查结果，并独立比较 profile，不能代替新的实时数据库验证。

后续顺序：确认报告补丁同步与专项测试；然后进入 M1 D 的方言、Gold 变体和评测来源隔离设计，继续保持默认 DuckDB，直至 PostgreSQL 正式回归验收通过。
