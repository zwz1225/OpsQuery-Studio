# M1 D3：79题 PostgreSQL Gold SQL 逐题审查

日期：2026-10-10。状态：79题显式变体与离线审查完成；后续服务器79题Gold执行及报告一致性核对也已通过。详见 [服务器核对记录](M1_D3_POSTGRES_GOLD79_SERVER_REVIEW.md)。下文保留制作时的离线逐题状态，未覆盖原始审查JSON；本次服务器报告不含完整结果行，未进行本地单元格级独立复评分。

## 审查范围与依据

范围固定为 classic 49题和 phase83 扩展30题，顺序沿用 M1 A 已验收清单。正式题集只为这些题添加 `gold_sql_by_dialect.postgres`；430题原始 DuckDB SQL、预期列/行、显式别名、排序与并列评分标注均保持原值。其余351题原始行字节保持一致，缺少 PostgreSQL 变体时继续明确拒绝。

原始题集完整字节留存在 `results/m1_all_cases_before_postgres_gold79_20261010.jsonl`。逐题机器记录在 `cases/m1_d3_postgres_gold79_review.json`，记录原 SQL/变体 SHA256、真实字段类型、过滤/连接/分组/排序/限制、逐题口径说明和待执行状态。审查类型是本次助手的离线审查，并非人工确认或服务器执行记录。

物理类型依据已经验收的 `m1_c3_postgres_runtime_server_v2.json`（41表、276字段）。当前审查只引用该冻结材料，未重新连接服务器验证其当前状态。

## 统一变更规则

| 项目 | 本次处理 | 数量 |
|---|---|---:|
| 数值真假判断 | 真实 BIGINT 标志改为 `<> 0`，保留非零为真、NULL 不进入 WHERE/CASE 真分支的语义 | 17处、13题 |
| 月份格式 | `strftime(..., '%Y-%m')` 改为 `TO_CHAR(..., 'YYYY-MM')`，原日期字段与范围不变 | 31处 |
| 除法 | 分子明确转为 DOUBLE PRECISION，保持原 DuckDB 浮点除法；原 NULLIF 零分母保护保留 | 19处 |
| 两参数 ROUND | 在原完整表达式外转为 NUMERIC/DECIMAL 后 ROUND，保持原2/4位精度与计算顺序 | 60处 |
| 月目标字符串 | SUBSTR 渲染为 PostgreSQL SUBSTRING，原起点、长度、月份条件不变 | 4处 |
| NULL/排序 | 每个排序节点保持 NULLS LAST；降序显式写出，升序沿用 PostgreSQL 默认。窗口排序也核对 | 88个节点 |
| 并列 | CONTENT_OPS-025 的 Top 10、边界值8和已批准候选逐字保留；其他次级排序键不变 | 既有规则 |

这些改写分别依据 PostgreSQL 16 的[数学函数](https://www.postgresql.org/docs/16/functions-math.html)、[格式化函数](https://www.postgresql.org/docs/16/functions-formatting.html)、[排序规则](https://www.postgresql.org/docs/16/queries-order.html)、[CASE/NULLIF](https://www.postgresql.org/docs/16/functions-conditional.html)及[聚合返回类型](https://www.postgresql.org/docs/16/functions-aggregate.html)。DECIMAL 在 PostgreSQL 中是 NUMERIC 的同义类型；本次不指定精度/标度，避免提前限制小数位数。[PostgreSQL数值类型](https://www.postgresql.org/docs/16/datatype-numeric.html)

SQL AST 用于辅助制作候选、比对允许的方言变化并核对字段作用域。正式评分始终选择题集中已保存的显式 SQL，不在运行时生成或回退。每题仍需实际 PostgreSQL 执行，尤其确认 numeric 舍入、中文排序、首月 NULL 和 Top N 并列。

## 逐题记录

以下逐题列出原问题、业务审查重点、来源与过滤、输出、类型变更、排序/并列，以及原 SQL 和最终保存的 PostgreSQL SQL。每题当前状态均为“离线审查通过，待 PostgreSQL 实际执行”。

### 1. GROWTH_OPS-001

**原问题：** 查询2026年每个月的新增用户数；请返回月份、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

**业务审查：** 按月求和原指标，保留冻结的 [2026-01-01, 2026-08-29) 日期范围；月份升序。

- 输出列：`month`, `value`。
- 物理来源：`growth_daily_metrics`。
- 本题引用的物理字段类型：`growth_daily_metrics.metric_date: date`、`growth_daily_metrics.new_users: bigint`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT strftime(metric_date, '%Y-%m') AS month, SUM(new_users) AS value FROM growth_daily_metrics WHERE metric_date >= DATE '2026-01-01' AND metric_date < DATE '2026-08-29' GROUP BY 1 ORDER BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  TO_CHAR(metric_date, 'YYYY-MM') AS month,
  SUM(new_users) AS value
FROM growth_daily_metrics
WHERE
  metric_date >= CAST('2026-01-01' AS DATE)
  AND metric_date < CAST('2026-08-29' AS DATE)
GROUP BY
  1
ORDER BY
  1
```

### 2. GROWTH_OPS-002

**原问题：** 查询2026年每个月的激活用户数；请返回月份、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

**业务审查：** 按月求和原指标，保留冻结的 [2026-01-01, 2026-08-29) 日期范围；月份升序。

- 输出列：`month`, `value`。
- 物理来源：`growth_daily_metrics`。
- 本题引用的物理字段类型：`growth_daily_metrics.activated_users: bigint`、`growth_daily_metrics.metric_date: date`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT strftime(metric_date, '%Y-%m') AS month, SUM(activated_users) AS value FROM growth_daily_metrics WHERE metric_date >= DATE '2026-01-01' AND metric_date < DATE '2026-08-29' GROUP BY 1 ORDER BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  TO_CHAR(metric_date, 'YYYY-MM') AS month,
  SUM(activated_users) AS value
FROM growth_daily_metrics
WHERE
  metric_date >= CAST('2026-01-01' AS DATE)
  AND metric_date < CAST('2026-08-29' AS DATE)
GROUP BY
  1
ORDER BY
  1
```

### 3. GROWTH_OPS-003

**原问题：** 查询2026年每个月的次日留存用户数；请返回月份、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

**业务审查：** 按月求和原指标，保留冻结的 [2026-01-01, 2026-08-29) 日期范围；月份升序。

- 输出列：`month`, `value`。
- 物理来源：`growth_daily_metrics`。
- 本题引用的物理字段类型：`growth_daily_metrics.day1_retained_users: bigint`、`growth_daily_metrics.metric_date: date`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT strftime(metric_date, '%Y-%m') AS month, SUM(day1_retained_users) AS value FROM growth_daily_metrics WHERE metric_date >= DATE '2026-01-01' AND metric_date < DATE '2026-08-29' GROUP BY 1 ORDER BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  TO_CHAR(metric_date, 'YYYY-MM') AS month,
  SUM(day1_retained_users) AS value
FROM growth_daily_metrics
WHERE
  metric_date >= CAST('2026-01-01' AS DATE)
  AND metric_date < CAST('2026-08-29' AS DATE)
GROUP BY
  1
ORDER BY
  1
```

### 4. GROWTH_OPS-004

**原问题：** 查询2026年每个月的七日留存用户数；请返回月份、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

**业务审查：** 按月求和原指标，保留冻结的 [2026-01-01, 2026-08-29) 日期范围；月份升序。

- 输出列：`month`, `value`。
- 物理来源：`growth_daily_metrics`。
- 本题引用的物理字段类型：`growth_daily_metrics.day7_retained_users: bigint`、`growth_daily_metrics.metric_date: date`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT strftime(metric_date, '%Y-%m') AS month, SUM(day7_retained_users) AS value FROM growth_daily_metrics WHERE metric_date >= DATE '2026-01-01' AND metric_date < DATE '2026-08-29' GROUP BY 1 ORDER BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  TO_CHAR(metric_date, 'YYYY-MM') AS month,
  SUM(day7_retained_users) AS value
FROM growth_daily_metrics
WHERE
  metric_date >= CAST('2026-01-01' AS DATE)
  AND metric_date < CAST('2026-08-29' AS DATE)
GROUP BY
  1
ORDER BY
  1
```

### 5. GROWTH_OPS-005

**原问题：** 查询2026年每个月的日活用户数；请返回月份、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

**业务审查：** 按月求和原指标，保留冻结的 [2026-01-01, 2026-08-29) 日期范围；月份升序。

- 输出列：`month`, `value`。
- 物理来源：`growth_daily_metrics`。
- 本题引用的物理字段类型：`growth_daily_metrics.daily_active_users: bigint`、`growth_daily_metrics.metric_date: date`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT strftime(metric_date, '%Y-%m') AS month, SUM(daily_active_users) AS value FROM growth_daily_metrics WHERE metric_date >= DATE '2026-01-01' AND metric_date < DATE '2026-08-29' GROUP BY 1 ORDER BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  TO_CHAR(metric_date, 'YYYY-MM') AS month,
  SUM(daily_active_users) AS value
FROM growth_daily_metrics
WHERE
  metric_date >= CAST('2026-01-01' AS DATE)
  AND metric_date < CAST('2026-08-29' AS DATE)
GROUP BY
  1
ORDER BY
  1
```

### 6. GROWTH_OPS-006

**原问题：** 查看2026-01每天的新增用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

**业务审查：** 原一月日期过滤、按日求和，保持 DATE 输出与日期升序。

- 输出列：`metric_date`, `value`。
- 物理来源：`growth_daily_metrics`。
- 本题引用的物理字段类型：`growth_daily_metrics.metric_date: date`、`growth_daily_metrics.new_users: bigint`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT metric_date, SUM(new_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-01' GROUP BY 1 ORDER BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  metric_date,
  SUM(new_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  1
```

### 7. GROWTH_OPS-026

**原问题：** 2026-01各获客渠道新增用户数排名；请返回渠道名称、新增用户数；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

**业务审查：** 一月渠道新增用户求和，保持渠道 JOIN、总数降序和渠道名次级排序。

- 输出列：`channel_name`, `new_users`。
- 物理来源：`acquisition_channels`, `growth_daily_metrics`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`growth_daily_metrics.channel_id: text`、`growth_daily_metrics.metric_date: date`、`growth_daily_metrics.new_users: bigint`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.channel_name, SUM(g.new_users) AS new_users FROM growth_daily_metrics g JOIN acquisition_channels c ON g.channel_id=c.channel_id WHERE strftime(g.metric_date, '%Y-%m')='2026-01' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.channel_name,
  SUM(g.new_users) AS new_users
FROM growth_daily_metrics AS g
JOIN acquisition_channels AS c
  ON g.channel_id = c.channel_id
WHERE
  TO_CHAR(g.metric_date, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 8. GROWTH_OPS-061

**原问题：** 自然推荐渠道激活用户的平均激活耗时；请返回渠道名称、平均激活耗时；聚合口径：平均指标取算术平均。

**业务审查：** 原指定渠道已激活样本的平均激活秒数；整数标志非零为真、NULL不进入样本，两位舍入。

- 输出列：`channel_name`, `avg_activation_seconds`。
- 物理来源：`acquisition_channels`, `user_activations`, `user_registrations`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`user_activations.activation_seconds: bigint`、`user_activations.is_activated: bigint`、`user_activations.registration_id: text`、`user_registrations.channel_id: text`、`user_registrations.registration_id: text`。
- 真假条件：`a.is_activated`（bigint）；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.channel_name, ROUND(AVG(a.activation_seconds),2) AS avg_activation_seconds FROM user_activations a JOIN user_registrations r ON a.registration_id=r.registration_id JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE a.is_activated AND c.channel_name='自然推荐' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.channel_name,
  ROUND(CAST(AVG(a.activation_seconds) AS DECIMAL), 2) AS avg_activation_seconds
FROM user_activations AS a
JOIN user_registrations AS r
  ON a.registration_id = r.registration_id
JOIN acquisition_channels AS c
  ON r.channel_id = c.channel_id
WHERE
  a.is_activated <> 0 AND c.channel_name = '自然推荐'
GROUP BY
  1
```

### 9. GROWTH_OPS-062

**原问题：** 应用商店渠道激活用户的平均激活耗时；请返回渠道名称、平均激活耗时；聚合口径：平均指标取算术平均。

**业务审查：** 原指定渠道已激活样本的平均激活秒数；整数标志非零为真、NULL不进入样本，两位舍入。

- 输出列：`channel_name`, `avg_activation_seconds`。
- 物理来源：`acquisition_channels`, `user_activations`, `user_registrations`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`user_activations.activation_seconds: bigint`、`user_activations.is_activated: bigint`、`user_activations.registration_id: text`、`user_registrations.channel_id: text`、`user_registrations.registration_id: text`。
- 真假条件：`a.is_activated`（bigint）；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.channel_name, ROUND(AVG(a.activation_seconds),2) AS avg_activation_seconds FROM user_activations a JOIN user_registrations r ON a.registration_id=r.registration_id JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE a.is_activated AND c.channel_name='应用商店' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.channel_name,
  ROUND(CAST(AVG(a.activation_seconds) AS DECIMAL), 2) AS avg_activation_seconds
FROM user_activations AS a
JOIN user_registrations AS r
  ON a.registration_id = r.registration_id
JOIN acquisition_channels AS c
  ON r.channel_id = c.channel_id
WHERE
  a.is_activated <> 0 AND c.channel_name = '应用商店'
GROUP BY
  1
```

### 10. GROWTH_OPS-063

**原问题：** 信息流广告渠道激活用户的平均激活耗时；请返回渠道名称、平均激活耗时；聚合口径：平均指标取算术平均。

**业务审查：** 原指定渠道已激活样本的平均激活秒数；整数标志非零为真、NULL不进入样本，两位舍入。

- 输出列：`channel_name`, `avg_activation_seconds`。
- 物理来源：`acquisition_channels`, `user_activations`, `user_registrations`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`user_activations.activation_seconds: bigint`、`user_activations.is_activated: bigint`、`user_activations.registration_id: text`、`user_registrations.channel_id: text`、`user_registrations.registration_id: text`。
- 真假条件：`a.is_activated`（bigint）；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.channel_name, ROUND(AVG(a.activation_seconds),2) AS avg_activation_seconds FROM user_activations a JOIN user_registrations r ON a.registration_id=r.registration_id JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE a.is_activated AND c.channel_name='信息流广告' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.channel_name,
  ROUND(CAST(AVG(a.activation_seconds) AS DECIMAL), 2) AS avg_activation_seconds
FROM user_activations AS a
JOIN user_registrations AS r
  ON a.registration_id = r.registration_id
JOIN acquisition_channels AS c
  ON r.channel_id = c.channel_id
WHERE
  a.is_activated <> 0 AND c.channel_name = '信息流广告'
GROUP BY
  1
```

### 11. GROWTH_OPS-064

**原问题：** 搜索广告渠道激活用户的平均激活耗时；请返回渠道名称、平均激活耗时；聚合口径：平均指标取算术平均。

**业务审查：** 原指定渠道已激活样本的平均激活秒数；整数标志非零为真、NULL不进入样本，两位舍入。

- 输出列：`channel_name`, `avg_activation_seconds`。
- 物理来源：`acquisition_channels`, `user_activations`, `user_registrations`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`user_activations.activation_seconds: bigint`、`user_activations.is_activated: bigint`、`user_activations.registration_id: text`、`user_registrations.channel_id: text`、`user_registrations.registration_id: text`。
- 真假条件：`a.is_activated`（bigint）；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.channel_name, ROUND(AVG(a.activation_seconds),2) AS avg_activation_seconds FROM user_activations a JOIN user_registrations r ON a.registration_id=r.registration_id JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE a.is_activated AND c.channel_name='搜索广告' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.channel_name,
  ROUND(CAST(AVG(a.activation_seconds) AS DECIMAL), 2) AS avg_activation_seconds
FROM user_activations AS a
JOIN user_registrations AS r
  ON a.registration_id = r.registration_id
JOIN acquisition_channels AS c
  ON r.channel_id = c.channel_id
WHERE
  a.is_activated <> 0 AND c.channel_name = '搜索广告'
GROUP BY
  1
```

### 12. GROWTH_OPS-066

**原问题：** 按激活规则统计用户数，重点查看观看3条视频；请返回激活规则、用户数；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 按激活规则计数；保留 CASE 对指定规则的排序优先级，再按人数和规则排序。

- 输出列：`activation_rule`, `users`。
- 物理来源：`user_activations`。
- 本题引用的物理字段类型：`user_activations.activation_id: text`、`user_activations.activation_rule: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY CASE WHEN activation_rule = '观看3条视频' THEN 0 ELSE 1 END, users DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT activation_rule, COUNT(activation_id) AS users FROM user_activations GROUP BY 1 ORDER BY CASE WHEN activation_rule='观看3条视频' THEN 0 ELSE 1 END, users DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  activation_rule,
  COUNT(activation_id) AS users
FROM user_activations
GROUP BY
  1
ORDER BY
  CASE WHEN activation_rule = '观看3条视频' THEN 0 ELSE 1 END,
  users DESC NULLS LAST,
  1
```

### 13. GROWTH_OPS-086

**原问题：** 华东用户平均活跃时长和会话次数；请返回地区、平均活跃时长、平均会话次数；聚合口径：平均指标取算术平均。

**业务审查：** 原地区筛选下的平均活跃分钟和会话数；保持原 JOIN、分组及两位精度。

- 输出列：`region`, `avg_active_minutes`, `avg_session_count`。
- 物理来源：`user_daily_activity`, `user_profiles`。
- 本题引用的物理字段类型：`user_daily_activity.active_minutes: bigint`、`user_daily_activity.session_count: bigint`、`user_daily_activity.user_id: text`、`user_profiles.region: text`、`user_profiles.user_id: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 2；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT p.region, ROUND(AVG(a.active_minutes),2) AS avg_active_minutes, ROUND(AVG(a.session_count),2) AS avg_session_count FROM user_daily_activity a JOIN user_profiles p ON a.user_id=p.user_id WHERE p.region='华东' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  p.region,
  ROUND(CAST(AVG(a.active_minutes) AS DECIMAL), 2) AS avg_active_minutes,
  ROUND(CAST(AVG(a.session_count) AS DECIMAL), 2) AS avg_session_count
FROM user_daily_activity AS a
JOIN user_profiles AS p
  ON a.user_id = p.user_id
WHERE
  p.region = '华东'
GROUP BY
  1
```

### 14. GROWTH_OPS-101

**原问题：** 用户按地区的分布；请返回地区、用户数；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 按原用户画像维度计数；人数降序、维度名次级排序。

- 输出列：`region`, `users`。
- 物理来源：`user_profiles`。
- 本题引用的物理字段类型：`user_profiles.region: text`、`user_profiles.user_id: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT region, COUNT(user_id) AS users FROM user_profiles GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  region,
  COUNT(user_id) AS users
FROM user_profiles
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 15. GROWTH_OPS-131

**原问题：** 面向沉默7天的召回活动效果排名；请返回活动名称、触达数量、召回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从高到低展示。

**业务审查：** 原召回人群条件下的触达计数与召回率；保持 JOIN 后触达总行数为分母，召回标志非零为真。

- 输出列：`campaign_name`, `touches`, `recall_rate`。
- 物理来源：`recall_campaigns`, `recall_results`, `recall_touches`。
- 本题引用的物理字段类型：`recall_campaigns.campaign_name: text`、`recall_campaigns.recall_campaign_id: text`、`recall_campaigns.target_segment: text`、`recall_results.recalled: bigint`、`recall_results.touch_id: text`、`recall_touches.recall_campaign_id: text`、`recall_touches.touch_id: text`。
- 真假条件：`r.recalled`（bigint）；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 1；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 3 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.campaign_name, COUNT(*) AS touches, ROUND(SUM(CASE WHEN r.recalled THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS recall_rate FROM recall_campaigns c JOIN recall_touches t ON c.recall_campaign_id=t.recall_campaign_id JOIN recall_results r ON t.touch_id=r.touch_id WHERE c.target_segment='沉默7天' GROUP BY 1 ORDER BY 3 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.campaign_name,
  COUNT(*) AS touches,
  ROUND(
    CAST(CAST(SUM(CASE WHEN r.recalled <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS recall_rate
FROM recall_campaigns AS c
JOIN recall_touches AS t
  ON c.recall_campaign_id = t.recall_campaign_id
JOIN recall_results AS r
  ON t.touch_id = r.touch_id
WHERE
  c.target_segment = '沉默7天'
GROUP BY
  1
ORDER BY
  3 DESC NULLS LAST,
  1
```

### 16. GROWTH_OPS-149

**原问题：** 2026-04各渠道激活率实际值与目标差距；请返回渠道名称、实际比率、激活率目标、目标差距；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

**业务审查：** 原注册月份 cohort 激活率与同月渠道目标比较；先用未舍入实际率减目标再舍入 gap，保留 gap 降序。

- 输出列：`channel_name`, `actual_rate`, `activation_rate_target`, `gap`。
- 物理来源：`acquisition_channels`, `growth_targets`, `user_activations`, `user_registrations`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`growth_targets.activation_rate_target: double precision`、`growth_targets.channel_id: text`、`growth_targets.target_month: text`、`user_activations.is_activated: bigint`、`user_activations.registration_id: text`、`user_registrations.channel_id: text`、`user_registrations.registered_at: timestamp without time zone`、`user_registrations.registration_id: text`。
- 真假条件：`a.is_activated`（bigint）；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 1；numeric ROUND 2；SUBSTRING 1；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY gap DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
WITH actual AS (SELECT r.channel_id, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/COUNT(*) AS actual_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id WHERE strftime(r.registered_at,'%Y-%m')='2026-04' GROUP BY 1) SELECT c.channel_name,ROUND(a.actual_rate,4) AS actual_rate,t.activation_rate_target, ROUND(a.actual_rate-t.activation_rate_target,4) AS gap FROM growth_targets t JOIN acquisition_channels c ON t.channel_id=c.channel_id JOIN actual a ON t.channel_id=a.channel_id WHERE substr(t.target_month,1,7)='2026-04' ORDER BY gap DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
WITH actual AS (
  SELECT
    r.channel_id,
    CAST(SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS actual_rate
  FROM user_registrations AS r
  JOIN user_activations AS a
    ON r.registration_id = a.registration_id
  WHERE
    TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-04'
  GROUP BY
    1
)
SELECT
  c.channel_name,
  ROUND(CAST(a.actual_rate AS DECIMAL), 4) AS actual_rate,
  t.activation_rate_target,
  ROUND(CAST(a.actual_rate - t.activation_rate_target AS DECIMAL), 4) AS gap
FROM growth_targets AS t
JOIN acquisition_channels AS c
  ON t.channel_id = c.channel_id
JOIN actual AS a
  ON t.channel_id = a.channel_id
WHERE
  SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-04'
ORDER BY
  gap DESC NULLS LAST,
  1
```

### 17. GROWTH_OPS-150

**原问题：** 2026-05各渠道激活率实际值与目标差距；请返回渠道名称、实际比率、激活率目标、目标差距；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

**业务审查：** 原注册月份 cohort 激活率与同月渠道目标比较；先用未舍入实际率减目标再舍入 gap，保留 gap 降序。

- 输出列：`channel_name`, `actual_rate`, `activation_rate_target`, `gap`。
- 物理来源：`acquisition_channels`, `growth_targets`, `user_activations`, `user_registrations`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`growth_targets.activation_rate_target: double precision`、`growth_targets.channel_id: text`、`growth_targets.target_month: text`、`user_activations.is_activated: bigint`、`user_activations.registration_id: text`、`user_registrations.channel_id: text`、`user_registrations.registered_at: timestamp without time zone`、`user_registrations.registration_id: text`。
- 真假条件：`a.is_activated`（bigint）；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 1；numeric ROUND 2；SUBSTRING 1；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY gap DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
WITH actual AS (SELECT r.channel_id, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/COUNT(*) AS actual_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id WHERE strftime(r.registered_at,'%Y-%m')='2026-05' GROUP BY 1) SELECT c.channel_name,ROUND(a.actual_rate,4) AS actual_rate,t.activation_rate_target, ROUND(a.actual_rate-t.activation_rate_target,4) AS gap FROM growth_targets t JOIN acquisition_channels c ON t.channel_id=c.channel_id JOIN actual a ON t.channel_id=a.channel_id WHERE substr(t.target_month,1,7)='2026-05' ORDER BY gap DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
WITH actual AS (
  SELECT
    r.channel_id,
    CAST(SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS actual_rate
  FROM user_registrations AS r
  JOIN user_activations AS a
    ON r.registration_id = a.registration_id
  WHERE
    TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-05'
  GROUP BY
    1
)
SELECT
  c.channel_name,
  ROUND(CAST(a.actual_rate AS DECIMAL), 4) AS actual_rate,
  t.activation_rate_target,
  ROUND(CAST(a.actual_rate - t.activation_rate_target AS DECIMAL), 4) AS gap
FROM growth_targets AS t
JOIN acquisition_channels AS c
  ON t.channel_id = c.channel_id
JOIN actual AS a
  ON t.channel_id = a.channel_id
WHERE
  SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-05'
ORDER BY
  gap DESC NULLS LAST,
  1
```

### 18. CHANNEL_OPS-001

**原问题：** 2026-01每天的广告消耗；请返回统计日期、广告消耗；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

**业务审查：** 原月份按日汇总花费，先 SUM 再两位舍入；日期升序，不补齐缺失日期。

- 输出列：`stat_date`, `spend`。
- 物理来源：`ad_daily_stats`。
- 本题引用的物理字段类型：`ad_daily_stats.spend: double precision`、`ad_daily_stats.stat_date: date`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT stat_date,ROUND(SUM(spend),2) spend FROM ad_daily_stats WHERE strftime(stat_date,'%Y-%m')='2026-01' GROUP BY 1 ORDER BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  stat_date,
  ROUND(CAST(SUM(spend) AS DECIMAL), 2) AS spend
FROM ad_daily_stats
WHERE
  TO_CHAR(stat_date, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  1
```

### 19. CHANNEL_OPS-002

**原问题：** 2026-02每天的广告消耗；请返回统计日期、广告消耗；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

**业务审查：** 原月份按日汇总花费，先 SUM 再两位舍入；日期升序，不补齐缺失日期。

- 输出列：`stat_date`, `spend`。
- 物理来源：`ad_daily_stats`。
- 本题引用的物理字段类型：`ad_daily_stats.spend: double precision`、`ad_daily_stats.stat_date: date`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT stat_date,ROUND(SUM(spend),2) spend FROM ad_daily_stats WHERE strftime(stat_date,'%Y-%m')='2026-02' GROUP BY 1 ORDER BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  stat_date,
  ROUND(CAST(SUM(spend) AS DECIMAL), 2) AS spend
FROM ad_daily_stats
WHERE
  TO_CHAR(stat_date, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  1
```

### 20. CHANNEL_OPS-003

**原问题：** 2026-03每天的广告消耗；请返回统计日期、广告消耗；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

**业务审查：** 原月份按日汇总花费，先 SUM 再两位舍入；日期升序，不补齐缺失日期。

- 输出列：`stat_date`, `spend`。
- 物理来源：`ad_daily_stats`。
- 本题引用的物理字段类型：`ad_daily_stats.spend: double precision`、`ad_daily_stats.stat_date: date`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT stat_date,ROUND(SUM(spend),2) spend FROM ad_daily_stats WHERE strftime(stat_date,'%Y-%m')='2026-03' GROUP BY 1 ORDER BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  stat_date,
  ROUND(CAST(SUM(spend) AS DECIMAL), 2) AS spend
FROM ad_daily_stats
WHERE
  TO_CHAR(stat_date, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  1
```

### 21. CHANNEL_OPS-004

**原问题：** 2026-04每天的广告消耗；请返回统计日期、广告消耗；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

**业务审查：** 原月份按日汇总花费，先 SUM 再两位舍入；日期升序，不补齐缺失日期。

- 输出列：`stat_date`, `spend`。
- 物理来源：`ad_daily_stats`。
- 本题引用的物理字段类型：`ad_daily_stats.spend: double precision`、`ad_daily_stats.stat_date: date`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT stat_date,ROUND(SUM(spend),2) spend FROM ad_daily_stats WHERE strftime(stat_date,'%Y-%m')='2026-04' GROUP BY 1 ORDER BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  stat_date,
  ROUND(CAST(SUM(spend) AS DECIMAL), 2) AS spend
FROM ad_daily_stats
WHERE
  TO_CHAR(stat_date, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  1
```

### 22. CHANNEL_OPS-005

**原问题：** 2026-05每天的广告消耗；请返回统计日期、广告消耗；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

**业务审查：** 原月份按日汇总花费，先 SUM 再两位舍入；日期升序，不补齐缺失日期。

- 输出列：`stat_date`, `spend`。
- 物理来源：`ad_daily_stats`。
- 本题引用的物理字段类型：`ad_daily_stats.spend: double precision`、`ad_daily_stats.stat_date: date`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT stat_date,ROUND(SUM(spend),2) spend FROM ad_daily_stats WHERE strftime(stat_date,'%Y-%m')='2026-05' GROUP BY 1 ORDER BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  stat_date,
  ROUND(CAST(SUM(spend) AS DECIMAL), 2) AS spend
FROM ad_daily_stats
WHERE
  TO_CHAR(stat_date, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  1
```

### 23. CHANNEL_OPS-066

**原问题：** registration转化事件的数量和平均价值；请返回转化类型、转化数、平均价值；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

**业务审查：** 原转化类型条件下的转化行数与平均转化价值；保留 COUNT(*) 与两位平均值。

- 输出列：`conversion_type`, `conversions`, `avg_value`。
- 物理来源：`channel_conversion_events`。
- 本题引用的物理字段类型：`channel_conversion_events.conversion_type: text`、`channel_conversion_events.conversion_value: bigint`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT conversion_type,COUNT(*) conversions,ROUND(AVG(conversion_value),2) avg_value FROM channel_conversion_events WHERE conversion_type='registration' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  conversion_type,
  COUNT(*) AS conversions,
  ROUND(CAST(AVG(conversion_value) AS DECIMAL), 2) AS avg_value
FROM channel_conversion_events
WHERE
  conversion_type = 'registration'
GROUP BY
  1
```

### 24. CHANNEL_OPS-067

**原问题：** activation转化事件的数量和平均价值；请返回转化类型、转化数、平均价值；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

**业务审查：** 原转化类型条件下的转化行数与平均转化价值；保留 COUNT(*) 与两位平均值。

- 输出列：`conversion_type`, `conversions`, `avg_value`。
- 物理来源：`channel_conversion_events`。
- 本题引用的物理字段类型：`channel_conversion_events.conversion_type: text`、`channel_conversion_events.conversion_value: bigint`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT conversion_type,COUNT(*) conversions,ROUND(AVG(conversion_value),2) avg_value FROM channel_conversion_events WHERE conversion_type='activation' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  conversion_type,
  COUNT(*) AS conversions,
  ROUND(CAST(AVG(conversion_value) AS DECIMAL), 2) AS avg_value
FROM channel_conversion_events
WHERE
  conversion_type = 'activation'
GROUP BY
  1
```

### 25. CHANNEL_OPS-068

**原问题：** 请汇总registration转化事件的数量和平均价值；请返回转化类型、转化数、平均价值；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

**业务审查：** 原转化类型条件下的转化行数与平均转化价值；保留 COUNT(*) 与两位平均值。

- 输出列：`conversion_type`, `conversions`, `avg_value`。
- 物理来源：`channel_conversion_events`。
- 本题引用的物理字段类型：`channel_conversion_events.conversion_type: text`、`channel_conversion_events.conversion_value: bigint`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT conversion_type,COUNT(*) conversions,ROUND(AVG(conversion_value),2) avg_value FROM channel_conversion_events WHERE conversion_type='registration' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  conversion_type,
  COUNT(*) AS conversions,
  ROUND(CAST(AVG(conversion_value) AS DECIMAL), 2) AS avg_value
FROM channel_conversion_events
WHERE
  conversion_type = 'registration'
GROUP BY
  1
```

### 26. CHANNEL_OPS-069

**原问题：** 请汇总activation转化事件的数量和平均价值；请返回转化类型、转化数、平均价值；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

**业务审查：** 原转化类型条件下的转化行数与平均转化价值；保留 COUNT(*) 与两位平均值。

- 输出列：`conversion_type`, `conversions`, `avg_value`。
- 物理来源：`channel_conversion_events`。
- 本题引用的物理字段类型：`channel_conversion_events.conversion_type: text`、`channel_conversion_events.conversion_value: bigint`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT conversion_type,COUNT(*) conversions,ROUND(AVG(conversion_value),2) avg_value FROM channel_conversion_events WHERE conversion_type='activation' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  conversion_type,
  COUNT(*) AS conversions,
  ROUND(CAST(AVG(conversion_value) AS DECIMAL), 2) AS avg_value
FROM channel_conversion_events
WHERE
  conversion_type = 'activation'
GROUP BY
  1
```

### 27. CHANNEL_OPS-070

**原问题：** 请分析registration转化事件的数量和平均价值；请返回转化类型、转化数、平均价值；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

**业务审查：** 原转化类型条件下的转化行数与平均转化价值；保留 COUNT(*) 与两位平均值。

- 输出列：`conversion_type`, `conversions`, `avg_value`。
- 物理来源：`channel_conversion_events`。
- 本题引用的物理字段类型：`channel_conversion_events.conversion_type: text`、`channel_conversion_events.conversion_value: bigint`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT conversion_type,COUNT(*) conversions,ROUND(AVG(conversion_value),2) avg_value FROM channel_conversion_events WHERE conversion_type='registration' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  conversion_type,
  COUNT(*) AS conversions,
  ROUND(CAST(AVG(conversion_value) AS DECIMAL), 2) AS avg_value
FROM channel_conversion_events
WHERE
  conversion_type = 'registration'
GROUP BY
  1
```

### 28. CHANNEL_OPS-076

**原问题：** 统计active状态广告计划的数量和预算；请返回状态、广告计划数、预算；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和。

**业务审查：** 原广告计划状态条件下的计划ID计数、预算总和；先求和再舍入。

- 输出列：`status`, `campaigns`, `budget`。
- 物理来源：`ad_campaigns`。
- 本题引用的物理字段类型：`ad_campaigns.ad_campaign_id: text`、`ad_campaigns.budget: bigint`、`ad_campaigns.status: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT status,COUNT(ad_campaign_id) campaigns,ROUND(SUM(budget),2) budget FROM ad_campaigns WHERE status='active' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  status,
  COUNT(ad_campaign_id) AS campaigns,
  ROUND(CAST(SUM(budget) AS DECIMAL), 2) AS budget
FROM ad_campaigns
WHERE
  status = 'active'
GROUP BY
  1
```

### 29. CHANNEL_OPS-077

**原问题：** 统计completed状态广告计划的数量和预算；请返回状态、广告计划数、预算；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和。

**业务审查：** 原广告计划状态条件下的计划ID计数、预算总和；先求和再舍入。

- 输出列：`status`, `campaigns`, `budget`。
- 物理来源：`ad_campaigns`。
- 本题引用的物理字段类型：`ad_campaigns.ad_campaign_id: text`、`ad_campaigns.budget: bigint`、`ad_campaigns.status: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT status,COUNT(ad_campaign_id) campaigns,ROUND(SUM(budget),2) budget FROM ad_campaigns WHERE status='completed' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  status,
  COUNT(ad_campaign_id) AS campaigns,
  ROUND(CAST(SUM(budget) AS DECIMAL), 2) AS budget
FROM ad_campaigns
WHERE
  status = 'completed'
GROUP BY
  1
```

### 30. CHANNEL_OPS-078

**原问题：** 请汇总统计active状态广告计划的数量和预算；请返回状态、广告计划数、预算；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和。

**业务审查：** 原广告计划状态条件下的计划ID计数、预算总和；先求和再舍入。

- 输出列：`status`, `campaigns`, `budget`。
- 物理来源：`ad_campaigns`。
- 本题引用的物理字段类型：`ad_campaigns.ad_campaign_id: text`、`ad_campaigns.budget: bigint`、`ad_campaigns.status: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT status,COUNT(ad_campaign_id) campaigns,ROUND(SUM(budget),2) budget FROM ad_campaigns WHERE status='active' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  status,
  COUNT(ad_campaign_id) AS campaigns,
  ROUND(CAST(SUM(budget) AS DECIMAL), 2) AS budget
FROM ad_campaigns
WHERE
  status = 'active'
GROUP BY
  1
```

### 31. CHANNEL_OPS-079

**原问题：** 请汇总统计completed状态广告计划的数量和预算；请返回状态、广告计划数、预算；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和。

**业务审查：** 原广告计划状态条件下的计划ID计数、预算总和；先求和再舍入。

- 输出列：`status`, `campaigns`, `budget`。
- 物理来源：`ad_campaigns`。
- 本题引用的物理字段类型：`ad_campaigns.ad_campaign_id: text`、`ad_campaigns.budget: bigint`、`ad_campaigns.status: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT status,COUNT(ad_campaign_id) campaigns,ROUND(SUM(budget),2) budget FROM ad_campaigns WHERE status='completed' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  status,
  COUNT(ad_campaign_id) AS campaigns,
  ROUND(CAST(SUM(budget) AS DECIMAL), 2) AS budget
FROM ad_campaigns
WHERE
  status = 'completed'
GROUP BY
  1
```

### 32. CHANNEL_OPS-101

**原问题：** 短视频创意的状态分布；请返回创意状态、创意数量；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 原素材类型按状态计数；保留素材ID计数、数量降序和状态次级排序。

- 输出列：`creative_status`, `creatives`。
- 物理来源：`ad_creatives`。
- 本题引用的物理字段类型：`ad_creatives.creative_id: text`、`ad_creatives.creative_status: text`、`ad_creatives.creative_type: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT creative_status,COUNT(creative_id) creatives FROM ad_creatives WHERE creative_type='短视频' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  creative_status,
  COUNT(creative_id) AS creatives
FROM ad_creatives
WHERE
  creative_type = '短视频'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 33. CHANNEL_OPS-141

**原问题：** registration转化按渠道分布；请返回渠道名称、转化数；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 原注册转化事件按渠道计数；保留事件ID口径、JOIN 与排序。

- 输出列：`channel_name`, `conversions`。
- 物理来源：`acquisition_channels`, `channel_conversion_events`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`channel_conversion_events.channel_id: text`、`channel_conversion_events.conversion_event_id: text`、`channel_conversion_events.conversion_type: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.channel_name,COUNT(e.conversion_event_id) conversions FROM channel_conversion_events e JOIN acquisition_channels c ON e.channel_id=c.channel_id WHERE e.conversion_type='registration' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.channel_name,
  COUNT(e.conversion_event_id) AS conversions
FROM channel_conversion_events AS e
JOIN acquisition_channels AS c
  ON e.channel_id = c.channel_id
WHERE
  e.conversion_type = 'registration'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 34. CONTENT_OPS-001

**原问题：** 2026-01每天的视频曝光量和播放量；请返回指标日期、曝光量、播放量；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

**业务审查：** 原月份按日汇总曝光与播放；日期粒度及升序不变。

- 输出列：`metric_date`, `impressions`, `plays`。
- 物理来源：`content_daily_metrics`。
- 本题引用的物理字段类型：`content_daily_metrics.impressions: bigint`、`content_daily_metrics.metric_date: date`、`content_daily_metrics.play_count: bigint`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT metric_date,SUM(impressions) impressions,SUM(play_count) plays FROM content_daily_metrics WHERE strftime(metric_date,'%Y-%m')='2026-01' GROUP BY 1 ORDER BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  metric_date,
  SUM(impressions) AS impressions,
  SUM(play_count) AS plays
FROM content_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  1
```

### 35. CONTENT_OPS-029

**原问题：** 基于播放明细，计算知识类内容每次播放的平均观看时长和平均完播率；请返回内容分类、平均观看时长、平均完播率；聚合口径：平均指标取算术平均。

**业务审查：** 原分类播放样本的平均观看秒数和完播率；保留普通 AVG、原 JOIN 及两/四位精度。

- 输出列：`category_name`, `avg_watch_seconds`, `avg_completion_rate`。
- 物理来源：`content_categories`, `contents`, `video_plays`。
- 本题引用的物理字段类型：`content_categories.category_id: text`、`content_categories.category_name: text`、`contents.category_id: text`、`contents.content_id: text`、`video_plays.completion_rate: double precision`、`video_plays.content_id: text`、`video_plays.watch_seconds: bigint`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 2；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT cat.category_name,ROUND(AVG(p.watch_seconds),2) avg_watch_seconds, ROUND(AVG(p.completion_rate),4) avg_completion_rate FROM video_plays p JOIN contents c ON p.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='知识' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  cat.category_name,
  ROUND(CAST(AVG(p.watch_seconds) AS DECIMAL), 2) AS avg_watch_seconds,
  ROUND(CAST(AVG(p.completion_rate) AS DECIMAL), 4) AS avg_completion_rate
FROM video_plays AS p
JOIN contents AS c
  ON p.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '知识'
GROUP BY
  1
```

### 36. CONTENT_OPS-030

**原问题：** 基于播放明细，计算体育类内容每次播放的平均观看时长和平均完播率；请返回内容分类、平均观看时长、平均完播率；聚合口径：平均指标取算术平均。

**业务审查：** 原分类播放样本的平均观看秒数和完播率；保留普通 AVG、原 JOIN 及两/四位精度。

- 输出列：`category_name`, `avg_watch_seconds`, `avg_completion_rate`。
- 物理来源：`content_categories`, `contents`, `video_plays`。
- 本题引用的物理字段类型：`content_categories.category_id: text`、`content_categories.category_name: text`、`contents.category_id: text`、`contents.content_id: text`、`video_plays.completion_rate: double precision`、`video_plays.content_id: text`、`video_plays.watch_seconds: bigint`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 2；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT cat.category_name,ROUND(AVG(p.watch_seconds),2) avg_watch_seconds, ROUND(AVG(p.completion_rate),4) avg_completion_rate FROM video_plays p JOIN contents c ON p.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='体育' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  cat.category_name,
  ROUND(CAST(AVG(p.watch_seconds) AS DECIMAL), 2) AS avg_watch_seconds,
  ROUND(CAST(AVG(p.completion_rate) AS DECIMAL), 4) AS avg_completion_rate
FROM video_plays AS p
JOIN contents AS c
  ON p.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '体育'
GROUP BY
  1
```

### 37. CONTENT_OPS-031

**原问题：** like互动按内容分类分布；请返回内容分类、互动数；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 原互动类型按内容分类计数；保留互动ID口径、JOIN、数量降序及分类名次级排序。

- 输出列：`category_name`, `interactions`。
- 物理来源：`content_categories`, `contents`, `video_interactions`。
- 本题引用的物理字段类型：`content_categories.category_id: text`、`content_categories.category_name: text`、`contents.category_id: text`、`contents.content_id: text`、`video_interactions.content_id: text`、`video_interactions.interaction_id: text`、`video_interactions.interaction_type: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT cat.category_name,COUNT(i.interaction_id) interactions FROM video_interactions i JOIN contents c ON i.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE i.interaction_type='like' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  cat.category_name,
  COUNT(i.interaction_id) AS interactions
FROM video_interactions AS i
JOIN contents AS c
  ON i.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  i.interaction_type = 'like'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 38. CONTENT_OPS-032

**原问题：** comment互动按内容分类分布；请返回内容分类、互动数；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 原互动类型按内容分类计数；保留互动ID口径、JOIN、数量降序及分类名次级排序。

- 输出列：`category_name`, `interactions`。
- 物理来源：`content_categories`, `contents`, `video_interactions`。
- 本题引用的物理字段类型：`content_categories.category_id: text`、`content_categories.category_name: text`、`contents.category_id: text`、`contents.content_id: text`、`video_interactions.content_id: text`、`video_interactions.interaction_id: text`、`video_interactions.interaction_type: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT cat.category_name,COUNT(i.interaction_id) interactions FROM video_interactions i JOIN contents c ON i.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE i.interaction_type='comment' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  cat.category_name,
  COUNT(i.interaction_id) AS interactions
FROM video_interactions AS i
JOIN contents AS c
  ON i.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  i.interaction_type = 'comment'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 39. CONTENT_OPS-033

**原问题：** share互动按内容分类分布；请返回内容分类、互动数；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 原互动类型按内容分类计数；保留互动ID口径、JOIN、数量降序及分类名次级排序。

- 输出列：`category_name`, `interactions`。
- 物理来源：`content_categories`, `contents`, `video_interactions`。
- 本题引用的物理字段类型：`content_categories.category_id: text`、`content_categories.category_name: text`、`contents.category_id: text`、`contents.content_id: text`、`video_interactions.content_id: text`、`video_interactions.interaction_id: text`、`video_interactions.interaction_type: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT cat.category_name,COUNT(i.interaction_id) interactions FROM video_interactions i JOIN contents c ON i.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE i.interaction_type='share' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  cat.category_name,
  COUNT(i.interaction_id) AS interactions
FROM video_interactions AS i
JOIN contents AS c
  ON i.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  i.interaction_type = 'share'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 40. CONTENT_OPS-034

**原问题：** favorite互动按内容分类分布；请返回内容分类、互动数；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 原互动类型按内容分类计数；保留互动ID口径、JOIN、数量降序及分类名次级排序。

- 输出列：`category_name`, `interactions`。
- 物理来源：`content_categories`, `contents`, `video_interactions`。
- 本题引用的物理字段类型：`content_categories.category_id: text`、`content_categories.category_name: text`、`contents.category_id: text`、`contents.content_id: text`、`video_interactions.content_id: text`、`video_interactions.interaction_id: text`、`video_interactions.interaction_type: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT cat.category_name,COUNT(i.interaction_id) interactions FROM video_interactions i JOIN contents c ON i.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE i.interaction_type='favorite' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  cat.category_name,
  COUNT(i.interaction_id) AS interactions
FROM video_interactions AS i
JOIN contents AS c
  ON i.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  i.interaction_type = 'favorite'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 41. CONTENT_OPS-035

**原问题：** follow互动按内容分类分布；请返回内容分类、互动数；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 原互动类型按内容分类计数；保留互动ID口径、JOIN、数量降序及分类名次级排序。

- 输出列：`category_name`, `interactions`。
- 物理来源：`content_categories`, `contents`, `video_interactions`。
- 本题引用的物理字段类型：`content_categories.category_id: text`、`content_categories.category_name: text`、`contents.category_id: text`、`contents.content_id: text`、`video_interactions.content_id: text`、`video_interactions.interaction_id: text`、`video_interactions.interaction_type: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT cat.category_name,COUNT(i.interaction_id) interactions FROM video_interactions i JOIN contents c ON i.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE i.interaction_type='follow' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  cat.category_name,
  COUNT(i.interaction_id) AS interactions
FROM video_interactions AS i
JOIN contents AS c
  ON i.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  i.interaction_type = 'follow'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 42. CONTENT_OPS-036

**原问题：** 2026-01每天的有效互动数；请返回互动日期、互动数；聚合口径：数量指标按对应业务记录计数；按时间升序展示。

**业务审查：** 一月有效互动按 interacted_at 转 DATE 聚合；数值有效标志非零为真，保留原日粒度和日期升序。

- 输出列：`interaction_date`, `interactions`。
- 物理来源：`video_interactions`。
- 本题引用的物理字段类型：`video_interactions.interacted_at: timestamp without time zone`、`video_interactions.interaction_id: text`、`video_interactions.valid_interaction: bigint`。
- 真假条件：`valid_interaction`（bigint）；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT CAST(interacted_at AS DATE) interaction_date,COUNT(interaction_id) interactions FROM video_interactions WHERE valid_interaction AND strftime(interacted_at,'%Y-%m')='2026-01' GROUP BY 1 ORDER BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  CAST(interacted_at AS DATE) AS interaction_date,
  COUNT(interaction_id) AS interactions
FROM video_interactions
WHERE
  valid_interaction <> 0 AND TO_CHAR(interacted_at, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  1
```

### 43. CONTENT_OPS-051

**原问题：** 搞笑类内容数量和平均视频时长；请返回内容分类、内容数量、平均视频时长；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

**业务审查：** 原分类内容量和平均时长；保持内容ID计数、普通 AVG 和两位精度。

- 输出列：`category_name`, `contents`, `avg_duration_seconds`。
- 物理来源：`content_categories`, `contents`。
- 本题引用的物理字段类型：`content_categories.category_id: text`、`content_categories.category_name: text`、`contents.category_id: text`、`contents.content_id: text`、`contents.duration_seconds: bigint`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT cat.category_name,COUNT(c.content_id) contents,ROUND(AVG(c.duration_seconds),2) avg_duration_seconds FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='搞笑' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  cat.category_name,
  COUNT(c.content_id) AS contents,
  ROUND(CAST(AVG(c.duration_seconds) AS DECIMAL), 2) AS avg_duration_seconds
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '搞笑'
GROUP BY
  1
```

### 44. CONTENT_OPS-076

**原问题：** 新星级创作者数量和状态分布；请返回创作者状态、创作者数量；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 原创作者等级按状态计数；创作者ID口径、数量降序及状态排序不变。

- 输出列：`creator_status`, `creators`。
- 物理来源：`creators`。
- 本题引用的物理字段类型：`creators.creator_id: text`、`creators.creator_level: text`、`creators.creator_status: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT creator_status,COUNT(creator_id) creators FROM creators WHERE creator_level='新星' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  creator_status,
  COUNT(creator_id) AS creators
FROM creators
WHERE
  creator_level = '新星'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 45. CONTENT_OPS-121

**原问题：** 流量加热系数至少1.0的热点内容数量和平均排名；请返回最低流量加热系数、内容数量、平均排名；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均；按核心指标从高到低展示。

**业务审查：** 原 traffic_boost 下限、固定阈值输出、内容ID计数与平均 ranking 保持一致。

- 输出列：`min_traffic_boost`, `contents`, `avg_ranking`。
- 物理来源：`topic_content_relations`。
- 本题引用的物理字段类型：`topic_content_relations.content_id: text`、`topic_content_relations.ranking: bigint`、`topic_content_relations.traffic_boost: double precision`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT 1.0 min_traffic_boost,COUNT(content_id) contents,ROUND(AVG(ranking),2) avg_ranking FROM topic_content_relations WHERE traffic_boost>=1.0
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  1.0 AS min_traffic_boost,
  COUNT(content_id) AS contents,
  ROUND(CAST(AVG(ranking) AS DECIMAL), 2) AS avg_ranking
FROM topic_content_relations
WHERE
  traffic_boost >= 1.0
```

### 46. CONTENT_OPS-126

**原问题：** approved审核状态按风险类型分布；请返回风险类型、审核数量；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 原 approved 审核按风险类型计数；审核ID口径与数量/类型排序不变。

- 输出列：`risk_type`, `audits`。
- 物理来源：`content_audits`。
- 本题引用的物理字段类型：`content_audits.audit_id: text`、`content_audits.audit_status: text`、`content_audits.risk_type: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT risk_type,COUNT(audit_id) audits FROM content_audits WHERE audit_status='approved' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  risk_type,
  COUNT(audit_id) AS audits
FROM content_audits
WHERE
  audit_status = 'approved'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 47. CONTENT_OPS-136

**原问题：** 不感兴趣举报按内容分类分布；请返回内容分类、举报数量；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 原举报原因按分类计数；保留举报ID、JOIN、数量降序及分类名次级排序。

- 输出列：`category_name`, `reports`。
- 物理来源：`content_categories`, `content_reports`, `contents`。
- 本题引用的物理字段类型：`content_categories.category_id: text`、`content_categories.category_name: text`、`content_reports.content_id: text`、`content_reports.report_id: text`、`content_reports.report_reason: text`、`contents.category_id: text`、`contents.content_id: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT cat.category_name,COUNT(r.report_id) reports FROM content_reports r JOIN contents c ON r.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE r.report_reason='不感兴趣' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  cat.category_name,
  COUNT(r.report_id) AS reports
FROM content_reports AS r
JOIN contents AS c
  ON r.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  r.report_reason = '不感兴趣'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 48. CONTENT_OPS-137

**原问题：** 低俗内容举报按内容分类分布；请返回内容分类、举报数量；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 原举报原因按分类计数；保留举报ID、JOIN、数量降序及分类名次级排序。

- 输出列：`category_name`, `reports`。
- 物理来源：`content_categories`, `content_reports`, `contents`。
- 本题引用的物理字段类型：`content_categories.category_id: text`、`content_categories.category_name: text`、`content_reports.content_id: text`、`content_reports.report_id: text`、`content_reports.report_reason: text`、`contents.category_id: text`、`contents.content_id: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT cat.category_name,COUNT(r.report_id) reports FROM content_reports r JOIN contents c ON r.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE r.report_reason='低俗内容' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  cat.category_name,
  COUNT(r.report_id) AS reports
FROM content_reports AS r
JOIN contents AS c
  ON r.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  r.report_reason = '低俗内容'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 49. CONTENT_OPS-138

**原问题：** 侵权搬运举报按内容分类分布；请返回内容分类、举报数量；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 原举报原因按分类计数；保留举报ID、JOIN、数量降序及分类名次级排序。

- 输出列：`category_name`, `reports`。
- 物理来源：`content_categories`, `content_reports`, `contents`。
- 本题引用的物理字段类型：`content_categories.category_id: text`、`content_categories.category_name: text`、`content_reports.content_id: text`、`content_reports.report_id: text`、`content_reports.report_reason: text`、`contents.category_id: text`、`contents.content_id: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT cat.category_name,COUNT(r.report_id) reports FROM content_reports r JOIN contents c ON r.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE r.report_reason='侵权搬运' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  cat.category_name,
  COUNT(r.report_id) AS reports
FROM content_reports AS r
JOIN contents AS c
  ON r.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  r.report_reason = '侵权搬运'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 50. GROWTH_OPS-007

**原问题：** 查看2026-01每天的激活用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

**业务审查：** 原一月日期过滤、按日求和，保持 DATE 输出与日期升序。

- 输出列：`metric_date`, `value`。
- 物理来源：`growth_daily_metrics`。
- 本题引用的物理字段类型：`growth_daily_metrics.activated_users: bigint`、`growth_daily_metrics.metric_date: date`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT metric_date, SUM(activated_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-01' GROUP BY 1 ORDER BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  metric_date,
  SUM(activated_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  1
```

### 51. GROWTH_OPS-050

**原问题：** 2026-02Android端各渠道注册人数排行；请返回渠道名称、注册用户数；聚合口径：数量指标按对应业务记录计数；按核心指标从高到低展示。

**业务审查：** 二月 Android 注册量按渠道聚合；保持原日期与平台筛选、JOIN 和排序。

- 输出列：`channel_name`, `registrations`。
- 物理来源：`acquisition_channels`, `user_registrations`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`user_registrations.channel_id: text`、`user_registrations.platform: text`、`user_registrations.registered_at: timestamp without time zone`、`user_registrations.registration_id: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.channel_name, COUNT(r.registration_id) AS registrations FROM user_registrations r JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE strftime(r.registered_at,'%Y-%m')='2026-02' AND r.platform='Android' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.channel_name,
  COUNT(r.registration_id) AS registrations
FROM user_registrations AS r
JOIN acquisition_channels AS c
  ON r.channel_id = c.channel_id
WHERE
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-02' AND r.platform = 'Android'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 52. GROWTH_OPS-051

**原问题：** 2026-01各渠道注册到激活的转化率；请返回渠道名称、注册用户数、激活用户数、激活率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

**业务审查：** 一月注册 cohort 的注册量、已激活量和激活率；两处真假判断一致，分母为注册ID计数，保留 NULLIF。

- 输出列：`channel_name`, `registrations`, `activated_users`, `activation_rate`。
- 物理来源：`acquisition_channels`, `user_activations`, `user_registrations`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`user_activations.is_activated: bigint`、`user_activations.registration_id: text`、`user_registrations.channel_id: text`、`user_registrations.registered_at: timestamp without time zone`、`user_registrations.registration_id: text`。
- 真假条件：`a.is_activated`（bigint）、`a.is_activated`（bigint）；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 1；numeric ROUND 1；SUBSTRING 0；NULLIF 1（保留）。
- 原排序/限制：`ORDER BY 4 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.channel_name, COUNT(r.registration_id) AS registrations, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) AS activated_users, ROUND(SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/NULLIF(COUNT(r.registration_id),0),4) AS activation_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE strftime(r.registered_at,'%Y-%m')='2026-01' GROUP BY 1 ORDER BY 4 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.channel_name,
  COUNT(r.registration_id) AS registrations,
  SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) AS activated_users,
  ROUND(
    CAST(CAST(SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / NULLIF(COUNT(r.registration_id), 0) AS DECIMAL),
    4
  ) AS activation_rate
FROM user_registrations AS r
JOIN user_activations AS a
  ON r.registration_id = a.registration_id
JOIN acquisition_channels AS c
  ON r.channel_id = c.channel_id
WHERE
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
```

### 53. GROWTH_OPS-075

**原问题：** 统计2026-05注册的用户数、其中最终激活的用户数，以及注册到激活率；请返回月份、注册用户数、激活用户数、激活率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

**业务审查：** 五月注册 cohort 总量与激活率；固定月份输出、两个激活标志判断和原注册ID分母不变。

- 输出列：`month`, `registrations`, `activated_users`, `activation_rate`。
- 物理来源：`user_activations`, `user_registrations`。
- 本题引用的物理字段类型：`user_activations.is_activated: bigint`、`user_activations.registration_id: text`、`user_registrations.registered_at: timestamp without time zone`、`user_registrations.registration_id: text`。
- 真假条件：`a.is_activated`（bigint）、`a.is_activated`（bigint）；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 1；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT '2026-05' AS month, COUNT(r.registration_id) AS registrations, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) AS activated_users, ROUND(SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/COUNT(r.registration_id),4) AS activation_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id WHERE strftime(r.registered_at,'%Y-%m')='2026-05'
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  '2026-05' AS month,
  COUNT(r.registration_id) AS registrations,
  SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) AS activated_users,
  ROUND(
    CAST(CAST(SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(r.registration_id) AS DECIMAL),
    4
  ) AS activation_rate
FROM user_registrations AS r
JOIN user_activations AS a
  ON r.registration_id = a.registration_id
WHERE
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-05'
```

### 54. GROWTH_OPS-076

**原问题：** 各渠道1日留存率排名；请返回渠道名称、观察用户数、留存率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从高到低展示。

**业务审查：** 1日留存按渠道聚合；留存标志非零为真，保持观测行数分母和留存率降序。

- 输出列：`channel_name`, `observed_users`, `retention_rate`。
- 物理来源：`acquisition_channels`, `user_retention`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`user_retention.channel_id: text`、`user_retention.is_retained: bigint`、`user_retention.retention_day: bigint`。
- 真假条件：`r.is_retained`（bigint）；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 1；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 3 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.channel_name, COUNT(*) AS observed_users, ROUND(SUM(CASE WHEN r.is_retained THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS retention_rate FROM user_retention r JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE r.retention_day=1 GROUP BY 1 ORDER BY 3 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.channel_name,
  COUNT(*) AS observed_users,
  ROUND(
    CAST(CAST(SUM(CASE WHEN r.is_retained <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS retention_rate
FROM user_retention AS r
JOIN acquisition_channels AS c
  ON r.channel_id = c.channel_id
WHERE
  r.retention_day = 1
GROUP BY
  1
ORDER BY
  3 DESC NULLS LAST,
  1
```

### 55. GROWTH_OPS-100

**原问题：** 统计2026-05期间注册平台为iOS的用户产生的播放总次数除以去重用户数；请返回注册平台、人均播放次数；聚合口径：去重数量按对应实体唯一标识计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

**业务审查：** 五月 iOS 人均播放数；分母保持 DISTINCT 活跃用户，JOIN 行数不能替代用户数。

- 输出列：`platform`, `plays_per_user`。
- 物理来源：`user_daily_activity`, `user_registrations`。
- 本题引用的物理字段类型：`user_daily_activity.activity_date: date`、`user_daily_activity.play_count: bigint`、`user_daily_activity.user_id: text`、`user_registrations.platform: text`、`user_registrations.user_id: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 1；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT 'iOS' AS platform, ROUND(SUM(a.play_count)*1.0/COUNT(DISTINCT a.user_id),2) AS plays_per_user FROM user_daily_activity a JOIN user_registrations r ON a.user_id=r.user_id WHERE r.platform='iOS' AND strftime(a.activity_date,'%Y-%m')='2026-05'
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  'iOS' AS platform,
  ROUND(
    CAST(CAST(SUM(a.play_count) * 1.0 AS DOUBLE PRECISION) / COUNT(DISTINCT a.user_id) AS DECIMAL),
    2
  ) AS plays_per_user
FROM user_daily_activity AS a
JOIN user_registrations AS r
  ON a.user_id = r.user_id
WHERE
  r.platform = 'iOS' AND TO_CHAR(a.activity_date, 'YYYY-MM') = '2026-05'
```

### 56. GROWTH_OPS-102

**原问题：** 用户按年龄段的分布；请返回年龄段、用户数；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 按原用户画像维度计数；人数降序、维度名次级排序。

- 输出列：`age_group`, `users`。
- 物理来源：`user_profiles`。
- 本题引用的物理字段类型：`user_profiles.age_group: text`、`user_profiles.user_id: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT age_group, COUNT(user_id) AS users FROM user_profiles GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  age_group,
  COUNT(user_id) AS users
FROM user_profiles
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 57. GROWTH_OPS-125

**原问题：** 按生命周期快照中的参与度评分，查询华中评分最高的前10名用户；请返回用户ID、参与度评分；按核心指标从高到低展示；最多返回10行。

**业务审查：** 原地区生命周期活跃度 Top 10；分数降序、用户ID次级排序和 LIMIT 10 不变。

- 输出列：`user_id`, `engagement_score`。
- 物理来源：`user_lifecycle_snapshots`, `user_profiles`。
- 本题引用的物理字段类型：`user_lifecycle_snapshots.engagement_score: double precision`、`user_lifecycle_snapshots.user_id: text`、`user_profiles.region: text`、`user_profiles.user_id: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY l.engagement_score DESC, l.user_id`；`LIMIT 10`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT l.user_id, l.engagement_score FROM user_lifecycle_snapshots l JOIN user_profiles p ON l.user_id=p.user_id WHERE p.region='华中' ORDER BY l.engagement_score DESC,l.user_id LIMIT 10
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  l.user_id,
  l.engagement_score
FROM user_lifecycle_snapshots AS l
JOIN user_profiles AS p
  ON l.user_id = p.user_id
WHERE
  p.region = '华中'
ORDER BY
  l.engagement_score DESC NULLS LAST,
  l.user_id
LIMIT 10
```

### 58. GROWTH_OPS-126

**原问题：** push触达方式的送达率、点击率和召回率；请返回触达方式、触达数量、送达率、点击率、召回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

**业务审查：** push 触达的送达/点击/召回率分别使用各自数值标志；保留 JOIN 后总行数分母与四位精度。

- 输出列：`touch_channel`, `touches`, `delivery_rate`, `click_rate`, `recall_rate`。
- 物理来源：`recall_results`, `recall_touches`。
- 本题引用的物理字段类型：`recall_results.recalled: bigint`、`recall_results.touch_id: text`、`recall_touches.clicked: bigint`、`recall_touches.delivered: bigint`、`recall_touches.touch_channel: text`、`recall_touches.touch_id: text`。
- 真假条件：`t.delivered`（bigint）、`t.clicked`（bigint）、`r.recalled`（bigint）；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 3；numeric ROUND 3；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT t.touch_channel, COUNT(*) AS touches, ROUND(SUM(CASE WHEN t.delivered THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS delivery_rate, ROUND(SUM(CASE WHEN t.clicked THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS click_rate, ROUND(SUM(CASE WHEN r.recalled THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS recall_rate FROM recall_touches t JOIN recall_results r ON t.touch_id=r.touch_id WHERE t.touch_channel='push' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  t.touch_channel,
  COUNT(*) AS touches,
  ROUND(
    CAST(CAST(SUM(CASE WHEN t.delivered <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS delivery_rate,
  ROUND(
    CAST(CAST(SUM(CASE WHEN t.clicked <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS click_rate,
  ROUND(
    CAST(CAST(SUM(CASE WHEN r.recalled <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS recall_rate
FROM recall_touches AS t
JOIN recall_results AS r
  ON t.touch_id = r.touch_id
WHERE
  t.touch_channel = 'push'
GROUP BY
  1
```

### 59. GROWTH_OPS-148

**原问题：** 2026-03各渠道激活率实际值与目标差距；请返回渠道名称、实际比率、激活率目标、目标差距；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

**业务审查：** 原注册月份 cohort 激活率与同月渠道目标比较；先用未舍入实际率减目标再舍入 gap，保留 gap 降序。

- 输出列：`channel_name`, `actual_rate`, `activation_rate_target`, `gap`。
- 物理来源：`acquisition_channels`, `growth_targets`, `user_activations`, `user_registrations`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`growth_targets.activation_rate_target: double precision`、`growth_targets.channel_id: text`、`growth_targets.target_month: text`、`user_activations.is_activated: bigint`、`user_activations.registration_id: text`、`user_registrations.channel_id: text`、`user_registrations.registered_at: timestamp without time zone`、`user_registrations.registration_id: text`。
- 真假条件：`a.is_activated`（bigint）；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 1；numeric ROUND 2；SUBSTRING 1；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY gap DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
WITH actual AS (SELECT r.channel_id, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/COUNT(*) AS actual_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id WHERE strftime(r.registered_at,'%Y-%m')='2026-03' GROUP BY 1) SELECT c.channel_name,ROUND(a.actual_rate,4) AS actual_rate,t.activation_rate_target, ROUND(a.actual_rate-t.activation_rate_target,4) AS gap FROM growth_targets t JOIN acquisition_channels c ON t.channel_id=c.channel_id JOIN actual a ON t.channel_id=a.channel_id WHERE substr(t.target_month,1,7)='2026-03' ORDER BY gap DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
WITH actual AS (
  SELECT
    r.channel_id,
    CAST(SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS actual_rate
  FROM user_registrations AS r
  JOIN user_activations AS a
    ON r.registration_id = a.registration_id
  WHERE
    TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-03'
  GROUP BY
    1
)
SELECT
  c.channel_name,
  ROUND(CAST(a.actual_rate AS DECIMAL), 4) AS actual_rate,
  t.activation_rate_target,
  ROUND(CAST(a.actual_rate - t.activation_rate_target AS DECIMAL), 4) AS gap
FROM growth_targets AS t
JOIN acquisition_channels AS c
  ON t.channel_id = c.channel_id
JOIN actual AS a
  ON t.channel_id = a.channel_id
WHERE
  SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-03'
ORDER BY
  gap DESC NULLS LAST,
  1
```

### 60. CHANNEL_OPS-006

**原问题：** 信息流广告2026年各月广告消耗；请返回月份、广告消耗；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

**业务审查：** 原指定渠道按月汇总花费；保持广告统计到计划到渠道的 JOIN 和月份升序。

- 输出列：`month`, `spend`。
- 物理来源：`acquisition_channels`, `ad_campaigns`, `ad_daily_stats`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`ad_campaigns.ad_campaign_id: text`、`ad_campaigns.channel_id: text`、`ad_daily_stats.ad_campaign_id: text`、`ad_daily_stats.spend: double precision`、`ad_daily_stats.stat_date: date`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT strftime(s.stat_date,'%Y-%m') AS month,ROUND(SUM(s.spend),2) spend FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='信息流广告' GROUP BY 1 ORDER BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  TO_CHAR(s.stat_date, 'YYYY-MM') AS month,
  ROUND(CAST(SUM(s.spend) AS DECIMAL), 2) AS spend
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  c.channel_name = '信息流广告'
GROUP BY
  1
ORDER BY
  1
```

### 61. CHANNEL_OPS-025

**原问题：** 截至2026-05各月广告消耗及环比变化；请返回月份、广告消耗、环比变化率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按时间升序展示。

**业务审查：** 原截至五月的月花费与环比；不增加起始月，LAG 使用未舍入花费，首月为 NULL、零上月值由 NULLIF 保护。

- 输出列：`month`, `spend`, `mom`。
- 物理来源：`ad_daily_stats`。
- 本题引用的物理字段类型：`ad_daily_stats.spend: double precision`、`ad_daily_stats.stat_date: date`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 2；浮点除法 1；numeric ROUND 2；SUBSTRING 0；NULLIF 1（保留）。
- 原排序/限制：`ORDER BY month；ORDER BY month；ORDER BY month`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
WITH m AS (SELECT strftime(stat_date,'%Y-%m') AS month,SUM(spend) spend FROM ad_daily_stats WHERE strftime(stat_date,'%Y-%m')<='2026-05' GROUP BY 1) SELECT month,ROUND(spend,2) spend,ROUND((spend-LAG(spend) OVER(ORDER BY month))/NULLIF(LAG(spend) OVER(ORDER BY month),0),4) mom FROM m ORDER BY month
```

**正式 PostgreSQL Gold SQL**

```sql
WITH m AS (
  SELECT
    TO_CHAR(stat_date, 'YYYY-MM') AS month,
    SUM(spend) AS spend
  FROM ad_daily_stats
  WHERE
    TO_CHAR(stat_date, 'YYYY-MM') <= '2026-05'
  GROUP BY
    1
)
SELECT
  month,
  ROUND(CAST(spend AS DECIMAL), 2) AS spend,
  ROUND(
    CAST(CAST((
      spend - LAG(spend) OVER (ORDER BY month)
    ) AS DOUBLE PRECISION) / NULLIF(LAG(spend) OVER (ORDER BY month), 0) AS DECIMAL),
    4
  ) AS mom
FROM m
ORDER BY
  month
```

### 62. CHANNEL_OPS-026

**原问题：** 2026-01各渠道曝光、点击和点击率；请返回渠道名称、曝光量、点击数、点击率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

**业务审查：** 一月渠道 CTR；点击总和/曝光总和，保留 NULLIF、四位精度和 CTR 降序。

- 输出列：`channel_name`, `impressions`, `clicks`, `ctr`。
- 物理来源：`acquisition_channels`, `ad_campaigns`, `ad_daily_stats`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`ad_campaigns.ad_campaign_id: text`、`ad_campaigns.channel_id: text`、`ad_daily_stats.ad_campaign_id: text`、`ad_daily_stats.clicks: bigint`、`ad_daily_stats.impressions: bigint`、`ad_daily_stats.stat_date: date`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 1；numeric ROUND 1；SUBSTRING 0；NULLIF 1（保留）。
- 原排序/限制：`ORDER BY 4 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.channel_name,SUM(s.impressions) impressions,SUM(s.clicks) clicks, ROUND(SUM(s.clicks)*1.0/NULLIF(SUM(s.impressions),0),4) ctr FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE strftime(s.stat_date,'%Y-%m')='2026-01' GROUP BY 1 ORDER BY 4 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.channel_name,
  SUM(s.impressions) AS impressions,
  SUM(s.clicks) AS clicks,
  ROUND(
    CAST(CAST(SUM(s.clicks) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(s.impressions), 0) AS DECIMAL),
    4
  ) AS ctr
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
```

### 63. CHANNEL_OPS-050

**原问题：** 请汇总信息流广告的平均点击成本；请返回渠道名称、平均点击成本；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

**业务审查：** 原指定渠道 CPC；花费总和/点击总和，保留 NULLIF 和四位精度。

- 输出列：`channel_name`, `cpc`。
- 物理来源：`acquisition_channels`, `ad_campaigns`, `ad_daily_stats`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`ad_campaigns.ad_campaign_id: text`、`ad_campaigns.channel_id: text`、`ad_daily_stats.ad_campaign_id: text`、`ad_daily_stats.clicks: bigint`、`ad_daily_stats.spend: double precision`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 1；numeric ROUND 1；SUBSTRING 0；NULLIF 1（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.channel_name,ROUND(SUM(s.spend)/NULLIF(SUM(s.clicks),0),4) cpc FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='信息流广告' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.channel_name,
  ROUND(
    CAST(CAST(SUM(s.spend) AS DOUBLE PRECISION) / NULLIF(SUM(s.clicks), 0) AS DECIMAL),
    4
  ) AS cpc
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  c.channel_name = '信息流广告'
GROUP BY
  1
```

### 64. CHANNEL_OPS-051

**原问题：** 2026-01各渠道转化数、转化率和CPA；请返回渠道名称、转化数、转化率、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

**业务审查：** 一月转化数、转化率及 CPA；各分母、NULLIF 与四/两位精度不变，按 CPA 升序。

- 输出列：`channel_name`, `conversions`, `conversion_rate`, `cpa`。
- 物理来源：`acquisition_channels`, `ad_campaigns`, `ad_daily_stats`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`ad_campaigns.ad_campaign_id: text`、`ad_campaigns.channel_id: text`、`ad_daily_stats.ad_campaign_id: text`、`ad_daily_stats.clicks: bigint`、`ad_daily_stats.conversions: bigint`、`ad_daily_stats.spend: double precision`、`ad_daily_stats.stat_date: date`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 2；numeric ROUND 2；SUBSTRING 0；NULLIF 2（保留）。
- 原排序/限制：`ORDER BY 4, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.channel_name,SUM(s.conversions) conversions, ROUND(SUM(s.conversions)*1.0/NULLIF(SUM(s.clicks),0),4) conversion_rate, ROUND(SUM(s.spend)/NULLIF(SUM(s.conversions),0),2) cpa FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE strftime(s.stat_date,'%Y-%m')='2026-01' GROUP BY 1 ORDER BY 4,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.channel_name,
  SUM(s.conversions) AS conversions,
  ROUND(
    CAST(CAST(SUM(s.conversions) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(s.clicks), 0) AS DECIMAL),
    4
  ) AS conversion_rate,
  ROUND(
    CAST(CAST(SUM(s.spend) AS DOUBLE PRECISION) / NULLIF(SUM(s.conversions), 0) AS DECIMAL),
    2
  ) AS cpa
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  4,
  1
```

### 65. CHANNEL_OPS-080

**原问题：** 请分析统计active状态广告计划的数量和预算；请返回状态、广告计划数、预算；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和。

**业务审查：** 原广告计划状态条件下的计划ID计数、预算总和；先求和再舍入。

- 输出列：`status`, `campaigns`, `budget`。
- 物理来源：`ad_campaigns`。
- 本题引用的物理字段类型：`ad_campaigns.ad_campaign_id: text`、`ad_campaigns.budget: bigint`、`ad_campaigns.status: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT status,COUNT(ad_campaign_id) campaigns,ROUND(SUM(budget),2) budget FROM ad_campaigns WHERE status='active' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  status,
  COUNT(ad_campaign_id) AS campaigns,
  ROUND(CAST(SUM(budget) AS DECIMAL), 2) AS budget
FROM ad_campaigns
WHERE
  status = 'active'
GROUP BY
  1
```

### 66. CHANNEL_OPS-100

**原问题：** 请汇总预算调整原因为转化成本偏高的调整次数和平均幅度；请返回调整原因、调整次数、平均调整幅度；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

**业务审查：** 原预算调整原因下的平均差额；先算每行新旧预算之差，再求平均及舍入。

- 输出列：`adjustment_reason`, `adjustments`, `avg_change`。
- 物理来源：`budget_adjustments`。
- 本题引用的物理字段类型：`budget_adjustments.adjustment_reason: text`、`budget_adjustments.new_budget: bigint`、`budget_adjustments.previous_budget: bigint`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT adjustment_reason,COUNT(*) adjustments, ROUND(AVG(new_budget-previous_budget),2) avg_change FROM budget_adjustments WHERE adjustment_reason='转化成本偏高' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  adjustment_reason,
  COUNT(*) AS adjustments,
  ROUND(CAST(AVG(new_budget - previous_budget) AS DECIMAL), 2) AS avg_change
FROM budget_adjustments
WHERE
  adjustment_reason = '转化成本偏高'
GROUP BY
  1
```

### 67. CHANNEL_OPS-102

**原问题：** 图文创意的状态分布；请返回创意状态、创意数量；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 原素材类型按状态计数；保留素材ID计数、数量降序和状态次级排序。

- 输出列：`creative_status`, `creatives`。
- 物理来源：`ad_creatives`。
- 本题引用的物理字段类型：`ad_creatives.creative_id: text`、`ad_creatives.creative_status: text`、`ad_creatives.creative_type: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT creative_status,COUNT(creative_id) creatives FROM ad_creatives WHERE creative_type='图文' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  creative_status,
  COUNT(creative_id) AS creatives
FROM ad_creatives
WHERE
  creative_type = '图文'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 68. CHANNEL_OPS-126

**原问题：** last_click归因按渠道的用户数和平均置信度；请返回渠道名称、用户数、平均置信度；聚合口径：去重数量按对应实体唯一标识计数，平均指标取算术平均。

**业务审查：** 原 last_click 归因；DISTINCT 用户数和平均置信度分开计算，保持渠道分组与排序。

- 输出列：`channel_name`, `users`, `avg_confidence`。
- 物理来源：`acquisition_channels`, `channel_attributions`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`channel_attributions.attribution_type: text`、`channel_attributions.channel_id: text`、`channel_attributions.confidence_score: double precision`、`channel_attributions.user_id: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.channel_name,COUNT(DISTINCT a.user_id) users,ROUND(AVG(a.confidence_score),4) avg_confidence FROM channel_attributions a JOIN acquisition_channels c ON a.channel_id=c.channel_id WHERE a.attribution_type='last_click' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.channel_name,
  COUNT(DISTINCT a.user_id) AS users,
  ROUND(CAST(AVG(a.confidence_score) AS DECIMAL), 4) AS avg_confidence
FROM channel_attributions AS a
JOIN acquisition_channels AS c
  ON a.channel_id = c.channel_id
WHERE
  a.attribution_type = 'last_click'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 69. CHANNEL_OPS-136

**原问题：** 2026-01各渠道实际CPA与目标CPA差距；请返回渠道名称、实际CPA、目标CPA、目标差距；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

**业务审查：** 一月渠道 CPA 与一月目标比较；先用未舍入 CPA 减目标再舍入 gap，保留 NULLIF 与 gap 升序、NULL末尾。

- 输出列：`channel_name`, `actual_cpa`, `target_cpa`, `gap`。
- 物理来源：`acquisition_channels`, `ad_campaigns`, `ad_daily_stats`, `channel_targets`。
- 本题引用的物理字段类型：`acquisition_channels.channel_id: text`、`acquisition_channels.channel_name: text`、`ad_campaigns.ad_campaign_id: text`、`ad_campaigns.channel_id: text`、`ad_daily_stats.ad_campaign_id: text`、`ad_daily_stats.conversions: bigint`、`ad_daily_stats.spend: double precision`、`ad_daily_stats.stat_date: date`、`channel_targets.channel_id: text`、`channel_targets.target_cpa: double precision`、`channel_targets.target_month: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 1；numeric ROUND 2；SUBSTRING 1；NULLIF 1（保留）。
- 原排序/限制：`ORDER BY gap, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
WITH actual AS (SELECT p.channel_id,SUM(s.spend)/NULLIF(SUM(s.conversions),0) cpa FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id WHERE strftime(s.stat_date,'%Y-%m')='2026-01' GROUP BY 1) SELECT c.channel_name,ROUND(a.cpa,2) actual_cpa,t.target_cpa,ROUND(a.cpa-t.target_cpa,2) gap FROM channel_targets t JOIN acquisition_channels c ON t.channel_id=c.channel_id JOIN actual a ON t.channel_id=a.channel_id WHERE substr(t.target_month,1,7)='2026-01' ORDER BY gap,1
```

**正式 PostgreSQL Gold SQL**

```sql
WITH actual AS (
  SELECT
    p.channel_id,
    CAST(SUM(s.spend) AS DOUBLE PRECISION) / NULLIF(SUM(s.conversions), 0) AS cpa
  FROM ad_daily_stats AS s
  JOIN ad_campaigns AS p
    ON s.ad_campaign_id = p.ad_campaign_id
  WHERE
    TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-01'
  GROUP BY
    1
)
SELECT
  c.channel_name,
  ROUND(CAST(a.cpa AS DECIMAL), 2) AS actual_cpa,
  t.target_cpa,
  ROUND(CAST(a.cpa - t.target_cpa AS DECIMAL), 2) AS gap
FROM channel_targets AS t
JOIN acquisition_channels AS c
  ON t.channel_id = c.channel_id
JOIN actual AS a
  ON t.channel_id = a.channel_id
WHERE
  SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-01'
ORDER BY
  gap,
  1
```

### 70. CONTENT_OPS-002

**原问题：** 2026-02每天的视频曝光量和播放量；请返回指标日期、曝光量、播放量；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

**业务审查：** 原月份按日汇总曝光与播放；日期粒度及升序不变。

- 输出列：`metric_date`, `impressions`, `plays`。
- 物理来源：`content_daily_metrics`。
- 本题引用的物理字段类型：`content_daily_metrics.impressions: bigint`、`content_daily_metrics.metric_date: date`、`content_daily_metrics.play_count: bigint`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT metric_date,SUM(impressions) impressions,SUM(play_count) plays FROM content_daily_metrics WHERE strftime(metric_date,'%Y-%m')='2026-02' GROUP BY 1 ORDER BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  metric_date,
  SUM(impressions) AS impressions,
  SUM(play_count) AS plays
FROM content_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  1
```

### 71. CONTENT_OPS-025

**原问题：** 体育类播放量最高的前10条内容；请返回内容标题、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

**业务审查：** 体育标题播放总和 Top 10；保留标题次级排序、既有边界值8及全部已批准并列候选。

- 输出列：`content_title`, `plays`。
- 物理来源：`content_categories`, `content_daily_metrics`, `contents`。
- 本题引用的物理字段类型：`content_categories.category_id: text`、`content_categories.category_name: text`、`content_daily_metrics.content_id: text`、`content_daily_metrics.play_count: bigint`、`contents.category_id: text`、`contents.content_id: text`、`contents.content_title: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`LIMIT 10`；所有排序 NULL 在末尾。
- 并列规则：保持既有 limit=10、boundary_value=8 与 12 项边界候选；完整候选见正式题集。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.content_title,SUM(m.play_count) plays FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='体育' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.content_title,
  SUM(m.play_count) AS plays
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '体育'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

### 72. CONTENT_OPS-026

**原问题：** 基于播放明细，计算搞笑类内容每次播放的平均观看时长和平均完播率；请返回内容分类、平均观看时长、平均完播率；聚合口径：平均指标取算术平均。

**业务审查：** 原分类播放样本的平均观看秒数和完播率；保留普通 AVG、原 JOIN 及两/四位精度。

- 输出列：`category_name`, `avg_watch_seconds`, `avg_completion_rate`。
- 物理来源：`content_categories`, `contents`, `video_plays`。
- 本题引用的物理字段类型：`content_categories.category_id: text`、`content_categories.category_name: text`、`contents.category_id: text`、`contents.content_id: text`、`video_plays.completion_rate: double precision`、`video_plays.content_id: text`、`video_plays.watch_seconds: bigint`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 2；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT cat.category_name,ROUND(AVG(p.watch_seconds),2) avg_watch_seconds, ROUND(AVG(p.completion_rate),4) avg_completion_rate FROM video_plays p JOIN contents c ON p.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='搞笑' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  cat.category_name,
  ROUND(CAST(AVG(p.watch_seconds) AS DECIMAL), 2) AS avg_watch_seconds,
  ROUND(CAST(AVG(p.completion_rate) AS DECIMAL), 4) AS avg_completion_rate
FROM video_plays AS p
JOIN contents AS c
  ON p.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '搞笑'
GROUP BY
  1
```

### 73. CONTENT_OPS-050

**原问题：** 2026-05平均完播率最高的前10条内容；请返回内容标题、完播率；聚合口径：平均指标取算术平均；按核心指标从高到低展示；最多返回10行。

**业务审查：** 五月标题平均每日完播率 Top 10；保持先舍入再排序的原口径、标题次级排序与 LIMIT 10。

- 输出列：`content_title`, `completion_rate`。
- 物理来源：`content_daily_metrics`, `contents`。
- 本题引用的物理字段类型：`content_daily_metrics.completion_rate: double precision`、`content_daily_metrics.content_id: text`、`content_daily_metrics.metric_date: date`、`contents.content_id: text`、`contents.content_title: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`LIMIT 10`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.content_title,ROUND(AVG(m.completion_rate),4) completion_rate FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id WHERE strftime(m.metric_date,'%Y-%m')='2026-05' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.content_title,
  ROUND(CAST(AVG(m.completion_rate) AS DECIMAL), 4) AS completion_rate
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

### 74. CONTENT_OPS-052

**原问题：** 生活类内容数量和平均视频时长；请返回内容分类、内容数量、平均视频时长；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

**业务审查：** 原分类内容量和平均时长；保持内容ID计数、普通 AVG 和两位精度。

- 输出列：`category_name`, `contents`, `avg_duration_seconds`。
- 物理来源：`content_categories`, `contents`。
- 本题引用的物理字段类型：`content_categories.category_id: text`、`content_categories.category_name: text`、`contents.category_id: text`、`contents.content_id: text`、`contents.duration_seconds: bigint`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT cat.category_name,COUNT(c.content_id) contents,ROUND(AVG(c.duration_seconds),2) avg_duration_seconds FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='生活' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  cat.category_name,
  COUNT(c.content_id) AS contents,
  ROUND(CAST(AVG(c.duration_seconds) AS DECIMAL), 2) AS avg_duration_seconds
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '生活'
GROUP BY
  1
```

### 75. CONTENT_OPS-077

**原问题：** 成长级创作者数量和状态分布；请返回创作者状态、创作者数量；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 原创作者等级按状态计数；创作者ID口径、数量降序及状态排序不变。

- 输出列：`creator_status`, `creators`。
- 物理来源：`creators`。
- 本题引用的物理字段类型：`creators.creator_id: text`、`creators.creator_level: text`、`creators.creator_status: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT creator_status,COUNT(creator_id) creators FROM creators WHERE creator_level='成长' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  creator_status,
  COUNT(creator_id) AS creators
FROM creators
WHERE
  creator_level = '成长'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 76. CONTENT_OPS-100

**原问题：** 请汇总查询2026年8月新星级创作者的每日互动率算术平均值前10名；请返回创作者名称、互动率；聚合口径：平均指标取算术平均；按核心指标从高到低展示；最多返回10行。

**业务审查：** 八月新星创作者平均互动率 Top 10；保持原等级筛选、名称分组和排序。

- 输出列：`creator_name`, `interaction_rate`。
- 物理来源：`creator_daily_metrics`, `creators`。
- 本题引用的物理字段类型：`creator_daily_metrics.creator_id: text`、`creator_daily_metrics.interaction_rate: double precision`、`creator_daily_metrics.metric_date: date`、`creators.creator_id: text`、`creators.creator_level: text`、`creators.creator_name: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 1；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`LIMIT 10`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT c.creator_name,ROUND(AVG(m.interaction_rate),4) interaction_rate FROM creator_daily_metrics m JOIN creators c ON m.creator_id=c.creator_id WHERE strftime(m.metric_date,'%Y-%m')='2026-08' AND c.creator_level='新星' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  c.creator_name,
  ROUND(CAST(AVG(m.interaction_rate) AS DECIMAL), 4) AS interaction_rate
FROM creator_daily_metrics AS m
JOIN creators AS c
  ON m.creator_id = c.creator_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '新星'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

### 77. CONTENT_OPS-101

**原问题：** content类型内容标签的使用次数；请返回标签名称、使用次数；聚合口径：数量指标按对应业务记录计数。

**业务审查：** 原内容标签类型使用次数；保留关联内容ID计数，不添加 DISTINCT。

- 输出列：`tag_name`, `uses`。
- 物理来源：`content_tag_relations`, `content_tags`。
- 本题引用的物理字段类型：`content_tag_relations.content_id: text`、`content_tag_relations.content_tag_id: text`、`content_tags.content_tag_id: text`、`content_tags.tag_name: text`、`content_tags.tag_type: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 0；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`ORDER BY 2 DESC, 1`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT t.tag_name,COUNT(r.content_id) uses FROM content_tags t JOIN content_tag_relations r ON t.content_tag_id=r.content_tag_id WHERE t.tag_type='content' GROUP BY 1 ORDER BY 2 DESC,1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  t.tag_name,
  COUNT(r.content_id) AS uses
FROM content_tags AS t
JOIN content_tag_relations AS r
  ON t.content_tag_id = r.content_tag_id
WHERE
  t.tag_type = 'content'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

### 78. CONTENT_OPS-125

**原问题：** 流量加热系数至少3.0的热点内容数量和平均排名；请返回最低流量加热系数、内容数量、平均排名；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均；按核心指标从高到低展示。

**业务审查：** 原 traffic_boost 下限、固定阈值输出、内容ID计数与平均 ranking 保持一致。

- 输出列：`min_traffic_boost`, `contents`, `avg_ranking`。
- 物理来源：`topic_content_relations`。
- 本题引用的物理字段类型：`topic_content_relations.content_id: text`、`topic_content_relations.ranking: bigint`、`topic_content_relations.traffic_boost: double precision`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 0；numeric ROUND 1；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT 3.0 min_traffic_boost,COUNT(content_id) contents,ROUND(AVG(ranking),2) avg_ranking FROM topic_content_relations WHERE traffic_boost>=3.0
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  3.0 AS min_traffic_boost,
  COUNT(content_id) AS contents,
  ROUND(CAST(AVG(ranking) AS DECIMAL), 2) AS avg_ranking
FROM topic_content_relations
WHERE
  traffic_boost >= 3.0
```

### 79. CONTENT_OPS-150

**原问题：** 请汇总human审核方式的通过率和驳回率；请返回审核方式、审核数量、通过率、驳回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

**业务审查：** human 审核的通过/拒绝率；分母保留全部审核行，包括其他状态，两个字符串状态判断保持原值。

- 输出列：`review_mode`, `audits`, `approval_rate`, `rejection_rate`。
- 物理来源：`content_audits`。
- 本题引用的物理字段类型：`content_audits.audit_status: text`、`content_audits.review_mode: text`。
- 真假条件：无数值真假判断；非零判断保持原 NULL 语义。
- 方言变化：月份格式 0；浮点除法 2；numeric ROUND 2；SUBSTRING 0；NULLIF 0（保留）。
- 原排序/限制：`原SQL无排序要求`；`无 LIMIT`；所有排序 NULL 在末尾。
- 并列规则：无新增并列宽容。
- 状态：离线字段/只读/应用权限/语义形状审查通过；PostgreSQL 实际执行待验收。

**原 DuckDB Gold SQL**

```sql
SELECT review_mode,COUNT(*) audits, ROUND(SUM(CASE WHEN audit_status='approved' THEN 1 ELSE 0 END)*1.0/COUNT(*),4) approval_rate, ROUND(SUM(CASE WHEN audit_status='rejected' THEN 1 ELSE 0 END)*1.0/COUNT(*),4) rejection_rate FROM content_audits WHERE review_mode='human' GROUP BY 1
```

**正式 PostgreSQL Gold SQL**

```sql
SELECT
  review_mode,
  COUNT(*) AS audits,
  ROUND(
    CAST(CAST(SUM(CASE WHEN audit_status = 'approved' THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS approval_rate,
  ROUND(
    CAST(CAST(SUM(CASE WHEN audit_status = 'rejected' THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS rejection_rate
FROM content_audits
WHERE
  review_mode = 'human'
GROUP BY
  1
```
