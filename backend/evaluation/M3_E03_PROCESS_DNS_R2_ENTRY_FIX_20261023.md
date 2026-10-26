# E03 process DNS v1 r2：修正实际模型检查入口

日期：2026-10-23。状态：本地修正；服务器复验待完成。

## 原因与修正

服务器 r1 的两侧静态、显式DNS及HTTPS检查通过，进入 `shared_transport_embedding_probe` 后子入口失败。检查交付代码发现确定缺陷：`model_probe()` 从 `context()` 返回的工作区记录读取 `row['workspace']`，但 `workspace.json` 未定义该键；工作区路径实际位于生产目录的 `m3_context.json`。这会在模型检查登记和创建模型客户端之前触发 `KeyError: 'workspace'`。

本地已执行冻结 r1 的实际 `model_probe()` 函数复现该错误，并断言模型客户端尚未创建。新增测试还实际调用修正函数，验证路径读取、10条输入、结果维度、成功/失败用量保存和重复登记拒绝。此前控制器测试使用了模拟子入口，未覆盖这一字段契约，这是交付测试的遗漏。

r2 改为从生产目录 `m3_context.json` 读取工作区及包身份。与 r1 比较，生产侧全部99/100个文件字节相同，控制器仅 `m3_e03_pair_side.py` 改变；解析服务、TLS、版本/二进制锁、模型配置、请求预算、题单、语义策略和原生评分不变。保留 r1 包和全部服务器报告，不对原报告回填用量。

本次交付不证明实际模型POST已通过；该结论等待服务器执行。冻结 r1 的本地复现也不替代服务器原始日志。

## 1. 上传修正版

将本地项目根目录两个文件上传至服务器 `~/Python_work/askdata_studio_ops_release/`：

```text
M3_E03_pair24_process_dns_v1_20261023_r2.zip
M3_E03_pair24_process_dns_v1_20261023_r2.zip.sha256
```

ZIP SHA-256：`f34688a688a0bacd01cb94cc274cba4f79f112b98686a78d5cf0dec3d01a38fc`。

包身份：`483c6a685bd96a5b5e495012ff37fc879011d4216b5fd40bb0abed2895759a2c`。

## 2. 校验、解压

```bash
cd "$HOME/Python_work/askdata_studio_ops_release"

sha256sum -c M3_E03_pair24_process_dns_v1_20261023_r2.zip.sha256 && \
test ! -e "$HOME/Python_work/m3_e03_tools_process_dns_v1_20261023_r2" && \
unzip -n -q M3_E03_pair24_process_dns_v1_20261023_r2.zip \
  -d "$HOME/Python_work/m3_e03_tools_process_dns_v1_20261023_r2"
```

只有校验及解压成功后才继续。无需覆盖原 backend 或编辑冻结工作区。

## 3. 新工作区直接执行带内置预检的模型连接检查

r1 已通过的检查继续保留为证据。r2 的 `--model-probe` 会自动执行两侧静态及显式DNS/HTTPS检查，然后锁定依赖，检查通过后才执行一次embedding批请求，因此本次可合并准备与模型检查，无需额外停在一次 `--check-only`。

```bash
bundle="$HOME/Python_work/m3_e03_tools_process_dns_v1_20261023_r2/m3_e03_pair24_process_dns_v1_20261023_r2"
work="$HOME/Python_work/m3_e03_pair24_process_dns_v1_20261023_r2"

python -u "$bundle/control/prepare_m3_e03_pair24.py" \
  --bundle-root "$bundle" \
  --source-backend "$HOME/Python_work/askdata_studio_ops_release/backend" \
  --workspace "$work" && \
python -u "$work/control/run_m3_e03_pair24.py" \
  --workspace "$work" --model-probe
```

仍然是10条固定短文本、最多2次模型HTTP、180秒、0次chat/SQL，不使用题目生成、不创建正式 `attempt/`。失败时保存报告，不用改名绕过登记再次调用模型。

预期：

```text
run_status=complete
phase=transport_model_probe_complete
errors=[]
```

报告路径：

```text
reports/e03_transport_model_probe_server.json
reports/e03_transport_model_probe_server_checks/model_probe.json
transport_dependency_lock.json
```

请先发送终端输出并下载上述三份文件，核对依赖、实际POST、10条向量、1024维和预算。服务器未完成前不宣布E03通过。

## 4. 核对通过后正式运行

```bash
work="$HOME/Python_work/m3_e03_pair24_process_dns_v1_20261023_r2"
"$HOME/.local/askdata/pg16-env/bin/pg_isready" \
  -h 127.0.0.1 -p 55432 -d askdata_m2_bird && \
python -u "$work/control/run_m3_e03_pair24.py" --workspace "$work"
```

正式运行门槛、独立索引、24题捕获、无模型原生复评和语义/成本验收沿用 [公共连接层运行说明](M3_E03_PROCESS_DNS_PAIR24_SERVER_RUNBOOK_20261023.md)，使用本页 r2 工作区路径。
