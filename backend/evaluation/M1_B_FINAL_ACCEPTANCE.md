# M1 B 最终验收：隔离 PostgreSQL 数据准备

日期：2026-10-08。

## 1. 验收结论

**M1 B 通过验收。** 用户在服务器完成统一事务导入及提交后只读独立验证；下载的两个报告已与冻结源清单逐项核对，独立归档审查 `status=passed`、`errors=[]`。

验收范围是隔离测试库 `askdata_m1_test`、业务 schema `askdata_ops` 的数据准备与数据库授权。应用仍使用 DuckDB，PostgreSQL 应用执行器、元数据与方言适配属于后续 M1 C/D，本结论不覆盖这些功能。

## 2. 材料与关联

- [服务器导入报告](results/m1_b_postgres_import_server.json)：`complete / committed / target_data_verified=true`，使用 `askdata_import`。
- [服务器独立验证报告](results/m1_b_postgres_validation_server.json)：`complete / completed / target_data_verified=true`，使用 `askdata_readonly`。
- [独立离线归档审查](results/m1_b_postgres_server_archive_review.json)：通过，生成脚本为 [audit_m1_b_postgres_archive.py](../scripts/audit_m1_b_postgres_archive.py)。
- [源数据准备记录](M1_B_PREPARATION.md)、[实施验收说明](M1_B_IMPORT_ACCEPTANCE.md)和[本地实施测试记录](results/m1_b_import_implementation_local.json)。

导入报告 SHA256：`215c9ce2e1ae53e140b7c17e4222d8eae29dcce7dd423ab03f74918d13032ce9`，与独立验证报告的 `import_record.sha256` 完全相同。验证在导入完成后开始，属于正常提交后的核对，不是未知提交状态的恢复。

导入与独立验证的目标版本一致，按两份报告实际列结构、主键、行数与行内容摘要重新计算版本也一致：

```text
882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1
```

源数据版本保持 M1 A 已验收值 `d23481ffef242c04bc2adcf1f5a7082ec65ce392d30a48b16e7ccb0b3a3809b8`；规范导入规格与三个源准备文件摘要均吻合，43 个当前本地源文件摘要与冻结材料一致。源版本和目标版本采用不同摘要范围，应分别保存。

## 3. 数据与环境结果

| 检查 | 结果 |
|---|---|
| 数据库环境 | PostgreSQL 16.15、UTF8、UTC、libc/C；目标库/schema 与来源身份正确 |
| COPY | 41 表逐表行数、发送 CSV SHA256、字节数一致；总 51,894,889 字节 |
| 表 / 字段 / 行 | 41 / 276 / 722,732 |
| 实际列定义 | 名称、顺序、类型、可空性、identity/generated/default 标记符合清单 |
| 主键 | 41 表定义符合清单，无 NULL 主键、无重复主键组 |
| 列统计 | NULL、非空 distinct、MIN/MAX、数字 SUM/AVG 按原规格逐项通过 |
| 完整行内容 | 41 个类型化行多重集合摘要与源清单一致，导入前提交内与提交后独立读取均通过 |
| 业务关系 | 53 条非空子字段均有匹配父记录，孤立记录为 0；本阶段未将业务关系自动建成物理外键 |
| 时间字段 | 21 个 TIMESTAMP 的值与源摘要一致；本批源值均无非零小数秒。微秒损失另有本地合成测试，本批真实数据不构成非零微秒样本验收 |
| 错误 / 新模型请求 | 0 / 0 |

五个含 NULL 字段已单独核对：

| 表.字段 | NULL 数量 |
|---|---:|
| channel_attributions.ad_campaign_id | 177 |
| channel_conversion_events.ad_campaign_id | 306 |
| recall_results.returned_at | 8,255 |
| user_activations.activated_at | 3,022 |
| user_activations.activation_seconds | 3,022 |

服务器报告运行时间：导入含提交前完整验证约 20.887 秒；提交后独立验证含权限探测约 12.926 秒。这是整段命令用时，不是应用查询延迟或性能承诺。

## 4. 权限与状态说明

- 全部 41 表的 SELECT 为 true；INSERT、UPDATE、DELETE、TRUNCATE、REFERENCES、TRIGGER 为 false。只读账号可连接目标库、使用业务 schema，无数据库 CREATE/TEMP、业务 schema CREATE 或 public CREATE。
- 在一张代表表上实际探测 INSERT/UPDATE/DELETE，并在业务 schema 探测 CREATE TABLE，四项均返回权限拒绝 SQLSTATE `42501`。探测使用可写事务，验证数据库授权本身；并非仅依赖只读事务错误。
- 四项探测回滚完成，连接恢复成功。全部表授权检查与代表表实际探测是不同范围的证据。
- 验证报告 `commit_state=not_started` 正常，验证没有提交业务写入。
- 导入报告 `readonly_independent_validation_pending=true` 是导入完成时的历史状态。后续独立验证已补齐，归档审查标明该标记已被后续证据满足；原报告保留不改写。

## 5. 后续边界

本次本地操作为服务器报告的离线核对，没有重新连接 PostgreSQL、执行 SQL 或修改两个原始报告。目标版本表示已验证快照；目标数据或 schema 后续改变时必须重新验证，不能将旧记录视为实时状态证明。

下一步进入 **M1 C：PostgreSQL 执行器及受控元数据适配**，使用 `askdata_readonly`，围绕同一来源身份实现连接生命周期、物理 schema 限定、catalog/profile、只读执行、结果归一化和错误处理；随后在 M1 D 传递方言并隔离索引、Gold 和运行报告。
