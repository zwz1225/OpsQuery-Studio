# M3 E07 r10：群体期间聚合与精简提示 development24 同轮对照

日期：2026-10-25。范围：相同development24题目，观察1480、0050、0173、0459及20题成功回归。r9已固定为有效实验、候选未通过；0173继续作为独立遗留项。

## 本轮处理与验收

两侧同样启用 `--categorical-population`，仅candidate启用 `--semantic-planning` v2。两侧producer字节相同、数据来源/模型/预算相同，分别新建索引并新生成24题。candidate提示要求先定粒度与指标，再聚合和排序，特别区分群体峰值月份、单条记录极值、平均值及比率；输出字段指导保留且压缩。没有修改原生评分和20%成本门槛。

准备控制器直接从已核对哈希的包内字面量读取提示策略，不再导入主项目的旧 `intent.py`。下面的命令不依赖PYTHONPATH，也不需要先同步主项目的业务代码。

本地49项相关测试通过；附加指导从1137缩至666 UTF-8字节，连同system转述共缩短44.37%。这不是实际模型Token验证；模型SQL语义及真实成本要由本轮服务器结果确认。

验收时仍须人工确认：

- 1480：对2013年的SME客户按月汇总 `SUM(consumption)`，再选峰值月份。单条记录最大值即使结果匹配Gold，也不通过。报告增加GROUP BY/SUM必要结构检查；这不能代替对正确月份、指标、范围与关联的人工核实。
- 0050：地址在前，学校名称在后；检查名称字段归属并报告NULL现状，不能把两个名称字段同为NULL当作普遍等价证据。
- 0459：仅输出所需名称，比较指标仅用于排名；NULL排序正确。
- 0173：记录当前表现及实际SQL，保持独立遗留项。不得加入题号处理或把金额3539硬编码成修正规则。
- 回归20题保持，观察题不得发生原生退步；Chat Token和墙钟P95增长均不超过20%。原生评分分母仍为24。

## 上传与准备

将以下两个文件上传至 `$HOME/Python_work/askdata_studio_ops_release/`：

```text
m3_categorical_population_pair24_v1_20261025_r10.zip
m3_categorical_population_pair24_v1_20261025_r10.zip.sha256
```

先校验压缩包：

```bash
cd "$HOME/Python_work/askdata_studio_ops_release"
tr -d '\r' < m3_categorical_population_pair24_v1_20261025_r10.zip.sha256 | sha256sum -c -
```

显示OK后，准备全新的r10目录：

```bash
tools_root="$HOME/Python_work/m3_categorical_population_pair24_tools_20261025_r10"
work="$HOME/Python_work/m3_categorical_population_pair24_20261025_r10"

test ! -e "$tools_root" &&
test ! -e "$work" &&
unzip -n -q m3_categorical_population_pair24_v1_20261025_r10.zip -d "$tools_root"

bundle="$tools_root/m3_categorical_population_pair24_v1_20261025_r10"
```

解压成功后执行准备：

```bash
python -E -s -u "$bundle/control/prepare_m3_e07_pair24.py" \
  --bundle-root "$bundle" \
  --source-backend "$HOME/Python_work/askdata_studio_ops_release/backend" \
  --workspace "$work"
```

预期为 `run_status=complete; model_calls=0; database_connected=false`。路径与配置来自既有主项目，但语义策略校验以r10冻结内容为准。

## 预检、模型探测与正式运行

依次执行，每步complete后再执行下一步：

```bash
python -E -s -u "$work/control/run_m3_e07_pair24.py" \
  --workspace "$work" --check-only
```

预期 `phase=preflight_with_process_dns_https`。

```bash
python -E -s -u "$work/control/run_m3_e07_pair24.py" \
  --workspace "$work" --model-probe
```

预期 `phase=transport_model_probe_complete`。此探测独立记账，不读取题目、不连接数据库。

```bash
"$HOME/.local/askdata/pg16-env/bin/pg_isready" \
  -h 127.0.0.1 -p 55432 -d askdata_m2_bird &&
python -E -s -u "$work/control/run_m3_e07_pair24.py" \
  --workspace "$work"
```

正式运行顺序为baseline生成、candidate生成，再分别原生复评。完成时应为 `run_status=complete`、`phase=complete`、`errors=[]`。每个workspace只预约一次生成。若失败，保留报告并检查失败阶段，不在原目录重新生成，也不因不满意分数重跑。

## 下载证据

服务器根目录：

```text
$HOME/Python_work/m3_categorical_population_pair24_20261025_r10/
```

下载10份文件并保持相对位置：

```text
reports/e07_pair24_preflight_server.json
reports/e07_pair24_transport_model_probe_server.json
reports/e07_pair24_server.json
reports/e07_pair24_comparison_server.json
transport_dependency_lock.json
transport_model_probe_receipt.json
baseline/backend/evaluation/results/m3_e07_pair24_baseline_capture_server.json
baseline/backend/evaluation/results/m3_e07_pair24_baseline_native_server.json
candidate/backend/evaluation/results/m3_e07_pair24_candidate_capture_server.json
candidate/backend/evaluation/results/m3_e07_pair24_candidate_native_server.json
```

本地放置于 `E:\PythonLearn\m3_categorical_population_pair24_20261025_r10\`。完整的服务器workspace含子检查日志与探测原件，也应保留以便追查。

## 冻结身份

- ZIP SHA-256：`a83e77b68d97883d79d2ad6cc26ad5fc6df57fdfcbb02d04c460b5e83a079f56`。
- Bundle ID：`cd6d0de51baf078baeb1c6a5035319dcee9ae33c9b496940340e4f6ddf37ecaa`。
- 实验身份：`m3_e07_population_grain_revision_development24_v2`。
- 提示策略：`bird_public_query_semantics_prompt_v2`，仅candidate生效。
- 清单记录r9比较报告摘要与本轮有限改动决策摘要。每侧producer为103文件，字节一致。
