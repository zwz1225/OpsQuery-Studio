# M1 D2：SQL 生成、解析和校验统一运行上下文

日期：2026-10-10。状态：本地实施通过；用户提供的服务器全量回归日志确认427项测试在26.516秒内全部通过。

## 1. 实际改动

| 环节 | 规则与改动 |
|---|---|
| SQL 上下文 | 新增 `app/querying/sql_context.py`。由调用者注入 runtime，不创建连接，不另行选择后端。检查 runtime 打开状态、backend/dialect 对应关系、catalog 版本、逻辑数据库和 Schema 图来源。 |
| SQL 生成 | Agent 和应用级 database_query Skill 明确当前方言、物理 schema 与引用规则。模型请求的 sql_context/source_identity 和工具调用记录来自同一个 runtime。PostgreSQL 提示包含日期格式、整数除法及 numeric 舍入规则。 |
| 完整字段校验 | SQLValidator 使用 runtime.catalog 的完整字段；检索结果只是子集，不能证明其他字段不存在。runtime 中没有的静态字段、检索图伪造字段不能补入。调用前沿用执行器的只读、schema、表、权限规则，再检查列。 |
| 指标规划 | MetricPlanner 的标准指标字段存在性核对和 SQL 解析读取同一 runtime；业务指标目录仍为既有独立口径定义。实际 catalog 缺少标准指标字段时明确失败，不能借静态 Schema 通过。 |
| 日期定位 | ConstraintPlanner 从 runtime catalog 扩充日期候选，范围限于可访问 Schema 图与实际 SQL 来源的交集，继续要求明确用户字段标签。 |
| 日期/粒度校验 | ConstraintValidator 按实际方言解析，用当前 catalog 定位无前缀字段；支持 SQLGlot 归一化后的 TO_CHAR/STRFTIME 和 DATE_TRUNC 节点。明确日粒度不能由月粒度替代。未确定表达式仍保留 WARN。 |
| MCP | 工具说明、参数 JSON Schema 和服务器 instructions 均包含实际后端、物理 schema、引用规则。工具始终调用该 runtime 的 executor。 |
| 工作流/报告 | 执行阶段统一为 sql_execution，并保存 backend、dialect 和 source_identity。结果步骤使用实际数据库名称，表标签来自当前 Schema 图。Gold/live trace、E2E 记录和 trace 展示保留真实来源字段。 |

允许 `表名` 或 `受控物理schema.表名`，字段可用 `表别名.字段名`。业务数据库 ID 是工具/权限标识，不能作为 SQL schema/catalog 限定名。

正式 QueryWorkflow 注入同一个 runtime 到 Agent 与四个规划/校验器，并检查对象共享关系。未注入 runtime 的既有独立 DuckDB 调用保持兼容；明确的 PostgreSQL Schema 图缺少 runtime 时拒绝，不回退到 DuckDB。不同 runtime 的 Schema 图也明确拒绝。

## 2. 已完成的本地验证

- 23 项 D2 专项测试通过，包括两后端引用规则、完整字段与静态 Schema 隔离、PostgreSQL CAST/CTE/TO_CHAR/DATE_TRUNC、日期边界、指标来源、错误 schema、应用权限、来源混用、关闭状态、模型修正后再执行、MCP 参数说明及报告标签。
- 全套 **427 项测试通过**，0 failure、0 error、0 skip。执行记录：[m1_d2_regression_local.json](results/m1_d2_regression_local.json)。
- 现有 **430 题原始 DuckDB Gold SQL** 按当前 runtime、完整 catalog、原场景权限进行调用前校验，全部 PASS。这是解析与引用兼容性检查，未执行这 430 条 SQL，不代表 430 题结果或模型生成验收。
- 三条代表题 GROWTH_OPS-001、CHANNEL_OPS-069、CONTENT_OPS-029 经实际 Agent 校验链路、MCP 进程内传输和 DuckDB 执行，严格结果均一致。SQL 决策由本地固定替身返回，无模型 API 请求。
- 正式题集 SHA256、源数据版本和已验收 C3 原始报告 SHA256 与 D1 留存记录一致。
- 实施证据：[m1_d2_implementation_local.json](results/m1_d2_implementation_local.json)。PostgreSQL 专项用显式测试替身，未连接远程数据库。本地通过不能替代后续正式 PostgreSQL Gold/live/E2E 验收。

## 3. 同步和服务器复核

本次同步包：项目根目录 `M1_D2_SQL运行上下文同步包_20261010.zip`。完整上传并解压，避免测试文件和实现文件混用版本。

```bash
cd ~/Python_work/askdata_studio_ops_release
ls -lh M1_D2_SQL运行上下文同步包_20261010.zip
unzip -o M1_D2_SQL运行上下文同步包_20261010.zip
cd backend

python -m unittest discover -s tests -p 'test_m1_d2_sql_runtime.py' -v
python -m unittest discover -s tests -q
```

预期先 23 项通过，再 427 项通过。两条命令均不需要模型密钥，也不连接远程 PostgreSQL。无需新 .env 参数；保持现有默认 DuckDB 和已验收 PG 配置。这里的本地 JSON 是实施证据，不是服务器本次运行报告。

此前用户提供的服务器日志已确认 D1 的17项专项测试通过，C3报告写入修复同步后全套404项测试在25.664秒内通过。随后提供的D2服务器全量日志确认427项在26.516秒内通过，包含D2新增测试；未单独提供23项专项命令日志。本地原始证明文件保持不变。

## 4. 后续顺序

已进入D3：制作和逐题审查正式PostgreSQL Gold SQL变体，先覆盖79题（classic49 + 扩展30），再扩展至全部430题。首轮79题已保存显式变体、完成离线审查，并通过实际PostgreSQL Gold执行与下载报告一致性核对；详见 [D3验收说明](M1_D3_POSTGRES_GOLD79_ACCEPTANCE.md)及 [服务器核对记录](M1_D3_POSTGRES_GOLD79_SERVER_REVIEW.md)。报告没有完整返回行，独立逐值复评分尚未执行。

后续再完成D4的索引/缓存/报告来源隔离复核与独立跨后端比较，以及正式PostgreSQL live与E2E验收。当前正式题集79题已具备变体，剩余351题仍由D1规则明确拒绝缺失变体的评分。

本步只完成方言和 catalog 贯通。M0 留存的业务口径/回复质量问题继续独立跟踪；未确定的校验表达式继续保留 WARN。
