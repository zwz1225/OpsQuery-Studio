# M1 E v3 日期修正与四题严格评分审查

日期：2026-10-13。保留三份 v3 原始 JSON 和 `M1_E_POSTGRES_V3_REVIEW.md`；本次尚未改变正式题集 `cases/all_cases.jsonl`。修正前正式题集 SHA-256：`2c72c23c00685ea2dca5247e50a9395ba8e3d885f64710059f86004d1f705c15`。

## `CHANNEL_OPS-025` 的日期约束

根因是 `ConstraintPlanner` 将“截至 2026-05 各月”规划成 `month_equals`，导致 `ConstraintValidator` 要求仅匹配 5 月。题目的 Gold 使用 `TO_CHAR(stat_date, 'YYYY-MM') <= '2026-05'`；v3 的三次候选都使用 `stat_date < DATE '2026-06-01'`。在当前日期列上，这两种写法均包含 5 月及此前记录。

现在只在月份前出现“截至/截止（到、至）”时规划 `month_on_or_before`。校验器接受目标月份的年月至比较，或下一月首日的严格小于比较；继续拦截漏写上界、早一个月的上界、只查询目标月份、放入 `OR` 的可绕过条件。普通单月查询继续使用原 `month_equals`。10 条现有“截至某月”PostgreSQL Gold（`CHANNEL_OPS-021`—`025`、`071`—`075`）均通过新规则。v3 候选 SQL 在本地按 PostgreSQL 方言验证后，日期约束由 `BLOCK` 变为 `PASS`；SQL 执行本身仍需服务器单题重跑。

## 四题逐题审查

下表的候选映射均来自保存的 v3 SQL 投影表达式，不使用通配别名。使用本地同版本冻结数据重放原 SQL 后，四题都是“原严格失败 → 候选严格通过”。这只是本地证据；正式题集更新前必须运行独立 PostgreSQL 重放。

| 题目 | v3 SQL 投影及当前严格差异 | 候选逐题策略 | 业务口径限制 |
| --- | --- | --- | --- |
| `CHANNEL_OPS-004` | `ad_daily_stats.stat_date AS "统计日期"`、`SUM(spend) AS "广告消耗"`；30 行普通结果正确 | `stat_date ← 统计日期`、`spend ← 广告消耗` | 生成 SQL 未显式两位舍入；当前冻结数据严格数值比较通过，未来数据需继续检查。 |
| `CHANNEL_OPS-005` | 与上一题相同的投影；31 行普通结果正确 | 相同两项映射，仅加入本题 | 同上。 |
| `GROWTH_OPS-100` | `avg_plays_per_user` 是人均播放；另输出 `total_play_count`、`distinct_user_count`；1 行普通结果正确 | `plays_per_user ← avg_plays_per_user`；仅为本题声明上述两项精确辅助列 | 分子是 `SUM(play_count)`，分母是去重 `user_id`，符合题面；不得开放任意额外列。 |
| `CHANNEL_OPS-102` | `creative_status AS "创意状态"`、`COUNT(*) AS "创意数量"`；2 行普通结果正确 | `creative_status ← 创意状态`、`creatives ← 创意数量` | Gold 是 `COUNT(creative_id)`；当前目标数据中 `creative_id` 是主键且无空值，因此当前结果一致，未来数据变化时仍需重新验证。 |

`scripts/rescore_m1_e_v3_strict.py` 固定三份证据的 SHA-256：正式题集和两份 v3 live 报告；还固定四条生成 SQL 的 SHA-256。它在已验证 PostgreSQL 上重新执行每条保存的 SQL 和 Gold，核对冻结期望行、原严格失败、候选严格通过、普通结果正确及行数。它只生成独立 JSON，不调用模型、不改正式题集。`scripts/apply_m1_e_v3_strict.py` 已准备好，只有独立报告完整且来源、逐行评分全部核对成功才会按四题写入 7 项精确列别名和 2 项精确辅助列许可；本阶段暂不运行应用脚本。

## 本地验证

- 新日期回归测试 6 项通过，包括 PostgreSQL 方言及错误上界拦截。
- 四题保存 SQL 的本地数据重放测试通过；四条原严格评分均失败，四条候选严格评分均通过。
- 修改后全量 `unittest discover -s tests -q` 通过 496 项（新增 PostgreSQL 方言测试随后单独通过）。
- 上述验证使用本地冻结数据。PostgreSQL 实际执行与结果复评分需要服务器完成。

## 服务器复验顺序

在服务器 `backend` 目录中，先同步本次代码与单题题单，再执行：

```bash
python -m unittest discover -s tests -p 'test_m1_e_month_upper_bound.py' -v
python -m unittest discover -s tests -p 'test_m1_e_v3_strict_review.py' -v

DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m scripts.rescore_m1_e_v3_strict \
  --output evaluation/results/m1_e_v3_strict4_rescore_server.json

DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_benchmark \
  --mode live --scope all --workers 1 --no-use-cached-gold --save-snapshot \
  --case-list evaluation/cases/m1_e_channel025_diagnostic.json \
  --output evaluation/results/m1_e_channel025_diagnostic_server_v4.json
```

先核对两份新报告。四题 PostgreSQL 独立重放若未全部通过，不应用候选评分策略；`CHANNEL_OPS-025` 若仍未执行成功，检查新候选 SQL、约束验证和数据库错误。两份报告通过后，再运行应用脚本并检查正式题集新 SHA-256，随后用新文件名重跑 classic 49、扩展 30 和 E2E 8 条。原始 v3 JSON 不得覆盖。
