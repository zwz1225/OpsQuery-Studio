# M3 E01：24题同轮基线／候选运行说明

日期：2026-10-21。状态：本地脚本及隔离目录准备；服务器生成与原生复评尚未执行。

## 1. 本轮范围与同步清单

上传项目根目录的 `M3_E01_pair24_sync_20261021.zip`，不需要覆盖服务器现有项目文件。ZIP 的 SHA-256 见同目录 `.sha256` 文件及本地交付记录 `evaluation/m3_e01_pair24_delivery_20261021.json`。

包内根目录是 `m3_e01_pair24_bundle_20261021/`：

| 内容 | 用途 |
| --- | --- |
| `control/prepare_m3_e01_pair24.py` | 独占创建新的对照目录，不读取或复制私密文件 |
| `control/run_m3_e01_pair24.py` | 静态检查、两次生成、原生复评与逐题比较 |
| `control/m3_pair_common.py` | 清单、路径、来源、索引字节和比较检查 |
| `control/m3_pair_side.py` | 在各自代码目录内校验运行身份及完整报告 |
| `payload/baseline/` | 已保存并校验的 M2 v4 原始代码，96个生产文件 |
| `payload/candidate/` | 输出契约候选，97个生产文件；只新增模块并改动两处最小接入 |
| `payload/shared/` | 原协议、题目清单、受信导入与历史就绪材料；不作为当前实时就绪证明 |
| `bundle_manifest.json`、`README.md` | 逐文件摘要、固定实验参数及本说明 |

生产差异只有 `evaluation/bird/output_contract.py`、`case_worker.py`、`diagnostic_runner.py`。不修改原 Gold、EX、检索、SQL修复和预算规则。控制脚本另行绑定摘要，不假冒原生产代码身份。

两边分别使用 `baseline/backend/` 和 `candidate/backend/`，有各自报告、snapshot、索引目录；共同指向服务器原有已验证数据、模型配置路径和数据库凭据路径。包内没有 `.env`、账号密码或数据库转储。不要把密码写入命令行。

固定24题为3个主目标、1个混合观察、20个原成功题，覆盖8个开发域。本轮只允许一次基线24题生成和一次候选24题生成，不自动扩展80题，不运行holdout。保留旧项目及M2证据。

## 2. 上传与解压

以下命令在服务器 Bash 执行，保持既有 `(py311)` 环境。将 ZIP 及同名 `.zip.sha256` 上传到 `~/Python_work/`。如果目录名已存在，先检查其内容，不要覆盖或删除旧尝试。

```bash
cd "$HOME/Python_work"
sha256sum -c M3_E01_pair24_sync_20261021.zip.sha256 && \
test ! -e "$HOME/Python_work/m3_e01_tools_20261021" && \
  unzip -n M3_E01_pair24_sync_20261021.zip \
    -d "$HOME/Python_work/m3_e01_tools_20261021"
```

必须先看到摘要校验 `OK` 再解压；校验失败时停止。`unzip -n` 不覆盖文件，目录存在时第二条命令不会解压。

## 3. 准备独立目录：0模型调用、0数据库连接

需要同一文件系统至少2GiB可用空间。默认沿用原项目数据目录 `backend/data/external/bird_mini_dev`、模型配置 `backend/.env`，以及 `~/.local/share/askdata/m2_bird_credentials.json`。源目录不存在时脚本会拒绝；实际数据在别处时加 `--data-root /实际路径`，配置在别处时用对应可选参数。

```bash
python -u "$HOME/Python_work/m3_e01_tools_20261021/m3_e01_pair24_bundle_20261021/control/prepare_m3_e01_pair24.py" \
  --bundle-root "$HOME/Python_work/m3_e01_tools_20261021/m3_e01_pair24_bundle_20261021" \
  --source-backend "$HOME/Python_work/askdata_studio_ops_release/backend" \
  --workspace "$HOME/Python_work/m3_e01_pair24_20261021"
```

成功输出 `run_status=complete; model_calls=0; database_connected=false`。准备报告是新目录中的 `preparation.json`。脚本不向原项目写入内容，不复制数据库或私密配置。

## 4. 静态预检：0模型调用、0数据库连接

```bash
python -u "$HOME/Python_work/m3_e01_pair24_20261021/control/run_m3_e01_pair24.py" \
  --workspace "$HOME/Python_work/m3_e01_pair24_20261021" \
  --check-only
```

报告：`~/Python_work/m3_e01_pair24_20261021/reports/pair24_preflight_server.json`。

预期 `run_status=complete`、`phase=static_preflight_only`、`new_model_request_count=0`。检查实际96/97生产代码、历史证据链、原协议、固定24题、同一Python/内核/依赖、公开模型配置及文件路径。要求 Linux、Psycopg 3.2.13、psycopg-pool 3.2.8、SQLGlot 30.17.0；隔离依赖由既有 seccomp 探针在实际运行验证。当前已有环境不满足时，先查看检查日志，不直接改版本。

**静态通过不代表数据库实时就绪。** 正式生成时原runner仍重新执行来源、权限、数据、隔离、硬超时及预算探针。初次部署可先下载本预检JSON核对，再运行下一节。

已有预检报告不能覆盖。排查后仅重新检查可用新文件名：

```bash
python -u "$HOME/Python_work/m3_e01_pair24_20261021/control/run_m3_e01_pair24.py" \
  --workspace "$HOME/Python_work/m3_e01_pair24_20261021" \
  --check-only \
  --output "$HOME/Python_work/m3_e01_pair24_20261021/reports/pair24_preflight_server_v2.json"
```

## 5. 正式启动一次24+24同轮对照

确认PostgreSQL运行、现有模型和数据库凭据有效；保持同一服务器、环境、公开模型配置及源数据，不在两边之间同步代码或修改配置。

```bash
test ! -e "$HOME/Python_work/m3_e01_pair24_20261021/reports/pair24_driver.log" && \
nohup python -u "$HOME/Python_work/m3_e01_pair24_20261021/control/run_m3_e01_pair24.py" \
  --workspace "$HOME/Python_work/m3_e01_pair24_20261021" \
  > "$HOME/Python_work/m3_e01_pair24_20261021/reports/pair24_driver.log" 2>&1 < /dev/null &
```

先做基线生成及完整性检查，将基线8域已验证索引的同身份、同字节内容复制到候选的独立索引目录，再做候选生成。候选继续通过原有索引身份和授权文档校验，不强行命中缓存。索引生产代码8个文件在两边完全相同；比较时要求8域索引身份与字节摘要一致，候选实际命中缓存。基线建索引费用单列，候选不是再次付费建立另一份embedding。

**两边生成报告都完整后**，才计算各自SHA并执行独立原生复评，最后逐题比较。相较最初计划，衔接顺序明确为“两份生成完成 → 两份复评”，在候选生成前不运行本轮新Gold复评。

每边每题仍是600秒、最多16次模型HTTP／10次chat、3次SQL工具，每轮最多3次生成和校验；独立复评0模型调用，每个已回答题2次结果SQL。未回答题计入24题分母，结果截断不评分。任一步检查失败就停止后续步骤，不自动生成重试。

### 查看进度

```bash
tail -n 40 "$HOME/Python_work/m3_e01_pair24_20261021/reports/pair24_driver.log"
pgrep -af '[p]ython.*run_m3_e01_pair24'
```

题目进度在 `reports/logs/baseline_generation.log` 和 `candidate_generation.log`；后者要到候选开始才创建。

```bash
python - <<'PY'
import json
from pathlib import Path
p = Path.home() / 'Python_work/m3_e01_pair24_20261021/reports/pair24_server.json'
if not p.exists():
    print('尚未创建流程报告，请先看driver日志')
else:
    r = json.loads(p.read_bytes())
    for key in ('run_status', 'phase', 'comparison_report', 'new_model_request_count', 'summary', 'errors'):
        print(key + ':', r.get(key))
PY
```

`run_status=complete`表示本次对照执行完整，不等于候选被接纳。`automatic_screen_pass=false`同样是有效实验结果，不因此重跑追分。模型别名随服务变化，temperature=0也不保证两次完全确定；本轮是同轮工程对照，不作统计显著性结论。

## 6. 中断与原生复评恢复

SSH断线后先查进程和报告。使用nohup时断线不意味着任务失败，不要再次启动生成。目录有一次生成尝试登记后，脚本拒绝第二次生成；不能靠换输出名续跑或补生成。

仅在**两份生成报告均完整且身份校验通过**、失败发生于之后原生复评时，支持一次0模型恢复：

```bash
python -u "$HOME/Python_work/m3_e01_pair24_20261021/control/run_m3_e01_pair24.py" \
  --workspace "$HOME/Python_work/m3_e01_pair24_20261021" \
  --replay-only
```

它复用已完整的原生报告，另存失败边为 `*_native_recovery1_server.json`，保留原失败报告；不启动模型，不覆盖证据。恢复登记仅一次。若生成中断或来源变化，先交回失败报告与日志，停止本次实验，不自行新建目录重复生成。失败复评的调用/耗时以原失败报告另存，不混进最终完整报告的两次SQL预算。

## 7. 下载材料与判定

请下载新工作目录中的 `preparation.json`、`workspace.json`、整个 `reports/`，以及以下4份完整JSON：

```text
baseline/backend/evaluation/results/m3_e01_baseline24_capture_server.json
baseline/backend/evaluation/results/m3_e01_baseline24_native_server.json
candidate/backend/evaluation/results/m3_e01_candidate24_capture_server.json
candidate/backend/evaluation/results/m3_e01_candidate24_native_server.json
```

若用过恢复，额外下载 `*_native_recovery1_server.json` 并保留原失败文件。这些文件放到本地 `backend/evaluation/results/m3_e01_pair24_server_20261021/` 下，保持工作目录相对层级，便于一次核对。

比较报告是 `reports/pair24_comparison_server.json`；完整流程报告是 `reports/pair24_server.json`。恢复时分别增加 `_recovery`／使用 `pair24_native_recovery_server.json`。

按固定24题查看错转对、对转错、3个主目标、20个成功回归、8域结果、初始授权Schema、每次SQL／校验／预算和候选输出契约。筛选线沿用首轮计划：主目标至少2/3、净增至少1题、20成功全部保留；chat token总量及逐题p95增长不超过20%，usage未知不填0。另核对两边授权Schema是否相同；不同时单列为归因干扰，不能直接认定提示收益。

1479的币种条件及0407的非NULL条件必须人工审查；原生匹配不自动代表业务缺口修复。自动检查通过后仍需语义审查，再决定是否另行安排完整80题。未通过就归档本候选与原因，不自动扩大实验。

本地测试只覆盖文件准备、顺序、摘要、故障恢复和报告校验；真实Linux隔离、PostgreSQL与模型调用仍待服务器验证。
