# M3 E02：Schema 条件上下文独立同轮对照

日期：2026-10-22。状态：本地控制脚本、隔离包与离线测试已完成；服务器预检及模型/数据库运行尚未执行。

## 实验问题与预登记范围

本轮只验证新增的公开条件与关联上下文能否帮助模型生成符合币种业务条件的 SQL。主目标为 `BIRD-PG-1479`，观察题为 `BIRD-PG-0407`；固定24题中其余20题是已成功回归题，另有两道 E01 主目标题保持在同一题单中。只运行 development，不接触 holdout。

基线使用已冻结的 M2 v4 生产快照。候选只叠加 E02 的四处既有模块修改和两个新模块。两侧的 schema coverage、intent 候选、修复策略、预算、题目顺序、数据库来源身份和公开模型配置保持一致；候选独有 `--condition-relations`。E01 输出契约关闭。基线和候选分别建立索引、使用独立目录和各自的代码身份；不复制索引、不强制命中缓存。索引构建的 embedding 用量会计入总模型调用与成本比较。

这是同一服务器、同一数据、同一配置下的一轮工程对照，不是正式 EX 测试或 holdout 成绩。两侧各最多生成24题；失败后不自动重新生成。候选通过自动筛查后仍需人工确认 1479 的 SQL 确实含有正确币种谓词及必要关联，并检查查询结果。

## 同步包

将项目根目录的 `M3_E02_pair24_sync_20261022_v5.zip` 与同名 `.zip.sha256` 上传到远程服务器 `~/Python_work/`。本地摘要：

```text
c37344a7a5f52f5d40735f629d7f0dc91bb4c0fad1557231f29b467eb0fb1524  M3_E02_pair24_sync_20261022_v5.zip
```

包中包含固定题单、96文件基线、98文件候选、校验清单和四个 E02 专用控制脚本。不包含 `.env`、数据库凭据、BIRD 数据库文件或服务器凭据。

## 1. 校验并解压

```bash
cd "$HOME/Python_work"
sha256sum -c M3_E02_pair24_sync_20261022_v5.zip.sha256 && \
test ! -e "$HOME/Python_work/m3_e02_tools_20261022_v5" && \
  unzip -n -q M3_E02_pair24_sync_20261022_v5.zip \
    -d "$HOME/Python_work/m3_e02_tools_20261022_v5"
```

只有摘要显示 `OK` 且解压成功后才继续。已存在目标目录时停止并保留现有内容。

## 2. 准备两份独立运行目录

沿用服务器现有 `(py311)` 环境、BIRD 数据目录、`backend/.env` 和 M2 凭据路径。脚本只检查私密文件是否存在，不读取或复制其内容。默认路径与 E01 相同；若 BIRD 数据目录位于其他位置，增加 `--data-root /实际路径`。

```bash
python -u "$HOME/Python_work/m3_e02_tools_20261022_v5/m3_e02_pair24_bundle_20261022_v5/control/prepare_m3_e02_pair24.py" \
  --bundle-root "$HOME/Python_work/m3_e02_tools_20261022_v5/m3_e02_pair24_bundle_20261022_v5" \
  --source-backend "$HOME/Python_work/askdata_studio_ops_release/backend" \
  --workspace "$HOME/Python_work/m3_e02_pair24_20261022_v5"
```

预期 `run_status=complete; model_calls=0; database_connected=false`。它会验证文件摘要和题单、复制隔离的生产文件，不会连接模型或数据库。至少需要2 GiB可用空间。旧 E01 工作区不受影响。

## 3. 静态预检

```bash
python -u "$HOME/Python_work/m3_e02_pair24_20261022_v5/control/run_m3_e02_pair24.py" \
  --workspace "$HOME/Python_work/m3_e02_pair24_20261022_v5" --check-only
```

报告为 `reports/e02_pair24_preflight_server.json`。只有 `run_status=complete`、`phase=static_preflight_only`、`new_model_request_count=0` 才通过静态预检。静态预检不证明实时数据库权限、数据版本、模型可用性或 Linux 隔离可用；正式运行会重新检查这些条件。先下载并核对该报告，再启动正式运行。

## 4. 正式同轮运行

确认静态预检通过，远程 PostgreSQL 和既有模型配置可用，且两侧未被改动。目录会登记一次生成尝试；正式运行最多执行基线24题和候选24题，先分别完成两边生成与完整性检查，然后才开始独立原生复评。

```bash
test ! -e "$HOME/Python_work/m3_e02_pair24_20261022_v5/reports/e02_pair24_driver.log" && \
nohup python -u "$HOME/Python_work/m3_e02_tools_20261022_v5/m3_e02_pair24_bundle_20261022_v5/control/run_m3_e02_pair24.py" \
  --workspace "$HOME/Python_work/m3_e02_pair24_20261022_v5" \
  > "$HOME/Python_work/m3_e02_pair24_20261022_v5/reports/e02_pair24_driver.log" 2>&1 < /dev/null &
```

查看日志和进程：

```bash
tail -n 40 "$HOME/Python_work/m3_e02_pair24_20261022_v5/reports/e02_pair24_driver.log"
pgrep -af '[p]ython.*run_m3_e02_pair24'
```

生成日志分别位于 `reports/logs/baseline_generation.log` 与 `candidate_generation.log`。不要因 SSH 断开或暂时没有新输出再次启动命令。换输出文件名也不会解除一次运行限制。

## 5. 报告与恢复

完整流程报告：`reports/e02_pair24_server.json`；逐题比较报告：`reports/e02_pair24_comparison_server.json`。两侧捕获、原生复评报告分别为：

```text
baseline/backend/evaluation/results/m3_e02_baseline24_capture_server.json
baseline/backend/evaluation/results/m3_e02_baseline24_native_server.json
candidate/backend/evaluation/results/m3_e02_candidate24_capture_server.json
candidate/backend/evaluation/results/m3_e02_candidate24_native_server.json
```

请下载以上文件以及 workspace 的 `preparation.json`、`workspace.json`、整个 `reports/` 目录。若失败发生在两份捕获均完整之后、且仅原生复评阶段中断，可以使用一次无模型恢复：

```bash
python -u "$HOME/Python_work/m3_e02_tools_20261022_v5/m3_e02_pair24_bundle_20261022_v5/control/run_m3_e02_pair24.py" \
  --workspace "$HOME/Python_work/m3_e02_pair24_20261022_v5" --replay-only
```

该模式不允许生成，只复用完整捕获和已完成的原生报告；原生复评失败报告保留，最多登记一次恢复。若任一生成中断、代码或来源身份改变，停止本轮并保留日志，不重跑模型。

## 6. 预登记筛查线

自动筛查同时要求：1479 候选原生结果正确；24题总体净增至少1题；20道既有成功回归题全部保留；模型总 token、HTTP 调用数及逐题 p95 均有可核验记录，且候选不超过基线的120%；1479候选侧实际 Schema 图发生变化。索引 embedding 用量包含在总 token 和 HTTP 数中。用量缺失按未知处理并使自动筛查不通过，不把未知当作0。0407 只作为诊断观察，不要求自动通过。

`automatic_screen_pass=true` 仍需人工检查 1479 SQL 的币种字段、字面值、关联表与原生结果，再决定 E02 是否支持这个策略。模型服务别名可能变化，temperature=0 也不保证输出确定；不因单题波动增加尝试或扩大到80题。
