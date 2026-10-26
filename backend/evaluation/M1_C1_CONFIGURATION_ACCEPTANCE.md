# M1 C1：PostgreSQL 配置与来源身份准备

日期：2026-10-09。

## 1. 当前完成范围

已补齐 PostgreSQL 配置、参数校验、只读来源规格和 M1 B 报告关联检查。新增 25 项测试通过；完整 `unittest discover -s tests -q` 执行 322 项测试，全部通过。

本地离线检查 [m1_c1_postgres_config_local.json](results/m1_c1_postgres_config_local.json) 为 `complete`，M1 B 材料引用与目标版本吻合。该检查明确使用 `--allow-missing-password`，本地凭据未配置，没有连接数据库。

这是 M1 C 的第一步。连接池、当前数据库状态核对、PostgreSQL 执行器和真实元数据读取仍待实现。默认应用使用 DuckDB，`DATA_BACKEND=postgresql` 仍会明确拒绝启动现有运行上下文。

## 2. 修改文件与边界

| 文件 | 作用 |
|---|---|
| [app/config.py](../app/config.py) | 读取 PG 参数，密码、主机和报告路径不进入 Settings 的 repr；公开状态仅显示 PostgreSQL 密码是否已配置及当前实施阶段 |
| [.env.example](../.env.example) | 添加 PG 配置示例，保留默认 DuckDB 和现有模型配置示例 |
| [postgres_config.py](../app/datasources/postgres_config.py) | 显式读取/校验配置，核对历史材料，生成 RecordedPostgresSource |
| [check_m1_c_postgres_config.py](../scripts/check_m1_c_postgres_config.py) | 离线检查入口，使用独立 JSON 保存结果，不请求模型或数据库 |
| [test_postgres_config.py](../tests/test_postgres_config.py) | 参数范围、脱敏、报告关联、来源版本及 DuckDB 兼容性测试 |

实际 `.env`、原 CSV、M0/M1 A/M1 B 报告保持原样。未安装新依赖；本步骤检查不依赖 Psycopg 或连接池包。

## 3. 参数默认值与约束

| 环境变量 | 默认值 | 校验 |
|---|---|---|
| PG_HOST | 127.0.0.1 | 单一 TCP 主机/IP，不能为空，不接受 DSN、主机列表或 socket 目录 |
| PG_PORT | 55432 | 1–65535 |
| PG_DATABASE | askdata_m1_test | 与本次 M1 B 固定目标一致 |
| PG_SCHEMA | askdata_ops | 与本次 M1 B 固定目标一致 |
| PG_USER | askdata_readonly | 仅接受只读账号 |
| PG_PASSWORD | 空 | 默认检查要求非空，原值不额外 strip；报告仅显示配置状态 |
| PG_SOURCE_ID | short_video_ops_postgres | 与 M1 B 来源一致 |
| PG_CONNECT_TIMEOUT_SECONDS | 10 | 2–120 秒 |
| PG_STATEMENT_TIMEOUT_MS | 120000 | 1000–1800000 毫秒 |
| PG_LOCK_TIMEOUT_MS | 5000 | 100–60000 毫秒，且不大于 SQL 超时 |
| PG_POOL_MIN_SIZE | 1 | 1–32，不大于最大连接数 |
| PG_POOL_MAX_SIZE | 4 | 1–32 |
| PG_POOL_WAIT_TIMEOUT_SECONDS | 10 | 1–120 秒 |
| PG_POOL_MAX_WAITING | 16 | 1–256 个等待请求 |
| PG_VERIFIED_DATA_VERSION | 见下方 | 小写 64 位 SHA256，必须与报告及重算目标版本一致 |
| PG_IMPORT_REPORT_PATH | evaluation/results/m1_b_postgres_import_server.json | 必须能读取并关联原始报告 |
| PG_VALIDATION_REPORT_PATH | evaluation/results/m1_b_postgres_validation_server.json | 必须为独立的已通过验证报告 |

已验收目标版本：

```text
882ba07c90b4db91328344b37974f362edf737b1f4f82379c8658fe514c10fa1
```

`PG_` 数字字段在 PostgreSQL 显式检查入口解析，尚未使用的错误 PG 数值不会让默认 DuckDB 启动失败。相对报告路径统一相对 `backend/` 解析，与命令当前目录无关。

连接超时与连接池等待超时分别限制建立连接和等待取得连接。下一步连接管理将实际应用这些参数，本步骤仅验证配置。[PostgreSQL 连接参数](https://www.postgresql.org/docs/16/libpq-connect.html)、[Psycopg 连接池参数](https://www.psycopg.org/psycopg3/docs/api/pool.html)

## 4. 来源身份与证据检查

公开准备规格包含：逻辑数据库 `short_video_ops`、source_id `short_video_ops_postgres`、backend `postgresql`、解析方言 `postgres`、提示词方言 `PostgreSQL`、物理数据库/schema、查询账号与已记录目标版本。

检查覆盖两份报告的运行与提交状态、环境/账号、导入规格、表/字段/行数、主键状态、重算目标版本、41 表授权及四项实际权限拒绝证据。验证报告引用的导入报告 SHA256 必须与本地实际字节一致；错误消息不输出主机、密码、路径或原始材料文本。

目标的已记录物理结构版本为：

```text
b12bffb567ee4aa3ca126d48154ddfb36c1721d1af7c6e8b65efc4780615a817
```

这个摘要来自报告中的实际表名、列定义和主键。它与现有应用 `CatalogSnapshot.version` 的含义不同，不能混用。第一步保持 `catalog_version=null`，待读取真实元数据、合并业务标注并冻结 catalog 后再生成完整 `SourceIdentity`。

报告区分：

- `recorded_evidence_verified=true`：本地持有的 M1 B 历史材料与配置一致。
- `live_target_verified=false`：本次未检查当前 PostgreSQL 状态。
- `runtime_available=false`：PostgreSQL runtime 尚未接通。
- `password_configured=true/false`：仅表示读取到了非空配置，不代表账号登录成功。

主机、端口、密码与报告绝对路径不进入公开来源规格。当前数据或结构发生变化时，后续实时核对必须拒绝继续使用过期版本。

## 5. 服务器操作

将 `M1_C1_配置与来源身份同步包_20261009.zip` 上传到项目根目录，解压后进入 backend：

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M1_C1_配置与来源身份同步包_20261009.zip
cd backend
```

保留服务器现有 `backend/.env` 中的模型设置。将 `.env.example` 新增的 `PG_` 段合并到该 `.env`，在服务器编辑 `PG_PASSWORD` 为 `askdata_readonly` 的密码；不要把整个示例覆盖成 `.env`。系统环境变量优先于 `.env`。

暂时保持：

```dotenv
DATA_BACKEND=duckdb
DATA_SOURCE_ID=short_video_ops_duckdb
```

两份 M1 B 原始报告必须仍在服务器 `evaluation/results/`，不要重新格式化或改写，验证报告记录的是导入报告原始字节 SHA256。

先运行本步骤测试：

```bash
python -m unittest discover -s tests -p 'test_postgres_config.py' -v
```

预期 25 项通过。然后执行默认严格配置检查：

```bash
python -u -m scripts.check_m1_c_postgres_config \
  --output evaluation/results/m1_c1_postgres_config_server.json
```

预期：

| 字段 | 预期 |
|---|---|
| run_status / errors | complete / [] |
| password_required / credentials_configured | true / true |
| application_backend | duckdb |
| recorded_source.recorded_evidence_verified | true |
| recorded_source.recorded_data_version | 与 M1 B 目标版本相同 |
| recorded_source.catalog_version | null，等待真实元数据模块 |
| postgresql_connected / live_target_verified / runtime_available | false / false / false，本步骤正常状态 |
| new_model_request_count | 0 |

若只检查参数和历史材料、尚未填密码，可以显式使用 `--allow-missing-password`，并改用新的输出文件名；它不满足凭据配置完成的检查。

输出文件已存在时换新文件名。出现账号、版本、原始材料摘要不符时先核对配置/文件，不通过放宽校验绕过。

执行后下载 `m1_c1_postgres_config_server.json` 到本地 `backend/evaluation/results/`。核对后继续 M1 C 第二步：连接池及只读事务生命周期。
