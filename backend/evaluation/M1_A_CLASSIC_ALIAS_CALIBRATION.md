# M1 A classic 显式别名校准收尾

日期：2026-10-07。状态：本地正式题集修改、服务器同步及两端独立复评分均已完成并审核通过。

## 1. 正式变更

在 [all_cases.jsonl](cases/all_cases.jsonl) 的 430 题中，仅向以下 8 题追加已核实的 13 项显式别名，保留原有别名。原题目、Gold SQL、排序、并列规则和数值精度均不变。

| 用例 | 追加映射：Gold 标准列 → 实际返回列 |
| --- | --- |
| CHANNEL_OPS-069 | avg_value → avg_conversion_value |
| CHANNEL_OPS-101 | creatives → creative_count |
| CONTENT_OPS-029 | category_name → content_category |
| CONTENT_OPS-035 | category_name → 内容分类；interactions → 互动数 |
| CONTENT_OPS-036 | interaction_date → interacted_date |
| CONTENT_OPS-051 | category_name → content_category；contents → content_count；avg_duration_seconds → avg_video_duration |
| CONTENT_OPS-136 | category_name → 内容分类；reports → 举报数量 |
| CONTENT_OPS-137 | category_name → 内容分类；reports → 举报数量 |

原文件完整字节备份：[m1_all_cases_before_classic_aliases_20261007.jsonl](results/m1_all_cases_before_classic_aliases_20261007.jsonl)。其余 422 行保留原始内容。

## 2. 独立验证

通过相同源身份、数据、应用和评分器版本核验后，逐题重放原服务器报告保存的 49 条最终 SQL，并使用原严格评分器。Gold 缓存仍须通过实际源身份、权限、问题、Gold SQL 与数据版本检查。

| 项目 | 结果 |
| --- | --- |
| 校准前严格结果复现 | 41/49 |
| 正式题集校准后严格结果 | 49/49 |
| 宽松结果 | 49/49 |
| 未评分 | 0 |
| 原始列名直接相同 | 6/49，保持原事实 |
| 新模型请求 | 0 |

独立结果：[m1_a_live_classic_alias_rescore_local.json](results/m1_a_live_classic_alias_rescore_local.json)。其中保存源运行 ID、原报告 SHA256、备份/正式题集 SHA256、原/新数据集版本、评分器版本、逐题 SQL/Gold SQL、完整结果行和追加别名。

服务器独立结果：[m1_a_live_classic_alias_rescore_server.json](results/m1_a_live_classic_alias_rescore_server.json)，运行 ID 为 95f399b7508742aaa03f039d00223fce。49 题全部通过，原/新题集 SHA256 和评分条件指纹与本地一致；逐题实际行及 Gold 行也全部完全相同。核查记录见 [m1_a_server_archive_review.json](results/m1_a_server_archive_review.json)。

本次是保存 SQL 的离线复评分，不是新 live 运行。原始 m1_a_live_classic_server.json 继续记录严格 41/49；原候选审查、M0 报告和 E2E 报告均保留。别名属于逐题明确许可，无通配规则，也没有放宽评分器。

## 3. 同步服务器

建议使用项目根目录的 `M1_A_列别名校准同步包_20261007.zip`。它包含正式题集、原题集备份、已审核候选记录、复评分脚本及其依赖模块、校准说明。它不包含模型密钥、数据文件或应用代码。

将 ZIP 上传到服务器项目根目录后执行：

```bash
unzip -o M1_A_列别名校准同步包_20261007.zip
cd backend
python -u -m scripts.rescore_m1_a_classic \
  --output evaluation/results/m1_a_live_classic_alias_rescore_server.json
```

此命令不请求模型。保留服务器已有的原始 m1_a_live_classic_server.json。脚本拒绝覆盖既有输出；若目标已存在，为下一次独立运行指定新的 --output 文件名。

同步包自带校准前题集备份，避免从已修改题集错误重建旧版本。服务器的源/代码摘要若与原始报告不同，脚本会停止，不绕过版本校验。

服务器同步命令已执行并验证通过。`m1_a_duckdb_gold_server.json` 也已完成本地归档与 79 题审核，M1 A 两项收尾均已闭环，详见 [最终验收结论](M1_A_FINAL_ACCEPTANCE.md)。本页保留同步命令供复现；原同步 ZIP 是打包时的历史版本，不因后来补齐验收文档而重写。
