# Phase 8.2.1：时间字段补充规则离线实验

在 `backend` 目录运行：

```bash
python -m evaluation.time_field_ablation \
  --input evaluation/results/retrieval_diagnosis_classic.json
```

命令读取已有诊断 JSON、静态 Schema、指标目录和角色权限配置，不调用模型、
数据库或 Agent，也不修改原诊断文件。默认生成：

- `evaluation/results/retrieval_diagnosis_classic_time_field_ablation.json`
- `evaluation/results/retrieval_diagnosis_classic_time_field_ablation.md`

候选规则仅使用问题和当前最终检索字段：问题必须明确包含时间要求；指标目录命中时
取该指标的时间字段；若目录没有对应指标，仅在问题明确提到已召回的指标字段，且
所属表只有一个时间字段时，尝试 Schema 回退。候选字段还必须存在于静态 Schema、
所属表已进入当前检索结果，且用户有访问权限。比较目标字段 `gold_fields` 只用于
运行后的评分，不参与候选选择。

报告包含五种结果：`baseline` 为原检索结果；`catalog_append` 和
`catalog_reserve` 只使用指标目录；`append` 和 `reserve` 还包括 Schema 回退。
`append` 最多额外加入两个时间字段，可能超过当前 20 字段上限；`reserve` 保持上限，
但可能挤出原本有用的字段。逐题查看 `proposed_fields`、
`reserve_evicted_fields` 和 `lost_gold_fields_vs_final` 后，再考虑在线接入。

这是离线候选实验，不能预测 SQL 结果准确率或参数变化后的检索耗时。
