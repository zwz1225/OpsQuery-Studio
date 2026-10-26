# M3 E03：process DNS r2 服务器24题同轮审查

日期：2026-10-24。范围：本地读取七份服务器原始JSON与交付包、公开题目/evidence和冻结参考SQL；没有连接数据库、调用模型、生成SQL或修改评分。

## 1. 结论

- 执行完整性和已记录来源/预算证据通过核对：880项记录一致性检查全部通过。两侧均完成24题捕获和24题独立原生复评，未排除任何题目。
- 公共连接层完成一次有效的真实配对运行：251次已记录模型尝试全部HTTP200，传输重试均为0，包含embedding、rerank和chat。此结论只覆盖本次运行。
- **E03候选未达到预登记筛选条件，不接纳推广。** 两侧均22/24，净增0；20道回归和1479保持，但0407仍未通过，目标Schema字段/连接没有改变。完整输入并非完全相同：候选输出提示、关系策略和图版本已改变。
- 保存本轮作为未达门槛的开发实验。不因通过原生评分而跳过语义审查，不调整Gold、原生集合语义、别名、容差、生成次数或题单。

## 2. 七份文件与身份

本地原始根目录：`E:/PythonLearn/m3_e03_pair24_process_dns_v1_20261023_r2/`。原始文件保持不变。

| 文件 | SHA-256 |
| --- | --- |
| reports/e03_pair24_server.json | `fd5977878e7009d5d5d0e1f4dbd9722e0b5da9041e251ae9295007d25b9c6f54` |
| reports/e03_pair24_comparison_server.json | `864223cad8e71e07049cd3cb1fd344f815cdac563117720de7eb0ce9565ab102` |
| baseline/backend/evaluation/results/m3_e03_baseline24_capture_server.json | `61b970c9e457b84088c12f581c533c87da3dea88a50a239d2030b27c12a4f81f` |
| baseline/backend/evaluation/results/m3_e03_baseline24_native_server.json | `5e153c6558fe44372c8b0a0854863469f4651121ceab471a783c5753a55430b1` |
| candidate/backend/evaluation/results/m3_e03_candidate24_capture_server.json | `dc5ddd924f3771c3d767a9c02217e5b09334d6b5d9d13b80b1d28608680093fc` |
| candidate/backend/evaluation/results/m3_e03_candidate24_native_server.json | `cb1c19c345529702ad4bea1a60982fd58f406d9efb1fafbe885e364506ffbb35` |
| transport_dependency_lock.json | `b4c7099e4c606365becf85f838fb147a975c8f140c4713afee7c95cc2435be46` |

包身份为 `483c6a685bd96a5b5e495012ff37fc879011d4216b5fd40bb0abed2895759a2c`，与交付清单和控制器一致。四份子报告字节摘要、对照报告摘要、两份复评引用的源捕获摘要全部匹配；12个子阶段退出码均为0。对照报告全部计算字段已用本地保存的捕获/复评重新汇总核对。

两侧生产文件分别99/100，与冻结包逐项一致。运行环境均为Python 3.11.15、Linux x86_64、kernel 6.8.0-59-generic；Psycopg 3.2.13、pool 3.2.8、SQLGlot 30.17.0、seccomp 2.5.3一致。

工具锁为 `/usr/bin/dig`、版本 `9.18.39-0ubuntu0.22.04.7-Ubuntu`，二进制SHA-256为 `421932872b073d8749d56c567319945b7f7bdfd42e705f1e6e2e2f461511c177`，解析器为 `114.114.114.114`。锁与总控、两侧捕获、索引身份、251份模型事件均一致。每个事件均记录有效DNS结果、来自应答的连接地址、原域名TLS校验和HTTP200。

## 3. 来源、索引、隔离及评分

两侧使用相同24题顺序、公开模型配置、来源/协议/权限/数据版本与原预算。每侧独立构建8域索引，缓存命中0；索引路径分离，记录的模块摘要与对应生产快照一致，每题引用的索引摘要与本侧构建记录一致。

8域的实时来源收据均标记已验证；48个题目记录的来源、角色、catalog/data版本和授权图来源一致。真实隔离探针、1秒硬超时探针和7项预算探针均通过；隔离Agent没有项目读取、环境凭据或直接数据库访问权限。48份授权图诊断完整、摘要匹配，字段数均不超过20。

两份捕获全部完成后才执行Gold复评。两侧各24/24复评、排除0；每题保存的生成SQL摘要、实际复评SQL、冻结Gold SQL摘要、完整结果诊断和捕获结果诊断一致；复评各执行48次SQL、新模型调用0、连接池均关闭。原生匹配按固定元组集合语义，未增加容差、值转换或列名规则。

这是开发集24题对照，`formal_benchmark=false`、`holdout_run=false`，不能写成官方成绩或新的保留集成绩。

## 4. 逐题结果

| Case | 用途 | 基线 | 候选 |
| --- | --- | --- | --- |
| BIRD-PG-0036 | 回归 | 通过 | 通过 |
| BIRD-PG-0050 | 目标/观察 | 通过 | 通过 |
| BIRD-PG-0082 | 回归 | 通过 | 通过 |
| BIRD-PG-0085 | 目标/观察 | 未通过 | 未通过 |
| BIRD-PG-0368 | 回归 | 通过 | 通过 |
| BIRD-PG-0379 | 回归 | 通过 | 通过 |
| BIRD-PG-0407 | 目标/观察 | 未通过 | 未通过 |
| BIRD-PG-0480 | 回归 | 通过 | 通过 |
| BIRD-PG-0586 | 回归 | 通过 | 通过 |
| BIRD-PG-0637 | 回归 | 通过 | 通过 |
| BIRD-PG-1473 | 回归 | 通过 | 通过 |
| BIRD-PG-1479 | 目标/观察 | 通过 | 通过 |
| BIRD-PG-1486 | 回归 | 通过 | 通过 |
| BIRD-PG-0095 | 回归 | 通过 | 通过 |
| BIRD-PG-0159 | 回归 | 通过 | 通过 |
| BIRD-PG-1405 | 回归 | 通过 | 通过 |
| BIRD-PG-1457 | 回归 | 通过 | 通过 |
| BIRD-PG-1460 | 回归 | 通过 | 通过 |
| BIRD-PG-0766 | 回归 | 通过 | 通过 |
| BIRD-PG-0773 | 回归 | 通过 | 通过 |
| BIRD-PG-0206 | 回归 | 通过 | 通过 |
| BIRD-PG-0226 | 回归 | 通过 | 通过 |
| BIRD-PG-0263 | 回归 | 通过 | 通过 |
| BIRD-PG-0273 | 回归 | 通过 | 通过 |

两侧唯一失败题均为0085、0407。0050本轮两侧均通过，且SQL相同；相对旧E02报告的变化不能归因于E03候选。

## 5. 0407：输出提示存在，关系补齐未被接纳

公开问题为 `Lists all types of cards in German.`；evidence明确 `all types` 指 `subtypes, supertypes`，两列均非空。

两侧实际SQL完全相同：

```sql
SELECT DISTINCT fd.type
FROM foreign_data fd
WHERE fd.language = 'German' AND fd.type IS NOT NULL
```

它正确出现了German筛选，但输出的是`foreign_data.type`一列，没有`cards.subtypes`和`cards.supertypes`、没有这两列各自非空要求、没有UUID关联。完整预测为2150行1列；冻结参考为1693行2列、408个不同元组。原生不匹配有效，不能用DISTINCT或预览行数改变该结论。

候选开关和输出契约真实存在：`public_output_contract_complete=true`，字段组精确绑定`cards.subtypes/cards.supertypes`，观察器报告`requested_output_not_observed`。因此不能解释为输出提示模块完全没运行。

关联补齐有明确拒绝轨迹：

1. 已选20字段包含`foreign_data.language`和`set_translations.language`。
2. `sample_hint_decisions=[]`，没有被接受的唯一样本条件；公开`German refer to language`按当前同名字段绑定得到两个所有者。离线复现该条件绑定分支，没有查询数据库或参考答案选字段。
3. `public_output_relation`决策为`selected=false`、`unresolved_output_group_or_filter`，新增字段/关联均为空。公开输出定义`all types -> subtypes`按原代码排除为输出组，不作为筛选条件。
4. 已审查的cards/foreign_data关系来源绑定有效，`limited_eligible=true`，仍保留16条孤儿记录警示；它并未在本轮转成已接纳关系。
5. 两端`cards.uuid/foreign_data.uuid`仍缺失，`graph.joins=[]`。所以本轮没有给模型完整的候选关联上下文。

另有诊断缺口：虽然补齐被拒，`unresolved_required_roles=[]`仍为空，拒绝细节只在开发诊断中出现，没有通过该列表传给模型。后续若继续研究，应先离线修正归属依据和未解析原因传递，不能直接宣称“完整关系提示给出后模型仍不遵守”，也不能因为Gold使用该关联而强制选择字段或JOIN。

## 6. 1479、0085与其他修复轨迹

### 1479：语义复核通过

两侧均关联`yearmonth.customerid/customers.customerid`，筛选`currency='CZK'`，提取年份、按`SUM(consumption)`降序且`NULLS LAST`、`LIMIT 1`，只输出年份。基线用`SUBSTRING`，候选用`LEFT`；两侧完整结果均为`2013`，原生通过，公开币种、度量、年度粒度和输出形态均保持。

### 0085：单位及显式公式未落实

两侧均直接投影`frpm."Percent (%) Eligible Free (K-12)"`及地区代码；地区代码为64857。该次实际数值为`0.7015113`，参考明确公式`Free Meal Count * 100 / Enrollment`得到`70.15113350125945`。

这不是列名问题。直接将已存近似值乘100只能得到`70.15113`，仍与公开公式的原生结果不同。按当前协议不得添加容差或对返回结果做变换。若将来修复，应依据公开公式及实际字段类型，不依据参考值调系数或舍入。

### 中间校验失败与最终成功分别记录

基线3次校验拒绝：0586（输出组）、1473（42703字段）、0095（输出组）。候选6次校验拒绝：0036/0586（输出组）、1473（42703）、0095（42P10及输出组）、0226（42883，`ROUND(double precision, integer)`）。均在原有预算内修复，最终实际SQL执行失败数两侧均为0。不能把顶层`errors=[]`解释为没有任何中间校验问题。

## 7. 成本与预算

| 指标 | 基线 | 候选 | 增幅 |
| --- | ---: | ---: | ---: |
| 含索引模型HTTP尝试 | 124 | 127 | 2.42% |
| 其中建索引 | 49 | 49 | 0 |
| 其中题内 | 75 | 78 | 4.00% |
| 含索引Token | 324827 | 357827 | 10.16% |
| 其中chat Token | 154968 | 187968 | 21.29% |
| 逐题p95（秒） | 18.654 | 21.630 | 15.95% |

索引Token两侧均45217，题内embedding均1189、rerank均123453，新增33000 Token全部发生在chat阶段；chat次数27到30，伴随更多中间修复。这里是观察结果，不据单轮对照证明因果或统计显著。

预登记E03的成本门槛使用含索引总Token、总HTTP及逐题p95，上述三项均在120%以内，因此成本筛选通过；chat分项增幅另报，不隐去。每题最多HTTP基线4/候选5、SQL两侧最多2，均未超原16/10chat/3SQL及600秒上限。

## 8. 处置与下一步建议

1. 接受本次运行完整性和连接层的已观察可用性记录；E03候选效果不接纳。
2. 原始七份文件、失败/修复轨迹和独立索引身份保持不变，当前不重复生成24题，不启动该E03候选的80题。
3. 优先以已通过E02语义策略加相同公共连接层作为完整development80候选，并准备与M2 v4语义基线加相同连接层的同轮比较；两侧仍需新的冻结身份，不能把本轮E02/E03差异当作M2/M3全量比较。
4. 0407的同名字段归属与未解析诊断、0085的公式/单位问题列入遗留。若另启修正实验，须有独立问题假设及边界，不以不断追加模型尝试追分。
5. 不重跑已观察holdout作为新盲测，不从本轮22/24推算80题或未见数据库准确率。

## 9. 复核范围限制

本地没有重执行SQL或重新核算远程表内容；完整索引文件及独立embedding检查回执不在本次七份下载文件中，核对的是受控服务器报告所记录的身份与检查结果。机器审查中对照汇总已重新计算，原生EX则核对已保存原生复评记录及其SQL/结果证据链。

机器记录：[m3_e03_process_dns_pair24_server_review_local_20261024.json](results/m3_e03_process_dns_pair24_server_review_local_20261024.json)。离线复核脚本保存在`backend/.downloads/review_m3_e03_process_dns_pair24_20261024.py`。
