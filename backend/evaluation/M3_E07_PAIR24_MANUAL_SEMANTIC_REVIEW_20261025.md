# M3 E07 development24 人工语义审查记录

日期：2026-10-25  
审查对象：`m3_categorical_population_pair24_v1_20261025_r5`  
范围：development24 中的 `BIRD-PG-1480`、`0050`、`0173`、`0459`。本记录是对受控开发集结果的人工语义审查，不是正式 BIRD EX 或 holdout 验收。

## 结论摘要

| 题目 | 人工审查结论 | 处理意见 |
| --- | --- | --- |
| `BIRD-PG-1480` | 当前候选 SQL 在本数据上的原生结果匹配 Gold，但没有实现按月份汇总的业务语义。不能判作语义通过。 | 下一候选须按月分组并汇总 SME 客户消费，再选择峰值月份；不能只按单条消费记录排序。 |
| `BIRD-PG-0050` | 候选选了地址和学校两个概念字段，但输出顺序与问题要求及 Gold 顺序相反；本轮原生比较失败。 | 输出必须先邮寄街道地址，再学校名称。 |
| `BIRD-PG-0173` | 生成 SQL 将 3539 当作账户标识筛选，问题和 Gold 表明它是汇总扣款金额；原生比较失败。 | 继续列为已观察的独立失败，不将其算作 E07 候选收益。 |
| `BIRD-PG-0459` | 问题要求、SQL 和原生结果一致。 | 作为通过的对照保留。 |

**候选结论：不冻结、不推广。** 对照报告中的 `automatic_screen_pass=true` 只表示预设的自动筛选项通过；最终 `acceptance=manual_semantic_review_required` 仍需人工语义判断。1480 的结果匹配不能替代 SQL 逻辑审查。

## 逐题审查

### BIRD-PG-1480：峰值月份需要按月聚合

问题：`What was the gas consumption peak month for SME customers in 2013?`  
配套 evidence 指出 SME 客户、2013 年范围和日期中的月份表示。Gold SQL 的核心逻辑是：通过 `customers` 与 `yearmonth` 关联、筛选 `Segment = 'SME'` 和 2013 年，按月份分组，再按 `SUM(Consumption)` 降序取第一名。

r5 候选 SQL 使用了授权补充字段 `customers.customerid`、`customers.segment`，并加入 `c.segment = 'SME'` 及 2013 年日期范围；但它直接按 `ym.consumption DESC` 排序并 `LIMIT 1`，没有按月份 `GROUP BY`，也没有 `SUM(ym.consumption)`。因此它找的是单条记录消费最大的月份，不是 SME 客户群体月总消费最大的月份。

候选原生复评为匹配，说明该固定数据快照上两条 SQL 恰好返回相同结果；这不足以证明它们对业务问题等价。人工语义结论为**不通过**，问题是聚合粒度缺失，而不是新增分类字段无效。

### BIRD-PG-0050：字段顺序必须是地址、学校名称

问题：`What is the postal street address for the school with the 7th highest Math average? Indicate the school's name.`  
Evidence 将 postal street 与 mailing street 声明为同义表达。Gold 输出顺序为 `MailStreet, School`，也就是先地址、后学校名称。

r5 候选 SQL 的投影顺序为 `s.school, s.mailstreet`，即先学校名称、后街道地址。捕获的原生结果也是先返回 `NULL`、后返回 `25 Churchill Avenue`；Gold 结果顺序是先 `25 Churchill Avenue`、后 `NULL`。两边均为一行两列，但按冻结的原生 tuple-set 评分规则，列位置属于 tuple 内容，因此候选与 Gold 不匹配。

人工结论为**字段概念部分覆盖、字段顺序错误、原生不通过**。下一候选必须输出地址在前、学校名称在后，且应通过验证完整结果而非仅检查是否包含这两个列名。

### BIRD-PG-0173：3539 是总金额，不是账户 ID

问题：`How often does account number 3 request an account statement to be released? What was the aim of debiting 3539 in total?`  
Gold 对第一部分读取账户 3 的 statement frequency；第二部分先按账户与 `k_symbol` 汇总 `SUM(order.amount)`，再用 `total_amount = 3539` 找到扣款用途。

r5 候选第二部分使用 `order.account_id = 3539`，把金额文字误当作账户标识；基线捕获则使用了 `account_to = 3539`，也把金额值套到了账户标识字段上。候选原生复评不匹配 Gold。

人工结论为**语义不通过，继续作为已观察失败单独跟踪**。它并非 E07 分类人口上下文的目标题，不计为该候选的预期收益。

### BIRD-PG-0459：保持通过

问题要求比较 Serra Angel 和 Shrine Keeper 的 converted mana cost。候选 SQL 以两张卡的名称过滤，按 `convertedManaCost` 降序取一张；候选原生结果匹配冻结 Gold。

人工结论为**通过**，保留为观察对照。

## 实验身份与解释边界

- Bundle ID：`f258fb96237e4d1948b7722a23c8469380f8cc613c0e5f8096c422e7062eecfe`。
- 对照、基线捕获、候选捕获和原生复评均记录为 `complete`，数据库连接及目标数据验证通过。
- 基线捕获复用了 r4 已完成报告：`baseline_capture_reused=true`、`strict_same_round=false`。因此本轮是恢复后的 development24 筛选比较，不是严格同轮实验。
- 基线和候选原生复评分别比较 22/24；候选修复 1480 的澄清，但回退 0050，净提升为 0。20 道既定成功回归题保持通过。
- 此比较不是正式 EX、不是 holdout，也不应单独用于因果归因或推广决策。

## 后续候选验收条件

1. 1480 SQL 明确包含按月份聚合消费的逻辑，并通过原生复评；人工检查确认分组粒度与问题一致。
2. 0050 SQL 先输出邮寄街道地址，再输出学校名称；原生复评通过。
3. 20 道冻结成功回归题继续保持通过；保留 0173、0459 的诊断记录。
4. 新候选使用独立身份及新输出文件；若要作严格同轮比较，基线与候选都必须在该轮重新捕获，不复用 r4/r5 的基线。

## 原始证据

保存在 `E:\PythonLearn\m3_categorical_population_pair24_20261025_r5\` 的文件：

- `reports/e07_pair24_server.json`
- `reports/e07_pair24_comparison_server.json`
- `baseline/backend/evaluation/results/m3_e07_pair24_baseline_capture_server.json`
- `baseline/backend/evaluation/results/m3_e07_pair24_baseline_native_server.json`
- `candidate/backend/evaluation/results/m3_e07_pair24_candidate_capture_server.json`
- `candidate/backend/evaluation/results/m3_e07_pair24_candidate_native_server.json`

题目文本与冻结 Gold 分别来自 `backend/evaluation/cases/bird_mini_dev/m2_pg_v1/inputs/development80.jsonl` 和 `backend/evaluation/cases/bird_mini_dev/m2_pg_v1/scorer/gold110.jsonl`。原始服务器报告保持不变。
