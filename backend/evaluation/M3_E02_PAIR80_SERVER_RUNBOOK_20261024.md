# M3：已接受 E02 语义候选的 development80 同轮对照

## 本轮固定范围

这轮比较冻结的 M2 v4 语义基线与已接受的 E02 条件/关系语义候选。两侧使用相同的进程内 DNS、HTTPS、模型配置、数据源、预算和原生评分规则；两侧各自构建索引。E03 对 0407 的关系/输出处理未纳入候选。仅运行公开开发集 80 题，不运行 holdout。

固定身份：bundle ID `3288d878d8d466104b57f561e3dc3c344fde21597c998285dd748208ea700797`；代码文件数基线 97、候选 99。历史 M2 v4 原生复评报告 SHA-256 为 `1bbb278d0a5ffb99b3049faff6e1da2c482230284188e71e8d4fb44504c38774`，其中成功 50/80；这些题的 ID 已冻结在包清单中。此前 E02 的 24 题结果仅用于确认候选来源，本轮按新的同轮 80 题结果判断。

包：`M3_E02_pair80_process_dns_v1_20261024_r3.zip`，SHA-256：`4f7925b24d9a7f47cbf9811a527f83d9596a147992bd8869df2d9f317814356b`。对应 `.sha256` 文件使用 LF；两文件都上传到远程项目根目录。

## 1. 解包与准备

在服务器执行以下命令。每个工作区只用于一次生成；遇到任何失败保留报告，并给下一次尝试另取工作区名称。

```bash
cd "$HOME/Python_work/askdata_studio_ops_release"

sha256sum M3_E02_pair80_process_dns_v1_20261024_r3.zip
tr -d '\r' < M3_E02_pair80_process_dns_v1_20261024_r3.zip.sha256 | sha256sum -c -

tools_root="$HOME/Python_work/m3_e02_pair80_tools_20261024_r3"
test ! -e "$tools_root"
unzip -n -q M3_E02_pair80_process_dns_v1_20261024_r3.zip -d "$tools_root"

bundle="$tools_root/m3_e02_pair80_process_dns_v1_20261024_r3"
work="$HOME/Python_work/m3_e02_pair80_process_dns_v1_20261024_r1"

"$HOME/.local/askdata/pg16-env/bin/pg_isready" \
  -h 127.0.0.1 -p 55432 -d askdata_m2_bird

python -u "$bundle/control/prepare_m3_e02_pair80.py" \
  --bundle-root "$bundle" \
  --source-backend "$HOME/Python_work/askdata_studio_ops_release/backend" \
  --workspace "$work"
```

准备阶段只复制冻结的公开代码和协议材料，不读取或复制 `.env`、数据库凭据及 BIRD 数据。预期 `run_status=complete; model_calls=0; database_connected=false`。

## 2. 静态与连接预检

```bash
python -u "$work/control/run_m3_e02_pair80.py" \
  --workspace "$work" --check-only
```

预期 `run_status=complete`、`phase=preflight_with_process_dns_https`。预检核对两侧代码、协议、角色、数据版本、模型公开配置、`dig` 二进制身份，以及实际进程内 DNS/HTTPS 连通性；不调用模型。若失败，查看 `$work/reports/e02_pair80_preflight_server.json` 及同名 `_checks` 目录。失败时不要在该工作区启动正式生成。

## 3. 有界模型连接检查

```bash
python -u "$work/control/run_m3_e02_pair80.py" \
  --workspace "$work" --model-probe
```

预期 `run_status=complete`、`phase=transport_model_probe_complete`。这一步只对 10 段固定的公开短文本发起一次 embedding 批量请求，最多 2 次 HTTP 尝试；不使用题目、Gold 或 SQL。它与正式 80 题成本分开登记。若失败，保留 `e02_pair80_transport_model_probe_server.json`；先处理网络，再新建工作区。

## 4. 正式同轮生成与独立复评

```bash
python -u "$work/control/run_m3_e02_pair80.py" \
  --workspace "$work"
```

预期 `run_status=complete`、`phase=complete`，并生成 `$work/reports/e02_pair80_comparison_server.json`。基线与候选依次各生成 80 题；两份捕获完整以后才分别执行不调用模型的原生复评。单工作区生成上限 160 题，失败后不续跑生成、不自动换提示或评分。只在两份捕获已完整而原生复评中断时，才可检查证据后使用一次 `--replay-only`；该模式不再生成题目。

## 5. 下载并交付核对

从同一个 `$work` 下载以下文件，保留目录结构：

```text
reports/e02_pair80_preflight_server.json
reports/e02_pair80_transport_model_probe_server.json
reports/e02_pair80_server.json
reports/e02_pair80_comparison_server.json
transport_dependency_lock.json
baseline/backend/evaluation/results/m3_e02_pair80_baseline_capture_server.json
baseline/backend/evaluation/results/m3_e02_pair80_baseline_native_server.json
candidate/backend/evaluation/results/m3_e02_pair80_candidate_capture_server.json
candidate/backend/evaluation/results/m3_e02_pair80_candidate_native_server.json
```

失败时先交付主报告和其提示的日志；不要覆盖旧报告。所有原始 JSON 保持原样。

## 预定判断规则

- 固定分母 80。候选至少 51/80，且超过这次同轮基线；历史 50/80 单列。
- 检查历史成功 50 题和既有 20 道回归题。任何退化逐题审查；自动筛选不会把退化用其他得分抵消。
- 逐题核对 1479；0407、0085 作为已观察诊断，核对模型实际 SQL 与公开语义，不沿用 E03 未成功的结论。
- `chat` token 总量与逐题耗时 p95 若较同轮基线增加超过 20%，先审查成本。另报告总 token、模型 HTTP 尝试和索引准备成本；未知 usage 保持未知。
- 核对来源身份、只读权限、隔离、完整结果、每题模型及 SQL 预算。比较报告中的 `automatic_screen_pass` 仅是预先约定的工程筛选，最终需要逐题业务语义审查。

这一轮是公开开发集工程实验；它不代表新的保留集分数或统计显著性。未通过时保留一次实验报告，记录原因并结束本候选的这轮对照。
