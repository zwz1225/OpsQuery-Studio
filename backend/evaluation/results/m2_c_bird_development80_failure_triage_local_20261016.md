# M2 development80 首轮基线核对与失败清单

原始报告 SHA-256：`7f59478b5d589a49d85027e965e8b3596416ac998df4618c655984841fc8c01d`。

证据核对：1940/1940 通过；失败项：[]。

主 EX：34/80（42.5%）。58 题完整计分，24 题 EX 不匹配、20 题澄清、2 题校验耗尽。
本记录只分析开发集；未执行 holdout 模型评测，未发起数据库或模型请求。

## 下一步

先补充诊断证据，再进行代表题诊断和通用修正，保留当前基线。新增诊断须有数量和长度上限，并脱敏；Gold、答案或 EX 反馈只能用于可信开发评审，不能传回 Agent 或索引器。
需记录排序候选及分数/筛选原因、最终授权 Schema 图及关联键、各次生成 SQL/哈希、结构化校验原因、澄清解释。
优先核查 0050、0095、1473 的校验错误；随后处理检索覆盖、实体/标识符与类别值、输出范围及 NULL 排序。
百分比题的 Decimal 与参考 REAL 计算路径需要原生结果证据，不能仅凭类型差异断言原因或放宽容差。

## 未通过 EX 的 46 题

| 题号 | 数据库 | 状态 | 选中字段 | 诊断分类 | 观察与证据边界 |
|---|---|---|---:|---|---|
| BIRD-PG-0011 | california_schools | scored | 5 | identifier_semantics | Returns School Code rather than the reference CDSCode; the former is a different identifier. |
| BIRD-PG-0025 | california_schools | scored | 12 | field_and_population_semantics | Filters satscores.rtype by Riverside and uses schools.fundingtype; reference uses frpm District Name and Charter Funding Type. |
| BIRD-PG-0036 | california_schools | scored | 8 | projection_and_null_order | Returns 2 instead of 6 administrator-name columns; DESC lacks NULLS LAST. |
| BIRD-PG-0050 | california_schools | validation_failed | 4 | validation_exhausted | Three failed validation attempts: 42703, 42703, 42703. SQL attempt text and detailed safe diagnostics are not recorded. |
| BIRD-PG-0072 | california_schools | scored | 4 | aggregation_scope | Prediction sums enrollment; reference returns matching enrollment rows. Full native tuples are needed for the exact discrepancy. |
| BIRD-PG-0077 | california_schools | scored | 20 | projection_and_percentage_expression | Returns grade span rather than school name, and a stored percentage rather than the reference ratio times 100. |
| BIRD-PG-0082 | california_schools | scored | 3 | null_order | Same longitude ordering expression, but prediction omits DESC NULLS LAST. |
| BIRD-PG-0083 | california_schools | clarification | 3 | clarification_before_sql | Selected 3 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-0085 | california_schools | scored | 13 | percentage_expression | Uses a stored percentage field; reference computes Free Meal Count / Enrollment * 100. |
| BIRD-PG-0352 | card_games | scored | 14 | population_and_native_numeric_path | Prediction queries foreign_data alone and returns Decimal; reference joins cards and uses REAL. Separate population and precision effects before assigning cause. |
| BIRD-PG-0368 | card_games | scored | 7 | native_numeric_path_candidate | Prediction uses NUMERIC-style 100.0 arithmetic and returns Decimal; reference casts numerator to REAL. Exact native values are not present, so precision is a candidate cause. |
| BIRD-PG-0371 | card_games | clarification | 3 | clarification_before_sql | Selected 3 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-0407 | card_games | scored | 20 | projection_semantics | Returns foreign_data.type instead of cards.subtypes and cards.supertypes with the required non-NULL filters. |
| BIRD-PG-0415 | card_games | scored | 6 | categorical_value_case | Prediction filters legalities.status=legal; frozen reference uses Legal. Report EX is false. |
| BIRD-PG-0473 | card_games | scored | 7 | join_and_answer_representation | No setCode=code join predicate and returns raw isforeignonly instead of the reference YES/NO expression. |
| BIRD-PG-0537 | codebase_community | scored | 20 | entity_resolution | Uses posts.ownerdisplayname; reference resolves users.displayname through OwnerUserId. |
| BIRD-PG-0557 | codebase_community | scored | 7 | native_numeric_path_candidate | Population and count expression appear aligned; prediction returns Decimal and reference casts numerator to REAL. Native result pairs are needed to confirm precision cause. |
| BIRD-PG-0586 | codebase_community | clarification | 1 | clarification_before_sql | Selected 1 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-0595 | codebase_community | scored | 6 | grouping_and_count_semantics | Groups by user and post, counts history rows; reference groups by user and counts DISTINCT history type. |
| BIRD-PG-0604 | codebase_community | clarification | 2 | clarification_before_sql | Selected 2 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-0637 | codebase_community | clarification | 2 | clarification_before_sql | Selected 2 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-0639 | codebase_community | clarification | 4 | clarification_before_sql | Selected 4 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-1473 | debit_card_specializing | clarification | 3 | clarification_after_validation_error | Selected 3 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-1476 | debit_card_specializing | clarification | 2 | clarification_before_sql | Selected 2 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-1480 | debit_card_specializing | clarification | 2 | clarification_before_sql | Selected 2 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-1481 | debit_card_specializing | clarification | 2 | clarification_before_sql | Selected 2 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-1486 | debit_card_specializing | scored | 1 | population_and_projection | Omits Segment=SME, adds YES/NO column and ABS around the difference. |
| BIRD-PG-1505 | debit_card_specializing | clarification | 3 | clarification_before_sql | Selected 3 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-1524 | debit_card_specializing | clarification | 2 | clarification_before_sql | Selected 2 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-1533 | debit_card_specializing | clarification | 2 | clarification_before_sql | Selected 2 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-0095 | financial | validation_failed | 9 | validation_exhausted | Three failed validation attempts: 42P10, 42P10, 42P10. SQL attempt text and detailed safe diagnostics are not recorded. |
| BIRD-PG-0115 | financial | scored | 3 | grouping_order_and_numeric_path | Prediction selects one district after integer population ordering; reference groups clients by A4 and orders A4. Prediction also returns Decimal; reference uses REAL. |
| BIRD-PG-0145 | financial | scored | 13 | identifier_and_average_population | Returns client_id rather than account_id and uses a different average population and extra card/disp joins. |
| BIRD-PG-0152 | financial | clarification | 1 | clarification_before_sql | Selected 1 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-0159 | financial | scored | 16 | projection_scope | SELECT t.* returns 10 columns; reference selects trans_id only. |
| BIRD-PG-1361 | student_club | clarification | 1 | clarification_before_sql | Selected 1 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-1398 | student_club | clarification | 3 | clarification_before_sql | Selected 3 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-1399 | student_club | clarification | 9 | clarification_before_sql | Selected 9 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-1405 | student_club | scored | 6 | foreign_key_value_resolution | Compares budget.link_to_event directly with an event name instead of resolving event_id via event. |
| BIRD-PG-1411 | student_club | scored | 8 | foreign_key_value_resolution | Compares expense.link_to_member directly with a full name instead of joining member identifiers. |
| BIRD-PG-1427 | student_club | clarification | 2 | clarification_before_sql | Selected 2 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-1435 | student_club | clarification | 0 | clarification_before_sql | Selected 0 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |
| BIRD-PG-0726 | superhero | scored | 2 | null_order_and_ranking | RANK height DESC lacks the reference NULLS LAST; rank values can change, beyond row-order differences. |
| BIRD-PG-0766 | superhero | scored | 5 | categorical_value_case_and_null_order | Prediction uses strength instead of reference Strength and omits NULLS LAST. |
| BIRD-PG-0773 | superhero | scored | 10 | projection_scope | Returns publisher only; reference also returns superhero_name. |
| BIRD-PG-0201 | toxicology | clarification | 1 | clarification_before_sql | Selected 1 fields. No SQL executed. Clarification wording and raw rerank scores are absent. |

## 原生 EX 与辅助诊断

BIRD-PG-0717：顺序不同但原生行集合一致，EX 通过。BIRD-PG-0738：重复次数不同但集合一致，EX 通过。两项符合冻结的 tuple-set EX，不应按排序或重复次数改判。
