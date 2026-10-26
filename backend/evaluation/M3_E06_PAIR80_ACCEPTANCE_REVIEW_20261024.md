# M3 E06 端点反馈候选 development80 同轮审查

日期：2026-10-24。只读取 `E:\PythonLearn\m3_e06_pair80_endpoint_feedback_v2_20261024_r1` 下九份服务器原始文件和已冻结的 r2 包清单；本次本地审查没有调用模型、连接数据库、重跑或改变评分。它是公开开发集诊断，`formal_benchmark=false`、`holdout_run=false`。

## 结论

**同轮实验执行有效，E06 候选未通过预定的 development80 自动筛选，暂不推广到主线。** 基线与候选均为 **52/80**，净增 0；错转对为 1505、0239，对转错为 0050、0173。原有 20 条回归题为 20/20；历史 M2 v4 成功 50 题中本轮候选保留 49 题，0459 未匹配。0239 的端点反馈确实触发修复，0206 没有误拒，但局部收益没有转成 80 题净收益。

另有基线 1399 的一次模型传输失败事件没有 Token usage。比较报告如实把基线总 Token、chat Token 记为 `null`，`cost_known=false`，自动成本门槛不通过。不能把缺失 usage 填成 0。已知 Token 的数学下界仍可供人工了解成本幅度；不能替代完整 usage 记录。

## 原始证据和身份

| 相对文件 | SHA-256 |
| --- | --- |
| `reports/e06_pair80_preflight_server.json` | `3f96b0cae1ba4d5c0e71adabcafb8c95707f803c090a17c0bd028c2792673a63` |
| `reports/e06_pair80_transport_model_probe_server.json` | `02b6e5307c01bb99545d4935f67c6a1bd7459ee50c8739e74372b9dfb1058d06` |
| `reports/e06_pair80_server.json` | `a9f62a3b91cb46b4583efaa4172ace03ded8f9423081c26d92d0068788054156` |
| `reports/e06_pair80_comparison_server.json` | `ab953d943b69b880061f50ddf4a1078aebbbf16dd0979bd7c6eead25abe324e6` |
| `transport_dependency_lock.json` | `08ded9ec12ff18d2d593a737f54e80996bfdc3e2977bd97c8df45cad3b6037ab` |
| `baseline/backend/evaluation/results/m3_e06_pair80_baseline_capture_server.json` | `7bbd12fc94f24582a26cc54e3beced454dd7bffc5628973dad25511453f2d995` |
| `baseline/backend/evaluation/results/m3_e06_pair80_baseline_native_server.json` | `c037dfe5be2157af8c1e39573c8b73067e7222e73fc9a28ed546db9ce47aa41c` |
| `candidate/backend/evaluation/results/m3_e06_pair80_candidate_capture_server.json` | `2e204fbc10bd9d37bef79caef8bf93a3c45e84b4c9f4def65f37d1960bf0b74c` |
| `candidate/backend/evaluation/results/m3_e06_pair80_candidate_native_server.json` | `283bd2a5b0cfae5b7ddeb5b29fdfbe641a7847738cdb934a0ace827157a24dbd` |

九份文件齐全且 JSON 可解析。包 ID `012c86dbc14a03f6d42aeffaf8d217099febcb6ac1c862b1fc72970e9fd7c7f1` 在预检、模型探针、主报告、比较与连接锁中一致；与本地冻结包清单相同。主报告记录的比较摘要以及主报告/比较报告中的四份子报告摘要，均与上述本地文件逐字节哈希一致。正式流程 12 个子阶段退出码均为 0；两侧捕获先完成，再开始原生复评。预检模型请求 0、生成未预约；独立模型连接探针使用 1 次 embedding 请求，不计入正式对照成本。

两侧选择同一原始 development80 顺序，模型公开配置、协议、数据源绑定、只读角色、SQL 修复和 Schema/意图策略相同。目标物理库为 `askdata_m2_bird`；来源绑定的全局数据版本为 `a8fbe7c8a393d3e61f2880ed75f177b17f8914265bc6a6e16744f632951c6641`，catalog 版本为 `f81bd94d4a761e3720855b8eba4b4a1b6dda0d2a3629ffb8002e987285e66636`。生产代码清单与 r2 冻结包逐文件相符：基线 100、候选 101 个文件，候选只改 `case_worker.py` 并新增 `endpoint_validation.py`。各侧分别构建 8 个索引，缓存命中 0、路径互不相交，8 域来源身份与查询角色一致。8 份实时来源收据均标记验证通过；隔离和超时探针均通过，80 个逐题运行上下文关闭。进程内 DNS/HTTPS 依赖锁与两侧模型事件一致，未变更系统 DNS。本地审查核对的是报告记录及交叉身份，没有再次连接服务器验证源数据。

## 原生复评与逐题变化

| 指标 | 基线 | 候选 |
| --- | ---: | ---: |
| 捕获题数 | 80 | 80 |
| 有最终 SQL，进入无模型原生复评 | 78 | 77 |
| 澄清，计错 | 2：1524、0152 | 3：1480、1524、0152 |
| 原生匹配 | 52 | 52 |
| 原生不匹配 | 26 | 25 |
| 原生 SQL 执行 | 156 | 154 |
| 复评新增模型请求 | 0 | 0 |

两份原生报告均 `complete`、`native_comparisons_complete=true`、`pools_closed=true`、错误为空。原生报告的捕获 SHA、代码/来源身份、逐题 SQL 哈希与捕获一致；80 题映射无遗漏或重复。捕获中的诊断模式没有执行 Gold；原生复评独立执行保存的预测 SQL 和冻结 Gold SQL，未回答题按固定分母计错。比较报告每题布尔结果与两份原生报告重新计数一致。

| 题目 | 本轮变化 | 核对 |
| --- | --- | --- |
| `BIRD-PG-0239` | 错→对 | 基线首次 SQL 用 `atom_id LIKE 'TR%_19' OR atom_id2 LIKE 'TR%_19'`，结果不匹配。候选首次生成相同错误形态；端点校验返回 `explicit_endpoint_widened_by_or`，反馈明确公开指定 `connected.atom_id`、被额外加入的 `atom_id2` 及 `bond_id` 计数指标。第二次 SQL 仅保留 `atom_id LIKE 'TR%_19'`，验证通过且原生匹配。候选 chat/验证尝试由 1/1 增为 2/2，SQL 执行仍为 1。此题修复可归因于反馈轨迹。 |
| `BIRD-PG-0206` | 对→对 | 两侧相同的双端点 `UNION` SQL 均原生正确。候选规则为 `abstain/no_unique_public_endpoint`，无 `candidate_repair`。 |
| `BIRD-PG-1505` | 错→对 | 基线 `COUNT(DISTINCT c.customerid)`，候选 `COUNT(*)`，后者与冻结 Gold 的连接行计数相符。候选端点规则弃权、没有额外修复尝试；不能把收益归因于端点校验。 |
| `BIRD-PG-0050` | 对→错 | 基线的字段顺序与 Gold 相符；候选把学校列放在邮寄地址前，并加入另一份 `schools` 关联，结果元组的两列顺序不符。端点规则弃权，结构校验没有报错。 |
| `BIRD-PG-0173` | 对→错 | 基线按订单 `amount=3539` 取目的字段并匹配；候选误把 `3539` 用作 `order.account_id`，得到空的目的值。冻结 Gold 使用按账户/目的汇总的金额条件。端点规则弃权，结构校验没有报错。 |
| `BIRD-PG-0459` | 历史成功，本轮两侧均错 | 两侧 SQL 相同，额外输出 `convertedmanacost`，而冻结 Gold 只输出 `name`；属于本轮对历史成功题的保持失败，非候选相对同轮基线的新退化。 |
| `BIRD-PG-1480` | 错→仍错，候选澄清 | 基线有可执行但不匹配的 SQL；候选发生 `undefined_column`，随后没有最终 SQL，作为澄清计错。端点规则没有给出拒绝。 |
| `BIRD-PG-0072` | 错→错 | 两侧相同聚合 SQL、均与原生参考不匹配；学校/年份条件和输出形态遗留问题仍在。 |
| `BIRD-PG-0092`、`0356` | 对→对 | 两侧原生正确；候选端点规则弃权。 |

候选共有 80 条端点观察：78 次弃权、1 次 `candidate_repair` 和同一 0239 修复后 1 次通过；唯一的 `candidate_repair` 是 0239。没有观察到其它题被端点规则误拒。20 条预选回归全部保留；历史 50 条成功题保留 49 条。按数据库分组，候选在 `toxicology` 与 `debit_card_specializing` 各 +1，在 `california_schools` 与 `financial` 各 −1，其余不变。

## 请求、预算与成本边界

| 指标 | 基线 | 候选 | 判断 |
| --- | ---: | ---: | --- |
| 正式模型 HTTP 尝试，含独立索引 | 300 | 301 | 候选 +1；两侧各 49 次索引请求 |
| 逐题模型 HTTP 尝试 | 251 | 252 | 候选 +1 |
| 总 Token，含索引 | `null`；已知下界 1,006,995 | 1,019,928 | 基线 1399 有一次传输失败，usage 未知 |
| chat Token | `null`；已知下界 527,802 | 540,735 | 自动 `cost_known=false` |
| 逐题墙钟 p95 | 20.745 秒 | 20.497 秒 | 候选约 −1.20%，但控制器因总体成本未知不标记 p95 成本门槛通过 |

若缺失的基线 usage 非负，候选总 Token 相对基线的增长上界约 1.284%，chat Token 增长上界约 2.450%；这是依据已知下界计算的人工界限，**不补写原报告的 `null`**。基线 1399 的事件标记为 `transport_error`、HTTP 状态空、没有 Token usage，随后题目仍回答并复评。两侧所有逐题模型尝试、SQL 工具调用及耗时均低于既定上限；逐题最大值分别为基线 4 次请求/2 次 SQL 工具调用/33.874 秒、候选 5 次请求/2 次 SQL 工具调用/25.060 秒。原生复评没有模型请求。

比较报告的自动筛选中，0239 正确、候选至少 51/80、20 条回归、0206 正确和未误拒为真；**超过同轮基线、历史 50 条全保留、成本记录完整**为假，故 `automatic_screen_pass=false`。即使 p95 数值本身下降，也不能改变这个结果。保留本轮九份证据，不为追求通过而在同一冻结候选上重跑或修改评分。后续应先离线审查 0050、0173、0459 与新增澄清 1480 的原因，确定另一个独立候选；0239 的窄规则仍是已证实的局部修复，但本轮没有证明其在完整开发集带来净收益。
