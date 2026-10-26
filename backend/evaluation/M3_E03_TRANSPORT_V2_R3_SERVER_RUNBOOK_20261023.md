# E03 r3：修正 DNS 预检等待上限

> r3 仍出现系统解析错误和超时。显式备用DNS独立验证通过后，已准备 [公共连接层接入运行说明](M3_E03_PROCESS_DNS_PAIR24_SERVER_RUNBOOK_20261023.md)。以下 r3 命令作为历史记录保留。

日期：2026-10-23。状态：本地 19 项专项测试通过；服务器复验待完成。

## 原因与修正范围

服务器 r2 报告显示两次 `dns_lookup_timeout`，耗时均为 5.007 秒，`generation_reserved=false`、`new_model_request_count=0`、`attempt/` 不存在。此前有同域名约 20 秒后成功的解析记录，因此 5 秒上限会过早中断可恢复的慢查询。这份报告不能证明等待更久一定成功。

r3 将生成登记前的 DNS 查询上限从每次 5 秒调整为 30 秒，每个去重主机最多两次，中间等待 2 秒。单个主机最多约 62 秒，进程调度与清理可能略有开销。子进程超时后继续终止并回收。两侧模型源码、所有生产文件、模型调用重试、Token、SQL 次数和题内时间预算与 r2 字节相同；双方继续使用系统解析、原 HTTPS 和证书校验。

本次不修改系统 DNS。DNS 长期不可用时仍会停止。预检只证明该次域名解析通过，不能证明之后的模型请求或数据库就绪。

证据：[19 项专项测试](results/m3_e03_transport_v2_r3_tests_local_20261023.json)、[交付记录](m3_e03_transport_v2_r3_delivery_20261023.json)。测试模拟 20 秒解析成功及超时，不进行真实 DNS、模型或数据库请求。Windows 沙箱阻止临时报告原子替换的首次测试出现 3 项权限错误；经授权在沙箱外复跑后 19 项全部通过。

## 1. 上传两份新文件

本地项目根目录：

```text
M3_E03_pair24_transport_v2_20261023_r3.zip
M3_E03_pair24_transport_v2_20261023_r3.zip.sha256
```

上传至服务器 `~/Python_work/askdata_studio_ops_release/`。

ZIP SHA-256：`42054724dd59c2baa2b6b577652a5bb924514adf788bc5660b556752226aa0bc`。

包身份：`07e8263e43700091c3c71787d5344648a6b1e9febb145ea25b6ffb24a9c846db`。

保留 r2 工作区和全部报告。r3 使用独立目录，不修改冻结包。

## 2. 校验、解压、准备并只做预检

在服务器 `(py311)` 环境执行：

```bash
cd "$HOME/Python_work/askdata_studio_ops_release"

sha256sum -c M3_E03_pair24_transport_v2_20261023_r3.zip.sha256 && \
test ! -e "$HOME/Python_work/m3_e03_tools_transport_v2_20261023_r3" && \
unzip -n -q M3_E03_pair24_transport_v2_20261023_r3.zip \
  -d "$HOME/Python_work/m3_e03_tools_transport_v2_20261023_r3"
```

仅在校验及解压成功后执行：

```bash
bundle="$HOME/Python_work/m3_e03_tools_transport_v2_20261023_r3/m3_e03_pair24_transport_v2_20261023_r3"
work="$HOME/Python_work/m3_e03_pair24_transport_v2_20261023_r3"

python -u "$bundle/control/prepare_m3_e03_pair24.py" \
  --bundle-root "$bundle" \
  --source-backend "$HOME/Python_work/askdata_studio_ops_release/backend" \
  --workspace "$work" && \
python -u "$work/control/run_m3_e03_pair24.py" \
  --workspace "$work" --check-only
```

报告：`$work/reports/e03_pair24_preflight_server.json`。通过需 `run_status=complete`、`phase=preflight_with_dns`、`dns_readiness.passed=true`、`generation_reserved=false`、`new_model_request_count=0`。

发送终端汇总和下面的 DNS 记录：

```bash
python - "$work" <<'PY'
import json
import sys
from pathlib import Path
r = json.loads((Path(sys.argv[1]) / "reports/e03_pair24_preflight_server.json").read_bytes())
print(json.dumps(r.get("dns_readiness"), ensure_ascii=False, indent=2))
PY
```

预检失败时保留报告，不重复执行准备命令。此次上限已经包含此前的慢解析窗口；持续失败应依据具体 errno/超时证据处理连接环境，不继续逐次提高上限或反复启动正式模型实验。环境恢复后如需复查，使用同一工作区和新报告名 `--output "$work/reports/e03_pair24_preflight_retry1_server.json" --check-only`。

## 3. 通过核对后前台正式运行

```bash
work="$HOME/Python_work/m3_e03_pair24_transport_v2_20261023_r3"
"$HOME/.local/askdata/pg16-env/bin/pg_isready" \
  -h 127.0.0.1 -p 55432 -d askdata_m2_bird && \
python -u "$work/control/run_m3_e03_pair24.py" --workspace "$work"
```

正式命令也会先做 DNS 检查，通过后才登记生成。已登记生成的工作区不能通过更改输出文件名再次生成。成功后的六份报告名称、0407/1479/20题回归与成本验收规则沿用 [r2 运行说明](M3_E03_TRANSPORT_V2_SERVER_RUNBOOK_20261023.md)，下载时使用 r3 工作区作为根目录。
