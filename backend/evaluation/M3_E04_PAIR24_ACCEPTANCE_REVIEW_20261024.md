# M3 E04：标量计数候选 24 题同轮验收记录

日期：2026-10-24。审查范围为本地下载的九份服务器原始 JSON、冻结题单和交付设计。本次只读取文件，没有连接数据库、调用模型、重跑 SQL 或修改评分。

## 结论

**实验执行及证据链通过核对；E04 候选未通过效果筛选，不接纳推广。**基线和候选均为 22/24，净增 0；目标 `BIRD-PG-0092` 两侧均正确，候选没有触发标量形态校验反馈。20 道预选成功回归题全部保留。两侧共同失败的是 `BIRD-PG-0072` 与 `BIRD-PG-0239`，详见 [两题离线语义审查](M3_E04_0072_0239_OFFLINE_SEMANTIC_REVIEW_20261024.md)。

这只是开发集 24 题的工程筛选：`formal_benchmark=false`、`holdout_run=false`。不把 22/24 写成正式 EX 或未见数据准确率，不因本轮结果改变 Gold、原生比较、题单或预算。

## 原始证据和身份

原始文件根目录：`E:/PythonLearn/m3_e04_pair24_scalar_count_20261024_r2/`。以下文件保持原样，SHA-256 按本地字节重新计算：

| 文件 | SHA-256 |
| --- | --- |
| `reports/e04_pair24_preflight_server.json` | `a75ed71a2a6c2b48a8c1b50b75c7d9f607994528c08eb97519404bd99bd5fd64` |
| `reports/e04_pair24_transport_model_probe_server.json` | `d5f9bd623963356a138208643ffb01b0e055d295a421a9716323b0797bb54c5d` |
| `reports/e04_pair24_server.json` | `77a3396ee30aaa3cdb86a3721fe1e708570b9487f9e1195cb90ea54da2597751` |
| `reports/e04_pair24_comparison_server.json` | `ac35c51e33460456ab323685131dfbe1fed6430f3909373008228e281626f64d` |
| `transport_dependency_lock.json` | `0c65e8c8413613d5e5364ab6a34b4fc67256dcecaf24723fd2fc3a5011aa5bd3` |
| `baseline/backend/evaluation/results/m3_e04_pair24_baseline_capture_server.json` | `47cb12175bd5e0278bae214c417554d274c645918db4b0374f7a749d2987aaf5` |
| `baseline/backend/evaluation/results/m3_e04_pair24_baseline_native_server.json` | `beddc41c3033df335396fdbd6078548019ac755bd34d292245535cedb935c4d4` |
| `candidate/backend/evaluation/results/m3_e04_pair24_candidate_capture_server.json` | `a4ede17c434aad8d0e7145f4574e8a8ff812228263841cbb25f207a39a7b4578` |
| `candidate/backend/evaluation/results/m3_e04_pair24_candidate_native_server.json` | `d2fb7f64222d2b994ae256494edef017121736781c2ab5bd897e14049c1a9438` |

包身份 `c57344fe558c72d03eb27da90a84a528987f8e84803205b9bed3d2b7c971019b` 与总控、对照、预检、连接探针及依赖锁一致。总控引用的四份子报告摘要和比较报告摘要均与本地原文件匹配；原生复评引用的捕获摘要也匹配。12 个正式子阶段退出码均为 0，两侧捕获均完成后才执行原生复评，复评文件没有重用旧结果。

两侧题目顺序、协议 SHA-256 `174a4d909131d0b8333d446f5bcb0815fe27ec6023a98e51729f3096f975ac77`、来源数据和 catalog 版本、8 域只读角色、模型公开配置与预算一致。基线代码身份为 `4b69ca1fc60e59cdaa3fd8912b4cc0dc0e5dec39a61c64f306636cc0bab05146`，候选为 `246e31bc1509052aee224cde21bd172e71031c1efea194053d16463e73120df5`。两侧各自构建 8 个独立索引，缓存命中均为 0。原生复评记录的连接池均已关闭。

预检完成且新增模型请求为 0；独立模型连接探针完成，使用 1 次请求。正式运行的两侧各 49 次建索引请求和 78 次题内请求，总计每侧 127 次。24 道题在两侧均 `diagnostic_answered`，运行时均关闭；报告没有顶层错误。原生复评每侧覆盖 24/24，排除 0，各执行 48 次 SQL，新增模型请求为 0。其固定比较是原生元组集合，不比较列名、顺序或重复次数，也不增加四舍五入或类型转换。

## 逐题结果与成本

| 类别 | 基线 | 候选 | 审查 |
| --- | --- | --- | --- |
| 0092 目标题 | 正确 | 正确 | 两侧 SQL 相同，均为一行一列；候选未产生标量形态拒绝或修复。 |
| 0072 边界题 | 错误 | 错误 | 两侧结果均为一个 `NULL`；Gold 为两行数值。候选学年字面值已与公开问题一致，但城市字段和输出形态仍有问题。 |
| 0356 边界题 | 正确 | 正确 | 两侧 SQL 与原生结果一致。 |
| 0239 边界题 | 错误 | 错误 | 两侧 SQL 相同，预测计数 754，Gold 计数 377。 |
| 20 道回归题 | 20/20 | 20/20 | 没有对转错。 |

两侧原生匹配均为 22/24；错转对、对转错和授权 Schema 上下文发生变化的题目清单均为空。比较报告的自动筛选失败项是“候选超过同轮基线”，因此 `automatic_screen_pass=false`，`acceptance=manual_semantic_review_required`。该状态表示需要人工审查边界题，并不代表候选已获接纳。

| 成本 | 基线 | 候选 | 变化 |
| --- | ---: | ---: | ---: |
| 含索引模型 HTTP 尝试 | 127 | 127 | 0 |
| 含索引总 Token | 341,026 | 344,089 | +0.90% |
| 聊天 Token | 175,246 | 178,309 | +1.75% |
| 逐题耗时 P95 | 21.929 秒 | 21.818 秒 | −0.51% |

成本在预定筛选范围内，但没有正确性增益。0092 的结果不能证明新规则有益：基线已经正确，候选只在一次生成和一次校验后直接通过。0072 被候选归为硬性单值计数，然而冻结参考返回两行，暴露出此规则的适用边界。

## 处置

保留九份原始文件与本记录，不将 E04 候选并入主运行链路，不重复运行已完成的 24 题或已观察的 holdout。下一步先做 0072、0239 的离线语义审查，区分字段检索、公开条件角色与参考输出形态，再决定是否设计新的独立候选。任何新候选只用公开问题、evidence 与授权来源信息决定行为；Gold 和原生结果只供离线审查与验收，不进入模型上下文或运行时规则。
