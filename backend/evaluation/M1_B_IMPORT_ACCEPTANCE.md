# M1 B：PostgreSQL 导入与目标一致性验收

更新：2026-10-08。

## 1. 当前结论

导入、独立验证脚本已实现；25 项针对性测试与两个入口的离线预检查通过。测试覆盖事务回滚、提交中断、输入变化、完整行内容错配、时间精度、权限拒绝及报告保护。完整行测试使用真实 DuckDB 聚合与读取、PostgreSQL 目录桩；事务测试使用故障注入。这些结果不替代真实 PostgreSQL 集成验收。

本地没有连接服务器 PostgreSQL。用户已完成服务器导入与提交后只读核对，下载报告逐项归档审查通过，M1 B 已验收；结果见 [M1 B 最终验收](M1_B_FINAL_ACCEPTANCE.md)。现有应用继续使用 DuckDB，PostgreSQL 应用适配属于 M1 C/D。下文执行命令作为本次实施记录保留，已导入的非空目标不能直接重复导入。

## 2. 实施内容

| 文件 | 用途 |
|---|---|
| [requirements-postgres.txt](../requirements-postgres.txt) | 可选驱动 `psycopg[binary]==3.2.13`，与应用原依赖分开安装 |
| [m1_b_postgres_common.py](../scripts/m1_b_postgres_common.py) | 冻结材料核对、实际元数据与内容验证、目标版本、权限检查、脱敏与报告保存 |
| [import_m1_b_postgres.py](../scripts/import_m1_b_postgres.py) | 导入账号统一事务建表与 COPY，完整验证后提交 |
| [validate_m1_b_postgres.py](../scripts/validate_m1_b_postgres.py) | 只读账号独立读取提交后数据，验证实际写入拒绝 |
| [test_m1_b_postgres.py](../tests/test_m1_b_postgres.py) | 25 项针对性测试；未装可选驱动时跳过本模块 |

共享代码依赖现有 [preflight_m1_b_source.py](../scripts/preflight_m1_b_source.py)。同步包带上该依赖文件，避免服务器遗漏。

### 数据与事务

- 使用服务器已通过审查的三个 JSON，核对原文件摘要、规范导入规格及全部 43 个源文件。规范规格 SHA256 固定为 `8f936c3089614a38b17194b76e0c073c20cfe5b194ecb8f9f1e27b8f4d2ca7fd`。
- 固定目标 `askdata_m1_test.askdata_ops`，默认连接 `127.0.0.1:55432`，固定导入角色 `askdata_import`、验证角色 `askdata_readonly`。校验 PostgreSQL 16、UTF8、UTC、libc/C 和角色权限。
- 目标业务 schema 必须为空。41 张表、41 个主键和 CSV 导入放在同一事务中，使用事务级导入锁。已有对象不会被覆盖；完整验证失败则回滚。
- COPY 从客户端逐块发送原始 CSV，显式列顺序、`HEADER TRUE`、`NULL ''`、逐列 `FORCE_NULL`；源文件 BOM 与内容不改写。发送字节摘要和 COPY 行数也必须符合清单。
- 目标核对 41 表、276 字段、722,732 行，列顺序/类型/可空性/默认值、主键、NULL、distinct、MIN/MAX、SUM/AVG、时间值和 53 条业务关系。
- 全量行以带类型的值生成多重集合摘要，保留重复行，允许行顺序不同。整数 SUM 精确比较；浮点聚合沿用预检约定的相对 `1e-9`、绝对 `1e-6` 容差，完整行摘要仍精确比较。这不会改变题集评分规则。
- 数据读取使用可重复读事务，每批 4,096 行；保存单表行摘要用于排序。单条 SQL 默认超时 120 秒，锁等待 5 秒；必要时可使用 `--statement-timeout-ms` 指定 1,000–1,800,000 毫秒。
- 目标版本由实际 PostgreSQL 列结构、主键、行数和完整内容摘要生成。它表示本次验证的快照，不能监控之后的修改；目标变化后必须重新验证。

### 只读验证与报告

- 核对 41 表 SELECT 授权及 INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER 均未授予，数据库/schema 无 CREATE、TEMP 权限。
- 另开可写事务检验 INSERT/UPDATE/DELETE/CREATE TABLE 的真实权限拒绝，要求四项均为 SQLSTATE `42501`。前三项使用零行条件；整个探测事务强制回滚。仅出现只读事务错误 `25006` 不算权限验收通过。
- 每次命令使用新输出文件，已有报告拒绝覆盖。运行中的报告更新采用临时文件与原子替换，保留提交恢复状态。
- 密码在终端通过隐藏提示输入，不作为命令参数，不读取应用 `.env`，报告不保存密码、DSN、主机或原始连接错误。错误报告保留阶段、错误类别和 SQLSTATE。
- 两个脚本均不调用模型。

## 3. 服务器执行顺序

将同步包上传到服务器项目根目录，再解压。压缩包不包含数据、密码或历史报告。

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M1_B_导入校验同步包_20261008.zip
cd backend
```

保留当前 `py311` 环境，安装可选驱动并执行针对性测试：

```bash
python -m pip install -r requirements-postgres.txt
python -m unittest discover -s tests -p 'test_m1_b_postgres.py' -v
```

预期 `Ran 25 tests ... OK`，没有跳过。源材料必须仍位于 `evaluation/results/m1_b_source_server_20261008/`，其中包含 `source_preflight.json`、`import_manifest.json`、`preparation_review.json`，原 CSV 位于 `data/databases/short_video_ops/`。

### 3.1 导入前离线检查

```bash
python -u -m scripts.import_m1_b_postgres \
  --check-only \
  --preparation-dir evaluation/results/m1_b_source_server_20261008 \
  --output evaluation/results/m1_b_import_check_server.json
```

预期 `run_status=complete`、`phase=source_plan_checked`、计划 41 表/276 字段/722,732 行。此模式不连接 PostgreSQL，`target_data_verified=false`、目标版本为空是正常的。

### 3.2 实际导入

```bash
python -u -m scripts.import_m1_b_postgres \
  --preparation-dir evaluation/results/m1_b_source_server_20261008 \
  --output evaluation/results/m1_b_postgres_import_server.json
```

提示 `Password for askdata_import:` 时输入导入账号密码。只有输出 `run_status=complete`、`commit_state=committed`、`target_data_verified=true` 才完成正常导入。导入报告同时标记只读独立验证待完成。

### 3.3 提交后独立验证

```bash
python -u -m scripts.validate_m1_b_postgres \
  --preparation-dir evaluation/results/m1_b_source_server_20261008 \
  --import-report evaluation/results/m1_b_postgres_import_server.json \
  --output evaluation/results/m1_b_postgres_validation_server.json
```

提示 `Password for askdata_readonly:` 时输入只读账号密码。

正常验收标准：

| 字段 | 预期 |
|---|---|
| run_status / phase | complete / completed |
| target_data_verified | true |
| summary.table_count / field_count / row_count | 41 / 276 / 722732 |
| summary.relation_count / error_count | 53 / 0 |
| summary.full_typed_row_match_count | 41 |
| summary.readonly_table_select_count | 41 |
| summary.actual_write_denial_count / actual_write_denial_sqlstate | 4 / 42501 |
| source_files_unchanged | true |
| verified_target_data_version | 与导入报告的目标版本一致 |
| write_denial_probes.all_probe_changes_rolled_back / connection_recovered | true / true |

验证脚本不提交业务写入，其顶层 `commit_state=not_started` 是正常的。权限探测只在回滚事务内执行。

## 4. 失败与重跑

- 输出文件已存在：保留原文件，改用新输出文件名。
- `commit_state=rolled_back`：先根据 `phase`、SQLSTATE 和验证明细解决原因，再以新报告名重跑导入。
- `commit_state=unknown` 或报告停在 `commit_in_progress`：先运行独立验证，传入该导入报告，用新验证输出名。可能已提交，不能直接再次导入；只有读取到完整目标并与候选版本一致，才能确认恢复成功。
- `rollback_not_confirmed`、目标非空或独立验证失败：保留报告，检查目标现状后再决定恢复步骤，不自动清空数据库。
- 失败记录不会宣称目标数据已验证。提交后若报告保存失败，磁盘上的原子提交中记录可用于独立恢复验证。

执行后请下载这两个新报告到本地 `backend/evaluation/results/`：

```text
m1_b_postgres_import_server.json
m1_b_postgres_validation_server.json
```

核对通过后再形成 M1 B 最终验收结论，进入 M1 C PostgreSQL 执行器和元数据适配。

## 5. 依据与本地证据

- 本地实施检查：[m1_b_import_implementation_local.json](results/m1_b_import_implementation_local.json)。此记录区分单元测试、离线输入检查与尚未执行的 PostgreSQL 集成验收。
- 原源准备与归档核对：[M1_B_PREPARATION.md](M1_B_PREPARATION.md)。原预检、清单和历史报告保持独立。
- 块式 COPY 与事务/savepoint 行为：[Psycopg COPY](https://www.psycopg.org/psycopg3/docs/basic/copy.html)、[Psycopg transactions](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)。本地另检查已安装 3.2.13 驱动完成 COPY 后更新 cursor.rowcount 的代码。
- CSV NULL 和 HEADER 约定：[PostgreSQL 16 COPY](https://www.postgresql.org/docs/16/sql-copy.html)。
