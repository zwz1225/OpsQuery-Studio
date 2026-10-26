# M2 B 服务器来源材料验收记录

核对日期：2026-10-15。输入目录为 `evaluation/results/m2_b_source_server_20261015/`，三份原始 JSON 保留不变。本地独立核对记录见[机器报告](results/m2_b_source_server_review_local_20261015.json)。

**结论：服务器来源预检与导入清单阶段通过，可以进入独立目标初始化脚本的实施。** 此结论结合已通过的[v2 服务器环境预检](M2_B_SERVER_PREFLIGHT_V2_REVIEW.md)，尚不代表已创建目标库/角色、导入数据、验证目标一致性或执行 Gold。

## 三份文件核对

| 文件 | 核对结果 |
| --- | --- |
| [source_preflight.json](results/m2_b_source_server_20261015/source_preflight.json) | `run_status=complete`、`errors=[]`；75 表、798 字段、3,898,114 行、11 个逻辑域、24 个序列、500 道题 |
| [import_manifest.json](results/m2_b_source_server_20261015/import_manifest.json) | 与本地冻结规格及本地 v2 生成清单均逐字节相同；规范 JSON 摘要与批准值一致 |
| [preparation_review.json](results/m2_b_source_server_20261015/preparation_review.json) | `run_status=complete`；两个输入文件的实际字节 SHA-256 与记录一致；汇总、导入规格摘要均与来源报告一致 |

规范导入规格 SHA-256：

```text
46bb3555b5906478264c81b6ebc8ba2e86c6c3136bc3d8e3ecfc079770b0eede
```

这里的规范摘要不同于文件字节 SHA-256；二者均已分别核对。`import_manifest.json` 的实际文件 SHA-256 为 `c32dbeeb015359126e393aabbe470ed4052463e69a407d7b2ba158f4349b8879`，与冻结文件完全相同。

## 来源与目标边界

Hugging Face 修订、当前 PostgreSQL 题目摘要、dump 摘要和 M2 协议摘要全部与 M2 A 对齐。清单中的 77 个来源项为 1 份 PostgreSQL dump、1 份逻辑 schema、75 份字段说明，与冻结血缘清单逐项相同；题目文件另用其相对路径和固定摘要绑定。传输包包含 README 和元数据等共 80 个文件，因此该来源项数量差异符合设计。

目标固定为 `askdata_m2_bird.public`，导入角色 `askdata_m2_import`，11 个域分别绑定预期的 `askdata_m2_ro_<db_id>`。全部 75 张表在域之间没有重复归属，域清单与逐表 `database_id` 一致。87 个外键均在所属逻辑域内部，没有跨域外键。

报告中的 `postgresql_connected=false`、`database_imported=false`、`target_data_verified=false` 是离线来源检查的实际状态，不能解释为本次来源预检失败，也不能改写成目标数据已经验收。

## 逐表与控制语句核对

75 张表的 COPY 列顺序与 DDL 字段一致，各表 COPY 字节区间均在源文件范围内且互不重叠。逐表原始 COPY 摘要格式有效，NULL 统计长度与列数一致，NULL 数量均在该表行数范围内，NOT NULL 字段未出现源 NULL。原 DDL 与全部控制语句的 SHA-256 已重新计算，语句分类与预计导入动作一致。

| 逻辑域 | 表数 | 字段数 | 源行数 |
| --- | ---: | ---: | ---: |
| california_schools | 3 | 89 | 29,941 |
| card_games | 6 | 115 | 803,445 |
| codebase_community | 8 | 71 | 740,646 |
| debit_card_specializing | 5 | 21 | 423,050 |
| european_football_2 | 7 | 199 | 222,796 |
| financial | 8 | 55 | 1,079,680 |
| formula_1 | 13 | 94 | 493,257 |
| student_club | 8 | 48 | 42,511 |
| superhero | 10 | 31 | 10,614 |
| thrombosis_prediction | 3 | 64 | 15,252 |
| toxicology | 4 | 11 | 36,922 |
| 合计 | 75 | 798 | 3,898,114 |

字段类型：BIGINT 366、TEXT 329、DATE 19、TIMESTAMPTZ 11、REAL 73。REAL 是 PostgreSQL 单精度类型，后续一致性检查需按其真实存储语义处理；TIMESTAMPTZ 则需按固定 UTC 规则比较。当前的原始 COPY 字节摘要不等于导入后的类型化行摘要。

控制语句共 462 条：会话设置 11、search_path 1、建表 75、所有权声明 99、序列创建/归属/默认值/当前值各 24、约束 155、唯一索引 25。会话设置被标记为由受控配置替代；作者所有权被标记为映射至 M2 导入角色，未直接执行原始设置或作者账号授权。

## 后续实施

下一步实现并测试独立初始化脚本：重新核对当前集群、容量、目标库/角色冲突与批准规格，再创建独立 M2 目标和受限角色，保存独立初始化记录。预检证据是时间点快照，不能省略初始化前的实时检查。

初始化材料通过后，再实施受控 COPY/DDL、所有权映射、分域授权和失败恢复，完成 75 表的目标结构/类型/NULL/行数/类型化摘要及 ACL 核验。正式 Gold110 和 live 仍在这些步骤之后。
