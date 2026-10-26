# M3 E05：公开字段角色边界与端点候选

日期：2026-10-24。状态：**两类问题的正反例已整理；0239 类端点范围候选、测试、无模型扫描及独立服务器配对包已完成。尚未在服务器运行 E05 对照。**依据是 [E04 0072/0239 离线语义审查](M3_E04_0072_0239_OFFLINE_SEMANTIC_REVIEW_20261024.md)。本地准备没有调用模型、连接数据库或读取 Gold 来选择运行时触发条件。

## 1. 先分开两个字段角色问题

### 0072：地点、名称和邮寄地址

来源字段说明里 `schools.City` 是城市，`schools.School` 是学校名，`schools.MailCity` 是邮寄地址的城市。0072 的公开问题说“school in Fremont”，但这轮授权 Schema 图缺少 `City`，模型用了 `School='Fremont'`。参考输出为两行，公开问法也可能被理解为一个合计；因此该题当前不能只靠单个 EX 结果验证城市字段补齐策略。

| 公开问法或来源状态 | 应保留的判断 |
| --- | --- |
| “school in Fremont”，来源表有物理城市 `City` | 将 `City` 作为地点字段候选，保留 `School` 作为学校名称字段；不自动将二者等同。 |
| “school named Fremont” | `School` 是名称候选；不能强加 `City='Fremont'`。 |
| “mailing address in Fremont” | `MailCity` 是邮寄地址候选；不能静默替代物理城市。 |
| 来源中同时存在 `City` 和另一同名城市字段，无法确认所属实体 | 记录归属不明，保持提示态。 |
| 只有问题词“Fremont”，没有地点、名称或邮寄语境 | 不能仅凭值强制定列。 |
| “How many ...”可能匹配多个学校 | 不从这几个字直接推断必须合计或必须逐校；独立登记结果形态歧义。 |

城市方向需要先验证公开问法到授权字段的选择，不使用 Gold 的两行结果或数值设定规则。本轮没有修改城市字段检索策略。

### 0239：公开 evidence 指定的关系端点

0239 同时有明确的计数对象 `bond_id` 和过滤字段 `atom_id LIKE 'TR%_19'`。模型却额外加入 `OR atom_id2 LIKE 'TR%_19'`。这是可从公开 evidence、授权字段与已保存 SQL 直接观察的作用域扩展。0072 的形态歧义不会干扰此题的一行计数输出，所以优先选它作为 E05 本地候选。

| 正反例 | 候选行为 |
| --- | --- |
| “connections refers to bond_id; atom 19 refers to atom_id like 'TR%_19'” 且唯一授权表同时拥有两字段 | 形成明确的 `connected.atom_id` 端点建议；保存公开模式。 |
| SQL 在上述条件上额外 `OR atom_id2 LIKE 'TR%_19'` | 记录 `explicit_endpoint_widened_by_or` 诊断，级别为 advisory。 |
| SQL 仅以 `atom_id LIKE 'TR%_19'` 过滤 | 不记录端点扩展。 |
| SQL 使用 `atom_id2 IS NOT NULL` 等不同含义的条件 | 不能仅因提到第二端点就判错。 |
| 问题明确要求一个 bond 的两个原子或两端元素（例如公开开发题 0206） | 不触发本候选的单端点模式；保留两端查询的合法空间。 |
| evidence 写明 `atom_id OR atom_id2`、带不确定措辞，或缺少计数对象字段 | 不形成唯一字段建议。 |
| 两张授权表都同时拥有计数与过滤字段 | 不猜表的归属；仅记录归属歧义。 |
| 换成别的授权库、字段名和公开模式 | 仍按公开 evidence 与来源字段绑定，不按 0239 的题号或字段名特判。 |

## 2. 本地候选和证据

候选模块是 `evaluation/bird/endpoint_scope.py`，策略 ID 为 `m3_public_explicit_endpoint_scope_candidate_v1`。它验证公开输入，只识别两个独立的 `refers to` 子句：一个指定计数对象字段，另一个指定 `LIKE/ILIKE` 过滤端点。只有这两个字段在同一授权数据库中唯一落到一张表，且公开问题明确提到两项主体时，才形成建议。SQL 观察器只检查简单单表 `SELECT` 中与公开模式相同的 `OR` 扩展；不拒绝、不自动改写 SQL。复杂 SQL、归属不唯一或证据不明确时留给原有流程。

正反例位于 `tests/test_m3_e05_endpoint_scope.py`，7 个测试通过，覆盖真实公开问法、改名后的通用表和字段、归属不唯一、双端点请求、0206、0072、case ID 不参与触发、私有字段输入拒绝。项目当前 Agent 不导入该模块；独立 E05 候选包中的 Agent 才导入它，并仅把公开字段建议写入生成上下文。**模型 SQL 是否改善仍待服务器对照验证**。

无模型扫描由 `scripts/audit_m3_e05_endpoint_scope.py` 生成 `results/m3_e05_endpoint_scope_offline_local_20261024.json`。它读取冻结 development80 的 80 条公开输入、已授权导入清单，以及 SHA-256 固定的 E04 candidate 24 题捕获报告；不读取 scorer Gold。扫描结果：80 题中仅 `BIRD-PG-0239` 满足这套保守的公开字段绑定语法；在已保存的 24 题 SQL 中，该题出现 `explicit_endpoint_widened_by_or`。本报告新增模型请求为 0、数据库连接为 false、正式评测为 false。

本地审查的固定输入摘要：公开 development80 `6760724e98b6da967ac5ebb2698c4e5cab385875bd150ad36a3b252ffdc52f03`，授权导入清单 `c32dbeeb015359126e393aabbe470ed4052463e69a407d7b2ba158f4349b8879`，E04 candidate 捕获 `a4ede17c434aad8d0e7145f4574e8a8ff812228263841cbb25f207a39a7b4578`；候选模块 `f3c6674579f60d86e8eeb526d9f9fbabba10de94b689c067acdf38dfa686a905`。

## 3. 进入实验前的边界

E05 服务器包 `M3_E05_pair24_endpoint_scope_v1_20261024.zip` 已冻结，两侧从同一个 E02 语义与公共连接层代码身份出发；候选侧只接入本模块给模型的公开端点提示，保持原 SQL 校验/预算/原生评分。该建议是 advisory，不把字段模式变成硬拒绝，也不依据 Gold 的 `RIGHT(atom_id,2)` 或目标数字 377 自动改写 SQL。详见 [E05 运行说明](M3_E05_PAIR24_SERVER_RUNBOOK_20261024.md)。

先用 0239、0072、0092、0356 和已冻结的 20 道成功回归题做受控同轮 24 题；检查 0239 的首次 SQL 是否保留公开端点、原生结果是否改善，以及 0206 等两端点任务是否回归。若 24 题有收益，再考虑完整 development80。既有 holdout 已观察，不重新当作盲测。现阶段不能宣称 E05 候选通过验收。
