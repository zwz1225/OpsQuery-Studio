# M1 E v4 七题别名应用与 v5 重跑

前提：服务器已有未修改的两份 v4 live JSON、独立报告 `evaluation/results/m1_e_v4_strict7_rescore_server.json`，且正式题集 SHA-256 为 `22a7ee6f9d8d2309e79ceb5d831468b30f609c485a0a31ba5d1a0cbde3d9ba6b`。独立报告已在本地审查，SHA-256 `7a400f6ce7835672a80e2f30fd8ac6147366b8f96c3a7983c05a771fd96fed92`，七题候选严格评分全通过。

## 同步与应用

将项目根目录下 `M1_E_V4_strict7_apply_20261014.zip` 上传至服务器项目根目录，随后执行：

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M1_E_V4_strict7_apply_20261014.zip
cd backend
python -m unittest discover -s tests -p 'test_m1_e_v4_apply.py' -v
python -u -m scripts.apply_m1_e_v4_strict7 \
  --replay evaluation/results/m1_e_v4_strict7_rescore_server.json \
  --output evaluation/results/m1_e_v4_strict7_apply_server.json
sha256sum evaluation/cases/all_cases.jsonl
```

应用脚本先检查复评分报告、两份 v4 原始报告、来源身份、实际与 Gold 行、七题旧/新严格评分和正式题集 SHA；只允许新增已核实的 16 项逐题别名，并保存更新前副本 `evaluation/results/m1_e_all_cases_before_v4_strict7_20261014.jsonl`。更新后正式题集 SHA-256 应为 `ff5956e9f4aca878ee63e232bdea1fef3416a28eda72669f91a33546c70f3adc`。报告输出路径如果已存在，改用新文件名保留原证据。

## v5 三组独立运行

确认更新后题集 SHA-256 正确，再分别运行：

```bash
DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_benchmark \
  --mode live --scope classic --workers 1 \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_e_postgres_live_classic_server_v5.json
```

```bash
DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_benchmark \
  --mode live --scope all --workers 1 \
  --case-list evaluation/cases/phase83_validation.json \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_e_postgres_live_phase83_server_v5.json
```

```bash
DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m evaluation.run_e2e \
  --case-list evaluation/cases/e2e_behavior_postgres.json \
  --no-use-cached-gold --save-snapshot \
  --output evaluation/results/m1_e_postgres_e2e_behavior_server_v5.json
```

三份 v5 JSON 均应下载到本地 `backend/evaluation/results/` 后再做最终逐题核对。既有 v4 报告、复评分报告和备份题集应保留。单次新生成 SQL 可能使用不同列名；如果出现新的严格评分差异，应审查该次 SQL 与输出，不应直接按前次结果宣告通过。
