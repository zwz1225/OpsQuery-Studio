# M3 A：逐题失败归因与首轮目标

整理日期：2026-10-21（Asia/Shanghai）。

**A阶段完成：已核对开发80题，归档30个失败、选择20个成功回归题，并确定首轮公开输出契约实验。尚未修改运行链路或启动模型实验。**

## 1. 材料和审查边界

- M2 v4开发基线50/80：27题原生不匹配，3题未回答；全部保留固定80题分母。
- 开发50个成功题全部登记；其中20题组成首轮回归集，覆盖全部8个开发域。
- 保留11个失败仅作已观察补充诊断，不进入本轮24题生成清单，不称为新的未见测试。
- 本次0模型调用、未连接数据库、未重新执行SQL、未修改题库/Gold/评分器/冻结产物。
- 每题主分类互斥，伴随标签可重叠。分类是排查组织方式，不表示单一根因已经由反事实实验证明。
- SQL和公开输入的差异、字段是否进入图可直接核实；完整EX沿用已验收服务器原生比较。截断预览不作完整复评，也不用于证明全部差异的原因。
- JSON含参考SQL和审查判断，仅供可信审查；Agent只接收既定五字段公开输入及授权元数据。

历史v4开发核对文件中“尚未开启holdout”是当时状态；最终M2状态以[M2最终验收](M2_FINAL_ACCEPTANCE_20261019.md)为准。

## 2. 开发集失败主分类

| 主分类 | 题数 | 题号 |
| --- | ---: | --- |
| 实体标识角色选择 | 1 | 0011 |
| 检索／关联上下文缺口 | 9 | 0025, 0072, 0352, 0371, 0604, 1479, 1480, 1533, 0152 |
| 明确输出项／顺序未落实 | 3 | 0050, 0085, 0407 |
| 数值路径与名称来源并存差异 | 1 | 0077 |
| 条件／时间／关系角色解释 | 4 | 0083, 0145, 0173, 0239 |
| 规范字面值绑定 | 1 | 0415 |
| 参考形态／公开口径待澄清 | 10 | 0473, 0595, 1481, 1505, 1524, 0115, 1399, 1427, 0726, 0201 |
| 来源拒绝后的重复失败 | 1 | 0639 |

这30题中没有最终仍执行报错的回答题；1533曾除零后恢复，但答案仍错。3题未回答为0639重复终止、1524和0152澄清。

## 3. 逐题审查

### BIRD-PG-0011 · california_schools

- **主分类**：实体标识角色选择；状态：`diagnostic_answered`。
- **问题**：Please list the codes of the schools with a total enrollment of over 500.
- **公开evidence**：Total enrollment can be represented by `Enrollment (K-12)` + `Enrollment (Ages 5-17)`
- **已观察差异**：输出frpm.School Code，而参考输出frpm.cdscode；均7806行，但学校短码与完整CDS码的原生元组不同。
- **归因依据**：cdscode虽未作为检索字段入选，已作为关联键进入最终图；不能把失败直接归因于字段完全未提供。模型选择了不同语义的标识。
- **仍待核实**：题面仅说codes，具体标识约定仍需官方字段说明支持；不依据Gold强制所有学校编号都使用CDS码。
- **后续方向**：核对授权标识说明与主键角色，建立标识歧义提示。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `california_schools.frpm.School Code` | 0.558631 | selected | 是 |
| `california_schools.frpm.cdscode` | 0.466669 | below_coverage_floor | 是 |

保存的最终SQL：

```sql
SELECT "School Code" FROM frpm WHERE ("Enrollment (K-12)" + "Enrollment (Ages 5-17)") > 500
```

参考SQL仅供可信审查：

```sql
SELECT T2.CDSCode FROM schools AS T1 INNER JOIN frpm AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2."Enrollment (K-12)" + T2."Enrollment (Ages 5-17)" > 500
```

### BIRD-PG-0025 · california_schools

- **主分类**：检索／关联上下文缺口；状态：`diagnostic_answered`。
- **问题**：Name schools in Riverside which the average of average math score for SAT is grater than 400, what is the funding type of these schools?
- **公开evidence**：Average of average math = sum(average math scores) / count(schools).
- **已观察差异**：把Riverside绑定到satscores.rtype并使用schools.fundingtype，预测0行、参考6行；参考使用frpm.District Name及Charter Funding Type。
- **归因依据**：Charter Funding Type已在图中，但District Name未进入最终图；同时存在地点覆盖缺口与同名业务字段角色选择问题。
- **仍待核实**：需授权字段说明／数据探测确认Riverside的地点层级和两种资金字段区别；AVG与SUM/COUNT的空值差异尚未单独验证。
- **后续方向**：优先补公开地点角色与授权字段覆盖，随后独立验证聚合口径。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `california_schools.frpm.District Name` | 未在候选记录出现 | 无候选筛选记录 | 否 |
| `california_schools.frpm.Charter Funding Type` | 0.620905 | selected | 是 |
| `california_schools.schools.fundingtype` | 0.685856 | selected | 是 |
| `california_schools.satscores.rtype` | 0.612814 | selected | 是 |

保存的最终SQL：

```sql
SELECT s.sname, sc.fundingtype FROM satscores s JOIN schools sc ON s.cds = sc.cdscode WHERE s.rtype = 'Riverside' GROUP BY s.sname, sc.fundingtype HAVING AVG(s.avgscrmath) > 400
```

参考SQL仅供可信审查：

```sql
SELECT T1.sname, T2."Charter Funding Type" FROM satscores AS T1 INNER JOIN frpm AS T2 ON T1.cds = T2.CDSCode WHERE T2."District Name" LIKE 'Riverside%' GROUP BY T1.sname, T2."Charter Funding Type" HAVING CAST(SUM(T1.AvgScrMath) AS REAL) / NULLIF(COUNT(T1.cds), 0) > 400
```

### BIRD-PG-0050 · california_schools

- **主分类**：明确输出项／顺序未落实；状态：`diagnostic_answered`。
- **问题**：What is the postal street address for the school with the 7th highest Math average? Indicate the school's name.
- **公开evidence**：Postal street and mailing street are synonyms.
- **已观察差异**：最终一行是(NULL,地址)，参考为(地址,NULL)，列顺序相反；首次sc别名错误已修复。
- **归因依据**：mailstreet、street、school和sname均在最终图中。问题先问postal street address，再要求school name；输出顺序没有落实公开请求。
- **仍待核实**：最终用了street而非公开同义指向的mailstreet，本次两地址相同；不能由这一行证明两字段普遍等价。
- **后续方向**：首轮主目标：按公开请求生成有序输出清单，保留邮寄地址角色。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `california_schools.schools.mailstreet` | 0.642024 | selected | 是 |
| `california_schools.schools.street` | 0.494179 | selected_intent_coverage | 是 |
| `california_schools.schools.school` | 未在候选记录出现 | 无候选筛选记录 | 是 |
| `california_schools.satscores.sname` | 0.547944 | selected_coverage | 是 |

保存的最终SQL：

```sql
SELECT s.school, s.street AS postal_street_address FROM schools s JOIN satscores sa ON s.cdscode = sa.cds ORDER BY sa.avgscrmath DESC NULLS LAST LIMIT 1 OFFSET 6
```

参考SQL仅供可信审查：

```sql
SELECT T2.MailStreet, T2.School FROM satscores AS T1 INNER JOIN schools AS T2 ON T1.cds = T2.CDSCode ORDER BY T1.AvgScrMath DESC NULLS LAST LIMIT 1 OFFSET 6
```

### BIRD-PG-0072 · california_schools

- **主分类**：检索／关联上下文缺口；状态：`diagnostic_answered`。
- **问题**：How many students from the ages of 5 to 17 are enrolled at the State Special School school in Fremont for the 2014-2015 academic year?
- **公开evidence**：State Special School means EdOpsCode = 'SSS'
- **已观察差异**：将Fremont作为学校名、把2014-2015改写为2014-15并SUM；预测一个NULL，参考两行人数。
- **归因依据**：schools.city未进入最终图，模型把地点绑定到school；学年字面值改写及求和是另外的已观察差异。
- **仍待核实**：how many与逐校行输出之间存在形态解释空间；不把参考的两行形式直接推广为规则。
- **后续方向**：补城市角色并保留公开学年原值；再分离检查是否应聚合。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `california_schools.schools.city` | 未在候选记录出现 | 无候选筛选记录 | 否 |
| `california_schools.schools.school` | 未在候选记录出现 | 无候选筛选记录 | 是 |
| `california_schools.frpm.Academic Year` | 0.510843 | selected_coverage | 是 |

保存的最终SQL：

```sql
SELECT SUM(f."Enrollment (Ages 5-17)") FROM frpm f JOIN schools s ON f.cdscode = s.cdscode WHERE s.edopscode = 'SSS' AND s.school = 'Fremont' AND f."Academic Year" = '2014-15'
```

参考SQL仅供可信审查：

```sql
SELECT T1."Enrollment (Ages 5-17)" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.EdOpsCode = 'SSS' AND T2.City = 'Fremont' AND T1."Academic Year" = '2014-2015'
```

### BIRD-PG-0077 · california_schools

- **主分类**：数值路径与名称来源并存差异；状态：`diagnostic_answered`。
- **问题**：Which schools served a grade span of Kindergarten to 9th grade in the county of Los Angeles and what is its Percent (%) Eligible FRPM (Ages 5-17)?
- **公开evidence**：Percent (%) Eligible FRPM (Ages 5-17) can be acquired by `FRPM Count (Ages 5-17)` / `Enrollment (Ages 5-17)` * 100
- **已观察差异**：两行均存在，但School Name与School产生Accelerated/The Accelerated差异，REAL中间转换和运算顺序也产生原生浮点差异。
- **归因依据**：输出来源和算术路径各自足以造成失败；模型修复了字段归属错误，却未保证名称来源与公开公式一致。
- **仍待核实**：最终图未提供两种名称和county字段；不能仅增加浮点容差或仅改列别名。运算路径与字段来源需要分别验证。
- **后续方向**：分开验证实体名称来源和原生数值路径，暂不纳入首轮输出顺序主目标。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `california_schools.schools.school` | 未在候选记录出现 | 无候选筛选记录 | 否 |
| `california_schools.frpm.School Name` | 未在候选记录出现 | 无候选筛选记录 | 否 |
| `california_schools.schools.county` | 未在候选记录出现 | 无候选筛选记录 | 否 |
| `california_schools.frpm.County Name` | 0.588116 | beyond_top20 | 否 |
| `california_schools.frpm.FRPM Count (Ages 5-17)` | 0.768159 | selected | 是 |

保存的最终SQL：

```sql
SELECT f."School Name", (f."FRPM Count (Ages 5-17)"::REAL / NULLIF(f."Enrollment (Ages 5-17)", 0)) * 100 AS "Percent (%) Eligible FRPM (Ages 5-17)" FROM public.schools s JOIN public.frpm f ON s.cdscode = f.cdscode WHERE s.gsserved = 'K-9' AND f."County Name" = 'Los Angeles'
```

参考SQL仅供可信审查：

```sql
SELECT T2.School, T1."FRPM Count (Ages 5-17)" * 100 / NULLIF(T1."Enrollment (Ages 5-17)", 0) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.County = 'Los Angeles' AND T2.GSserved = 'K-9'
```

### BIRD-PG-0083 · california_schools

- **主分类**：条件／时间／关系角色解释；状态：`diagnostic_answered`。
- **问题**：Of the schools that offers a magnet program serving a grade span of Kindergarten to 8th grade, how many offers Multiple Provision Types? List the number of cities that offers a Kindergarten to 8th grade span and indicate how many schools are there serving such grade span for each city.
- **公开evidence**：Kindergarten to 8th grade refers to K-8; 'Offers a magnet program' means Magnet = 1; Multiple Provision Types refers to `NSLP Provision Status` = 'Multiple Provision Types'
- **已观察差异**：Multiple Provision Types仅用于条件计数，未限制总体；使用gsserved并输出3列18行，参考使用gsoffered、总体过滤后输出2列1行。
- **归因依据**：相关条件字段、gsoffered与gsserved均已入图。主要是条件作用范围与offered/served角色解释，不是简单漏字段。
- **仍待核实**：多句题面涉及城市数量和各城学校数，参考只输出部分形态；需先明确公开业务契约，不强制照抄参考。
- **后续方向**：记录总体过滤与条件指标的不同角色，先做无模型条件范围诊断。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `california_schools.schools.gsoffered` | 0.551123 | selected | 是 |
| `california_schools.schools.gsserved` | 0.581176 | selected | 是 |
| `california_schools.frpm.NSLP Provision Status` | 0.515617 | selected_intent_coverage | 是 |
| `california_schools.schools.city` | 未在候选记录出现 | 无候选筛选记录 | 是 |

保存的最终SQL：

```sql
WITH k8_magnet_schools AS (
    SELECT s.cdscode, s.city
    FROM schools s
    WHERE s.magnet = 1
      AND s.gsserved = 'K-8'
)
SELECT 
    COUNT(CASE WHEN f."NSLP Provision Status" = 'Multiple Provision Types' THEN 1 END) AS num_multiple_provision_types,
    k.city,
    COUNT(*) AS num_schools_k8_span
FROM k8_magnet_schools k
JOIN frpm f ON k.cdscode = f.cdscode
GROUP BY k.city
```

参考SQL仅供可信审查：

```sql
SELECT T2.City, COUNT(T2.CDSCode) FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.Magnet = 1 AND T2.GSoffered = 'K-8' AND T1."NSLP Provision Status" = 'Multiple Provision Types' GROUP BY T2.City
```

### BIRD-PG-0085 · california_schools

- **主分类**：明确输出项／顺序未落实；状态：`diagnostic_answered`。
- **问题**：What is the Percent (%) Eligible Free (K-12) in the school administered by an administrator whose first name is Alusine. List the district code of the school.
- **公开evidence**：Percent (%) Eligible Free (K-12) = `Free Meal Count (K-12)` / `Enrollment (K-12)` * 100%
- **已观察差异**：只输出District Code一列，漏掉第一句明确要求的免费餐百分数；参考为百分数、District Code两列。
- **归因依据**：分子、分母、姓名条件与District Code均已进入图，遗漏发生在SQL投影阶段。
- **仍待核实**：补回百分数后仍需原生验证算术路径；本次不承诺仅补列即可通过。
- **后续方向**：首轮主目标：把跨句的计算输出及补充标识一起列入输出清单。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `california_schools.frpm.Free Meal Count (K-12)` | 0.701870 | selected | 是 |
| `california_schools.frpm.Enrollment (K-12)` | 0.635072 | selected | 是 |
| `california_schools.frpm.District Code` | 0.600490 | selected | 是 |

保存的最终SQL：

```sql
SELECT f."District Code" FROM frpm f JOIN schools s ON f.cdscode = s.cdscode WHERE s.admfname1 = 'Alusine'
```

参考SQL仅供可信审查：

```sql
SELECT T1."Free Meal Count (K-12)" * 100 / NULLIF(T1."Enrollment (K-12)", 0), T1."District Code" FROM frpm AS T1 INNER JOIN schools AS T2 ON T1.CDSCode = T2.CDSCode WHERE T2.AdmFName1 = 'Alusine'
```

### BIRD-PG-0352 · card_games

- **主分类**：检索／关联上下文缺口；状态：`diagnostic_answered`。
- **问题**：Calculate the percentage of the cards availabe in Chinese Simplified.
- **公开evidence**：Chinese Simplified' is the language; percentage = Divide(Sum(id where language = 'Chinese Simplified'), Count(id)) *100
- **已观察差异**：仅在foreign_data统计语言比例，参考在cards与foreign_data的uuid关联总体上统计；两边都是一个浮点数但不同。
- **归因依据**：两表uuid均未进入最终图，且图无这条关联；存在关联总体覆盖缺口。
- **仍待核实**：不能把缺少声明外键的同名uuid直接视为可靠关联；需授权唯一性、类型、取值及关联基数证据。
- **后续方向**：单独设计受控关联候选验证，避免全局按同名字段猜JOIN。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `card_games.cards.uuid` | 未在候选记录出现 | 无候选筛选记录 | 否 |
| `card_games.foreign_data.uuid` | 未在候选记录出现 | 无候选筛选记录 | 否 |
| `card_games.foreign_data.language` | 0.743437 | selected | 是 |

保存的最终SQL：

```sql
SELECT CAST(SUM(CASE WHEN fd.language = 'Chinese Simplified' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(*), 0) AS percentage FROM foreign_data fd
```

参考SQL仅供可信审查：

```sql
SELECT CAST(SUM(CASE WHEN T2.language = 'Chinese Simplified' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(T1.id), 0) FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid
```

### BIRD-PG-0371 · card_games

- **主分类**：检索／关联上下文缺口；状态：`diagnostic_answered`。
- **问题**：What is the percentage of cards whose language is French among the Story Spotlight cards?
- **公开evidence**：Story Spotlight card refers to isStorySpotlight = 1; French is the language; Percentage = Divide(Count(id) where language = 'French' and isStorySpotlight = 1, Count(id) where isStorySpotlight = 1)*100
- **已观察差异**：选择set_translations.language并以cards.id=set_translations.id连接；修复不存在的card_id后可执行，结果NULL，参考10%。
- **归因依据**：卡牌语言foreign_data.language及uuid路径均未进入图；局部字段修复没有恢复正确关系语义。
- **仍待核实**：正确关联需授权证据，不通过向模型提供Gold的表名来补齐。
- **后续方向**：按卡牌／卡组语言实体区分检索候选，再审查合法关系路径。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `card_games.foreign_data.language` | 0.498680 | below_coverage_floor | 否 |
| `card_games.foreign_data.uuid` | 未在候选记录出现 | 无候选筛选记录 | 否 |
| `card_games.cards.uuid` | 未在候选记录出现 | 无候选筛选记录 | 否 |
| `card_games.set_translations.language` | 0.655410 | selected | 是 |

保存的最终SQL：

```sql
SELECT CAST(SUM(CASE WHEN st.language = 'French' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(*), 0) AS percentage FROM cards c JOIN set_translations st ON c.id = st.id WHERE c.isstoryspotlight = 1
```

参考SQL仅供可信审查：

```sql
SELECT CAST(SUM(CASE WHEN T2.language = 'French' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(T1.id), 0) FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid WHERE T1.isStorySpotlight = 1
```

### BIRD-PG-0407 · card_games

- **主分类**：明确输出项／顺序未落实；状态：`diagnostic_answered`。
- **问题**：Lists all types of cards in German.
- **公开evidence**：German refer to language; all types refer to the subtypes, supertypes; subtypes is not null AND supertypes is not null
- **已观察差异**：输出foreign_data.type一列，遗漏evidence明确展开的subtypes、supertypes及两者非NULL条件；参考两列。
- **归因依据**：subtypes、supertypes和language均已入图，模型没有落实公开字段组；无需先扩大候选数量。
- **仍待核实**：首次实验只改输出契约，非NULL条件作为伴随观察，不能通过隐藏添加参考WHERE条件补分。
- **后续方向**：首轮主目标：依据公开定义展开有序字段组，报告条件覆盖。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `card_games.cards.subtypes` | 0.701652 | selected | 是 |
| `card_games.cards.supertypes` | 0.741283 | selected | 是 |
| `card_games.foreign_data.language` | 0.616153 | selected | 是 |

保存的最终SQL：

```sql
SELECT DISTINCT "type" FROM foreign_data WHERE language = 'German'
```

参考SQL仅供可信审查：

```sql
SELECT T1.subtypes, T1.supertypes FROM cards AS T1 INNER JOIN foreign_data AS T2 ON T1.uuid = T2.uuid WHERE T2.language = 'German' AND NOT T1.subtypes IS NULL AND NOT T1.supertypes IS NULL
```

### BIRD-PG-0415 · card_games

- **主分类**：规范字面值绑定；状态：`diagnostic_answered`。
- **问题**：What percentage of cards with format commander and legal status do not have a content warning?
- **公开evidence**：do not have a content warning refers to hasContentWarning = 0; percentage refers to DIVIDE(COUNT(hasContentWarning = 0),COUNT(ID))*100 where format = 'commander' AND Status = 'legal';
- **已观察差异**：最终JOIN键已修复，仍按公开evidence的status='legal'筛选，返回NULL；参考使用'Legal'返回100%。规范值探测次数为0。
- **归因依据**：已确认大小写字面值差异；当前规范值绑定没有覆盖该条件。
- **仍待核实**：公开evidence与参考字面值存在大小写冲突，不能直接把Gold的Legal注入模型。需授权原生取值查找确认唯一拼写。
- **后续方向**：后续规范值查找实验候选，保留本次原生失败。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `card_games.legalities.status` | 0.572416 | selected | 是 |
| `card_games.legalities.format` | 0.584743 | selected | 是 |
| `card_games.cards.uuid` | 未在候选记录出现 | 无候选筛选记录 | 否 |
| `card_games.legalities.uuid` | 0.575904 | selected | 是 |

保存的最终SQL：

```sql
SELECT CAST(SUM(CASE WHEN c.hascontentwarning = 0 THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(*), 0) AS percentage FROM cards c JOIN legalities l ON c.uuid = l.uuid WHERE l.format = 'commander' AND l.status = 'legal'
```

参考SQL仅供可信审查：

```sql
SELECT CAST(SUM(CASE WHEN T1.hasContentWarning = 0 THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(T1.id), 0) FROM cards AS T1 INNER JOIN legalities AS T2 ON T1.uuid = T2.uuid WHERE T2.format = 'commander' AND T2.status = 'Legal'
```

### BIRD-PG-0473 · card_games

- **主分类**：参考形态／公开口径待澄清；状态：`diagnostic_answered`。
- **问题**：Is the set of cards with Adarkar Valkyrie only available outside the United States?
- **公开evidence**：card set Adarkar Valkyrie refers to name = 'Adarkar Valkyrie'; isForeignOnly = 1 means only available outside the United States;
- **已观察差异**：预测一行No；参考5行均NO，原生集合比较主要体现文本大小写差异，重复行本身被忽略。
- **归因依据**：题面没有规定YES/NO大小写；MAX聚合与逐条判断也不是普遍等价。
- **仍待核实**：本次不能归因于缺字段，也不能制定所有布尔文本都大写的Gold特例。
- **后续方向**：先建立并披露公开布尔输出约定；另验证多行真假混合时的语义。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `card_games.sets.isforeignonly` | 0.873269 | selected | 是 |
| `card_games.cards.name` | 0.570520 | selected | 是 |

保存的最终SQL：

```sql
SELECT CASE WHEN MAX(s.isforeignonly) = 1 THEN 'Yes' ELSE 'No' END AS is_foreign_only FROM cards c JOIN sets s ON c.setcode = s.code WHERE c.name = 'Adarkar Valkyrie'
```

参考SQL仅供可信审查：

```sql
SELECT CASE WHEN isForeignOnly = 1 THEN 'YES' ELSE 'NO' END FROM cards AS T1 INNER JOIN sets AS T2 ON T2.code = T1.setCode WHERE T1.name = 'Adarkar Valkyrie'
```

### BIRD-PG-0595 · codebase_community

- **主分类**：参考形态／公开口径待澄清；状态：`diagnostic_answered`。
- **问题**：Which user have only one post history per post and having at least 1000 views?
- **公开evidence**：having at least 1000 view refers to Views > = 1000; user refers to UserId
- **已观察差异**：预测按用户和帖子分组COUNT(*)=1，271行；参考按用户COUNT(DISTINCT PostHistoryTypeId)=1，94行。
- **归因依据**：关键字段均在图中，但post history per post与全用户唯一历史类型不是同一个统计定义。
- **仍待核实**：原题不足以唯一支持参考的历史类型去重口径；差异确认，业务正确性待澄清。
- **后续方向**：作为粒度约束反例，禁止仅凭Gold反推DISTINCT。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `codebase_community.posthistory.userid` | 0.719442 | selected | 是 |
| `codebase_community.posthistory.postid` | 0.678147 | selected | 是 |
| `codebase_community.posthistory.posthistorytypeid` | 0.603549 | selected | 是 |

保存的最终SQL：

```sql
SELECT DISTINCT ph.userid
FROM posthistory ph
JOIN posts p ON ph.postid = p.id
WHERE p.viewcount >= 1000
GROUP BY ph.userid, ph.postid
HAVING COUNT(*) = 1
```

参考SQL仅供可信审查：

```sql
SELECT T2.UserId FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN posts AS T3 ON T2.PostId = T3.Id WHERE T3.ViewCount >= 1000 GROUP BY T2.UserId HAVING COUNT(DISTINCT T2.PostHistoryTypeId) = 1
```

### BIRD-PG-0604 · codebase_community

- **主分类**：检索／关联上下文缺口；状态：`diagnostic_answered`。
- **问题**：What is the average of the up votes and the average user age for users creating more than 10 posts?
- **公开evidence**：creating more than 10 post refers to Count (UserId) > 10; average of the up votes = Divide (Sum(UpVotes), Count (UserId)); average age = Divide (Sum(Age), Count(UserId))
- **已观察差异**：按votes.userid计数>10选用户，而参考按posts.owneruserid统计发帖；两项平均值均不同。
- **归因依据**：posts.owneruserid已在候选，分数0.509714，但因表未锚定被过滤；最终图仅users/votes。
- **仍待核实**：候选覆盖与动作角色解释都可能影响生成，尚无单变量反事实验证。
- **后续方向**：检索分支优先验证creating posts的动作实体覆盖，保持投票和发帖角色分离。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `codebase_community.posts.owneruserid` | 0.509714 | coverage_table_not_anchored | 否 |
| `codebase_community.votes.userid` | 0.487999 | selected_intent_coverage | 是 |
| `codebase_community.users.upvotes` | 0.585040 | selected | 是 |
| `codebase_community.users.age` | 0.576277 | selected | 是 |

保存的最终SQL：

```sql
SELECT AVG(u.upvotes) AS average_upvotes, AVG(u.age) AS average_age FROM users u WHERE u.id IN (SELECT v.userid FROM votes v GROUP BY v.userid HAVING COUNT(v.userid) > 10)
```

参考SQL仅供可信审查：

```sql
SELECT AVG(T1.UpVotes), AVG(T1.Age) FROM users AS T1 INNER JOIN (SELECT OwnerUserId, COUNT(*) AS post_count FROM posts GROUP BY OwnerUserId HAVING COUNT(*) > 10) AS T2 ON T1.Id = T2.OwnerUserId
```

### BIRD-PG-0639 · codebase_community

- **主分类**：来源拒绝后的重复失败；状态：`repeated_sql`。
- **问题**：Based on posts posted by Community, calculate the percentage of posts that use the R language.
- **公开evidence**：DIVIDE(COUNT(PostId WHERE TagName = 'r')), (COUNT(PostId WHERE DisplayName = 'Community')) as percentage; R language refers to tagname = 'r'
- **已观察差异**：两次生成完全相同SQL，引用posttags并在tags使用id；来源拒绝后重复阻断，未执行预测SQL。
- **归因依据**：tags表已在授权图中，不能说tags整体未授权；核心是虚构posttags关系及无效字段，来源拒绝和重复终止按设计生效。
- **仍待核实**：公开posts/tag问题与参考posthistory/ExcerptPostId路径是否同义仍需说明；缺口不能靠放开权限解决。
- **后续方向**：修复分支检查来源拒绝后的可用关系反馈，不增加重试预算。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `codebase_community.tags.tagname` | 0.507786 | selected_intent_coverage | 是 |
| `codebase_community.tags.excerptpostid` | 0.512800 | selected_coverage | 是 |
| `codebase_community.posts.id` | 0.555453 | selected | 是 |
| `codebase_community.posthistory.postid` | 0.532845 | coverage_table_not_anchored | 否 |

保存的最终SQL：

```sql
-- 未生成最终可执行SQL；见JSON中的尝试与澄清记录。
```

参考SQL仅供可信审查：

```sql
SELECT CAST(SUM(CASE WHEN T3.TagName = 'r' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(T1.Id), 0) FROM users AS T1 INNER JOIN postHistory AS T2 ON T1.Id = T2.UserId INNER JOIN tags AS T3 ON T3.ExcerptPostId = T2.PostId WHERE T1.DisplayName = 'Community'
```

### BIRD-PG-1479 · debit_card_specializing

- **主分类**：检索／关联上下文缺口；状态：`diagnostic_answered`。
- **问题**：Which year recorded the most consumption of gas paid in CZK?
- **公开evidence**：The first 4 strings of the Date values in the yearmonth table can represent year.
- **已观察差异**：未筛选CZK且额外输出total_consumption；预测(year,total)，参考仅year。当前year都为2013不证明总体正确。
- **归因依据**：customers.currency候选分数0.503396但表未锚定，最终图只有yearmonth；另有明确输出形态差异。
- **仍待核实**：去掉额外输出可能使本次EX通过，但仍不得将缺失CZK条件的SQL判为业务修复成功。
- **后续方向**：首轮混合观察题，分别检查输出及缺失筛选，后续检索补币种角色。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `debit_card_specializing.customers.currency` | 0.503396 | coverage_table_not_anchored | 否 |
| `debit_card_specializing.yearmonth.date` | 0.563490 | selected | 是 |
| `debit_card_specializing.yearmonth.consumption` | 0.669462 | selected | 是 |

保存的最终SQL：

```sql
SELECT SUBSTRING(date FROM 1 FOR 4) AS year, SUM(consumption) AS total_consumption FROM yearmonth GROUP BY SUBSTRING(date FROM 1 FOR 4) ORDER BY total_consumption DESC NULLS LAST LIMIT 1
```

参考SQL仅供可信审查：

```sql
SELECT SUBSTR(T2.Date, 1, 4) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' GROUP BY SUBSTR(T2.Date, 1, 4) ORDER BY SUM(T2.Consumption) DESC NULLS LAST LIMIT 1
```

### BIRD-PG-1480 · debit_card_specializing

- **主分类**：检索／关联上下文缺口；状态：`diagnostic_answered`。
- **问题**：What was the gas consumption peak month for SME customers in 2013?
- **公开evidence**：Year 2013 can be presented as Between 201301 And 201312; The first 4 strings of the Date values in the yearmonth table can represent year; The 5th and 6th string of the date can refer to month.
- **已观察差异**：缺少SME条件，另加消费>0客户子查询；预测月份10，参考04。
- **归因依据**：customers.segment已在候选，分数0.548829但因表未锚定被过滤，最终图无customers。
- **仍待核实**：补字段后能否正确使用总体尚未验证；不能以额外查询改写题目总体。
- **后续方向**：检索分支验证公开客户群体字段跨表覆盖。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `debit_card_specializing.customers.segment` | 0.548829 | coverage_table_not_anchored | 否 |
| `debit_card_specializing.customers.customerid` | 0.430666 | below_coverage_floor | 否 |
| `debit_card_specializing.yearmonth.customerid` | 0.582459 | selected | 是 |

保存的最终SQL：

```sql
SELECT SUBSTRING(date FROM 5 FOR 2) AS month
FROM yearmonth
WHERE customerid IN (SELECT customerid FROM yearmonth WHERE consumption > 0 AND SUBSTRING(date FROM 1 FOR 4) = '2013')
  AND SUBSTRING(date FROM 1 FOR 4) = '2013'
GROUP BY SUBSTRING(date FROM 5 FOR 2)
ORDER BY SUM(consumption) DESC NULLS LAST
LIMIT 1
```

参考SQL仅供可信审查：

```sql
SELECT SUBSTR(T2.Date, 5, 2) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE SUBSTR(T2.Date, 1, 4) = '2013' AND T1.Segment = 'SME' GROUP BY SUBSTR(T2.Date, 5, 2) ORDER BY SUM(T2.Consumption) DESC NULLS LAST LIMIT 1
```

### BIRD-PG-1481 · debit_card_specializing

- **主分类**：参考形态／公开口径待澄清；状态：`diagnostic_answered`。
- **问题**：What is the difference in the annual average consumption of the customers with the least amount of consumption paid in CZK for 2013 between SME and LAM, LAM and KAM, and KAM and SME?
- **公开evidence**：annual average consumption of customer with the lowest consumption in each segment = total consumption per year / the number of customer with lowest consumption in each segment; Difference in annual average = SME's annual average - LAM's annual average; Difference in annual average = LAM's annual average - KAM's annual average; Year 2013 can be presented as Between 201301 And 201312; The first 4 strings of the Date values in the yearmonth table can represent year.
- **已观察差异**：预测先逐客户年度求和，再取各segment最低客户；参考使用yearmonth全表单行MIN(consumption)和共享COUNT分母，三项差值不同。
- **归因依据**：每组年度最低客户与全表最低月消费不是同一定义；同时图没有客户连接键，首次猜测字段失败后修复。
- **仍待核实**：公开题目/evidence与参考最小值范围、分母存在明显解释差异；未做全量反事实验证，不能单标模型SQL错误。
- **后续方向**：先澄清最低值范围与统计单位，另补授权连接键；暂缓硬约束。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `debit_card_specializing.customers.customerid` | 0.416349 | below_coverage_floor | 否 |
| `debit_card_specializing.yearmonth.customerid` | 0.495830 | below_coverage_floor | 否 |
| `debit_card_specializing.customers.segment` | 0.593606 | selected | 是 |
| `debit_card_specializing.yearmonth.consumption` | 0.590841 | selected | 是 |

保存的最终SQL：

```sql
WITH yearly_totals AS (
    SELECT 
        c.segment,
        c.customerid,
        SUM(ym.consumption) AS total_consumption
    FROM customers c
    JOIN yearmonth ym ON c.customerid = ym.customerid
    WHERE c.currency = 'CZK'
      AND ym.date >= '201301' AND ym.date <= '201312'
    GROUP BY c.segment, c.customerid
),
min_consumption_per_segment AS (
    SELECT 
        segment,
        MIN(total_consumption) AS min_total
    FROM yearly_totals
    GROUP BY segment
),
lowest_customers AS (
    SELECT 
        yt.segment,
        yt.total_consumption
    FROM yearly_totals yt
    JOIN min_consumption_per_segment mc 
        ON yt.segment = mc.segment 
        AND yt.total_consumption = mc.min_total
),
segment_averages AS (
    SELECT 
        segment,
        SUM(total_consumption) / COUNT(*) AS annual_avg
    FROM lowest_customers
    GROUP BY segment
)
SELECT 
    MAX(CASE WHEN segment = 'SME' THEN annual_avg END) - MAX(CASE WHEN segment = 'LAM' THEN annual_avg END) AS SME_LAM_diff,
    MAX(CASE WHEN segment = 'LAM' THEN annual_avg END) - MAX(CASE WHEN segment = 'KAM' THEN annual_avg END) AS LAM_KAM_diff,
    MAX(CASE WHEN segment = 'KAM' THEN annual_avg END) - MAX(CASE WHEN segment = 'SME' THEN annual_avg END) AS KAM_SME_diff
FROM segment_averages
WHERE segment IN ('SME', 'LAM', 'KAM')
```

参考SQL仅供可信审查：

```sql
SELECT CAST(SUM(CASE WHEN T1.Segment = 'SME' THEN T2.Consumption ELSE 0 END) AS REAL) / NULLIF(COUNT(T1.CustomerID), 0) - CAST(SUM(CASE WHEN T1.Segment = 'LAM' THEN T2.Consumption ELSE 0 END) AS REAL) / NULLIF(COUNT(T1.CustomerID), 0), CAST(SUM(CASE WHEN T1.Segment = 'LAM' THEN T2.Consumption ELSE 0 END) AS REAL) / NULLIF(COUNT(T1.CustomerID), 0) - CAST(SUM(CASE WHEN T1.Segment = 'KAM' THEN T2.Consumption ELSE 0 END) AS REAL) / NULLIF(COUNT(T1.CustomerID), 0), CAST(SUM(CASE WHEN T1.Segment = 'KAM' THEN T2.Consumption ELSE 0 END) AS REAL) / NULLIF(COUNT(T1.CustomerID), 0) - CAST(SUM(CASE WHEN T1.Segment = 'SME' THEN T2.Consumption ELSE 0 END) AS REAL) / NULLIF(COUNT(T1.CustomerID), 0) FROM customers AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Currency = 'CZK' AND T2.Consumption = (SELECT MIN(Consumption) FROM yearmonth) AND T2.Date::text BETWEEN '201301' AND '201312'
```

### BIRD-PG-1505 · debit_card_specializing

- **主分类**：参考形态／公开口径待澄清；状态：`diagnostic_answered`。
- **问题**：Among the customers who paid in euro, how many of them have a monthly consumption of over 1000?
- **公开evidence**：Pays in euro = Currency = 'EUR'.
- **已观察差异**：预测COUNT(DISTINCT customerid)=391，参考COUNT(*)=2730；EUR和消费阈值均保留。
- **归因依据**：问题说多少客户，参考计客户月记录，存在实体与记录粒度歧义，不能把去重直接视为误修复。
- **仍待核实**：需业务协议明确统计单位；本次两条SQL的计数差异已确认，未改变原分数。
- **后续方向**：作为粒度硬约束不适用反例，避免全局删除或增加DISTINCT。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `debit_card_specializing.customers.customerid` | 0.531503 | coverage_no_intent_match | 否 |
| `debit_card_specializing.yearmonth.customerid` | 0.549418 | selected_coverage | 是 |
| `debit_card_specializing.yearmonth.consumption` | 0.601702 | selected | 是 |

保存的最终SQL：

```sql
SELECT COUNT(DISTINCT c.customerid) FROM customers c JOIN yearmonth y ON c.customerid = y.customerid WHERE c.currency = 'EUR' AND y.consumption > 1000
```

参考SQL仅供可信审查：

```sql
SELECT COUNT(*) FROM yearmonth AS T1 INNER JOIN customers AS T2 ON T1.CustomerID = T2.CustomerID WHERE T2.Currency = 'EUR' AND T1.Consumption > 1000.00
```

### BIRD-PG-1524 · debit_card_specializing

- **主分类**：参考形态／公开口径待澄清；状态：`clarification`。
- **问题**：What's the nationality of the customer who spent 548.4 in 2012/8/24?
- **公开evidence**：'2012/8/24' can be represented by '2012-08-24'; spent 548.4 refers to price = '548.4' 
- **已观察差异**：只有transactions_1k的price/date/customerid，模型澄清缺少客户国籍；Gold实际取gasstations.country并按gasstationid连接。
- **归因依据**：授权上下文缺口确实存在，但客户国籍与加油站所在国是不同实体角色，不能直接建议添加customers.nationality来追赶Gold。
- **仍待核实**：必须先核实官方字段说明与题面角色冲突。gasstations.country候选0.468436、低于覆盖下限，不证明它就是正确的客户国籍来源。
- **后续方向**：单列参考实体角色问题；检索补齐仍需明确公开依据。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `debit_card_specializing.gasstations.country` | 0.468436 | below_coverage_floor | 否 |
| `debit_card_specializing.gasstations.gasstationid` | 0.416054 | below_coverage_floor | 否 |
| `debit_card_specializing.transactions_1k.gasstationid` | 0.450218 | below_coverage_floor | 否 |
| `debit_card_specializing.transactions_1k.customerid` | 0.517395 | selected_coverage | 是 |

保存的最终SQL：

```sql
-- 未生成最终可执行SQL；见JSON中的尝试与澄清记录。
```

参考SQL仅供可信审查：

```sql
SELECT T2.Country FROM transactions_1k AS T1 INNER JOIN gasstations AS T2 ON T1.GasStationID = T2.GasStationID WHERE T1.Date = '2012-08-24' AND T1.Price = '548.4'
```

### BIRD-PG-1533 · debit_card_specializing

- **主分类**：检索／关联上下文缺口；状态：`diagnostic_answered`。
- **问题**：For all the people who paid more than 29.00 per unit of product id No.5. Give their consumption status in the August of 2012.
- **公开evidence**：August of 2012 refers to the Date value = '201208' ; Price per unit of product = Price / Amount;
- **已观察差异**：按年月而非customerid关联，预测17010行、参考10行；首次除零后加amount>0恢复执行但答案仍错。
- **归因依据**：最终图没有customerid关联键和JOIN；修复只消除除零，未修复实体关联，还改变了amount非零的过滤语义。
- **仍待核实**：amount>0与NULLIF(amount,0)非普遍等价，未证明负值是否存在；不能把执行恢复报告为答案修复。
- **后续方向**：补有证据的实体关联，并约束修复保持原条件，不因非空/执行成功改分。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `debit_card_specializing.transactions_1k.customerid` | 0.484359 | below_coverage_floor | 否 |
| `debit_card_specializing.yearmonth.customerid` | 0.503959 | coverage_no_intent_match | 否 |
| `debit_card_specializing.transactions_1k.amount` | 0.503426 | selected_coverage | 是 |

保存的最终SQL：

```sql
SELECT DISTINCT y.consumption FROM transactions_1k t JOIN yearmonth y ON TO_CHAR(t.date, 'YYYYMM') = y.date WHERE t.productid = 5 AND t.amount > 0 AND (t.price / t.amount) > 29.00 AND y.date = '201208'
```

参考SQL仅供可信审查：

```sql
SELECT T2.Consumption FROM transactions_1k AS T1 INNER JOIN yearmonth AS T2 ON T1.CustomerID = T2.CustomerID WHERE T1.Price / NULLIF(T1.Amount, 0) > 29.00 AND T1.ProductID = 5 AND T2.Date = '201208'
```

### BIRD-PG-0115 · financial

- **主分类**：参考形态／公开口径待澄清；状态：`diagnostic_answered`。
- **问题**：For the branch which located in the south Bohemia with biggest number of inhabitants, what is the percentage of the male clients?
- **公开evidence**：Percentage of the male clients = DIVIDE(COUNT(male clients), COUNT(clients)) * 100; Male refers to gender = 'M', A3 is the region name. A4 contains the information about inhabitants.
- **已观察差异**：A4实际类型text；预测CAST(a4 AS INTEGER)后选最大地区，参考GROUP BY A4并按原text排序，两边百分数不同。
- **归因依据**：人口数字排序与文本字典序不同，且参考按人口值分组；字段均已提供，不能认定缺检索。
- **仍待核实**：题目要求最大人口数，预测数值转换可能更符合题义；需全量人口/地区对照确认贡献，不按参考强制文本排序。
- **后续方向**：先做无模型排序与分组诊断，单列参考类型路径问题。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `financial.district.a4` | 0.588407 | selected | 是 |
| `financial.district.district_id` | 0.497950 | below_coverage_floor | 是 |
| `financial.client.gender` | 0.555620 | selected | 是 |

保存的最终SQL：

```sql
SELECT CAST(SUM(CASE WHEN c.gender = 'M' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(*), 0) AS percentage_male_clients FROM client c JOIN district d ON c.district_id = d.district_id WHERE d.a3 = 'south Bohemia' AND d.district_id = (SELECT district_id FROM district WHERE a3 = 'south Bohemia' ORDER BY CAST(a4 AS INTEGER) DESC NULLS LAST LIMIT 1)
```

参考SQL仅供可信审查：

```sql
SELECT CAST(SUM(CASE WHEN T1.gender = 'M' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(T1.client_id), 0) FROM client AS T1 INNER JOIN district AS T2 ON T1.district_id = T2.district_id WHERE T2.A3 = 'south Bohemia' GROUP BY T2.A4 ORDER BY T2.A4 DESC LIMIT 1
```

### BIRD-PG-0145 · financial

- **主分类**：条件／时间／关系角色解释；状态：`diagnostic_answered`。
- **问题**：Who are the account holder identification numbers whose who have transactions on the credit card with the amount is less than the average, in 1998?
- **公开evidence**：Operation = 'VYBER KARTOU' refers to credit card withdrawal
- **已观察差异**：首次对trans.date调用TO_DATE出错，修复改为card.issued年份；最终返回client_id并按卡发行年筛选，参考为account_id及交易年。
- **归因依据**：修复改变了公开1998交易时间锚点，且混淆账户与客户标识；trans.date未进入图是伴随覆盖缺口。
- **仍待核实**：平均金额的总体和account holder措辞另有解释空间；先确认时间与输出角色，不依Gold整体替换SQL。
- **后续方向**：修复约束保留原时间所属事件，提供授权字段类型和角色提示。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `financial.trans.date` | 0.483905 | below_coverage_floor | 否 |
| `financial.card.issued` | 0.520029 | coverage_no_intent_match | 否 |
| `financial.trans.account_id` | 0.577376 | selected | 是 |
| `financial.disp.client_id` | 0.561975 | selected | 是 |

保存的最终SQL：

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
CROSS JOIN avg_amt
WHERE t.operation = 'VYBER KARTOU'
  AND EXTRACT(YEAR FROM c.issued) = 1998
  AND t.amount < avg_amt.val;
```

参考SQL仅供可信审查：

```sql
SELECT T1.account_id FROM trans AS T1 INNER JOIN account AS T2 ON T1.account_id = T2.account_id WHERE TO_CHAR(CAST(T1.date AS TIMESTAMP), 'YYYY') = '1998' AND T1.operation = 'VYBER KARTOU' AND T1.amount < (SELECT AVG(amount) FROM trans WHERE TO_CHAR(CAST(date AS TIMESTAMP), 'YYYY') = '1998')
```

### BIRD-PG-0152 · financial

- **主分类**：检索／关联上下文缺口；状态：`clarification`。
- **问题**：What is the average number of crimes committed in 1995 in regions where the number exceeds 4000 and the region has accounts that are opened starting from the year 1997?
- **公开evidence**：A3 refers to region names; A15 stands for the average number of crimes commited in 1995.
- **已观察差异**：最终图只有district.a15/a3，模型明确缺少account及开户日期后澄清，未生成SQL。
- **归因依据**：account.date候选0.472824、account.district_id候选0.426，未进入最终图；公开开户年条件无法在当前上下文完成。
- **仍待核实**：补齐上下文后的平均犯罪率权重仍需独立结果检查，不把澄清改成盲猜关联。
- **后续方向**：检索分支验证开户动作与日期字段组和声明关联覆盖。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `financial.account.date` | 0.472824 | below_coverage_floor | 否 |
| `financial.account.district_id` | 0.426000 | below_coverage_floor | 否 |
| `financial.district.district_id` | 0.389305 | below_coverage_floor | 否 |

保存的最终SQL：

```sql
-- 未生成最终可执行SQL；见JSON中的尝试与澄清记录。
```

参考SQL仅供可信审查：

```sql
SELECT AVG(T1.A15) FROM district AS T1 INNER JOIN account AS T2 ON T1.district_id = T2.district_id WHERE TO_CHAR(CAST(T2.date AS TIMESTAMP), 'YYYY') >= '1997' AND T1.A15 > 4000
```

### BIRD-PG-0173 · financial

- **主分类**：条件／时间／关系角色解释；状态：`diagnostic_answered`。
- **问题**：How often does account number 3 request an account statement to be released? What was the aim of debiting 3539 in total?
- **公开evidence**：k_symbol refers to the purpose of payments
- **已观察差异**：把3539绑定为order.account_to，返回付款目的NULL；参考按account_id=3、聚合SUM(amount)=3539取得目的。
- **归因依据**：amount、account_id和k_symbol已在图中；数值被错误分配为账号角色，缺少debiting in total的金额总和关系。
- **仍待核实**：总金额分组口径需要公开业务依据，不把参考分组SQL作为模型反馈。
- **后续方向**：根据公开动词和单位区分金额常量与标识常量。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `financial.order.amount` | 0.590865 | selected | 是 |
| `financial.order.account_to` | 0.609943 | selected | 是 |
| `financial.order.account_id` | 0.626368 | selected | 是 |
| `financial.order.k_symbol` | 0.687515 | selected | 是 |

保存的最终SQL：

```sql
WITH q1 AS (
  SELECT a.frequency
  FROM account a
  WHERE a.account_id = 3
),
q2 AS (
  SELECT o.k_symbol
  FROM "order" o
  WHERE o.account_to = 3539
)
SELECT (SELECT frequency FROM q1) AS statement_frequency, (SELECT k_symbol FROM q2 LIMIT 1) AS debit_aim
```

参考SQL仅供可信审查：

```sql
SELECT T1.frequency, T2.k_symbol FROM account AS T1 INNER JOIN (SELECT account_id, k_symbol, SUM(amount) AS total_amount FROM "order" GROUP BY account_id, k_symbol) AS T2 ON T1.account_id = T2.account_id WHERE T1.account_id = 3 AND T2.total_amount = 3539
```

### BIRD-PG-1399 · student_club

- **主分类**：参考形态／公开口径待澄清；状态：`diagnostic_answered`。
- **问题**：Did Maya Mclean attend the 'Women's Soccer' event?
- **公开evidence**：Maya Mclean is the full name; full name refers to first_name, last_name; 'Women's Soccer' is an event_name
- **已观察差异**：预测一行Yes；参考14行去重为YES与NULL两种元组。
- **归因依据**：existential yes/no回答与保留其他事件NULL行的参考形态不同，另有大小写差异。
- **仍待核实**：不能为通过EX而要求所有是否题保留无关NULL行；原生失分保留。
- **后续方向**：独立记录参考输出形态，排除出首轮强制输出规则目标。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `student_club.member.first_name` | 0.475164 | selected_intent_coverage | 是 |
| `student_club.member.last_name` | 0.502266 | selected_intent_coverage | 是 |
| `student_club.event.event_name` | 0.570066 | selected | 是 |

保存的最终SQL：

```sql
SELECT CASE WHEN COUNT(*) > 0 THEN 'Yes' ELSE 'No' END AS attended FROM attendance a JOIN member m ON a.link_to_member = m.member_id JOIN event e ON a.link_to_event = e.event_id WHERE m.first_name = 'Maya' AND m.last_name = 'Mclean' AND e.event_name = 'Women''s Soccer'
```

参考SQL仅供可信审查：

```sql
SELECT CASE WHEN T3.event_name = 'Women''s Soccer' THEN 'YES' END AS result FROM member AS T1 INNER JOIN attendance AS T2 ON T1.member_id = T2.link_to_member INNER JOIN event AS T3 ON T2.link_to_event = T3.event_id WHERE T1.first_name = 'Maya' AND T1.last_name = 'Mclean'
```

### BIRD-PG-1427 · student_club

- **主分类**：参考形态／公开口径待澄清；状态：`diagnostic_answered`。
- **问题**：What are the budget category of the events located at MU 215 and a guest speaker type with a 0 budget spent?
- **公开evidence**：budget category refers to category; events located at refers to location; type = 'Guest Speaker'; 0 budget spent refers to spent = 0; 
- **已观察差异**：所有业务筛选均保留，预测4行category，参考相同类别另加恒定Guest Speaker的type列。
- **归因依据**：问题问预算类别，type是筛选上下文；额外投影是否必须没有明确公开要求。
- **仍待核实**：不可仅因参考有两列就把所有过滤字段强制输出。
- **后续方向**：首轮规则的反例边界：纯筛选上下文不自动成为投影。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `student_club.budget.category` | 0.475546 | selected_intent_coverage | 是 |
| `student_club.event.type` | 0.524412 | selected_intent_coverage | 是 |

保存的最终SQL：

```sql
SELECT DISTINCT b.category FROM budget b JOIN event e ON b.link_to_event = e.event_id WHERE e.location = 'MU 215' AND e.type = 'Guest Speaker' AND b.spent = 0
```

参考SQL仅供可信审查：

```sql
SELECT DISTINCT T2.category, T1.type FROM event AS T1 INNER JOIN budget AS T2 ON T1.event_id = T2.link_to_event WHERE T1.location = 'MU 215' AND T2.spent = 0 AND T1.type = 'Guest Speaker'
```

### BIRD-PG-0726 · superhero

- **主分类**：参考形态／公开口径待澄清；状态：`diagnostic_answered`。
- **问题**：Rank heroes published by Marvel Comics by their height in descending order.
- **公开evidence**：name refers to superhero_name; the tallest hero refers to MAX(height_cm); published by Marvel Comics refers to publisher_name = 'Marvel Comics'
- **已观察差异**：预测英雄名、身高并排序；参考另输出RANK列，387行但列数2对3。
- **归因依据**：Rank可以表示排序，也可要求显式名次列，公开输出约定需说明；字段覆盖不是主要问题。
- **仍待核实**：本次不按Gold自动增加排名列；未来明确排名指令时仍需保留并列语义。
- **后续方向**：先作为排名输出约定待澄清项，使用合成正反例定义适用范围。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `superhero.superhero.superhero_name` | 0.445043 | selected_intent_coverage | 是 |
| `superhero.superhero.height_cm` | 0.686239 | selected | 是 |

保存的最终SQL：

```sql
SELECT s.superhero_name, s.height_cm FROM superhero s JOIN publisher p ON s.publisher_id = p.id WHERE p.publisher_name = 'Marvel Comics' ORDER BY s.height_cm DESC NULLS LAST
```

参考SQL仅供可信审查：

```sql
SELECT superhero_name, height_cm, RANK() OVER (ORDER BY height_cm DESC NULLS LAST) AS HeightRank FROM superhero INNER JOIN publisher ON superhero.publisher_id = publisher.id WHERE publisher.publisher_name = 'Marvel Comics'
```

### BIRD-PG-0201 · toxicology

- **主分类**：参考形态／公开口径待澄清；状态：`diagnostic_answered`。
- **问题**：What is the percentage of carbon in double-bond molecules?
- **公开evidence**：carbon refers to element = 'c'; double-bond molecules refers to bond_type = '='; percentage = DIVIDE(SUM(element = 'c'), COUNT(atom_id))
- **已观察差异**：按原关联行统计得到41.196235238637925，参考去重atom_id得到38.80961092816197。
- **归因依据**：关联重复权重与唯一原子比例不同；公开evidence写COUNT(atom_id)，未明确DISTINCT。
- **仍待核实**：不能仅凭一对多关联要求去重，0263是保留原行权重的成功反例。
- **后续方向**：先明确公开粒度约定，保持v4的歧义提示，不重新全局强制去重。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `toxicology.atom.atom_id` | 0.379095 | selected_intent_coverage | 是 |
| `toxicology.atom.element` | 0.421087 | selected_intent_coverage | 是 |
| `toxicology.atom.molecule_id` | 0.458934 | below_coverage_floor | 是 |
| `toxicology.bond.molecule_id` | 0.437729 | below_coverage_floor | 是 |

保存的最终SQL：

```sql
SELECT CAST(SUM(CASE WHEN a.element = 'c' THEN 1 ELSE 0 END) AS REAL) * 100 / NULLIF(COUNT(a.atom_id), 0) AS percentage FROM atom a JOIN bond b ON a.molecule_id = b.molecule_id WHERE b.bond_type = '='
```

参考SQL仅供可信审查：

```sql
SELECT CAST(COUNT(DISTINCT CASE WHEN T1.element = 'c' THEN T1.atom_id ELSE NULL END) AS REAL) * 100 / NULLIF(COUNT(DISTINCT T1.atom_id), 0) FROM atom AS T1 INNER JOIN bond AS T2 ON T1.molecule_id = T2.molecule_id WHERE T2.bond_type = '='
```

### BIRD-PG-0239 · toxicology

- **主分类**：条件／时间／关系角色解释；状态：`diagnostic_answered`。
- **问题**：How many connections does the atom 19 have?
- **公开evidence**：connections refers to bond_id; atom 19 refers to atom_id like 'TR%_19';
- **已观察差异**：公开指定atom_id模式，预测额外OR atom_id2，COUNT=754；参考单侧端点COUNT=377。
- **归因依据**：模型扩展了公开字段限定的关系端点，双侧统计并非请求中明确授权的角色范围。
- **仍待核实**：参考RIGHT与公开LIKE的模式差异尚未单独量化；不能把所有连接一律单向化，0206需要两侧端点。
- **后续方向**：关系角色改进时保留公开指定端点，并加入双向查询正例。

| 相关授权字段 | 候选分数 | 筛选记录 | 最终图包含 |
| --- | ---: | --- | --- |
| `toxicology.connected.atom_id` | 0.512554 | selected_coverage | 是 |
| `toxicology.connected.atom_id2` | 0.430387 | below_coverage_floor | 是 |
| `toxicology.connected.bond_id` | 0.582665 | selected | 是 |

保存的最终SQL：

```sql
SELECT COUNT(*) FROM connected WHERE atom_id LIKE 'TR%_19' OR atom_id2 LIKE 'TR%_19'
```

参考SQL仅供可信审查：

```sql
SELECT COUNT(T.bond_id) FROM connected AS T WHERE RIGHT(T.atom_id, 2) = '19'
```

## 4. 成功回归集：从50题中选择20题

以下均在v4原生通过；属于开发回归，不是新保留集。未选的30个成功题仍保留在JSON的完整成功清单，后续development80全部参与。

| 题号 | 数据库域 | 主要保护点 |
| --- | --- | --- |
| BIRD-PG-0036 | california_schools | 多组完整姓名与NULL排序，已发生输出组修复 |
| BIRD-PG-0082 | california_schools | 仅请求单字段，ABS排序表达式不变成额外投影 |
| BIRD-PG-0368 | card_games | 百分数原生数值路径，不因输出清单改变算术 |
| BIRD-PG-0379 | card_games | 显式只列ID，不能附加名称 |
| BIRD-PG-0480 | card_games | 卡牌名与语言只是筛选，最终只输出flavor text |
| BIRD-PG-0586 | codebase_community | 已有参与者／标题输出组及角色关联 |
| BIRD-PG-0637 | codebase_community | 用户名称和零评论条件，不附加上下文字段 |
| BIRD-PG-1473 | debit_card_specializing | 跨表客户群与月份条件，既有计算不变 |
| BIRD-PG-1486 | debit_card_specializing | 公开差值标量，禁止额外Yes/No或两个计数 |
| BIRD-PG-0095 | financial | 复合排序及ID投影，修复预算保持 |
| BIRD-PG-0159 | financial | 实体列表ID输出与条件覆盖 |
| BIRD-PG-1405 | student_club | 类别＋计算金额的输出顺序和名称到ID关联 |
| BIRD-PG-1457 | student_club | 完整姓名＋明确要求的联系电话 |
| BIRD-PG-1460 | student_club | 完整姓名＋明确要求的成本字段组 |
| BIRD-PG-0766 | superhero | full_name不能替换为superhero_name或额外输出属性值 |
| BIRD-PG-0773 | superhero | 英雄名和发布者两项公开输出 |
| BIRD-PG-0206 | toxicology | 明确双端点关系语义，不能全局禁止OR或UNION |
| BIRD-PG-0226 | toxicology | 五位小数及NUMERIC函数修复，原生结果不后处理 |
| BIRD-PG-0263 | toxicology | 一对多行权重的成功反例，禁止全局去重 |
| BIRD-PG-0273 | toxicology | 冲突evidence不强制合取，保留既定条件角色 |

## 5. 已观察保留集补充（不进入首轮生成）

| 题号 | 分类 | 审查结论 |
| --- | --- | --- |
| BIRD-PG-1039 | numeric_path | Decimal AVG与REAL SUM/COUNT原生路径不同，空值分母也非普遍等价。 |
| BIRD-PG-0897 | output_and_aggregation | 姓名合并导致列数不同，另有SUM wins与COUNT wins条件口径差异。 |
| BIRD-PG-0928 | relation_role_and_reference_shape | standings.position与results.rank角色不同，参考额外姓名列单列。 |
| BIRD-PG-0962 | numerator_denominator_grain | 分子比赛行与分母唯一车手混用。 |
| BIRD-PG-0964 | evidence_reference_conflict | 公开America与参考American冲突，不能提供Gold字面值。 |
| BIRD-PG-1153 | entity_table_role | examination.diagnosis与patient.diagnosis来源不同。 |
| BIRD-PG-1205 | native_output_type | Yes/No字符串与原生布尔不同，不回溯转型。 |
| BIRD-PG-1227 | public_age_formula | 公开年份差与AGE完整周岁不同。 |
| BIRD-PG-1242 | evidence_reference_conflict | 公开当前年与参考1984检验日期年冲突。 |
| BIRD-PG-1267 | enum_storage_mapping | 显示符号到存储值映射缺失，涉及IN列表。 |
| BIRD-PG-1275 | enum_storage_mapping | 多字段IN列表映射缺失，原DISTINCT已保留。 |

## 6. 首轮选择与下一步

**选择SQL生成语义分支：公开输出需求的有序覆盖。** 主目标0050、0085、0407；1479是混合观察题；加20个成功回归题，共24题。

三道主目标的相关字段已进入最终Schema，公开请求可支持检查输出顺序、遗漏计算项或字段组；因此首轮无需同时改检索、关联或模型。1479还缺币种上下文，不能因去掉多余列碰巧通过就宣称业务修复。

检索是下一优先候选：9题归入上下文覆盖主类，0604/1479/1480可定位到表未锚定过滤，0152有明确开户日期缺口；但关联缺声明、实体角色和参考歧义需分开处理。

不在首轮追求全部30题通过，也不放宽EX、添加题号特例或重跑正式holdout30。范围、预算、通过与停止条件见[M3首轮实验计划](M3_A_FIRST_EXPERIMENT_PLAN_20261021.md)。

## 7. 审计

- 独立核对冻结交付143个文件，摘要均保持不变。
- 原始报告和协议文件前后SHA-256一致；新运行时必须使用新候选身份，不能修改M2冻结摘要来绕过版本检查。
- 逐题完整证据、50题成功登记、11题补充材料、代码/来源身份和检查项见[机器报告](results/m3_a_failure_attribution_local_20261021.json)。
