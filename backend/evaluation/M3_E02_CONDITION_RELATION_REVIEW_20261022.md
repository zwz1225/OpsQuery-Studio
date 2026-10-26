# M3 E02：条件与关系依据离线审查

日期：2026-10-22（Asia/Shanghai）。状态：1479筛选审查、0407关联审查、最小适配与正反例清单均已完成；候选策略尚未实现，未启动模型或服务器评测。

## 1. 范围、材料与核验方式

- 使用E01两边已保存生成报告、相应同身份索引、原development80公开question/evidence、受信M2导入清单及官方列描述。
- 重放现有coverage.select_fields与intent.expand_fields，仅传入报告中的rerank分数、授权文档和由已声明约束重建的元数据；两边两个案例的结果均与原记录一致。没有调用检索模型或新SQL。
- 原始约1GB PostgreSQL文本包仅做文件摘要校验；实际解析限于cards、foreign_data、customers、yearmonth四张开发表的COPY块，保留键计数与包含关系，不执行SQL、不计算答案或EX、不解析保留集表。
- 四份描述CSV、数据包、COPY块摘要与M2受信清单一致。全部44项审查核验通过；随后补查孤儿键的语言范围。正式运行仍须复用现有实时来源验证，不能把离线统计当作新服务器验证。
- 本审查没有读取模型配置或数据库私密凭据，没有导入scorer/Gold，没有改动原始报告、生产代码、数据、Gold、EX或预算。

机器证据：[主审查JSON](results/m3_e02_condition_relation_review_local_20261022.json)、[孤儿键范围JSON](results/m3_e02_card_orphan_scope_local_20261022.json)。
实施清单：[最小适配与正反例清单v2](m3_e02_minimal_adaptation_review_20261022_v2.json)。正反例是后续验收场景，尚未实现为新策略测试，不能称为已通过的候选测试。

## 2. 第一部分：1479字段筛选过程

公开问题：Which year recorded the most consumption of gas paid in CZK? 公开evidence只解释yearmonth.date前四位表示年份，CZK要求来自question，不是evidence中的显式等式。

### 2.1 候选已召回，筛选阶段丢失关键角色

| 字段 | rerank分数 | 报告中的筛选原因 | 解释 |
| --- | ---: | --- | --- |
| yearmonth.consumption | 0.669462 | selected | 主表锚点 |
| yearmonth.date | 0.563490 | selected | 主表锚点 |
| customers.currency | 0.503396 | coverage_table_not_anchored | 超过0.50覆盖下限，但customers不是0.55主阈值锚点 |
| yearmonth.customerid | 0.512599 | coverage_no_intent_match | 关联键不是公开问题的输出／条件词 |
| customers.customerid | 0.337843 | below_coverage_floor | 低于0.50；不能靠统一放宽阈值解决关联 |

该域只有21个RRF候选。coverage基线只保留消费量和日期，锚表为yearmonth；不是题意需要的字段在源库中不存在。

currency的matched_intent_terms和uncovered_intent_terms也均为空：问题写的是paid in CZK，没有直接出现currency字段词。因此即使让customers成为锚表，普通coverage的词面匹配门槛仍不足以接纳它；后面的分类值提示需要单独检查，而不是只改一个锚表判断。

### 2.2 后续intent层存在两个独立门槛

重放发现，sample_conditions确实产生了customers.currency=CZK的唯一分类样本提示，authority=coverage_hint_only、mandatory=false。索引样本包含CZK和EUR，未截断。

该提示仍未补入字段，原因同时包括：

1. condition_scope=false：customers既不是已有锚表，也未被公开表名或唯一字段名显式命中；问题中的CZK不等于字面字段名currency。
2. reachable=false：当前关系图只使用声明外键，而该域没有yearmonth→customers的声明外键路径。

即使仅修正“表未锚定”，外键可达门槛仍会拦截；仅增加关系边，原样的condition_scope规则也未必接纳该提示。最终intent没有任何新增字段，图只有2个字段、0条边，规范值查询probe_count=0。

**诊断缺口：** 当前sample_condition_candidates在返回前只保留最终已选择字段对应的提示，隐藏了这条真实存在但被拒绝的原始提示。应先补充拒绝记录，避免把“报告列表为空”误读为“样本没识别到CZK”。

### 2.3 条件字段与关联键的依据

- 官方customers.Currency描述为Currency，customers.CustomerID描述为客户标识；yearmonth.CustomerID的标签和描述均为Customer ID。
- 两端CustomerID均为BIGINT；customers.customerid有主键和唯一索引。yearmonth的唯一索引为(date,customerid)，不能把其customerid单列误当唯一。
- 冻结数据中customers共32,461行，customerid无NULL且唯一；yearmonth共383,282行，30,566个不同customerid，全部可匹配父表，孤儿键和NULL均为0；同一客户最多20条子记录。

这些事实支持“客户标识的一对多候选关联”，不等于数据库声明过外键，也不能仅因相同键值就证明任意业务JOIN语义。应保留来源版本、公开列角色、唯一性和包含关系证据，作为有明确角色的可选关联。

**最小候选字段集合：** 原消费量、日期，加customers.currency、customers.customerid、yearmonth.customerid，共5个字段即可覆盖条件及连接需求，当前有充足额度，不需要扩大20字段上限。仅识别字段后仍要由公开问题决定筛选，不能把所有样本提示强制变成WHERE条件。

## 3. 第二部分：0407关联依据

公开question要求German卡牌的all types；evidence将all types定义为subtypes、supertypes，并明确两列非NULL。

### 3.1 字段存在不代表关联可执行

- 两个输出字段、foreign_data.language都已选入20个字段；同时还有set_translations.language等竞争候选。
- cards.uuid和foreign_data.uuid都存在于授权索引，但未进入本题RRF候选，不能写成“某个已观察分数低于阈值”。
- 两个UUID都没在question/evidence中直接提及，现有intent也不会靠字段名提及补齐；图构建器没有声明外键，就不会制造关联边或两端键。最终joins=[]。
- 选择阶段已经占满20字段，后续若想加入两个键，需要明确字段分配策略；不能静默突破上限，也不能声称只多加一条提示就有完整上下文。

### 3.2 真实键约束与列描述

- cards.uuid和foreign_data.uuid均为TEXT，DDL允许NULL；冻结样本中两列实际均无NULL，不能据此把DDL改成NOT NULL。
- cards.uuid有独立唯一索引；cards和foreign_data各自的主键都是id。UUID不是cards的主键。
- cards.uuid公开描述为MTGJSON生成的唯一标识；foreign_data.uuid的描述为空，不提供显式指向cards的关系说明。少量样本有交集，不能仅凭3个样本确认全表引用。
- 受信清单中没有foreign_data.uuid→cards.uuid外键。确实存在rulings.uuid→cards.uuid外键，但不能转移为foreign_data的外键。
- 当前runtime catalog将主键标为primary_key，仅声明外键生成关系；已核验的次级唯一索引没有作为候选关系证据进入catalog/graph。因此cards.uuid在文档中仍是普通field。当前元数据读取没有漏读一条已声明外键，缺的是独立的候选关系表达。

### 3.3 全量键包含检查发现真实孤儿记录

| 核对项 | 结果 |
| --- | ---: |
| cards行数／不同非NULL UUID | 56,822／56,822 |
| foreign_data行数 | 229,186 |
| foreign_data不同UUID | 34,056 |
| 可匹配cards的子记录 | 229,170 |
| 不可匹配的子记录／不同UUID | 16／3 |
| German子记录／其中不可匹配 | 28,891／3 |

**决策：** 有充分证据把UUID连接列入“待审查的同域候选关系”，但不能将其标记为真实外键、完整参照关系或无损JOIN。即使限定German仍有3条孤儿记录；INNER JOIN会排除这些记录，是否符合业务总体需要显式依据，不能依据Gold采用了INNER JOIN就直接固定。

数据中存在孤儿键不意味着禁止合法JOIN或要修补原始数据；它要求表达不完整性、保留join类型选择与未解决语义，不得静默提升可信等级或新增数据库约束。

本轮首个最小候选建议不为0407自动开启关联补全，先补齐诊断、唯一键证据和候选关联记录；孤儿键语义与已满20字段的分配另行审查。将其作为观察案例，避免同时加入两个未经区分的关系策略。

## 4. 第三部分：问题与最小适配清单

| 问题 | 证据级别 | 建议 | 首个候选范围 |
| --- | --- | --- | --- |
| 1479币种字段被锚表规则阻断 | 已重放确认 | 记录并有界接纳具有明确公开角色的条件覆盖候选 | 进入 |
| 被拒绝样本提示在报告中消失 | 已重放确认 | 保留原始提示和每个门槛的拒绝原因 | 进入 |
| 必需关联键没有输出词匹配 | 已重放确认 | 经审查关联的两端键作为条件上下文组成部分，不靠普通语义排名 | 1479进入 |
| 未声明关系没有独立表达 | 已核对DDL和runtime实现 | declared FK和reviewed candidate分开标记；不修改数据库约束 | 进入设计 |
| 次级唯一索引信息未进入候选关系证据 | 已核对实现 | 从已核验授权结构中携带唯一键集合，保留复合键整体 | 进入设计 |
| 0407存在孤儿键 | 冻结数据全量核对 | 风险与join语义单列；不当作完整参照关系自动接纳 | 仅诊断 |
| 0407已占20字段 | 已核对轨迹 | 明确必要键额度及溢出状态，字段重分配另立规则 | 本轮不重排 |
| 0085公式落实、0050名称歧义 | E01已观察 | 留在SQL语义队列 | 暂缓 |

### 4.1 最小实施顺序

1. 定义带公开文本span和角色的需求记录；保留原始覆盖提示、拒绝理由、字段所有者、关联证据与缺口状态。
2. 增加来源绑定的候选关系说明，与声明外键严格区分；表达唯一键、类型、数据版本、验证范围、孤儿记录和歧义，不自动选JOIN类型。
3. 在独立开发开关下，尝试1479类“明确公开条件角色＋唯一授权字段所有者＋经核对同域键关系”的有界补充，将条件字段及两端键一起考虑。只读当前授权域，沿用原20字段、4个coverage补充、8个intent补充、2跳及题内预算；不全面降低阈值。
4. 保持现有模型生成、SQL校验、修复和原生评分规则。条件提示本身不构成强制WHERE依据，运行时仍需明确题意；关系依据或额度不足时显式记录未完成，不声称覆盖成功。
5. 实现清单中的6类正例、10类反例，并检查成功回归。当前这些是待实现的验收条件，尚未运行新策略测试。

### 4.2 字段额度与对照接入的两个约定

- 目前20字段限制作用于选择阶段，原图构建器是在之后补充声明关系键，不能把“图全字段始终<=20”说成已存在的实现。首个候选1479只需5字段；0407的额度重排暂缓。后续若设全图总上限或保留键额度，要在实验前明确版本及验收含义。
- E01对照要求索引生产代码相同、两边观察Schema相同；新的检索实验预期改变Schema，且intent/relationships等文件属于索引身份摘要的一部分。后续必须单独冻结索引身份和比较接口，按真实身份构建／验证索引并分列费用，不能直接复用旧脚本硬判同Schema、强行让旧缓存命中或修改E01结论。

## 5. 正反例验收清单（待实现）

### 正例

- P1 Explicit public payment currency + unique authorized currency owner + stored value match => coverage candidate, not a sample-only hard predicate
- P2 Reviewed parent unique key + compatible child key + recorded same-domain evidence => bounded annotated candidate relation
- P3 Explicit evidence output group across selected tables => diagnose missing join keys even when output fields exist
- P4 Declared FK bridge => preserve prior path behavior and include both key ends
- P5 Composite unique index => preserve entire key; never treat a subset as unique
- P6 Output/filter/key closure within original20 fields and2 hops => record reason and authority for each field

### 反例

- N1 Same name/type alone without ownership or verified unique target => no confirmed edge
- N2 Profile sample code without an explicit public condition role => advisory coverage only
- N3 Multiple currency owners or competing actor/owner edges => retain ambiguity; no mandatory conjunction
- N4 Nonunique parent, orphan or incompatible key types => reject high-confidence relation candidate
- N5 A null or orphan child does not authorize filling data, coercing IDs or arbitrary inner joins
- N6 Cross-database/schema or unauthorized field => reject before value profiling
- N7 Field/addition/hop cap exceeded => record incomplete context; do not drop the business condition silently
- N8 Only old3 samples or frozen-dump support without live source binding => do not claim current server validation
- N9 Token case, renamed case_id or public paraphrase => no case-ID rules or answer-dependent branch
- N10 E01 output observer, numeric unit behavior, Gold and EX policy => unchanged/disabled as specified

## 6. 当前结论与下一步

三部分离线审查已完成。1479不是单一rerank阈值问题：条件所有者的跨锚表接纳、声明外键可达门槛和拒绝提示丢失共同存在。0407则有非主键唯一性未表达、未声明关系、孤儿键和额度四项边界。

下一步可以在本地实现需求／拒绝诊断与候选关系数据结构，先为1479类场景准备最小、有开关的补充策略及正反例测试。0407先保留完整诊断与候选证据，不纳入自动可信关系补全。之后再冻结第二轮运行身份、题目和门槛，并交付独立对照命令。

本阶段不改变E01未推广的结论，不安排完整80题、不使用已观察保留集调参，也不要求用户重新导入数据或重跑服务器。

## 7. 代码定位与证据摘要

- `evaluation/bird/coverage.py:40`：`select_fields`。
- `evaluation/bird/intent.py:42`：`checked_tables`。
- `evaluation/bird/intent.py:100`：`sample_conditions`。
- `evaluation/bird/intent.py:199`：`expand_fields`。
- `evaluation/bird/relationships.py:64`：`build_graph`。
- `evaluation/bird/relationships.py:14`：`_shortest_path_relations`。
- `evaluation/bird/runtime.py:246`：`_catalog`。

- 主审查JSON SHA-256：`d03bcb1e9c384a3237484a7d1574fce6ce1baa257570791ebad794e24aabf472`。
- 孤儿键范围JSON SHA-256：`d07938812906e5231df8d076857b058470d07c567bf97f14f4406f81187a28f7`。
- 原始数据、描述、索引、报告及选择器文件摘要均在机器证据中逐项保存。完整键值未导出，结果统计不进入模型输入。
