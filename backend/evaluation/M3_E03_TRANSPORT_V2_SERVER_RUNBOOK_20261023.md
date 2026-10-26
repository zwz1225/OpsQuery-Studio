# E03 公共连接层 v2：有界 DNS 恢复与失败用量记录

> r2 服务器预检出现两次 5 秒查询超时，尚未调用模型。新部署请使用 [r3 运行说明](M3_E03_TRANSPORT_V2_R3_SERVER_RUNBOOK_20261023.md)，其中仅将生成登记前的 DNS 查询等待上限改为 30 秒。以下 r2 命令和身份保留为历史记录。

日期：2026-10-23。交付修订：r2。状态：本地实现与离线检查完成；服务器运行待验证。本包是新实验身份，不能覆盖或续跑旧工作区。

## 改动范围与实验解释

原 E02 验收记录继续有效。本包从原 E03 包的两份生产快照派生，在基线和候选上应用相同的三项公共改动：`model.py` 的传输处理、`retrieval.py` 的失败索引用量、`diagnostic_runner.py` 的诊断汇总。基线仍为 E02 语义策略，候选仍为 E03 关系与输出策略；两侧公共连接层已修订，因此基线应标作“E02语义策略＋公共连接层v2”，不称为原 E02 的字节相同重放。

- 每个模型逻辑请求仍最多2次 HTTP 尝试。只有首次 `EAI_AGAIN` 临时解析失败时，等待2秒后使用原重试机会；等待计入原墙钟预算。永久解析错误及证书校验错误立即停止。401/400等不重试。未增加 SQL 生成、SQL执行、题目总时间、模型HTTP和索引批量上限。
- 使用原系统解析器、原域名、原 HTTPS 与证书校验。无新增库、全局 socket 修改、IP硬编码、系统DNS或VPN设置改动。
- HTTP事件分别保存安全的异常类型、原因类型、errno、主机名、退避时长及单次耗时。异常消息、请求头、密钥、响应正文不进入诊断。
- 建索引失败时保留已发生的全部模型尝试和 usage；没有 usage 的事件保留 null。报告中 `new_model_request_count` 现在统计题内和建索引的总HTTP尝试；两个部分继续单列。旧报告不会被回填或改写。
- 登记生成尝试前检查三个模型端点的去重主机名。每个主机最多2次DNS查询，每次由子进程监督5秒硬超时，两次之间等待2秒；不发HTTP、不读模型答案。检查失败不会创建 `attempt/`，可以在环境恢复后用新报告名复查同一新工作区。

恢复机制只能处理短暂故障。系统解析持续不可用时会明确停止，不能保证这台服务器一定完成实验。DNS检查成功也不保证后续网络始终正常。

客户端策略中的 `extra_dns_probes=false` 指单个模型请求不增加额外预解析；独立的启动前DNS就绪检查另有版本化策略。事件的 `attempt_wall_seconds` 包含该次失败后的退避，`retry_delay_seconds` 单列退避时间。

本地验证：[相关回归证据](results/m3_e03_transport_v2_tests_final_local_20261023.json)收集186项，183通过、3项真实Linux隔离检查在Windows跳过；最终r2的[18项专项测试](results/m3_e03_transport_v2_r2_tests_local_20261023.json)全部通过，覆盖冻结E02接口、包准备、预算边界、恢复和脱敏。均无真实模型、DNS或数据库请求。文件与身份详见[交付清单](m3_e03_transport_v2_r2_delivery_20261023.json)。

验收控制脚本还修复了对冻结 E02 基线 `policy()` 无参数接口的调用，防止生成完成后才发生参数不兼容错误；E03 候选继续使用自己的关系/输出策略。该修复不改变模型输入。

## 文件与身份

上传到服务器 **`~/Python_work/askdata_studio_ops_release/`**：

```text
M3_E03_pair24_transport_v2_20261023_r2.zip
M3_E03_pair24_transport_v2_20261023_r2.zip.sha256
```

ZIP SHA-256：`23fbc459e132f59147a1cd389e059ef40855ef65e217fded97a76666632bc668`。

新包 ID：`168e7bb782dd3b57b5e6f1cca01dd6290596bb81c7a362c18f67b2b10ae02224`。基线98文件、候选99文件。24题顺序、来源/权限/数据版本、模型参数、Gold、原生评分和筛查线保留原E03约定。原E03包及失败工作区继续保存。

## 1. 校验并解压

在服务器原 `(py311)` 环境执行：

```bash
cd "$HOME/Python_work/askdata_studio_ops_release"

sha256sum -c M3_E03_pair24_transport_v2_20261023_r2.zip.sha256 && \
test ! -e "$HOME/Python_work/m3_e03_tools_transport_v2_20261023_r2" && \
unzip -n -q M3_E03_pair24_transport_v2_20261023_r2.zip \
  -d "$HOME/Python_work/m3_e03_tools_transport_v2_20261023_r2"
```

只有显示 `OK`、解压成功才继续。已存在目录时保留，不覆盖。

## 2. 创建新工作区

```bash
bundle="$HOME/Python_work/m3_e03_tools_transport_v2_20261023_r2/m3_e03_pair24_transport_v2_20261023_r2"
work="$HOME/Python_work/m3_e03_pair24_transport_v2_20261023_r2"

python -u "$bundle/control/prepare_m3_e03_pair24.py" \
  --bundle-root "$bundle" \
  --source-backend "$HOME/Python_work/askdata_studio_ops_release/backend" \
  --workspace "$work"
```

预期 `run_status=complete; model_calls=0; database_connected=false`。沿用服务器原数据、凭据和 `.env` 路径；不复制私密文件，不需要把本地修改逐个覆盖到服务器原backend。

## 3. 带DNS就绪检查的预检

```bash
python -u "$work/control/run_m3_e03_pair24.py" \
  --workspace "$work" --check-only
```

报告为 `reports/e03_pair24_preflight_server.json`。通过要求：

```text
run_status=complete
phase=preflight_with_dns
preflight_passed=true
dns_readiness.passed=true
generation_reserved=false
new_model_request_count=0
```

该预检仍不调用模型、不连接PostgreSQL，也不证明实时权限或数据版本；正式生成阶段继续做原有实时核验。先将预检JSON下载到本地对应新目录核对，再启动正式运行。

如果预检失败，发送完整JSON即可。只要 `attempt/` 未创建，就没有启动生成；无需删除工作区。环境恢复后可用 `--output "$work/reports/e03_pair24_preflight_retry1_server.json" --check-only` 保留独立复查记录。不要自动无限循环查询。

## 4. 前台正式运行一次

```bash
work="$HOME/Python_work/m3_e03_pair24_transport_v2_20261023_r2"

"$HOME/.local/askdata/pg16-env/bin/pg_isready" \
  -h 127.0.0.1 -p 55432 -d askdata_m2_bird && \
python -u "$work/control/run_m3_e03_pair24.py" --workspace "$work"
```

正式命令会重复预检及DNS就绪检查，通过后才登记一次生成尝试。两侧分别建索引，先完成两份捕获，再做独立原生复评。若检查阶段失败且 `generation_reserved=false`，保存报告后可以选择新输出名重新检查；若已登记生成，则停止，不通过改文件名重跑模型。

## 5. 下载与核对

成功后下载以下六份JSON，保存到本地独立目录 `PythonLearn/m3_e03_pair24_transport_v2_20261023_r2/`：

```text
reports/e03_pair24_server.json
reports/e03_pair24_comparison_server.json
baseline/backend/evaluation/results/m3_e03_baseline24_capture_server.json
baseline/backend/evaluation/results/m3_e03_baseline24_native_server.json
candidate/backend/evaluation/results/m3_e03_candidate24_capture_server.json
candidate/backend/evaluation/results/m3_e03_candidate24_native_server.json
```

如果生成失败，先下载总控JSON及已生成的capture JSON；总控的 `generation_failure_evidence` 包含捕获摘要、失败的 `preparation_attempts` 和模型事件，不需要再用一串探针猜测失败原因。超时/强制结束导致用量无法确认时保持unknown，不填0。

验收仍检查0407双列、德语、非空和有依据的关联，1479及20题回归，完整原生比较、权限/隔离/预算和包含索引的成本。连接层修订是双方公共条件；不能用这一轮与旧E03失败运行计算准确率差异，也不因网络故障调整评分或提高预算。
