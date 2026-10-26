# M2 B1：服务器预检与导入清单交付

日期：2026-10-15。当前完成 B 的第一步：只读服务器预检脚本、离线来源清单脚本、已审查清单及测试。尚未创建远程 M2 库/角色、导入数据、验证目标数据或运行模型。外部 runner 的预算与 Agent/评分器隔离仍按 M2 A 的后续门槛实施。

首轮服务器报告已核对：8/9 项通过，唯一失败来自 `127.0.0.1/32` 与裸 IP 的字符串比较误判。地址解析已修正，M2 专项测试现为 26 项通过。已有服务器代码包之后需再同步 `M2_B_endpoint_fix_20261015.zip`，并使用独立 `_v2.json` 文件重跑；具体见[首轮报告核对与补丁命令](M2_B_SERVER_PREFLIGHT_REVIEW.md)。原始报告和初次交付包继续保留。

## 交付内容与本地结果

| 内容 | 文件 / 结果 |
| --- | --- |
| 服务器只读预检 | `scripts/preflight_m2_b_server.py` |
| 来源/导入清单 | `scripts/preflight_m2_b_source.py`、`scripts/m2_b_dump.py` |
| 独立公共约定 | `scripts/m2_b_common.py`，不读取应用 `.env` 或 M1 `PG_PASSWORD` |
| 固定导入规格 | `evaluation/cases/bird_mini_dev/m2_b_import_spec_v1.json` |
| 本地真实来源预检 | `evaluation/results/m2_b_source_local_20261015/`；加入规格摘要检查后的复跑为 `m2_b_source_local_20261015_v2/` |
| 专项测试 | `test_m2_b_preparation.py` 新增 11 项；连同 M2 A 的 14 项，共 25 项通过 |

本地全量 source 检查实际读取官方 SQL 和描述材料，核对为 75 表、798 字段、3,898,114 行、24 序列。完整控制清单包含 11 个原会话设置、1 个 search_path 设置、75 个建表、99 个所有权声明、24 个序列创建、24 个序列归属、24 个列默认值、24 个序列值、155 个约束和25个唯一索引。全部 COPY 数据按行作为数据读取，未执行 SQL。

导入规格的规范 JSON SHA-256 固定为：

```text
46bb3555b5906478264c81b6ebc8ba2e86c6c3136bc3d8e3ecfc079770b0eede
```

每表包含原始 DDL、列名/类型/约束、COPY 列顺序、数据字节区间、原始 COPY SHA-256、行数及各列 NULL 数。当前是源侧证据；`real` 浮点、日期等类型化值与真实目标是否相等仍需导入后验证，不能把原始 COPY 摘要冒充目标数据版本。

## 同步包

两个包保存在项目根目录：

```text
E:\PythonLearn\askdata_studio_ops_release\M2_B_preflight_sync_20261015.zip
E:\PythonLearn\askdata_studio_ops_release\M2_B_source_data_20261015.zip
```

第一个是较小的代码/协议同步包，包含本次脚本、M2 A 公共模块与冻结清单、已审查导入规格、测试和执行说明。第二个包含 80 个必要来源文件，主要是 PostgreSQL SQL，另含官方题目、表关系、75 份字段说明及原始 README/元数据；不包含 MySQL、SQLite 或完整混合 ZIP。

**先仅上传代码包**到远程项目根目录 `~/Python_work/askdata_studio_ops_release/`。确认服务器预检通过后，再上传较大的来源包。包的大小和逐包 SHA-256 见 `evaluation/results/m2_b_preparation_delivery_20261015.json`。

## 服务器第一轮命令

先将代码包上传到上述目录，再执行：

```bash
cd ~/Python_work/askdata_studio_ops_release
ls -lh M2_B_preflight_sync_20261015.zip
unzip -o M2_B_preflight_sync_20261015.zip
cd backend

python -m unittest discover -s tests -p 'test_m2_*.py' -v

python -u -m scripts.preflight_m2_b_server \
  --prompt-password \
  --output evaluation/results/m2_b_server_preflight_server.json
```

出现 `M2 PostgreSQL admin password:` 时，输入之前创建 PostgreSQL 服务时的 **`askdata_admin` 密码**，不是模型密钥或 `askdata_readonly` 密码。终端不回显输入；报告不记录密码，脚本不更改 `.env`。也支持事先配置独立的 `M2_PG_ADMIN_PASSWORD` 环境变量，但不要把明文写进可分享的命令或报告。

预检只连接 `127.0.0.1:55432` 的维护库 `postgres`，显式只读事务，检查以下内容：实际登录、PG16、UTF8/C locale、本机地址/端口、实际 pgdata、管理员初始化权限、M2 目标和角色尚未存在、来源和 PG 存储容量。默认 pgdata 为 `~/.local/share/askdata/pg16-data`；若位置确已迁移，应提供真实 `--pgdata` 并核对报告，不能仅为绕过失败而填写任意路径。

默认检查的 M2 目标固定为 `askdata_m2_bird.public`，角色为 `askdata_m2_import` 及 11 个 `askdata_m2_ro_<db_id>`。本轮预检采用**目标库和角色尚未存在**的首次初始化条件；已存在时停止并审查既有状态，不自动复用空库，也不删除对象。

容量预检采用至少 **10 GiB 额外可用空间**作为保守的准备门槛，检查真实 PG 数据目录和待存放来源文件的分区。该值是操作预算，不是实测导入占用；上传来源后还要重新核对空间。原 `/home` 有过空间满的情况，容量检查失败时应先处理空间或存储布局。

服务器报告 `run_status=complete`、`ready_for_initialization=true` 且各项 checks 通过，才进入后续准备；`blocked` 或 `failed` 都会非零退出并保留原因。请先反馈/下载：

```text
backend/evaluation/results/m2_b_server_preflight_server.json
```

报告只证明检查当时的状态，真正初始化前仍需重新核对目标和权限，不能把预检等同于已经创建目标。

## 服务器通过预检后的来源准备命令

以下是第二轮命令，需先上传 `M2_B_source_data_20261015.zip` 到远程项目根目录：

```bash
cd ~/Python_work/askdata_studio_ops_release
ls -lh M2_B_source_data_20261015.zip
unzip -o M2_B_source_data_20261015.zip
cd backend

python -u -m scripts.preflight_m2_b_source \
  --output-dir evaluation/results/m2_b_source_server_20261015
```

来源包会解压到 `backend/data/external/bird_mini_dev/`，脚本默认读取该路径。固定协议和题目摘要均必须匹配；不会连接数据库。成功时输出三份独立材料：

```text
evaluation/results/m2_b_source_server_20261015/source_preflight.json
evaluation/results/m2_b_source_server_20261015/import_manifest.json
evaluation/results/m2_b_source_server_20261015/preparation_review.json
```

需核对 `run_status=complete`、75表/798字段/3,898,114行/24序列，以及规格摘要与上方一致。输出已存在时换新目录或报告名，保留旧材料。上述两轮检查均不初始化库、不导入数据、不调用模型；服务器材料核对后再实施独立初始化、受控导入及目标一致性验证。
