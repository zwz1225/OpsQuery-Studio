# M1 B：PostgreSQL 环境与源数据准备

更新日期：2026-10-08。M1 A 已归档，见 [最终验收](M1_A_FINAL_ACCEPTANCE.md)。

## 1. 当前状态

- 根据用户提供的服务器输出，PostgreSQL 16.15 已安装在用户目录，监听 `127.0.0.1:55432`；测试库 `askdata_m1_test` 为 UTF8、libc/C 排序，`askdata_ops` 已创建。
- `askdata_import` 与 `askdata_readonly` 密码登录均成功，均无超级用户、创建数据库、创建角色权限。
- 导入账号 search_path 为 `askdata_ops, pg_catalog`，默认事务可写；查询账号为 `pg_catalog, askdata_ops`，默认事务只读。
- 查询账号可连接测试库、使用业务 schema；不可创建 schema、临时表或业务表。导入后 41 表 SELECT/写权限与四项实际写入拒绝均已验证通过，探测事务回滚且连接恢复。
- 本地与服务器完整源数据预检、导入规格审查均通过；服务器三个准备 JSON 及两个导入/独立验证报告已下载并逐项核对。M1 B 已验收，见 [最终验收](M1_B_FINAL_ACCEPTANCE.md)；项目运行后端仍为 DuckDB。

环境证据来自用户粘贴的命令输出。本地脚本没有连接 PostgreSQL、读取 `.env` 或请求模型，记录不包含密码。

### 服务器源材料归档核对

服务器材料：[源预检](results/m1_b_source_server_20261008/source_preflight.json)、[导入清单](results/m1_b_source_server_20261008/import_manifest.json)、[规格审查](results/m1_b_source_server_20261008/preparation_review.json)。独立核对记录：[m1_b_server_source_archive_review.json](results/m1_b_server_source_archive_review.json)，生成脚本：[audit_m1_b_server_archive.py](../scripts/audit_m1_b_server_archive.py)。

- 43 个源文件（41 个 CSV、Schema、数据库数据清单）SHA256 与当前本地逐一相同，data_version 保持 M1 A 已验收值，catalog_version 相同。
- 41 表/276 字段/722,732 行逐表一致；字段物理类型、NULL、distinct、MIN/MAX、SUM/AVG、时间精度、主键检查和全量类型化行多重集合摘要全部精确一致。
- 53 条业务关系和 NULL/COPY 约定、目标库/schema/账号、建表与 COPY 语句、目标未验证标记全部一致。
- 导入规格的规范 JSON 指纹相同：`8f936c3089614a38b17194b76e0c073c20cfe5b194ecb8f9f1e27b8f4d2ca7fd`。
- 下载的源预检和清单文件 SHA256 均与服务器规格审查记录吻合；清单文件与本地的字节差异仅是 CRLF/LF，完整源预检内容只相差运行时间。
- 服务器 SQL 文件没有下载。其审查记录中的 SHA256 与本地建表规格转换为 Linux 换行后的 SHA256 相同；没有宣称直接读取过服务器 SQL 文件，也没有执行 PostgreSQL DDL。
- 三个下载报告及本地原材料保持原样；独立核对没有重跑 SQL、请求模型或修改源文件。源材料准备已通过，目标库的数据与实际表权限仍待导入验证。

## 2. 本地源数据实际检查结果

证据：[源数据预检](results/m1_b_source_local_v2/source_preflight.json)、[导入清单](results/m1_b_source_local_v2/import_manifest.json)、[建表规格](results/m1_b_source_local_v2/create_tables.sql)、[独立审查](results/m1_b_source_local_v2/preparation_review.json)。

| 检查 | 实际结果 |
|---|---|
| CSV 表 / 字段 / 业务关系 | 41 / 276 / 53 |
| 总行数 | 722,732；CSV、DuckDB、Schema、数据清单逐表一致 |
| CSV 字节数 | 51,894,889，约 49.5 MiB |
| 字段名、顺序与物理类型 | 全部一致 |
| 主键 | 41 表均无重复主键组、无 NULL 主键行 |
| 业务关系 | 53 条端点有效，非空子字段均有匹配父记录 |
| 原始 CSV 与 DuckDB 的全量类型化行内容 | 41 表的行多重集合摘要逐表一致，重复行不会被去除 |
| UTF-8 BOM | 41 个 CSV 均包含；仅读取时识别，未改写文件 |
| 源文件变化 | CSV、Schema、数据清单全部摘要保持不变 |
| 错误 / 告警 / 新模型请求 | 0 / 0 / 0 |

源数据版本保持为 M1 A 已验收版本：

```text
d23481ffef242c04bc2adcf1f5a7082ec65ce392d30a48b16e7ccb0b3a3809b8
```

五个含 NULL 的字段已全量核实：

| 表 | 字段 | NULL 数量 |
|---|---|---:|
| channel_attributions | ad_campaign_id | 177 |
| channel_conversion_events | ad_campaign_id | 306 |
| recall_results | returned_at | 8,255 |
| user_activations | activated_at | 3,022 |
| user_activations | activation_seconds | 3,022 |

## 3. 类型映射与导入约定

| source_type | 字段数 | PostgreSQL 类型 |
|---|---:|---|
| VARCHAR | 168 | text |
| BIGINT | 54 | bigint |
| DATE | 16 | date |
| TIMESTAMP | 21 | timestamp without time zone |
| DOUBLE | 17 | double precision |

- 字符串保持原内容；BIGINT 验证十进制整数和有符号 64 位范围，不通过 float 转换整数。
- 日期与时间分别处理。时间只接受无时区、最多六位小数的 ISO 值；带时区或超出精度会失败，不静默裁剪。
- 所有字段记录 NULL、非空 distinct、MIN/MAX；数值字段另外记录 SUM/AVG；时间字段记录精度，供目标库验证。
- NULL 规则来自当前 DuckDB 实测：未加引号空字段和 `""` 均读为 NULL，字面文本 `NULL` 保持文本。计划使用 `COPY FROM STDIN`、显式列顺序、CSV/UTF8、`NULL ''` 和逐列 `FORCE_NULL` 保持相同行为，不改评分别名或容差。
- `HEADER TRUE` 丢弃原始表头，字段名与顺序已在预检中严格检查；不从原文件删除 BOM。
- 只生成已验证的业务主键约束，其他字段保持可空；不依据本次 NULL 为零擅自增加 NOT NULL。53 条关系保留业务含义，本次不自动生成数据库 FK。
- 表由 `askdata_import` 创建，以使已配置的默认 SELECT 授权作用于新表。不要使用管理员账号替代导入账号执行建表。
- 规格只允许新表，不生成 DROP、TRUNCATE、覆盖或跳过错误的操作。`create_tables.sql` 只建表，没有导入数据；目前不要单独执行，后续导入脚本将统一处理事务。

`COPY FROM STDIN` 由客户端传输 CSV，无须为导入账号授予服务器文件读取权限；`FORCE_NULL` 对带引号的空值生效。[PostgreSQL 16 COPY 文档](https://www.postgresql.org/docs/16/sql-copy.html)

## 4. 脚本与验证边界

- [preflight_m1_b_source.py](../scripts/preflight_m1_b_source.py)：仅读源文件，在内存 DuckDB 中扫描，生成三个独立文件，不导入应用运行上下文。已有非空输出目录、源目录内输出或错误源版本均拒绝执行；扫描失败只留下失败报告，不生成可导入规格。
- [audit_m1_b_source_preparation.py](../scripts/audit_m1_b_source_preparation.py)：复核源文件、清单指纹、41 条 PostgreSQL CREATE TABLE 语法及受控 schema；用小样本确认 BOM、引号内逗号/换行、字面 NULL/空值、BIGINT 上界及微秒精度保持一致。
- 行摘要算法：类型标记和归一化值组成紧凑 UTF8 JSON，每行 SHA256，排序二进制摘要后再 SHA256；保留重复次数。DOUBLE 用 `float.hex()`，TIMESTAMP 固定为无时区微秒 ISO；精确规则写入清单，供目标验证复用。
- 目标数值聚合检查拟使用相对 `1e-9`、绝对 `1e-6` 容差处理浮点累加差异，全量类型化行摘要仍须一致。这只用于导入验证，不修改题集评分规则。
- SQLGlot 检查不是 PostgreSQL 实际执行。清单标记 `target_data_verified=false`、`verified_target_data_version=null`；源 CSV 摘要不能充当已验证的目标数据版本。
- 首次开发预检因 BOM 表头读取失败的记录留存于 `results/m1_b_source_local/source_preflight.json`。通过记录保存于独立的 `m1_b_source_local_v2`，未覆盖诊断记录或 M0/M1 A 报告。

## 5. 服务器下一步命令

同步两个脚本到服务器相同位置：

```text
backend/scripts/preflight_m1_b_source.py
backend/scripts/audit_m1_b_source_preparation.py
```

使用原项目 `py311` 环境，在 backend 执行：

```bash
cd ~/Python_work/askdata_studio_ops_release/backend

python -u -m scripts.preflight_m1_b_source \
  --output-dir evaluation/results/m1_b_source_server_20261008

python -u -m scripts.audit_m1_b_source_preparation \
  --input-dir evaluation/results/m1_b_source_server_20261008
```

只在第一条预检 `status=passed`、`error_count=0`、`warning_count=0` 后执行第二条。两条均不需要 PostgreSQL 密码或模型密钥，不修改 CSV，不创建或导入 PostgreSQL 表。

若输出目录已存在且非空，保留它，换新目录名，并同步修改两条命令。若报源数据版本不一致，先比较源文件摘要，不修改 expected-data-version 绕过基线。

输出文件：

```text
evaluation/results/m1_b_source_server_20261008/
  source_preflight.json
  import_manifest.json
  create_tables.sql
  preparation_review.json
```

本地和服务器的时间、换行及输出文件 SHA256 可以不同。比较源文件 SHA256、data_version、统计与类型化行摘要，以及 `source_preflight.json` 的 `import_spec_sha256`（规范 JSON 摘要），不只比较平台相关的输出文件字节。

## 6. 随后的工作

1. 已完成：服务器三个 JSON 下载、源文件与逐表完整统计/内容/规格的独立归档核对，结果全部一致。
2. 已实现独立 PostgreSQL 导入及验证脚本，使用导入账号在统一事务中创建新表、传输 CSV；完整目标核对通过后提交，失败时回滚并保留独立失败证据。25 项针对性测试与两个入口的离线预检查通过。
3. 已完成服务器实际导入和只读独立验证：41 表/276 字段/722,732 行、主键、NULL、时间值、聚合及全量类型化行摘要与源清单一致，读取授权和实际写入拒绝通过。下载报告的关联 SHA256 与重新计算的目标版本一致。命令及恢复步骤见 [M1 B 导入验收说明](M1_B_IMPORT_ACCEPTANCE.md)。
4. 实际目标版本和独立报告已形成并归档；下一步进入 M1 C 的执行器、catalog/profile 及后续方言适配，详见 [最终验收与阶段边界](M1_B_FINAL_ACCEPTANCE.md)。

目前没有使用 PostgreSQL 运行原 DuckDB Gold、切换应用后端或改写原题集、评分规则、CSV、`.env` 和历史报告。
