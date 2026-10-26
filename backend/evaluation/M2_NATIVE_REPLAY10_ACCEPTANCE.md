# M2：复用 10 条已生成 SQL，进行无模型原生复评

日期：2026-10-17。策略：`bird_captured_development_native_replay_v1`。

## 目标与范围

本轮先把真实错误清单固定下来，供后续通用修复使用。源报告为已核对的：

`evaluation/results/m2_schema_coverage_diagnostics14_server.json`

其 SHA-256 必须为：

```text
4f08270884badfe30d896d5c5ac55c84a7eee1c1060891c2846a452949a4512a
```

仅选择报告中实际执行完成的 10 题，保留预测 SQL 原始字节：

0050、0095、1473、0036、0082、1486、0159、1405、0368、0766。

1435、0201、1399、0586 没有实际执行 SQL，作为四个澄清排除项单独记录。复评不替它们编造答案，不把“已执行 10 题”的匹配数当作 14 题或完整 development80 的成绩。

## 实现

新增 `evaluation/bird/replay.py` 和入口 `scripts/rescore_m2_development10.py`。

1. 先检查源文件完整字节、开发集成员、题号与数据库、退出状态、完整结果记录以及预测 SQL 的执行事件/原文/hash。
2. 核对源报告来源绑定、生产代码身份摘要，以及执行器、SQL 策略、原生结果、预算与评分代码未变化。
3. 通过既有只读 Registry，为六个涉及的数据库域重新验证权限、结构、typed 数据版本和内容守卫；每题来源身份须与捕获报告一致。
4. 每题原样执行预测 SQL 和冻结 Gold SQL，共 20 次业务 SELECT。运行时原有 EXPLAIN、结构/数据校验另行正常执行。
5. 在原生值上使用冻结 tuple-set 谓词比较完整结果，再生成带类型的 JSON 预览。列名、行顺序、重复行数按原评分规则处理；不增加类型强制相同、数值舍入、误差容忍或别名规则。
6. 独立检查重放结果摘要是否与原报告一致。如果不同，记录 `captured_native_diagnostic_preserved=false`，不把新结果冒充原记录；需进一步判断并列排序或运算路径等原因。
7. 保存每题差异及 `fixed_error_list`。该字段表示固定下来的本轮差异清单，不表示 SQL 已修好。
8. 无论成功或失败均执行连接池关闭。中途查询失败会保留已执行结果、Gold 尝试状态、错误类别及预算；未比较成功的题目不会被补成“答案不正确”或“匹配”。

这是可信审查过程：不创建 Agent，不调用模型，不读取模型 `.env`，不构建索引，不修改数据、原题集或 Gold。Gold 和参考分析只进入这份审查报告，不传给后续模型输入。

## 差异与线索如何区分

`native_comparison` 是真实原生结果比较，记录：

- 是否匹配 Gold；预测/Gold 的行数、列数和去重 tuple 数。
- 列数差异、空集与非空集差异、缺失或多出的 tuple。
- 结果类型集合是否不同。类型不同本身不改变冻结比较谓词。
- 双方最多 5 行差异预览，各自最多 65,536 UTF-8 字节，明确标记省略；比较使用完整结果，不使用预览。

`reviewer_hypotheses` 是参考 SQL 的结构线索，包括 NULL 排序、投影、WHERE 字段、关联表与字面量差异。它们标为 `trusted_reviewer_only_not_model_feedback`、`causes_confirmed=false`。结构不同可以得到相同结果；这些线索不自动改写 SQL，也不覆盖原生评分。

报告按“真实不匹配 + 对应结构线索”组织清单。后续生成链路的通用修复应从原问题、官方 evidence 和授权 metadata/profile 得到约束，不把参考 SQL 或答案作为 Agent 提示。

## 预算与报告状态

- 每题独立审查预算：2 次业务 SELECT、600 秒；单 SQL 超时、完整结果行数/字节数仍沿用运行时的 30 秒、100,000 行/64 MiB。
- 模型调用预算为 0；原有 Agent 生成预算不变。
- `run_status=complete` 表示 10 题复评完成，允许其中存在真实结果不匹配。
- `summary.native_match_count` 和 `native_mismatch_count` 只对应这 10 条保存的 SQL。
- `formal_ex_denominator=null`、`primary_ex=null`，holdout 仍未开放。

## 本地验证

- 新增 21 项测试：开发范围与输入完整性、原 SQL 字节保留、完整结果而非前 20 行比较、原生数值语义、空结果、输出形状、结构线索、差异预览边界、执行失败预算及连接池关闭。
- 完整 M2 回归：169 项，166 项通过，3 项 Linux 专属检查待服务器执行。
- 10 题共 20 条 SQL 已通过本地只读策略检查。
- 本地准备报告：`evaluation/results/m2_native_replay10_preparation_local_20261017.json`。
- 本地测试报告：`evaluation/results/m2_native_replay10_tests_local_20261017.json`。

这些是离线/模拟检查；实际 PostgreSQL 匹配数量和真实错误清单需由下面的服务器命令产生。

## 服务器操作

将 `M2_native_replay10_sync_20261017.zip` 上传至项目根目录：

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M2_native_replay10_sync_20261017.zip
cd backend

python -m unittest discover -s tests -p 'test_m2_*.py' -v
```

测试通过后执行：

```bash
python -u -m scripts.rescore_m2_development10 \
  --source-report evaluation/results/m2_schema_coverage_diagnostics14_server.json \
  --output evaluation/results/m2_development_native_replay10_server.json
```

使用已有 PostgreSQL 私有凭据文件，不需要模型密钥。输出路径须尚不存在；重跑使用新文件名，保留原报告。

下载 `m2_development_native_replay10_server.json` 到本地 `backend/evaluation/results/` 核对。

## 返回报告后的工作

1. 检查实际原生差异、重放与捕获结果是否一致、来源及预算；固定错误清单。
2. 据真实差异优先确定 NULL 排序、输出角色/字段组、业务条件和值匹配的通用修复范围。
3. 对四个澄清题另行设计有数量上限、可追溯的同域关联表与字段组补充候选。
4. 候选冻结后再安排独立模型验证。当前复评直接复用已有 SQL，减少重新生成造成的定位波动。
