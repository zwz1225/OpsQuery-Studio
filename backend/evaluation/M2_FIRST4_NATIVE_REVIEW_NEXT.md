# 四题首次 SQL 原生复评验收与下一步

日期：2026-10-18。输入为 `evaluation/results/m2_rejected_first4_native_server.json`。

## 核对结论

- 输入 SHA-256：`481c54c9fbf3a4ceab76c8f231b3bd6bb740b3368a108d981091e4d954ffb587`。
- 本地审查 159 项全部通过，完整记录为 `evaluation/results/m2_rejected_first4_native_review_local_20261018.json`。
- 四题原始首次 SQL 全部原生匹配；共执行 8 次 SQL，新增模型调用 0 次，错误为空，连接池已关闭。
- 逐题 SQL 与原始生成轨迹一致；来源账号、授权 catalog、数据版本和先前成功报告的哈希链一致。当前目标经过服务器重新验证。
- 这是可信进程执行预测 SQL 和冻结 Gold 的诊断审查，Gold 未提供给生成模型；保留题仍关闭。

| 题号 | 结果规模 | 原生匹配 | 旧规则的错误要求 |
| --- | --- | --- | --- |
| 0036 | 1 行，6 列 | 是 | 额外要求管理员姓氏为 `Administrator` |
| 0159 | 140 行，1 列 | 是 | 将 `operation='VYBER'` 错套到 `type` |
| 1405 | 4 行，2 列 | 是 | 额外要求活动 `type='Budget'` |
| 0368 | 1 行，1 列 | 是 | 将公式中的 100 误作多个 ID 字段的筛选值 |

0368 两端均为浮点数 `0.42413149836331`，十六进制表示均为 `0x1.b24f870ab2114p-2`。原生评分没有使用容差。

0159 本地只有各 20 行预览，140 行完整比较依赖服务器记录的结果摘要和原生比较；其他六个完整结果对象已在本地重建并复核。

两份前置成功报告无需 `_v2` 后缀：按内容 SHA-256 验证，与文件名后缀无关。所有原始报告保持不变。

## 本次补充修正

v2 已修正四条错误样本条件，新增统计粒度与关系角色支持。本次审查发现 v2 还会因 0368 先除后乘而强制拒绝其正确首次 SQL，因此删除仅凭乘除顺序的拒绝，改为公开公式和类型提示。

候选仍为 `bird_public_intent_candidate_v2`；数值策略细分版本更新为 `percentage_real_operand_operation_order_advisory_v2`。代码哈希记录这次变化。REAL 路径检查、生成次数、预算、权限、来源隔离和原生评分规则继续适用。不将本次查询的浮点相等推广到其他查询。

这次四题成功不能替代新版模型生成验收，也不能与旧 14 题成绩相加作为正式 EX。0201 统计粒度、0586 关系角色及输出仍需观察；1399 继续独立记录参考输出形态差异，不改 Gold 或评分。

## 服务器命令

将 `M2_public_intent_v2_numeric_review_sync_20261018.zip` 上传至服务器项目根目录。它包含上次 v2 文件和此次修正，可整体覆盖代码；不含密钥或服务器报告。

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M2_public_intent_v2_numeric_review_sync_20261018.zip
cd backend
python -m scripts.check_m2_public_intent_delivery
python -m unittest discover -s tests -p 'test_m2_*.py' -q
```

同步与测试通过后，重新生成相同 14 题的开发诊断：

```bash
python -u -m evaluation.bird.diagnostic_runner \
  --case-list evaluation/cases/bird_mini_dev/m2_development_diagnostics14.json \
  --model-config-file .env \
  --schema-coverage --intent-candidate --save-snapshot \
  --output evaluation/results/m2_public_intent_v2_diagnostics14_server.json
```

随后对这次生成结果保存独立、无模型的原生复评：

```bash
candidate_sha=$(sha256sum evaluation/results/m2_public_intent_v2_diagnostics14_server.json | cut -d ' ' -f 1)
python -u -m scripts.rescore_m2_intent_candidate \
  --source-report evaluation/results/m2_public_intent_v2_diagnostics14_server.json \
  --source-sha256 "$candidate_sha" \
  --output evaluation/results/m2_public_intent_v2_native14_server.json
```

输出路径若已存在，使用新名字，并同步修改后续输入路径。不要覆盖旧报告。两条命令之间不要修改代码。

新版代码使用新的索引身份；八域无缓存时预计产生 49 批共享 embedding 请求，另计逐题模型调用和重试，均由报告记账。题目预算不提高。暂不扩大 development80 或打开 holdout。

完成后下载两份新报告到本地 `backend/evaluation/results/`，重点验收四题错误筛选是否消失、原 7 个成功题是否退化，以及 0201、0586、1399 的真实轨迹。
