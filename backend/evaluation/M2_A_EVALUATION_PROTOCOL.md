# M2 A：固定题集与评测协议 v1

冻结日期：2026-10-15。协议 ID：`m2_bird_pg_v1`。这是 M2 A，后续为受控数据导入和通用来源适配。

本阶段已经完成**离线协议和清单冻结**：500 题来源版本、80 道开发题、30 道保留题、8 道开发集内 smoke、公开输入、评分器专用 Gold、资源预算及来源材料摘要。数据库运行上下文、导入、Gold 执行和 live 尚未完成。机器协议的 `stage_status` 明确为 `protocol_frozen_runtime_integration_pending`。

主要材料：

- [机器协议](cases/bird_mini_dev/m2_pg_v1/protocol.json)
- [开发集 80 题清单](cases/bird_mini_dev/m2_pg_v1/development80.json)
- [保留集 30 题清单](cases/bird_mini_dev/m2_pg_v1/holdout30.json)
- [smoke 8 题清单](cases/bird_mini_dev/m2_pg_v1/smoke8.json)
- [冻结记录](results/m2_a_protocol_freeze_20261015.json)、[独立重建复核](results/m2_a_protocol_recheck_20261015.json)
- [本地数据就绪记录](results/m2_a_data_ready_20261015.json)
- [后续受控导入方案](M2_B_CONTROLLED_IMPORT_PLAN.md)

## 数据与抽样方法

任务使用原始 Mini-Dev 500 题的 PostgreSQL 文件，保留英文原题和官方 evidence。Hugging Face 提交、题目、原始包、SQL dump 与 75 份字段说明均固定摘要，见 [来源血缘清单](cases/bird_mini_dev/m2_pg_v1/source_lineage.json)。包内旧题目/Gold 仅作版本审计，正式 Gold 取冻结版 Hugging Face 的 `SQL` 字段。

抽样种子是 `askdata-m2-bird-pg-v1`。先将 11 个 `db_id` 按 `SHA256(seed|database|db_id)` 排序，前 3 个归入保留域，其余 8 个归入开发域。每域按官方难度选 3 道 simple、5 道 moderate、2 道 challenging，域内按 `SHA256(seed|question|question_id)` 排序取样。该算法不使用问题、evidence、Gold SQL 或执行结果进行挑选。缺少配额会报错，不补换其他难度。

| 集合 | 题数 | 域数 | 难度：简单 / 中等 / 困难 | 用途 |
| --- | ---: | ---: | --- | --- |
| development80 | 80 | 8 | 24 / 40 / 16 | 开发、诊断、确定配置 |
| holdout30 | 30 | 3 | 9 / 15 / 6 | 配置固定后的保留评测 |
| smoke8 | 8 | 8 | 每个开发域选 1 题，具体见清单 | 联调；是 80 题的子集 |
| 未选题 | 390 | — | — | 本轮不使用，不计入成绩 |

开发域：`california_schools`、`card_games`、`codebase_community`、`debit_card_specializing`、`financial`、`student_club`、`superhero`、`toxicology`。

保留域：`european_football_2`、`formula_1`、`thrombosis_prediction`。开发域和保留域没有交集，110 个题号互不重复。该划分只保证本项目不利用保留题反馈调参；公开数据可能已在模型训练材料中出现，不能称为私有未知测试。

## Agent 输入与评分器边界

`inputs/` 下仅保存 `case_id`、`database_id`、`dialect`、`question`、`evidence`。`difficulty`、Gold SQL、期望结果、Gold 检索词均不进入这些文件。官方 evidence 原文提供；是否不提供 evidence 属于另一版实验协议。

`scorer/gold110.jsonl` 只供评分器使用，保存题号、来源、原始 PostgreSQL Gold SQL 及 SQL 摘要。这个目录的用途标记不等于已经实现操作系统权限隔离；未来 runner 和工具必须只加载白名单公开字段，索引不能扫描整个题库/项目目录。实际运行时的隔离仍是 live 前置门槛。

每题从自然问题和允许的 evidence 进入通用服务路径，读取该 `database_id` 授权范围内的实时 schema、官方字段说明和受控值样例。每字段至多 3 个不同值，按数据库原生类型升序、NULL 最后；文本样例最多 64 字符，记录截断。不注入 Gold 派生字段或检索词，不套用短视频指标目录，不使用跨题记忆。检索阈值及 Top-K 沿用协议中冻结的 M1 基线参数。

每题从独立会话开始。若系统请求澄清，记录澄清状态并计为本轮未解答；不根据 Gold 自动回答或选择澄清选项。

## EX 主评分规则

已阅读并固定[官方 EX 实现](https://github.com/bird-bench/mini_dev/blob/abd11b6db92a1c9f809b32f7564c7c71b34d67f0/evaluation/evaluation_ex.py#L18)，提交为 `abd11b6db92a1c9f809b32f7564c7c71b34d67f0`；原始 Git 字节摘要和关键函数快照写入协议。连接、权限、事务、来源选择与超时使用本项目受控适配，不直接运行官方连接辅助代码。

主比较谓词为 `set(predicted_native_row_tuples) == set(gold_native_row_tuples)`。忽略列名、结果行顺序、重复行出现次数；保留每行中各列值的位置，比较原生 PostgreSQL 驱动值。没有额外浮点容差、字符串转数值或全局/逐题别名。Decimal、日期和 NULL 应在 JSON 序列化前参与比较，不能先丢精度或把值全转成字符串。

两边都空时按官方集合语义通过；列值对调不因列名相似而通过。主 EX 本身不检验排序与重复行次数，另外记录有序结果、多重集和列数诊断，不能拿主 EX 声称这些条件也已满足。Soft F1、R-VES 暂不纳入本轮主分。

主指标为：**EX 通过题数 / 固定集合全部题数**。模型错误、SQL 错误、权限拒绝、澄清、超时、结果超限等均不能从分母删除。另报完整结果条件下的 EX、首次/最终 SQL 成功率、分数据库/难度结果、失败分类、延迟、模型请求和 usage。无法获取 usage 时记录未知，不能填 0。

预览和部分结果禁止评分。行数、结果负载或时间超限时，正确性为未知，主分贡献为 0，并保留明确失败原因。此规则既避免只对已执行成功题报告高分，也不把超限与已证明的语义错误混为同一原因。

本轮是自选子集、提供 evidence 的 Agent 任务。虽然保留了官方 EX 比较语义，来源隔离、事务和资源限制均为项目条件，结果不能作为完整官方执行框架或官方排行榜成绩，也不与内部 430 题合成一个百分比。

## 模型与资源预算

| 项目 | 固定值 |
| --- | --- |
| 模型 | `qwen3.7-plus`，temperature=0，thinking=false |
| Embedding / Rerank | `text-embedding-v4`（1024 维） / `qwen3-rerank` |
| 并发 | 1 |
| 单题整体时间 / 单次模型请求 | 600 秒 / 180 秒 |
| 总模型 HTTP 尝试 / 其中 Chat 尝试 | 最多 16 / 10，含传输重试 |
| 每请求传输重试 | 最多 1 次，共享计数；不能另开无界循环 |
| 单次 Chat 输出 / 提示词大小 | 最多 4096 token / 98,304 UTF-8 字节 |
| SQL 工具调用 / 每轮校验尝试 | 最多 3 / 3 |
| PG 连接 / SQL / 锁等待 | 10 秒 / 30 秒 / 5 秒 |
| 评分结果上限 | 每边 100,000 行、64 MiB，额外读 1 行探测超限 |

模型名称沿用 M1 v7 报告。服务商模型别名可能更新，每次运行还需记录返回的模型标识、时间和配置指纹。所有生成、预处理、Embedding、Rerank 和传输重试计入共享单题预算；预建索引单独报告成本。Gold 预执行在正式单题预算外单独记录。

**预算已写入协议，但现有内部 runner 尚未实现这些外部约束。** 后续必须在外部 runner 中落实整体终止、计数、输出上限和完整结果边界，再开始 live。不能因为 JSON 已写了上限就声称执行受到了限制。

## 执行顺序与保留集使用

1. 按[受控导入方案](M2_B_CONTROLLED_IMPORT_PLAN.md)准备独立目标和 11 个逻辑域的授权映射，验证数据、catalog 和权限版本。
2. 评分器对选中的 110 道 Gold 做预执行，确认全部为支持的完整结果。发生源数据、Gold、权限或资源问题时保留题号和证据，阻止正式 live；任何规则或 Gold 修订另起协议版本，不能静默删题换题。
3. 用开发集内的 smoke8 联调，再跑 development80。只使用开发集反馈定位问题。
4. 绑定已验证来源、数据/catalog、权限、代码、Prompt、依赖、模型、检索参数和预算，固定候选版本，之后运行 holdout30。
5. 每个固定候选保存一轮正式保留评测及所有失败/中断尝试。观察保留结果后用于调参的后续运行须明确披露复用及版本变化，不能继续描述为未参与调参。

Gold 预执行只用于评分侧验证环境，不能向 Agent 或调参路径传递保留题的答案提示。除 M2 本地文件摘要外，运行时还必须有真实目标验证版本；不能把尚未导入的源文件摘要冒充目标数据版本。

## 本地复核

在 `backend` 中运行专项测试：

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_m2_bird_protocol.py -v
```

本次 14 项专项测试通过，覆盖数据库分离、难度配额、抽样确定性、Gold 不参与选题、公开字段白名单、原生 EX 与固定官方函数的一致性、NULL/精度/空结果、截断拒绝，以及冻结产物篡改和覆盖拒绝。

本地已有完整数据与官方 Git 克隆时，可重新生成并逐字节检查清单；输出报告必须用新文件名：

```powershell
.venv\Scripts\python.exe -u -m scripts.freeze_m2_bird_protocol --check `
  --report evaluation/results/m2_a_protocol_recheck_20261015_v2.json
```

首次冻结报告和独立复核均通过，11 个产物完全一致。内部运行入口和评分策略没有接入这些文件；当前不能直接用旧 `evaluation.run_benchmark` 对这些新题号开始 PostgreSQL live。
