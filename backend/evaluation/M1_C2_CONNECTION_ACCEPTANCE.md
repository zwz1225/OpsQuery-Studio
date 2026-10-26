# M1 C2：PostgreSQL 连接管理与生命周期

日期：2026-10-10。

## 1. 实施内容

新增共享的 `PostgresConnectionManager`，供下一阶段执行器和受控元数据读取模块使用。配置沿用 C1；默认应用继续使用 DuckDB。此阶段的连接管理尚未接入 PostgreSQL 应用 runtime。

| 要求 | 实现 |
|---|---|
| 驱动及依赖 | `psycopg[binary]==3.2.13`、`psycopg-pool==3.2.8`；显式创建管理器时检查版本 |
| 有界同步连接池 | min/max、等待时间、最大等待请求数取自 C1；`open=False`，显式打开并等待初始连接就绪 |
| 明确事务 | 每次 `transaction()` 开启只读、REPEATABLE READ 事务；autocommit 连接避免额外隐式外层事务 |
| 事务设置 | 局部设置 `pg_catalog,askdata_ops`、UTC、ISO 日期格式、浮点输出精度及 SQL/锁等待超时 |
| 故障清理 | 事务异常回滚；归还前同步 RESET ROLE/RESET ALL 并确认 IDLE；回滚或清理失败则关闭、丢弃连接 |
| 生命周期 | 所有者负责关闭；上下文管理器和 finally 均支持；重复 close 安全，关闭后禁止借用和重开 |
| 诊断脱敏 | 公共错误只有受控类别和 SQLSTATE；驱动连接错误及连接池日志中的连接 repr 隐去连接参数 |

连接建立时核对实际数据库、登录角色、PostgreSQL 16、UTF8/UTC/C、角色特权、数据库/schema 权限、schema 所有者及导入角色成员关系。该检查只证明连接身份与基础权限；41 表实际元数据、全量数据版本和完整 catalog 由后续步骤核验。

池关闭后，等待中的借用者被唤醒失败；已经借出的连接在归还时关闭。服务关闭前应先结束正在执行的操作，close 本身不会强行取消所有已借出的查询。依据：[Psycopg 连接池 API](https://www.psycopg.org/psycopg3/docs/api/pool.html)、[事务管理](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)。实现同时核对了本地安装的 3.2.8 API。

连接模块接受内部受信任 SQL。应用 SQL AST、函数和表权限策略仍由后续执行器实施；只读事务不能代替这些策略。

## 2. 所有权与使用方式

```python
with PostgresConnectionManager(config) as connections:
    with connections.transaction() as conn:
        row = conn.execute("SELECT 1").fetchone()
```

未来 executor 和 metadata 共用同一个 manager，分别借用事务，不能在借用结束后保留连接、改变事务边界或分别关闭共享池。runtime/executor 所有者统一调用 close。

现有 `app/main.py` 已有 lifespan finally 调用 service.close，service 按 runtime 所有权关闭资源。C2 提供可接入此关闭链的模块和命令生命周期，完整 PostgreSQL runtime 装配将在后续完成。

## 3. 本地验证与服务器验收边界

本地新增 31 项测试覆盖显式开启、事务局部设置、成功提交、SQL/客户端异常回滚、超时分类、吞掉 SQL 异常后的事务检查、回滚/清理失败丢弃、取消、关闭期间归还和脱敏。使用真实安装的连接池加内存连接替身验证容量、排队上限及等待超时；没有连接真实 PostgreSQL。完整回归共 353 项。

本地执行记录见 [m1_c2_implementation_local.json](results/m1_c2_implementation_local.json)。服务器已独立执行真实 PostgreSQL 验收，下载的报告经 20 项一致性核对通过，详见下方归档结论。

## 4. 服务器操作

将根目录同步包上传到服务器项目根目录，确认文件已上传后执行：

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M1_C2_连接管理同步包_20261010.zip
cd backend
python -m pip install -r requirements-postgres.txt
python -m unittest discover -s tests -p 'test_postgres_connections.py' -v
```

保留服务器 C1 已配置的 `.env` 和原始 M1 B 导入/验证报告，保持 `DATA_BACKEND=duckdb`、`DATA_SOURCE_ID=short_video_ops_duckdb`。PostgreSQL 用户实例须已启动。然后执行：

```bash
python -u -m scripts.check_m1_c2_postgres_connections \
  --output evaluation/results/m1_c2_postgres_connections_server.json
```

该输出使用独占创建，拒绝覆盖历史报告。若第一次失败，排除原因后改为新的文件名，例如 `m1_c2_postgres_connections_server_v2.json`。

脚本执行九项真实检查：

1. 实际登录、只读事务、search_path、UTC、隔离级别和超时设置。
2. 正常查询。
3. 除零失败、回滚和下一次查询恢复。
4. 建表被拒绝及连接恢复；即使意外允许建表，探针也强制回滚。
5. 局部时区设置不泄漏到下一操作。
6. 重复关闭和关闭后拒绝借用。
7. 独立诊断池内 1 秒 SQL 超时及恢复。
8. 独立诊断池只允许 1 个连接、1 个等待请求；额外请求立即拒绝，等待者超时，随后查询恢复。
9. 关闭期间活动连接可完成事务，并在归还时实际关闭。

诊断池配置只存在于脚本进程，不改 `.env`。没有模型请求、持久化业务写入、SQL 评分或应用后端切换。

## 5. 验收字段与下一步

| 字段 | 预期 |
|---|---|
| run_status / errors | complete / [] |
| application_backend | duckdb |
| postgresql_connected | true |
| connection_lifecycle_verified | true |
| check_pass_count | 9 |
| main_manager_final.state / probe_manager_final.state | closed / closed |
| 两个 manager 的 active_operation_count | 0 |
| live_target_verified / runtime_available | false / false |
| catalog_version | null |
| new_model_request_count | 0 |

## 6. 服务器报告归档结论

2026-10-10 已核对 [m1_c2_postgres_connections_server.json](results/m1_c2_postgres_connections_server.json)，九项真实检查全部通过，`run_status=complete`、`errors=[]`、`connection_lifecycle_verified=true`。运行时间为 UTC 01:51:27.449904 至 01:51:30.635861，耗时 3.185957 秒。

实际连接为 PostgreSQL 16.15 / `askdata_m1_test` / `askdata_readonly`，UTF8、UTC；只读事务、受控 search_path、REPEATABLE READ、120000 ms SQL 超时及 5000 ms 锁超时均符合配置。除零失败为 `22012`，写入拒绝为 `25006`，独立诊断池 SQL 超时为 `57014`，每次失败后均完成恢复。

配置与 C1 服务器报告一致，已记录的数据版本、物理结构版本以及 M1 B 两份原始报告的 SHA256 经本地重新核对一致。原始服务器报告未修改，其 SHA256 为：

```text
f8fd6a37aae2c2e8536c51199153e9572156bc7e12489855c05c45604777835e
```

独立复核记录见 [m1_c2_postgres_server_archive_review.json](results/m1_c2_postgres_server_archive_review.json)。

报告中的统计按以下含义解释：

- 诊断池 `requests_errors=2`：主动触发的队列满和等待超时，属于预期验证，整体 `errors` 仍为空。
- 主池配置为 1—4 个连接、16 个等待请求、10 秒等待；独立诊断池使用 1 个连接、1 个等待请求、2 秒等待及 1 秒 SQL 超时验证机制，不改主配置。
- 两个管理器最终 `state=closed`、`active_operation_count=0`、`pool_available=0`、`requests_waiting=0`。该连接池版本关闭时保留 `pool_size` 的内部计数，因此这里的 `pool_size=1` 不表示关闭后仍有一个可用连接；活动连接归还后实际关闭也已通过探针断言。
- 此次 `25006` 证明只读事务阻止了写入；M1 B 的 `42501` 是独立账号权限拒绝证据。完整当前表级 ACL 与数据版本仍需下一阶段核验。

**M1 C2：连接管理与生命周期验收通过。** 下一步实现受控实时元数据/数据版本核验，随后实现 PostgreSQL 执行器、catalog/profile 与 runtime 装配。`live_target_verified=false`、`catalog_version=null`、`runtime_available=false` 是当前阶段的正确状态，应用继续使用 DuckDB。
