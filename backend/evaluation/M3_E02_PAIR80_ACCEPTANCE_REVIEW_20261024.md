# M3 E02：development80 同轮对照最终审查

日期：2026-10-24。仅在本地读取服务器下载的原始报告、冻结交付包与历史 M2 v4 原生复评；本次审查没有连接数据库、调用模型、重跑题目或改动评分。

## 结论

**实验执行有效，E02 候选未通过完整开发集筛选，不接纳推广。** 基线和候选均为 50/80，净增 0；1479 从错到对，0092 从对到错。历史 50 道成功题保留 49 道，预选 20 道回归题保留 20 道。预登记门槛中“候选至少 51/80”“超过同轮基线”“历史成功 50 道全保留”均未通过。

本轮是受控开发集对照，`formal_benchmark=false`、`holdout_run=false`。不把 24 题 E02 的局部收益外推为 80 题收益，不重跑已观察的 holdout，也不改变 Gold、原生元组集合比较、预算或题单。

## 原始证据与身份

本地原始根目录：`E:/PythonLearn/m3_e02_pair80_process_dns_v1_20261024_r1/`。以下文件保持原样；SHA-256 均已按字节重新计算。

| 文件 | SHA-256 |
| --- | --- |
| `reports/e02_pair80_preflight_server.json` | `0b8b19fe2a801bd0520e9859ae4d5739d3a33aac9304859031be3f7b0168e072` |
| `reports/e02_pair80_transport_model_probe_server.json` | `425966749e94261341b20e2e797e02d384aaaab2aa0987bfae4d41b37356e5db` |
| `reports/e02_pair80_server.json` | `89cc55228bb39762ee6217d2220c8bf2028ecb0fd6e691214aeb4b29085d838a` |
| `reports/e02_pair80_comparison_server.json` | `bc2556b81b19b2e56e01f4f7b4ab379131971982bf979c0af63453ec39a7fb18` |
| `baseline/backend/evaluation/results/m3_e02_pair80_baseline_capture_server.json` | `6ff077418d6ab841772f85ec08a0cd7dc85c101091e30d3be71a60d66ec176a0` |
| `baseline/backend/evaluation/results/m3_e02_pair80_baseline_native_server.json` | `fbbaea474e3fa3f28e00e1930e04a4ca38ff2d9c3bbd7f2e4541f3e68332aecf` |
| `candidate/backend/evaluation/results/m3_e02_pair80_candidate_capture_server.json` | `aef227e08d14cb6e903df2a71b2a1b8615901febe3788453af1bd12462068ff8` |
| `candidate/backend/evaluation/results/m3_e02_pair80_candidate_native_server.json` | `0419fe886890d6e0fcc55e04a1cf19204d8e4bb1a0bbe7c7dabe987643f0ba6f` |
| `transport_dependency_lock.json` | `5f215adc348cfd1b01fc89610a8e9cebb514f4cbb34bc5c06d749da089b05055` |

交付包 ID `3288d878d8d466104b57f561e3dc3c344fde21597c998285dd748208ea700797` 与各控制报告及本地冻结包清单一致。比较报告登记的四份子报告摘要、总控登记的四份子报告摘要、两份原生复评登记的捕获摘要与实际文件均一致；总控登记的比较报告摘要也一致。全部 12 个正式子阶段退出码为 0。两侧捕获完成后，才开始原生复评；原生报告均非重用缓存。

两侧选择同一 80 题顺序，协议、来源绑定、8 域只读角色、模型配置一致；代码身份不同。候选相对基线修改 4 个已有生产文件（`case_worker.py`、`diagnostic_runner.py`、`intent.py`、`retrieval.py`），增加 `demand_relations.py` 与 `reviewed_relations.py`。两侧各独立构建 8 域索引，记录的索引缓存命中均为 0。8 域实时来源收据均标记验证通过；两侧捕获中的隔离及超时探针均通过。这里核对的是报告内记录及其交叉身份，没有重新连接服务器复测数据或重新读取服务器索引文件。

传输锁记录 `/usr/bin/dig` 版本 `9.18.39-0ubuntu0.22.04.7-Ubuntu`、二进制 SHA-256 `421932872b073d8749d56c567319945b7f7bdfd42e705f1e6e2e2f461511c177`，进程内使用解析器 `114.114.114.114`，未修改系统 DNS。锁与总控、两侧捕获及本轮 600 条模型事件的绑定一致。预检新增模型请求为 0，独立传输探针请求为 1；正式生成每侧 251 次逐题请求和 49 次索引请求，合计每侧 300 次。600 条事件均记录 HTTP 200、TLS 验证通过及完整使用量。正式捕获逐题模型请求不超过 16、SQL 工具调用不超过 3、单题耗时不超过 600 秒。

## 独立原生复评与计数

| 指标 | 基线 | 候选 |
| --- | ---: | ---: |
| 捕获题数 | 80 | 80 |
| 进入原生复评 | 77 | 78 |
| 排除（计错） | 0639 重复 SQL、1524/0152 澄清 | 1524/0152 澄清 |
| 原生匹配 | 50 | 50 |
| 原生不匹配 | 27 | 28 |
| 原生 SQL 执行 | 154 | 156 |
| 复评新增模型请求 | 0 | 0 |

两份原生复评均 `complete`、`native_comparisons_complete=true`、`pools_closed=true`。原生复评只对捕获中有最终 SQL 的题执行预测 SQL 与冻结 Gold SQL；其余题计为失败。逐题预测 SQL 摘要与捕获 SQL 一致，复评保存的 Gold SQL 摘要与实际执行的冻结 Gold SQL 一致。捕获报告中 `gold_sql_sha256=null`、`gold_executed=false` 是诊断模式设计，并非来源丢失。

本地按复评结果重算 80 题，得到基线 50、候选 50、错转对仅 1479、对转错仅 0092。冻结包的 `historical_success50_ids` 与本地原始 M2 v4 原生复评中的 50 个成功 ID 一致；该原始报告 SHA-256 为 `1bbb278d0a5ffb99b3049faff6e1da2c482230284188e71e8d4fb44504c38774`。按冻结清单重算，历史成功题仅 0092 回归，20 道指定回归题全部保持。当前配对捕获自带的 `historical_baseline` 字段对应另一项旧诊断观察，不能替代冻结的 50 题清单。

## 关键逐题证据

- **1479，错转对。** 基线仅取 `yearmonth` 年份与消费总和，没有 `CZK` 筛选，还额外输出总消费量；候选授权字段补入 `customers.currency` 及两侧 `customerid`，首次 SQL 关联两表、筛选 `c.currency='CZK'`、按年份汇总和降序取一项，只输出年份。原生比较由不匹配变为匹配。授权字段变化由公开问题“paid in CZK”和同来源已审查关联支持。
- **0092，对转错。** 两侧授权字段及声明关联相同；候选没有新增字段或关联。基线首次 SQL 返回一个 `COUNT(DISTINCT district_id)` 总数，原生匹配。候选首次 SQL 加入 `GROUP BY d.district_id,d.a11`，把薪资条件放入 `HAVING`；执行成功且现有结构校验通过，但产生 69 行（不同元组值为 `1`），参考为单行 `69`，原生不匹配。可以确定缺少对明确标量计数输出粒度的约束；现有证据不能证明某条新增提示单独导致模型采用分组写法。
- **0407、0085** 两侧仍未匹配，不能计入本次收益。0407 仍未输出公开 evidence 要求的 `cards.subtypes` 与 `cards.supertypes` 双列；0085 仍缺公开问题要求的百分比计算。
- **1481、1505** 的授权图发生变化，但本次仍未原生匹配；不能把图变化计作正确性收益。

## 成本和筛选

| 指标 | 基线 | 候选 | 变化 |
| --- | ---: | ---: | ---: |
| 含索引的模型 HTTP 尝试 | 300 | 300 | 0 |
| 含索引的模型 Token | 972,474 | 1,004,115 | +3.25% |
| 聊天 Token | 493,281 | 524,922 | +6.41% |
| 单题耗时 P95 | 19.963 秒 | 19.757 秒 | −1.03% |

以上成本已从两侧索引及逐题模型事件重新相加；P95 已从逐题耗时按原控制器采用的最近秩位置重新计算。聊天 Token 与 P95 均在预登记的 20% 成本阈值内，但准确率门槛和历史成功题保持门槛未通过。

## 后续处理

保留冻结包、九份原始文件及本审查记录。E02 候选不进入生产或正式保留集复测。下一项独立设计聚焦**公开问题明确要求一个计数时的输出粒度**：先用 0092 和正反例做无模型结构检查，再决定是否形成带独立身份的新候选。规则只读取公开题目与授权 SQL 结构，不能读取 Gold、得分或 case ID；不得自动改写 SQL、放宽原生比较或扩大预算。
