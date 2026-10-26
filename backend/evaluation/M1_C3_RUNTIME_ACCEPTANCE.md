# M1 C3：受控实时元数据、来源校验与 PostgreSQL runtime

日期：2026-10-10。

## 1. 当前产出与验收边界

已实现受控实时元数据读取、来源校验、PostgreSQL 执行器、动态 profile 和统一 runtime 装配。新增 26 项测试，全套 379 项回归通过。2026-10-10 下载的服务器 `_v2` 报告包含完整 24 项通过结果，另经 36 项本地材料审查通过，当前隔离数据源的 C3 验收通过。详见 [服务器审查结论](M1_C3_SERVER_REVIEW.md) 和 [独立审查记录](results/m1_c3_postgres_server_archive_review.json)。报告写入修复补丁的服务器同步状态仍需确认；M1 D 的方言与正式 live/E2E 回归尚未验收。

默认应用继续使用 DuckDB。服务器 C3 脚本只在自己的进程中选择 PostgreSQL，不修改 `.env`，不请求模型。后续仍需 M1 D 的提示词/方言、PostgreSQL Gold 变体及评测隔离核验，再开展正式 live/E2E 验收。

| 文件 | 作用 |
|---|---|
| `app/datasources/row_digest.py` | 提取 M1 B 类型化行摘要，保持既有时间、浮点、NULL 编码及多重集合算法 |
| `scripts/preflight_m1_b_source.py` | 复用相同摘要函数，保留原准备与导入材料 |
| `app/datasources/postgres_metadata.py` | 受控元数据、权限、全量数据验证、业务标注合并及动态 profile |
| `app/querying/postgres_engine.py` | PostgreSQL 只读执行器、服务端游标、有界取数与安全错误 |
| `app/datasources/sql_policy.py` | PostgreSQL schema 限定、函数白名单、写入 CTE/SELECT INTO/锁定查询拒绝；DuckDB 策略保持兼容 |
| `app/datasources/runtime.py` | 显式 PostgreSQL 装配；验证失败关闭连接池并终止；默认 DuckDB 分支继续使用 |
| `app/config.py` | 公共实施阶段标记更新，参数及默认后端保持原值 |
| `scripts/check_m1_c3_postgres_runtime.py` | 服务器独立验收，输出新 JSON |

测试覆盖来源变化、表/列权限扩大、结构与索引变化、同题数但内容变化、失败清理、未知 profile 字段、非法 SQL 连接前拒绝、合法 CTE/分析函数、200/10000 行限制、空结果、重复列名和 JSON 类型转换。结果见 [本地实施记录](results/m1_c3_implementation_local.json)。

## 2. 实时读取与来源验证

元数据查询全部限定 `askdata_m1_test.askdata_ops`，使用参数绑定和经过验证的标识符引用。此版本仅接受 M1 B 已验收的 41 个普通持久表；分区、继承、视图、物化视图、外部表、序列以及受控 schema 中额外的函数/操作符均拒绝。

核对内容包括：

1. 当前账号、数据库、PostgreSQL 16、UTF8、UTC、C 排序/字符规则、schema 所有者、账号特权与角色成员关系。
2. 数据库 CONNECT/CREATE/TEMP、受控 schema USAGE/CREATE 和 public CREATE。
3. 每表 SELECT 与 INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER 权限；补查列级 INSERT/UPDATE/REFERENCES，避免只查表 ACL 遗漏列级写权限。
4. 表集合、所有者、RLS、列顺序、物理类型、可空性、默认值、identity/generated 属性和列排序规则。
5. 主键列、约束验证/延迟属性，以及主键索引的 primary/unique/valid/ready 状态；额外约束和索引要求重新审查。
6. 服务端游标逐批读取全部行，按原 M1 B 类型化算法重新计算每表摘要与最终目标版本；不以行数或抽样替代完整数据验证。

启动时核对 41 表、276 字段、722,732 行的真实内容，目标版本须仍为：

```text
882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1
```

已记录物理结构摘要须仍为：

```text
b12bffb567ee4aa3ca126d48154ddfb36c1721d1af7c6e8b65efc4780615a817
```

业务标注从 `_schema.json` 读取并核对已验收 catalog 摘要；保持 logical table/field ID、业务标签和 53 个关系端点，合并实际 PostgreSQL 类型、nullable 与 physical_schema。业务关系保留其标注含义，不声称数据库新增了 53 条外键约束。完整行摘要匹配保证关系所依赖的原始值仍与 M1 B 相同。

PostgreSQL catalog 版本包含真实后端/schema/类型信息，因此与原 DuckDB catalog 版本区分。完成上述验证后才生成完整 SourceIdentity 并发布 runtime。PostgreSQL runtime 数据查询不加载 CSV；它需要已验收报告和业务标注文件。

## 3. 启动后变化与事务一致性

启动验证通过后，在同一 REPEATABLE READ 事务中计算所有表的服务端内容指纹：对完整列值的 PostgreSQL ROW 文本做 SHA256，排序全部行摘要再做多重集合 SHA256，保留重复行和 NULL 差别。该指纹只作为运行期变化检测，不替代 M1 B 目标数据版本。

每次 SQL 执行或 profile 操作在自己的只读事务中：

1. 取得 ACCESS SHARE 表锁，保护操作期间的表结构。
2. 重查结构、权限和环境。
3. 重算所有表完整内容指纹，与已验证快照比较。
4. 在同一事务中执行查询/profile 并消费有界结果。

来源变化返回明确失败，不生成成功空结果，也不自动使用旧数据版本。事务快照保证该次查询看到与该次内容校验一致的数据；下一操作重新核验。依据：[PostgreSQL REPEATABLE READ](https://www.postgresql.org/docs/16/transaction-iso.html)、[PostgreSQL SHA256](https://www.postgresql.org/docs/16/functions-binarystring.html)。

此策略每次操作都会扫描所有受控表并检查元数据，增加查询开销。服务器报告记录执行耗时；在确认固定数据版本的机制前，不使用统计计数或缓存时间窗口跳过校验。该版本面向当前隔离的 M1 验收数据集，后续扩大数据量时需另行设计经过验证的版本发布机制。

## 4. SQL、结果与资源边界

- 只允许单条 SELECT/WITH；拒绝写入 CTE、SELECT INTO、FOR UPDATE/SHARE、多语句、SELECT *、跨 schema/catalog、未知表及应用角色无权访问的表。
- 仅允许已列出的分析函数；拒绝 set_config、文件读取、序列、锁等未授权函数和自定义对象类型转换。受控 schema 额外函数/操作符也触发来源拒绝。
- 使用 named/server-side cursor，预览取 201 行返回最多 200 行，评分取 10001 行返回最多 10000 行，按额外行设置 truncated；不先 fetchall 再切片。依据：[Psycopg 服务端游标](https://www.psycopg.org/psycopg3/docs/advanced/cursors.html)。
- 日期/时间转 ISO，NULL 保留 None，Decimal 按现有数值输出契约转 float；非有限值和重复结果列名返回明确失败。
- metadata 与 executor 共用 C2 manager；executor/runtime 所有者关闭连接池，metadata 不单独关闭。装配失败、命令结束均关闭已拥有的资源。

## 5. 服务器操作

将 `M1_C3_实时来源与执行器同步包_20261010.zip` 上传到项目根目录，确认文件存在后执行：

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M1_C3_实时来源与执行器同步包_20261010.zip
cd backend
python -m pip install -r requirements-postgres.txt
python -m unittest discover -s tests -p 'test_postgres_runtime.py' -v
```

预期 26 项专项测试通过。保留 C1/C2 已配置的 `PG_` 参数、原始 M1 B 报告和原业务 `_schema.json`。保持默认应用配置为 DuckDB，然后运行：

```bash
python -u -m scripts.check_m1_c3_postgres_runtime \
  --output evaluation/results/m1_c3_postgres_runtime_server.json
```

脚本会打印逐表全量摘要验证进度。启动校验和后续来源检查需要扫描数据，请等待进程结束。输出为独立新文件，拒绝覆盖；失败后修正原因，重跑时使用 `_v2.json` 等新的文件名。

## 6. 预期服务器结果

| 字段 | 预期 |
|---|---|
| run_status / errors | complete / [] |
| check_pass_count | 24 |
| application_backend / application_source_id | duckdb / short_video_ops_duckdb |
| source_identity.backend / dialect / physical_schema | postgresql / postgres / askdata_ops |
| postgresql_connected / live_target_verified / runtime_available | true / true / true |
| catalog_version | 非空，与 source_identity.catalog_version 一致 |
| live_verification.table_count / field_count / row_count / relation_count | 41 / 276 / 722732 / 53 |
| live_verification.full_typed_row_match_count | 41 |
| live_verification.readonly_table_acl_match_count / readonly_column_acl_match_count | 41 / 41 |
| manager_final.state / active_operation_count | closed / 0 |
| new_model_request_count | 0 |

24 项检查涵盖 native PostgreSQL COUNT、CTE、月份函数、日期/NULL/Decimal 输出、空结果、200/10000 行限额、SQL 失败与恢复、十类非法 SQL、应用角色拒绝、预期内容指纹注入不匹配与恢复、动态日期/文本/数值 profile、共享池关闭。

指纹不匹配探针只在脚本进程中临时改变预期摘要，不修改 PostgreSQL；报告明确记录 `injected_expected_guard_mismatch=true`、`target_data_modified=false`。实际数据修改后的失败路径由本地测试替身覆盖，这次服务器命令不对数据库执行变更实验。

顶层 `runtime_available=true` 表示脚本成功装配并验证过 PostgreSQL runtime；结束时池已关闭，不表示当前默认服务已经切换到 PostgreSQL。连接管理器自身的 `live_target_verified/runtime_available=false` 继续表示 C2 模块不负责完整数据/catalog 验证，须结合顶层与 `live_verification` 阅读。

完成后下载 `evaluation/results/m1_c3_postgres_runtime_server.json` 至同名本地目录，核对原始报告后再确认完整 M1 C 验收，随后继续 M1 D。
