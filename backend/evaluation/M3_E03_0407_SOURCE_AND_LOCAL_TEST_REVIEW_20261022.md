# M3 E03：0407来源依据与本地正反例核查

日期：2026-10-22。范围：只检查 development 公开输入、已受信的 BIRD 源结构与 E02 报告；本次未连接 PostgreSQL、未运行模型、未执行 Gold SQL，也未读取 holdout。参照答案只用于先前 E02 验收审查，不参与本设计判断。

## 来源依据

| 证据 | 观察 | 可支持的结论 |
| --- | --- | --- |
| 冻结的 `card_games/database_description/cards.csv`，SHA-256 `41bc566e91e165f43f7484a1d3d3f17e66094e2c0cc3092829366f6e2f019d23` | `cards.uuid` 被描述为卡牌唯一标识；`subtypes`、`supertypes` 分别是卡牌的子类型、超类型 | 双列输出有公开字段归属，父侧 UUID 唯一性还需受信 DDL 与数据核对 |
| 冻结的 `card_games/database_description/foreign_data.csv`，SHA-256 `ac254726eeb2d0fd574ec64bac31617ac233842623f692469b7569febe9f3310` | `language` 是卡牌外语语言；`foreign_data.uuid` 的描述为空 | 可定位德语筛选列，**不能**从此文件单独证明 `foreign_data.uuid` 指向 `cards.uuid` |
| [E02 离线来源审查](results/m3_e02_condition_relation_review_local_20261022.json)，SHA-256 `d03bcb1e9c384a3237484a7d1574fce6ce1baa257570791ebad794e24aabf472` | 两端 UUID 均为 TEXT，父侧有单列唯一索引，未声明两表外键；229,186条子记录中229,170条可匹配、16条孤儿 | 支持同域候选键的诊断，不构成无损关系或自动 JOIN 依据 |
| [孤儿范围核查](results/m3_e02_card_orphan_scope_local_20261022.json) | 德语记录28,891条，其中3条为孤儿 | 将语言限定为 German 也不能消除不完整性 |
| [E02 候选捕获](../../../m3_e02_pair24_20261022_v5/candidate/backend/evaluation/results/m3_e02_candidate24_capture_server.json) | 0407的授权图已有 `cards.subtypes`、`cards.supertypes`、`foreign_data.language`，但20列已满、缺两端 UUID；当前 `relation_candidates` 为 `eligible=false`，原因 `incomplete_child_key_coverage` | 当前程序没有漏读一条已声明外键，也没有证据可直接升级关系 |

MTGJSON 的[现行 Foreign Data 模型](https://mtgjson.com/data-models/foreign-data/)把外语数据列在卡牌的 `foreignData` 属性下，说明这类数据在概念上属于卡牌；同页也标明 Foreign Data 自身的 `uuid` 字段从 v5.2.2 引入。[MTGJSON v5 更新记录](https://mtgjson.com/changelogs/mtgjson-v5/)记载 v5.3.0 修复过 SQLite `cardForeignData` 的 UUID 不匹配。**据此推断**，现行上游模型不能直接证明 BIRD 冻结库中同名 UUID 的具体生成与连接语义；该库的上游 MTGJSON 版本和转换链尚未被独立绑定。不能把当前网页解释、近乎全部匹配的数据统计或参考 SQL 当成真实外键证明。

## 本地正反例

[专用测试](../tests/test_m3_e03_0407_evidence.py) 共9条，全部通过：

- 真实来源记录：保持 `source_bound=true`、`eligible=false`、`incomplete_child_key_coverage`，记录16条孤儿及缺少归属依据。
- 只补一条人工归属说明仍因孤儿被拒；只假设孤儿消失仍因缺少归属依据被拒。只有**合成测试中同时满足**完整覆盖和独立归属两项才可通过现有门槛；该合成例不描述真实 BIRD 数据。
- 数据版本不匹配被拒；即使合成例通过，也不被标为声明外键或预设 JOIN 类型。
- 0407的原公开 evidence 能按顺序解析出 `cards.subtypes`、`cards.supertypes`。已保存错误 SQL 的投影会收到 `requested_output_not_observed`；观察器不会给出正确性或 EX 结论。
- 只有正确双列投影而没有 German 筛选或关联的 SQL 可以通过投影观察，证明观察结果不能替代完整业务校验。
- 缺少输出组成员或存在冲突定义时，必须保持未解析。

最后一条测试在实现前揭示了一个实际风险：若 `supertypes` 不在授权图，原解析器会丢弃不完整的 evidence 定义，并退回把 `all types` 绑定成 `foreign_data.type`。已在 [output_contract.py](bird/output_contract.py) 做保守修正：保留未完整绑定的公开定义并返回 `incomplete_public_definition`，不再将错误单列报告为已完整解析。此模块仍为开发诊断的可选输出观察器；本次没有打开 E01 输出提示、改变生成预算、校验、Gold 或评分。

相关验证：新专用测试9/9；E02条件关系测试11/11；输出契约相关测试30/30。完整输出契约文件中的另1条旧测试在本机因缺少 `psycopg` 的包元数据，未能运行到其冻结代码身份断言；该错误与本次解析改动无关，不能将完整31条记为通过。

## 后续版本核查补充

[冻结包版本与关系依据核查](M3_E03_0407_VERSION_BOUND_RELATION_REVIEW_20261022.md)从同一 `minidev_0703.zip` 内发现更直接的证据：`dev_tables.json` 标注 `foreign_data.uuid → cards.uuid`，包内 `card_games.sqlite` 的 DDL 也声明该外键。故本记录关于“缺少独立归属依据”的判断已由新证据修正。SQLite 原库有16条此关系的外键违规，其中3条德语记录；PostgreSQL 转储和目标库并未声明该外键。精确 MTGJSON 上游版本仍未知，但冻结 BIRD 包足以给出**有边界的设计关系依据**。以下决定按核查当时的状态保留，实施判断以新核查为准。

## 决定

1. **候选关系暂不升级、暂不向模型展示为可用连接。**先补冻结 BIRD 库的上游版本／转换依据，或其他独立且可复核的 `foreign_data.uuid` 归属证据；同时保留16条孤儿及3条德语孤儿事实。来源证据不足时维持 `diagnostic_unresolved`。
2. **输出字段组识别已有可用的公开依据。**本轮仅修正了不完整证据的误绑定，保留其提示与观察模块关闭状态。0407仍需跨表关系上下文；不能单靠双列提示宣称已经修复 SQL。
3. 下一步若获得可版本绑定的归属依据，再按 [E03 设计](M3_E03_0407_RELATION_OUTPUT_DESIGN_20261022.md)实现低信任关系状态、20字段内键额度决策与输出提示的分项消融，并冻结新身份做服务器同轮对照。E02 六份原始报告保持不变。
