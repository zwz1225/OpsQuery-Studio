# E03 process DNS v1 r1：公共连接层与独立配对实验

> r1 模型检查入口存在工作区字段读取错误。新部署使用 [r2 入口修复说明](M3_E03_PROCESS_DNS_R2_ENTRY_FIX_20261023.md)；本页 r1 命令和身份作为历史记录保留，公共连接策略及验收边界继续适用。

日期：2026-10-23。状态：本地接入完成；服务器预检、实际 embedding 检查及 E03 效果验收待执行。

## 1. 本次修正与身份

服务器 r3 的系统解析在约20秒返回 EAI_AGAIN，第二次30秒超时。独立报告 `e03_process_dns_https_probe_server.json` 的三轮显式 DNS/HTTPS 验证通过，脚本摘要与交付一致；这只支持继续验证新连接方案。

本包从不可变的 r3 两侧快照派生，双方应用相同的模型、索引和用量报告改动，并各新增相同的 `evaluation/bird/process_dns.py`。基线99个生产文件、候选100个；候选仍仅多输出契约模块，原5处语义差异保持。24题、20题回归、权限、数据/协议版本、Gold、SQL校验和原生评分保持原约定。旧E02结果、旧E03/r2/r3失败报告及成功独立探针均保留。

公共连接策略：

- 使用 `/usr/bin/dig` 直接向 `114.114.114.114` 查询 IPv4 A；不依赖 worker 的 PATH。固定已在服务器输出中出现的版本 `9.18.39-0ubuntu0.22.04.7-Ubuntu`；支持解析附加的 Extended Support Version 后缀。预检核对两侧真实版本和二进制 SHA-256，并独立保存 `transport_dependency_lock.json`。每次请求核对实际工具与锁；版本/二进制变化即停止。具体服务器依赖身份等待新预检确认。
- 每次模型 HTTP 尝试最多一次DNS查询、一次地址连接。`dig -r +time=3 +tries=1`，忽略 `.digrc`，使用UDP，子进程上限5秒；截断应答失败，NXDOMAIN不重试。不隐含执行更多DNS或地址尝试。
- 每次HTTP尝试重新解析，不缓存服务IP。验证CNAME链、正TTL、公网IPv4及应答归属，连接前拒绝过期答案。第二次既有模型尝试可选择同轮DNS列表的第二个地址。
- 保留原URL域名、HTTPS证书链/主机名校验、SNI及Host；不全局修改socket或系统DNS，不继承HTTP代理，不跟随HTTP跳转。鉴权只发送到配置允许的模型域名。报告不保存请求头、密钥或响应正文。
- 连接建立上限10秒；模型响应继续使用原请求剩余时间，避免将正常耗时约25秒的embedding错误缩成10秒。DNS、TLS、响应和既有2秒退避均在原请求/题目时间预算内。保留每逻辑请求最多2次HTTP、每题600秒/16次模型HTTP/10次chat/3次SQL等原预算。
- 预检与模型请求调用相同 `process_dns.open_url`。预检只发送无密钥 `HEAD /`，404可作为连接成功记录。真实POST由后续独立embedding检查确认，不把HEAD视为模型调用成功。
- 索引身份加入解析模块摘要、连接策略及依赖锁；两侧各自建索引，不跨侧复制或强制命中。每个模型事件记录解析、TLS、地址及依赖身份。新连接层不触及隔离Agent的网络/进程权限。

本地验证共收集180项：177通过、3项真实Linux隔离检查在Windows跳过，失败/错误均为0。包含21项新连接层专项、原有传输/包准备、M3语义与工作流、BIRD运行上下文与预算回归。Windows沙箱曾阻止临时报告原子替换，经授权在沙箱外完成最终回归。本地没有真实DNS、模型或数据库请求。详见 [测试记录](results/m3_e03_process_dns_v1_r1_tests_local_20261023.json) 和 [交付清单](m3_e03_process_dns_v1_r1_delivery_20261023.json)。包CRC、全部生产文件语法、双方公共文件一致性及旧r3产物摘要亦已核对。

## 2. 上传并解压

上传到服务器 `~/Python_work/askdata_studio_ops_release/`：

```text
M3_E03_pair24_process_dns_v1_20261023_r1.zip
M3_E03_pair24_process_dns_v1_20261023_r1.zip.sha256
```

ZIP SHA-256：`414f2a4fccffd8df982f9fa9fac44785eefdec3c8cfc38d2983100340c7a36ea`。

包身份：`fe68e7c432be3bb0233ca532ce309cf5da805cca23c21ff3c8af66dd24a2e6d8`。

在服务器 `(py311)` 环境运行：

```bash
cd "$HOME/Python_work/askdata_studio_ops_release"

sha256sum -c M3_E03_pair24_process_dns_v1_20261023_r1.zip.sha256 && \
test ! -e "$HOME/Python_work/m3_e03_tools_process_dns_v1_20261023_r1" && \
unzip -n -q M3_E03_pair24_process_dns_v1_20261023_r1.zip \
  -d "$HOME/Python_work/m3_e03_tools_process_dns_v1_20261023_r1"
```

仅在校验及解压成功后继续。已存在目录时保留，不覆盖。

## 3. 准备新工作区并只做预检

```bash
bundle="$HOME/Python_work/m3_e03_tools_process_dns_v1_20261023_r1/m3_e03_pair24_process_dns_v1_20261023_r1"
work="$HOME/Python_work/m3_e03_pair24_process_dns_v1_20261023_r1"

python -u "$bundle/control/prepare_m3_e03_pair24.py" \
  --bundle-root "$bundle" \
  --source-backend "$HOME/Python_work/askdata_studio_ops_release/backend" \
  --workspace "$work" && \
python -u "$work/control/run_m3_e03_pair24.py" \
  --workspace "$work" --check-only
```

预期报告 `reports/e03_pair24_preflight_server.json`：

```text
run_status=complete
phase=preflight_with_process_dns_https
dns_readiness.passed=true
generation_reserved=false
new_model_request_count=0
```

预检不调用模型、不连接PostgreSQL。两侧分别验证依赖和DNS/HTTPS，成功后创建相同依赖锁。先发送预检输出或JSON核对。失败时发送完整报告及 `_checks/` 下失败的side JSON；不删除工作区、不修改冻结文件或放宽版本检查。没有生成登记的预检复查可用新 `--output` 路径。

## 4. 通过预检后，独立实际模型连接检查一次

此命令会调用embedding模型：10条固定短文本、一次逻辑批请求、最多2次HTTP、180秒总预算、0次chat/SQL，不使用题目或Gold，不建正式索引，不登记题目生成。使用基线的公共模型代码；两侧模型与连接模块字节相同。

```bash
work="$HOME/Python_work/m3_e03_pair24_process_dns_v1_20261023_r1"
python -u "$work/control/run_m3_e03_pair24.py" \
  --workspace "$work" --model-probe
```

预期 `run_status=complete`、`phase=transport_model_probe_complete`；子结果应有 `passed=true`、`vector_count=10`、`dimensions=[1024]`、模型尝试1或2次，完整budget/events记录。单独保存：

```text
reports/e03_transport_model_probe_server.json
reports/e03_transport_model_probe_server_checks/model_probe.json
transport_model_probe_attempt.json
transport_model_probe_receipt.json
```

生成前会核对成功检查回执及不可变子报告摘要。此检查只能登记一次；失败后保留证据，控制器拒绝以新报告名重复调用模型。真实请求失败/中断无法确认用量时保持unknown，不回填0。该检查只验证embedding，chat及rerank实际POST仍在配对运行中验证。

## 5. 前两步都核对通过后，前台正式运行一次

```bash
work="$HOME/Python_work/m3_e03_pair24_process_dns_v1_20261023_r1"

"$HOME/.local/askdata/pg16-env/bin/pg_isready" \
  -h 127.0.0.1 -p 55432 -d askdata_m2_bird && \
python -u "$work/control/run_m3_e03_pair24.py" --workspace "$work"
```

正式命令再次检查两侧身份与同一路径的DNS/HTTPS，核对依赖锁和成功模型连接回执后才创建 `attempt/reservation.json`。每侧独立建8域索引、各生成24题，两份完整捕获后才独立原生复评。不自动续跑生成、不自动扩为80题、不运行holdout。

如正式生成已登记，先保留报告核对故障，不通过改名再次生成。只有两份捕获都完整时，才可根据原规则使用一次 `--replay-only` 无模型恢复。

## 6. 下载与验收

成功后下载至本地 `E:\PythonLearn\m3_e03_pair24_process_dns_v1_20261023_r1\` 的对应目录：

```text
reports/e03_pair24_server.json
reports/e03_pair24_comparison_server.json
baseline/backend/evaluation/results/m3_e03_baseline24_capture_server.json
baseline/backend/evaluation/results/m3_e03_baseline24_native_server.json
candidate/backend/evaluation/results/m3_e03_candidate24_capture_server.json
candidate/backend/evaluation/results/m3_e03_candidate24_native_server.json
transport_dependency_lock.json
```

连同模型连接检查报告保留。独立连接检查的费用另报，不计入配对差异；两侧各自索引与题目中的全部模型事件均计入原筛选成本。

验收重点仍为0407公开双列、German条件、两列非空及有依据的关联；1479和20道回归题保持；调用、含索引Token和逐题p95有完整证据且满足预登记120%筛选线。通过HEAD或embedding不能替代E03语义与原生结果验收。
