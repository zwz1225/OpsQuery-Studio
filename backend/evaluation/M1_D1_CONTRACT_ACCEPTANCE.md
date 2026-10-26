# M1 D1：方言、Gold SQL 选择与评测身份接口

日期：2026-10-10。范围：D1 接口实施与本地验证。

## 1. 接口规则

| 内容 | DuckDB | PostgreSQL |
|---|---|---|
| backend | duckdb | postgresql |
| parser dialect / Gold 变体键 | duckdb | postgres |
| prompt dialect | DuckDB | PostgreSQL |
| 当前 source_id | short_video_ops_duckdb | short_video_ops_postgres |
| Gold 选择 | 原始 gold_sql | gold_sql_by_dialect.postgres |

`app/datasources/dialects.py` 提供统一映射与公开身份校验。身份必须包含既有八个字段；校验后端/方言对应关系、受控标识符及 SHA256 版本，拒绝额外凭据字段和缓存路径穿越。

`evaluation/gold_sql.py` 提供 `select_gold_sql` 与按题生成的 Gold 选择身份：

- DuckDB 继续执行原始 gold_sql；旧的无 SQL 静态题仍可使用 expected_rows。
- PostgreSQL 必须提供非空字符串 gold_sql_by_dialect.postgres。缺失、空串、错误类型或错误变体键均明确失败，即使存在原始 SQL、静态答案或缓存也不能替代。
- 选择器不自动转换 SQL，不证明 PostgreSQL 变体等价。正式变体的制作和审查属于后续步骤。
- 无 Gold/预期结果的路由、权限等行为题可以不提供变体。需要结果评分的题必须提供对应 Gold。

本步未修改任何正式题目。当前 430 题均保留原始 DuckDB SQL；PostgreSQL 变体尚待制作。

## 2. 执行与报告

Gold 解析器实际执行选中的 SQL，沿用相同权限与结果行数限制。Gold 结果、缓存和 Gold 模式的 generated_sql/trace 均记录实际 SQL。

新增公开字段：gold_sql、gold_dialect、gold_selection_key、gold_selection_version。Gold 缓存格式版本为 2，身份包含选择结果和完整来源身份；SQL、来源、catalog/data 版本或权限变化会使缓存失效。旧缓存按新格式重新生成。

`run_benchmark` 和 `run_e2e` 向 manifest 传入实际 runtime。现有模型流程和评分器继续沿用；运行 PostgreSQL 正式评测前，还需要后续方言校验链路及正式 Gold 变体。

## 3. manifest v3

- runtime 必须处于打开状态，实际身份与额外声明身份必须一致。
- PostgreSQL 不允许只传一份来源标签；必须传入 runtime，并核对实时验证标记及 data/catalog 版本。
- PostgreSQL 的 versions.data 来自已验证 runtime；versions.schema 为 runtime catalog 摘要，versions.physical_schema 为 C3 验证过的物理结构摘要。创建 manifest 不读取 CSV 来代表 PostgreSQL 数据。
- DuckDB 数据版本继续与本地 CSV 摘要核对；有来源身份时 schema 版本也采用 catalog 摘要。
- manifest 保存每题实际选择的 Gold SQL 和选择摘要；正式 PostgreSQL 评分题缺少变体时，在模型服务装配/逐题执行之前明确失败。
- regression comparison identity 加入 manifest 版本、物理结构版本和 Gold 选择摘要，保留既有来源、权限与评分代码身份。

v2 与 v3 报告身份不可直接作为同条件回归。原始 M0/M1 报告保留；后续通过 v3 建立新的同源基线。跨后端等价性仍需单独的比较入口，不能通过允许不兼容比较冒充同源回归。

## 4. 验证与边界

- 新增 17 项 D1 测试全部通过。
- 全套 404 项测试通过，耗时 54.246 秒。
- 新测试使用 PostgreSQL 替身验证接口，未连接远程 PostgreSQL、未请求模型。
- DuckDB 兼容性与实际 manifest/代表题核对记录见 [本地实施记录](results/m1_d1_implementation_local.json)。

D1 不是 PostgreSQL 全量 Gold、live 或 E2E 验收。本步未更新提示词、四类 SQL 规划/校验器、正式 PostgreSQL Gold 变体、索引实现或跨后端等价比较工具；这些仍按 M1 D 后续顺序实施。评分比较器、逐题别名和并列规则保持原逻辑。

## 5. 服务器同步与接口复核

将 `M1_D1_方言与Gold接口同步包_20261010.zip` 上传到项目根目录后：

```bash
cd ~/Python_work/askdata_studio_ops_release
unzip -o M1_D1_方言与Gold接口同步包_20261010.zip
cd backend
python -m unittest discover -s tests -p 'test_m1_d1_contracts.py' -v
```

预期 17 项通过。这条命令不使用模型，也不连接 PostgreSQL。可继续执行完整回归：

```bash
python -m unittest discover -s tests -q
```

预期 404 项通过。本步无需新增 .env 参数；保持已验收的 DuckDB 默认配置和现有 PG 参数。正式题集尚未添加 PostgreSQL 变体，此时切换到 PostgreSQL 跑正式评测会按新规则拒绝缺失变体。

下一步为 D2：将 runtime 方言和 catalog 传递到 Skill/Agent、SQLValidator、MetricPlanner、ConstraintPlanner、ConstraintValidator 及执行说明。
