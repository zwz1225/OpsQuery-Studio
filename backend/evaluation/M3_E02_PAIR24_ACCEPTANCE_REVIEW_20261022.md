# M3 E02：24题同轮对照与1479人工语义审查

日期：2026-10-22。范围：已保存的 E02 development24 服务器报告。审查仅在本地读取六份 JSON、公开 question/evidence 和冻结 Gold SQL；没有重新生成、连接数据库、改写评分或使用 holdout。

## 1. 证据与执行完整性

六份服务器原始报告存放于 `E:\PythonLearn\m3_e02_pair24_20261022_v5\` 的原目录，保持不变。文件字节 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| `reports/e02_pair24_server.json` | `71c3cfb6bf9359c89afd26c9183356de8dfd101f894c2544abdf5bc85fb36d8e` |
| `reports/e02_pair24_comparison_server.json` | `d4e70cdba46cce6ad1b3c13fa81e7edf193d66cba3d92fda0184fe4a17aa3e11` |
| `baseline/backend/evaluation/results/m3_e02_baseline24_capture_server.json` | `b97756e8a8b6214d56d2b30e25ab87d8b5052ce9c57c2d33bf304b91a70b7590` |
| `baseline/backend/evaluation/results/m3_e02_baseline24_native_server.json` | `8bd16d7f8b3380e656b2c7fca7b03859aeb0ceaf3165fc0bcc0d134974838eb4` |
| `candidate/backend/evaluation/results/m3_e02_candidate24_capture_server.json` | `3bb8bf209b91becc9f19fa467f640e027f18121f1995513e9dd814e3613dc05f` |
| `candidate/backend/evaluation/results/m3_e02_candidate24_native_server.json` | `4475360425936aeafdd33029fd5801eeffb0b1bbdbf37e947fba7b72c4ab75ce` |

总控与对照报告均为 `complete`，无错误；总控登记的四份子报告和对照报告摘要与本地文件一致。两侧24题题单、协议、来源版本、授权角色映射和模型配置相同，代码身份分别冻结。两侧各独立构建8个索引，索引缓存命中均为0；各生成24/24、运行上下文均关闭。两份生成完成后才进行独立原生复评；复评各24题、排除0题、0次新模型请求、连接池均关闭。生成时两侧 PostgreSQL 目标验证、隔离及超时探针均通过。总控中的 `live_readiness_verified=false` 是启动前静态预检字段，不能替代后续实时来源验证字段。

## 2. 预登记24题筛查

| 指标 | 基线 | 候选 | 结果 |
| --- | ---: | ---: | --- |
| 完整原生匹配 | 20/24 | 21/24 | 净增1题 |
| 错转对 | — | `BIRD-PG-1479` | 仅此1题 |
| 对转错 | — | 0 | 20道原成功回归题全部保持 |
| 含独立索引构建的模型 HTTP 尝试 | 126 | 126 | 相同 |
| 含独立索引构建的模型 token | 330,064 | 337,703 | 增加7,639，约2.31% |
| 逐题耗时 p95 | 19.874秒 | 19.479秒 | 候选较低 |

预登记的7项自动筛查全部为真，`automatic_screen_pass=true`。这是一次受控开发集工程对照；`formal_benchmark=false`、`holdout_run=false`。24题差值不能外推为总体准确率提升或统计显著性。

## 3. BIRD-PG-1479 人工语义审查

公开问题是“Which year recorded the most consumption of gas paid in CZK?”；公开 evidence 只说明 `yearmonth.date` 的前4个字符表示年份。币种 `CZK` 的依据来自问题，不是冻结答案。

基线授权图只有 `yearmonth.consumption`、`yearmonth.date`，没有连接边。生成 SQL 未筛选币种，还额外输出总消费量；原生复评为1行2列，不匹配冻结 Gold 的1行1列。

候选图保留上述两列，另补入 `customers.currency`、`customers.customerid`、`yearmonth.customerid`。条件记录把公开短语 `paid in CZK` 绑定到授权的 `customers.currency`；同时附上来源绑定的 `customers.customerid = yearmonth.customerid` 候选关联。该关联在冻结数据中父键唯一、两端类型兼容、子表383,282行均匹配、孤儿及空键均为0，但**不是声明外键**，也没有预设连接类型。

候选首次生成并通过校验的 SQL 以 `yearmonth` 关联 `customers`，使用 `c.currency = 'CZK'` 筛选，按 `SUBSTRING(ym.date FROM 1 FOR 4)` 分组，按 `SUM(ym.consumption) DESC NULLS LAST` 排序并 `LIMIT 1`，只输出年份。它与公开问题的筛选人群、度量、年度粒度和返回形态一致。独立原生复评的完整结果为1行1列 `2013`，与冻结 Gold 的完整原生元组集合相同；没有依赖预览截断、列别名或评分放宽。候选此题1轮 SQL、1次校验、1次执行。

**人工语义审查结论：1479通过。**它支持“明确公开条件＋已审查同来源关系＋有界字段补充”在本题提供了有效上下文；不能据此把该候选关系提升为数据库外键，或宣称所有类似币种题都会改善。自动筛查和本项人工审查共同构成 E02 这轮 development24 的通过结论；尚未决定生产推广或运行完整 development80。

## 4. 0407与其他遗留

`BIRD-PG-0407` 两侧均输出 `SELECT DISTINCT fd.type ... WHERE fd.language = 'German' AND fd.type IS NOT NULL`，原生复评均不匹配。公开 evidence 指定的输出是 `cards.subtypes` 与 `cards.supertypes`，两列均非空；当前 SQL 只有 `foreign_data.type` 一列。两端 `uuid` 未入授权图，候选关系也未被自动接纳：冻结数据中 `foreign_data` 有16条孤儿记录，其中3条为德语行。0407的关系和输出缺口按独立设计处理，见 [M3_E03_0407_RELATION_OUTPUT_DESIGN_20261022.md](M3_E03_0407_RELATION_OUTPUT_DESIGN_20261022.md)。

0050和0085在本轮仍未通过；本轮不据此修改 E02 门槛，也不追加模型尝试。继续保存六份原始报告及本记录，下一次实验采用新的候选身份与报告文件名。
