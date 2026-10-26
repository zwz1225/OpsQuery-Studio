# M2 v4 正式 holdout30 详细核对

核对日期：2026-10-19（Asia/Shanghai）。

**结论：下载材料的1,166项核心检查全部通过。正式EX为19/30（63.33%），M2按“可信外部基线与评测校准”范围验收完成。11题原生不匹配保留，不再追加本轮调参。**

## 1. 正式身份与登记

- 候选：`m2_v4_97342997118d809666147b0d943f0a676fbb65e220fe5bbc62d89e4e2ecfbbfc`。
- attempt_id：`1218483158c643a085e7b9360dd4a7d7`。
- 主报告SHA-256：`9c8afa202a10ac9bf7f396d37d7efa4a739fe6d7f3de5bc25414ec04a0a5b008`。
- 日志SHA-256：`7146bf74d892890b9eedbb2eb0f21b86c2b99dc36f4fb10cc0c614f05f9d690d`。
- 同一冻结文件、96个原执行文件和5个控制器/复评依赖文件；协议11个产物、模型公开配置、来源与预算完全一致。
- 本地冻结记录时间早于服务器reserved事件；服务器使用的冻结文件哈希与本地一致。
- 所提供登记目录只有一个候选目录、一次attempt，97个事件链完整；30份Gold就绪记录和30份病例文件均与根报告及事件哈希一致。最后事件为completed。
- 全30条Gold就绪先于索引和Agent调用；隔离、预算和600秒硬超时探针通过。预测对象与原生成结果诊断一致。
- 最终报告（排除journal.finished_at）与完成事件的内容摘要一致。日志中的Gold就绪、30题状态及最终summary与JSON逐项一致。

该核对仅证明所提供登记材料的一致性，不能独立排除工作区外运行、删除过的历史尝试或服务器其他目录。本轮没有重新执行SQL或调用模型。

## 2. 成绩与覆盖

| database_id | 完整评分 | EX通过 | EX |
| --- | ---: | ---: | ---: |
| european_football_2 | 10 | 9 | 90% |
| formula_1 | 10 | 6 | 60% |
| thrombosis_prediction | 10 | 4 | 40% |

| 难度 | 通过/总数 | EX |
| --- | ---: | ---: |
| simple | 6/9 | 66.67% |
| moderate | 9/15 | 60.00% |
| challenging | 4/6 | 66.67% |

30题全部完成原生评分；0澄清、0超时、0结果超限、0结果SQL执行失败。SQL执行成功不等于答案正确；11题均保留为原生不匹配。主EX不是官方排行榜成绩。开发集50/80与保留集19/30分开报告，不合并。

本地重建48个完整原生结果对象和22题完整原生比较；另12个结果为有界预览，涉及8题。这8题的完整比较依赖服务器原生摘要、比较记录及其登记绑定。本地未查询数据库。原服务器snapshot未下载，但已重建其内容哈希并与报告一致。

## 3. 模型、修复与成本

- 逐题模型HTTP95次=30次embedding+30次rerank+35次chat；共享索引37次embedding，合计132次HTTP。服务返回模型标识符合冻结配置，未发生传输重试，单题计数均在冻结上限内。
- 3个保留域索引均新建：european_football_2 20次、formula_1 10次、thrombosis_prediction 7次embedding，全部绑定本域账号、catalog和data版本。
- 25题一次生成，5题两次生成；单次生成题原生通过15题，修复题原生通过4题。
- 五次校验拒绝：1030和0981的NULL排序；1048受限函数；0962和1192的函数不兼容。都在执行前被处理，最终30题第一次实际结果SQL执行都成功。不能将“第一次实际执行成功”表述为“第一条模型SQL全部正确”。
- 生成SQL工具41次=11次规范值查找（12对字段/字面值）+30次预测结果SQL；另30次正式Gold评分、30次Gold就绪，合计101次结果查询。EXPLAIN、元数据和profile读取另计，不包含在101内。
- chat返回usage：prompt247808、completion2620、total250428 tokens；不冒充实际账单。
- 单题延迟p50=13.353秒、p95=30.658秒、最大36.798秒；整次运行692.632秒，包含就绪与索引准备。

## 4. 11题遗留逐项核对

### BIRD-PG-1039：numeric_path_and_native_precision

预测AVG(long_shots)返回Decimal 61.5714285714285714；参考SUM::REAL/COUNT(date)返回float。当前差异体现原生数值路径，AVG的空值分母规则与参考也非普遍等价。

后续方向：通用数值路径兼容与公开公式保真；保持本次原生失败，不添加浮点容差。

### BIRD-PG-0897：output_field_group_and_aggregation

预测将forename/surname合并为一列，输出3列；参考分别输出姓名两列，共4列。同时SUM(wins)与参考COUNT(wins)/wins>=1口径不同。本次都返回同一车手，列形态差异足以导致原生失败。

后续方向：输出字段组与计数/求和角色；不能仅靠列别名处理。

### BIRD-PG-0928：relationship_rank_role_and_reference_shape

预测driverstandings.position=1并仅返回driverref；参考results.rank=1并返回forename、surname、driverref。本次返回的车手也不同。题面要求reference name而参考增加姓名列，另记参考形态差异。

后续方向：关联表/排名字段角色，并独立记录参考输出形态问题。

### BIRD-PG-0962：mixed_numerator_denominator_grain

分子按比赛结果行计数，分母COUNT(DISTINCT driverid)，参考分母COUNT(*)。第一次函数错误已修复，最终SQL可执行但分子分母粒度仍不一致。

后续方向：公开百分数分子/分母总体一致性，不按题号修正。

### BIRD-PG-0964：public_evidence_reference_literal_conflict

官方evidence明确nationality='America'，预测照此筛选为空；参考用'American'并返回157行。此次canonical_lookup.probe_count=0，没有执行规范值探测。

后续方向：单列公开evidence与参考字面值冲突；后续只能根据授权数据值核实，不能向模型注入Gold字面值。

### BIRD-PG-1153：table_entity_role_alignment

预测使用examination.diagnosis并关联laboratory，结果为空；参考从patient.diagnosis关联laboratory，返回60行。

后续方向：区分实体主表与检查记录表的相同字段角色。

### BIRD-PG-1205：native_boolean_text_output_shape

条件表达式相同，但预测输出字符串Yes/No，参考输出原生布尔TRUE/FALSE；两边均67行。不能在冻结EX中自动转型通过。

后续方向：通用布尔输出约定及参考形态披露，不回溯归一化本次结果。

### BIRD-PG-1227：explicit_age_formula

公开公式要求当前年份减出生年份；预测使用AGE后取完整岁数。预测74.5732087227414330，参考74.6853582554517134。

后续方向：区分年份差与完整周岁，按公开公式选择计算路径。

### BIRD-PG-1242：public_evidence_reference_time_conflict

官方evidence明确用current_timestamp年份减出生年份；预测照此计算。参考用1984年的检验日期年份减出生年份。当前预测5行，参考76行。

后续方向：单列公开evidence与参考时间锚点冲突；保留本次失败，不用Gold覆盖公开指令。

### BIRD-PG-1267：authorized_enum_storage_mapping

预测筛选SM IN('-', '+-')，参考用数据库存储值('negative','0')；官方evidence已经说明符号与存储值的对应关系。预测0，参考7。

后续方向：落实公开值映射与授权原生枚举查找，覆盖IN列表。

### BIRD-PG-1275：authorized_enum_storage_mapping

CENTROMEA、SSB使用了显示符号('-', '+-')，参考用存储值('negative','0')；预测0，参考1。DISTINCT已经保留。

后续方向：基于授权字段说明和数据值建立通用枚举映射；不得制作参考答案特例。

0964与1242存在明确公开evidence/Gold口径冲突；0928另有参考输出形态差异，1205是布尔/字符串形态差异。本次均按冻结原生规则计失败，不删题、不修订Gold、不改分。以上参考比较仅供运行后的可信审查，不回传生成模型。

## 5. 30题逐题清单

| case_id | 数据库 | 难度 | EX | 生成次数 | 本地完整比较重建 |
| --- | --- | --- | --- | ---: | --- |
| BIRD-PG-1028 | european_football_2 | challenging | 通过 | 1 | 是 |
| BIRD-PG-1030 | european_football_2 | moderate | 通过 | 2 | 是 |
| BIRD-PG-1036 | european_football_2 | challenging | 通过 | 1 | 否，依赖服务器完整记录 |
| BIRD-PG-1039 | european_football_2 | simple | 失败 | 1 | 是 |
| BIRD-PG-1048 | european_football_2 | simple | 通过 | 2 | 是 |
| BIRD-PG-1091 | european_football_2 | moderate | 通过 | 1 | 是 |
| BIRD-PG-1102 | european_football_2 | moderate | 通过 | 1 | 是 |
| BIRD-PG-1110 | european_football_2 | moderate | 通过 | 1 | 是 |
| BIRD-PG-1116 | european_football_2 | simple | 通过 | 1 | 是 |
| BIRD-PG-1130 | european_football_2 | moderate | 通过 | 1 | 否，依赖服务器完整记录 |
| BIRD-PG-0859 | formula_1 | simple | 通过 | 1 | 是 |
| BIRD-PG-0879 | formula_1 | moderate | 通过 | 1 | 是 |
| BIRD-PG-0897 | formula_1 | moderate | 失败 | 1 | 是 |
| BIRD-PG-0928 | formula_1 | moderate | 失败 | 1 | 是 |
| BIRD-PG-0933 | formula_1 | moderate | 通过 | 1 | 是 |
| BIRD-PG-0962 | formula_1 | challenging | 失败 | 2 | 是 |
| BIRD-PG-0964 | formula_1 | simple | 失败 | 1 | 否，依赖服务器完整记录 |
| BIRD-PG-0971 | formula_1 | simple | 通过 | 1 | 是 |
| BIRD-PG-0981 | formula_1 | moderate | 通过 | 2 | 是 |
| BIRD-PG-0994 | formula_1 | challenging | 通过 | 1 | 是 |
| BIRD-PG-1150 | thrombosis_prediction | moderate | 通过 | 1 | 是 |
| BIRD-PG-1153 | thrombosis_prediction | simple | 失败 | 1 | 否，依赖服务器完整记录 |
| BIRD-PG-1155 | thrombosis_prediction | simple | 通过 | 1 | 否，依赖服务器完整记录 |
| BIRD-PG-1192 | thrombosis_prediction | challenging | 通过 | 2 | 是 |
| BIRD-PG-1205 | thrombosis_prediction | moderate | 失败 | 1 | 否，依赖服务器完整记录 |
| BIRD-PG-1220 | thrombosis_prediction | simple | 通过 | 1 | 否，依赖服务器完整记录 |
| BIRD-PG-1227 | thrombosis_prediction | moderate | 失败 | 1 | 是 |
| BIRD-PG-1242 | thrombosis_prediction | challenging | 失败 | 1 | 否，依赖服务器完整记录 |
| BIRD-PG-1267 | thrombosis_prediction | moderate | 失败 | 1 | 是 |
| BIRD-PG-1275 | thrombosis_prediction | moderate | 失败 | 1 | 是 |

## 6. 结论与后续

M2本轮结束。保留代码、冻结文件、协议、原始报告、日志、snapshot引用和登记目录。M3再处理数值路径、输出组/类型、条件/关联角色、原生枚举映射以及检索覆盖。

保留结果已经观察，后续任何依据这30题反馈的修正与复跑都须披露为保留集复用，不能再描述为未参与调参的首次保留评测。无需为了清零11个失败而继续M2验收重跑。
