# M2 v4：六题生成与独立原生复评审查

## 结论

两份报告完整、证据链有效，449项离线一致性检查全部通过。12份完整原生结果对象及6组完整比较可在本地独立重建。

v4本轮6题均生成并执行成功，原生匹配5题、不匹配1题，完整分母6题，匹配率83.33%。相比v3完整80题中相同六题的3/6，本轮恢复0226、0263、0273，保留0368、0586，失去0201，净增2题。该小集结果不能推算v4完整80题分数；v3的49/80保持原始历史记录。

有限修正的效果已经观察到，同时出现了此前明确提示的0201退化。建议保留这次取舍记录，固定v4代码进行一次完整development80生成及独立原生复评，再比较并选择最终候选。无需为了这六题全对而按题号、元素或键型增加特殊规则。保留集继续关闭。

## 报告与来源

| 文件 | SHA-256 |
| --- | --- |
| `m2_public_intent_v4_diagnostics6_server.json` | `20ab65e3b05fb59767a67478ea9d8b5ed426ec9001bb660df9390c2b3023e712` |
| `m2_public_intent_v4_native6_server.json` | `1f7e9f974d678ae118007591b0d2c78d8d8495e4043321077e10627a6895c90a` |

- 两份报告运行状态均为complete、errors为空，目标数据验证成功，未创建或导入数据库。
- 服务器代码绑定均为`4797728132b4f65c9b5d18539d3032dbe2a403d531253e0bacff632761c69769`。
- 96个执行代码文件与v4交付一致；相对v3仅intent.py、relationships.py、units_output.py三个模块变化。服务器Python、依赖、内核等环境元数据与此前一致。
- 完整交付清单131份文件核对通过。生成及复评使用同一个v4策略、代码身份、数据/catalog、权限及原生评分政策。
- 六题顺序、清单摘要、模型配置、七项预算探针、隔离及watchdog探针、生成snapshot内容哈希均核对通过。
- 仅使用toxicology、card_games、codebase_community三个授权来源及对应只读账号。各自索引身份、图字段、关系键及数据/catalog版本分别匹配。
- 三个新索引按v4代码身份创建：card_games 12批、codebase_community 8批、toxicology 2批embedding，共22次共享索引HTTP，与预估一致。
- 生成阶段未执行Gold；Gold只在独立可信复评执行。所有六题runtime、准备连接池及复评连接池已关闭；保留题未开放。

## 逐题结果

| 题目 | v3同题原生结果 | v4原生结果 | chat次数 | 观察 |
| --- | --- | --- | ---: | --- |
| 0201 | 匹配 | 不匹配 | 1 | advisory后保留按关联记录加权的首次SQL |
| 0263 | 不匹配 | 匹配 | 1 | 不再因模糊粒度强制去重，直接保留原始JOIN总体 |
| 0273 | 校验失败、未复评，计0 | 匹配 | 1 | cl/pb冲突显式记录，未再强制pb条件 |
| 0226 | 不匹配 | 匹配 | 1 | 首次即生成NUMERIC运算和ROUND(...,5) |
| 0368 | 匹配 | 匹配 | 1 | 原百分数数值路径保持精确匹配 |
| 0586 | 匹配 | 匹配 | 2 | 首次漏标题列，输出组反馈后补齐 |

### 0201：明确保留的回归风险已发生

v4的entity_grain为advisory/unspecified，公开依据是COUNT(atom_id)。首次SQL通过来源、PostgreSQL及现有公开意图校验，直接执行；它与v3三题诊断中0201的首次被拒SQL字节完全相同。

模型结果：41.196235238637925（`0x1.4991e3c7e22e6p+5`）。冻结参考：38.80961092816197（`0x1.367a154b5784ep+5`）。差异是关联权重与去重原子口径，不是百分数尺度、舍入、版本错配或评分器问题。

0263的公开公式同样写SUM条件/COUNT(atom_id)，也没有明确DISTINCT。当前证据不能提供一个仅凭题目公开语义就必然将两题分到不同参考粒度的可靠规则。不能读Gold后按题号或bond_type选择去重策略。

### 0263：误拒绝已消除并形成新模型成功

v4生成的SQL与三题诊断中首次被拒SQL相同，结果为2.6840451814272206，原生精确匹配参考。未被迫改为EXISTS或COUNT DISTINCT，无重复生成。这是本轮新生成执行成功，未移植反事实得分。

### 0273：冲突处理已进入模型上下文

contract.public_evidence.conflicts记录element的cl/pb值及定义/分子条件角色，resolution为advisory_no_mandatory_conjunction。required_profile_conditions仅保留molecule.label='+'；cl、pb不被合并成强制条件。

模型使用cl条件计数并保留致癌总体，首次原生结果3.1419284940411703，与冻结Gold完全匹配；没有添加pb筛选，也未请求澄清。

### 0226：五位精度在首次生成时落实

precision记录question中five decimal places的原文位置，decimal_places=5、enforcement=hard_for_simple_numeric_output。首次SQL即包含：

```sql
SELECT ROUND(
  CAST(SUM(CASE WHEN bond_type = '=' THEN 1 ELSE 0 END) AS NUMERIC)
  * 100 / NULLIF(COUNT(bond_id), 0),
  5
) AS percentage
FROM bond
WHERE molecule_id = 'TR008'
```

预测和Gold均为原生Decimal('3.84615')。本轮没有触发精度拒绝或在线修复，验证的是精度约定被采用且SQL通过；精度错误的结构化反馈路径已有本地专项测试，不能把本次结果描述为“模型经反馈修复精度”。

### 0368与0586：已有成功保持

0368保留REAL分子乘100后除计数的路径，预测和Gold均为`0x1.b24f870ab2114p-2`。没有新增运算顺序拒绝。

0586首次SQL只投影displayname，被incomplete_participant_context_output拒绝；反馈准确指出缺codebase_community.posts.title。第二次补齐displayname、title，仍使用votes.userid的参与者角色，完整两行原生结果匹配参考。未因ILIKE/LIKE、DISTINCT或重复行形态差异放宽评分。

## 预算及成本

| 指标 | v3相同六题 | v4本轮六题 |
| --- | ---: | ---: |
| 逐题模型HTTP | 25 | 19 |
| 其中chat | 13 | 7 |
| chat输入token（服务返回usage） | 68558 | 37160 |
| chat输出token（服务返回usage） | 1016 | 498 |
| chat总token | 69574 | 37658 |
| 生成侧SQL工具调用 | 10 | 11 |

v4生成侧SQL为5次规范值查询（共7对）及6次结果SQL；独立复评另执行12条SQL，0模型。逐题修复成本下降，但本轮另有新索引22次embedding，因此本次总模型HTTP为41，不能把逐题19次当作完整总成本，也不能据此直接声明实际费用下降。

六题均在既定16次总HTTP、10次chat、3次SQL、每轮3次生成/校验及600秒上限内。未发现传输重试。只有0586发生一次再生成。5题首次校验通过，其中4题首次SQL原生正确；首次校验通过不等于首次原生正确。

## 下一步

保持本次v4代码、配置、模型与预算，做一次完整development80生成和独立原生复评。逐题比较原始34题、v3的49题以及本轮三个恢复题/0201回归，核对其余74题是否受到影响；索引新建与缓存命中成本继续单列。

该完整比较之后选择并冻结最终候选，准备受控holdout30入口和尝试台账。将0201粒度歧义及未解决案例记入遗留项，不把保留集反馈用于继续调参。

机器审查记录：`m2_public_intent_v4_reports_review_local_20261018.json`。本地仅核对文件和完整预览重建，未连接PostgreSQL、调用模型或修改原始报告/生成代码。
