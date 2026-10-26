# M3 E05：公开端点候选 24 题同轮验收记录

日期：2026-10-24。审查本地下载的九份服务器原始 JSON，根目录 `E:/PythonLearn/m3_e05_pair24_endpoint_scope_20261024_r1/`。只读取报告，没有重新调用模型或数据库，也没有修改评分。

## 结论

**实验运行与证据链通过核对；E05 候选未通过效果筛选，不接入主链路。**基线与候选均为 22/24，净增 0；两个共同失败题是 `BIRD-PG-0239` 和 `BIRD-PG-0072`。20 道预选成功回归题全部保留。0239 的公开端点契约已生成，但首次 SQL 仍扩成双端点查询，校验通过后直接执行；因此没有触发 SQL 修复。此轮为开发集工程对照，`formal_benchmark=false`、`holdout_run=false`，不能表述为正式 EX 或未见数据准确率。

## 九份原始证据

| 相对路径 | 本地 SHA-256 |
| --- | --- |
| `reports/e05_pair24_preflight_server.json` | `c337579826739b1856a39b38f03f69c5e16bbc01920f57b2d7a2fe0ff231ac21` |
| `reports/e05_pair24_transport_model_probe_server.json` | `ec64f2a48f620666bc156a500a2187a97972e59e634cde850221411053ca634a` |
| `reports/e05_pair24_server.json` | `25fb0e992ebac77f0ed15ef07f809731544c718ad972972d07cbc50ea5164ef2` |
| `reports/e05_pair24_comparison_server.json` | `08fb16e2d8a95f2f078e79a2ffa303ebb80fea62f54dfca4fe0fd05a59e83247` |
| `transport_dependency_lock.json` | `c7aa7b588a4acfd592d4ec4d1f14726c8d8c4d8efad1b67f28ee1bd5747a3dce` |
| `baseline/backend/evaluation/results/m3_e05_pair24_baseline_capture_server.json` | `df34944e6ddbfa839d6c4292bc475b53b1fc83dc38f166ca0c953dae0fc6c2e7` |
| `baseline/backend/evaluation/results/m3_e05_pair24_baseline_native_server.json` | `8807af787636b007c9eec49653673cbde7e560d4d7160d41c004084dd7075c34` |
| `candidate/backend/evaluation/results/m3_e05_pair24_candidate_capture_server.json` | `c119587d66b557edff8178d3f9d098e2b4a682f0c7c2247e4668fa583ebba783` |
| `candidate/backend/evaluation/results/m3_e05_pair24_candidate_native_server.json` | `af27d02bfc1f86c2f4095381b4d3c31c318390c22fb8a21259e444f22b006377` |

包 ID `456e1aae181956c8e28c2193b71f8a750e50f8bc5a738043e8ec5de11b192a53` 与总控、比较报告、依赖锁及本地冻结清单一致。总控和比较报告引用的四份捕获/复评 SHA-256 均与本地字节一致；总控引用的比较报告 SHA-256 也一致。12 个正式子阶段退出码均为 0，基线和候选捕获都完成后才开始无模型原生复评，复评报告均未重用旧文件。

## 来源、执行与预算

两侧固定题目顺序一致，24 道题都 `diagnostic_answered`，执行成功、无逐题错误且运行时关闭。原生复评每侧完整覆盖 24/24，排除 0；每题分别执行保存 SQL 和冻结 Gold，共 48 次 SQL/侧，新增模型请求 0，连接池关闭。两侧复评使用同一原生比较策略，24 道 Gold SQL 摘要逐题一致；复评均引用各自捕获报告的 SHA-256。

两侧来源绑定、公开模型配置、Schema 选择策略、SQL 修复策略和传输策略一致。8 个数据库域各自使用对应 `askdata_m2_ro_*` 只读账号及正确来源身份；逐题隔离记录显示项目文件、环境凭据和直接数据库访问均不可用。两侧各建 8 个来源绑定索引，缓存命中均为 0。基线代码身份 `4b69ca1fc60e59cdaa3fd8912b4cc0dc0e5dec39a61c64f306636cc0bab05146`，候选 `f03a14dd68c0319476abb380d87fe5beeea13b10d26e71d06c27dec6e6c8fd69`；候选仅修改 `evaluation/bird/intent.py`，新增 `evaluation/bird/endpoint_scope.py`。

静态和 DNS/HTTPS 预检完成，模型请求 0；模型连接探针完成，用 1 次 embedding 请求，返回 10 个 1024 维向量。锁定的 DNS 工具摘要 `421932872b073d8749d56c567319945b7f7bdfd42e705f1e6e2e2f461511c177` 在两侧预检、探针和正式总控中一致，没有修改系统 DNS。正式捕获模型 HTTP 尝试：基线索引 49 次、逐题 77 次，合计 126；候选索引 49 次、逐题 76 次，合计 125；总控登记 251 次，不包含独立模型连接探针。

| 成本 | 基线 | 候选 |
| --- | ---: | ---: |
| 含索引总 Token | 332,501 | 329,205 |
| 聊天 Token | 166,721 | 163,425 |
| 含索引 HTTP 尝试 | 126 | 125 |
| 逐题耗时 P95 | 19.698 秒 | 19.304 秒 |

成本未超出预定 20% 边界，但正确性没有增益。

## 逐题语义核对

- **0239 目标失败。**候选 `intent_contract.explicit_endpoint_scope` 明确包含 `toxicology.connected.atom_id`、`bond_id`、`LIKE 'TR%_19'`，且标为 `advisory_only`。两侧授权 Schema 图均含 `connected.atom_id`、`atom_id2` 和 `bond_id`。两侧第一轮都生成 `SELECT COUNT(*) FROM connected WHERE atom_id LIKE 'TR%_19' OR atom_id2 LIKE 'TR%_19'`，第 1 次校验通过、第 1 次 SQL 执行成功，没有修复轮。原生比较的预测计数均为 754，冻结答案计数为 377。观察结论是**提示送达，但未改变模型选择**；不能把这次失败归因于字段未授权或 SQL 执行错误。
- **0072 边界失败。**候选端点契约为 `none`。两侧授权 Schema 图均有 `schools.school`，却没有 `schools.City`；模型仍把 Fremont 筛成 `schools.school='Fremont'`，返回单个 `NULL`，冻结答案为两行数值。候选只是给聚合列增加别名，没有解决城市字段选择和输出形态问题。本规则本来不覆盖此题。
- **0092、0356 边界通过。**两侧原生匹配均为 true；候选端点契约均为 `none`。
- **0206 合法双端点通过。**候选端点契约为 `none`，SQL 仍通过 `UNION` 查询 `connected.atom_id` 与 `atom_id2`，原生匹配为 true；本候选没有误拒双端点任务。
- **成功回归 20/20。**候选没有对转错。24 题中有 5 题 SQL 文本发生变化，其中 0072 仅增加输出别名；0239 的 SQL 与基线完全相同。两侧无授权 Schema 上下文变化。

## 处置

比较报告中 `target_0239_native_correct=false`、`candidate_exceeds_same_round_baseline=false`，因此 `automatic_screen_pass=false`。保留九份原始文件和此验收记录，不推广 E05，不为这次相同结果重复运行既有 24 题或已观察的 holdout。下一项可在离线阶段研究如何把明确的公开端点绑定转为可解释的校验反馈，同时先验证其不会误拒 0206 等双端点任务；0072 另行处理城市字段检索和结果形态。
