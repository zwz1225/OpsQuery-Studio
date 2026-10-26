# M2 C：逻辑域运行上下文、预算隔离与原生 Gold110 就绪检查

实施日期：2026-10-16。M2 B 的独立初始化、受控导入和完整数据/权限验证已经通过。本次实现下一阶段代码；远程验收仍需执行下述命令并核对新报告。

## 运行上下文与来源约定

外部入口为 `evaluation.run_bird_benchmark`，运行上下文在 `evaluation/bird/`。每个 `database_id` 只装配固定的 `askdata_m2_ro_<database_id>`、本域表集合、catalog、profile 和同步连接池。未知域、`short_video_ops` 或冲突的来源直接拒绝。

每域池固定最小/最大连接数 1、等待队列 1、等待与连接上限 10 秒；注册表最多 11 个域池，正式题目串行执行。每次借用都显式使用只读、可重复读事务，设置受控 `pg_catalog,public`、UTC、ISO 日期、浮点显示精度、SQL 30 秒和锁等待 5 秒。异常回滚，归还前 RESET ROLE/RESET ALL；清理失败丢弃连接，关闭可重复调用。

来源以已验收的 M2 B 验证报告为根，原始文件 SHA-256 为：

```text
221678d07dd0509048ae2563a3a006e3dc033ea474265ac90ceb9723bfa103c6
```

构造每域 runtime 时，使用该域真实查询账号核对身份、账号特权/成员关系、数据库/schema、全部 75 表及列权限、24 序列权限，以及本域列、默认值、排序规则、约束、索引、所有者、RLS 和对象类型。字段说明只读取本域固定 CSV，类型以实时 catalog 为准。

首次构造还完整读取本域数据，以原生类型摘要匹配 M2 B 已验收结果，并在同一快照建立服务器行内容摘要。查询和 profile 操作在各自事务内重新检查元数据、权限及本域完整内容摘要，再执行操作。批量 runner 只预验证每域一次，向受信任的题目进程传递本次 receipt；题目进程仍必须实时核对结构和完整内容摘要。

**版本分两层记录：** M2 B 全局数据/catalog 版本是已验收来源的材料身份；每域 runtime 使用包含本域字段说明/权限的 catalog 版本和本域已验证数据版本。不同域的 `catalog_version` 不相同是正常的，不能拿它直接替代全局版本。验证快照是逐域建立的，不宣称 11 个账号共享一个全局数据库快照。

Profile 按实际数据库类型排序，使用 `SELECT DISTINCT ... ORDER BY ... ASC NULLS LAST LIMIT 3`；文本显示最多 64 字符，每个样例保留截断标志。完整 catalog 可以校验全部授权字段，检索仍按冻结协议选择最多 20 个字段，并补足 Schema 图关联键。

## Agent、索引器与评分器隔离

- Agent 和索引文档构建器均运行于独立的 `python -I -S` 子进程，只启动一份私有目录内的标准库程序。
- Agent 只接收公开五字段及本域检索 Schema；索引器只接收本域 catalog/profile，不接收题目、Gold、完整题库、密码或模型密钥。
- 完成启动后，必选 seccomp 规则拒绝新文件打开、文件改写、直接网络连接、创建进程和读取其他进程。内核支持时额外叠加 Landlock；即使 Landlock 未启用，新文件打开仍由 seccomp 禁止。
- Agent 通过三项受控 RPC 请求 chat、validate、SQL；索引器没有模型/SQL RPC，只负责从授权元数据构造文档。模型 HTTP、数据库访问和索引落盘由受信任 broker 执行。
- 评分器保留 Gold 和原生完整结果，Agent 退出后再比较；正确率、Gold SQL 和答案不会反馈到 Agent。Gold 就绪报告也不公开答案行、行数或答案摘要。

Linux 验收会实际尝试读取私有探测文件、Gold110、完整题库及凭据文件，并探测网络和进程创建拒绝。必须具备 x86_64 Linux、seccomp 与 `libseccomp.so.2`；不可用时不允许继续 Agent/索引器任务。无需管理员密码或 sudo。具体库版本和内核信息会记录到报告。

索引只由本域真实字段、官方说明和受控样例构成，复用现有 BM25、向量检索、RRF 和 Schema 图组件。检索输入固定为原问题与 evidence，不使用 Gold 检索词或运营指标目录。索引身份包含协议、域、账号、数据/catalog 版本、模型配置、样例策略及相关代码摘要；载入时检查完整字段集合、来源及文档摘要。

## 强制预算与原生结果

| 项目 | 实现约束 |
| --- | --- |
| 正式题目并发 | 固定 1 |
| 单题整体 | 父进程 600 秒硬上限，超时终止题目进程组及 Agent |
| 模型请求 | 180 秒，覆盖 DNS、连接与响应体读取 |
| 每请求重试 | 最多 1 次，共享计数 |
| 总模型 / Chat HTTP 尝试 | 每题最多 16 / 10，含 embedding、rerank 和重试 |
| 提示词 / Chat 输出 | 最多 98,304 UTF-8 字节 / 4,096 token |
| SQL 工具 / 每轮校验 | 最多 3 / 3；生成修正也最多 3 次/轮 |
| SQL / 锁等待 | 30 秒 / 5 秒 |
| 完整结果 | 每边最多 100,000 行、64 MiB，额外读取一行确认超限 |

完整结果保留 Psycopg 原生元组、列位置、Decimal 精度及日期类型，允许重复列名。EX 仍是冻结的 `set(predicted tuples) == set(gold tuples)`；预览最多 200 行，不能拿它评分。行数或字节超限时记录独立失败原因，主分贡献为 0，不能返回部分结果作为正确答案。

负载大小策略记为 `bird_native_tagged_utf8_payload_v1`：列信息与每行带类型标签的 UTF-8 表示计入字节数；该表示仅用于测量/预览/诊断，EX 比较发生在原生值上。没有引入别名规则或数值容差。

共享索引的 profile/embedding 准备在正式单题预算外单独报告；索引构建的模型尝试有明确批次数和重试上限。正式题目内不允许隐式重建索引。供应商没有返回 usage 时记录 `null`；进程被强制终止导致调用计数不可知时记录未知与已观察计数。

## 服务器分阶段执行

上传 `M2_C_runtime_runner_sync_20261016.zip` 到服务器项目根目录后：

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M2_C_runtime_runner_sync_20261016.zip
cd backend

python -m unittest discover -s tests -p 'test_m2_*.py' -v
```

### 第一步：运行上下文、profile、预算和隔离验收

```bash
python -u -m scripts.check_m2_c_bird_runtime \
  --output evaluation/results/m2_c_bird_runtime_server.json
```

默认读取服务器上现有源目录、M2 B 三份报告及 `$HOME/.local/share/askdata/m2_bird_credentials.json`。无需模型密钥，不发模型请求。

通过条件：`run_status=complete`，`runtime_verified=true`、`target_data_verified=true`、`agent_isolation_verified=true`、`budget_enforcement_verified=true`、`pools_closed=true`，覆盖 11 域、75 表、798 字段，`errors=[]`。`runtime_available=true` 表示适配器已成功装配验证，命令退出后连接池已关闭。

将 **`m2_c_bird_runtime_server.json`** 下载到本地原目录核对。若失败，先保存报告定位，不修改原协议、角色权限或评分规则来跳过检查。

### 第二步：原生 Gold110 就绪检查

运行上下文报告通过后执行：

```bash
python -u -m evaluation.run_bird_benchmark \
  --mode gold \
  --runtime-report evaluation/results/m2_c_bird_runtime_server.json \
  --save-snapshot \
  --output evaluation/results/m2_c_bird_gold110_server.json
```

该模式固定覆盖开发 80 题和保留 30 题的全部原始 PostgreSQL Gold SQL，不生成或改写 SQL，不调用模型。每题使用对应域账号，完整读取受限的原生结果；报告保留题号、SQL SHA-256、完整性/类型支持状态及失败分类，不暴露答案。Gold 出错、超时、超限或不支持类型时 `gold110_ready=false`，拒绝正式 live，保留全部题号和失败记录。

通过条件：`run_status=complete`、`gold110_ready=true`，110/110 均为 `gold_ready` 且完整、支持、正确关闭 runtime，模型请求数为 0。下载 **`m2_c_bird_gold110_server.json`** 后再核对正式就绪结论。

### 后续开发集 live 入口

本次先完成上面两份报告的验收。验收后可使用已有外部入口联调 smoke8：

```bash
python -u -m evaluation.run_bird_benchmark \
  --mode live --split smoke8 \
  --runtime-report evaluation/results/m2_c_bird_runtime_server.json \
  --gold-report evaluation/results/m2_c_bird_gold110_server.json \
  --model-config-file .env \
  --save-snapshot \
  --output evaluation/results/m2_c_bird_smoke8_server.json
```

模型名、temperature、thinking、embedding 维度及 rerank 名称从冻结协议固定；`.env` 只读取密钥和三个端点地址。会记录实际请求配置及供应商返回的模型标识。切换为 `--split development80` 可跑开发集，全部失败和澄清均保留在固定分母中。此命令会产生模型调用费用，当前阶段不执行它。

**保留集正式 live 是后续阶段。** 当前 CLI 仅开放 smoke8/development80；需要另行固定开发候选、全部相关索引和一次性尝试台账后，才能开放 holdout30，不能把 Gold 环境检查当作保留集模型成绩。

所有输出使用新文件名。runtime/Gold 门槛绑定源材料、代码/提示词、Python/关键依赖及内核；相关版本变化需重新建立对应证据。Gold 不使用结果缓存；索引严格核对来源身份；快照按协议、已验收数据版本和 split 分目录，当前入口拒绝续跑参数。

## 本地验证边界

完整 M2 测试运行 79 项，本地通过 76 项，3 项 Linux 专项检查明确跳过，记录见 `results/m2_c_bird_tests_local_20261016_v2.json`。最终运行上下文/runner 变更又单独验证 34 项，31 项通过、同样 3 项待 Linux 验证，见 `results/m2_c_bird_tests_final_delta_local_20261016.json`。

最终离线审计为 `results/m2_c_bird_offline_audit_local_20261016_v2.json`，核对 11 域、75 表、798 字段以及 110 条 Gold 的原始字节/只读策略；它不执行这些 Gold。官方 `formula_1/constructors.csv` 多出的 `wins ` 描述行未对应真实列，已保留诊断；catalog 没有据此增加不存在的字段。

本地 Windows 只运行离线审计与模拟测试。Linux 文件/网络/进程隔离、进程超时和真实索引子进程必须在服务器验证；真实 PostgreSQL runtime 与 Gold110 执行也未由本地测试替代。冻结协议、开发/保留题目、原始 Gold 和 M2 B 既有报告均保持原始字节。
