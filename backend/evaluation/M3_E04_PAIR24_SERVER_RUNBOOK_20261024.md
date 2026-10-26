# M3 E04：标量计数输出粒度的独立 24 题同轮对照

## 范围与身份

基线、候选均从已冻结的 E02 条件/关系语义和相同进程内 DNS/HTTPS 连接代码出发。候选只改 `evaluation/bird/intent.py`、新增 `evaluation/bird/scalar_count_shape.py`；模型、来源、预算、索引策略及原生评分保持一致。两侧各建独立索引，不复制跨侧缓存。候选的输出规则只读取公开问题、evidence 和生成的 SQL，不读取参考 SQL 或结果。

固定 24 道公开开发题：目标 `BIRD-PG-0092`，边界题 `BIRD-PG-0072`、`BIRD-PG-0356`、`BIRD-PG-0239`，以及既有成功回归 20 题。此轮每侧最多生成 24 题，单工作区最多 48 题；不运行保留集。`m2_pg_v1` 协议校验和独立原生复评需要冻结的 holdout 文件及 scorer 文件留在代码包内，但正式生成入口只选这 24 道开发题。

包 ID：`c57344fe558c72d03eb27da90a84a528987f8e84803205b9bed3d2b7c971019b`。代码清单：基线 99 文件，候选 100 文件。包：`M3_E04_pair24_scalar_count_v2_20261024.zip`，SHA-256：`26049e11141dfb40ff981f7d64cb062204576a0d49d4ade9902da06d0462f35d`。请只上传 v2 交付包。

## 1. 上传与准备

从本地项目根目录上传 ZIP 和 `.zip.sha256` 至服务器项目根目录。SSH 登录服务器后执行：

```bash
cd "$HOME/Python_work/askdata_studio_ops_release"
tr -d '\r' < M3_E04_pair24_scalar_count_v2_20261024.zip.sha256 | sha256sum -c -

tools_root="$HOME/Python_work/m3_e04_pair24_tools_20261024_r2"
test ! -e "$tools_root"
unzip -n -q M3_E04_pair24_scalar_count_v2_20261024.zip -d "$tools_root"

bundle="$tools_root/m3_e04_pair24_scalar_count_v2_20261024"
work="$HOME/Python_work/m3_e04_pair24_scalar_count_20261024_r2"

"$HOME/.local/askdata/pg16-env/bin/pg_isready" \
  -h 127.0.0.1 -p 55432 -d askdata_m2_bird

python -u "$bundle/control/prepare_m3_e04_pair24.py" \
  --bundle-root "$bundle" \
  --source-backend "$HOME/Python_work/askdata_studio_ops_release/backend" \
  --workspace "$work"
```

预期准备输出 `run_status=complete; model_calls=0; database_connected=false`。准备只复制冻结代码和协议材料；现有 `.env`、BIRD 数据与数据库凭据从原位置读取，凭据内容不复制入工作区。工作区只能准备一次。网络或模型失败后保留旧工作区和报告，下一次使用新的 `work` 名称。

## 2. 静态与 DNS/HTTPS 预检

```bash
python -u "$work/control/run_m3_e04_pair24.py" \
  --workspace "$work" --check-only
```

预期 `run_status=complete`、`phase=preflight_with_process_dns_https`，模型调用为 0。它核对两侧冻结代码、24 题选择、协议/来源、模型公开配置和进程内 DNS/HTTPS 连通性。失败时保留 `reports/e04_pair24_preflight_server.json` 与相应 `_checks`；该工作区不应进入生成。

## 3. 有界模型连接检查

```bash
python -u "$work/control/run_m3_e04_pair24.py" \
  --workspace "$work" --model-probe
```

预期 `run_status=complete`、`phase=transport_model_probe_complete`。这一步只用固定短文本测试一次 10 输入 embedding 批次，最多 2 次 HTTP 尝试，独立登记，不读取题目或 Gold。失败时保留报告并在网络恢复后使用新工作区。

## 4. 正式同轮对照

```bash
python -u "$work/control/run_m3_e04_pair24.py" \
  --workspace "$work"
```

预期 `run_status=complete`、`phase=complete`，生成 `reports/e04_pair24_comparison_server.json`。流程依次完成基线 24 题捕获、候选 24 题捕获，然后各自用保存的 SQL 做无模型原生复评。生成失败后不在同一工作区续跑，也不覆盖报告；只有两份捕获都完整、原生复评中断时，核对证据后才能使用一次 `--replay-only`，且不会重新调用模型。

## 5. 下载核对材料

从同一个 `$work` 保留目录结构下载：

```text
reports/e04_pair24_preflight_server.json
reports/e04_pair24_transport_model_probe_server.json
reports/e04_pair24_server.json
reports/e04_pair24_comparison_server.json
transport_dependency_lock.json
baseline/backend/evaluation/results/m3_e04_pair24_baseline_capture_server.json
baseline/backend/evaluation/results/m3_e04_pair24_baseline_native_server.json
candidate/backend/evaluation/results/m3_e04_pair24_candidate_capture_server.json
candidate/backend/evaluation/results/m3_e04_pair24_candidate_native_server.json
```

如果失败，先下载主报告及它指明的日志和已生成的子报告；保留原始文件，不重命名为成功报告。

## 预定判断

- 固定分母 24；逐题核对 0092 是否返回单个总数，实际 SQL 的人口、薪资区间、关联和计算口径是否正确，不能只依赖原生匹配标志。
- 观察 0072、0356、0239 的首次 SQL、校验反馈及最终输出，确认规则没有强制使用 `COUNT(*)` 或误拒合法的内层分组。
- 既有成功回归 20 题全部保留；候选须超过同轮基线，且 0092 原生正确，才能通过自动筛选。任何其它退化逐题审查。
- 分开报告索引准备、逐题模型尝试、Token、p95 耗时；`chat` Token 与 p95 超过基线 20% 时先审查成本。来源、只读角色、隔离和预算仍按原协议核对。
- 这是公开开发集的工程筛选，不是正式 EX、保留集结果或统计显著性证明。
