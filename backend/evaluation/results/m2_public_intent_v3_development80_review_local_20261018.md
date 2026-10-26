# M2 v3：完整 development80 报告审查

## 结论

两份下载报告完整，来源链与运行约束检查通过；可以保留为本轮开发证据。当前候选不建议冻结：49/80相对34/80净增15题，但由新增21题、退化6题组成，存在粒度约束过宽、精度遗漏及Schema覆盖问题。该结论不是既定正式验收门槛，也不是M2已完成。

- 本地离线核对：2376项检查全部通过，未调用模型、未连接PostgreSQL。
- 逐题原生结果：76题进入复评，49匹配、27不匹配；4题未回答或失败仍留在80题分母。
- 8个授权来源均绑定PostgreSQL/public、各自只读账号、数据/catalog版本；8份索引均命中缓存，索引内容哈希与已核对的v3定向14题相同。
- 两份报告与v3定向14题的完整服务器代码绑定一致，96个执行代码文件与本地交付文件逐个匹配。
- 生成阶段不执行Gold，独立原生复评执行152条SQL、0次模型调用；80个逐题runtime及复评连接池均关闭，隔离/预算探针通过，保留题未开放。

## 文件与版本

- 生成报告 SHA-256：`8823926748c359d43ae011e94a1bed8fe5cf592599170c831840d51325ad398b`
- 原生复评 SHA-256：`a6b2cadaff7bf20e47ab210182c05029c98ab61b4adef803a5d9450fd832a551`
- 服务器代码绑定：`ad9ede65218a065a3b0d2bcecb23a73b50a20502a1f5df884845aa9572d64bc2`
- 生成报告UTC起止：2026-10-18T09:05:19.947702+00:00 至 2026-10-18T09:21:31.862818+00:00
- 复评报告UTC起止：2026-10-18T09:30:15.822476+00:00 至 2026-10-18T09:34:42.306830+00:00

## 效果与成本

| 指标 | 原始80题基线 | 本轮v3 |
| --- | ---: | ---: |
| 原生匹配/全部开发题 | 34/80（42.50%） | 49/80（61.25%） |
| 完整结果 | 58 | 76 |
| 澄清 | 20 | 2 |
| 校验失败 | 2 | 1，另有1题重复SQL终止 |
| 原成功保持 | — | 28/34 |
| 新增通过 / 原成功退化 | — | 21 / 6 |
| 此前14题的成功保持 | — | 13/13 |
| 逐题模型HTTP | 245 | 256 |
| 其中chat | 85 | 96 |
| 新增索引HTTP | 0 | 0 |
| chat输入token（服务返回usage） | 183724 | 496272 |
| chat输出token（服务返回usage） | 5275 | 7422 |
| chat总token（服务返回usage） | 188999 | 503694 |
| 逐题p50秒 | 8.992 | 10.687 |
| 逐题p95秒 | 19.628 | 30.580 |

净增18.75个百分点，但不能归为21题全部新增且无退化。HTTP只增加约4.49%，chat总token却约为原来的2.67倍；报告的是本次成功运行成本，不含此前中断任务可能已发生的调用，不等同于实际费用。输入token含缓存token，不将其当作全价计费量。延迟采用nearest-rank，含逐题runtime准备，非单独模型耗时。

本轮96次chat分布：67题1次、10题2次、3题3次；13题有再生成。65题单次生成即得到完整执行结果，其中44题最终原生匹配。另2题单次生成选择澄清。首次校验通过不能直接称为首次原生正确。

生成侧SQL工具调用109次＝33次规范值查询＋76次结果执行；规范值共40对，消耗原有每题3次SQL预算。独立复评另计152次SQL。所有逐题HTTP、chat、SQL、生成轮次及600秒限制均在预算内；未发现传输重试。

## 按数据库对照

| database_id | 原匹配 | 现匹配 | 新增 | 退化 |
| --- | ---: | ---: | ---: | ---: |
| california_schools | 1/10 | 4/10 | 3 | 0 |
| card_games | 4/10 | 5/10 | 1 | 0 |
| codebase_community | 3/10 | 7/10 | 4 | 0 |
| debit_card_specializing | 2/10 | 4/10 | 3 | 1 |
| financial | 5/10 | 6/10 | 2 | 1 |
| student_club | 3/10 | 8/10 | 5 | 0 |
| superhero | 7/10 | 9/10 | 2 | 0 |
| toxicology | 9/10 | 6/10 | 1 | 4 |

toxicology从9/10降为6/10，是当前优先审查对象；新增0201成功，损失0226、0239、0263、0273。

## 六题退化

| 题目 | 已观察的问题 |
| --- | --- |
| BIRD-PG-0173 | 原基线通过；当前把总扣款3539解释成 order.account_to=3539，并拆成互不关联的子查询；第二列为NULL而参考为POJISTNE。应保留account_id=3与金额总和的关系。 |
| BIRD-PG-0226 | 原基线通过；题目明确 five decimal places，contract已标记explicit_rounding，但SQL仍输出未舍入DOUBLE。预测约3.8461538461538463，参考Decimal 3.84615；应落实公开精度请求，不应新增数值容差。 |
| BIRD-PG-0239 | 原基线通过；当前同时匹配 atom_id 与 atom_id2，结果754，参考为377。需核实有向/双向连接记录语义与公开 evidence 指定端点，不能用OR自动扩展两端。 |
| BIRD-PG-0263 | 原基线通过；首次SQL被entity_grain_fanout拒绝，随后先加DISTINCT再改EXISTS。最终是原子去重总体，参考保留atom-bond关联权重。需先复用被拒绝首次SQL做无模型原生验证，判断是否误拒绝；不可把0201的半连接策略无条件推广。 |
| BIRD-PG-0273 | 原基线通过，本次3次校验均失败且未执行结果SQL。公开文本同时有chlorine=cl及公式SUM(element=pb)，当前把cl、pb都设为强制条件，并从COUNT(molecule_id)推定分子去重粒度。冻结参考统计致癌分子中的cl原子，不要求pb。需冲突检测及粒度适用范围审查；先原生复评首次被拒SQL，不能把参考注入模型。 |
| BIRD-PG-1479 | 原基线通过；当前图只有 yearmonth.consumption/date，未覆盖 customers.currency，SQL漏CZK且多输出 total_consumption。年份恰同为2013仍因额外列原生不匹配。基线SQL也漏CZK但在当前数据碰巧匹配，不能回退到该不完整写法。 |

0263/0273存在规则误拒绝的强证据，但本地未执行被拒SQL。先用捕获的首次SQL做可信原生复评，再确定修复适用范围；不把参考SQL/结果回传模型。0239和1479的原基线通过也不代表其旧SQL在一般数据上语义完整。

## 四题未进入复评

| 题目 | 状态 | 核实结果 |
| --- | --- | --- |
| BIRD-PG-0639 | repeated_sql | 模型两次使用不在授权catalog中的posttags；首次被本地来源策略拒绝，第二次因重复SQL阻断，未提交PG分析。来源拒绝及重复保护有效；后续需核实公开关系路径，不能放开posttags。 |
| BIRD-PG-1524 | clarification | 最终图只有transactions_1k.price/date/customerid，模型说明缺客户国籍。授权customers确实只有customerid/segment/currency；冻结参考却经gasstationid取gasstations.country（加油站国家）。同时存在图覆盖不足及客户国籍/加油站国家语义差异，不能简单强制该JOIN并宣称语义修复。 |
| BIRD-PG-0152 | clarification | 最终图只有district.a15/a3；模型说明缺1997年起开户信息。授权catalog存在account及日期字段，但未进入最终图，应按公开问题补齐日期与关联键路径。 |
| BIRD-PG-0273 | validation_failed | 原基线通过，本次3次校验均失败且未执行结果SQL。公开文本同时有chlorine=cl及公式SUM(element=pb)，当前把cl、pb都设为强制条件，并从COUNT(molecule_id)推定分子去重粒度。冻结参考统计致癌分子中的cl原子，不要求pb。需冲突检测及粒度适用范围审查；先原生复评首次被拒SQL，不能把参考注入模型。 |

注意：报告顶层errors=[]表示流程无未处理异常，不表示不存在逐题校验拒绝。未回答题没有偷偷从80题整体分母剔除。

## 校验与误拒绝审查

18次拒绝分布在13题：4次undefined_column、1次undefined_function、10次intent_contract_violation、1次来源拒绝、1次重复阻断、1次函数策略拒绝。结构化反馈可按相同公开输入及授权catalog离线重建，说明记录完整；这不证明每个业务约束都适用。

- 0263：原子在多条bond上的关联权重与去重原子总体并不相同。entity_grain_fanout不能仅看到一对多JOIN及COUNT标识就强行改为EXISTS。
- 0273：同时强制cl和pb，未表达公开evidence内部冲突；COUNT(molecule_id)也不足以单独证明应去重分子。
- 0226：公开precision要求已在contract标记explicit_rounding，却未记录具体五位精度并阻止遗漏舍入。
- 0639：posttags不在当前授权catalog，重复SQL保护有效；应保留来源边界。
- 0586：仅该题触发参与者上下文输出组，本轮仍修复后原生通过。没有证据支持将所有筛选上下文列普遍强制加入输出。

## 全部80题记录

题号仅用于审查记录，不用于生成策略或逐题硬编码。

| 题目 | 原匹配 | 本次状态 | 本次原生 | chat次数 | 结果分类 |
| --- | --- | --- | --- | ---: | --- |
| BIRD-PG-0011 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-0025 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-0036 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-0048 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0050 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-0072 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-0077 | 否 | diagnostic_answered | 不匹配 | 2 | 仍未通过 |
| BIRD-PG-0082 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-0083 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-0085 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-0352 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-0356 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0368 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-0371 | 否 | diagnostic_answered | 不匹配 | 2 | 仍未通过 |
| BIRD-PG-0379 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0407 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-0415 | 否 | diagnostic_answered | 不匹配 | 2 | 仍未通过 |
| BIRD-PG-0459 | 是 | diagnostic_answered | 匹配 | 2 | 保持通过 |
| BIRD-PG-0473 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-0480 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0537 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-0557 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-0586 | 否 | diagnostic_answered | 匹配 | 2 | 新增通过 |
| BIRD-PG-0595 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-0604 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-0629 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0637 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-0639 | 否 | repeated_sql | 未复评，计失败 | 2 | 仍未通过 |
| BIRD-PG-0671 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0707 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-1473 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-1476 | 否 | diagnostic_answered | 匹配 | 2 | 新增通过 |
| BIRD-PG-1479 | 是 | diagnostic_answered | 不匹配 | 1 | 退化 |
| BIRD-PG-1480 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-1481 | 否 | diagnostic_answered | 不匹配 | 2 | 仍未通过 |
| BIRD-PG-1486 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-1505 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-1509 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-1524 | 否 | clarification | 未复评，计失败 | 1 | 仍未通过 |
| BIRD-PG-1533 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-0092 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0095 | 否 | diagnostic_answered | 匹配 | 2 | 新增通过 |
| BIRD-PG-0099 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0112 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0115 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-0118 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0145 | 否 | diagnostic_answered | 不匹配 | 2 | 仍未通过 |
| BIRD-PG-0152 | 否 | clarification | 未复评，计失败 | 1 | 仍未通过 |
| BIRD-PG-0159 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-0173 | 是 | diagnostic_answered | 不匹配 | 1 | 退化 |
| BIRD-PG-1361 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-1398 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-1399 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-1405 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-1409 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-1411 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-1427 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-1435 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-1457 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-1460 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0717 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0726 | 否 | diagnostic_answered | 不匹配 | 1 | 仍未通过 |
| BIRD-PG-0738 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0760 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0766 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-0773 | 否 | diagnostic_answered | 匹配 | 1 | 新增通过 |
| BIRD-PG-0782 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0790 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0794 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0806 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0195 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0200 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0201 | 否 | diagnostic_answered | 匹配 | 3 | 新增通过 |
| BIRD-PG-0206 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0226 | 是 | diagnostic_answered | 不匹配 | 1 | 退化 |
| BIRD-PG-0232 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0239 | 是 | diagnostic_answered | 不匹配 | 1 | 退化 |
| BIRD-PG-0242 | 是 | diagnostic_answered | 匹配 | 1 | 保持通过 |
| BIRD-PG-0263 | 是 | diagnostic_answered | 不匹配 | 3 | 退化 |
| BIRD-PG-0273 | 是 | validation_failed | 未复评，计失败 | 3 | 退化 |

## 27题不匹配及4题未复评：逐题审查

以下区分可直接观察的SQL/结果差异与待核实的业务解释；参考形态差异不自动成为生成规则。

### BIRD-PG-0011：标识字段角色（P2）

- 原始问题：Please list the codes of the schools with a total enrollment of over 500.
- 官方evidence：Total enrollment can be represented by `Enrollment (K-12)` + `Enrollment (Ages 5-17)`
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：预测返回7位 School Code，参考返回14位 CDSCode；同为7806行也不相等。需区分局部编号与完整业务标识。

预测/参考：7806/7806行，1/1列。

捕获的最终SQL：

```sql
SELECT "School Code" FROM frpm WHERE ("Enrollment (K-12)" + "Enrollment (Ages 5-17)") > 500
```

冻结参考SQL（仅审查端）：

```sql
SELECT T2.CDSCode FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2."Enrollment (K-12)" + T2."Enrollment (Ages 5-17)" > 500
```

### BIRD-PG-0025：位置条件与字段所属表（P2）

- 原始问题：Name schools in Riverside which the average of average math score for SAT is grater than 400, what is the funding type of these schools?
- 官方evidence：Average of average math = sum(average math scores) / count(schools).
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：预测把 Riverside 绑定为 schools.soctype，输出 schools.fundingtype；参考筛选 frpm.District Name 并输出 Charter Funding Type。预测0行、参考6行。

预测/参考：0/6行，2/2列。

捕获的最终SQL：

```sql
SELECT DISTINCT s.sname, sc.fundingtype
FROM satscores s
JOIN schools sc ON s.cds = sc.cdscode
WHERE sc.soctype = 'Riverside'
GROUP BY s.sname, sc.fundingtype
HAVING AVG(s.avgscrmath) > 400
```

冻结参考SQL（仅审查端）：

```sql
SELECT T1.sname, T2."Charter Funding Type" FROM satscores AS T1 INNER JOIN frpm AS T2 ON T1.cds = T2.CDSCode WHERE T2."District Name" LIKE 'Riverside%' GROUP BY T1.sname, T2."Charter Funding Type" HAVING CAST(SUM(T1.AvgScrMath) AS REAL) / NULLIF(COUNT(T1.cds), 0) > 400
```

### BIRD-PG-0072：地名角色与聚合形态（P2）

- 原始问题：How many students from the ages of 5 to 17 are enrolled at the State Special School school in Fremont for the 2014-2015 academic year?
- 官方evidence：State Special School means EdOpsCode = 'SSS'
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：把 Fremont 绑定为 school 而不是 city，并将明细人数 SUM 为单值；预测NULL，参考两行人数。

预测/参考：1/2行，1/1列。

捕获的最终SQL：

```sql
SELECT SUM(f."Enrollment (Ages 5-17)") FROM frpm f JOIN schools s ON f.cdscode = s.cdscode WHERE s.edopscode = 'SSS' AND s.school = 'Fremont' AND f."Academic Year" = '2014-2015'
```

冻结参考SQL（仅审查端）：

```sql
SELECT T1."Enrollment (Ages 5-17)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1."Academic Year" = '2014-2015'
```

### BIRD-PG-0077：已有比率列与显式百分数公式（P2）

- 原始问题：Which schools served a grade span of Kindergarten to 9th grade in the county of Los Angeles and what is its Percent (%) Eligible FRPM (Ages 5-17)?
- 官方evidence：Percent (%) Eligible FRPM (Ages 5-17) can be acquired by `FRPM Count (Ages 5-17)` / `Enrollment (Ages 5-17)` * 100
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：预测直接读取现有比率列，参考按公开 evidence 的计数/人数*100 计算。两行结果呈0–1与0–100尺度差异，不能在评分时乘100放宽。

预测/参考：2/2行，2/2列。

捕获的最终SQL：

```sql
SELECT s.school, f."Percent (%) Eligible FRPM (Ages 5-17)" FROM public.schools s JOIN public.frpm f ON s.cdscode = f.cdscode WHERE s.gsserved = 'K-9' AND s.county = 'Los Angeles'
```

冻结参考SQL（仅审查端）：

```sql
SELECT T2.School, T1."FRPM Count (Ages 5-17)" * 100 / NULLIF(T1."Enrollment (Ages 5-17)", 0) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.GSserved = 'K-9'
```

### BIRD-PG-0083：输出组与业务筛选（P2）

- 原始问题：Of the schools that offers a magnet program serving a grade span of Kindergarten to 8th grade, how many offers Multiple Provision Types? List the number of cities that offers a Kindergarten to 8th grade span and indicate how many schools are there serving such grade span for each city.
- 官方evidence：Kindergarten to 8th grade refers to K-8; 'Offers a magnet program' means Magnet = 1; Multiple Provision Types refers to `NSLP Provision Status` = 'Multiple Provision Types'
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：预测3列、21行，参考2列、1行；把 Provision Status 放入条件计数而非同样的总体筛选，并放宽 GSserved/GSoffered。题目较复杂，修复不能仅照抄参考列数。

预测/参考：21/1行，3/2列。

捕获的最终SQL：

```sql
WITH k8_magnet_schools AS (
    SELECT s.cdscode, s.city
    FROM schools s
    WHERE s.magnet = 1
      AND (s.gsserved = 'K-8' OR s.gsoffered = 'K-8')
)
SELECT 
    COUNT(CASE WHEN f."NSLP Provision Status" = 'Multiple Provision Types' THEN 1 END) AS num_multiple_provision_types,
    k.city,
    COUNT(*) AS num_schools_k8_span
FROM k8_magnet_schools k
JOIN frpm f ON k.cdscode = f.cdscode
GROUP BY k.city
```

冻结参考SQL（仅审查端）：

```sql
SELECT T2.City, COUNT(T2.CDSCode) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.Magnet = 1 AND T2.GSoffered = 'K-8' AND T1."NSLP Provision Status" = 'Multiple Provision Types' GROUP BY T2.City
```

### BIRD-PG-0085：漏输出百分数（P2）

- 原始问题：What is the Percent (%) Eligible Free (K-12) in the school administered by an administrator whose first name is Alusine. List the district code of the school.
- 官方evidence：Percent (%) Eligible Free (K-12) = `Free Meal Count (K-12)` / `Enrollment (K-12)` * 100%
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：仅返回 District Code，遗漏题目明确要求的 Eligible Free 百分数。

预测/参考：1/1行，1/2列。

捕获的最终SQL：

```sql
SELECT f."District Code" FROM frpm f JOIN schools s ON f.cdscode = s.cdscode WHERE s.admfname1 = 'Alusine'
```

冻结参考SQL（仅审查端）：

```sql
SELECT T1."Free Meal Count (K-12)" * 100 / NULLIF(T1."Enrollment (K-12)", 0), T1."District Code" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'
```

### BIRD-PG-0352：总体关系范围（P2）

- 原始问题：Calculate the percentage of the cards availabe in Chinese Simplified.
- 官方evidence：Chinese Simplified' is the language; percentage = Divide(Sum(id where language = 'Chinese Simplified'), Count(id)) *100
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：预测只对 foreign_data 计数；参考先关联 cards。均为单值，但原生数值不同；需核实关联保留的总体，不能归为单纯浮点误差。

预测/参考：1/1行，1/1列。

捕获的最终SQL：

```sql
SELECT CAST(SUM(CASE WHEN fd.language = 'Chinese Simplified' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(*), 0) AS percentage FROM foreign_data fd
```

冻结参考SQL（仅审查端）：

```sql
SELECT CAST(SUM(CASE WHEN T2.language = 'Chinese Simplified' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(T1.id), 0) FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid
```

### BIRD-PG-0371：关联表与键角色（P2）

- 原始问题：What is the percentage of cards whose language is French among the Story Spotlight cards?
- 官方evidence：Story Spotlight card refers to isStorySpotlight = 1; French is the language; Percentage = Divide(Count(id) where language = 'French' and isStorySpotlight = 1, Count(id) where isStorySpotlight = 1)*100
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：SQL修复把不存在的 st.card_id 改成 st.id，但仍将 cards.id 与 set_translations.id 关联；参考使用 cards.uuid=foreign_data.uuid。语法修好后业务关联仍错。

预测/参考：1/1行，1/1列。

捕获的最终SQL：

```sql
SELECT CAST(SUM(CASE WHEN st.language = 'French' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(*), 0) AS percentage FROM cards c JOIN set_translations st ON c.id = st.id WHERE c.isstoryspotlight = 1
```

冻结参考SQL（仅审查端）：

```sql
SELECT CAST(SUM(CASE WHEN T2.language = 'French' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(T1.id), 0) FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid WHERE T1.isStorySpotlight = 1
```

### BIRD-PG-0407：输出字段组（P2）

- 原始问题：Lists all types of cards in German.
- 官方evidence：German refer to language; all types refer to the subtypes, supertypes; subtypes is not null AND supertypes is not null
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：预测输出 foreign_data.type 单列，参考为 cards.subtypes、supertypes 两列；evidence已明确两类字段，且要求各自非NULL。

预测/参考：2150/1693行，1/2列。

捕获的最终SQL：

```sql
SELECT DISTINCT fd.type FROM foreign_data fd WHERE fd.language = 'German' AND fd.type IS NOT NULL
```

冻结参考SQL（仅审查端）：

```sql
SELECT T1.subtypes, T1.supertypes FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid WHERE T2.language = 'German' AND NOT T1.subtypes IS NULL AND NOT T1.supertypes IS NULL
```

### BIRD-PG-0415：规范字面值（P2）

- 原始问题：What percentage of cards with format commander and legal status do not have a content warning?
- 官方evidence：do not have a content warning refers to hasContentWarning = 0; percentage refers to DIVIDE(COUNT(hasContentWarning = 0),COUNT(ID))*100 where format = 'commander' AND Status = 'legal';
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：预测保留 status=legal，参考为 Legal；本轮单值分别为NULL与非NULL百分数。应验证授权库的真实大小写及规范值查询覆盖，不应在评分端忽略大小写。

预测/参考：1/1行，1/1列。

捕获的最终SQL：

```sql
SELECT CAST(SUM(CASE WHEN c.hascontentwarning = 0 THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(*), 0) AS percentage FROM cards c JOIN legalities l ON c.uuid = l.uuid WHERE l.format = 'commander' AND l.status = 'legal'
```

冻结参考SQL（仅审查端）：

```sql
SELECT CAST(SUM(CASE WHEN T1.hasContentWarning = 0 THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(T1.id), 0) FROM cards AS T1 INNER JOIN legalities AS T2 ON T1.uuid = T2.uuid WHERE T2.format = 'commander' AND T2.status = 'Legal'
```

### BIRD-PG-0473：输出编码与参考形态（P2）

- 原始问题：Is the set of cards with Adarkar Valkyrie only available outside the United States?
- 官方evidence：card set Adarkar Valkyrie refers to name = 'Adarkar Valkyrie'; isForeignOnly = 1 means only available outside the United States;
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：预测为 isforeignonly 原始数字单列，参考映射为YES/NO。原生集合编码不同；重复行数本身被EX忽略，不能据1行与5行直接认定失败原因。

预测/参考：1/5行，1/1列。

捕获的最终SQL：

```sql
SELECT DISTINCT s.isforeignonly FROM cards c JOIN sets s ON c.setcode = s.code WHERE c.name = 'Adarkar Valkyrie'
```

冻结参考SQL（仅审查端）：

```sql
SELECT CASE WHEN isForeignOnly = 1 THEN 'YES' ELSE 'NO' END FROM cards AS T1 INNER JOIN sets AS T2 ON T2.code = T1.setCode WHERE T1.name = 'Adarkar Valkyrie'
```

### BIRD-PG-0595：统计粒度与关系角色（P2）

- 原始问题：Which user have only one post history per post and having at least 1000 views?
- 官方evidence：having at least 1000 view refers to Views > = 1000; user refers to UserId
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：预测按 user、post 分组并计历史记录行数；参考按用户分组、统计不同 PostHistoryTypeId。题目 per post 与参考统计范围还需独立审查。

预测/参考：270/94行，1/1列。

捕获的最终SQL：

```sql
SELECT DISTINCT u.id
FROM users u
JOIN posthistory ph ON u.id = ph.userid
JOIN posts p ON ph.postid = p.id
WHERE p.viewcount >= 1000
GROUP BY u.id, ph.postid
HAVING COUNT(ph.id) = 1
```

冻结参考SQL（仅审查端）：

```sql
SELECT T2.UserId FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T2.PostId = T3.Id WHERE T3.ViewCount >= 1000 GROUP BY T2.UserId HAVING COUNT(DISTINCT T2.PostHistoryTypeId) = 1
```

### BIRD-PG-0604：参与者动作角色（P2）

- 原始问题：What is the average of the up votes and the average user age for users creating more than 10 posts?
- 官方evidence：creating more than 10 post refers to Count (UserId) > 10; average of the up votes = Divide (Sum(UpVotes), Count (UserId)); average age = Divide (Sum(Age), Count(UserId))
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：把 creating posts 理解成 votes.userid 的投票次数；参考按 posts.owneruserid 统计发帖数后平均用户属性。

预测/参考：1/1行，2/2列。

捕获的最终SQL：

```sql
WITH user_post_counts AS (
    SELECT 
        u.id,
        u.upvotes,
        u.age,
        COUNT(v.userid) AS post_count
    FROM users u
    JOIN votes v ON u.id = v.userid
    GROUP BY u.id, u.upvotes, u.age
)
SELECT 
    AVG(upvotes * 1.0) AS average_upvotes,
    AVG(age * 1.0) AS average_age
FROM user_post_counts
WHERE post_count > 10
```

冻结参考SQL（仅审查端）：

```sql
SELECT AVG(T1.UpVotes), AVG(T1.Age) FROM users AS T1 INNER JOIN (SELECT OwnerUserId, COUNT(*) AS post_count FROM posts GROUP BY OwnerUserId HAVING COUNT(*) > 10) AS T2 ON T1.Id = T2.OwnerUserId
```

### BIRD-PG-0639：不存在表与重复阻断（P2）

- 原始问题：Based on posts posted by Community, calculate the percentage of posts that use the R language.
- 官方evidence：DIVIDE(COUNT(PostId WHERE TagName = 'r')), (COUNT(PostId WHERE DisplayName = 'Community')) as percentage; R language refers to tagname = 'r'
- 本轮状态：repeated_sql；原基线匹配：False；本轮匹配：False。
- 审查：模型两次使用不在授权catalog中的posttags；首次被本地来源策略拒绝，第二次因重复SQL阻断，未提交PG分析。来源拒绝及重复保护有效；后续需核实公开关系路径，不能放开posttags。

第1次拒绝：sql_source_denied；业务约束：无。

```sql
SELECT CAST(SUM(CASE WHEN t.tagname = 'r' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(*), 0) AS percentage FROM posts p JOIN users u ON p.owneruserid = u.id LEFT JOIN posttags pt ON p.id = pt.postid LEFT JOIN tags t ON pt.tagid = t.id WHERE u.displayname = 'Community'
```

第2次拒绝：repeated_invalid_sql；业务约束：无。

```sql
SELECT CAST(SUM(CASE WHEN t.tagname = 'r' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(*), 0) AS percentage FROM posts p JOIN users u ON p.owneruserid = u.id LEFT JOIN posttags pt ON p.id = pt.postid LEFT JOIN tags t ON pt.tagid = t.id WHERE u.displayname = 'Community'
```

### BIRD-PG-1479：遗漏条件与多余输出（P1）

- 原始问题：Which year recorded the most consumption of gas paid in CZK?
- 官方evidence：The first 4 strings of the Date values in the yearmonth table can represent year.
- 本轮状态：diagnostic_answered；原基线匹配：True；本轮匹配：False。
- 审查：原基线通过；当前图只有 yearmonth.consumption/date，未覆盖 customers.currency，SQL漏CZK且多输出 total_consumption。年份恰同为2013仍因额外列原生不匹配。基线SQL也漏CZK但在当前数据碰巧匹配，不能回退到该不完整写法。

预测/参考：1/1行，2/1列。

捕获的最终SQL：

```sql
SELECT SUBSTRING(date FROM 1 FOR 4) AS year, SUM(consumption) AS total_consumption FROM yearmonth GROUP BY SUBSTRING(date FROM 1 FOR 4) ORDER BY total_consumption DESC NULLS LAST LIMIT 1
```

冻结参考SQL（仅审查端）：

```sql
SELECT SUBSTR(T2.Date, 1, 4) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' GROUP BY SUBSTR(T2.Date, 1, 4) ORDER BY SUM(T2.Consumption) DESC NULLS LAST LIMIT 1
```

### BIRD-PG-1480：遗漏分群条件（P2）

- 原始问题：What was the gas consumption peak month for SME customers in 2013?
- 官方evidence：Year 2013 can be presented as Between 201301 And 201312; The first 4 strings of the Date values in the yearmonth table can represent year; The 5th and 6th string of the date can refer to month.
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：保留2013，但漏掉 customers.segment=SME，转而增加 consumption>0 子查询。

预测/参考：1/1行，1/1列。

捕获的最终SQL：

```sql
SELECT SUBSTRING(date FROM 5 FOR 2) AS month
FROM yearmonth
WHERE customerid IN (SELECT customerid FROM yearmonth WHERE consumption > 0 AND date BETWEEN '201301' AND '201312')
  AND date BETWEEN '201301' AND '201312'
GROUP BY SUBSTRING(date FROM 5 FOR 2)
ORDER BY SUM(consumption) DESC NULLS LAST
LIMIT 1
```

冻结参考SQL（仅审查端）：

```sql
SELECT SUBSTR(T2.Date, 5, 2) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY SUBSTR(T2.Date, 5, 2) ORDER BY SUM(T2.Consumption) DESC NULLS LAST LIMIT 1
```

### BIRD-PG-1481：最低值选择与平均范围（P2）

- 原始问题：What is the difference in the annual average consumption of the customers with the least amount of consumption paid in CZK for 2013 between SME and LAM, LAM and KAM, and KAM and SME?
- 官方evidence：annual average consumption of customer with the lowest consumption in each segment = total consumption per year / the number of customer with lowest consumption in each segment; Difference in annual average = SME's annual average - LAM's annual average; Difference in annual average = LAM's annual average - KAM's annual average; Year 2013 can be presented as Between 201301 And 201312; The first 4 strings of the Date values in the yearmonth table can represent year.
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：预测按分群选最低消费再平均；参考按全局最低消费过滤，采用全体结果分母。题目本身包含 each segment，存在参考口径审查需求；先固定差异，不据参考自动改变业务解释。

预测/参考：1/1行，3/3列。

捕获的最终SQL：

```sql
WITH y2013 AS (
    SELECT c.segment, y.consumption
    FROM yearmonth y
    JOIN customers c ON y.customerid = c.customerid
    WHERE LEFT(y.date, 4) = '2013'
      AND c.currency = 'CZK'
),
min_consumption AS (
    SELECT segment, MIN(consumption) AS min_cons
    FROM y2013
    GROUP BY segment
),
lowest_customers AS (
    SELECT y.segment, y.consumption
    FROM y2013 y
    JOIN min_consumption m ON y.segment = m.segment AND y.consumption = m.min_cons
),
avg_annual AS (
    SELECT segment, AVG(consumption) AS avg_cons
    FROM lowest_customers
    GROUP BY segment
)
SELECT 
    (SELECT avg_cons FROM avg_annual WHERE segment = 'SME') - (SELECT avg_cons FROM avg_annual WHERE segment = 'LAM') AS diff_sme_lam,
    (SELECT avg_cons FROM avg_annual WHERE segment = 'LAM') - (SELECT avg_cons FROM avg_annual WHERE segment = 'KAM') AS diff_lam_kam,
    (SELECT avg_cons FROM avg_annual WHERE segment = 'KAM') - (SELECT avg_cons FROM avg_annual WHERE segment = 'SME') AS diff_kam_sme
```

冻结参考SQL（仅审查端）：

```sql
SELECT CAST(SUM(CASE WHEN T1.Segment = 'SME' THEN T2.Consumption ELSE 0 END) AS REAL) / NULLIF(COUNT(T1.CustomerID), 0) - CAST(SUM(CASE WHEN T1.Segment = 'LAM' THEN T2.Consumption ELSE 0 END) AS REAL) / NULLIF(COUNT(T1.CustomerID), 0), CAST(SUM(CASE WHEN T1.Segment = 'LAM' THEN T2.Consumption ELSE 0 END) AS REAL) / NULLIF(COUNT(T1.CustomerID), 0) - CAST(SUM(CASE WHEN T1.Segment = 'KAM' THEN T2.Consumption ELSE 0 END) AS REAL) / NULLIF(COUNT(T1.CustomerID), 0), CAST(SUM(CASE WHEN T1.Segment = 'KAM' THEN T2.Consumption ELSE 0 END) AS REAL) / NULLIF(COUNT(T1.CustomerID), 0) - CAST(SUM(CASE WHEN T1.Segment = 'SME' THEN T2.Consumption ELSE 0 END) AS REAL) / NULLIF(COUNT(T1.CustomerID), 0) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' AND T2.Consumption = (SELECT MIN(Consumption) FROM yearmonth) AND T2.Date::text BETWEEN '201301' AND '201312'
```

### BIRD-PG-1505：去重实体与记录数（P2）

- 原始问题：Among the customers who paid in euro, how many of them have a monthly consumption of over 1000?
- 官方evidence：Pays in euro = Currency = 'EUR'.
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：预测 COUNT(DISTINCT customerid)，参考 COUNT(*)；题目客户数量与参考月度记录数量有口径差异，需要单列调查，不能无条件要求DISTINCT或禁止DISTINCT。

预测/参考：1/1行，1/1列。

捕获的最终SQL：

```sql
SELECT COUNT(DISTINCT y.customerid) FROM yearmonth y JOIN customers c ON y.customerid = c.customerid WHERE c.currency = 'EUR' AND y.consumption > 1000
```

冻结参考SQL（仅审查端）：

```sql
SELECT COUNT(*) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

### BIRD-PG-1524：澄清与参考实体歧义（P2）

- 原始问题：What's the nationality of the customer who spent 548.4 in 2012/8/24?
- 官方evidence：'2012/8/24' can be represented by '2012-08-24'; spent 548.4 refers to price = '548.4' 
- 本轮状态：clarification；原基线匹配：False；本轮匹配：False。
- 审查：最终图只有transactions_1k.price/date/customerid，模型说明缺客户国籍。授权customers确实只有customerid/segment/currency；冻结参考却经gasstationid取gasstations.country（加油站国家）。同时存在图覆盖不足及客户国籍/加油站国家语义差异，不能简单强制该JOIN并宣称语义修复。

模型澄清解释：

The schema for table 'transactions_1k' only contains 'price', 'date', and 'customerid'. There is no column for 'nationality' in this table, nor is there any other table provided in the schema to join with to retrieve customer nationality information.

### BIRD-PG-1533：关联键错误（P2）

- 原始问题：For all the people who paid more than 29.00 per unit of product id No.5. Give their consumption status in the August of 2012.
- 官方evidence：August of 2012 refers to the Date value = '201208' ; Price per unit of product = Price / Amount;
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：预测按交易年月与 yearmonth.date 关联，缺 customerid 关联；结果17010行对10行，明显扩大关联总体。

预测/参考：17010/10行，1/1列。

捕获的最终SQL：

```sql
SELECT DISTINCT y.consumption
FROM transactions_1k t
JOIN yearmonth y ON TO_CHAR(t.date, 'YYYYMM') = y.date
WHERE t.productid = 5
  AND (t.price / NULLIF(t.amount, 0)) > 29.00
  AND y.date = '201208'
```

冻结参考SQL（仅审查端）：

```sql
SELECT T2.Consumption FROM transactions_1k AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Price / NULLIF(T1.Amount, 0) > 29.00 AND T1.ProductID = 5 AND T2.Date = '201208'
```

### BIRD-PG-0115：文本数值与分组范围（P2）

- 原始问题：For the branch which located in the south Bohemia with biggest number of inhabitants, what is the percentage of the male clients?
- 官方evidence：Percentage of the male clients = DIVIDE(COUNT(male clients), COUNT(clients)) * 100; Male refers to gender = 'M', A3 is the region name. A4 contains the information about inhabitants.
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：预测把 A4 转INTEGER后挑单个 district；参考按文本A4分组排序并取首组。需确认字段原生类型及题意，再说明参考形态差异；当前不能通过类型转换评分。

预测/参考：1/1行，1/1列。

捕获的最终SQL：

```sql
WITH target_district AS (
    SELECT district_id
    FROM district
    WHERE a3 = 'south Bohemia'
    ORDER BY CAST(a4 AS INTEGER) DESC NULLS LAST
    LIMIT 1
)
SELECT 
    CAST(SUM(CASE WHEN c.gender = 'M' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(*), 0) AS percentage_male_clients
FROM client c
JOIN target_district td ON c.district_id = td.district_id;
```

冻结参考SQL（仅审查端）：

```sql
SELECT CAST(SUM(CASE WHEN T1.gender = 'M' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(T1.client_id), 0) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY T2.A4 DESC LIMIT 1
```

### BIRD-PG-0145：日期归属与输出实体（P2）

- 原始问题：Who are the account holder identification numbers whose who have transactions on the credit card with the amount is less than the average, in 1998?
- 官方evidence：Operation = 'VYBER KARTOU' refers to credit card withdrawal
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：修复移除受限 TO_TIMESTAMP 后改用 card.issued 年份，偏离交易日期；同时输出 client_id 而参考 account_id。语法修复不应改变日期所属实体。

预测/参考：277/4484行，1/1列。

捕获的最终SQL：

```sql
WITH avg_amt AS (
    SELECT AVG(t.amount) AS val
    FROM trans t
    JOIN card c ON t.account_id = (SELECT d.account_id FROM disp d WHERE d.disp_id = c.disp_id)
    WHERE t.operation = 'VYBER KARTOU'
      AND EXTRACT(YEAR FROM c.issued) = 1998
)
SELECT DISTINCT d.client_id
FROM trans t
JOIN card c ON t.account_id = (SELECT d2.account_id FROM disp d2 WHERE d2.disp_id = c.disp_id)
JOIN disp d ON c.disp_id = d.disp_id
CROSS JOIN avg_amt a
WHERE t.operation = 'VYBER KARTOU'
  AND EXTRACT(YEAR FROM c.issued) = 1998
  AND t.amount < a.val;
```

冻结参考SQL（仅审查端）：

```sql
SELECT T1.account_id FROM trans AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE TO_CHAR(CAST(T1.date AS TIMESTAMP), 'YYYY') = '1998' AND T1.operation = 'VYBER KARTOU' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE TO_CHAR(CAST(date AS TIMESTAMP), 'YYYY') = '1998')
```

### BIRD-PG-0152：授权关联表未进图（P2）

- 原始问题：What is the average number of crimes committed in 1995 in regions where the number exceeds 4000 and the region has accounts that are opened starting from the year 1997?
- 官方evidence：A3 refers to region names; A15 stands for the average number of crimes commited in 1995.
- 本轮状态：clarification；原基线匹配：False；本轮匹配：False。
- 审查：最终图只有district.a15/a3；模型说明缺1997年起开户信息。授权catalog存在account及日期字段，但未进入最终图，应按公开问题补齐日期与关联键路径。

模型澄清解释：

The question requires filtering regions based on accounts opened starting from 1997, but the provided schema only contains the 'district' table with fields for region name (a3) and crime statistics (a15). There is no 'account' table or any field indicating account opening dates in the supplied schema.

### BIRD-PG-0173：金额与账号角色混淆（P1）

- 原始问题：How often does account number 3 request an account statement to be released? What was the aim of debiting 3539 in total?
- 官方evidence：k_symbol refers to the purpose of payments
- 本轮状态：diagnostic_answered；原基线匹配：True；本轮匹配：False。
- 审查：原基线通过；当前把总扣款3539解释成 order.account_to=3539，并拆成互不关联的子查询；第二列为NULL而参考为POJISTNE。应保留account_id=3与金额总和的关系。

预测/参考：1/1行，2/2列。

捕获的最终SQL：

```sql
WITH part1 AS (
    SELECT a.frequency
    FROM account a
    WHERE a.account_id = 3
),
part2 AS (
    SELECT o.k_symbol
    FROM "order" o
    WHERE o.account_to = 3539
)
SELECT 
    (SELECT frequency FROM part1) AS statement_frequency,
    (SELECT k_symbol FROM part2) AS debit_aim
```

冻结参考SQL（仅审查端）：

```sql
SELECT T1.frequency, T2.k_symbol FROM account AS T1 INNER JOIN (SELECT account_id, k_symbol, SUM(amount) AS total_amount FROM "order" GROUP BY account_id, k_symbol) AS T2 ON T1.account_id = T2.account_id WHERE T1.account_id = 3 AND T2.total_amount = 3539
```

### BIRD-PG-1399：已知参考答案形态（P3）

- 原始问题：Did Maya Mclean attend the 'Women's Soccer' event?
- 官方evidence：Maya Mclean is the full name; full name refers to first_name, last_name; 'Women's Soccer' is an event_name
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：仍为标量Yes，对参考YES/NULL集合；参考有14行、集合有2种值。保持既有已知问题记录，不改标签、NULL或EX。

预测/参考：1/14行，1/1列。

捕获的最终SQL：

```sql
SELECT CASE WHEN COUNT(*) > 0 THEN 'Yes' ELSE 'No' END AS attended FROM attendance a JOIN member m ON a.link_to_member = m.member_id JOIN event e ON a.link_to_event = e.event_id WHERE m.first_name = 'Maya' AND m.last_name = 'Mclean' AND e.event_name = 'Women''s Soccer'
```

冻结参考SQL（仅审查端）：

```sql
SELECT CASE WHEN T3.event_name = 'Women''s Soccer' THEN 'YES' END AS result FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member INNER JOIN event AS T3 ON T2.link_to_event = T3.event_id WHERE T1.first_name = 'Maya' AND T1.last_name = 'Mclean'
```

### BIRD-PG-1427：参考上下文输出列（P2）

- 原始问题：What are the budget category of the events located at MU 215 and a guest speaker type with a 0 budget spent?
- 官方evidence：budget category refers to category; events located at refers to location; type = 'Guest Speaker'; 0 budget spent refers to spent = 0; 
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：预测只有 budget.category，参考另含 event.type；题目问类别、type同时作为筛选条件，是否必须输出上下文应公开约定，不能为过分而普遍强加所有筛选字段。

预测/参考：4/4行，1/2列。

捕获的最终SQL：

```sql
SELECT DISTINCT b.category FROM budget b JOIN event e ON b.link_to_event = e.event_id WHERE e.location = 'MU 215' AND e.type = 'Guest Speaker' AND b.spent = 0
```

冻结参考SQL（仅审查端）：

```sql
SELECT DISTINCT T2.category, T1.type FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215' AND T2.spent = 0 AND T1.type = 'Guest Speaker'
```

### BIRD-PG-0726：排名输出形态（P2）

- 原始问题：Rank heroes published by Marvel Comics by their height in descending order.
- 官方evidence：name refers to superhero_name; the tallest hero refers to MAX(height_cm); published by Marvel Comics refers to publisher_name = 'Marvel Comics'
- 本轮状态：diagnostic_answered；原基线匹配：False；本轮匹配：False。
- 审查：预测只返回姓名并排序；参考额外输出 height_cm、RANK()。行数同为387不能替代列组一致性；需要区分有序列表与显式名次列。

预测/参考：387/387行，1/3列。

捕获的最终SQL：

```sql
SELECT s.superhero_name FROM superhero s JOIN publisher p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' ORDER BY s.height_cm DESC NULLS LAST
```

冻结参考SQL（仅审查端）：

```sql
SELECT superhero_name, height_cm, RANK() OVER (ORDER BY height_cm DESC NULLS LAST) AS HeightRank FROM superhero INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics'
```

### BIRD-PG-0226：显式小数精度未落实（P1）

- 原始问题：What is the percentage of double bonds in the molecule TR008? Please provide your answer as a percentage with five decimal places.
- 官方evidence：double bond refers to bond_type = '='; TR008 is the molecule id; percentage = DIVIDE(SUM(bond_type = '='), COUNT(bond_id)) as percent where molecule_id = 'TR008'
- 本轮状态：diagnostic_answered；原基线匹配：True；本轮匹配：False。
- 审查：原基线通过；题目明确 five decimal places，contract已标记explicit_rounding，但SQL仍输出未舍入DOUBLE。预测约3.8461538461538463，参考Decimal 3.84615；应落实公开精度请求，不应新增数值容差。

预测/参考：1/1行，1/1列。

捕获的最终SQL：

```sql
SELECT CAST(SUM(CASE WHEN bond_type = '=' THEN 1 ELSE 0 END) AS DOUBLE PRECISION) * 100 / NULLIF(COUNT(bond_id), 0) AS percent FROM bond WHERE molecule_id = 'TR008'
```

冻结参考SQL（仅审查端）：

```sql
SELECT ROUND(CAST(COUNT(CASE WHEN T.bond_type = '=' THEN T.bond_id ELSE NULL END) AS NUMERIC) * 100 / CAST(COUNT(T.bond_id) AS NUMERIC), 5) AS percentage FROM bond AS T WHERE T.molecule_id = 'TR008'
```

### BIRD-PG-0239：关系端点扩张（P1）

- 原始问题：How many connections does the atom 19 have?
- 官方evidence：connections refers to bond_id; atom 19 refers to atom_id like 'TR%_19';
- 本轮状态：diagnostic_answered；原基线匹配：True；本轮匹配：False。
- 审查：原基线通过；当前同时匹配 atom_id 与 atom_id2，结果754，参考为377。需核实有向/双向连接记录语义与公开 evidence 指定端点，不能用OR自动扩展两端。

预测/参考：1/1行，1/1列。

捕获的最终SQL：

```sql
SELECT COUNT(*) FROM connected WHERE atom_id LIKE 'TR%_19' OR atom_id2 LIKE 'TR%_19'
```

冻结参考SQL（仅审查端）：

```sql
SELECT COUNT(T.bond_id) FROM connected AS T WHERE RIGHT(T.atom_id, 2) = '19'
```

### BIRD-PG-0263：粒度硬约束改变口径（P1）

- 原始问题：What is the composition of element chlorine in percentage among the single bond molecules?
- 官方evidence：element chlorine refers to element = 'cl'; single bond refers to bond_type = '-'; percentage = DIVIDE(SUM(element = 'cl'), COUNT(atom_id)) as percent where bond_type = '-'
- 本轮状态：diagnostic_answered；原基线匹配：True；本轮匹配：False。
- 审查：原基线通过；首次SQL被entity_grain_fanout拒绝，随后先加DISTINCT再改EXISTS。最终是原子去重总体，参考保留atom-bond关联权重。需先复用被拒绝首次SQL做无模型原生验证，判断是否误拒绝；不可把0201的半连接策略无条件推广。

预测/参考：1/1行，1/1列。

捕获的最终SQL：

```sql
SELECT CAST(SUM(CASE WHEN a.element = 'cl' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(DISTINCT a.atom_id), 0) AS percent FROM atom a WHERE EXISTS (SELECT 1 FROM bond b WHERE b.molecule_id = a.molecule_id AND b.bond_type = '-')
```

冻结参考SQL（仅审查端）：

```sql
SELECT CAST(COUNT(CASE WHEN T.element = 'cl' THEN T.atom_id ELSE NULL END) AS REAL) * 100 / NULLIF(COUNT(T.atom_id), 0) FROM (SELECT T1.atom_id, T1.element FROM atom AS T1 INNER JOIN molecule AS T2 ON T1.molecule_id = T2.molecule_id INNER JOIN bond AS T3 ON T2.molecule_id = T3.molecule_id WHERE T3.bond_type = '-') AS T
```

### BIRD-PG-0273：公开evidence冲突及粒度误判风险（P1）

- 原始问题：What is the percentage of element chlorine in carcinogenic molecules?
- 官方evidence：chlorine refers to element = 'cl'; label = '+' mean molecules are carcinogenic; percentage = DIVIDE(SUM(element = 'pb'); COUNT(molecule_id)) as percentage where label = '+'
- 本轮状态：validation_failed；原基线匹配：True；本轮匹配：False。
- 审查：原基线通过，本次3次校验均失败且未执行结果SQL。公开文本同时有chlorine=cl及公式SUM(element=pb)，当前把cl、pb都设为强制条件，并从COUNT(molecule_id)推定分子去重粒度。冻结参考统计致癌分子中的cl原子，不要求pb。需冲突检测及粒度适用范围审查；先原生复评首次被拒SQL，不能把参考注入模型。

第1次拒绝：intent_contract_violation；业务约束：missing_population_condition, entity_grain_fanout。

```sql
SELECT CAST(SUM(CASE WHEN a.element = 'cl' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(*), 0) AS percentage FROM molecule m JOIN atom a ON m.molecule_id = a.molecule_id WHERE m.label = '+'
```

第2次拒绝：intent_contract_violation；业务约束：entity_grain_fanout。

```sql
SELECT CAST(SUM(CASE WHEN a.element = 'cl' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(DISTINCT m.molecule_id), 0) AS percentage FROM molecule m JOIN atom a ON m.molecule_id = a.molecule_id WHERE m.label = '+' AND EXISTS (SELECT 1 FROM atom a2 WHERE a2.molecule_id = m.molecule_id AND a2.element = 'pb')
```

第3次拒绝：intent_contract_violation；业务约束：missing_population_condition, entity_grain_fanout。

```sql
SELECT CAST(SUM(CASE WHEN a.element = 'cl' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(DISTINCT m.molecule_id), 0) AS percentage FROM molecule m JOIN atom a ON m.molecule_id = a.molecule_id WHERE m.label = '+'
```

## 下一步建议

1. 保留本轮原始报告及本地审查记录；先不重跑完整80题，也不打开holdout30。
2. 先准备仅使用已捕获SQL的无模型诊断：0263、0273首次被拒SQL，配合0201成功轨迹作粒度对照。绑定报告与SQL哈希，单独输出新报告，不改写本轮得分。
3. 依据证据修复通用规则：粒度约束适用范围、公开evidence冲突、显式精度落实；补充正反例回归测试。
4. 再处理0173/0239的语义角色，以及1479/0152的授权图条件覆盖；1524的客户国籍与加油站国家单独列为语义歧义。
5. 先对定向小集生成并独立原生复评，确认旧成功保持后再扩到80题。同时压缩重复提示和反馈，观察chat token及p95。

## 核对范围与限制

- 可从报告完整预览独立重建130个原生结果对象、64题完整比较；另22个大结果对象只有截断预览。
- 大结果的完整集合比较仍依赖服务器的比较记录及哈希。远程索引文件本体未下载，已核对报告中的身份、文件哈希关联和Schema图内容哈希。
- 相同模型名称、temperature=0和相同配置不保证服务权重未变或输出完全确定；21新增/6退化是本轮配对观测，不将所有差异归因于单个规则。
- 本地检查不重新证明当前远程数据库状态；核对的是两次服务器运行记录的实时验证材料、身份及结果一致性。
- 保持原生tuple-set EX；不增加别名、数值容差、标签转换、结果舍入或列裁剪。
