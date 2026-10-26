# M1 E v5 两题修正与分阶段复验

本地代码已加入 PostgreSQL 的嵌套排序别名检查和确定性改写。v5 的 `CHANNEL_OPS-136` 原 SQL 在 `ORDER BY ABS(target_gap)` 中引用同层输出别名，预检现在会阻止此写法，并改为把 `target_gap` 的原始表达式放进 `ABS`，再次校验后才调用数据库。修复前后 SQL 会记录在 `sql_order_alias_repair`。`CONTENT_OPS-001` 的三个精确对应关系为：`metric_date → 指标日期`（`cdm.metric_date`）、`impressions → 曝光量`（`SUM(cdm.impressions)`）、`plays → 播放量`（`SUM(cdm.play_count)`）。正式题集仍保持原样，等待服务器独立复评分。

## 先同步代码和运行两个独立证据脚本

把项目根目录的 `M1_E_V5_remediation_20261014.zip` 上传至服务器同名项目根目录，再运行：

```bash
cd ~/Python_work/askdata_studio_ops_release
sha256sum M1_E_V5_remediation_20261014.zip
unzip -o M1_E_V5_remediation_20261014.zip
cd backend
sha256sum evaluation/cases/all_cases.jsonl \
  evaluation/results/m1_e_postgres_live_classic_server_v5.json \
  evaluation/results/m1_e_postgres_live_phase83_server_v5.json
python -m unittest discover -s tests -p 'test_m1_d2_sql_runtime.py' -q
python -m unittest discover -s tests -p 'test_m1_e_v5_remediation.py' -q
```

题集 SHA 应为 `ff5956e9f4aca878ee63e232bdea1fef3416a28eda72669f91a33546c70f3adc`；两份 v5 报告 SHA 分别应为 `bd8d2a5fb01d0a87c34f43656ae228183b7f7e8efa3143519e862060fd8ef37e`、`41a2670f7dc5fd6cc490149d36d4fe9cd2f2b2c9239f278446b6c9560cf18af6`。随后执行：

```bash
DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m scripts.diagnose_m1_e_v5_channel136 \
  --output evaluation/results/m1_e_v5_channel136_diagnostic_server.json

DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m scripts.rescore_m1_e_v5_content001 \
  --output evaluation/results/m1_e_v5_content001_rescore_server.json
```

这两份新 JSON 应下载到本地 `backend/evaluation/results/` 供逐项核对。第一份应证明原 SQL 重现 `42703`、修复 SQL 执行并与 PostgreSQL Gold 严格一致；第二份应证明原始严格评分为 false，添加三个指定别名后的候选严格评分为 true，宽松结果仍为 true。两个脚本均不改题集，也不请求模型。若输出路径已有文件，使用新文件名并保留既有证据。

## 独立证据核对通过后应用别名

先得到已核对的复评分文件 SHA-256，再执行下列命令，将 `<已核对的复评分SHA-256>` 替换为实际完整值：

```bash
python -u -m scripts.apply_m1_e_v5_content001 \
  --replay evaluation/results/m1_e_v5_content001_rescore_server.json \
  --replay-sha256 <已核对的复评分SHA-256> \
  --output evaluation/results/m1_e_v5_content001_apply_server.json
sha256sum evaluation/cases/all_cases.jsonl
python -m unittest discover -s tests -q
```

应用脚本先检查来源报告、当前题集、复评分清单、实际与 Gold 行、三列逐列映射及重新计算的评分。只修改 `CONTENT_OPS-001` 的三项显式别名，并保存原始题集副本 `evaluation/results/m1_e_all_cases_before_v5_content001_20261014.jsonl`。更新后的正式题集 SHA-256 应为 `08cf84a50f43eb2d176d96246e1210c398a13a89beec69a9d0db1b7361b7815a`。

## 最终三组全量验收

确认诊断与复评分均通过、题集 SHA 正确后，分别运行并保留 v5 原始报告：

```bash
DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_benchmark \
  --mode live --scope classic --workers 1 \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_e_postgres_live_classic_server_v6.json

DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_benchmark \
  --mode live --scope all --workers 1 \
  --case-list evaluation/cases/phase83_validation.json \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_e_postgres_live_phase83_server_v6.json

DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_e2e \
  --case-list evaluation/cases/e2e_behavior_postgres.json \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_e_postgres_e2e_behavior_server_v6.json
```

v6 新生成 SQL 仍可能使用不同列名或计算方式，因此须逐题核查三份完整 JSON，不能只凭汇总数字宣布 M1 E 通过。
