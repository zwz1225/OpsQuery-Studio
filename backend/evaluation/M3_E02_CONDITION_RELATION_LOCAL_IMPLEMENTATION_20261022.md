# M3 E02 本地实现记录：条件需求、拒绝原因与候选关系

日期：2026-10-22。范围：M2 development80 中的公开问题、授权 Schema 与已冻结的 M3 E01 开发集轨迹。本次没有调用模型或 PostgreSQL，也没有复跑 holdout30。

## 已接入的行为

- `diagnostic_runner` 增加独立的 `--condition-relations` 开关。它要求同时启用 `--schema-coverage --intent-candidate`，排斥 E01 的 `--output-contract`，且只允许开发诊断。默认仍按 M2 v4 路径运行。
- 检索报告保留完整的旧策略样本提示拒绝原因、公开请求中的字段及条件跨度、候选字段归属、来源校验结果、候选关系审查状态、预算拒绝原因和缺少的关联键。样本值本身不会成为强制 SQL 谓词。
- 已审查的关系独立存放在 `reviewed_relations.py`。每条记录绑定来源 ID、数据库、catalog 与数据版本、查询角色、两端键、完整唯一键、字段类型及冻结数据的键覆盖统计。只有当前 runtime 已验证同一来源和目标数据、唯一键与类型符合、子表没有空键和孤儿、且归属依据已审查时，才可为条件字段提供候选关联。候选关系明确标为非数据库外键，不指定连接类型。
- 对“paid in CZK”这类公开货币条件，只有公开语句表达条件角色、授权索引中的样本能唯一定位 `currency` 所属表、该表有已审查的受控关联时，才将条件字段和两端关联键作为一个整体加入。沿用 20 字段、8 个意图新增字段与 2 跳上限；超额时整组拒绝并记录原因。
- 关系候选在 Schema 图中以说明性的等值路径呈现；SQL 生成、修复、校验次数、预算、Gold 和原生 EX 评分均未修改。未解决的条件或关系在上下文中有明确提示。

## 实际离线回放

基于 M3 E01 候选侧保存的 24 题 Schema 索引及选择结果回放，24 题只有 `BIRD-PG-1479` 的字段选择变化：2 列变为 5 列，新增 `customers.currency`、`customers.customerid`、`yearmonth.customerid`。候选关系来自已审查的同来源键覆盖证据，不是数据库外键。旧策略的 `coverage_table_not_anchored`、`condition_owner_outside_anchor_seed_or_named_scope`、`no_declared_fk_path_within_two_hops` 均可在诊断中追溯。

`BIRD-PG-0407` 仍为 20 列，没有自动补键。报告指出 `cards.uuid`、`foreign_data.uuid` 缺失；源数据有 16 条孤儿记录，其中 3 条为德语行，因此这条关系只保留审查和缺口诊断，不自动作为可信连接路径。

回放文件：`evaluation/results/m3_e02_condition_relation24_offline_local_20261022.json`。该过程只模拟已记录的来源身份以检查选择逻辑，不表示当前服务器已完成实时验证，也不代表模型 SQL 或 EX 的改善。

## 本地验证及后续边界

新模块正反例、完整检索路径及 M2 v4/E01 相关测试覆盖 179 条。E01 工作流的 Windows 临时目录需位于后端项目之外；旧版首次 SQL 审计依照冻结代码身份拒绝重放，保持此保护。

下一轮若要评估生成结果，应另建 E02 基线/候选同轮实验。由于 Schema 与索引生产代码已改变，E01 的“索引生产代码相同、Schema 图相同”前提不再适用；新实验需冻结各侧真实索引身份、来源、模型、预算，并重新记录模型调用、SQL、原生比较和时间。正式验收前不能把本地回放视为性能或 EX 成功。
