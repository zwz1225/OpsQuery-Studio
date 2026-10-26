# M2 v4 完整 development80 报告核对

核对日期：2026-10-19（Asia/Shanghai）。

## 结论

**两份报告证据核对通过。v4为50/80（62.5%），可进入候选冻结准备；M2尚未完成，holdout30仍未开启。**

原始报告、Gold、题集、规则和评分均未修改。本次在本地做离线核对，0次模型请求、未连接PostgreSQL。没有新增一轮模型生成。

## 1. 完整性、来源、代码与隔离

- 2,506项检查全部通过，检查项明细见同名JSON。
- 两份报告complete/errors=[]；生成80题，77题回答、2题澄清、1题重复SQL终止；80题均关闭runtime。
- 复评77题、154次SQL、0次模型调用；来源数据重新验证、连接池关闭；77份预测结果诊断与生成时全部一致。
- 同一v4六题已验收的96个执行文件、完整服务器依赖与环境身份；与v3相比只有intent.py、relationships.py、units_output.py三处候选模块变化。
- 原始问题/evidence、题目顺序、模型公开配置、预算与原生评分策略保持固定；8个数据库域的账号、catalog/data版本、索引与授权Schema均匹配。
- 7项预算探针、硬超时探针以及文件/网络/进程/环境凭据隔离探针全部通过；生成未读取/执行Gold，保留集未开启。
- 生成snapshot内容哈希可在本地重建；原生复评报告引用的生成报告SHA与实际文件一致。

| 报告 | SHA-256 |
| --- | --- |
| v4生成 | `e19e9eb40db7bc72c9bbf88ecbb31eb126aa28432c183669f4ff08ff4d8c25ef` |
| v4原生复评 | `1bbb278d0a5ffb99b3049faff6e1da2c482230284188e71e8d4fb44504c38774` |

本地独立重建133份完整原生结果对象、66题完整原生比较；另外21份结果只有有界预览，涉及11题，其完整比较依赖服务器结果摘要、哈希与原生比较记录。本地未重新执行数据库查询。

## 2. 固定80题分母的比较

| 指标 | 原始基线 | v3 | v4 |
| --- | ---: | ---: | ---: |
| 原生匹配 | 34/80 | 49/80 | 50/80 |
| 开发集匹配率 | 42.5% | 61.25% | 62.5% |
| 完整回答 | 58 | 76 | 77 |
| 未回答 | 22 | 4 | 3 |

相对原始基线净增16题、提高20个百分点：原成功34题保留31题，新增19题，丢失3题。相对v3保留47个成功题，新增3题，丢失2题，净增1题（1.25个百分点）。不能把一题净增解释为统计显著或跨域泛化证据。

v4已回答题中的条件匹配率为50/77≈64.94%；正式比较口径仍为50/80，不能删除澄清和失败题。

### 相对v3变化的五题

- **BIRD-PG-0226**：v3失败、v4通过。首次已使用ROUND(...,5)，但ROUND(double precision, integer)不受PostgreSQL支持；模型收到42883函数错误后改用NUMERIC计算，最终Decimal 3.84615与参考完全一致。此次不是精度缺失被本地拒绝后修复。
- **BIRD-PG-0263**：v3失败、v4通过。首次SQL保留按关联行统计的公开公式，未被主键/一对多关联强制改成DISTINCT，最终2.6840451814272206与参考完全一致。
- **BIRD-PG-0273**：v3校验失败、v4通过。只以label=+筛选，未将冲突的元素定义同时转成必选过滤；首次SQL通过，最终3.1419284940411703与参考完全一致。
- **BIRD-PG-0050**：v3通过、v4失败。首次SQL误用未声明的sc别名，反馈准确定位后修正为s.street；最终结果为(NULL, 地址)，参考为(地址, NULL)，列位置相反。mailstreet、sname已在初始Schema中，不能归因于关键字段被过滤。名称来源也有变化，但当前行均为NULL，不能据此证明名称字段普遍等价。没有触发本地意图硬拒绝。
- **BIRD-PG-0201**：v3通过、v4失败。v4沿用关联后的行数作为COUNT分母，结果41.196235238637925，参考38.80961092816197。公开COUNT(atom_id)没有明确去重，v4按既定策略仅作粒度提示；保留此歧义和失败，不依据参考添加特例。

### 分数据库域结果

| database_id | 原始 | v3 | v4 |
| --- | ---: | ---: | ---: |
| california_schools | 1/10 | 4/10 | 3/10 |
| card_games | 4/10 | 5/10 | 5/10 |
| codebase_community | 3/10 | 7/10 | 7/10 |
| debit_card_specializing | 2/10 | 4/10 | 4/10 |
| financial | 5/10 | 6/10 | 6/10 |
| student_club | 3/10 | 8/10 | 8/10 |
| superhero | 7/10 | 9/10 | 9/10 |
| toxicology | 9/10 | 6/10 | 8/10 |

## 3. 拒绝、修复与未回答

共14题出现15次校验拒绝，其中4次是本地意图约束：0036输出姓名组、0459与0095的NULL排序、0586参与者/标题输出组。这4题修复后的最终结果均原生通过；未发现由这些拒绝直接造成的最终失分。没有在本次本地核对中执行被拒首条SQL的独立原生复评，因此不宣称绝无误拒绝。

1533还有一次执行阶段division_by_zero，模型下一次生成后执行成功但答案仍错误，不能将“执行恢复”与“答案正确”混为一谈。

- **BIRD-PG-0639**：引用未授权的posttags/tags后原样重复SQL，被来源约束与重复阻断终止；没有执行越权SQL，仍在80题分母计失败。
- **BIRD-PG-1524**：检索Schema只有transactions_1k部分字段，模型明确缺少客户国籍字段及客户信息关联路径后澄清。授权上下文覆盖仍不足，计失败。
- **BIRD-PG-0152**：检索Schema只有district部分字段，模型明确缺少account及开户日期关联路径后澄清。授权上下文覆盖仍不足，计失败。

## 4. 生成质量与成本

| 指标 | 原始基线 | v3 | v4 |
| --- | ---: | ---: | ---: |
| 逐题模型HTTP | 245 | 256 | 255 |
| chat调用 | 85 | 96 | 95 |
| chat返回total_tokens | 188,999 | 503,694 | 516,542 |
| 逐题延迟p95（秒） | 19.628 | 30.580 | 25.001 |

- v4：65题仅一次模型生成，15题需要第二次；63题一次生成后完成回答，其中43题最终原生通过。其余14个修复后回答中7题原生通过；另1题重复SQL终止。
- 255次逐题HTTP=80 embedding +80 rerank +95 chat。共享索引另27次embedding，合计282次；v3已有索引全命中、共享新增0次，因此不能用总HTTP直接判断生成策略成本变化。
- 3个六题阶段已建索引命中；其余5域新建：california_schools 9、debit_card_specializing 3、financial 6、student_club 5、superhero 4次embedding。
- 生成SQL工具110次=32次规范值查找（36个字段/字面值探测）+78次结果SQL（77成功、1次除零后恢复）。原生复评另154次SQL，0模型调用。
- v4比v3少1次chat，但chat tokens增加约2.55%；不能宣称token成本下降。模型返回usage不等同于实际账单金额。

首次生成校验通过不等于首次原生正确；本次没有额外执行所有被拒首条SQL。上述“一次生成通过”来自只有一次生成且最终原生匹配的可直接核实病例。

## 5. 保留的问题与下一步

- **BIRD-PG-0173**：原始基线通过，本轮仍失败。将3539解释为account_to，未按参考的支付金额条件处理。属于公开问题语义解释与筛选字段问题。
- **BIRD-PG-0239**：原始基线通过，本轮仍失败。atom_id与atom_id2两端用OR计数，参考只使用atom_id端点；保留关系角色差异。
- **BIRD-PG-1479**：原始基线通过，本轮仍失败。当前SQL未筛选CZK，并额外输出total_consumption；属于业务条件及输出形态差异。原基线单次通过不证明原SQL业务条件完整。
- **BIRD-PG-1399**：继续保留原生失败。预测为一行Yes；原参考14行去重后为YES与NULL两种元组。大小写与参考形态均有差异，不增加答案归一化、不排除分母。

剩余30题=27题完整SQL但原生不匹配+3题未回答。当前证据足以结束这轮有限开发校准，建议下一步冻结v4（代码/模型配置/来源/协议/预算/候选身份），再实现受控holdout30入口与尝试登记，进行一次正式保留集评测后归档M2。当前只完成报告核对，尚未创建最终冻结清单或执行保留集。

不再为0050、0201等病例追加按题号或参考答案特例，也不回溯修改已保存分数。相同模型名称、temperature=0不保证远端权重不变或逐次完全确定，五题变化不能全部归因于单一规则。

未下载workflow JSON或服务器snapshot原文件；本次确认的是两份主要报告及可重建的snapshot内容哈希，不宣称额外材料已核对。

## 6. 80题逐题对照

| case_id | 原始通过 | v3通过 | v4状态 | v4原生通过 | chat次数 |
| --- | --- | --- | --- | --- | ---: |
| BIRD-PG-0011 | 否 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-0025 | 否 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-0036 | 否 | 是 | diagnostic_answered | 是 | 2 |
| BIRD-PG-0048 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0050 | 否 | 是 | diagnostic_answered | 否 | 2 |
| BIRD-PG-0072 | 否 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-0077 | 否 | 否 | diagnostic_answered | 否 | 2 |
| BIRD-PG-0082 | 否 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0083 | 否 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-0085 | 否 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-0352 | 否 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-0356 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0368 | 否 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0371 | 否 | 否 | diagnostic_answered | 否 | 2 |
| BIRD-PG-0379 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0407 | 否 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-0415 | 否 | 否 | diagnostic_answered | 否 | 2 |
| BIRD-PG-0459 | 是 | 是 | diagnostic_answered | 是 | 2 |
| BIRD-PG-0473 | 否 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-0480 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0537 | 否 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0557 | 否 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0586 | 否 | 是 | diagnostic_answered | 是 | 2 |
| BIRD-PG-0595 | 否 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-0604 | 否 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-0629 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0637 | 否 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0639 | 否 | 否 | repeated_sql | 否 | 2 |
| BIRD-PG-0671 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0707 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-1473 | 否 | 是 | diagnostic_answered | 是 | 2 |
| BIRD-PG-1476 | 否 | 是 | diagnostic_answered | 是 | 2 |
| BIRD-PG-1479 | 是 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-1480 | 否 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-1481 | 否 | 否 | diagnostic_answered | 否 | 2 |
| BIRD-PG-1486 | 否 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-1505 | 否 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-1509 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-1524 | 否 | 否 | clarification | 否 | 1 |
| BIRD-PG-1533 | 否 | 否 | diagnostic_answered | 否 | 2 |
| BIRD-PG-0092 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0095 | 否 | 是 | diagnostic_answered | 是 | 2 |
| BIRD-PG-0099 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0112 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0115 | 否 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-0118 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0145 | 否 | 否 | diagnostic_answered | 否 | 2 |
| BIRD-PG-0152 | 否 | 否 | clarification | 否 | 1 |
| BIRD-PG-0159 | 否 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0173 | 是 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-1361 | 否 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-1398 | 否 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-1399 | 否 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-1405 | 否 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-1409 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-1411 | 否 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-1427 | 否 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-1435 | 否 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-1457 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-1460 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0717 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0726 | 否 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-0738 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0760 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0766 | 否 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0773 | 否 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0782 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0790 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0794 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0806 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0195 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0200 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0201 | 否 | 是 | diagnostic_answered | 否 | 1 |
| BIRD-PG-0206 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0226 | 是 | 否 | diagnostic_answered | 是 | 2 |
| BIRD-PG-0232 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0239 | 是 | 否 | diagnostic_answered | 否 | 1 |
| BIRD-PG-0242 | 是 | 是 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0263 | 是 | 否 | diagnostic_answered | 是 | 1 |
| BIRD-PG-0273 | 是 | 否 | diagnostic_answered | 是 | 1 |

## 7. 全部剩余错误

### 已回答但原生不匹配

BIRD-PG-0011、BIRD-PG-0025、BIRD-PG-0050、BIRD-PG-0072、BIRD-PG-0077、BIRD-PG-0083、BIRD-PG-0085、BIRD-PG-0352、BIRD-PG-0371、BIRD-PG-0407、BIRD-PG-0415、BIRD-PG-0473、BIRD-PG-0595、BIRD-PG-0604、BIRD-PG-1479、BIRD-PG-1480、BIRD-PG-1481、BIRD-PG-1505、BIRD-PG-1533、BIRD-PG-0115、BIRD-PG-0145、BIRD-PG-0173、BIRD-PG-1399、BIRD-PG-1427、BIRD-PG-0726、BIRD-PG-0201、BIRD-PG-0239

### 未回答

BIRD-PG-0639、BIRD-PG-1524、BIRD-PG-0152
