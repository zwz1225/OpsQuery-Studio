# M1 A：DuckDB 统一运行上下文实施与验收

实施时间：2026-10-06 至 2026-10-07。

## 1. 当前状态

**M1 A DuckDB 统一上下文验收及资料归档已完成（2026-10-07），已知 WARN 和回复质量事项继续留存：服务器 Gold 79/79、classic 正式别名离线复评分 49/49、E2E 行为 8/8 与结果评分 2/2 均已审核通过。服务器与本地复评分结果行完全一致，8 题的 13 项显式别名已同步验证。** 详见 [最终功能验收结论](M1_A_FINAL_ACCEPTANCE.md)、[别名校准收尾记录](M1_A_CLASSIC_ALIAS_CALIBRATION.md) 和 [服务器归档核查](results/m1_a_server_archive_review.json)。 PostgreSQL 适配、隔离导入和跨后端验收尚未实施。当前 `DATA_BACKEND` 仅支持 `duckdb`，设置其他值会明确报错。

本阶段保留逻辑数据库 `short_video_ops`、业务表／字段 ID、角色范围、M0 逐题列别名和并列评分规则。评测器与应用版本发生变化，新的报告使用 manifest v2 并携带源身份；旧 M0 报告保持原样，不使用它们续跑新实验。

## 2. 已实现的调用关系

```text
启动配置 → create_datasource_runtime
             ├─ SourceIdentity：source ID／backend／dialect／catalog／data version
             ├─ CatalogSnapshot：不可变内容，读取时返回独立字典
             ├─ DuckDbEngine：只读 SQL、范围校验、执行与取数
             └─ CsvMetadataProvider：catalog、受控字段 profile
                    ↓ 同一个 runtime 注入
          Service → SchemaIndex／Workflow／SchemaGraph／Agent → MCP
                    ↓ 同一个 executor
          Benchmark／E2E → Gold／完整结果重取数
```

主要代码入口：

- [runtime.py](../app/datasources/runtime.py)、[contracts.py](../app/datasources/contracts.py)：源身份、最小协议、生命周期与一致性检查。
- [csv_metadata.py](../app/datasources/csv_metadata.py)：业务快照、源文件内容摘要、受控采样。
- [sql_policy.py](../app/datasources/sql_policy.py)、[DuckDbEngine](../app/querying/duckdb_engine.py)：共享只读策略、限定来源、权限与兼容结果。
- [SchemaIndex](../app/retrieval/service.py)、[SchemaGraph](../app/retrieval/graph.py)：通过上下文取得 catalog，检索层不再直接调用驱动采样。
- [AskDataService](../app/services/askdata_service.py)、[QueryWorkflow](../app/workflows/query_graph.py)、[MCP server](../app/mcp_runtime/server.py)：共享执行器、动态方言说明及任务身份。
- [run_benchmark](run_benchmark.py)、[run_e2e](run_e2e.py)、[Gold resolver](gold_result.py)、[run_manifest](run_manifest.py)：查询、Gold、截断后的重取数使用同一来源。

### 边界与兼容性

1. 默认配置为 `DATA_BACKEND=duckdb`、`DATA_SOURCE_ID=short_video_ops_duckdb`。本阶段没有新增模型密钥要求或修改用户 `.env`。
2. runtime 在装配时读取 catalog／内容摘要，执行时创建并释放原有临时 DuckDB 连接。CSV 数据作为固定验收材料；修改数据或配置后重启并创建新实验，运行中不替换材料。
3. 预览仍为 200 行，评分上限仍为 10,000 行，以 `row_limit+1` 判断截断。失败、成功零行和截断保持不同状态。
4. 查询入口、评分执行器或请求身份不一致时拒绝执行；LangGraph checkpoint 保存源身份，恢复时检查完整身份，无法恢复其他来源／版本的任务。
5. `close` 可重复调用。创建 runtime 的调用方负责关闭；注入它的 SchemaIndex／Service 不擅自关闭共享对象。FastAPI shutdown 和 runner 的上下文退出释放拥有的 runtime。
6. 保留历史 `DuckDbEngine()` 和旧接口的直接调用兼容性，供 M0 离线脚本使用；正式服务及两个评测 runner 已接入 runtime。
7. 四类业务 SQL 校验／规划器、澄清及 ResultBuilder 中部分业务定义仍经由原 `database.py`；本阶段固定使用同一业务材料。PostgreSQL catalog 合并和这些消费者的完整方言改造属于后续 C／D，不宣称已支持 PostgreSQL。

## 3. 索引、缓存和来源校验

- 默认索引位置改为 `backend/data/schema_stores/<source_id>/schema_store.json`。
- 索引签名包含 backend／dialect、catalog 与 CSV 内容版本；同一 runtime 内使用构建锁，文件以临时文件加原子替换发布。
- Gold 默认保存到 `backend/evaluation/cache/gold_results/<source_id>/`；实际源身份、数据版本及 Gold SQL 参与有效性校验。
- 原 `schema_store.json` 和旧 Gold cache 不删除。新目录首次需要建立对应 Embedding 索引；这会调用既有 Embedding 接口。
- DuckDB SQL 可使用无前缀表名或合法 `main.table`；拒绝把业务 ID 当 schema、错误 schema 或跨 catalog 来源。CTE 按作用域解析，避免同名 CTE 掩盖真实表权限检查。
- manifest v2、续跑指纹和回归比较身份均记录源；缺少身份的 M0 历史运行不会冒充新运行的同源回归。

这部分保持原检索算法和评分器：未添加通配列别名，未放宽排序、并列、权限或结果评分。

## 4. 本地验证证据

| 验证 | 结果／证据 |
|---|---|
| 改造前测试基线 | 基础 Python 环境运行 255 项，3 项因缺少 LangGraph 跳过 |
| 改造后完整测试 | 项目 `.venv` 运行 **272 项全部通过，无跳过**；[日志](results/m1_a_unittest_local.log) |
| 新增运行上下文测试 | 17 项；[测试文件](../tests/test_datasource_runtime.py)，包含真实服务／MCP、错源拒绝、CTE 权限、关闭、取数、动态 profile 与并发索引发布 |
| M0 核心行为 | 既有路由、澄清选项语义、真实 LangGraph 中断／同任务恢复、单日条件、空结果与评分测试通过；不是新的 live 模型验收 |
| 索引文本等价 | **276 个字段文档逐项相同**；[等价记录](results/m1_a_index_content_equivalence_local.json) |
| 数据／用例材料 | 原审查中的 44 个不同输入文件摘要一致，未改写原题集或 CSV |
| 改造后静态审查 | 全部 5 项一致性检查通过；[当前审查](results/m1_a_datasource_dependency_audit.json)，[原审查](results/m1_datasource_dependency_audit.json) 留存 |
| 独立 DuckDB Gold | 原 classic49＋扩展30，**79／79 执行与严格结果通过，0 条未评分、0 次模型请求**；[结果](results/m1_a_duckdb_gold_local.json)，[题集清单](cases/m1_a_duckdb_regression.json) |

最终结果与源／代码摘要汇总于 [本地验证 JSON](results/m1_a_runtime_verification_local.json)。本次没有调用在线模型，也没有执行 PostgreSQL。

静态审查 JSON 中 `runtime_behavior_changed=false` 表示审查脚本本身只读、不调用应用，不表示 M1 A 没有改动代码。Gold 延迟来自本地运行环境，不能直接与远程服务器 M0 延迟作性能回归结论。

本地完整测试使用 Python 3.10.9，依赖为 LangGraph 1.2.11、DuckDB 1.5.5、SQLGlot 30.17.0、MCP 2.2.0、FastAPI 0.116.1。服务器 Python 3.11 的运行结果需独立保留。

## 5. 同步与服务器验收

同步清单见 [变更清单](results/m1_a_change_manifest.json)。同步代码、测试、新增 79 题清单和 `.env.example`；服务器现有 `.env`、`.venv`、数据及 M0 报告继续保留。停止旧服务后同步并重启，使整个进程使用新上下文。

在服务器项目的 `backend` 目录、原 py311 环境中依次运行：

### 5.1 单元与集成回归

```bash
python -m unittest discover -s tests -q
```

应为 272 项通过且无跳过。出现依赖缺失时按现有 `requirements.txt` 核对环境，不能将集成测试跳过视为验收通过。

### 5.2 同一服务器数据上的 79 题 Gold

```bash
python -u -m evaluation.run_benchmark \
  --mode gold --scope all --no-use-cached-gold \
  --case-list evaluation/cases/m1_a_duckdb_regression.json \
  --save-snapshot \
  --output evaluation/results/m1_a_duckdb_gold_server.json
```

检查 79 题 complete、全部可评分、执行与 strict 结果正确率，以及 manifest 的 source ID／backend／dialect／数据摘要。

### 5.3 独立 classic live

```bash
TIME_FIELD_SUPPLEMENT_ENABLED=false python -u -m evaluation.run_benchmark \
  --mode live --scope classic --workers 1 --no-use-cached-gold \
  --save-snapshot \
  --output evaluation/results/m1_a_live_classic_server.json
```

检查 49 题 complete、SQL／结果／strict 指标及逐题错误。与 M0 经典集作明确的前后分析；应用、评测器和源身份格式已有变化，不能用允许不兼容选项将它们包装成正式同源自动回归。

### 5.4 八条服务入口行为

```bash
TIME_FIELD_SUPPLEMENT_ENABLED=false python -u -m evaluation.run_e2e \
  --case-list evaluation/cases/e2e_behavior.json \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_a_e2e_behavior_server.json
```

检查 8 类行为全部通过、2 条正式 SQL 结果评分通过；其余 6 条行为不计入 SQL 正确率，并检查最终回复、校验原因和 WARN。将上述三个新 JSON 下载到本地 `backend/evaluation/results/` 后逐题审核，不能只看汇总百分比。

## 6. 后续阶段

服务器回归确认后进入 B：准备隔离 PostgreSQL 库、按原物理类型导入 41 表并验证内容，形成独立导入版本。随后实施 C 的 adapter／元数据和 D 的完整方言传递／Gold 变体。当前依然保留 M0 的月份 WARN、回复质量跟踪及预算允许后的 430 题全量 live，M1 A Gold 回归不替代这些工作。
