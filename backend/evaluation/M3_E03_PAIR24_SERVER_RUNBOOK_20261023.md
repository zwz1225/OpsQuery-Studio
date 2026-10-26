# M3 E03：0407 关系与双列输出的服务器同轮对照

2026-10-23 更新：本页为原包的历史说明。服务器尝试曾受 PostgreSQL 未运行及临时 DNS 解析失败影响，尚未取得有效 E03 对照结论。新的服务器运行请使用 [公共连接层 v2 / r2 说明](M3_E03_TRANSPORT_V2_SERVER_RUNBOOK_20261023.md)，保留本页原包及失败报告。

日期：2026-10-23。状态：本地候选、隔离包、控制脚本和静态校验完成；服务器模型运行待执行。

## 固定范围

本轮沿用 E02 的相同 development24 题目与顺序。主目标为 `BIRD-PG-0407`，观察 `BIRD-PG-1479` 是否保持正确，其余20道既有成功题用于回归。两侧都从已冻结的 E02 候选代码出发，均启用 `--schema-coverage --intent-candidate --condition-relations`。E03 侧增加来源绑定的不完整关系候选、公开双列输出提示，以及 `--output-contract --relation-output`；不更改评分、Gold、模型生成次数或字段上限。两侧分别建索引，并在同一服务器使用相同数据、模型配置和预算。仅在两份捕获完成后独立无模型原生复评。本轮不运行 holdout，也不代表正式 EX。

同步包位于项目根目录：`M3_E03_pair24_sync_20261023.zip` 和同名 `.zip.sha256`。SHA-256：

```text
61e9af6373f7b41058ddba50658c9f2ea4823fde20ae1b3624ea9beac38956e9  M3_E03_pair24_sync_20261023.zip
```

包内为98文件的 E02 基线、99文件的 E03 候选、24题题单和四个 E03 控制脚本；不包含 `.env`、数据库、密码或模型密钥。下面命令在远程服务器的 `(py311)` 环境执行。

## 1. 上传、校验、解压

将两个文件上传到 `~/Python_work/`，再执行：

```bash
cd "$HOME/Python_work"
sha256sum -c M3_E03_pair24_sync_20261023.zip.sha256 && \
test ! -e "$HOME/Python_work/m3_e03_tools_20261023" && \
unzip -n -q M3_E03_pair24_sync_20261023.zip \
  -d "$HOME/Python_work/m3_e03_tools_20261023"
```

摘要必须显示 `OK`。每一步失败即停止，不覆盖同名目录或既有报告。

## 2. 准备独立目录

```bash
python -u "$HOME/Python_work/m3_e03_tools_20261023/m3_e03_pair24_bundle_20261023/control/prepare_m3_e03_pair24.py" \
  --bundle-root "$HOME/Python_work/m3_e03_tools_20261023/m3_e03_pair24_bundle_20261023" \
  --source-backend "$HOME/Python_work/askdata_studio_ops_release/backend" \
  --workspace "$HOME/Python_work/m3_e03_pair24_20261023"
```

预期 `run_status=complete; model_calls=0; database_connected=false`。默认读取原项目的 BIRD 数据目录与 `.env` 路径，以及用户目录中的 M2 数据库凭据文件；若路径有变动，可按 `--help` 分别指定 `--data-root`、`--model-config-file`、`--credentials-file`。该步骤只检查私密文件存在，不复制内容，且至少需要2 GiB磁盘空余。

## 3. 静态预检

```bash
python -u "$HOME/Python_work/m3_e03_pair24_20261023/control/run_m3_e03_pair24.py" \
  --workspace "$HOME/Python_work/m3_e03_pair24_20261023" --check-only
```

下载 `reports/e03_pair24_preflight_server.json` 核对：`run_status=complete`、`phase=static_preflight_only`、`new_model_request_count=0`。这一步不证明实时 PostgreSQL、模型与隔离状态；正式运行还会重新检查。

## 4. 一次性同轮生成与复评

静态预检通过后执行一次：

```bash
test ! -e "$HOME/Python_work/m3_e03_pair24_20261023/reports/e03_pair24_driver.log" && \
nohup python -u "$HOME/Python_work/m3_e03_pair24_20261023/control/run_m3_e03_pair24.py" \
  --workspace "$HOME/Python_work/m3_e03_pair24_20261023" \
  > "$HOME/Python_work/m3_e03_pair24_20261023/reports/e03_pair24_driver.log" 2>&1 < /dev/null &
```

检查进度：

```bash
tail -n 40 "$HOME/Python_work/m3_e03_pair24_20261023/reports/e03_pair24_driver.log"
pgrep -af '[p]ython.*run_m3_e03_pair24'
```

子任务日志在 `reports/logs/`。网络断开或日志暂时为空时不要再启动第二次；工作区会登记一次生成尝试，两侧各最多24题。

## 5. 需要下载的报告

```text
reports/e03_pair24_server.json
reports/e03_pair24_comparison_server.json
baseline/backend/evaluation/results/m3_e03_baseline24_capture_server.json
baseline/backend/evaluation/results/m3_e03_baseline24_native_server.json
candidate/backend/evaluation/results/m3_e03_candidate24_capture_server.json
candidate/backend/evaluation/results/m3_e03_candidate24_native_server.json
```

连同 `workspace.json`、`preparation.json`、`reports/` 中的检查记录和日志一起保留。只有两份捕获均完整、失败仅发生在原生复评阶段时，才能用一次 `--replay-only` 无模型恢复；原报告必须保留。

## 6. 验收观察

自动筛查要求：0407 候选原生结果匹配且授权 Schema 图确实变化；整体净增至少1题；20道既有成功题及1479保持正确；索引和逐题模型 token、HTTP调用及逐题 p95 可核验，候选不超过同轮基线120%。缺失用量按未知处理。还要人工逐字审查0407首次及最终 SQL 是否同时输出 `cards.subtypes` 和 `cards.supertypes`、限制 German、采用有授权依据的 `foreign_data.uuid` 与 `cards.uuid` 关联，并核对孤儿记录及 JOIN 选择；原生结果相等本身不足以接受语义。若不满足，保留本轮报告作为失败证据，不改评分或重跑追分。
