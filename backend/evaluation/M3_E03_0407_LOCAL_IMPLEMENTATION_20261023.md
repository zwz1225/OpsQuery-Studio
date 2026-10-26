# M3 E03：0407 不完整关系与双列输出候选的本地实现

后续状态（2026-10-23）：服务器尚无有效 E03 同轮对照；已观察到 PostgreSQL 未运行及系统解析器间歇性 `EAI_AGAIN`。已完成 [公共连接层 v2 / r2](M3_E03_TRANSPORT_V2_SERVER_RUNBOOK_20261023.md)，在两侧共享有界恢复、失败用量记录和生成登记前 DNS 就绪检查。本地通过不代替服务器验收，不修改原 E02 已通过结论。

日期：2026-10-23。状态：本地代码、定向测试及 [独立服务器同轮包](M3_E03_PAIR24_SERVER_RUNBOOK_20261023.md)已完成；尚未运行服务器模型对照或原生复评。

## 接入边界

新增诊断入口组合：`--schema-coverage --intent-candidate --condition-relations --output-contract --relation-output`。最后一个开关是 E03 专用；原 E02 `--condition-relations` 仍不能单独与 `--output-contract` 合用。入口只允许开发诊断，不改变 Gold、评分、SQL 校验、修复次数或模型预算。

冻结 [来源核查](M3_E03_0407_VERSION_BOUND_RELATION_REVIEW_20261022.md)记录 BIRD 包内 SQLite 外键和 `dev_tables.json` 关系；`reviewed_relations.py` 绑定相应哈希、现有 PostgreSQL 来源身份与只读角色。候选继续显示 `eligible=false`、`decision_reason=incomplete_child_key_coverage`；仅 E03 在来源、版本、授权、键类型、父键唯一性和独立归属证据全部通过时可使用 `limited_eligible=true`。记录的16条孤儿不会被抹去，也不产生 PostgreSQL 约束。

授权图中的公开双列输出组由原 question/evidence 和当前 catalog 唯一绑定；语言条件由公开 evidence 与问题共同绑定，资料不完整、冲突或不唯一时停止。一个唯一的不完整候选可补两端键。若20字段已满，按原分数从非公开需求、非关系键的正分字段中确定性移出足够名额，记录原分数和原因；无安全名额则返回 `context_field_cap`。不扩充字段上限、不预选 JOIN 类型，不自动改写 SQL。

输出组仍通过原有 `output_contract` 作为生成提示和报告型观察，检查器不参与 SQL 拒绝或评分。关系上下文另记公开输出列、筛选列、来源和孤儿数，说明当前 PostgreSQL 未声明此外键。E02 1479 的原路径保持独立。

## 本地验证

- `test_m3_condition_relations.py`：11/11 通过，覆盖 E02 原有来源门槛、1479 路径和字段上限。
- `test_m3_e03_0407_evidence.py`：14/14 通过，新增满额键位腾挪、来源或审查哈希缺失、不完整公开输入、无法安全腾挪、1479 条件路径保持与 E02/E03 开关隔离。
- 修改的 Python 模块通过 `py_compile`。测试均无模型调用、无 PostgreSQL 连接、无 Gold SQL 或 holdout 输入。

下一关是独立的服务器基线／E03 候选同轮实验。需要先冻结代码、来源、模型、索引与预算，再用新报告名执行；重点检查实际首次 SQL 是否同时采用双列、德语条件和有依据的连接，及20道成功回归题、token和延迟。

## E03 独立包

`M3_E03_pair24_sync_20261023.zip` 的 SHA-256 为 `61e9af6373f7b41058ddba50658c9f2ea4823fde20ae1b3624ea9beac38956e9`。两侧都以已保存的 E02 候选快照作为起点：基线98个 Python 文件，候选99个；候选仅修改 `retrieval.py`、`case_worker.py`、`diagnostic_runner.py`、`demand_relations.py`、`reviewed_relations.py`，并添加 `output_contract.py`。24题题单与 E02 保持相同顺序。E03 侧的顶层策略标签已修正为 `bird_public_relation_output_context_v1`，逐题标签与之对应。包内无私密配置或数据库数据；静态包身份与 E02 来源快照经本地校验。
