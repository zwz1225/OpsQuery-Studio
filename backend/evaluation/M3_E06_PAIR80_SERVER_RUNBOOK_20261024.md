# M3 E06 冻结候选 development80 服务器同轮运行

本次交付仅用 `M3_E06_pair80_endpoint_feedback_v2_20261024_r2.zip` 及同名 `.sha256`。请从本地项目根目录上传这两个文件到服务器项目根目录。包 SHA-256：`e64bf68313813ce72f528daeca7cd77871b6ba5b436697830bf03a0a0fea20c2`；包 ID：`012c86dbc14a03f6d42aeffaf8d217099febcb6ac1c862b1fc72970e9fd7c7f1`。这是公开开发集诊断，不访问 holdout。

## 1. 校验与准备

在服务器执行：

```bash
cd "$HOME/Python_work/askdata_studio_ops_release"
sha256sum -c M3_E06_pair80_endpoint_feedback_v2_20261024_r2.zip.sha256

tools_root="$HOME/Python_work/m3_e06_pair80_tools_20261024_r2"
work="$HOME/Python_work/m3_e06_pair80_endpoint_feedback_v2_20261024_r1"
test ! -e "$tools_root"
test ! -e "$work"
unzip -n -q M3_E06_pair80_endpoint_feedback_v2_20261024_r2.zip -d "$tools_root"
bundle="$tools_root/m3_e06_pair80_endpoint_feedback_v2_20261024_r2"

"$HOME/.local/askdata/pg16-env/bin/pg_isready" \
  -h 127.0.0.1 -p 55432 -d askdata_m2_bird

python -u "$bundle/control/prepare_m3_e06_pair80.py" \
  --bundle-root "$bundle" \
  --source-backend "$HOME/Python_work/askdata_studio_ops_release/backend" \
  --workspace "$work"
```

准备阶段只复制冻结代码和公开协议材料，不读取或复制密钥及数据库数据。预期 `run_status=complete; model_calls=0; database_connected=false`。

## 2. 静态、连接和模型探针

```bash
python -u "$work/control/run_m3_e06_pair80.py" \
  --workspace "$work" --check-only

python -u "$work/control/run_m3_e06_pair80.py" \
  --workspace "$work" --model-probe
```

第一步预期 `run_status=complete`、`phase=preflight_with_process_dns_https`，核对代码、来源、协议、模型公开配置、进程内 DNS/HTTPS 及绑定依赖，不调用模型。第二步预期 `phase=transport_model_probe_complete`；它用 10 个固定短输入测试一次 embedding，最多 2 次 HTTP 尝试，不含题目或 SQL，成本与正式对照分开。任一步失败都保留报告，先解决对应网络/配置问题，再建立新工作区，不在失败工作区继续生成。

## 3. 正式同轮对照

```bash
python -u "$work/control/run_m3_e06_pair80.py" \
  --workspace "$work"
```

预期 `run_status=complete`、`phase=complete`，生成 `reports/e06_pair80_comparison_server.json`。两侧依次各生成 80 题，索引独立，生成完两侧捕获后再做不调用模型的原生复评。一个工作区仅有一次生成预约；失败后不重新运行正式生成命令。如两份捕获都完整、仅原生复评中断，可核对证据后执行一次 `--replay-only`；它不会再次生成 SQL：

```bash
python -u "$work/control/run_m3_e06_pair80.py" \
  --workspace "$work" --replay-only
```

## 4. 下载供本地核对

从同一个 `$work` 下载以下九份原始文件，保留相对目录：

```text
reports/e06_pair80_preflight_server.json
reports/e06_pair80_transport_model_probe_server.json
reports/e06_pair80_server.json
reports/e06_pair80_comparison_server.json
transport_dependency_lock.json
baseline/backend/evaluation/results/m3_e06_pair80_baseline_capture_server.json
baseline/backend/evaluation/results/m3_e06_pair80_baseline_native_server.json
candidate/backend/evaluation/results/m3_e06_pair80_candidate_capture_server.json
candidate/backend/evaluation/results/m3_e06_pair80_candidate_native_server.json
```

若运行失败，先保留主报告、已有捕获和 `$work/reports/logs/` 中对应日志；不要覆盖、删除或修改原始报告。成功后按 [M3_E06_CANDIDATE_FREEZE_20261024.md](M3_E06_CANDIDATE_FREEZE_20261024.md) 中已冻结的口径核对每题变化与成本。
