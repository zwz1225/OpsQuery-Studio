# M3 E06：明确端点校验反馈的独立 24 题同轮对照

## 固定设计

两侧都继承 E05 已冻结的公开端点提示和 E02 条件/关系策略。候选仅新增 `endpoint_validation.py` 并修改 `case_worker.py`，在原生只读 SQL 结构校验通过后、查询执行前，针对公开证据唯一指定端点而生成 SQL 用 `OR` 扩展到另一端点的精确形态返回结构化修复反馈。其他形态弃权。基线不启用这一反馈。模型配置、来源、权限、生成次数与预算、24 题顺序、各侧独立索引和独立原生复评保持一致。

目标 `BIRD-PG-0239`；边界 `BIRD-PG-0206` 在 20 条成功回归题中。另有 0072、0092、0356 作为已观察诊断题。只运行公开开发题，不运行 holdout。成功筛选要求：0239 候选原生正确、候选优于同轮基线、20 条回归全部保留、0206 原生正确且未被本规则拒绝，并核对模型调用、Token、p95 延迟与每次 SQL 尝试。

本地包：`M3_E06_pair24_endpoint_feedback_v2_20261024.zip`。SHA-256：`7663826f94cce7538434c973873a545b2710aa06e6ab1b06e08c2a9ab01824f7`。包 ID：`b0d2526fed45f2ad3c54f723afb1390930a826764e029ac0c6283f93a3d5b0bc`。代码清单：基线 100、候选 101 文件。包不含 `.env`、数据库密码或数据转储。本地 E06 12 个测试通过；服务器正式对照尚未运行。v1 包保留为制作过程记录，本次只使用 v2。

## 1. 上传、准备与检查

把 ZIP 和 `.zip.sha256` 上传到服务器项目根目录，登录后执行：

```bash
cd "$HOME/Python_work/askdata_studio_ops_release"
tr -d '\r' < M3_E06_pair24_endpoint_feedback_v2_20261024.zip.sha256 | sha256sum -c -

tools_root="$HOME/Python_work/m3_e06_pair24_tools_v2_20261024_r1"
work="$HOME/Python_work/m3_e06_pair24_endpoint_feedback_v2_20261024_r1"
test ! -e "$tools_root"
test ! -e "$work"
unzip -n -q M3_E06_pair24_endpoint_feedback_v2_20261024.zip -d "$tools_root"
bundle="$tools_root/m3_e06_pair24_endpoint_feedback_v2_20261024"

"$HOME/.local/askdata/pg16-env/bin/pg_isready" \
  -h 127.0.0.1 -p 55432 -d askdata_m2_bird

python -u "$bundle/control/prepare_m3_e06_pair24.py" \
  --bundle-root "$bundle" \
  --source-backend "$HOME/Python_work/askdata_studio_ops_release/backend" \
  --workspace "$work"

python -u "$work/control/run_m3_e06_pair24.py" \
  --workspace "$work" --check-only
```

预期准备 `run_status=complete; model_calls=0; database_connected=false`；静态及进程内 DNS/HTTPS 预检 `run_status=complete`、`phase=preflight_with_process_dns_https`。预检失败时保留报告，不进入生成；网络恢复后另建新工作区。

## 2. 有界模型连接检查和正式对照

```bash
python -u "$work/control/run_m3_e06_pair24.py" \
  --workspace "$work" --model-probe

python -u "$work/control/run_m3_e06_pair24.py" \
  --workspace "$work"
```

模型连接检查只执行固定 10 输入 embedding，最多 2 次 HTTP 尝试，不使用题目。正式对照各侧生成 24 题，两个捕获都完成后再分别做无模型原生复评。预期主报告 `run_status=complete`、`phase=complete`，并生成 `reports/e06_pair24_comparison_server.json`。

一个工作区最多保留一次生成尝试，不覆盖失败报告，也不在同一工作区重做生成。若两份捕获完整而只中断了原生复评，核对后可在同一工作区执行一次 `--replay-only`；其余失败使用新的工具目录和工作区名称。

## 3. 下载核对材料

从同一 `$work` 保持相对目录下载：

```text
reports/e06_pair24_preflight_server.json
reports/e06_pair24_transport_model_probe_server.json
reports/e06_pair24_server.json
reports/e06_pair24_comparison_server.json
transport_dependency_lock.json
baseline/backend/evaluation/results/m3_e06_pair24_baseline_capture_server.json
baseline/backend/evaluation/results/m3_e06_pair24_baseline_native_server.json
candidate/backend/evaluation/results/m3_e06_pair24_candidate_capture_server.json
candidate/backend/evaluation/results/m3_e06_pair24_candidate_native_server.json
```

重点检查 0239 的首次 SQL、每次 `endpoint_validation_observations`、`validation_events` 中的公开依据与修复反馈、最终 SQL 和原生结果。若候选 0239 首次 SQL 已正确而没有触发反馈，不把改善归因于本规则；只有观察到反馈、随后生成不同 SQL 且原生结果正确，才认为修复路径得到验证。检查 0206 没有 `candidate_repair`，双端点语义和原生正确性保持。再逐题核对 20 条回归、其它边界、来源身份、独立索引、生成尝试、模型调用、Token 与延迟。报告只代表这次开发集工程筛选。
