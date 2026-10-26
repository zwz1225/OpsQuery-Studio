# M3 E03：0407 冻结来源版本与关系依据核查

日期：2026-10-22。范围：BIRD Mini-Dev `minidev_0703.zip` 的公开结构、SQLite 原库、PostgreSQL 转储及既有 M2/M3 审查报告。未运行模型、Gold SQL、PostgreSQL 查询或 holdout。

## 来源绑定

| 材料 | 固定证据 | 结论 |
| --- | --- | --- |
| `minidev_0703.zip` | SHA-256 `aeb211c0e39010bbdae3838bb5e8bd27dc446ed77495b1709f85ccc9bf67f2be` | 同一下载包同时包含 SQLite 原库、`dev_tables.json` 和 PostgreSQL 转储；包名和文件时间不能当作 MTGJSON 版本 |
| 包内 `MINIDEV/dev_tables.json` | SHA-256 `48aa9febe7282d1690f3ed1f222dc040c182df83812ba4e9bee956084d99c8ff`；与 M2 导入清单登记及本地解压件一致 | `card_games.foreign_keys` 有索引对 `[82, 72]`，分别是 `foreign_data.uuid` 和 `cards.uuid` |
| 包内 `card_games.sqlite` | SHA-256 `c98bdb57fe7474da798b407785544b9af0daaad5d61fd21e2a73309493bc1227`；只读打开并执行 `PRAGMA foreign_key_list(foreign_data)` | 原始 SQLite DDL **声明** `foreign_data.uuid REFERENCES cards(uuid)`；`cards.uuid` 声明唯一 |
| 包内 PostgreSQL `BIRD_dev.sql` | M2 导入清单 SHA-256 `31b1da211849d24a57c9af7636da46a5b82fc8a3ca1542bb3ebd8775e9a31cec`；dump 头部为 PostgreSQL 14.12 | PostgreSQL 转储及已验收目标库**没有**这条外键；14.12 是导出数据库版本，不是卡牌数据版本 |

包内 `dev_tables.json` 的哈希由压缩包内容直接计算，且与本地提取文件一致。M2 [导入清单](results/m2_b_source_server_20261015/import_manifest.json)登记了同一结构文件及转储哈希；M2 [目标验证报告](results/m2_b_postgres_validation_server.json)记录当前 PostgreSQL 来源。

## 约束与数据并存的事实

只读检查 SQLite 原库得到：`cards` 56,822 行、`foreign_data` 229,186 行；后者有 **16** 行找不到 `cards.uuid`，其中 **3** 行语言为 German。`PRAGMA foreign_key_check` 共报 88 个违规，其中该表 16 个。SQLite 中“声明了外键”与“所有行满足外键”是两件事。相同的 16/3 孤儿范围也出现在既有 [E02 来源审查](results/m3_e02_condition_relation_review_local_20261022.json)和[专项核查](results/m3_e02_card_orphan_scope_local_20261022.json)中。

BIRD [项目说明](https://github.com/bird-bench/mini_dev)将 SQLite 库作为包内数据库内容，PostgreSQL 是另行构建的版本。当前 [MTGJSON Foreign Data 文档](https://mtgjson.com/data-models/foreign-data/)说明外语记录属于卡牌模型，但没有给出这份冻结 BIRD 库所用的 MTGJSON 修订、导出脚本提交或 UUID 生成链。包内结构、README、SQLite `user_version`/`application_id` 和 PostgreSQL dump 头部均未标出该精确上游版本。因此**上游 MTGJSON 版本仍未查明**，也不能以现行 MTGJSON 文档替代冻结包的关系依据。

## 对 0407 的决定

1. **归属依据已找到**：冻结 BIRD 包自身的 SQLite DDL 与结构注解独立于题目 Gold，且两者一致，足以支持 `foreign_data.uuid` 与 `cards.uuid` 是设计上的关联键。此前“没有独立字段归属证据”的判断应更正。
2. **完整性仍不成立**：当前 PostgreSQL 没有该外键，冻结源数据有 16 条孤儿，其中 3 条是 German。不能把候选展示为 `declared_fk`、完整参照、无损连接或预设 `INNER JOIN`。
3. **下一实现阶段可评估 `reviewed_incomplete_candidate`**：必须绑定已验证的 `card_games` 来源身份、只读权限、数据和 catalog 版本，显式携带 SQLite DDL/`dev_tables.json` 来源及孤儿统计；通过 20 字段额度保护与正反例测试后，才允许作为低信任关系上下文进入模型提示。版本不匹配、授权缺失或候选路径歧义时保持诊断态。
4. 本轮仅完成证据核查并更新文档。`reviewed_relations.py` 中的 0407 记录和生成链路尚未改变；E02 六份原始报告保持不变。
