# M1 E v4 七题独立 PostgreSQL 复评分

本轮脚本只保存独立证据，不修改 `evaluation/cases/all_cases.jsonl`，不调用模型，不覆盖 v4 原始报告。

## 固定输入

- 正式题集 SHA-256：`22a7ee6f9d8d2309e79ceb5d831468b30f609c485a0a31ba5d1a0cbde3d9ba6b`。
- classic v4 SHA-256：`71069c4ab43ef935c9e7ea16481c33a688684b952e3b0abdbe42248a9bc56735`；运行 ID `c8659a8ae7d54366b324c47d35214111`。
- phase83 v4 SHA-256：`e001bfffb11b9037720e759efdb5f959b4ed42e04121c7d0f5d067736fd55025`；运行 ID `ece685dafeaa456c87397e62d09b2932`。
- 来源：`short_video_ops_postgres`、PostgreSQL、`askdata_ops`，以报告中的数据、catalog、物理结构版本和服务器现场验证结果为准。

脚本固定 7 条 v4 生成 SQL 的 SHA-256，以及每题候选列别名。总计候选 16 项，均为逐题明确列名，不允许辅助列，不使用通配规则。运行时复验两个报告及当前题集的 SHA、manifest、清单、现场来源身份，然后用 `askdata_readonly` 重新执行保存的 SQL 和 PostgreSQL Gold。Gold 不使用缓存，另核对 Gold 与冻结期望、实际行数、原/候选严格评分及宽松评分。

本地离线测试已对 6 题使用同一份 CSV 数据重放，并确认原严格失败、候选严格通过。`CHANNEL_OPS-136` 在本地 DuckDB 重放时，某行实际 CPA 为 12.22，而冻结期望为 12.21；这与 PostgreSQL v4 现场宽松结果通过不同，可能是两种数据库的数值运算或类型转换差异。因此该题只在本地核对 `target_gap` 的 SQL 投影语义，**以服务器 PostgreSQL 重放的完整行和严格评分为准**。

## 同步与运行

将项目根目录下 `M1_E_V4_strict7_replay_20261014.zip` 上传到服务器项目根目录后，在服务器运行：

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M1_E_V4_strict7_replay_20261014.zip
cd backend
python -m unittest discover -s tests -p 'test_m1_e_v4_strict_review.py' -v
```

服务器脚本正式运行：

```bash
DATA_BACKEND=postgresql DATA_SOURCE_ID=short_video_ops_postgres TIME_FIELD_SUPPLEMENT_ENABLED=false \
python -u -m scripts.rescore_m1_e_v4_strict7 \
  --output evaluation/results/m1_e_v4_strict7_rescore_server.json
```

期望报告：`run_status=complete`、`case_count=7`、`original_strict_pass_count=0`、`candidate_strict_pass_count=7`、`loose_pass_count=7`、`alias_addition_count=16`、`auxiliary_allow_count=0`、`new_model_request_count=0`、`failed_case_ids=[]`。脚本若发现候选评分或宽松结果不一致，会保存 `run_status=failed` 的逐题实际行与原因，并以非零状态退出；应下载报告先审查。输出文件若已存在，请换新文件名，保留已有证据。

完成后将 `evaluation/results/m1_e_v4_strict7_rescore_server.json` 下载到本地同名目录。只有独立报告逐项核对通过，才进入正式题集应用和 v5 三组重跑。
