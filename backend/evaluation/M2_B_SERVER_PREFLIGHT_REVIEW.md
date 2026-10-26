# M2 B 首轮服务器预检核对与地址格式修正

核对日期：2026-10-15。原始报告：[m2_b_server_preflight_server.json](results/m2_b_server_preflight_server.json)。原始状态 `blocked`、`ready_for_initialization=false` 保留，不改写为通过。独立核对与候选规则重放见[本地复核记录](results/m2_b_server_preflight_review_local_20261015.json)。

## 逐项结果

| 检查 | 原始结果 / 原始值 | 判断 |
| --- | --- | --- |
| 登录与维护库 | `askdata_admin` / `postgres`，通过 | 与预期一致 |
| PostgreSQL 版本 | `160015`，通过 | PostgreSQL 16.15 |
| 编码与 locale | UTF8、C、C、c，通过 | 与冻结源准备约定一致 |
| 本机地址与端口 | `127.0.0.1/32` / 55432，失败 | 地址字符串表示差异造成脚本误判 |
| 实际数据目录 | `/home/zhangwenzong_25/.local/share/askdata/pg16-data`，通过 | 与预期集群一致 |
| 初始化权限 | superuser/createdb/createrole 均为 true，通过 | 可进行后续受控初始化 |
| 独立目标不存在 | `target_exists=false`，通过 | 尚未创建 `askdata_m2_bird` |
| M2 角色不存在 | `existing_m2_roles=[]`，通过 | 没有本轮预期角色冲突 |
| 容量预算 | 98,755,670,016 字节，约 91.97 GiB，通过 | 当时 PG 和来源存储均超过 10 GiB 准备门槛 |

Python 为 3.11.15，Linux x86_64；Psycopg 3.2.13、psycopg-pool 3.2.8 与固定依赖一致。Timezone 为 UTC，`errors=[]`，新增模型请求数为 0。没有创建数据库或导入数据。

## 修正内容及验证

旧判断直接比较 `server_address == '127.0.0.1'`。报告查询返回的是 `inet_server_addr()::text`，本次真实结果带 `/32`。修正使用标准库 `ipaddress.ip_interface` 解析，只接受 IPv4 地址 `127.0.0.1`、主机掩码 `/32`、端口 55432；同时支持不带掩码的同一主机表示。

回归覆盖 `/24`、其他 IPv4、IPv6、映射 IPv6、空值、非法字符串以及错误端口，均继续拒绝。保留其他身份、权限、容量和来源限制。新报告带 `preflight_check_version=2`。

当前 M2 专项测试合计 26 项通过。用原报告的原始字段离线重放后，候选规则 9/9 通过；这只证明已保存数据在新规则下的判断，不表示已重新连接服务器或重新检查容量。必须保存一次独立服务器重跑报告。

## 同步和重跑

把项目根目录中的 `M2_B_endpoint_fix_20261015.zip` 上传到远程项目根目录，再执行：

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M2_B_endpoint_fix_20261015.zip
cd backend

python -m unittest discover -s tests -p 'test_m2_*.py' -v

python -u -m scripts.preflight_m2_b_server \
  --prompt-password \
  --output evaluation/results/m2_b_server_preflight_server_v2.json
```

输入 `askdata_admin` 的密码。核对新报告有 `preflight_check_version=2`、`run_status=complete`、`ready_for_initialization=true`，9 项检查全部通过后，继续上传已准备的来源数据包并执行来源预检。旧代码包若需重传，应先应用旧包、再应用本补丁，避免覆盖修正。
