# M3 E04：0072 与 0239 离线语义审查

日期：2026-10-24。依据为 [E04 同轮验收记录](M3_E04_PAIR24_ACCEPTANCE_REVIEW_20261024.md)所列九份原始文件、冻结 development80 公开题目/evidence、仅供审查的 Gold SQL，以及本地 BIRD 数据包的字段说明 CSV。只静态读取现有证据；没有连接数据库、执行新的 SQL、调用模型或修改评测。

## BIRD-PG-0072：城市字段缺失与参考输出形态边界

公开问题询问 2014-2015 学年、Fremont 的 State Special School 中 5 至 17 岁学生人数；evidence 明确 `EdOpsCode='SSS'`。来源字段说明将 `schools.City` 描述为城市、`schools.School` 描述为学校名、`schools.MailCity` 描述为邮寄地址所在城市；`frpm."Enrollment (Ages 5-17)"` 是人数列，`frpm."Academic Year"` 是学年列。`frpm.CDSCode -> schools.CDSCode` 的声明关联在两侧角色上下文中均可见。

两侧检索的 40 个记录候选没有 `schools.City`；最终选中字段有 `schools.edopscode`、`schools.school`、`schools.state`、`frpm."Enrollment (Ages 5-17)"` 和 `frpm."Academic Year"` 等，但没有 `schools.City`。`schools.school` 与 `schools.state` 是意图扩充以公开标识词为依据加入；`schools.MailCity` 得分约 0.30955，被 `below_coverage_floor` 排除。当前来源说明和 Gold 均能确认 `schools.City` 是真实字段；本轮报告不能证明它为什么没有进入最初的 40 个候选。

基线首次及最终 SQL 使用 `s.school='Fremont'`、`"Academic Year"='2014-15'`，并 `SUM` 人数；候选仍用 `s.school='Fremont'` 和 `SUM`，但把学年写成公开问题的 `2014-2015`。两侧均只生成一次、校验一次，SQL 执行成功并返回一行一列 `NULL`；没有得到语义修复反馈。候选对该题启用了 `hard_for_simple_outer_select`，但实际 SQL 为单列表达式、没有外层分组，所以形态校验直接通过。

冻结 Gold 使用 `s.City='Fremont'`、公开学年原值，并直接投影 `"Enrollment (Ages 5-17)"`，原生返回两行，数值为 40、335。两侧预测的一行 `NULL` 与之不匹配。可以确定的缺口有两层：

1. **地点字段角色。** 报告中 `City` 没进入最终授权字段图，模型改用学校名筛选；候选虽然修正学年字面值，结果仍为 `NULL`。地点筛选需要由公开题目和来源字段说明支持，不能把学校名或邮寄城市当作物理城市的通用替代。
2. **输出形态。** “How many students ...”可以被理解为合计人数，但冻结参考给出逐行人数。即使地点字段改正确，单个 `SUM` 与两行参考在当前原生元组集合评分下仍可能不匹配。不能仅凭 Gold 反向规定所有同类问题必须输出逐校行，也不能在 E04 中将这题作为硬性单值契约的肯定样本。

结论：主要可行动的公开来源缺口是**城市角色未进入授权 Schema 上下文**；学年原值保护是独立问题；参考输出形态存在需要单独登记的歧义。下一项候选若处理地点角色，应先做公开问法与字段说明的正反例：`in <city>` 对 `City`、明确学校名称对 `School`、邮寄地址场景对 `MailCity`；不能用本题 Gold 或数值 40/335 作为运行时规则。标量规则对含地点和多个匹配实体、参考形态不确定的问题应保持提示态，不能据此题加强硬拒绝。

## BIRD-PG-0239：公开端点限定未传为条件

公开问题是“atom 19 有多少 connections”；evidence 明确 `connections refers to bond_id; atom 19 refers to atom_id like 'TR%_19'`。来源字段说明将 `connected.atom_id` 定为第一个原子、`connected.atom_id2` 定为第二个原子、`connected.bond_id` 定为两原子之间的键。当前关系角色上下文同时列出 `atom_id` 与 `atom_id2` 两条外键候选，这两条关系可用于不同问题，但公开 evidence 本题只点名 `atom_id`。

两侧最终检索选中 `connected.bond_id`、`connected.atom_id` 及相关的 `atom`/`bond` 字段；`connected.atom_id2` 得分约 0.43039，未进入选中字段清单，原因 `below_coverage_floor`。不过关系角色上下文仍包含 `atom_id2` 的描述，模型 SQL 也引用了该字段。公开 evidence 在 `intent_contract.public_evidence.conditions` 与 `required_profile_conditions` 中没有形成结构化条件。由此可见，缺口不是缺少 `atom_id` 或 `bond_id` 的授权字段，而是**公开字段限定没有约束筛选端点**。

两侧首次及最终 SQL 相同：

```sql
SELECT COUNT(*)
FROM connected
WHERE atom_id LIKE 'TR%_19' OR atom_id2 LIKE 'TR%_19'
```

一次生成、一次校验，SQL 执行成功，原生结果为 754。冻结 Gold 使用 `COUNT(bond_id)` 和 `RIGHT(atom_id,2)='19'`，结果为 377。候选的标量形态规则对这条单行单列 SQL 不产生错误；本次失败属于条件和实体角色语义，不属于输出粒度。

模型额外加入 `atom_id2` 的 `OR`，扩大了公开 evidence 指定的筛选范围；这是静态 SQL 中能确认的差异。754 恰为 377 的两倍，但在没有按端点分别执行 SQL 的情况下，不能据此证明数据中每条连接恰好被对称重复。`COUNT(*)` 对 `COUNT(bond_id)`、公开 `LIKE` 对参考 `RIGHT` 的影响也没有在本轮独立量化。它们应作为剩余差异登记，不能仅根据最终数值判断哪一项单独造成全部错误。

正向边界是 `BIRD-PG-0206`：公开问题询问指定 bond 的原子元素，证据按 `bond_id` 定位。E04 两侧实际生成 SQL 用 `UNION` 汇集 `atom_id` 和 `atom_id2` 两端元素，并原生匹配。因此不能制定“所有 connection 查询只能使用 `atom_id`”的规则；应只在公开 evidence 明确指定端点时保留该限定，其他请求由关系角色和问题语义决定。

结论：0239 值得作为**公开条件中的实体端点绑定**候选，而不是标量计数候选。后续正反例需覆盖明确单端点、明确双端点、指定 bond 的两个原子、以及只有实体名称没有端点说明的情况。模型反馈可引用公开 evidence 和授权字段角色，不得引用 Gold 的 `RIGHT` 写法或目标数字 377。若要量化 `OR`、`COUNT(*)` 与 `LIKE` 的各自贡献，需要另立受控数据库诊断报告；本离线审查没有做这项执行。

## 两题共同的处理边界

两题来源身份、题单和原生复评均已由 E04 验收记录核对。它们都不是 SQL 语法或数据库执行失败；两侧均在第一次生成后通过结构校验。0072 属于**地点字段覆盖 + 参考输出形态歧义**，0239 属于**公开端点条件作用域**。单独修正 E04 的外层计数形态检查不能解决这两题，也不能从两题推导统一的 SQL 改写模板。先保留审查结论，再为每个问题设计有公开依据的正反例与独立候选。
