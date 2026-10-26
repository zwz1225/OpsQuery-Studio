# M3 E05：公开端点作用域的独立 24 题同轮对照

## 范围与身份

基线、候选都从已冻结的 E02 条件/关系语义和相同进程内 DNS/HTTPS 连接代码出发。候选只修改 `evaluation/bird/intent.py`、新增 `evaluation/bird/endpoint_scope.py`，向模型提供公开 evidence 指定的端点提示。提示为 advisory，不改写 SQL，不增加硬拒绝。模型、来源、预算、授权 Schema、索引策略及原生评分保持一致；两侧各建独立索引。

固定 24 道公开开发题：目标 `BIRD-PG-0239`，边界题 `BIRD-PG-0072`、`BIRD-PG-0092`、`BIRD-PG-0356`，及既有成功回归 20 题，其中包含合法双端点题 `BIRD-PG-0206`。每侧最多生成 24 题，共最多 48 题；不运行保留集。协议校验和独立原生复评需要冻结的 holdout/scorer 文件保留在包内；生成入口只选这 24 题。

包 ID：`456e1aae181956c8e28c2193b71f8a750e50f8bc5a738043e8ec5de11b192a53`。代码清单：基线 99 文件、候选 100 文件。包：`M3_E05_pair24_endpoint_scope_v1_20261024.zip`；SHA-256：`3d1295b37c35ff31eee5b84ec6fe65e5fbfffdca2342df8a879e275b2e6aa12b`。

## 1. 上传与准备

把 ZIP 和 `.zip.sha256` 放到服务器项目根目录，SSH 登录后执行：

```bash
cd "$HOME/Python_work/askdata_studio_ops_release"
tr -d '\r' < M3_E05_pair24_endpoint_scope_v1_20261024.zip.sha256 | sha256sum -c -

tools_root="$HOME/Python_work/m3_e05_pair24_tools_20261024_r1"
test ! -e "$tools_root"
unzip -n -q M3_E05_pair24_endpoint_scope_v1_20261024.zip -d "$tools_root"

bundle="$tools_root/m3_e05_pair24_endpoint_scope_v1_20261024"
work="$HOME/Python_work/m3_e05_pair24_endpoint_scope_20261024_r1"

"$HOME/.local/askdata/pg16-env/bin/pg_isready" \
  -h 127.0.0.1 -p 55432 -d askdata_m2_bird

python -u "$bundle/control/prepare_m3_e05_pair24.py" \
  --bundle-root "$bundle" \
  --source-backend "$HOME/Python_work/askdata_studio_ops_release/backend" \
  --workspace "$work"
```

预期 `run_status=complete; model_calls=0; database_connected=false`。准备只复制冻结代码和协议材料；现有 `.env`、BIRD 数据与数据库凭据从原位置读取，不复制凭据内容。工作区只准备一次；失败后保留原报告，新尝试使用新的 `tools_root`/`work` 名称。

## 2. 静态与 DNS/HTTPS 预检

```bash
python -u "$work/control/run_m3_e05_pair24.py" \
  --workspace "$work" --check-only
```

预期 `run_status=complete`、`phase=preflight_with_process_dns_https`，模型调用为 0。失败时保留 `reports/e05_pair24_preflight_server.json` 和相应 `_checks`，不进入生成。

## 3. 有界模型连接检查

```bash
python -u "$work/control/run_m3_e05_pair24.py" \
  --workspace "$work" --model-probe
```

预期 `run_status=complete`、`phase=transport_model_probe_complete`。它只用固定短文本测试一个 10 输入 embedding 批次，最多 2 次 HTTP 尝试，不读取题目或 Gold。失败时保留报告，网络恢复后使用新工作区。

## 4. 正式同轮对照

```bash
python -u "$work/control/run_m3_e05_pair24.py" \
  --workspace "$work"
```

预期 `run_status=complete`、`phase=complete`，并生成 `reports/e05_pair24_comparison_server.json`。流程依次完成基线和候选各 24 题捕获，再各自用保存的 SQL 做无模型原生复评。生成失败后不在同一工作区续跑或覆盖报告；只有两份捕获完整而原生复评中断时，核对证据后才可使用一次 `--replay-only`。

## 5. 下载核对材料

从同一 `$work` 保持相对目录下载：

```text
reports/e05_pair24_preflight_server.json
reports/e05_pair24_transport_model_probe_server.json
reports/e05_pair24_server.json
reports/e05_pair24_comparison_server.json
transport_dependency_lock.json
baseline/backend/evaluation/results/m3_e05_pair24_baseline_capture_server.json
baseline/backend/evaluation/results/m3_e05_pair24_baseline_native_server.json
candidate/backend/evaluation/results/m3_e05_pair24_candidate_capture_server.json
candidate/backend/evaluation/results/m3_e05_pair24_candidate_native_server.json
```

若失败，先保留并下载主报告、指向的日志和已生成子报告，不重命名为成功报告。

## 预定判断

- 固定分母 24。逐题核对 0239 的首次和最终 SQL 是否只对公开 evidence 指定的 `atom_id` 施加 `LIKE 'TR%_19'`，并核对 `bond_id` 计数、原生结果和修复成本。不能只看原生匹配标志。
- 核对 0206 的合法双端点查询仍保留。0072 的 `City` 检索和输出形态、0092 的标量计数、0356 的边界作为观察，不归因于本候选。
- 成功回归 20 题全部保留；候选须超过同轮基线且 0239 原生正确，才能通过自动筛选。其它退化逐题审查。
- 分开核对索引准备和逐题调用、Token、p95 耗时；chat Token 或 p95 超过基线 20% 时审查成本。来源、只读角色、隔离和预算按原协议核对。
- 这是公开开发集工程筛选，不是正式 EX、保留集结果或统计显著性证明。
