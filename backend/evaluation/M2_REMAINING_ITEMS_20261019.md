# M2 遗留项清单

日期：2026-10-19。M2已验收完成，以下进入后续通用改进计划。

## 保留集11题

| 题号 | 分类 | 已确认差异 | 后续方向 |
| --- | --- | --- | --- |
| BIRD-PG-1039 | numeric_path_and_native_precision | 预测AVG(long_shots)返回Decimal 61.5714285714285714；参考SUM::REAL/COUNT(date)返回float。当前差异体现原生数值路径，AVG的空值分母规则与参考也非普遍等价。 | 通用数值路径兼容与公开公式保真；保持本次原生失败，不添加浮点容差。 |
| BIRD-PG-0897 | output_field_group_and_aggregation | 预测将forename/surname合并为一列，输出3列；参考分别输出姓名两列，共4列。同时SUM(wins)与参考COUNT(wins)/wins>=1口径不同。本次都返回同一车手，列形态差异足以导致原生失败。 | 输出字段组与计数/求和角色；不能仅靠列别名处理。 |
| BIRD-PG-0928 | relationship_rank_role_and_reference_shape | 预测driverstandings.position=1并仅返回driverref；参考results.rank=1并返回forename、surname、driverref。本次返回的车手也不同。题面要求reference name而参考增加姓名列，另记参考形态差异。 | 关联表/排名字段角色，并独立记录参考输出形态问题。 |
| BIRD-PG-0962 | mixed_numerator_denominator_grain | 分子按比赛结果行计数，分母COUNT(DISTINCT driverid)，参考分母COUNT(*)。第一次函数错误已修复，最终SQL可执行但分子分母粒度仍不一致。 | 公开百分数分子/分母总体一致性，不按题号修正。 |
| BIRD-PG-0964 | public_evidence_reference_literal_conflict | 官方evidence明确nationality='America'，预测照此筛选为空；参考用'American'并返回157行。此次canonical_lookup.probe_count=0，没有执行规范值探测。 | 单列公开evidence与参考字面值冲突；后续只能根据授权数据值核实，不能向模型注入Gold字面值。 |
| BIRD-PG-1153 | table_entity_role_alignment | 预测使用examination.diagnosis并关联laboratory，结果为空；参考从patient.diagnosis关联laboratory，返回60行。 | 区分实体主表与检查记录表的相同字段角色。 |
| BIRD-PG-1205 | native_boolean_text_output_shape | 条件表达式相同，但预测输出字符串Yes/No，参考输出原生布尔TRUE/FALSE；两边均67行。不能在冻结EX中自动转型通过。 | 通用布尔输出约定及参考形态披露，不回溯归一化本次结果。 |
| BIRD-PG-1227 | explicit_age_formula | 公开公式要求当前年份减出生年份；预测使用AGE后取完整岁数。预测74.5732087227414330，参考74.6853582554517134。 | 区分年份差与完整周岁，按公开公式选择计算路径。 |
| BIRD-PG-1242 | public_evidence_reference_time_conflict | 官方evidence明确用current_timestamp年份减出生年份；预测照此计算。参考用1984年的检验日期年份减出生年份。当前预测5行，参考76行。 | 单列公开evidence与参考时间锚点冲突；保留本次失败，不用Gold覆盖公开指令。 |
| BIRD-PG-1267 | authorized_enum_storage_mapping | 预测筛选SM IN('-', '+-')，参考用数据库存储值('negative','0')；官方evidence已经说明符号与存储值的对应关系。预测0，参考7。 | 落实公开值映射与授权原生枚举查找，覆盖IN列表。 |
| BIRD-PG-1275 | authorized_enum_storage_mapping | CENTROMEA、SSB使用了显示符号('-', '+-')，参考用存储值('negative','0')；预测0，参考1。DISTINCT已经保留。 | 基于授权字段说明和数据值建立通用枚举映射；不得制作参考答案特例。 |

## 开发集遗留

30题=27题原生不匹配+3题未回答；详细保留在results/m2_public_intent_v4_development80_triage_local_20261019.json。主要涉及0050列位置、0201粒度、0173业务条件、0239关系方向、1479业务条件/输出、0639授权引用与重复SQL、1524/0152关联覆盖、1533执行恢复后结果仍错、1399参考形态，以及其他逐题SQL差异。

## 评测与工程后续

- 明确公开公式、原生算术路径、布尔输出与字段组的通用约定；不使用题号或Gold特例。
- 规范值查找覆盖IN列表与官方字段说明中的显示值/存储值映射，继续受原SQL预算及授权范围约束。
- 对明确的evidence/Gold冲突单独标记；修订数据或评分必须新协议，不能悄悄覆盖原始分数。
- 降低提示词token及检索误覆盖成本；实际usage与共享索引成本分列。
- 继续保留来源、权限、预算及隔离回归。当前未发现需要在本轮修改控制器或重跑正式保留集的执行缺陷。
- 保留结果已观察，后续评测必须披露复用并维护候选/尝试记录。
