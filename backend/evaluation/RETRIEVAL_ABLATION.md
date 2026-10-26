# Phase 8.1 Schema 检索离线对照

在 `backend` 目录运行：

```bash
python -m evaluation.retrieval_ablation \
  --input evaluation/results/retrieval_diagnosis_classic.json
```

命令只读取已有诊断 JSON，不调用模型、SQL 或 Agent。输出：

- `evaluation/results/retrieval_diagnosis_classic_ablation.json`
- `evaluation/results/retrieval_diagnosis_classic_ablation.md`

报告比较 BM25、Dense、RRF、Rerank 在相同 Top-K 下的 Gold 字段覆盖情况，
并用已保存的 Rerank 分数模拟最终字段上限和阈值。`gained_gold_fields_vs_final`
和 `lost_gold_fields_vs_final` 记录相对于原最终结果新增、丢失的 Gold 字段。

离线模拟只能选择诊断文件中已有的候选字段，无法恢复初召回未进入前 30 的字段。
它不提供 SQL 正确率或修改参数后的耗时估计；有希望的方案仍需用 Live benchmark 验证。
