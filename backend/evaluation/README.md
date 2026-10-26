# OpsQuery Studio · 短视频运营问数评测

当前产品名称为 OpsQuery Studio 智能数据分析平台（原名 AskData Studio）。内部标识、历史报告与冻结实验包保持原版本；展示名称更改不改变评测协议与历史成绩。

> 2026-10-26阶段状态：M3有限研究与证据收尾完成，整体效果推广验收未通过；运营产品默认未接纳M3候选，M4暂不启动。见[M3最终验收](M3_FINAL_ACCEPTANCE_20261026.md)、[12份比较台账](M3_EXPERIMENT_LEDGER_20261026.md)、[实际启用审计](M3_RUNTIME_ACTIVATION_AUDIT_20261026.md)和[遗留项](M3_OPEN_ISSUES_20261026.md)。下文430题说明属于内部运营评测，BIRD原生评分与开发/保留边界另见M2/M3记录。

当前评测集包含 430 条用例，覆盖用户增长、渠道投放和内容运营；其中 49 条标记为经典冒烟用例。

## 指标

- 字段级 Schema 召回率：正确召回字段数 / 标准字段数
- 字段级 Schema 准确率：正确召回字段数 / 实际召回字段数
- SQL 执行成功率：成功执行 SQL 数 / 测试用例数
- 查询结果正确率：模型 SQL 与标准 SQL 的执行结果一致数 / 测试用例数
- SQL 执行时间：DuckDB 执行层平均耗时与 P95 耗时

结果比较允许等价 SQL；未要求排序时忽略行列顺序，明确要求 Top N 或排序时校验顺序和数量。

Live 评测优先读取 `cache/gold_results` 中与用例 SQL、权限范围和排序配置匹配的 Gold Result；没有缓存时执行 `gold_sql` 并原子写入缓存。修改数据库数据后可使用 `--no-use-cached-gold` 强制刷新。没有 `gold_sql` 的旧用例继续使用 `expected_columns` 和 `expected_rows`。

## 运行

在 `backend` 目录执行：

```powershell
# 验证全部标准 SQL，不调用模型
.\.venv\Scripts\python.exe -m evaluation.run_benchmark --mode gold --scope all

# 运行 49 条经典冒烟用例，会调用模型服务
.\.venv\Scripts\python.exe -u -m evaluation.run_benchmark --mode live --scope classic

# 运行全部 430 条用例，会调用模型服务
.\.venv\Scripts\python.exe -u -m evaluation.run_benchmark --mode live --scope all

# 强制重新执行 Gold SQL，刷新标准结果缓存
python -m evaluation.run_benchmark --mode live --scope classic --no-use-cached-gold
```

已完成的基线报告保存在 `evaluation/results`，包含 JSON、CSV 和 Markdown 三种格式。运行 live 评测会产生接口调用费用。

Phase 8.3.1 的非经典 30 题扩展验证集、Gold SQL 校验和 Schema 检索阶段基线命令见 [PHASE83_VALIDATION.md](PHASE83_VALIDATION.md)。

## M0：可复现基线

`run_benchmark.py` 的 `live` 模式是**组件评测**：它会使用 Case 中的 `retrieval_terms`，不能当作用户入口的端到端成绩。`run_e2e.py` 从 `AskDataService.submit()` 输入原始问题；两类结果分别保存，不合并准确率。

新运行报告包含 `run_manifest`：所选 Case 的内容哈希、数据和 Schema 哈希、应用和评测代码哈希、模型配置、权限角色、基准日期、运行 ID 与时间。逐题结果带 `run_id`、`trace_id`。`--resume` 只接受运行指纹完全一致的报告；回归比较默认拒绝缺少清单、缺题或条件不一致的 Snapshot。确需诊断旧报告时使用 `--allow-incompatible`，其差异不能作为正式回归结论。

结果分数有两种口径：`result_accuracy` 是历史宽松列映射规则，`strict_result_accuracy` 要求列名或 Case 声明的别名及辅助列匹配。两者都保留行顺序、重复行、NULL 与数值容差规则。明确要求排序的 180 条 Case 已标注主排序列；主指标相同的行允许互换。Top N 的并列截断目前仍使用 Gold SQL 的固定成员集合，这部分要结合逐题结果解释。`result_scored_count`、`strict_scored_count` 和 `unscored_count` 显示分母；Gold 执行或评分失败属于未评分。SQL 执行失败属于可评分的错误。执行结果超过接口的 200 行预览时，评测器重新执行 SQL 取得完整结果；超过 10000 行上限则标记未评分。

在 `backend` 目录运行：

```powershell
# 不调用模型，校验全部 430 条 Gold SQL 和静态预期
.\.venv\Scripts\python.exe -u -m evaluation.run_benchmark --mode gold --scope all --no-use-cached-gold --save-snapshot --output evaluation/results/m0_gold_all.json

# 组件评测，调用模型；先固定 49 题，再固定 30 题，最后按预算跑 430 题
.\.venv\Scripts\python.exe -u -m evaluation.run_benchmark --mode live --scope classic --save-snapshot --output evaluation/results/m0_live_classic.json
.\.venv\Scripts\python.exe -u -m evaluation.run_benchmark --mode live --scope all --case-list evaluation/cases/phase83_validation.json --save-snapshot --output evaluation/results/m0_live_phase83.json

# 端到端小样本，调用模型，且不传 Case 的 retrieval_terms
.\.venv\Scripts\python.exe -u -m evaluation.run_e2e --save-snapshot

# 同条件 Snapshot 比较
.\.venv\Scripts\python.exe -m evaluation.regression --baseline evaluation/results/snapshots/BASELINE.json --candidate evaluation/results/snapshots/CANDIDATE.json
```

运行材料及当前可用基线的状态见 [M0_BASELINE_INVENTORY.md](M0_BASELINE_INVENTORY.md)。
