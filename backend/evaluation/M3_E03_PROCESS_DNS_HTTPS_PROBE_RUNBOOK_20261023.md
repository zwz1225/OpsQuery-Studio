# E03：独立进程 DNS 与 HTTPS 验证

日期：2026-10-23。阶段：连接方案的独立验证；尚未接入正式基线和候选。

## 背景与边界

r3 正式运行前，`dashscope.aliyuncs.com` 两次系统解析分别在约 20 秒返回 errno=-3、约 30 秒超时。`generation_reserved=false`，模型请求为 0，`attempt/` 不存在。延长预检等待未消除间歇故障。

本工具直接向显式指定的备用 DNS 查询 IPv4 A 记录，随后验证实际地址的 HTTPS。默认候选 `114.114.114.114` 是服务器原配置中已有且曾直接查询成功的解析服务；本次命令只作用于该工具，无法修改其他进程的解析方式。持续可用性等待服务器结果确认。

- 使用已有 `dig -r`，忽略个人 `.digrc`；显式指定解析服务。使用 UDP，每轮每域名一次、3 秒、一次尝试，外层子进程最多 5 秒；截断应答明确失败，避免隐含 TCP 重试。
- 从当前 `.env` 和进程环境的三个端点设置读取去重域名；不加载或使用模型密钥。仅支持 HTTPS 443。默认三个端点同为 DashScope。
- 验证应答状态、CNAME 归属链、TTL 和公网 IPv4。每轮重新解析，不保存可复用地址文件。TTL=0、已过期地址和无关记录不会成为连接目标。
- 三轮验证，每轮最多两个候选地址。每个 socket 超时 10 秒，轮间等 2 秒，查询和 HTTPS 阶段总墙钟上限 120 秒。依靠 Linux 定时器终止缓慢响应。
- 直接建立数字地址 TCP 连接，使用原域名做 SNI、证书主机名校验和 HTTP Host。保留系统默认信任库及证书校验；不继承 HTTP 代理、不修改全局 socket、系统 DNS 或固定服务 IP。
- 每次只发送无 Authorization、无请求正文的 `HEAD /`；不读响应正文，不跟随跳转。收到有效 HTTP 响应（包括 3xx、401、404、405、5xx）仅代表本次 TCP/TLS/HTTP 连接成功，不代表模型鉴权、API 路径或模型服务健康。TLS 校验失败时不尝试本轮其他 IP。
- 本工具既不连接 PostgreSQL，也不调用模型、不登记生成尝试，不是 E03 配对实验。新方案尚未改变 r3 正式运行代码。

实现参考：[BIND dig 文档](https://bind9.readthedocs.io/en/latest/manpages.html#dig-dns-lookup-utility)、[Python HTTPSConnection](https://docs.python.org/3/library/http.client.html#http.client.HTTPSConnection)、[TLS 与 server_hostname](https://docs.python.org/3/library/ssl.html#ssl.SSLContext.wrap_socket)。

## 1. 上传两个文件

从本地项目根目录上传至服务器 `~/Python_work/askdata_studio_ops_release/`：

```text
probe_m3_e03_process_dns.py
probe_m3_e03_process_dns.py.sha256
```

只有这两个文件需要上传。无需重新解压 E03 包，无需重新创建工作区。

## 2. 校验并前台运行一次

在服务器 `(py311)` 环境执行：

```bash
cd "$HOME/Python_work/askdata_studio_ops_release"

sha256sum -c probe_m3_e03_process_dns.py.sha256 && \
python -E -s -u "$HOME/Python_work/askdata_studio_ops_release/probe_m3_e03_process_dns.py" \
  --model-config-file "$HOME/Python_work/askdata_studio_ops_release/backend/.env" \
  --resolver 114.114.114.114 \
  --output "$HOME/Python_work/m3_e03_pair24_transport_v2_20261023_r3/reports/e03_process_dns_https_probe_server.json"
```

保留已有报告，输出路径存在时会拒绝执行。命令可能需要约两分钟。无需 sudo，不安装依赖。

## 3. 下载报告并核对

服务器报告：

```text
~/Python_work/m3_e03_pair24_transport_v2_20261023_r3/reports/e03_process_dns_https_probe_server.json
```

下载到本地：

```text
E:\PythonLearn\m3_e03_pair24_transport_v2_20261023_r3\reports\e03_process_dns_https_probe_server.json
```

报告包含每轮 DNS 状态、CNAME、地址/有效期、TCP/TLS/HEAD 结果和实际尝试数。异常只保存类别和数字错误码，不保存原始异常、HTTP 响应头/正文或凭据。

通过条件：`run_status=complete`、`all_rounds_passed=true`，每个端点域名连续三轮至少一个地址的 TLS 和 HEAD 成功。此时仍应有 `new_model_request_count=0`、`generation_reserved=false`、`production_transport_changed=false`、`model_api_verified=false`。

若失败，依据 `checks` 中 DNS / 证书 / TCP / HTTP 的具体分类决定下一步，不自动循环测试或增加预算。若通过，再将相同解析与 TLS 连接方案装配到两侧公共连接层，并将解析服务、TTL、尝试上限、dig 依赖和代码纳入新身份。当前 r3 命令仍使用系统 DNS，不能因本探针通过而直接宣称 r3 已获得备用解析能力。

## 本地检查

19 项离线测试覆盖 CNAME、TTL、无关记录、私网/截断/错误应答、端点验证、数字地址连接、原域名 SNI/Host、证书失败关闭、无鉴权 HEAD、无跳转跟随、三轮上限、错误脱敏及独立报告。Windows 沙箱阻止临时报告原子替换；经授权在沙箱外复跑全部通过。未进行真实服务器、DNS、模型或 PostgreSQL 请求。
