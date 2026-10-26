# M2 开发集诊断记录与服务器执行说明

日期：2026-10-17。目标：补齐可信评测端的观察证据，支持分析首轮 development80 的 46 道失败题。

## 本次实现

### 1. 排序候选、分数和筛选原因

`development_diagnostics.retrieval.candidates` 最多记录 40 个 RRF 候选：

- 字段 ID、BM25 排名/分数、dense 排名/分数、RRF 排名/分数。
- rerank 排名/分数、是否选中，以及 `selected`、`below_threshold`、`rerank_not_returned`、`beyond_top20` 原因。
- 分数是既有 broker 将供应商分数限制到 [0,1] 后的值；不宣称保存了原始 HTTP 响应。

阈值仍为 0.55，上限仍为 20 个字段；候选顺序、并列排序和模型请求内容均沿用原逻辑。

### 2. 最终授权 Schema 图和补充关联键

记录实际传给 Agent 的最终图，以及 `relation_key_field_ids` 和 `added_relation_key_field_ids`。新增诊断数据由 broker 从 Schema 返回值中移出，Agent 收到的 Schema 键、图、文本与原链路一致。

图快照包含 `value`、`complete`、字节数、SHA-256 和截断/省略原因。过长元数据、超限图会明确标为不完整，不能将其当作完整图验收。

### 3. 每次 SQL 和结构化校验原因

按模型决定、校验、执行三个阶段记录实际 SQL、原始 SQL SHA-256、长度及截断/脱敏标记。即使最后澄清或校验失败，已发生的 SQL 尝试仍保留。

PostgreSQL 错误保留 SQLSTATE、条件分类，并对解析/分析类错误记录受控的 primary message、语句位置和标识符。不会读取原始异常字符串、detail、hint、context、内部 SQL 或连接串。

原有 `BirdFailure.public()` 和返回给 Agent 的校验反馈保持原格式。本步骤只补报告，不增强模型的错误修复提示。

### 4. 模型澄清解释

broker 在模型返回 `action=clarify` 时保存它实际提供的 `reason`。模型没有提供解释时记为未知，不补写推测理由。该记录不会发送回模型或索引器。

## 边界和大小限制

- SQL 显示文本：8,192 UTF-8 字节，另存原文哈希和原长度。
- 澄清解释：2,048 UTF-8 字节。
- 图快照：98,304 字节，字符串/容器另有上限，完整性标记可核对。
- 每题诊断：393,216 字节；最多 9 次生成、9 次校验和 3 次执行记录。
- 新增诊断会清除已配置的 API/查询密码值及常见密钥赋值、Bearer token、PostgreSQL DSN。正常业务 SQL 字面量仍用于开发评审。
- 不写完整模型请求、HTTP 错误响应、向量或 Gold 答案。诊断输出只能用于可信开发评审，不能进入索引。

## 独立开发诊断入口

新增 `evaluation.bird.diagnostic_runner`，默认选择 14 道开发题，覆盖 8 个开发域：

| 范围 | 题号尾号 |
|---|---|
| 校验错误 | 0050、0095、1473 |
| 检索/澄清 | 1435、0201、1399、0586 |
| NULL 排序/输出范围 | 0036、0082、1486、0159 |
| 实体值、原生数值路径、类别值 | 1405、0368、0766 |

所有题号必须属于冻结 development80；重复、未知和 holdout 题号会被拒绝。

该入口执行新的模型诊断，不回放旧报告中缺失的 SQL，输出可能不同于旧运行。它不向 worker 传递 Gold SQL、旧 SQL 或旧成绩，也不执行 Gold；`primary_ex=null`、`formal_benchmark=false`。旧状态由可信父进程在 worker 退出之后附加，便于人工对照。

### 来源与代码版本的处理

历史 runtime、Gold110 和 development80 的原始字节哈希必须分别为：

```text
ecaf50f6c7a17460dd6260a9dcf198f91fcf33e397e581c16aa82a55d7d63473  runtime
e87dc6e51833eaa22344c0882ac49109822cbd0bff6526eda05a361c7cf8ea03  Gold110
7f59478b5d589a49d85027e965e8b3596416ac998df4618c655984841fc8c01d  development80
```

它们只证明已验收的历史来源链。诊断入口另行绑定当前代码，实际执行当前 Linux 文件/网络/进程/环境隔离探测、硬超时探测和预算探测，并对选中的 8 个域重新验证类型化全量数据、结构、权限和查询前内容 guard。

正式 `run_bird_benchmark` 仍严格拒绝把旧代码 runtime/Gold 报告当作当前代码就绪证据。后续正式候选回归需要为新代码建立新的 runtime 和 Gold110 报告，使用新文件名保存；本诊断入口不会绕过正式验收。

索引身份含有代码哈希，本次改动会产生新的索引分区。预计首次准备 8 域索引需要约 49 个 embedding 批次，无重试时如此；成本单独记入 `shared_index_http_attempts`。14 题题内调用也会产生费用。

## 服务器操作

将 `M2_development_diagnostics_sync_20261017.zip` 上传至服务器项目根目录。保留旧报告及已有数据、私有凭据文件。

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M2_development_diagnostics_sync_20261017.zip
cd backend

python -m unittest discover -s tests -p 'test_m2_*.py' -v

python -u -m evaluation.bird.diagnostic_runner \
  --baseline-report evaluation/results/m2_c_bird_development80_server.json \
  --runtime-report evaluation/results/m2_c_bird_runtime_server.json \
  --gold-report evaluation/results/m2_c_bird_gold110_server.json \
  --case-list evaluation/cases/bird_mini_dev/m2_development_diagnostics14.json \
  --model-config-file .env \
  --save-snapshot \
  --output evaluation/results/m2_development_diagnostics14_server.json
```

输出文件名必须尚未存在。运行结束后下载 `m2_development_diagnostics14_server.json` 到本地 `backend/evaluation/results/`。

## 报告核对重点

1. `formal_benchmark=false`、`gold_executed=false`、`primary_ex=null`，没有把诊断当作正式得分。
2. 当前隔离与硬超时探测通过，8 个域来源绑定正确，准备连接池和逐题 runtime 关闭。
3. `summary.case_count=14`、`diagnostics_recorded_count=14`、`runtime_closed_count=14`；逐题检查是否有异常。
4. 排序候选/筛选原因和最终图记录齐全；图 `complete=true` 或有明确的截断说明。
5. 对 0050、0095、1473 检查新一次运行中的 SQL、SQLSTATE、位置和具体原因；若没有复现旧错误，要如实记录。
6. 对澄清检查实际理由，对遗漏字段检查其候选排名、分数和补充关联路径。
7. 记录题内与索引调用成本；本次不设 EX 通过率门槛。

本地测试使用模拟连接和模型。真实 PostgreSQL、Linux 内核隔离和新模型输出须以上述服务器诊断报告为证据。
