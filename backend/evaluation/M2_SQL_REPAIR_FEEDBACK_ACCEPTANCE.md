# M2 SQL 修复反馈：实现与服务器验证

日期：2026-10-17。候选策略：`bird_authorized_sql_repair_v1`。

## 本次修改

### 1. 向模型提供受控原因和位置

校验失败的响应新增 `repair_feedback`，Agent 将它放进下一次模型请求的 `validation_error`。

- 只使用失败的预测 SQL、原始问题/官方 evidence、当前 runtime 授权 catalog 和受控 PostgreSQL 错误字段。
- 错误原因包含 SQLSTATE、条件分类和脱敏的 primary message；不转发异常字符串、detail、hint、context、内部查询、连接串或凭据。
- 运行时分别标记 EXPLAIN 包装语句和原始执行语句。位置按字符计算，输出 1 起始的 `sql_position`、行、列。
- 对 `EXPLAIN (FORMAT JSON) ` 包装减去实际前缀长度；无法确认来源、位置越界或重复 SQL 版式不同，明确标为不可用。
- 反馈中复制的失败 SQL 最多 2,048 UTF-8 字节；诊断尝试记录仍最多 8,192 字节，两者都保留原始长度、SHA-256 和截断标记。

0050、0095、1473 历史错误位置分别从 30、192、191 归一化为生成 SQL 的 8、170、169。

### 2. 有授权依据的字段提示

提示字段来自当前 runtime 的已验证 catalog，并限制在失败 SQL 引用的、属于当前逻辑域的物理表中。最多 4 张表、16 个字段，给出表 ID、表名、别名、字段名、类型和带引号的引用形式。

字段排序使用失败标识符、原始问题/evidence 和官方字段名称/描述；不使用 Gold、旧成绩或逐题 SQL 替换表。提示不查询数据库、不扩展账号权限，也不增加模型调用。

离线真实材料测试确认：0050 可提供 `schools.school`、`satscores.sname`；1473 可提供 `yearmonth.date`、`customers.customerid`。这些是字段目录提示，不代表其生成结果已通过 EX。

### 3. 重复失败 SQL 提前终止

对确定性的解析、分析和只读策略错误，保存当前题内的失败指纹。

- 指纹归一化空白、注释及不带引号的标识符大小写。
- 保留字符串字面量、带引号标识符和 NULL 排序等语义差异。
- 再次提交等价的已失败 SQL 时，计入本次生成/校验尝试，不重复执行数据库校验，返回 `retryable=false`。
- Agent 结束该题，状态为 `repeated_sql`。这仍然是未答/未通过，不记成功；可避免第三次重复生成与校验浪费。
- 超时、连接等暂态失败不进入重复失败缓存；缓存不跨题共享。

### 4. 预算与评分

仍为每轮最多 3 次生成/校验、最多 3 轮 SQL 工具调用、每题 16 次 HTTP/10 次 chat、600 秒；HTTP 重试、提示长度、SQL 超时和结果上限保持原约定。三条不同 SQL 仍可各自尝试。

没有自动改写 SQL。有效 SQL 原文继续由执行器执行。原始 Gold、原生 tuple-set EX、初始检索阈值/字段上限、权限与隔离规则保持原字节或原逻辑。

这是修复反馈候选，不包含下一阶段的初始 Schema 覆盖改造。

## 诊断报告新增内容

- 根节点及逐题 `sql_repair_policy`。
- 失败 `validation_events` 中的 `repair_feedback`。
- `runtime_validation_performed`：是否调用运行时校验流程。
- `database_validation_performed`：是否有对应 EXPLAIN/查询的数据库错误上下文；本地策略拒绝和重复阻断不会标成数据库校验。
- `development_diagnostics.attempts` 保留反馈副本、原始 SQL 和错误记录。
- 汇总新增 `repeated_sql_case_count` 和 `database_validation_skipped_count`。

## 服务器先验证三题

将 `M2_sql_repair_feedback_sync_20261017.zip` 上传至服务器项目根目录。

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M2_sql_repair_feedback_sync_20261017.zip
cd backend

python -m unittest discover -s tests -p 'test_m2_*.py' -v

python -u -m evaluation.bird.diagnostic_runner \
  --baseline-report evaluation/results/m2_c_bird_development80_server.json \
  --runtime-report evaluation/results/m2_c_bird_runtime_server.json \
  --gold-report evaluation/results/m2_c_bird_gold110_server.json \
  --case-list evaluation/cases/bird_mini_dev/m2_sql_repair_validation3.json \
  --model-config-file .env \
  --save-snapshot \
  --output evaluation/results/m2_sql_repair_validation3_server.json
```

保留原报告，输出文件名必须尚未存在。下载 `m2_sql_repair_validation3_server.json` 到本地 `backend/evaluation/results/` 核对。

本命令是开发诊断，`gold_executed=false`、`primary_ex=null`。历史 runtime/Gold 报告作为已验收来源链；诊断入口会执行当前隔离、超时和预算探测，并重新验证三个目标域的数据、结构、权限和内容 guard。

需要模型密钥，会产生调用费用。代码身份变更会创建新索引分区；三域首次无重试的 embedding 批次预计为 9+6+3=18，成本单独记录。

## 如何判断结果

1. 检查新反馈中的具体原因、位置和字段归属是否正确、完整且脱敏。
2. 检查模型是否实际修改错误字段/SQL 结构，以及是否出现新的错误。
3. 若重复 SQL，确认第二次被阻断、没有第三次重复调用，并保留未通过状态。
4. 校验不同 SQL 时仍保留原尝试次数；所有调用和预算记录可核对。
5. 不能把 `diagnostic_answered` 当作 EX 正确；修复 SQL 语义还需正式对照。

先验证本轮反馈，再衔接 Schema 覆盖修正。候选稳定后，为新代码建立独立 runtime、Gold110 报告，再做新的 development80；正式入口仍严格校验代码身份，不复用旧代码就绪证明。

本地测试只执行离线/模拟链路；真实 PostgreSQL、Linux 内核隔离和模型修复效果仍需服务器证据。
