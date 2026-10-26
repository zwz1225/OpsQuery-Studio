# M3 E06：明确端点条件的离线校验反馈审查

日期：2026-10-24。范围：BIRD Mini-Dev 开发题的公开问题、evidence、已授权 catalog 和 E05 保存的 SQL。此审查没有调用模型、连接数据库、读取 Gold 或改动正式评分。

## 现象与依据

- E05 同轮对照有效，但 baseline 和 candidate 都为 22/24，0239 均未修正。E05 给出了端点范围提示，但保存的首次 SQL 仍把 `connected.atom_id LIKE 'TR%_19'` 与 `connected.atom_id2 LIKE 'TR%_19'` 用 `OR` 相连；首次校验通过，没有进入修复流程。
- 0239 的公开 evidence 将 `atom 19` 明确映射为 `connected.atom_id LIKE 'TR%_19'`，并把“连接数”的计数字段映射为 `bond_id`。反馈可以准确指出：同一模式在另一端点上的 `OR` 扩大了公开指定的筛选范围。这一判断不依赖参考答案数值。
- 0206 的公开 evidence 指定的是 `bond_id = 'TR004_8_9'`；问题询问该 bond 的 atoms，没有将任务限制在某一个端点。保存的双端点 `UNION` SQL 因此不应受 0239 规则约束。

## 离线规则与边界

`evaluation/bird/endpoint_validation.py` 是尚未接入服务的提案。仅当公开证据唯一绑定一个端点和计数指标，并且 SQL 是单条、单表、简单计数 SELECT、WHERE 恰好把该端点与另一个已授权字段上的相同 `LIKE/ILIKE` 模式用 `OR` 相连时，返回 `candidate_repair`。反馈包含公开依据、两个字段、运算符、模式、原因和修复方向，以及原 SQL 的哈希。

证据不唯一、题目明确要求两端、联表、CTE、UNION、额外条件、不同模式、不同计数路径、多语句、字段归属不明等情形一律弃权。已正确保留指定端点的简单 SQL 返回 `pass`。规则不按题号硬编码，也不重写 SQL。

现有修复通道已具备结构化 `intent_contract_violation` 反馈、重复 SQL 阻断和预算限制。单元测试用模拟运行上下文验证反馈可进入该通道；正式 `case_worker` 尚未调用本提案。若制作独立候选，拟在只读 SQL 结构校验通过之后、执行查询之前调用，并沿用原有生成与预算上限。

## 已核查结果

- `python -m unittest discover -s tests -p 'test_m3_e06_endpoint_validation.py' -v`：8 个测试通过。覆盖 0239 正例、正确端点 SQL、0206 原始双端点 SQL、明确双端点问题、复杂 SQL、多语句、不同模式、未授权或歧义字段，以及修复反馈和重复阻断。
- 离线复查报告：`evaluation/results/m3_e06_endpoint_validation_offline_local_20261024_v2.json`，`run_status=complete`。E05 两侧各 24 条保存 SQL：各 1 条 `candidate_repair`，均为 `BIRD-PG-0239`；其余 23 条弃权。`BIRD-PG-0206` 两侧均为 `abstain/no_unique_public_endpoint`。
- 报告绑定 E05 两份捕获文件 SHA-256、公开 development80 输入、授权导入清单及规则模块 SHA-256；模型请求数为 0。此前的 `...offline_local_20261024.json` 保留为多语句边界补齐前的记录。

## 决定与后续验证

值得制作**独立 E06 候选**，但目前不能宣布 0239 已修复或规则已可并入主线。候选只应对上述精确形态发出可解释的校验失败及修复反馈；对 0206 和不确定形态继续弃权。保持 E05 源报告和正式评分不变。

下一轮使用新的候选身份及报告名，先核对 0239 的首次 SQL、反馈、第二次 SQL、原生结果和尝试次数；同时核对 0206 的 SQL 未被拒绝，保留 20 条成功回归题，并报告模型调用、Token 和延迟。若 0239 没有变为原生正确，或 0206/成功题回退，则不推进扩大实验。离线 24 条无误拒记录只能支持制作候选，不能证明对所有模型输出安全。

## 后续实现状态

已制作隔离的 E06 v2 同轮包：两侧继承 E05 advisory 代码，候选仅增加 `endpoint_validation.py` 并修改 `case_worker.py`，在原生结构校验之后通过原有修复通道发送结构化反馈。规则不进入主线。本地 12 个 E06 定向/包测试通过；正式服务器实验尚未运行。同步包及逐步命令见 `M3_E06_PAIR24_SERVER_RUNBOOK_20261024.md`。
