# M2 B 独立初始化、受控导入与目标一致性验收

交付日期：2026-10-16。前置证据是已经核对通过的服务器预检 v2，以及 `m2_b_source_server_20261015/` 中的三份来源报告。

本次实现三个服务器阶段和一个离线审计工具。代码交付不代表远程数据库已经初始化、导入或验收；最终结论以服务器新报告为准。应用仍使用原有配置，本次工具不读取应用 `.env`、M1 的 `PG_PASSWORD` 或业务 runtime。

## 固定身份与输入

- 服务器：现有用户目录 PostgreSQL 16，`127.0.0.1:55432`。
- 独立目标：`askdata_m2_bird.public`，75 表、798 列、3,898,114 行、24 序列、155 约束、93 索引（68 个主键索引及 25 个显式索引）。
- 所有者/导入账号：`askdata_m2_import`；11 个 `askdata_m2_ro_<database_id>` 各自仅可读所属逻辑域的表。
- 已审查规格规范 SHA-256：`46bb3555b5906478264c81b6ebc8ba2e86c6c3136bc3d8e3ecfc079770b0eede`。与原来源清单一致，没有重新冻结题目或修改评分规则。
- 默认源目录：`backend/data/external/bird_mini_dev/`；默认来源报告目录：`backend/evaluation/results/m2_b_source_server_20261015/`。已上传的大型数据包无需再次上传。
- 默认凭据文件：`$HOME/.local/share/askdata/m2_bird_credentials.json`。初始化自动生成 12 个随机密码，以独占创建的 0600 文件保存，不保存管理员密码、不显示角色密码，也不将它们写入报告。凭据文件必须留在服务器，后续两阶段自动读取；不要下载、发到聊天或打入同步包。

## 脚本行为

### 独立初始化

`scripts.initialize_m2_b_postgres` 先核对来源及既有 v2 预检，再重新连接维护库检查版本、端口、实际 PGDATA、权限、剩余空间及目标/角色不存在。已存在任一同名角色、目标数据库或凭据文件时拒绝重用，不自动删除。

初始化先保存独立凭据，在事务中创建受限角色，再单独创建数据库（PostgreSQL 的 CREATE DATABASE 不能放在事务内），随后配置所有权、公共权限、域账号默认只读、UTC、search_path、30 秒 SQL 超时和 5 秒锁等待。使用 12 个新账号分别真实登录验证空目标。数据库注释保存本次初始化 ID 与规格身份，后续操作必须匹配。

由于建库跨事务，初始化中途失败可能留下部分角色、凭据或数据库。脚本保留证据，不承诺整体自动回滚，不提供自动 DROP 或重试复用。此时先提交失败报告核对恢复方法。

### 受控导入

`scripts.import_m2_b_postgres` 只接受成功初始化证据，重新核对全部冻结来源，确认身份和空目标。DDL、COPY、序列值、约束、索引和域授权在同一个显式事务内完成。

执行来源仅限已固定规格中的语句。12 条源会话设置由受控设置替代；99 条作者 OWNER 声明不执行，所有对象直接以 M2 导入账号创建，实现显式所有权映射。COPY 使用清单中的列和精确字节范围，通过 Psycopg COPY 流写入，每表重新核对字节摘要及 PostgreSQL 返回的行数。不会把 COPY 数据当作 SQL 执行，也不使用全局字符串替换。

提交前独立检查列、类型、顺序、NULL、默认值、所有者、约束定义和状态、索引定义及状态、序列定义、关联列和当前值。失败时由事务回滚，并尽力确认连接恢复及空目标；提交响应中断时记录 `commit_pending_or_unknown`，不会声称已回滚或自动重新导入。

### 独立一致性与权限验证

`scripts.validate_m2_b_postgres` 必须关联成功、已提交的导入报告及原初始化报告。导入账号使用只读、可重复读快照读取全部 75 表，与源 COPY 逐行类型解码后的完整行多重集摘要比较，同时核对每列 NULL 数和总行数。摘要保留重复行；列顺序、类型和值均参与编码。

类型化摘要策略是 `m2_copy_native_typed_multiset_v1`：BIGINT 按有符号 64 位整数；TEXT 解码 COPY 转义后按 UTF-8；REAL 按 IEEE 754 binary32；DATE 按日期；TIMESTAMPTZ 按 UTC 时刻及微秒；SQL NULL 与空文本、字面 `\\N` 区分。行摘要排序后再取 SHA-256。只在内存保留行摘要，不复制整个 dump。它是导入完整性验证策略，**没有改变 M2 A 冻结的 EX 答案评分规则**。

11 个域账号分别真实登录，逐个检查全部 75 表、列权限、24 序列权限、账号特权及角色成员关系，并验证数据库与 schema 权限。每账号在强制回滚的读写事务中实测跨域 SELECT、INSERT、UPDATE、DELETE、CREATE TABLE、CREATE TEMP、CREATE SCHEMA、SET ROLE 的拒绝及失败后恢复；预期 SQLSTATE 是 `42501`。写入探测均使用 `WHERE FALSE`，意外成功的 DDL 也会回滚。每个账号再实读所属域一张表的总行数。

验证成功报告记录实际 `verified_catalog_version`、`verified_data_version` 和各域权限证据。该证据针对本次快照；目标有变更需重新验证，不是持续监控。

准备阶段每条语句上限 600 秒、锁等待 5 秒。未来模型 runner 的 30 秒 SQL、调用次数、完整结果上限及进程隔离预算尚需在后续 runtime/runner 实施中落实，本次不宣称这些门槛已经完成。

## 服务器操作

先将项目根目录交付的 `M2_B_init_import_sync_20261016.zip` 上传到服务器项目根目录。已有大型源文件和历史报告保留。

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M2_B_init_import_sync_20261016.zip
cd backend

python -m unittest discover -s tests -p 'test_m2_*.py' -v
```

第一步：执行初始化，提示时输入现有 **askdata_admin** 的 PostgreSQL 密码。脚本自动生成的新 M2 角色密码不需要手动输入。

```bash
python -u -m scripts.initialize_m2_b_postgres \
  --prompt-password \
  --server-preflight evaluation/results/m2_b_server_preflight_server_v2.json \
  --output evaluation/results/m2_b_postgres_initialization_server.json
```

仅在上一阶段 `run_status=complete`、`initialization_verified=true`、12 个登录检查通过后继续。第一次初始化失败时不要重复执行建库命令；保存报告核对残留状态。

第二步：执行导入，无需管理员密码。输出逐表 COPY 进度，禁止同时运行另一个导入或验证任务。

```bash
python -u -m scripts.import_m2_b_postgres \
  --initialization-report evaluation/results/m2_b_postgres_initialization_server.json \
  --output evaluation/results/m2_b_postgres_import_server.json
```

仅在 `run_status=complete`、`transaction_outcome=committed`、`database_imported=true` 后继续。此时 `target_data_verified=false` 是正确的阶段状态。

第三步：执行完整目标及账号权限验证，可能耗时数分钟，等待全部 75 表和 11 个账号完成。

```bash
python -u -m scripts.validate_m2_b_postgres \
  --initialization-report evaluation/results/m2_b_postgres_initialization_server.json \
  --import-report evaluation/results/m2_b_postgres_import_server.json \
  --output evaluation/results/m2_b_postgres_validation_server.json
```

预期 `run_status=complete`、`target_data_verified=true`、75 表类型化摘要一致、总行数 3,898,114、11 账号、825 组表 ACL、264 组序列 ACL、88 项拒绝探测通过且 `errors=[]`。

将上述三份服务器 JSON 下载到本地 `backend/evaluation/results/` 后进行最终材料核对。所有输出要求新文件名；保留旧报告，不通过删报告、删库或放宽检查来重试。

## 离线审计与尚待工作

本地验证记录（2026-10-16）：45 项 M2 专项测试通过，覆盖既有协议/预检及新增 COPY、数据类型、结构漂移、来源边界、权限和事务恢复检查。真实源全量审计报告为 `results/m2_b_import_plan_offline_local_20261016_v2.json`，75 表、798 列、3,898,114 行全部通过，`errors=[]`；初始化离线输入检查为 `results/m2_b_initialization_inputs_local_20261016.json`，状态 `checked_only`。两者均未连接 PostgreSQL。

首次本地审计报告 `m2_b_import_plan_offline_local_20261016.json` 保留：它在 PostgreSQL `+08` 时区文本的 Python 3.10 解析处失败，随后补齐时区格式兼容并独立重跑 v2，通过全部源行。没有修改官方数据或跳过失败行。

离线工具 `scripts.audit_m2_b_import_plan` 无需 PostgreSQL，会真实解析全部源行并输出源类型摘要；它不能替代目标验证。

```bash
python -u -m scripts.audit_m2_b_import_plan \
  --output evaluation/results/m2_b_import_plan_offline_server.json
```

本次不运行模型、不执行 Gold110，也没有完成各逻辑域的 runtime/catalog/profile 和外部 runner。三阶段远程验收后，再实施通用运行上下文和预算隔离，随后完成原生 Gold110 就绪检查。
