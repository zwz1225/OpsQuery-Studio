# M2 B v2 服务器预检验收记录

核对日期：2026-10-15。输入为用户下载的 [m2_b_server_preflight_server_v2.json](results/m2_b_server_preflight_server_v2.json)，本地独立复核见 [JSON 记录](results/m2_b_server_preflight_v2_review_local_20261015.json)。

**结论：M2 B 的服务器初始化前预检通过，允许继续上传来源包和生成离线导入清单。** 本记录不表示数据库已经初始化、数据已经导入或目标一致性已验证。

## 状态与原始字段

报告使用 `preflight_check_version=2`，`run_status=complete`、`postgresql_connected=true`、`ready_for_initialization=true`，9 项检查全部通过，`errors=[]`。本地依据原始字段重新计算 9 项判断，与报告逐项一致。

| 项目 | 证据 | 结果 |
| --- | --- | --- |
| 维护连接身份 | `askdata_admin` / `postgres` | 通过 |
| 版本与依赖 | PostgreSQL 16.15；Psycopg 3.2.13；psycopg-pool 3.2.8 | 通过 |
| 编码、locale 与时区 | UTF8；C/C/c；UTC | 通过 |
| 本机连接 | `127.0.0.1/32:55432` | 通过；同一 IPv4 主机的 `/32` 表示被正确识别 |
| 实际集群目录 | `/home/zhangwenzong_25/.local/share/askdata/pg16-data` | 通过 |
| 初始化权限 | superuser、CREATEDB、CREATEROLE 均为 true | 通过 |
| 目标库冲突 | `askdata_m2_bird` 不存在 | 通过 |
| 角色冲突 | 导入及 11 个查询角色均不存在 | 通过 |
| 额外可用空间 | 98,755,608,576 字节，约 91.97 GiB，PG 与来源存储均满足 10 GiB 门槛 | 通过 |

主机为 Linux x86_64、Python 3.11.15。目标配置与固定 M2 B 规格一致：`askdata_m2_bird.public`、`askdata_m2_import` 和按逻辑域隔离的 11 个 `askdata_m2_ro_<db_id>`。与首轮报告相比，`database_state` 所有原始字段相同；本轮是实际服务器独立重跑，不是把旧报告状态改成通过。

报告原始文件 SHA-256 为：

```text
b3e71673dee329a06f3e1f02b4d80385a98798eb0b2fe0a63ded2ef13de59a88
```

服务器检查发生在 `2026-10-15T14:43:52.752552+00:00` 至 `2026-10-15T14:43:56.280565+00:00`。本地复核只检查该次服务器证据，未从本地再次连接远程或实时测量磁盘。初始化前和上传来源后仍需重新核对实时状态。

## 下一步：上传来源并预检

将本地项目根目录的 `M2_B_source_data_20261015.zip` 上传到远程项目根目录。该包大小 226,816,643 字节，SHA-256 为 `4a07f17fa0b999d81c48b569dd78120595382cb3f9a45eba15a8f5fd016b0bce`，只包含所需 80 个来源文件。它不会覆盖本次已修复的代码。

```bash
cd ~/Python_work/askdata_studio_ops_release
ls -lh M2_B_source_data_20261015.zip
unzip -o M2_B_source_data_20261015.zip
cd backend

python -u -m scripts.preflight_m2_b_source \
  --output-dir evaluation/results/m2_b_source_server_20261015
```

成功后核对三份材料：

```text
evaluation/results/m2_b_source_server_20261015/source_preflight.json
evaluation/results/m2_b_source_server_20261015/import_manifest.json
evaluation/results/m2_b_source_server_20261015/preparation_review.json
```

应有 75 表、798 字段、3,898,114 行、24 序列；规范导入规格摘要应为 `46bb3555b5906478264c81b6ebc8ba2e86c6c3136bc3d8e3ecfc079770b0eede`。输出目录存在时使用新名称，保留旧证据。来源清单核对后，再继续独立数据库初始化、受控导入和目标一致性验证。

本阶段报告中的 `database_created=false`、`data_imported=false`、新增模型请求数 0 均符合当前实际阶段，不能据此声称 M2 B 全阶段或外部基线已完成。
