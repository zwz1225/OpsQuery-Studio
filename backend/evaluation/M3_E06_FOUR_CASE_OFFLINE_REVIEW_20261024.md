# M3 E06：0050、0173、0459、1480 离线归因与下一候选决策

日期：2026-10-24。范围是 E06 development80 已保存的公开题目、两侧生成轨迹、独立原生复评和既有的来源关系审查。本次只读本地文件；没有调用模型、连接数据库、重跑题目或修改题库、Gold、原生评分及预算。此处的 Gold 和复评差异仅供**离线审查**，不能进入下一候选的生成或校验提示。

## 1. 证据固定

- 原始九份报告位于 `E:\PythonLearn\m3_e06_pair80_endpoint_feedback_v2_20261024_r1`，逐份摘要、来源身份和执行完整性已记录在 [E06 development80 验收审查](M3_E06_PAIR80_ACCEPTANCE_REVIEW_20261024.md)。其中比较报告 SHA-256 为 `ab953d943b69b880061f50ddf4a1078aebbbf16dd0979bd7c6eead25abe324e6`；基线/候选生成报告分别为 `7bbd12fc94f24582a26cc54e3beced454dd7bffc5628973dad25511453f2d995` / `2e204fbc10bd9d37bef79caef8bf93a3c45e84b4c9f4def65f37d1960bf0b74c`；两份原生复评分别为 `c037dfe5be2157af8c1e39573c8b73067e7222e73fc9a28ed546db9ce47aa41c` / `283bd2a5b0cfae5b7ddeb5b29fdfbe641a7847738cdb934a0ace827157a24dbd`。
- 公开输入是 `cases/bird_mini_dev/m2_pg_v1/inputs/development80.jsonl`，既有审查固定的 SHA-256 为 `6760724e98b6da967ac5ebb2698c4e5cab385875bd150ad36a3b252ffdc52f03`。四题均属 development80；没有读取保留集来设计规则。
- 四题的两侧检索字段均相同；E06 的端点校验在 0050、0173、0459 均弃权，在 1480 没有端点观察。四题变化不能直接归因于 E06 的端点反馈。原生复评对预测和冻结参考执行完整 SQL，比较原生**元组集合**：忽略列名、行序和重复次数，保留元组内列位置，不做数值舍入。

## 2. 逐题审查

| 题目 | 公开需求及已有授权上下文 | 保存的两侧轨迹与独立复评 | 可确认的问题及边界 |
| --- | --- | --- | --- |
| `BIRD-PG-0050` | 询问数学平均分第七高学校的 **邮寄街道地址，随后学校名称**；evidence 说明 postal street 与 mailing street 同义。两侧均有 `schools.mailstreet`、学校名候选、`satscores.avgscrmath` 和 `satscores.cds → schools.cdscode` 声明关系。 | 基线首次 SQL 投影 `s.mailstreet, sc.sname`，`ORDER BY avgscrmath DESC NULLS LAST LIMIT 1 OFFSET 6`，原生匹配；候选首次 SQL 投影 `s.school, sc.mailstreet`，多连一次 `schools`，同样排序与偏移，原生不匹配。两侧都只生成一轮、校验通过。基线结果为 `[地址, NULL]`，候选为 `[NULL, 地址]`；参考为 `[地址, NULL]`。 | **列位置颠倒**足以解释本轮元组差异；候选的额外自关联需要单独审查，但现有结果不能证明它改变了选中行。基线 `satscores.sname` 与参考 `schools.school` 当前恰好同为 NULL，不能据原生匹配宣称两字段通用等价，也不能据此宣称学校名称已被正确提供。属于输出契约/源字段语义问题，并非缺字段。 |
| `BIRD-PG-0173` | 两问分别要账户 3 的对账单频率，以及“debiting **3539 in total**”的付款目的；evidence 说明 `k_symbol` 表示付款目的。授权图已有 `account.frequency`、`order.amount`、`order.account_id` 和 `order.k_symbol`。 | 基线把 `3539` 放在 `order.amount=3539`，返回 `[POPLATEK MESICNE, POJISTNE]`，原生匹配；候选把它放在 `order.account_id=3539`，返回 `[POPLATEK MESICNE, NULL]`，原生不匹配。两侧首轮 SQL 均通过结构及数据库校验，也均未进入修复。离线参考通过对订单金额求和并按账户/目的分组判断 3539。 | 当前可确认的是**数值角色错配**：候选将公开语句中的借记金额错绑到账户标识。基线 `amount=3539` 在现有数据上匹配，但不等于已证明与“in total”的聚合语义普遍相同；聚合口径只能从公开措辞与授权字段另行验证，不能把参考 SQL 作为模型反馈。 |
| `BIRD-PG-0459` | 问两张指定卡牌“哪一张”法力费用更高；evidence 将比较量绑定为 `cards.convertedmanacost`。两侧授权图已有 `cards.name` 和比较量，无关联缺口。 | 两侧本轮 SQL 完全相同：`SELECT name, convertedmanacost ... ORDER BY convertedmanacost DESC LIMIT 1`。均返回 `[Serra Angel, 5.0]`，参考只返回 `[Serra Angel]`；原生不匹配，均首轮校验通过。历史 M2 v4 保存的 SQL 曾只投影 `name`。 | 比较指标进入了输出列，导致**多一列**。问题请求的是获胜卡牌，比较量用于排序即可；这从公开问句本身就能解释。它是历史成功题保持失败，**不是** E06 候选相对同轮基线新增的退化。参考 SQL 的 NULL 排序差异只是离线结构假设，本轮结果没有证明它是失败原因。 |
| `BIRD-PG-1480` | 问 2013 年 SME 客户的天然气消费峰值月份；evidence 给出 2013 的 `201301` 至 `201312` 范围及 `yearmonth.date` 月份位置。两侧授权图只有 `yearmonth.consumption/customerid/date`，没有 `customers.segment`、`customers.customerid` 或关联边。 | 基线按 `yearmonth` 全体客户汇总月份，没有 SME 条件；SQL 可执行但月份为 `10`，参考为 `04`，原生不匹配。候选首次 SQL 误把 `segment='SME'` 写在 `yearmonth` 子查询，数据库报 `42703 undefined_column`；修复反馈只列出已授权的 `yearmonth` 三列。模型随后明确指出缺少 `customers.segment` 和可用关联路径并澄清；无最终 SQL，复评按固定分母计错。 | **条件字段及关联上下文不足**已被候选检索和澄清轨迹同时证实。不能因参考月份为 `04` 而把月份、聚合方式或连接类型写成题目特例；补齐上下文后模型是否能正确处理“峰值月份”仍未验证。候选的澄清是缺口的可解释表现，不是成功答案。 |

1480 的字段筛选细节：`customers.segment` 已被检索到，rerank `0.548829`，拒绝原因 `coverage_table_not_anchored`；`customers.customerid` 为 `0.430666`，低于覆盖下限；`yearmonth.customerid` 为 `0.582459`，已选。样本条件观察识别了 `customers.segment='SME'`，依据为公开 SME 词与授权分类样本的唯一匹配，权限仅 `coverage_hint_only`、`mandatory=false`。它在 intent 阶段的 `condition_scope=true`，但 `reachable=false`，门槛为 `no_declared_fk_path_within_two_hops`。因此**单纯放宽 rerank 阈值**仍不足以完整补齐两侧键和关系，也可能扩大无关字段。

## 3. 1480 关系依据与约束

[E02 来源关系离线审查](M3_E02_CONDITION_RELATION_REVIEW_20261022.md)已核对同一受控数据包：`customers.customerid` 为 BIGINT 主键且唯一；`yearmonth.customerid` 为 BIGINT，冻结样本的 383,282 条子记录全部能匹配父表，空键和孤儿键均为 0，一个客户最多对应 20 条 `yearmonth` 记录。两表之间**没有数据库声明外键**。这支持带来源版本的“经审查候选关系”，并不证明所有业务 JOIN 语义，也不允许把它伪装成声明外键。E06 两侧的实时来源收据显示同一数据和 catalog 身份；本次审查没有重新连接服务器做现场验证。

E06 已有的条件/关系策略在 `BIRD-PG-1479` 成功把 `customers.currency` 和两侧 `customerid` 加入授权图，使模型筛选 CZK 并正确关联；这是该路径能工作的**局部正例**。1480 的 SME 条件被“只沿声明外键可达”门槛挡住，说明既有经审查关系没有被该条样本条件选择路径一致使用。这是下一项最值得单独实验的缺口。

## 4. 下一候选决策

**决定设计一个新的、独立身份的跨表分类条件覆盖候选；暂不把这四题一起做成一项修改。** 首个目标是 1480 类型的公开群体限定词，作用在检索/授权 Schema 上下文阶段：仅当公开问题中的分类词能唯一对应同来源的授权字段样本，且该字段所属表与现有锚表之间存在已声明关系或**已单独审查、同版本绑定的候选关系**时，成组考虑条件字段和两端连接键。关系以 `reviewed_candidate` 标签和完整性证据呈现；不强制 `WHERE`、JOIN 类型、聚合口径或最终 SQL。不以题号、`SME` 常量、参考 SQL、原生分数触发，不全面降低 0.55/0.50 阈值或突破原 20 字段、补充字段、2 跳及题内预算。

实施前的无模型正反例至少包括：1480 类唯一分类样本＋同源已审查关系；1479 币种路径不回归；分类词同时匹配多个表、关系未审查/版本不符、跨数据库、只存在同名键但缺证据、关系有孤儿记录、客户类别词未在公开问题中出现、两端键超出字段额度、`0206` 等不相关端点题均须弃权或保留歧义。对“peak month”的求和与逐行最大值歧义，另列 SQL 语义观察，不借检索策略强定。

0050、0173、0459 留在独立的 SQL 语义队列：0050 检查公开请求的有序投影并保留学校名称来源歧义；0173 检查数字常量的金额/标识角色及“in total”的聚合提示；0459 检查比较指标与请求输出的区分。此前 [E01 输出契约 24 题](M3_E01_PAIR24_REVIEW_20261021.md)虽然使 0050 局部转对，但未达到预定门槛，不能原样推广为这三题的通用修复。各方向需要各自正反例和单变量候选，不用一次重跑掩盖原因。

下一实际步骤是先实现**仅面向开发集、默认关闭**的跨表分类条件选择路径及正反例测试，离线核对授权图与拒绝原因；通过后再用新冻结身份做 1480、1479 和成功回归题的同轮生成/原生复评，满足预登记筛选才扩大到 development80。既有 E06 九份证据保持原样；已观察的 holdout 不再当盲测。
