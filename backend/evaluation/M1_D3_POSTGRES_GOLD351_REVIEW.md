# M1 D3：剩余351题 PostgreSQL Gold 逐题审查

2026-10-12。以下为逐题离线结构、类型和语义核对记录；真实 PostgreSQL 执行待服务器验收。原 DuckDB SQL、预期结果、别名、排序及已批准并列策略不变。

新增范围：增长118、渠道114、内容119。正式430题全部保存显式变体。首批79题不在此重新生成，原审查记录和行字节保留。

仅采用已验证的月份格式、整数非零真假、浮点除法、numeric舍入及NULL排序转换。完整机器记录：`cases/m1_d3_postgres_gold351_review.json`；服务器验收命令：`M1_D3_POSTGRES_GOLD430_ACCEPTANCE.md`。

## GROWTH_OPS-008

查看2026-01每天的次日留存用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-01'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(day1_retained_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-01' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(day1_retained_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `beda999bd78fe6d5d6a69bde08649286278db6b586641e23fcbe22f07748e387`

PostgreSQL SQL SHA256: `c38d33a479a7052369737f16c5ad87e9432d991d671f130dd183e853b350a9b2`

## GROWTH_OPS-009

查看2026-01每天的七日留存用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-01'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(day7_retained_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-01' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(day7_retained_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `269a206fef698bd4b2a76fb847763ca7c62aa8dcb56b5fcb6adc0dbd2edf6ae2`

PostgreSQL SQL SHA256: `c091213cabc1cb51f2205d2edc1aa1f906f946884383b6822c5014f2064ad0cb`

## GROWTH_OPS-010

查看2026-01每天的日活用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-01'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(daily_active_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-01' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(daily_active_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `1c0a7c7abe19fb8881288c3d71ac82e746d505d074499ff46802b308e27eacc3`

PostgreSQL SQL SHA256: `8dd0759636f1f0574faecddb3ccbfe12fe2e586b52e3e3698e5fc118566d60b0`

## GROWTH_OPS-011

查看2026-02每天的新增用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-02'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(new_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-02' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(new_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `69404bcf194f76619d5b7a2f30ad109aba4ad7889777fdad123ee258db0271cc`

PostgreSQL SQL SHA256: `5cd7e2ebe2f88cc145d91487f57ba20acf0f153fff73450eb73b60a2d094a8eb`

## GROWTH_OPS-012

查看2026-02每天的激活用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-02'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(activated_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-02' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(activated_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `1478796afbd4e637f593a534972608965bc62703ecdff75fbfa4772dc8ee6de7`

PostgreSQL SQL SHA256: `5b6c7f7894caf3719f946c3d52224350f10bc0c45e441e5464927f380e3bb9c8`

## GROWTH_OPS-013

查看2026-02每天的次日留存用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-02'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(day1_retained_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-02' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(day1_retained_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `b5bd5dc53f2a54f402bb2fd33f85579800aed8d58e1d4cb71f5377efa0c383bf`

PostgreSQL SQL SHA256: `e13b759664517dbd4adcbd790389156b36259555a8affc3ddf6881c06bd03d8a`

## GROWTH_OPS-014

查看2026-02每天的七日留存用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-02'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(day7_retained_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-02' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(day7_retained_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `c55fdbbfc9e5b351bce5fc77fdaaaaaa1604bbe4edf6fc66de1bd67049dff4a5`

PostgreSQL SQL SHA256: `66acc10cf1684a32aec4fed8eaabb6f31265bfac1621f8821cbf722971615ca8`

## GROWTH_OPS-015

查看2026-02每天的日活用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-02'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(daily_active_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-02' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(daily_active_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `9121a2ea557a5628ec220acb295c330125db99efba90c899d07f8f10b4b4135b`

PostgreSQL SQL SHA256: `f3581aaffe68d5e6f97fb72f7d5adcbbfa1e1c00bf534efbbd7c6c769cf6f4fc`

## GROWTH_OPS-016

查看2026-03每天的新增用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-03'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(new_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-03' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(new_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `a8c095abfcdf32b7059b006c01f1a546fca1d529aed526f9dbbcaed4e5871283`

PostgreSQL SQL SHA256: `e46b827de572b9b77c290e7c3b4cc7fd5c8f4a169b6b542fa1e118e899904441`

## GROWTH_OPS-017

查看2026-03每天的激活用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-03'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(activated_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-03' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(activated_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `05d47c981b3bb208d93fcf7e8edf41fa4c4cfbf4de29d0964874c36b64c6d130`

PostgreSQL SQL SHA256: `2ade57031013d414b7d6a5ee2059bb57557cc30bbf5a775804e2a86cd7f5d318`

## GROWTH_OPS-018

查看2026-03每天的次日留存用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-03'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(day1_retained_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-03' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(day1_retained_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `42e2e89835f59572e380c33d504712ec8ef7efe1611448e2207e0f5d0aeabe93`

PostgreSQL SQL SHA256: `5e5efada53e3b2f4aec9bad67f07305acb92c9fbcc3cf3ec55025d215406adf6`

## GROWTH_OPS-019

查看2026-03每天的七日留存用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-03'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(day7_retained_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-03' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(day7_retained_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `e65211a76a7a7d64991e9b119dfe084b6f26d090b02065c2790fa83ddb80293c`

PostgreSQL SQL SHA256: `821e4796dece51b0927031db2da2a9768e5f9616a27c62a9226fea5aae83ad18`

## GROWTH_OPS-020

查看2026-03每天的日活用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-03'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(daily_active_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-03' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(daily_active_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `dfdaa16f37a5f8152720c91fb7f99efe0a501671705462e5b3a4bc1f82ff1b2c`

PostgreSQL SQL SHA256: `6d80cce80f03815c50f4576bbf36247d7bbc7301e657d2c4e27cb46e68c30295`

## GROWTH_OPS-021

查看2026-04每天的新增用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-04'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(new_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-04' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(new_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `f24ce4032faa72abb1e6ff34c79c9ec2647e2e647ab6c2619ea21e361a67c979`

PostgreSQL SQL SHA256: `63ff7f919341aba90bda3b3d9b8119eb5d9c96a2bd36e5514995a48335a3aec4`

## GROWTH_OPS-022

查看2026-04每天的激活用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-04'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(activated_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-04' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(activated_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `9f4682f7d5b5392008d221d6824f9da79799a06613aedeac13bb011bbe158c68`

PostgreSQL SQL SHA256: `2d18172031536979c896624c83679e222457b78f0a89bc58b899aaaa924ce1d5`

## GROWTH_OPS-023

查看2026-04每天的次日留存用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-04'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(day1_retained_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-04' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(day1_retained_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `ad6371273a5ccd029e58dbd76320ce4201a4d662d6829f2a01d6008bde66aaa7`

PostgreSQL SQL SHA256: `a1deb871fb179a14de5fb813905b7de46f184ba7603d6667b0c51b523e6c2411`

## GROWTH_OPS-024

查看2026-04每天的七日留存用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-04'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(day7_retained_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-04' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(day7_retained_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `24c0ab4b5efc18054b136ed1f5671f2db0fc2a6f28566e1dbfe23e3f0742ac53`

PostgreSQL SQL SHA256: `dd6c24aa48bb1779bdbd3b1c1558d815a27196133d558eb1c2158103d00a85a7`

## GROWTH_OPS-025

查看2026-04每天的日活用户数变化；请返回指标日期、指标值；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, value. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-04'.

Output: `metric_date, value`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date, SUM(daily_active_users) AS value FROM growth_daily_metrics WHERE strftime(metric_date, '%Y-%m') = '2026-04' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(daily_active_users) AS value
FROM growth_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `69c37450d9f47dde0765deeb365a1f0d41e388568869b01f4965291c826b9e17`

PostgreSQL SQL SHA256: `f68783ff24f865b5123cbd6660764d0c2906f983e82ef6bbbd44190533cc0eaa`

## GROWTH_OPS-027

2026-02各获客渠道新增用户数排名；请返回渠道名称、新增用户数；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, new_users. Filters: WHERE TO_CHAR(g.metric_date, 'YYYY-MM') = '2026-02'.

Output: `channel_name, new_users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, SUM(g.new_users) AS new_users FROM growth_daily_metrics g JOIN acquisition_channels c ON g.channel_id=c.channel_id WHERE strftime(g.metric_date, '%Y-%m')='2026-02' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  SUM(g.new_users) AS new_users
FROM growth_daily_metrics AS g
JOIN acquisition_channels AS c
  ON g.channel_id = c.channel_id
WHERE
  TO_CHAR(g.metric_date, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `859b52f65c02f90c610b09b6561f4879b056519bbc24dcd7cc3dec5fe9956467`

PostgreSQL SQL SHA256: `65b6b2717c5990e46543c03981534939dbe357ac882a7e113f1565976e547a93`

## GROWTH_OPS-028

2026-03各获客渠道新增用户数排名；请返回渠道名称、新增用户数；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, new_users. Filters: WHERE TO_CHAR(g.metric_date, 'YYYY-MM') = '2026-03'.

Output: `channel_name, new_users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, SUM(g.new_users) AS new_users FROM growth_daily_metrics g JOIN acquisition_channels c ON g.channel_id=c.channel_id WHERE strftime(g.metric_date, '%Y-%m')='2026-03' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  SUM(g.new_users) AS new_users
FROM growth_daily_metrics AS g
JOIN acquisition_channels AS c
  ON g.channel_id = c.channel_id
WHERE
  TO_CHAR(g.metric_date, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `6dfae54f5a9a9ed38d38ef7db6e5fe9cbf72d9025e2e61560a8a1a0db6036d43`

PostgreSQL SQL SHA256: `19421f8465f45f8229e933ed54f84b9c9348852bdd24aa81a6057243e5310c91`

## GROWTH_OPS-029

2026-04各获客渠道新增用户数排名；请返回渠道名称、新增用户数；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, new_users. Filters: WHERE TO_CHAR(g.metric_date, 'YYYY-MM') = '2026-04'.

Output: `channel_name, new_users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, SUM(g.new_users) AS new_users FROM growth_daily_metrics g JOIN acquisition_channels c ON g.channel_id=c.channel_id WHERE strftime(g.metric_date, '%Y-%m')='2026-04' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  SUM(g.new_users) AS new_users
FROM growth_daily_metrics AS g
JOIN acquisition_channels AS c
  ON g.channel_id = c.channel_id
WHERE
  TO_CHAR(g.metric_date, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `3256e983e2742955a55cc5b9438eb4363342975eb5480183acfa89542d2e2e5c`

PostgreSQL SQL SHA256: `9de92ba79274bbcb1562a1a31679b714df10de97f81791cc281ffb85d527ba8a`

## GROWTH_OPS-030

2026-05各获客渠道新增用户数排名；请返回渠道名称、新增用户数；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, new_users. Filters: WHERE TO_CHAR(g.metric_date, 'YYYY-MM') = '2026-05'.

Output: `channel_name, new_users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, SUM(g.new_users) AS new_users FROM growth_daily_metrics g JOIN acquisition_channels c ON g.channel_id=c.channel_id WHERE strftime(g.metric_date, '%Y-%m')='2026-05' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  SUM(g.new_users) AS new_users
FROM growth_daily_metrics AS g
JOIN acquisition_channels AS c
  ON g.channel_id = c.channel_id
WHERE
  TO_CHAR(g.metric_date, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `8ace915541ee8b63b5d3565f475b1aa2c6023726616bb7f0f7be68a76ab1abb6`

PostgreSQL SQL SHA256: `7a3c6aef32625f60218eaa079275a4b27b4224c93df6c6f476e6fae53d06cc8a`

## GROWTH_OPS-031

自然推荐渠道2026年各月拉新人数；请返回月份、新增用户数；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, new_users. Filters: WHERE c.channel_name = '自然推荐'.

Output: `month, new_users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT strftime(g.metric_date,'%Y-%m') AS month, SUM(g.new_users) AS new_users FROM growth_daily_metrics g JOIN acquisition_channels c ON g.channel_id=c.channel_id WHERE c.channel_name='自然推荐' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  TO_CHAR(g.metric_date, 'YYYY-MM') AS month,
  SUM(g.new_users) AS new_users
FROM growth_daily_metrics AS g
JOIN acquisition_channels AS c
  ON g.channel_id = c.channel_id
WHERE
  c.channel_name = '自然推荐'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `3ba8cf632af2de100417a9101c6fe98c7054444061e4a5ceba7f9fa28c1e3633`

PostgreSQL SQL SHA256: `f1d79a1481e60f58f6fe6cf36a54bd10a3d197d601171761633d81da4b262257`

## GROWTH_OPS-032

应用商店渠道2026年各月拉新人数；请返回月份、新增用户数；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, new_users. Filters: WHERE c.channel_name = '应用商店'.

Output: `month, new_users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT strftime(g.metric_date,'%Y-%m') AS month, SUM(g.new_users) AS new_users FROM growth_daily_metrics g JOIN acquisition_channels c ON g.channel_id=c.channel_id WHERE c.channel_name='应用商店' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  TO_CHAR(g.metric_date, 'YYYY-MM') AS month,
  SUM(g.new_users) AS new_users
FROM growth_daily_metrics AS g
JOIN acquisition_channels AS c
  ON g.channel_id = c.channel_id
WHERE
  c.channel_name = '应用商店'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `18403eff556ff2b8fadb9cce3f920eb682b8ffd3b3367479d76094fefa01b01f`

PostgreSQL SQL SHA256: `f4ea7d4c2c78fcc4fad3016162ca3945b98c41a2a117f1b7e4f8ec2ac94d1956`

## GROWTH_OPS-033

信息流广告渠道2026年各月拉新人数；请返回月份、新增用户数；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, new_users. Filters: WHERE c.channel_name = '信息流广告'.

Output: `month, new_users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT strftime(g.metric_date,'%Y-%m') AS month, SUM(g.new_users) AS new_users FROM growth_daily_metrics g JOIN acquisition_channels c ON g.channel_id=c.channel_id WHERE c.channel_name='信息流广告' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  TO_CHAR(g.metric_date, 'YYYY-MM') AS month,
  SUM(g.new_users) AS new_users
FROM growth_daily_metrics AS g
JOIN acquisition_channels AS c
  ON g.channel_id = c.channel_id
WHERE
  c.channel_name = '信息流广告'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `f6ca710143dc14efadcecc946e5f7332ebd27d912f96d763e30654ca68c3d1b1`

PostgreSQL SQL SHA256: `f3df328e6a7de14bde50ffe2a42672897b387b705d9c9728f97931d39b4b054b`

## GROWTH_OPS-034

搜索广告渠道2026年各月拉新人数；请返回月份、新增用户数；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, new_users. Filters: WHERE c.channel_name = '搜索广告'.

Output: `month, new_users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT strftime(g.metric_date,'%Y-%m') AS month, SUM(g.new_users) AS new_users FROM growth_daily_metrics g JOIN acquisition_channels c ON g.channel_id=c.channel_id WHERE c.channel_name='搜索广告' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  TO_CHAR(g.metric_date, 'YYYY-MM') AS month,
  SUM(g.new_users) AS new_users
FROM growth_daily_metrics AS g
JOIN acquisition_channels AS c
  ON g.channel_id = c.channel_id
WHERE
  c.channel_name = '搜索广告'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `0fcdd1ee15bc88f60a73054f661774407ca0245c7bcc3d1951613b44a246ebcf`

PostgreSQL SQL SHA256: `81ce813f22c820f492de1f94c7a684981cb40b686b83fe4a088c55f4a425aa76`

## GROWTH_OPS-035

达人推广渠道2026年各月拉新人数；请返回月份、新增用户数；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, new_users. Filters: WHERE c.channel_name = '达人推广'.

Output: `month, new_users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT strftime(g.metric_date,'%Y-%m') AS month, SUM(g.new_users) AS new_users FROM growth_daily_metrics g JOIN acquisition_channels c ON g.channel_id=c.channel_id WHERE c.channel_name='达人推广' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  TO_CHAR(g.metric_date, 'YYYY-MM') AS month,
  SUM(g.new_users) AS new_users
FROM growth_daily_metrics AS g
JOIN acquisition_channels AS c
  ON g.channel_id = c.channel_id
WHERE
  c.channel_name = '达人推广'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `14b4d3f8feda8ded8ee54758749cfe2342441af021ffba3ef01073d24451fc2a`

PostgreSQL SQL SHA256: `6e9375a008f49e3a7050b2da7f0dd602838c3da6a654839ce2bb76c57dd66e7e`

## GROWTH_OPS-036

统计华东各注册平台的新增用户数；请返回注册平台、新增用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: platform, new_users. Filters: WHERE p.region = '华东'.

Output: `platform, new_users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT r.platform, COUNT(r.registration_id) AS new_users FROM user_registrations r JOIN user_profiles p ON r.user_id=p.user_id WHERE p.region='华东' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  r.platform,
  COUNT(r.registration_id) AS new_users
FROM user_registrations AS r
JOIN user_profiles AS p
  ON r.user_id = p.user_id
WHERE
  p.region = '华东'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `233428a74c678774a0b57488323201eca1a3bd9b7024ca6ae6faa8c640921180`

PostgreSQL SQL SHA256: `79d66093c2ef04ba954f3834320c5130dc1dc88169bf0a481ca23d1b674152b1`

## GROWTH_OPS-037

统计华南各注册平台的新增用户数；请返回注册平台、新增用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: platform, new_users. Filters: WHERE p.region = '华南'.

Output: `platform, new_users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT r.platform, COUNT(r.registration_id) AS new_users FROM user_registrations r JOIN user_profiles p ON r.user_id=p.user_id WHERE p.region='华南' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  r.platform,
  COUNT(r.registration_id) AS new_users
FROM user_registrations AS r
JOIN user_profiles AS p
  ON r.user_id = p.user_id
WHERE
  p.region = '华南'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `44c15eb60caffbf8971f3a957879b1102ddf66fd530caa99d8d3cf8dd5e67291`

PostgreSQL SQL SHA256: `44d912b26f9a7ae6fad11d316e049441be748fdc84e96c7cfd4b2af74112030d`

## GROWTH_OPS-038

统计华北各注册平台的新增用户数；请返回注册平台、新增用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: platform, new_users. Filters: WHERE p.region = '华北'.

Output: `platform, new_users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT r.platform, COUNT(r.registration_id) AS new_users FROM user_registrations r JOIN user_profiles p ON r.user_id=p.user_id WHERE p.region='华北' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  r.platform,
  COUNT(r.registration_id) AS new_users
FROM user_registrations AS r
JOIN user_profiles AS p
  ON r.user_id = p.user_id
WHERE
  p.region = '华北'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `35ffd4feb9c94419d4ed1a90d87ac4e00ef444f0a9b660ca46baef0858213cde`

PostgreSQL SQL SHA256: `ed6e79c9c2f791d1d92a4b3fe9ba0fa2efe9a34d836e4b95a7d6644c9fcd5005`

## GROWTH_OPS-039

统计西南各注册平台的新增用户数；请返回注册平台、新增用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: platform, new_users. Filters: WHERE p.region = '西南'.

Output: `platform, new_users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT r.platform, COUNT(r.registration_id) AS new_users FROM user_registrations r JOIN user_profiles p ON r.user_id=p.user_id WHERE p.region='西南' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  r.platform,
  COUNT(r.registration_id) AS new_users
FROM user_registrations AS r
JOIN user_profiles AS p
  ON r.user_id = p.user_id
WHERE
  p.region = '西南'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `697989071464697cdfc648031144f0b50a7505923cf3c3231f0fd3c6fececd80`

PostgreSQL SQL SHA256: `a6e2c61eeafa7208a704cbae24bb94dc9263370dde5153e36cf761f57a53a4e1`

## GROWTH_OPS-040

统计华中各注册平台的新增用户数；请返回注册平台、新增用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: platform, new_users. Filters: WHERE p.region = '华中'.

Output: `platform, new_users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT r.platform, COUNT(r.registration_id) AS new_users FROM user_registrations r JOIN user_profiles p ON r.user_id=p.user_id WHERE p.region='华中' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  r.platform,
  COUNT(r.registration_id) AS new_users
FROM user_registrations AS r
JOIN user_profiles AS p
  ON r.user_id = p.user_id
WHERE
  p.region = '华中'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `9d88e15570864310419c72528227b28a8d42abafbedf57676f8acd051e64028c`

PostgreSQL SQL SHA256: `b83f555141b842c801e24235c49094db6f8100f3fbaf4a6592cb3d0f34fc7d6d`

## GROWTH_OPS-041

2026-01付费、自然和推荐渠道分别带来多少注册用户；请返回渠道类型、注册用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_type, registrations. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-01'.

Output: `channel_type, registrations`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_type, COUNT(r.registration_id) AS registrations FROM user_registrations r JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE strftime(r.registered_at,'%Y-%m')='2026-01' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_type,
  COUNT(r.registration_id) AS registrations
FROM user_registrations AS r
JOIN acquisition_channels AS c
  ON r.channel_id = c.channel_id
WHERE
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `5174265df6cad6120d43a27cecd6b1e35db12071b39692f1c740f040942dc9a2`

PostgreSQL SQL SHA256: `8f47aff4cbc818da0518101511aabf21b53cd56d0f01ed9bc156553dda5f3129`

## GROWTH_OPS-042

2026-02付费、自然和推荐渠道分别带来多少注册用户；请返回渠道类型、注册用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_type, registrations. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-02'.

Output: `channel_type, registrations`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_type, COUNT(r.registration_id) AS registrations FROM user_registrations r JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE strftime(r.registered_at,'%Y-%m')='2026-02' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_type,
  COUNT(r.registration_id) AS registrations
FROM user_registrations AS r
JOIN acquisition_channels AS c
  ON r.channel_id = c.channel_id
WHERE
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `c3bd7dc220d0f0becd6b03e178fe7a10ae010ab1afa1fb35bfffd7ebcf3d5b1e`

PostgreSQL SQL SHA256: `b9273329eb7b6fca3f1a44f5d8acf3ad5bbd187bee100efe1febc17d1a0f76d8`

## GROWTH_OPS-043

2026-03付费、自然和推荐渠道分别带来多少注册用户；请返回渠道类型、注册用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_type, registrations. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-03'.

Output: `channel_type, registrations`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_type, COUNT(r.registration_id) AS registrations FROM user_registrations r JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE strftime(r.registered_at,'%Y-%m')='2026-03' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_type,
  COUNT(r.registration_id) AS registrations
FROM user_registrations AS r
JOIN acquisition_channels AS c
  ON r.channel_id = c.channel_id
WHERE
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `44b9c559c673194b359974833140f3bdc07161b4e2d1b1a7025bf3491bb338bc`

PostgreSQL SQL SHA256: `b0de6bade11d9617c04c92290fab1f95aa287f22b4d64b6a158460807f30b521`

## GROWTH_OPS-044

2026-04付费、自然和推荐渠道分别带来多少注册用户；请返回渠道类型、注册用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_type, registrations. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-04'.

Output: `channel_type, registrations`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_type, COUNT(r.registration_id) AS registrations FROM user_registrations r JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE strftime(r.registered_at,'%Y-%m')='2026-04' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_type,
  COUNT(r.registration_id) AS registrations
FROM user_registrations AS r
JOIN acquisition_channels AS c
  ON r.channel_id = c.channel_id
WHERE
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `39de966a98b6927273aa727dc03840305ef4c019611a270e9c4fac07be83d1d0`

PostgreSQL SQL SHA256: `778a76277395b2202cbb7ef9676562ac6f0d72b24a5082b57295b158731a0058`

## GROWTH_OPS-045

2026-05付费、自然和推荐渠道分别带来多少注册用户；请返回渠道类型、注册用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_type, registrations. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-05'.

Output: `channel_type, registrations`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_type, COUNT(r.registration_id) AS registrations FROM user_registrations r JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE strftime(r.registered_at,'%Y-%m')='2026-05' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_type,
  COUNT(r.registration_id) AS registrations
FROM user_registrations AS r
JOIN acquisition_channels AS c
  ON r.channel_id = c.channel_id
WHERE
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `7aa91943143f14fbe81be61934e76dd131bc0930bd261174d273134040033101`

PostgreSQL SQL SHA256: `9473e2ee0b27c8ed6be696303e6dbd8b7f6f3b5db2cd82025608f918298b4318`

## GROWTH_OPS-046

2026-01iOS端各渠道注册人数排行；请返回渠道名称、注册用户数；聚合口径：数量指标按对应业务记录计数；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, registrations. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-01' AND r.platform = 'iOS'.

Output: `channel_name, registrations`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, COUNT(r.registration_id) AS registrations FROM user_registrations r JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE strftime(r.registered_at,'%Y-%m')='2026-01' AND r.platform='iOS' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  COUNT(r.registration_id) AS registrations
FROM user_registrations AS r
JOIN acquisition_channels AS c
  ON r.channel_id = c.channel_id
WHERE
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-01' AND r.platform = 'iOS'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `42336c5f166f64ef03fdb56fd5adc510695102085f7445bdc5712f2d317bba85`

PostgreSQL SQL SHA256: `0114bb95295cf96679992b5765fef326408869695b6e2759394e39867227d608`

## GROWTH_OPS-047

2026-02iOS端各渠道注册人数排行；请返回渠道名称、注册用户数；聚合口径：数量指标按对应业务记录计数；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, registrations. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-02' AND r.platform = 'iOS'.

Output: `channel_name, registrations`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, COUNT(r.registration_id) AS registrations FROM user_registrations r JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE strftime(r.registered_at,'%Y-%m')='2026-02' AND r.platform='iOS' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  COUNT(r.registration_id) AS registrations
FROM user_registrations AS r
JOIN acquisition_channels AS c
  ON r.channel_id = c.channel_id
WHERE
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-02' AND r.platform = 'iOS'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `2d28524a3e1d0345d2c00fa4ac36f275b8dae83a84a3d2aebdf3bd61833561a0`

PostgreSQL SQL SHA256: `746f7d27d01a663254f5f53f9d28e0345f058c10b8adb3bf9db0c87b5c47f646`

## GROWTH_OPS-048

2026-03iOS端各渠道注册人数排行；请返回渠道名称、注册用户数；聚合口径：数量指标按对应业务记录计数；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, registrations. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-03' AND r.platform = 'iOS'.

Output: `channel_name, registrations`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, COUNT(r.registration_id) AS registrations FROM user_registrations r JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE strftime(r.registered_at,'%Y-%m')='2026-03' AND r.platform='iOS' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  COUNT(r.registration_id) AS registrations
FROM user_registrations AS r
JOIN acquisition_channels AS c
  ON r.channel_id = c.channel_id
WHERE
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-03' AND r.platform = 'iOS'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `3f016d80ba70e264d957f137aa75bac847ed8ea815b27c0b16b36d1da55b81f8`

PostgreSQL SQL SHA256: `eb05637b913b6c3308cfbf8f9f919e65af23a4632f0674bf95cf2448d9e0cac9`

## GROWTH_OPS-049

2026-01Android端各渠道注册人数排行；请返回渠道名称、注册用户数；聚合口径：数量指标按对应业务记录计数；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, registrations. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-01' AND r.platform = 'Android'.

Output: `channel_name, registrations`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, COUNT(r.registration_id) AS registrations FROM user_registrations r JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE strftime(r.registered_at,'%Y-%m')='2026-01' AND r.platform='Android' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  COUNT(r.registration_id) AS registrations
FROM user_registrations AS r
JOIN acquisition_channels AS c
  ON r.channel_id = c.channel_id
WHERE
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-01' AND r.platform = 'Android'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `34ce345bcc627296f756db1143fd50fda180655832b9c8f155494ad504fadd3e`

PostgreSQL SQL SHA256: `e33ac3ad45ac6344a9601ac4b60d5f4b387dd6be7e58af0e124050661fd274ea`

## GROWTH_OPS-052

2026-02各渠道注册到激活的转化率；请返回渠道名称、注册用户数、激活用户数、激活率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, registrations, activated_users, activation_rate. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-02'.

Output: `channel_name, registrations, activated_users, activation_rate`

Changes: `{"integer_truth_tests": [{"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}, {"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, COUNT(r.registration_id) AS registrations, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) AS activated_users, ROUND(SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/NULLIF(COUNT(r.registration_id),0),4) AS activation_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE strftime(r.registered_at,'%Y-%m')='2026-02' GROUP BY 1 ORDER BY 4 DESC,1
```

Explicit PostgreSQL SQL:

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
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
```

Original SQL SHA256: `8faf9b70dd8613ed04638b51e1d94a259eec963756514e9ffbf4269aba12c4d9`

PostgreSQL SQL SHA256: `7066f78a0528aaf1f6cd6535b09d2c19b2e919f60e6fb4e1034dacf0f6bcef79`

## GROWTH_OPS-053

2026-03各渠道注册到激活的转化率；请返回渠道名称、注册用户数、激活用户数、激活率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, registrations, activated_users, activation_rate. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-03'.

Output: `channel_name, registrations, activated_users, activation_rate`

Changes: `{"integer_truth_tests": [{"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}, {"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, COUNT(r.registration_id) AS registrations, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) AS activated_users, ROUND(SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/NULLIF(COUNT(r.registration_id),0),4) AS activation_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE strftime(r.registered_at,'%Y-%m')='2026-03' GROUP BY 1 ORDER BY 4 DESC,1
```

Explicit PostgreSQL SQL:

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
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
```

Original SQL SHA256: `6fdf26c7c9f5fdce76413ab4021adfd4e99de440164b9e1f8359bb038ce5be5c`

PostgreSQL SQL SHA256: `6da875eef022a66aff85c0a3c8a9739cee3d44b0cb0d3260936cd8a972532c69`

## GROWTH_OPS-054

2026-04各渠道注册到激活的转化率；请返回渠道名称、注册用户数、激活用户数、激活率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, registrations, activated_users, activation_rate. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-04'.

Output: `channel_name, registrations, activated_users, activation_rate`

Changes: `{"integer_truth_tests": [{"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}, {"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, COUNT(r.registration_id) AS registrations, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) AS activated_users, ROUND(SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/NULLIF(COUNT(r.registration_id),0),4) AS activation_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE strftime(r.registered_at,'%Y-%m')='2026-04' GROUP BY 1 ORDER BY 4 DESC,1
```

Explicit PostgreSQL SQL:

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
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
```

Original SQL SHA256: `95941c09c858dfe2d2e7aa16187dc2b80264cf505b6eab09f55ff033303ff066`

PostgreSQL SQL SHA256: `2bfa0c4420d241e4dd87a2783d5193ca3b8119042c87f55e84783b1774945109`

## GROWTH_OPS-055

2026-05各渠道注册到激活的转化率；请返回渠道名称、注册用户数、激活用户数、激活率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, registrations, activated_users, activation_rate. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-05'.

Output: `channel_name, registrations, activated_users, activation_rate`

Changes: `{"integer_truth_tests": [{"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}, {"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, COUNT(r.registration_id) AS registrations, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) AS activated_users, ROUND(SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/NULLIF(COUNT(r.registration_id),0),4) AS activation_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE strftime(r.registered_at,'%Y-%m')='2026-05' GROUP BY 1 ORDER BY 4 DESC,1
```

Explicit PostgreSQL SQL:

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
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
```

Original SQL SHA256: `f3f05c6fe204021046c465260718c5f90668de58ec8f71e78a2e06854b315bcb`

PostgreSQL SQL SHA256: `33794d4c52ea1c25c8c693b79e3cf58331ec1415dcb85f6b75850e4c55dc649e`

## GROWTH_OPS-056

华东不同注册平台的激活率；请返回注册平台、注册用户数、激活用户数、激活率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: platform, registrations, activated_users, activation_rate. Filters: WHERE p.region = '华东'.

Output: `platform, registrations, activated_users, activation_rate`

Changes: `{"integer_truth_tests": [{"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}, {"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT r.platform, COUNT(r.registration_id) AS registrations, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) AS activated_users, ROUND(SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/COUNT(r.registration_id),4) AS activation_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id JOIN user_profiles p ON r.user_id=p.user_id WHERE p.region='华东' GROUP BY 1 ORDER BY 4 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  r.platform,
  COUNT(r.registration_id) AS registrations,
  SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) AS activated_users,
  ROUND(
    CAST(CAST(SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(r.registration_id) AS DECIMAL),
    4
  ) AS activation_rate
FROM user_registrations AS r
JOIN user_activations AS a
  ON r.registration_id = a.registration_id
JOIN user_profiles AS p
  ON r.user_id = p.user_id
WHERE
  p.region = '华东'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
```

Original SQL SHA256: `4ac2094cd8b02e17bedb6e23c1f5db15d9200d2853967b63a63cab46ca8a526f`

PostgreSQL SQL SHA256: `319367ef53e226307c65748cb521d8d82f017cb4f5ecd3f7cfa60a380c49b783`

## GROWTH_OPS-057

华南不同注册平台的激活率；请返回注册平台、注册用户数、激活用户数、激活率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: platform, registrations, activated_users, activation_rate. Filters: WHERE p.region = '华南'.

Output: `platform, registrations, activated_users, activation_rate`

Changes: `{"integer_truth_tests": [{"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}, {"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT r.platform, COUNT(r.registration_id) AS registrations, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) AS activated_users, ROUND(SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/COUNT(r.registration_id),4) AS activation_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id JOIN user_profiles p ON r.user_id=p.user_id WHERE p.region='华南' GROUP BY 1 ORDER BY 4 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  r.platform,
  COUNT(r.registration_id) AS registrations,
  SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) AS activated_users,
  ROUND(
    CAST(CAST(SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(r.registration_id) AS DECIMAL),
    4
  ) AS activation_rate
FROM user_registrations AS r
JOIN user_activations AS a
  ON r.registration_id = a.registration_id
JOIN user_profiles AS p
  ON r.user_id = p.user_id
WHERE
  p.region = '华南'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
```

Original SQL SHA256: `1ae8a138e65122fc565ebbb17970bfb93e4099571574476336438b7d52a2316b`

PostgreSQL SQL SHA256: `3abda7a7c70821409df4771585dfa855c234f3801f52e56675557d635c7a118b`

## GROWTH_OPS-058

华北不同注册平台的激活率；请返回注册平台、注册用户数、激活用户数、激活率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: platform, registrations, activated_users, activation_rate. Filters: WHERE p.region = '华北'.

Output: `platform, registrations, activated_users, activation_rate`

Changes: `{"integer_truth_tests": [{"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}, {"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT r.platform, COUNT(r.registration_id) AS registrations, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) AS activated_users, ROUND(SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/COUNT(r.registration_id),4) AS activation_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id JOIN user_profiles p ON r.user_id=p.user_id WHERE p.region='华北' GROUP BY 1 ORDER BY 4 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  r.platform,
  COUNT(r.registration_id) AS registrations,
  SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) AS activated_users,
  ROUND(
    CAST(CAST(SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(r.registration_id) AS DECIMAL),
    4
  ) AS activation_rate
FROM user_registrations AS r
JOIN user_activations AS a
  ON r.registration_id = a.registration_id
JOIN user_profiles AS p
  ON r.user_id = p.user_id
WHERE
  p.region = '华北'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
```

Original SQL SHA256: `0767b459f19f0ba34839d0cf43dd38a4e247fd5361f9b7e038aa0493401dc732`

PostgreSQL SQL SHA256: `318e954bfcc1dbd3f0f2c88bf6fe050a6813322b091514518fa4f4aaf8003dec`

## GROWTH_OPS-059

西南不同注册平台的激活率；请返回注册平台、注册用户数、激活用户数、激活率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: platform, registrations, activated_users, activation_rate. Filters: WHERE p.region = '西南'.

Output: `platform, registrations, activated_users, activation_rate`

Changes: `{"integer_truth_tests": [{"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}, {"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT r.platform, COUNT(r.registration_id) AS registrations, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) AS activated_users, ROUND(SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/COUNT(r.registration_id),4) AS activation_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id JOIN user_profiles p ON r.user_id=p.user_id WHERE p.region='西南' GROUP BY 1 ORDER BY 4 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  r.platform,
  COUNT(r.registration_id) AS registrations,
  SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) AS activated_users,
  ROUND(
    CAST(CAST(SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(r.registration_id) AS DECIMAL),
    4
  ) AS activation_rate
FROM user_registrations AS r
JOIN user_activations AS a
  ON r.registration_id = a.registration_id
JOIN user_profiles AS p
  ON r.user_id = p.user_id
WHERE
  p.region = '西南'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
```

Original SQL SHA256: `fb859e2383cad248933197c3536ad5cd97e213a71ed82cd1346baa187b457c10`

PostgreSQL SQL SHA256: `845c86ca5db070571d8cb1ba6560e9bb71220c7a117b215ad1b57a098442d0d3`

## GROWTH_OPS-060

华中不同注册平台的激活率；请返回注册平台、注册用户数、激活用户数、激活率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: platform, registrations, activated_users, activation_rate. Filters: WHERE p.region = '华中'.

Output: `platform, registrations, activated_users, activation_rate`

Changes: `{"integer_truth_tests": [{"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}, {"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT r.platform, COUNT(r.registration_id) AS registrations, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) AS activated_users, ROUND(SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/COUNT(r.registration_id),4) AS activation_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id JOIN user_profiles p ON r.user_id=p.user_id WHERE p.region='华中' GROUP BY 1 ORDER BY 4 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  r.platform,
  COUNT(r.registration_id) AS registrations,
  SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) AS activated_users,
  ROUND(
    CAST(CAST(SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(r.registration_id) AS DECIMAL),
    4
  ) AS activation_rate
FROM user_registrations AS r
JOIN user_activations AS a
  ON r.registration_id = a.registration_id
JOIN user_profiles AS p
  ON r.user_id = p.user_id
WHERE
  p.region = '华中'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
```

Original SQL SHA256: `ef9b300906778af60bc847ad8b501cd3f8b2fb7529fd1bea058938340033d778`

PostgreSQL SQL SHA256: `cbb194e53f454510ec0644e043ed4c228586924553b52fdc300f2539c4aa9fad`

## GROWTH_OPS-065

达人推广渠道激活用户的平均激活耗时；请返回渠道名称、平均激活耗时；聚合口径：平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, avg_activation_seconds. Filters: WHERE a.is_activated <> 0 AND c.channel_name = '达人推广'.

Output: `channel_name, avg_activation_seconds`

Changes: `{"integer_truth_tests": [{"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, ROUND(AVG(a.activation_seconds),2) AS avg_activation_seconds FROM user_activations a JOIN user_registrations r ON a.registration_id=r.registration_id JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE a.is_activated AND c.channel_name='达人推广' GROUP BY 1
```

Explicit PostgreSQL SQL:

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
  a.is_activated <> 0 AND c.channel_name = '达人推广'
GROUP BY
  1
```

Original SQL SHA256: `b0b3af7816bc37488948e4a7ad3c25177da44dd66e954d474a4fa5006016de77`

PostgreSQL SQL SHA256: `0c2da97db7b60f7508a0c179718d90594867cb6e929205a44c3a11266daf3528`

## GROWTH_OPS-067

按激活规则统计用户数，重点查看观看满5分钟；请返回激活规则、用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: activation_rule, users. Filters: none.

Output: `activation_rule, users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 3}`

Original DuckDB SQL:

```sql
SELECT activation_rule, COUNT(activation_id) AS users FROM user_activations GROUP BY 1 ORDER BY CASE WHEN activation_rule='观看满5分钟' THEN 0 ELSE 1 END, users DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  activation_rule,
  COUNT(activation_id) AS users
FROM user_activations
GROUP BY
  1
ORDER BY
  CASE WHEN activation_rule = '观看满5分钟' THEN 0 ELSE 1 END,
  users DESC NULLS LAST,
  1
```

Original SQL SHA256: `6f86de4b0a8eeee73071d22b12997a605b03867fdaa55ac2389d64f3aa49f731`

PostgreSQL SQL SHA256: `3377e444457858802e52eaa5a295b11a18fcbf3e062e3ede63e5a5d98a7518ef`

## GROWTH_OPS-068

按激活规则统计用户数，重点查看未达到激活条件；请返回激活规则、用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: activation_rule, users. Filters: none.

Output: `activation_rule, users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 3}`

Original DuckDB SQL:

```sql
SELECT activation_rule, COUNT(activation_id) AS users FROM user_activations GROUP BY 1 ORDER BY CASE WHEN activation_rule='未达到激活条件' THEN 0 ELSE 1 END, users DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  activation_rule,
  COUNT(activation_id) AS users
FROM user_activations
GROUP BY
  1
ORDER BY
  CASE WHEN activation_rule = '未达到激活条件' THEN 0 ELSE 1 END,
  users DESC NULLS LAST,
  1
```

Original SQL SHA256: `047d31e072f06060db6c14d2034ca92123754f1e01e599e7be2cc5991dddce50`

PostgreSQL SQL SHA256: `15b8f271063225222fa1e551dccfa150995bd76b89dbb92eb785b7fefc9dcedf`

## GROWTH_OPS-069

按激活规则统计用户数，重点查看完成首次互动；请返回激活规则、用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: activation_rule, users. Filters: none.

Output: `activation_rule, users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 3}`

Original DuckDB SQL:

```sql
SELECT activation_rule, COUNT(activation_id) AS users FROM user_activations GROUP BY 1 ORDER BY CASE WHEN activation_rule='完成首次互动' THEN 0 ELSE 1 END, users DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  activation_rule,
  COUNT(activation_id) AS users
FROM user_activations
GROUP BY
  1
ORDER BY
  CASE WHEN activation_rule = '完成首次互动' THEN 0 ELSE 1 END,
  users DESC NULLS LAST,
  1
```

Original SQL SHA256: `bb886f04c86bf095e5fbd79e1504b75d4b6ab422a1de96d67b6dd8d6d9f86717`

PostgreSQL SQL SHA256: `847f3e88b61f38b12e20387f2e40e9c702b96242e526f0fe18be3632050d0ba1`

## GROWTH_OPS-070

请汇总按激活规则统计用户数，重点查看观看3条视频；请返回激活规则、用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: activation_rule, users. Filters: none.

Output: `activation_rule, users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 3}`

Original DuckDB SQL:

```sql
SELECT activation_rule, COUNT(activation_id) AS users FROM user_activations GROUP BY 1 ORDER BY CASE WHEN activation_rule='观看3条视频' THEN 0 ELSE 1 END, users DESC,1
```

Explicit PostgreSQL SQL:

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

Original SQL SHA256: `9e255ec362d717e487c84f4c1773bf7b091d71087c5274c9e0c390cc3c7ab067`

PostgreSQL SQL SHA256: `58aec54d4de280a03b1d0a8ef93816604d385f0dcd3527fc4e5160848a2caab2`

## GROWTH_OPS-071

统计2026-01注册的用户数、其中最终激活的用户数，以及注册到激活率；请返回月份、注册用户数、激活用户数、激活率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, registrations, activated_users, activation_rate. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-01'.

Output: `month, registrations, activated_users, activation_rate`

Changes: `{"integer_truth_tests": [{"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}, {"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT '2026-01' AS month, COUNT(r.registration_id) AS registrations, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) AS activated_users, ROUND(SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/COUNT(r.registration_id),4) AS activation_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id WHERE strftime(r.registered_at,'%Y-%m')='2026-01'
```

Explicit PostgreSQL SQL:

```sql
SELECT
  '2026-01' AS month,
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
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-01'
```

Original SQL SHA256: `fbec9736b78138f3adafb158cf09edfea64745a808f10107b98a9c9e351abc42`

PostgreSQL SQL SHA256: `67b6e8cd088f47836fd563fa33261a27833df393122ceb527f634db3f024c5d5`

## GROWTH_OPS-072

统计2026-02注册的用户数、其中最终激活的用户数，以及注册到激活率；请返回月份、注册用户数、激活用户数、激活率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, registrations, activated_users, activation_rate. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-02'.

Output: `month, registrations, activated_users, activation_rate`

Changes: `{"integer_truth_tests": [{"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}, {"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT '2026-02' AS month, COUNT(r.registration_id) AS registrations, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) AS activated_users, ROUND(SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/COUNT(r.registration_id),4) AS activation_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id WHERE strftime(r.registered_at,'%Y-%m')='2026-02'
```

Explicit PostgreSQL SQL:

```sql
SELECT
  '2026-02' AS month,
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
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-02'
```

Original SQL SHA256: `bcf2bdf3fbdb7e016c39e4e6357691808ea1110db78558f54bf8faf67c7b3c7b`

PostgreSQL SQL SHA256: `8b4fb622996da5ed7b80a95864c8c316aa93d386bc788646e584b38323612ccf`

## GROWTH_OPS-073

统计2026-03注册的用户数、其中最终激活的用户数，以及注册到激活率；请返回月份、注册用户数、激活用户数、激活率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, registrations, activated_users, activation_rate. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-03'.

Output: `month, registrations, activated_users, activation_rate`

Changes: `{"integer_truth_tests": [{"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}, {"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT '2026-03' AS month, COUNT(r.registration_id) AS registrations, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) AS activated_users, ROUND(SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/COUNT(r.registration_id),4) AS activation_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id WHERE strftime(r.registered_at,'%Y-%m')='2026-03'
```

Explicit PostgreSQL SQL:

```sql
SELECT
  '2026-03' AS month,
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
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-03'
```

Original SQL SHA256: `a334af97400c7129f16cb8582060186d723540bad82718f89271e563584d557f`

PostgreSQL SQL SHA256: `2f145ba010e4ca57dd71fbe2fa19cd2508c2786e0e1608d6b40697369b2c32b5`

## GROWTH_OPS-074

统计2026-04注册的用户数、其中最终激活的用户数，以及注册到激活率；请返回月份、注册用户数、激活用户数、激活率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, registrations, activated_users, activation_rate. Filters: WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-04'.

Output: `month, registrations, activated_users, activation_rate`

Changes: `{"integer_truth_tests": [{"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}, {"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT '2026-04' AS month, COUNT(r.registration_id) AS registrations, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END) AS activated_users, ROUND(SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/COUNT(r.registration_id),4) AS activation_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id WHERE strftime(r.registered_at,'%Y-%m')='2026-04'
```

Explicit PostgreSQL SQL:

```sql
SELECT
  '2026-04' AS month,
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
  TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-04'
```

Original SQL SHA256: `f876598ac6002683413f69d11d13388a7b5010a5111fcea98386ea699b794dbf`

PostgreSQL SQL SHA256: `e9d1a78d9a8d712864332c8c27aaed56b8fb260fe2d6cf616f16501c1c6e4761`

## GROWTH_OPS-077

各渠道3日留存率排名；请返回渠道名称、观察用户数、留存率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, observed_users, retention_rate. Filters: WHERE r.retention_day = 3.

Output: `channel_name, observed_users, retention_rate`

Changes: `{"integer_truth_tests": [{"expression": "r.is_retained", "table": "user_retention", "column": "is_retained", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, COUNT(*) AS observed_users, ROUND(SUM(CASE WHEN r.is_retained THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS retention_rate FROM user_retention r JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE r.retention_day=3 GROUP BY 1 ORDER BY 3 DESC,1
```

Explicit PostgreSQL SQL:

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
  r.retention_day = 3
GROUP BY
  1
ORDER BY
  3 DESC NULLS LAST,
  1
```

Original SQL SHA256: `f8615b3bd24f926bf64d91e3050c0593d5eb4524ded2880db0ba8a9e617bb60a`

PostgreSQL SQL SHA256: `7c37f6994df2b74a4bdda93b7cffe2f5672d371526ab4825d8ce6896749b0608`

## GROWTH_OPS-078

各渠道7日留存率排名；请返回渠道名称、观察用户数、留存率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, observed_users, retention_rate. Filters: WHERE r.retention_day = 7.

Output: `channel_name, observed_users, retention_rate`

Changes: `{"integer_truth_tests": [{"expression": "r.is_retained", "table": "user_retention", "column": "is_retained", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, COUNT(*) AS observed_users, ROUND(SUM(CASE WHEN r.is_retained THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS retention_rate FROM user_retention r JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE r.retention_day=7 GROUP BY 1 ORDER BY 3 DESC,1
```

Explicit PostgreSQL SQL:

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
  r.retention_day = 7
GROUP BY
  1
ORDER BY
  3 DESC NULLS LAST,
  1
```

Original SQL SHA256: `3dd3f9a5537c36eb500c47d3058a45c046c3cf39a7118a07bebce0c3d26f6f19`

PostgreSQL SQL SHA256: `e8eabfdba3e997c432eabf5c9b180b52c277249f57330aa9a6931f163faf0374`

## GROWTH_OPS-079

各渠道14日留存率排名；请返回渠道名称、观察用户数、留存率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, observed_users, retention_rate. Filters: WHERE r.retention_day = 14.

Output: `channel_name, observed_users, retention_rate`

Changes: `{"integer_truth_tests": [{"expression": "r.is_retained", "table": "user_retention", "column": "is_retained", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, COUNT(*) AS observed_users, ROUND(SUM(CASE WHEN r.is_retained THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS retention_rate FROM user_retention r JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE r.retention_day=14 GROUP BY 1 ORDER BY 3 DESC,1
```

Explicit PostgreSQL SQL:

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
  r.retention_day = 14
GROUP BY
  1
ORDER BY
  3 DESC NULLS LAST,
  1
```

Original SQL SHA256: `e1cfd4249f0e35ad6383bec5964a0163a7ffcb9a7c78a53cb3eb4ee65b669f18`

PostgreSQL SQL SHA256: `5983791f4d9020f6963c729298a94cace70b4fee79da2ebf5163d7c4ca2d3d63`

## GROWTH_OPS-080

各渠道30日留存率排名；请返回渠道名称、观察用户数、留存率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, observed_users, retention_rate. Filters: WHERE r.retention_day = 30.

Output: `channel_name, observed_users, retention_rate`

Changes: `{"integer_truth_tests": [{"expression": "r.is_retained", "table": "user_retention", "column": "is_retained", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name, COUNT(*) AS observed_users, ROUND(SUM(CASE WHEN r.is_retained THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS retention_rate FROM user_retention r JOIN acquisition_channels c ON r.channel_id=c.channel_id WHERE r.retention_day=30 GROUP BY 1 ORDER BY 3 DESC,1
```

Explicit PostgreSQL SQL:

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
  r.retention_day = 30
GROUP BY
  1
ORDER BY
  3 DESC NULLS LAST,
  1
```

Original SQL SHA256: `55f1b6100b5fc20c15c759b89842d91a3b3007848901eb1531a6c48f6d9c9dde`

PostgreSQL SQL SHA256: `5aeb6de5460d532cc061d6f923c7a60bfbe8597b0d5843ba156da9b6037e5efd`

## GROWTH_OPS-081

2026-01各留存周期的留存率；请返回留存周期、观察用户数、留存率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: retention_day, observed_users, retention_rate. Filters: WHERE TO_CHAR(registration_date, 'YYYY-MM') = '2026-01'.

Output: `retention_day, observed_users, retention_rate`

Changes: `{"integer_truth_tests": [{"expression": "is_retained", "table": "user_retention", "column": "is_retained", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT retention_day, COUNT(*) AS observed_users, ROUND(SUM(CASE WHEN is_retained THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS retention_rate FROM user_retention WHERE strftime(registration_date,'%Y-%m')='2026-01' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  retention_day,
  COUNT(*) AS observed_users,
  ROUND(
    CAST(CAST(SUM(CASE WHEN is_retained <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS retention_rate
FROM user_retention
WHERE
  TO_CHAR(registration_date, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `148d4ff1bdbf91683b689b7daca0162ccc8d9f4216cd6aaa77473e585d4ed5ef`

PostgreSQL SQL SHA256: `8313c13c99a80222d1a407bd7348535a13ca77d86a2ee0d47d412f9fa4775ee7`

## GROWTH_OPS-082

2026-02各留存周期的留存率；请返回留存周期、观察用户数、留存率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: retention_day, observed_users, retention_rate. Filters: WHERE TO_CHAR(registration_date, 'YYYY-MM') = '2026-02'.

Output: `retention_day, observed_users, retention_rate`

Changes: `{"integer_truth_tests": [{"expression": "is_retained", "table": "user_retention", "column": "is_retained", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT retention_day, COUNT(*) AS observed_users, ROUND(SUM(CASE WHEN is_retained THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS retention_rate FROM user_retention WHERE strftime(registration_date,'%Y-%m')='2026-02' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  retention_day,
  COUNT(*) AS observed_users,
  ROUND(
    CAST(CAST(SUM(CASE WHEN is_retained <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS retention_rate
FROM user_retention
WHERE
  TO_CHAR(registration_date, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `198b3996310c6745fa502c4e466367a10827c888565deb5bf0aa7545d9634ead`

PostgreSQL SQL SHA256: `a3a1e6ea706c77d600cdde44ee73fc6587a974d856162cc7428dbb3a6f2eb1ec`

## GROWTH_OPS-083

2026-03各留存周期的留存率；请返回留存周期、观察用户数、留存率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: retention_day, observed_users, retention_rate. Filters: WHERE TO_CHAR(registration_date, 'YYYY-MM') = '2026-03'.

Output: `retention_day, observed_users, retention_rate`

Changes: `{"integer_truth_tests": [{"expression": "is_retained", "table": "user_retention", "column": "is_retained", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT retention_day, COUNT(*) AS observed_users, ROUND(SUM(CASE WHEN is_retained THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS retention_rate FROM user_retention WHERE strftime(registration_date,'%Y-%m')='2026-03' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  retention_day,
  COUNT(*) AS observed_users,
  ROUND(
    CAST(CAST(SUM(CASE WHEN is_retained <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS retention_rate
FROM user_retention
WHERE
  TO_CHAR(registration_date, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `edbae38f7d37ef1b1be82c565546e835b3e7b9011e2eb191fbcfa5bb7108e593`

PostgreSQL SQL SHA256: `5c6a821813909cb8e59bd52668008824e8c32519b660144e17fd78b608abfd88`

## GROWTH_OPS-084

2026-04各留存周期的留存率；请返回留存周期、观察用户数、留存率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: retention_day, observed_users, retention_rate. Filters: WHERE TO_CHAR(registration_date, 'YYYY-MM') = '2026-04'.

Output: `retention_day, observed_users, retention_rate`

Changes: `{"integer_truth_tests": [{"expression": "is_retained", "table": "user_retention", "column": "is_retained", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT retention_day, COUNT(*) AS observed_users, ROUND(SUM(CASE WHEN is_retained THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS retention_rate FROM user_retention WHERE strftime(registration_date,'%Y-%m')='2026-04' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  retention_day,
  COUNT(*) AS observed_users,
  ROUND(
    CAST(CAST(SUM(CASE WHEN is_retained <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS retention_rate
FROM user_retention
WHERE
  TO_CHAR(registration_date, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `2105fe51ab51ab8ebb29d04085d8278351bef6e31179344940a0ff2c2fa4e584`

PostgreSQL SQL SHA256: `e72eae61e172b010852ffac2a797bbb87fccb59bbc7496b1b5894f2d6db9976d`

## GROWTH_OPS-085

2026-05各留存周期的留存率；请返回留存周期、观察用户数、留存率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: retention_day, observed_users, retention_rate. Filters: WHERE TO_CHAR(registration_date, 'YYYY-MM') = '2026-05'.

Output: `retention_day, observed_users, retention_rate`

Changes: `{"integer_truth_tests": [{"expression": "is_retained", "table": "user_retention", "column": "is_retained", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT retention_day, COUNT(*) AS observed_users, ROUND(SUM(CASE WHEN is_retained THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS retention_rate FROM user_retention WHERE strftime(registration_date,'%Y-%m')='2026-05' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  retention_day,
  COUNT(*) AS observed_users,
  ROUND(
    CAST(CAST(SUM(CASE WHEN is_retained <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS retention_rate
FROM user_retention
WHERE
  TO_CHAR(registration_date, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `f2c402170bce4d77ea02636241b5ee8dca16da0b06b048a6f7b397eabee02d84`

PostgreSQL SQL SHA256: `e3b22e4e055ac89dba86106c036807af01f47c28f86ca1e6d313060b80f09bad`

## GROWTH_OPS-087

华南用户平均活跃时长和会话次数；请返回地区、平均活跃时长、平均会话次数；聚合口径：平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: region, avg_active_minutes, avg_session_count. Filters: WHERE p.region = '华南'.

Output: `region, avg_active_minutes, avg_session_count`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.region, ROUND(AVG(a.active_minutes),2) AS avg_active_minutes, ROUND(AVG(a.session_count),2) AS avg_session_count FROM user_daily_activity a JOIN user_profiles p ON a.user_id=p.user_id WHERE p.region='华南' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.region,
  ROUND(CAST(AVG(a.active_minutes) AS DECIMAL), 2) AS avg_active_minutes,
  ROUND(CAST(AVG(a.session_count) AS DECIMAL), 2) AS avg_session_count
FROM user_daily_activity AS a
JOIN user_profiles AS p
  ON a.user_id = p.user_id
WHERE
  p.region = '华南'
GROUP BY
  1
```

Original SQL SHA256: `6c6186667215e89cff8a90d079d7802b61f0a9fbe50215375156155c2a60287f`

PostgreSQL SQL SHA256: `de8bb8060212e0d55af9eb9f8ab9a58016c9ad944daea788f94c437955f628f7`

## GROWTH_OPS-088

华北用户平均活跃时长和会话次数；请返回地区、平均活跃时长、平均会话次数；聚合口径：平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: region, avg_active_minutes, avg_session_count. Filters: WHERE p.region = '华北'.

Output: `region, avg_active_minutes, avg_session_count`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.region, ROUND(AVG(a.active_minutes),2) AS avg_active_minutes, ROUND(AVG(a.session_count),2) AS avg_session_count FROM user_daily_activity a JOIN user_profiles p ON a.user_id=p.user_id WHERE p.region='华北' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.region,
  ROUND(CAST(AVG(a.active_minutes) AS DECIMAL), 2) AS avg_active_minutes,
  ROUND(CAST(AVG(a.session_count) AS DECIMAL), 2) AS avg_session_count
FROM user_daily_activity AS a
JOIN user_profiles AS p
  ON a.user_id = p.user_id
WHERE
  p.region = '华北'
GROUP BY
  1
```

Original SQL SHA256: `8fe2dc29e9bd32fcca94499869b97c0188e54b917386ea72c4c68e1ea38796d3`

PostgreSQL SQL SHA256: `ee41756824b6d03283cc9d263fef09e2d832435976459b63899f0af5bd34a460`

## GROWTH_OPS-089

西南用户平均活跃时长和会话次数；请返回地区、平均活跃时长、平均会话次数；聚合口径：平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: region, avg_active_minutes, avg_session_count. Filters: WHERE p.region = '西南'.

Output: `region, avg_active_minutes, avg_session_count`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.region, ROUND(AVG(a.active_minutes),2) AS avg_active_minutes, ROUND(AVG(a.session_count),2) AS avg_session_count FROM user_daily_activity a JOIN user_profiles p ON a.user_id=p.user_id WHERE p.region='西南' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.region,
  ROUND(CAST(AVG(a.active_minutes) AS DECIMAL), 2) AS avg_active_minutes,
  ROUND(CAST(AVG(a.session_count) AS DECIMAL), 2) AS avg_session_count
FROM user_daily_activity AS a
JOIN user_profiles AS p
  ON a.user_id = p.user_id
WHERE
  p.region = '西南'
GROUP BY
  1
```

Original SQL SHA256: `c53f0b3a0b0b57d91cda73258ef2000e204135baa9d2a4eae9e58b366bf8a786`

PostgreSQL SQL SHA256: `8efa4ac7725115d5be533122684b4d69ffff8c6e7d0d21c7dc05391cf9cdb7fc`

## GROWTH_OPS-090

华中用户平均活跃时长和会话次数；请返回地区、平均活跃时长、平均会话次数；聚合口径：平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: region, avg_active_minutes, avg_session_count. Filters: WHERE p.region = '华中'.

Output: `region, avg_active_minutes, avg_session_count`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.region, ROUND(AVG(a.active_minutes),2) AS avg_active_minutes, ROUND(AVG(a.session_count),2) AS avg_session_count FROM user_daily_activity a JOIN user_profiles p ON a.user_id=p.user_id WHERE p.region='华中' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.region,
  ROUND(CAST(AVG(a.active_minutes) AS DECIMAL), 2) AS avg_active_minutes,
  ROUND(CAST(AVG(a.session_count) AS DECIMAL), 2) AS avg_session_count
FROM user_daily_activity AS a
JOIN user_profiles AS p
  ON a.user_id = p.user_id
WHERE
  p.region = '华中'
GROUP BY
  1
```

Original SQL SHA256: `3aa7c682a461659d8518bc47eb46df144863aa7664365cfaaf3e15e5984d33f2`

PostgreSQL SQL SHA256: `7f1f37d142df8bc9c43ed7cc595b36f21c6fce4a440e82dfc974ab534f134662`

## GROWTH_OPS-091

2026-01有效活跃记录占比；请返回月份、活跃记录数、有效活跃占比；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, activity_records, valid_active_rate. Filters: WHERE TO_CHAR(activity_date, 'YYYY-MM') = '2026-01'.

Output: `month, activity_records, valid_active_rate`

Changes: `{"integer_truth_tests": [{"expression": "is_valid_active", "table": "user_daily_activity", "column": "is_valid_active", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT '2026-01' AS month, COUNT(*) AS activity_records, ROUND(SUM(CASE WHEN is_valid_active THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS valid_active_rate FROM user_daily_activity WHERE strftime(activity_date,'%Y-%m')='2026-01'
```

Explicit PostgreSQL SQL:

```sql
SELECT
  '2026-01' AS month,
  COUNT(*) AS activity_records,
  ROUND(
    CAST(CAST(SUM(CASE WHEN is_valid_active <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS valid_active_rate
FROM user_daily_activity
WHERE
  TO_CHAR(activity_date, 'YYYY-MM') = '2026-01'
```

Original SQL SHA256: `4c5e993783ac7509f4bff4e1225b811872c52f66bd2ff05f2138cca1a408277d`

PostgreSQL SQL SHA256: `43fe2a343a593964168ebdb87df24c331d828640264b6f0c9405072cf6c70d43`

## GROWTH_OPS-092

2026-02有效活跃记录占比；请返回月份、活跃记录数、有效活跃占比；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, activity_records, valid_active_rate. Filters: WHERE TO_CHAR(activity_date, 'YYYY-MM') = '2026-02'.

Output: `month, activity_records, valid_active_rate`

Changes: `{"integer_truth_tests": [{"expression": "is_valid_active", "table": "user_daily_activity", "column": "is_valid_active", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT '2026-02' AS month, COUNT(*) AS activity_records, ROUND(SUM(CASE WHEN is_valid_active THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS valid_active_rate FROM user_daily_activity WHERE strftime(activity_date,'%Y-%m')='2026-02'
```

Explicit PostgreSQL SQL:

```sql
SELECT
  '2026-02' AS month,
  COUNT(*) AS activity_records,
  ROUND(
    CAST(CAST(SUM(CASE WHEN is_valid_active <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS valid_active_rate
FROM user_daily_activity
WHERE
  TO_CHAR(activity_date, 'YYYY-MM') = '2026-02'
```

Original SQL SHA256: `493c0878367072d686d11ef3719950defecc3751dc4afea12214a17f10f2eaf8`

PostgreSQL SQL SHA256: `5b6321437e54586eb7f4cb9dedfcd0df22dd152142c403a243deed3c97cdbcdb`

## GROWTH_OPS-093

2026-03有效活跃记录占比；请返回月份、活跃记录数、有效活跃占比；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, activity_records, valid_active_rate. Filters: WHERE TO_CHAR(activity_date, 'YYYY-MM') = '2026-03'.

Output: `month, activity_records, valid_active_rate`

Changes: `{"integer_truth_tests": [{"expression": "is_valid_active", "table": "user_daily_activity", "column": "is_valid_active", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT '2026-03' AS month, COUNT(*) AS activity_records, ROUND(SUM(CASE WHEN is_valid_active THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS valid_active_rate FROM user_daily_activity WHERE strftime(activity_date,'%Y-%m')='2026-03'
```

Explicit PostgreSQL SQL:

```sql
SELECT
  '2026-03' AS month,
  COUNT(*) AS activity_records,
  ROUND(
    CAST(CAST(SUM(CASE WHEN is_valid_active <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS valid_active_rate
FROM user_daily_activity
WHERE
  TO_CHAR(activity_date, 'YYYY-MM') = '2026-03'
```

Original SQL SHA256: `368857efe0c4f41cee99d515b412936e446a901bec2d9fcbf0f7c65a9cb2f05d`

PostgreSQL SQL SHA256: `3dfcb35bbc75a7bed575c0a3f3dded6b5cc890a88adda0f9f3650fa4fed5c45a`

## GROWTH_OPS-094

2026-04有效活跃记录占比；请返回月份、活跃记录数、有效活跃占比；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, activity_records, valid_active_rate. Filters: WHERE TO_CHAR(activity_date, 'YYYY-MM') = '2026-04'.

Output: `month, activity_records, valid_active_rate`

Changes: `{"integer_truth_tests": [{"expression": "is_valid_active", "table": "user_daily_activity", "column": "is_valid_active", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT '2026-04' AS month, COUNT(*) AS activity_records, ROUND(SUM(CASE WHEN is_valid_active THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS valid_active_rate FROM user_daily_activity WHERE strftime(activity_date,'%Y-%m')='2026-04'
```

Explicit PostgreSQL SQL:

```sql
SELECT
  '2026-04' AS month,
  COUNT(*) AS activity_records,
  ROUND(
    CAST(CAST(SUM(CASE WHEN is_valid_active <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS valid_active_rate
FROM user_daily_activity
WHERE
  TO_CHAR(activity_date, 'YYYY-MM') = '2026-04'
```

Original SQL SHA256: `9876d913e0ece22264cb43403cac3c3c827a666d37b1f63b2291d09780db9173`

PostgreSQL SQL SHA256: `276633403f9805e1f65f908243eccafde4d4bec48042f6210d9eb8ac5b01f72b`

## GROWTH_OPS-095

2026-05有效活跃记录占比；请返回月份、活跃记录数、有效活跃占比；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, activity_records, valid_active_rate. Filters: WHERE TO_CHAR(activity_date, 'YYYY-MM') = '2026-05'.

Output: `month, activity_records, valid_active_rate`

Changes: `{"integer_truth_tests": [{"expression": "is_valid_active", "table": "user_daily_activity", "column": "is_valid_active", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT '2026-05' AS month, COUNT(*) AS activity_records, ROUND(SUM(CASE WHEN is_valid_active THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS valid_active_rate FROM user_daily_activity WHERE strftime(activity_date,'%Y-%m')='2026-05'
```

Explicit PostgreSQL SQL:

```sql
SELECT
  '2026-05' AS month,
  COUNT(*) AS activity_records,
  ROUND(
    CAST(CAST(SUM(CASE WHEN is_valid_active <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS valid_active_rate
FROM user_daily_activity
WHERE
  TO_CHAR(activity_date, 'YYYY-MM') = '2026-05'
```

Original SQL SHA256: `348e763e5c85d5991f27832df1fc51eaf6d6df111da64818cb06b452abf67010`

PostgreSQL SQL SHA256: `3ea2b00dcedcb029623f27f4aff979f9d8f15b6ad1fc2ece436a654375f39a4c`

## GROWTH_OPS-096

统计2026-01期间注册平台为iOS的用户产生的播放总次数除以去重用户数；请返回注册平台、人均播放次数；聚合口径：去重数量按对应实体唯一标识计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: platform, plays_per_user. Filters: WHERE r.platform = 'iOS' AND TO_CHAR(a.activity_date, 'YYYY-MM') = '2026-01'.

Output: `platform, plays_per_user`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT 'iOS' AS platform, ROUND(SUM(a.play_count)*1.0/COUNT(DISTINCT a.user_id),2) AS plays_per_user FROM user_daily_activity a JOIN user_registrations r ON a.user_id=r.user_id WHERE r.platform='iOS' AND strftime(a.activity_date,'%Y-%m')='2026-01'
```

Explicit PostgreSQL SQL:

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
  r.platform = 'iOS' AND TO_CHAR(a.activity_date, 'YYYY-MM') = '2026-01'
```

Original SQL SHA256: `955d1482982b5fb858acaf9525d353baf2356a979d317f7e463babd439e2a859`

PostgreSQL SQL SHA256: `53f582a6061dbf448080fc32e4ac5b5d55dbe58eea5b9b6a6c0032ed8845229b`

## GROWTH_OPS-097

统计2026-02期间注册平台为iOS的用户产生的播放总次数除以去重用户数；请返回注册平台、人均播放次数；聚合口径：去重数量按对应实体唯一标识计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: platform, plays_per_user. Filters: WHERE r.platform = 'iOS' AND TO_CHAR(a.activity_date, 'YYYY-MM') = '2026-02'.

Output: `platform, plays_per_user`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT 'iOS' AS platform, ROUND(SUM(a.play_count)*1.0/COUNT(DISTINCT a.user_id),2) AS plays_per_user FROM user_daily_activity a JOIN user_registrations r ON a.user_id=r.user_id WHERE r.platform='iOS' AND strftime(a.activity_date,'%Y-%m')='2026-02'
```

Explicit PostgreSQL SQL:

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
  r.platform = 'iOS' AND TO_CHAR(a.activity_date, 'YYYY-MM') = '2026-02'
```

Original SQL SHA256: `02be85403b7b08e28aa85a1cae76817276024ce29e9a3ddd3bdf70abcb6e1f47`

PostgreSQL SQL SHA256: `6853ba402355fa467168cadfd62da1b6f9ff8bd197b0372d0f95865489512fd5`

## GROWTH_OPS-098

统计2026-03期间注册平台为iOS的用户产生的播放总次数除以去重用户数；请返回注册平台、人均播放次数；聚合口径：去重数量按对应实体唯一标识计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: platform, plays_per_user. Filters: WHERE r.platform = 'iOS' AND TO_CHAR(a.activity_date, 'YYYY-MM') = '2026-03'.

Output: `platform, plays_per_user`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT 'iOS' AS platform, ROUND(SUM(a.play_count)*1.0/COUNT(DISTINCT a.user_id),2) AS plays_per_user FROM user_daily_activity a JOIN user_registrations r ON a.user_id=r.user_id WHERE r.platform='iOS' AND strftime(a.activity_date,'%Y-%m')='2026-03'
```

Explicit PostgreSQL SQL:

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
  r.platform = 'iOS' AND TO_CHAR(a.activity_date, 'YYYY-MM') = '2026-03'
```

Original SQL SHA256: `1da090a3b16d04eb8c3265a2d184be3e438c70741ea3503f44bcc69e8583542f`

PostgreSQL SQL SHA256: `7570c4096104bd0efea987cc85493102392c9a63649daf3266e53c8523428e9f`

## GROWTH_OPS-099

统计2026-04期间注册平台为iOS的用户产生的播放总次数除以去重用户数；请返回注册平台、人均播放次数；聚合口径：去重数量按对应实体唯一标识计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: platform, plays_per_user. Filters: WHERE r.platform = 'iOS' AND TO_CHAR(a.activity_date, 'YYYY-MM') = '2026-04'.

Output: `platform, plays_per_user`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT 'iOS' AS platform, ROUND(SUM(a.play_count)*1.0/COUNT(DISTINCT a.user_id),2) AS plays_per_user FROM user_daily_activity a JOIN user_registrations r ON a.user_id=r.user_id WHERE r.platform='iOS' AND strftime(a.activity_date,'%Y-%m')='2026-04'
```

Explicit PostgreSQL SQL:

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
  r.platform = 'iOS' AND TO_CHAR(a.activity_date, 'YYYY-MM') = '2026-04'
```

Original SQL SHA256: `9c9734e2a2060cae0572ff08edf467e31110d8196650686d55d970d5a19986af`

PostgreSQL SQL SHA256: `a70c766f76a48f0e47999927aa2496205ce018ea59ce24cb284f8cf03b46032f`

## GROWTH_OPS-103

用户按性别的分布；请返回性别、用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: gender, users. Filters: none.

Output: `gender, users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT gender, COUNT(user_id) AS users FROM user_profiles GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  gender,
  COUNT(user_id) AS users
FROM user_profiles
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `333d653afa580c9ef97f040eaaf116601fdc0e6fdf557d2003ae36f9b96f0044`

PostgreSQL SQL SHA256: `29a87a439e9686212e3cb695044b6c8bb2fe86e878ebc7c544ed3941546d6007`

## GROWTH_OPS-104

用户按城市等级的分布；请返回城市等级、用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: city_tier, users. Filters: none.

Output: `city_tier, users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT city_tier, COUNT(user_id) AS users FROM user_profiles GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  city_tier,
  COUNT(user_id) AS users
FROM user_profiles
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `1e71502ed4a9832d0138819835ab47e4fa49205bcc94cf23412c2dc8773e429a`

PostgreSQL SQL SHA256: `5ae0c2d46a698bc2a9417f9fd602eb6d3392407298d0c0ecc674aebf084de31d`

## GROWTH_OPS-105

用户按主要兴趣的分布；请返回主要兴趣、用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: primary_interest, users. Filters: none.

Output: `primary_interest, users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT primary_interest, COUNT(user_id) AS users FROM user_profiles GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  primary_interest,
  COUNT(user_id) AS users
FROM user_profiles
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `e10a2a405011f94061a43ca9855ff8084649cc8689475ef6c9022161089f3355`

PostgreSQL SQL SHA256: `2927a43c85fb2df4630663bb0c0f81860bd994320ba457141fe91feaf9436971`

## GROWTH_OPS-106

新用户用户按地区分布及平均参与度；请返回地区、用户数、平均参与度；聚合口径：去重数量按对应实体唯一标识计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: region, users, avg_engagement_score. Filters: WHERE l.lifecycle_stage = '新用户'.

Output: `region, users, avg_engagement_score`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.region, COUNT(DISTINCT l.user_id) AS users, ROUND(AVG(l.engagement_score),2) AS avg_engagement_score FROM user_lifecycle_snapshots l JOIN user_profiles p ON l.user_id=p.user_id WHERE l.lifecycle_stage='新用户' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.region,
  COUNT(DISTINCT l.user_id) AS users,
  ROUND(CAST(AVG(l.engagement_score) AS DECIMAL), 2) AS avg_engagement_score
FROM user_lifecycle_snapshots AS l
JOIN user_profiles AS p
  ON l.user_id = p.user_id
WHERE
  l.lifecycle_stage = '新用户'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `9a7155069990368dda5560a159ed1b6d089433cce16c7230f06f105e5a61e074`

PostgreSQL SQL SHA256: `426c5d10150928581034e57c19983e65c525e3ae43c627cd18656459c032b5f8`

## GROWTH_OPS-107

活跃用户用户按地区分布及平均参与度；请返回地区、用户数、平均参与度；聚合口径：去重数量按对应实体唯一标识计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: region, users, avg_engagement_score. Filters: WHERE l.lifecycle_stage = '活跃用户'.

Output: `region, users, avg_engagement_score`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.region, COUNT(DISTINCT l.user_id) AS users, ROUND(AVG(l.engagement_score),2) AS avg_engagement_score FROM user_lifecycle_snapshots l JOIN user_profiles p ON l.user_id=p.user_id WHERE l.lifecycle_stage='活跃用户' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.region,
  COUNT(DISTINCT l.user_id) AS users,
  ROUND(CAST(AVG(l.engagement_score) AS DECIMAL), 2) AS avg_engagement_score
FROM user_lifecycle_snapshots AS l
JOIN user_profiles AS p
  ON l.user_id = p.user_id
WHERE
  l.lifecycle_stage = '活跃用户'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `4b59dc55bd1c78151da13c58bd3347f378852885846b7cef8098fba49b521340`

PostgreSQL SQL SHA256: `987558b8ee00b9fc5eb1a2aa532e7d6209faa796f16c30261d21cbb4cb174f38`

## GROWTH_OPS-108

沉默用户用户按地区分布及平均参与度；请返回地区、用户数、平均参与度；聚合口径：去重数量按对应实体唯一标识计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: region, users, avg_engagement_score. Filters: WHERE l.lifecycle_stage = '沉默用户'.

Output: `region, users, avg_engagement_score`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.region, COUNT(DISTINCT l.user_id) AS users, ROUND(AVG(l.engagement_score),2) AS avg_engagement_score FROM user_lifecycle_snapshots l JOIN user_profiles p ON l.user_id=p.user_id WHERE l.lifecycle_stage='沉默用户' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.region,
  COUNT(DISTINCT l.user_id) AS users,
  ROUND(CAST(AVG(l.engagement_score) AS DECIMAL), 2) AS avg_engagement_score
FROM user_lifecycle_snapshots AS l
JOIN user_profiles AS p
  ON l.user_id = p.user_id
WHERE
  l.lifecycle_stage = '沉默用户'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `de188707af3e9487eaca09012063fe71b4022a387d839a587534efbf20453328`

PostgreSQL SQL SHA256: `a2cbd032b807c1dfbd0e8d2f024bb2fa573f57b222f63955c60b4eb7a29b01fb`

## GROWTH_OPS-109

流失用户用户按地区分布及平均参与度；请返回地区、用户数、平均参与度；聚合口径：去重数量按对应实体唯一标识计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: region, users, avg_engagement_score. Filters: WHERE l.lifecycle_stage = '流失用户'.

Output: `region, users, avg_engagement_score`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.region, COUNT(DISTINCT l.user_id) AS users, ROUND(AVG(l.engagement_score),2) AS avg_engagement_score FROM user_lifecycle_snapshots l JOIN user_profiles p ON l.user_id=p.user_id WHERE l.lifecycle_stage='流失用户' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.region,
  COUNT(DISTINCT l.user_id) AS users,
  ROUND(CAST(AVG(l.engagement_score) AS DECIMAL), 2) AS avg_engagement_score
FROM user_lifecycle_snapshots AS l
JOIN user_profiles AS p
  ON l.user_id = p.user_id
WHERE
  l.lifecycle_stage = '流失用户'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `eccdaa6be4898a2c5764a8952f7ae957f8ac6e04749d5427ed8c330ba41a4dbc`

PostgreSQL SQL SHA256: `fd823cbb297f26d196a1cd34074f9f34f42227fc8000d252f3818690ef4da768`

## GROWTH_OPS-110

请汇总活跃用户用户按地区分布及平均参与度；请返回地区、用户数、平均参与度；聚合口径：去重数量按对应实体唯一标识计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: region, users, avg_engagement_score. Filters: WHERE l.lifecycle_stage = '活跃用户'.

Output: `region, users, avg_engagement_score`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.region, COUNT(DISTINCT l.user_id) AS users, ROUND(AVG(l.engagement_score),2) AS avg_engagement_score FROM user_lifecycle_snapshots l JOIN user_profiles p ON l.user_id=p.user_id WHERE l.lifecycle_stage='活跃用户' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.region,
  COUNT(DISTINCT l.user_id) AS users,
  ROUND(CAST(AVG(l.engagement_score) AS DECIMAL), 2) AS avg_engagement_score
FROM user_lifecycle_snapshots AS l
JOIN user_profiles AS p
  ON l.user_id = p.user_id
WHERE
  l.lifecycle_stage = '活跃用户'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `4b59dc55bd1c78151da13c58bd3347f378852885846b7cef8098fba49b521340`

PostgreSQL SQL SHA256: `987558b8ee00b9fc5eb1a2aa532e7d6209faa796f16c30261d21cbb4cb174f38`

## GROWTH_OPS-111

华东medium流失用户的流失原因分布；请返回流失原因、用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: churn_reason, users. Filters: WHERE p.region = '华东' AND c.churn_level = 'medium'.

Output: `churn_reason, users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.churn_reason, COUNT(*) AS users FROM user_churn_events c JOIN user_profiles p ON c.user_id=p.user_id WHERE p.region='华东' AND c.churn_level='medium' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.churn_reason,
  COUNT(*) AS users
FROM user_churn_events AS c
JOIN user_profiles AS p
  ON c.user_id = p.user_id
WHERE
  p.region = '华东' AND c.churn_level = 'medium'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `fa529c2b67cfaa78b2c8cc04ba50bedc7e1b77f62d5923a444f8230ea83d1cdf`

PostgreSQL SQL SHA256: `2624329c94f4d1a63a05f71bee693ac32ea16acc7fb1e6dbca16ba7d2f04ddeb`

## GROWTH_OPS-112

华南high流失用户的流失原因分布；请返回流失原因、用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: churn_reason, users. Filters: WHERE p.region = '华南' AND c.churn_level = 'high'.

Output: `churn_reason, users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.churn_reason, COUNT(*) AS users FROM user_churn_events c JOIN user_profiles p ON c.user_id=p.user_id WHERE p.region='华南' AND c.churn_level='high' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.churn_reason,
  COUNT(*) AS users
FROM user_churn_events AS c
JOIN user_profiles AS p
  ON c.user_id = p.user_id
WHERE
  p.region = '华南' AND c.churn_level = 'high'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `c839ec5cfb0595d9852be523d7b5b3dd68c3493664c6c00126fa13576bbf2aca`

PostgreSQL SQL SHA256: `4bd347a5e852a6a3f54ed5b7a246972bcf4fd848bc2f6626d089533400ff7b96`

## GROWTH_OPS-113

华北medium流失用户的流失原因分布；请返回流失原因、用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: churn_reason, users. Filters: WHERE p.region = '华北' AND c.churn_level = 'medium'.

Output: `churn_reason, users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.churn_reason, COUNT(*) AS users FROM user_churn_events c JOIN user_profiles p ON c.user_id=p.user_id WHERE p.region='华北' AND c.churn_level='medium' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.churn_reason,
  COUNT(*) AS users
FROM user_churn_events AS c
JOIN user_profiles AS p
  ON c.user_id = p.user_id
WHERE
  p.region = '华北' AND c.churn_level = 'medium'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `bcb5fe9b92a701dc3eef16b0c133b6756062d46ae283a02aaef6d1aabacc446e`

PostgreSQL SQL SHA256: `99821c7d0e69879fc7475d82ec17aa2b26700e5ee3a493170f2d93a80e03380b`

## GROWTH_OPS-114

西南high流失用户的流失原因分布；请返回流失原因、用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: churn_reason, users. Filters: WHERE p.region = '西南' AND c.churn_level = 'high'.

Output: `churn_reason, users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.churn_reason, COUNT(*) AS users FROM user_churn_events c JOIN user_profiles p ON c.user_id=p.user_id WHERE p.region='西南' AND c.churn_level='high' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.churn_reason,
  COUNT(*) AS users
FROM user_churn_events AS c
JOIN user_profiles AS p
  ON c.user_id = p.user_id
WHERE
  p.region = '西南' AND c.churn_level = 'high'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `c1e390a906f1ac330e88a7c89a9bf5af5c2d96bdfbcd60728c686a212d779a31`

PostgreSQL SQL SHA256: `baa9abeb5dea94b6e175fd7ba8c3ca96e51e7c71f280ebb09091bdf53ba4b71a`

## GROWTH_OPS-115

华中medium流失用户的流失原因分布；请返回流失原因、用户数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: churn_reason, users. Filters: WHERE p.region = '华中' AND c.churn_level = 'medium'.

Output: `churn_reason, users`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.churn_reason, COUNT(*) AS users FROM user_churn_events c JOIN user_profiles p ON c.user_id=p.user_id WHERE p.region='华中' AND c.churn_level='medium' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.churn_reason,
  COUNT(*) AS users
FROM user_churn_events AS c
JOIN user_profiles AS p
  ON c.user_id = p.user_id
WHERE
  p.region = '华中' AND c.churn_level = 'medium'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `cc5c31d9914b1d72dfff2a99809a7d7f7b2aa324dfa2faa269c8e20e79fe3f9d`

PostgreSQL SQL SHA256: `529e4181523cfe277230c5fae7e299a508bab6746b624f10e15f7e08591c6ea0`

## GROWTH_OPS-116

2026年8月华东各流失等级人数和平均未活跃天数；请返回流失等级、用户数、平均未活跃天数；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: churn_level, users, avg_inactive_days. Filters: WHERE TO_CHAR(c.identified_date, 'YYYY-MM') = '2026-08' AND p.region = '华东'.

Output: `churn_level, users, avg_inactive_days`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.churn_level,COUNT(*) AS users,ROUND(AVG(c.inactive_days),2) AS avg_inactive_days FROM user_churn_events c JOIN user_profiles p ON c.user_id=p.user_id WHERE strftime(c.identified_date,'%Y-%m')='2026-08' AND p.region='华东' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.churn_level,
  COUNT(*) AS users,
  ROUND(CAST(AVG(c.inactive_days) AS DECIMAL), 2) AS avg_inactive_days
FROM user_churn_events AS c
JOIN user_profiles AS p
  ON c.user_id = p.user_id
WHERE
  TO_CHAR(c.identified_date, 'YYYY-MM') = '2026-08' AND p.region = '华东'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `bfe66cf32ba67632a54735cb10ca0a045e45bbb25a983f17acb88d8d9c4592aa`

PostgreSQL SQL SHA256: `66ba0a991a9b98540b712de05e0bf8e9e765a7b0dc90edc7c38ecd3a94881fa3`

## GROWTH_OPS-117

2026年8月华南各流失等级人数和平均未活跃天数；请返回流失等级、用户数、平均未活跃天数；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: churn_level, users, avg_inactive_days. Filters: WHERE TO_CHAR(c.identified_date, 'YYYY-MM') = '2026-08' AND p.region = '华南'.

Output: `churn_level, users, avg_inactive_days`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.churn_level,COUNT(*) AS users,ROUND(AVG(c.inactive_days),2) AS avg_inactive_days FROM user_churn_events c JOIN user_profiles p ON c.user_id=p.user_id WHERE strftime(c.identified_date,'%Y-%m')='2026-08' AND p.region='华南' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.churn_level,
  COUNT(*) AS users,
  ROUND(CAST(AVG(c.inactive_days) AS DECIMAL), 2) AS avg_inactive_days
FROM user_churn_events AS c
JOIN user_profiles AS p
  ON c.user_id = p.user_id
WHERE
  TO_CHAR(c.identified_date, 'YYYY-MM') = '2026-08' AND p.region = '华南'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `eaf0b7fe4036af85866000ad00d8e5e36b067d0cc0309928b5be7dc980a70f58`

PostgreSQL SQL SHA256: `017f52277a39f98f1170319edbd88629395c9e9fded73c7fc5d3ac9ae3d56f7f`

## GROWTH_OPS-118

2026年8月华北各流失等级人数和平均未活跃天数；请返回流失等级、用户数、平均未活跃天数；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: churn_level, users, avg_inactive_days. Filters: WHERE TO_CHAR(c.identified_date, 'YYYY-MM') = '2026-08' AND p.region = '华北'.

Output: `churn_level, users, avg_inactive_days`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.churn_level,COUNT(*) AS users,ROUND(AVG(c.inactive_days),2) AS avg_inactive_days FROM user_churn_events c JOIN user_profiles p ON c.user_id=p.user_id WHERE strftime(c.identified_date,'%Y-%m')='2026-08' AND p.region='华北' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.churn_level,
  COUNT(*) AS users,
  ROUND(CAST(AVG(c.inactive_days) AS DECIMAL), 2) AS avg_inactive_days
FROM user_churn_events AS c
JOIN user_profiles AS p
  ON c.user_id = p.user_id
WHERE
  TO_CHAR(c.identified_date, 'YYYY-MM') = '2026-08' AND p.region = '华北'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `1202cda35cc90cb91991e8213193ac0df86f0c8ea45310d7111c7b462912a3b0`

PostgreSQL SQL SHA256: `780a757e83b8ab409884fcb8a9a841cacb009be10a2fd51f16140140801f714f`

## GROWTH_OPS-119

2026年8月西南各流失等级人数和平均未活跃天数；请返回流失等级、用户数、平均未活跃天数；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: churn_level, users, avg_inactive_days. Filters: WHERE TO_CHAR(c.identified_date, 'YYYY-MM') = '2026-08' AND p.region = '西南'.

Output: `churn_level, users, avg_inactive_days`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.churn_level,COUNT(*) AS users,ROUND(AVG(c.inactive_days),2) AS avg_inactive_days FROM user_churn_events c JOIN user_profiles p ON c.user_id=p.user_id WHERE strftime(c.identified_date,'%Y-%m')='2026-08' AND p.region='西南' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.churn_level,
  COUNT(*) AS users,
  ROUND(CAST(AVG(c.inactive_days) AS DECIMAL), 2) AS avg_inactive_days
FROM user_churn_events AS c
JOIN user_profiles AS p
  ON c.user_id = p.user_id
WHERE
  TO_CHAR(c.identified_date, 'YYYY-MM') = '2026-08' AND p.region = '西南'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `8e246f3fa446b8febb45d44b62f25a6dd442a08746627a7109e15e2356437e85`

PostgreSQL SQL SHA256: `e41b2ca6960f272fe25791b72c08cbad8bd758333d9283d2db781a520741e3fa`

## GROWTH_OPS-120

2026年8月华中各流失等级人数和平均未活跃天数；请返回流失等级、用户数、平均未活跃天数；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: churn_level, users, avg_inactive_days. Filters: WHERE TO_CHAR(c.identified_date, 'YYYY-MM') = '2026-08' AND p.region = '华中'.

Output: `churn_level, users, avg_inactive_days`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.churn_level,COUNT(*) AS users,ROUND(AVG(c.inactive_days),2) AS avg_inactive_days FROM user_churn_events c JOIN user_profiles p ON c.user_id=p.user_id WHERE strftime(c.identified_date,'%Y-%m')='2026-08' AND p.region='华中' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.churn_level,
  COUNT(*) AS users,
  ROUND(CAST(AVG(c.inactive_days) AS DECIMAL), 2) AS avg_inactive_days
FROM user_churn_events AS c
JOIN user_profiles AS p
  ON c.user_id = p.user_id
WHERE
  TO_CHAR(c.identified_date, 'YYYY-MM') = '2026-08' AND p.region = '华中'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `4ee09fb209c45764171cb92e4b497f9a772a4e3098ec94844386c97000048fb3`

PostgreSQL SQL SHA256: `bb2861ce94e997dcf71115c665f470762a5a75b71e72bc4b79e64101e936830a`

## GROWTH_OPS-121

按生命周期快照中的参与度评分，查询华东评分最高的前10名用户；请返回用户ID、参与度评分；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: user_id, engagement_score. Filters: WHERE p.region = '华东'.

Output: `user_id, engagement_score`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT l.user_id, l.engagement_score FROM user_lifecycle_snapshots l JOIN user_profiles p ON l.user_id=p.user_id WHERE p.region='华东' ORDER BY l.engagement_score DESC,l.user_id LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  l.user_id,
  l.engagement_score
FROM user_lifecycle_snapshots AS l
JOIN user_profiles AS p
  ON l.user_id = p.user_id
WHERE
  p.region = '华东'
ORDER BY
  l.engagement_score DESC NULLS LAST,
  l.user_id
LIMIT 10
```

Original SQL SHA256: `12f55a26ca9da28d21da7ba9cb50e2209cd87d53e8ac2c13dd6537a634de8635`

PostgreSQL SQL SHA256: `46e3387be9fcf0959f42499e99e87547c3ceab06438349ae0644ba45c66d2444`

## GROWTH_OPS-122

按生命周期快照中的参与度评分，查询华南评分最高的前10名用户；请返回用户ID、参与度评分；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: user_id, engagement_score. Filters: WHERE p.region = '华南'.

Output: `user_id, engagement_score`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT l.user_id, l.engagement_score FROM user_lifecycle_snapshots l JOIN user_profiles p ON l.user_id=p.user_id WHERE p.region='华南' ORDER BY l.engagement_score DESC,l.user_id LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  l.user_id,
  l.engagement_score
FROM user_lifecycle_snapshots AS l
JOIN user_profiles AS p
  ON l.user_id = p.user_id
WHERE
  p.region = '华南'
ORDER BY
  l.engagement_score DESC NULLS LAST,
  l.user_id
LIMIT 10
```

Original SQL SHA256: `b744a65e82db962be0a1a90706edb1d15e416b829ed92d9b9f74da7f1908ca29`

PostgreSQL SQL SHA256: `f06d8a14eeb73c8f6537de8bd748d28bdc224da1e65ed6af10fac142bc0c1e10`

## GROWTH_OPS-123

按生命周期快照中的参与度评分，查询华北评分最高的前10名用户；请返回用户ID、参与度评分；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: user_id, engagement_score. Filters: WHERE p.region = '华北'.

Output: `user_id, engagement_score`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT l.user_id, l.engagement_score FROM user_lifecycle_snapshots l JOIN user_profiles p ON l.user_id=p.user_id WHERE p.region='华北' ORDER BY l.engagement_score DESC,l.user_id LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  l.user_id,
  l.engagement_score
FROM user_lifecycle_snapshots AS l
JOIN user_profiles AS p
  ON l.user_id = p.user_id
WHERE
  p.region = '华北'
ORDER BY
  l.engagement_score DESC NULLS LAST,
  l.user_id
LIMIT 10
```

Original SQL SHA256: `283f82f0b80569928c8b7aa93e8813d55f118db0409549843f088c9e0f75b244`

PostgreSQL SQL SHA256: `ba72a5c9d8f398984c1723a53b60315c198c9f7b8e5a80fbd1a75f3cfc4bb578`

## GROWTH_OPS-124

按生命周期快照中的参与度评分，查询西南评分最高的前10名用户；请返回用户ID、参与度评分；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: user_id, engagement_score. Filters: WHERE p.region = '西南'.

Output: `user_id, engagement_score`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT l.user_id, l.engagement_score FROM user_lifecycle_snapshots l JOIN user_profiles p ON l.user_id=p.user_id WHERE p.region='西南' ORDER BY l.engagement_score DESC,l.user_id LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  l.user_id,
  l.engagement_score
FROM user_lifecycle_snapshots AS l
JOIN user_profiles AS p
  ON l.user_id = p.user_id
WHERE
  p.region = '西南'
ORDER BY
  l.engagement_score DESC NULLS LAST,
  l.user_id
LIMIT 10
```

Original SQL SHA256: `9d9682b3c15c3d433eb786d72a466bb0bb5d7cb272491363174b5c6c6580db11`

PostgreSQL SQL SHA256: `b8a70859184f5c7100b4743814d2443ee76bc64223196167907ff9dab030d119`

## GROWTH_OPS-127

in_app触达方式的送达率、点击率和召回率；请返回触达方式、触达数量、送达率、点击率、召回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: touch_channel, touches, delivery_rate, click_rate, recall_rate. Filters: WHERE t.touch_channel = 'in_app'.

Output: `touch_channel, touches, delivery_rate, click_rate, recall_rate`

Changes: `{"integer_truth_tests": [{"expression": "t.delivered", "table": "recall_touches", "column": "delivered", "physical_type": "bigint"}, {"expression": "t.clicked", "table": "recall_touches", "column": "clicked", "physical_type": "bigint"}, {"expression": "r.recalled", "table": "recall_results", "column": "recalled", "physical_type": "bigint"}], "round_numeric_cast_count": 3, "floating_division_count": 3, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT t.touch_channel, COUNT(*) AS touches, ROUND(SUM(CASE WHEN t.delivered THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS delivery_rate, ROUND(SUM(CASE WHEN t.clicked THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS click_rate, ROUND(SUM(CASE WHEN r.recalled THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS recall_rate FROM recall_touches t JOIN recall_results r ON t.touch_id=r.touch_id WHERE t.touch_channel='in_app' GROUP BY 1
```

Explicit PostgreSQL SQL:

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
  t.touch_channel = 'in_app'
GROUP BY
  1
```

Original SQL SHA256: `4539cb8ddadcaee0a2e27a628ae86929ca88480de7edf299eed70048dfadb91f`

PostgreSQL SQL SHA256: `4c04eec009fc521fd0b5b5ec9a49eb9bba1d5051def4e2c70b939c5b7bbee408`

## GROWTH_OPS-128

sms触达方式的送达率、点击率和召回率；请返回触达方式、触达数量、送达率、点击率、召回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: touch_channel, touches, delivery_rate, click_rate, recall_rate. Filters: WHERE t.touch_channel = 'sms'.

Output: `touch_channel, touches, delivery_rate, click_rate, recall_rate`

Changes: `{"integer_truth_tests": [{"expression": "t.delivered", "table": "recall_touches", "column": "delivered", "physical_type": "bigint"}, {"expression": "t.clicked", "table": "recall_touches", "column": "clicked", "physical_type": "bigint"}, {"expression": "r.recalled", "table": "recall_results", "column": "recalled", "physical_type": "bigint"}], "round_numeric_cast_count": 3, "floating_division_count": 3, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT t.touch_channel, COUNT(*) AS touches, ROUND(SUM(CASE WHEN t.delivered THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS delivery_rate, ROUND(SUM(CASE WHEN t.clicked THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS click_rate, ROUND(SUM(CASE WHEN r.recalled THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS recall_rate FROM recall_touches t JOIN recall_results r ON t.touch_id=r.touch_id WHERE t.touch_channel='sms' GROUP BY 1
```

Explicit PostgreSQL SQL:

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
  t.touch_channel = 'sms'
GROUP BY
  1
```

Original SQL SHA256: `0dd5c59add40635c6e747ed77f1e9aeed860791cc73efd1d621756ac9cc527f2`

PostgreSQL SQL SHA256: `90f6543cc242177c5ed6af2635ffec727901c62d9acd62a50bfa7c0cd0815137`

## GROWTH_OPS-129

请汇总push触达方式的送达率、点击率和召回率；请返回触达方式、触达数量、送达率、点击率、召回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: touch_channel, touches, delivery_rate, click_rate, recall_rate. Filters: WHERE t.touch_channel = 'push'.

Output: `touch_channel, touches, delivery_rate, click_rate, recall_rate`

Changes: `{"integer_truth_tests": [{"expression": "t.delivered", "table": "recall_touches", "column": "delivered", "physical_type": "bigint"}, {"expression": "t.clicked", "table": "recall_touches", "column": "clicked", "physical_type": "bigint"}, {"expression": "r.recalled", "table": "recall_results", "column": "recalled", "physical_type": "bigint"}], "round_numeric_cast_count": 3, "floating_division_count": 3, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT t.touch_channel, COUNT(*) AS touches, ROUND(SUM(CASE WHEN t.delivered THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS delivery_rate, ROUND(SUM(CASE WHEN t.clicked THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS click_rate, ROUND(SUM(CASE WHEN r.recalled THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS recall_rate FROM recall_touches t JOIN recall_results r ON t.touch_id=r.touch_id WHERE t.touch_channel='push' GROUP BY 1
```

Explicit PostgreSQL SQL:

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

Original SQL SHA256: `947d6f2d337250848e0ec337dc17930f12cc5d551b5a9745feffc4fe7db775c2`

PostgreSQL SQL SHA256: `168854483a56c8659545d00bfe59e05d93c63c31a68f4ee3aa05e3b3aef807be`

## GROWTH_OPS-130

请汇总in_app触达方式的送达率、点击率和召回率；请返回触达方式、触达数量、送达率、点击率、召回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: touch_channel, touches, delivery_rate, click_rate, recall_rate. Filters: WHERE t.touch_channel = 'in_app'.

Output: `touch_channel, touches, delivery_rate, click_rate, recall_rate`

Changes: `{"integer_truth_tests": [{"expression": "t.delivered", "table": "recall_touches", "column": "delivered", "physical_type": "bigint"}, {"expression": "t.clicked", "table": "recall_touches", "column": "clicked", "physical_type": "bigint"}, {"expression": "r.recalled", "table": "recall_results", "column": "recalled", "physical_type": "bigint"}], "round_numeric_cast_count": 3, "floating_division_count": 3, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT t.touch_channel, COUNT(*) AS touches, ROUND(SUM(CASE WHEN t.delivered THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS delivery_rate, ROUND(SUM(CASE WHEN t.clicked THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS click_rate, ROUND(SUM(CASE WHEN r.recalled THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS recall_rate FROM recall_touches t JOIN recall_results r ON t.touch_id=r.touch_id WHERE t.touch_channel='in_app' GROUP BY 1
```

Explicit PostgreSQL SQL:

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
  t.touch_channel = 'in_app'
GROUP BY
  1
```

Original SQL SHA256: `4539cb8ddadcaee0a2e27a628ae86929ca88480de7edf299eed70048dfadb91f`

PostgreSQL SQL SHA256: `4c04eec009fc521fd0b5b5ec9a49eb9bba1d5051def4e2c70b939c5b7bbee408`

## GROWTH_OPS-132

面向沉默14天的召回活动效果排名；请返回活动名称、触达数量、召回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: campaign_name, touches, recall_rate. Filters: WHERE c.target_segment = '沉默14天'.

Output: `campaign_name, touches, recall_rate`

Changes: `{"integer_truth_tests": [{"expression": "r.recalled", "table": "recall_results", "column": "recalled", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.campaign_name, COUNT(*) AS touches, ROUND(SUM(CASE WHEN r.recalled THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS recall_rate FROM recall_campaigns c JOIN recall_touches t ON c.recall_campaign_id=t.recall_campaign_id JOIN recall_results r ON t.touch_id=r.touch_id WHERE c.target_segment='沉默14天' GROUP BY 1 ORDER BY 3 DESC,1
```

Explicit PostgreSQL SQL:

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
  c.target_segment = '沉默14天'
GROUP BY
  1
ORDER BY
  3 DESC NULLS LAST,
  1
```

Original SQL SHA256: `87dc0ce3b8332ad995556882aac68afee5fd831ccf7fbb43a68dcdbcba6bc9c2`

PostgreSQL SQL SHA256: `7cb86ae5ca823fd916336083da765ade193c3ba904353121c3f3ba17e88b1dd4`

## GROWTH_OPS-133

面向流失30天的召回活动效果排名；请返回活动名称、触达数量、召回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: campaign_name, touches, recall_rate. Filters: WHERE c.target_segment = '流失30天'.

Output: `campaign_name, touches, recall_rate`

Changes: `{"integer_truth_tests": [{"expression": "r.recalled", "table": "recall_results", "column": "recalled", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.campaign_name, COUNT(*) AS touches, ROUND(SUM(CASE WHEN r.recalled THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS recall_rate FROM recall_campaigns c JOIN recall_touches t ON c.recall_campaign_id=t.recall_campaign_id JOIN recall_results r ON t.touch_id=r.touch_id WHERE c.target_segment='流失30天' GROUP BY 1 ORDER BY 3 DESC,1
```

Explicit PostgreSQL SQL:

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
  c.target_segment = '流失30天'
GROUP BY
  1
ORDER BY
  3 DESC NULLS LAST,
  1
```

Original SQL SHA256: `06d61002cc759e9e07eec3f79a5773de1a57968c4c3768ec2ca56c06defb8fbf`

PostgreSQL SQL SHA256: `fdda80fc87d45024560f36ad9c18ce084113b61f0126daa0351f80a95825d678`

## GROWTH_OPS-134

请汇总面向沉默7天的召回活动效果排名；请返回活动名称、触达数量、召回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: campaign_name, touches, recall_rate. Filters: WHERE c.target_segment = '沉默7天'.

Output: `campaign_name, touches, recall_rate`

Changes: `{"integer_truth_tests": [{"expression": "r.recalled", "table": "recall_results", "column": "recalled", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.campaign_name, COUNT(*) AS touches, ROUND(SUM(CASE WHEN r.recalled THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS recall_rate FROM recall_campaigns c JOIN recall_touches t ON c.recall_campaign_id=t.recall_campaign_id JOIN recall_results r ON t.touch_id=r.touch_id WHERE c.target_segment='沉默7天' GROUP BY 1 ORDER BY 3 DESC,1
```

Explicit PostgreSQL SQL:

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

Original SQL SHA256: `dd7aa1c8cec2dfce21e0f1e45c048d1de8262ef53bf55fb070cc72a0ab8fbb3d`

PostgreSQL SQL SHA256: `8095745b229570144801f827212fabf9822d534043e05f08b5d930fd6f06cb04`

## GROWTH_OPS-135

请汇总面向沉默14天的召回活动效果排名；请返回活动名称、触达数量、召回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: campaign_name, touches, recall_rate. Filters: WHERE c.target_segment = '沉默14天'.

Output: `campaign_name, touches, recall_rate`

Changes: `{"integer_truth_tests": [{"expression": "r.recalled", "table": "recall_results", "column": "recalled", "physical_type": "bigint"}], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.campaign_name, COUNT(*) AS touches, ROUND(SUM(CASE WHEN r.recalled THEN 1 ELSE 0 END)*1.0/COUNT(*),4) AS recall_rate FROM recall_campaigns c JOIN recall_touches t ON c.recall_campaign_id=t.recall_campaign_id JOIN recall_results r ON t.touch_id=r.touch_id WHERE c.target_segment='沉默14天' GROUP BY 1 ORDER BY 3 DESC,1
```

Explicit PostgreSQL SQL:

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
  c.target_segment = '沉默14天'
GROUP BY
  1
ORDER BY
  3 DESC NULLS LAST,
  1
```

Original SQL SHA256: `87dc0ce3b8332ad995556882aac68afee5fd831ccf7fbb43a68dcdbcba6bc9c2`

PostgreSQL SQL SHA256: `7cb86ae5ca823fd916336083da765ade193c3ba904353121c3f3ba17e88b1dd4`

## GROWTH_OPS-141

2026-01各渠道七日留存实际值与目标差距；请返回渠道名称、实际比率、七日留存目标、目标差距；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, actual_rate, day7_retention_target, gap. Filters: WHERE SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-01'; WHERE retention_day = 7 AND TO_CHAR(registration_date, 'YYYY-MM') = '2026-01'.

Output: `channel_name, actual_rate, day7_retention_target, gap`

Changes: `{"integer_truth_tests": [{"expression": "is_retained", "table": "user_retention", "column": "is_retained", "physical_type": "bigint"}], "round_numeric_cast_count": 2, "floating_division_count": 1, "month_format_count": 1, "substring_count": 1, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
WITH actual AS (SELECT channel_id, SUM(CASE WHEN is_retained THEN 1 ELSE 0 END)*1.0/COUNT(*) AS actual_rate FROM user_retention WHERE retention_day=7 AND strftime(registration_date,'%Y-%m')='2026-01' GROUP BY 1) SELECT c.channel_name,ROUND(a.actual_rate,4) AS actual_rate,t.day7_retention_target, ROUND(a.actual_rate-t.day7_retention_target,4) AS gap FROM growth_targets t JOIN acquisition_channels c ON t.channel_id=c.channel_id JOIN actual a ON t.channel_id=a.channel_id WHERE substr(t.target_month,1,7)='2026-01' ORDER BY gap DESC,1
```

Explicit PostgreSQL SQL:

```sql
WITH actual AS (
  SELECT
    channel_id,
    CAST(SUM(CASE WHEN is_retained <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS actual_rate
  FROM user_retention
  WHERE
    retention_day = 7 AND TO_CHAR(registration_date, 'YYYY-MM') = '2026-01'
  GROUP BY
    1
)
SELECT
  c.channel_name,
  ROUND(CAST(a.actual_rate AS DECIMAL), 4) AS actual_rate,
  t.day7_retention_target,
  ROUND(CAST(a.actual_rate - t.day7_retention_target AS DECIMAL), 4) AS gap
FROM growth_targets AS t
JOIN acquisition_channels AS c
  ON t.channel_id = c.channel_id
JOIN actual AS a
  ON t.channel_id = a.channel_id
WHERE
  SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-01'
ORDER BY
  gap DESC NULLS LAST,
  1
```

Original SQL SHA256: `9d56587899c7e7bddbcd7823ac3803c3426f28d932145c62e6761c91f63d32a0`

PostgreSQL SQL SHA256: `2248e1717c58dea7cdc73966c4dca35542ffc24abbd5f066fab18aadda0c57ab`

## GROWTH_OPS-142

2026-02各渠道七日留存实际值与目标差距；请返回渠道名称、实际比率、七日留存目标、目标差距；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, actual_rate, day7_retention_target, gap. Filters: WHERE SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-02'; WHERE retention_day = 7 AND TO_CHAR(registration_date, 'YYYY-MM') = '2026-02'.

Output: `channel_name, actual_rate, day7_retention_target, gap`

Changes: `{"integer_truth_tests": [{"expression": "is_retained", "table": "user_retention", "column": "is_retained", "physical_type": "bigint"}], "round_numeric_cast_count": 2, "floating_division_count": 1, "month_format_count": 1, "substring_count": 1, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
WITH actual AS (SELECT channel_id, SUM(CASE WHEN is_retained THEN 1 ELSE 0 END)*1.0/COUNT(*) AS actual_rate FROM user_retention WHERE retention_day=7 AND strftime(registration_date,'%Y-%m')='2026-02' GROUP BY 1) SELECT c.channel_name,ROUND(a.actual_rate,4) AS actual_rate,t.day7_retention_target, ROUND(a.actual_rate-t.day7_retention_target,4) AS gap FROM growth_targets t JOIN acquisition_channels c ON t.channel_id=c.channel_id JOIN actual a ON t.channel_id=a.channel_id WHERE substr(t.target_month,1,7)='2026-02' ORDER BY gap DESC,1
```

Explicit PostgreSQL SQL:

```sql
WITH actual AS (
  SELECT
    channel_id,
    CAST(SUM(CASE WHEN is_retained <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS actual_rate
  FROM user_retention
  WHERE
    retention_day = 7 AND TO_CHAR(registration_date, 'YYYY-MM') = '2026-02'
  GROUP BY
    1
)
SELECT
  c.channel_name,
  ROUND(CAST(a.actual_rate AS DECIMAL), 4) AS actual_rate,
  t.day7_retention_target,
  ROUND(CAST(a.actual_rate - t.day7_retention_target AS DECIMAL), 4) AS gap
FROM growth_targets AS t
JOIN acquisition_channels AS c
  ON t.channel_id = c.channel_id
JOIN actual AS a
  ON t.channel_id = a.channel_id
WHERE
  SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-02'
ORDER BY
  gap DESC NULLS LAST,
  1
```

Original SQL SHA256: `176312bcc79c9a26b98129605baafab607df4e4f41e17794cd1a47df4670a3e5`

PostgreSQL SQL SHA256: `fc9c436a1cb8dc3863ff90925707abe23b19aa65579328fd55a62e8ea4588e44`

## GROWTH_OPS-143

2026-03各渠道七日留存实际值与目标差距；请返回渠道名称、实际比率、七日留存目标、目标差距；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, actual_rate, day7_retention_target, gap. Filters: WHERE SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-03'; WHERE retention_day = 7 AND TO_CHAR(registration_date, 'YYYY-MM') = '2026-03'.

Output: `channel_name, actual_rate, day7_retention_target, gap`

Changes: `{"integer_truth_tests": [{"expression": "is_retained", "table": "user_retention", "column": "is_retained", "physical_type": "bigint"}], "round_numeric_cast_count": 2, "floating_division_count": 1, "month_format_count": 1, "substring_count": 1, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
WITH actual AS (SELECT channel_id, SUM(CASE WHEN is_retained THEN 1 ELSE 0 END)*1.0/COUNT(*) AS actual_rate FROM user_retention WHERE retention_day=7 AND strftime(registration_date,'%Y-%m')='2026-03' GROUP BY 1) SELECT c.channel_name,ROUND(a.actual_rate,4) AS actual_rate,t.day7_retention_target, ROUND(a.actual_rate-t.day7_retention_target,4) AS gap FROM growth_targets t JOIN acquisition_channels c ON t.channel_id=c.channel_id JOIN actual a ON t.channel_id=a.channel_id WHERE substr(t.target_month,1,7)='2026-03' ORDER BY gap DESC,1
```

Explicit PostgreSQL SQL:

```sql
WITH actual AS (
  SELECT
    channel_id,
    CAST(SUM(CASE WHEN is_retained <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS actual_rate
  FROM user_retention
  WHERE
    retention_day = 7 AND TO_CHAR(registration_date, 'YYYY-MM') = '2026-03'
  GROUP BY
    1
)
SELECT
  c.channel_name,
  ROUND(CAST(a.actual_rate AS DECIMAL), 4) AS actual_rate,
  t.day7_retention_target,
  ROUND(CAST(a.actual_rate - t.day7_retention_target AS DECIMAL), 4) AS gap
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

Original SQL SHA256: `1368bee88190a08655fc0ba4f0cb2542ba6b257e6bd89d3fa30d2b1ac501862e`

PostgreSQL SQL SHA256: `f706322d7ec28f32bdeaa61830032907213d7453de2e38e69c71b7bcb0615c2a`

## GROWTH_OPS-144

2026-04各渠道七日留存实际值与目标差距；请返回渠道名称、实际比率、七日留存目标、目标差距；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, actual_rate, day7_retention_target, gap. Filters: WHERE SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-04'; WHERE retention_day = 7 AND TO_CHAR(registration_date, 'YYYY-MM') = '2026-04'.

Output: `channel_name, actual_rate, day7_retention_target, gap`

Changes: `{"integer_truth_tests": [{"expression": "is_retained", "table": "user_retention", "column": "is_retained", "physical_type": "bigint"}], "round_numeric_cast_count": 2, "floating_division_count": 1, "month_format_count": 1, "substring_count": 1, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
WITH actual AS (SELECT channel_id, SUM(CASE WHEN is_retained THEN 1 ELSE 0 END)*1.0/COUNT(*) AS actual_rate FROM user_retention WHERE retention_day=7 AND strftime(registration_date,'%Y-%m')='2026-04' GROUP BY 1) SELECT c.channel_name,ROUND(a.actual_rate,4) AS actual_rate,t.day7_retention_target, ROUND(a.actual_rate-t.day7_retention_target,4) AS gap FROM growth_targets t JOIN acquisition_channels c ON t.channel_id=c.channel_id JOIN actual a ON t.channel_id=a.channel_id WHERE substr(t.target_month,1,7)='2026-04' ORDER BY gap DESC,1
```

Explicit PostgreSQL SQL:

```sql
WITH actual AS (
  SELECT
    channel_id,
    CAST(SUM(CASE WHEN is_retained <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS actual_rate
  FROM user_retention
  WHERE
    retention_day = 7 AND TO_CHAR(registration_date, 'YYYY-MM') = '2026-04'
  GROUP BY
    1
)
SELECT
  c.channel_name,
  ROUND(CAST(a.actual_rate AS DECIMAL), 4) AS actual_rate,
  t.day7_retention_target,
  ROUND(CAST(a.actual_rate - t.day7_retention_target AS DECIMAL), 4) AS gap
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

Original SQL SHA256: `bd130e5a21fa17c3ef6174c1ea800c6f29f9f7d6cef016d7b9e6a0f8824c6dd2`

PostgreSQL SQL SHA256: `1aa88f609996a218d0c2cea64aa4abdf8b147e307971c26b48df5623fc3a7f42`

## GROWTH_OPS-145

2026-05各渠道七日留存实际值与目标差距；请返回渠道名称、实际比率、七日留存目标、目标差距；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, actual_rate, day7_retention_target, gap. Filters: WHERE SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-05'; WHERE retention_day = 7 AND TO_CHAR(registration_date, 'YYYY-MM') = '2026-05'.

Output: `channel_name, actual_rate, day7_retention_target, gap`

Changes: `{"integer_truth_tests": [{"expression": "is_retained", "table": "user_retention", "column": "is_retained", "physical_type": "bigint"}], "round_numeric_cast_count": 2, "floating_division_count": 1, "month_format_count": 1, "substring_count": 1, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
WITH actual AS (SELECT channel_id, SUM(CASE WHEN is_retained THEN 1 ELSE 0 END)*1.0/COUNT(*) AS actual_rate FROM user_retention WHERE retention_day=7 AND strftime(registration_date,'%Y-%m')='2026-05' GROUP BY 1) SELECT c.channel_name,ROUND(a.actual_rate,4) AS actual_rate,t.day7_retention_target, ROUND(a.actual_rate-t.day7_retention_target,4) AS gap FROM growth_targets t JOIN acquisition_channels c ON t.channel_id=c.channel_id JOIN actual a ON t.channel_id=a.channel_id WHERE substr(t.target_month,1,7)='2026-05' ORDER BY gap DESC,1
```

Explicit PostgreSQL SQL:

```sql
WITH actual AS (
  SELECT
    channel_id,
    CAST(SUM(CASE WHEN is_retained <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS actual_rate
  FROM user_retention
  WHERE
    retention_day = 7 AND TO_CHAR(registration_date, 'YYYY-MM') = '2026-05'
  GROUP BY
    1
)
SELECT
  c.channel_name,
  ROUND(CAST(a.actual_rate AS DECIMAL), 4) AS actual_rate,
  t.day7_retention_target,
  ROUND(CAST(a.actual_rate - t.day7_retention_target AS DECIMAL), 4) AS gap
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

Original SQL SHA256: `d88a2179d74453dd7a95612f5cce3749d8ec57053e9d5dd076056ad4df2ca830`

PostgreSQL SQL SHA256: `09c3f8b152c8c82ed406be8a050bc273b1128abf82f77da1b9c1d807ba617c59`

## GROWTH_OPS-146

2026-01各渠道激活率实际值与目标差距；请返回渠道名称、实际比率、激活率目标、目标差距；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, actual_rate, activation_rate_target, gap. Filters: WHERE SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-01'; WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-01'.

Output: `channel_name, actual_rate, activation_rate_target, gap`

Changes: `{"integer_truth_tests": [{"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}], "round_numeric_cast_count": 2, "floating_division_count": 1, "month_format_count": 1, "substring_count": 1, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
WITH actual AS (SELECT r.channel_id, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/COUNT(*) AS actual_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id WHERE strftime(r.registered_at,'%Y-%m')='2026-01' GROUP BY 1) SELECT c.channel_name,ROUND(a.actual_rate,4) AS actual_rate,t.activation_rate_target, ROUND(a.actual_rate-t.activation_rate_target,4) AS gap FROM growth_targets t JOIN acquisition_channels c ON t.channel_id=c.channel_id JOIN actual a ON t.channel_id=a.channel_id WHERE substr(t.target_month,1,7)='2026-01' ORDER BY gap DESC,1
```

Explicit PostgreSQL SQL:

```sql
WITH actual AS (
  SELECT
    r.channel_id,
    CAST(SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS actual_rate
  FROM user_registrations AS r
  JOIN user_activations AS a
    ON r.registration_id = a.registration_id
  WHERE
    TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-01'
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
  SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-01'
ORDER BY
  gap DESC NULLS LAST,
  1
```

Original SQL SHA256: `1f07969c5cb67dbf365733a9725dd19cc380561828355e5900a6d8a7dfa256d8`

PostgreSQL SQL SHA256: `ea9de69ade9b23b5b12ae3bfd76fbbc06ca28bde463281b07c7c5144a2144160`

## GROWTH_OPS-147

2026-02各渠道激活率实际值与目标差距；请返回渠道名称、实际比率、激活率目标、目标差距；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, actual_rate, activation_rate_target, gap. Filters: WHERE SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-02'; WHERE TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-02'.

Output: `channel_name, actual_rate, activation_rate_target, gap`

Changes: `{"integer_truth_tests": [{"expression": "a.is_activated", "table": "user_activations", "column": "is_activated", "physical_type": "bigint"}], "round_numeric_cast_count": 2, "floating_division_count": 1, "month_format_count": 1, "substring_count": 1, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
WITH actual AS (SELECT r.channel_id, SUM(CASE WHEN a.is_activated THEN 1 ELSE 0 END)*1.0/COUNT(*) AS actual_rate FROM user_registrations r JOIN user_activations a ON r.registration_id=a.registration_id WHERE strftime(r.registered_at,'%Y-%m')='2026-02' GROUP BY 1) SELECT c.channel_name,ROUND(a.actual_rate,4) AS actual_rate,t.activation_rate_target, ROUND(a.actual_rate-t.activation_rate_target,4) AS gap FROM growth_targets t JOIN acquisition_channels c ON t.channel_id=c.channel_id JOIN actual a ON t.channel_id=a.channel_id WHERE substr(t.target_month,1,7)='2026-02' ORDER BY gap DESC,1
```

Explicit PostgreSQL SQL:

```sql
WITH actual AS (
  SELECT
    r.channel_id,
    CAST(SUM(CASE WHEN a.is_activated <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS actual_rate
  FROM user_registrations AS r
  JOIN user_activations AS a
    ON r.registration_id = a.registration_id
  WHERE
    TO_CHAR(r.registered_at, 'YYYY-MM') = '2026-02'
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
  SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-02'
ORDER BY
  gap DESC NULLS LAST,
  1
```

Original SQL SHA256: `a1ab48a951df6b878b2c33efc3ba4499799c2511460c4a43fc81e9a8959ab94c`

PostgreSQL SQL SHA256: `87de9feb15b77683dc60ccf0cf73ddf4dcae4d7b8f859f19b09d137fa4b52d6c`

## CHANNEL_OPS-007

搜索广告2026年各月广告消耗；请返回月份、广告消耗；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, spend. Filters: WHERE c.channel_name = '搜索广告'.

Output: `month, spend`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT strftime(s.stat_date,'%Y-%m') AS month,ROUND(SUM(s.spend),2) spend FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='搜索广告' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

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
  c.channel_name = '搜索广告'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `b51ff90764a4a80f1d5def34aab6d7dfb86fdf3b4b4ee7ed76843e72271ab034`

PostgreSQL SQL SHA256: `0a926f339af28237c86af075c5296029ad3c5dbeaa62cd7da679f0aa92d4d05b`

## CHANNEL_OPS-008

达人推广2026年各月广告消耗；请返回月份、广告消耗；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, spend. Filters: WHERE c.channel_name = '达人推广'.

Output: `month, spend`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT strftime(s.stat_date,'%Y-%m') AS month,ROUND(SUM(s.spend),2) spend FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='达人推广' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

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
  c.channel_name = '达人推广'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `6c03662cd15bd32622d1110f4450dbdcd26af8471def07bba86e922a40349445`

PostgreSQL SQL SHA256: `08d2f9fe287feba79a21a4107216a1190678e2f864727da196f499f7a96375e7`

## CHANNEL_OPS-009

品牌广告2026年各月广告消耗；请返回月份、广告消耗；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, spend. Filters: WHERE c.channel_name = '品牌广告'.

Output: `month, spend`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT strftime(s.stat_date,'%Y-%m') AS month,ROUND(SUM(s.spend),2) spend FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='品牌广告' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

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
  c.channel_name = '品牌广告'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `22fe125005b7aa2f26724a67bd920f63f38fb422c3db2fbf2c06a39b53789d69`

PostgreSQL SQL SHA256: `f48020f76d688e37bfa3f959f9be5bfdc5c1bd285f346842b9ec4d0ca4e7e317`

## CHANNEL_OPS-010

请汇总信息流广告2026年各月广告消耗；请返回月份、广告消耗；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, spend. Filters: WHERE c.channel_name = '信息流广告'.

Output: `month, spend`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT strftime(s.stat_date,'%Y-%m') AS month,ROUND(SUM(s.spend),2) spend FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='信息流广告' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

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

Original SQL SHA256: `9afc4becb7404ac020b8a4a1d1fabc40f8aa79b47b7bbec9ab547b71482b5293`

PostgreSQL SQL SHA256: `39c9f70c3aa8123b6c42370873b5daa2fd5aa41bcabc45038345508774cfbcc3`

## CHANNEL_OPS-011

2026-01各投放渠道消耗排名；请返回渠道名称、广告消耗；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, spend. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-01'.

Output: `channel_name, spend`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,ROUND(SUM(s.spend),2) spend FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE strftime(s.stat_date,'%Y-%m')='2026-01' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  ROUND(CAST(SUM(s.spend) AS DECIMAL), 2) AS spend
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
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `2493cffc4fbc15675f4a7b571c0934fd6431e1d3312d01d58dcb311aa3c08eb7`

PostgreSQL SQL SHA256: `e954e31ff41657cfdeee2ec742c93d0d7bba8b1c1a7bdff1e5064969b17ad6cd`

## CHANNEL_OPS-012

2026-02各投放渠道消耗排名；请返回渠道名称、广告消耗；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, spend. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-02'.

Output: `channel_name, spend`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,ROUND(SUM(s.spend),2) spend FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE strftime(s.stat_date,'%Y-%m')='2026-02' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  ROUND(CAST(SUM(s.spend) AS DECIMAL), 2) AS spend
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `f2f22cb8ca88e4e721fb71c179969dd3a913226e395b9cf5a92a17d413b6a538`

PostgreSQL SQL SHA256: `0f2f94993266afd0dc9794154319364272632639189acd44bdf272f18616b535`

## CHANNEL_OPS-013

2026-03各投放渠道消耗排名；请返回渠道名称、广告消耗；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, spend. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-03'.

Output: `channel_name, spend`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,ROUND(SUM(s.spend),2) spend FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE strftime(s.stat_date,'%Y-%m')='2026-03' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  ROUND(CAST(SUM(s.spend) AS DECIMAL), 2) AS spend
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `da338614a489bb3e81d8cc10ad3337840ccdfbe4a69d8799c2eb6e1b19bbc068`

PostgreSQL SQL SHA256: `81ab48cb93c9b94026d25529b342ccc207afa687cd1585c9495aa4bb6274035e`

## CHANNEL_OPS-014

2026-04各投放渠道消耗排名；请返回渠道名称、广告消耗；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, spend. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-04'.

Output: `channel_name, spend`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,ROUND(SUM(s.spend),2) spend FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE strftime(s.stat_date,'%Y-%m')='2026-04' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  ROUND(CAST(SUM(s.spend) AS DECIMAL), 2) AS spend
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `3c092c613a8195ed983ec3c89716c01e093d888dd3c70a50243e217205261e76`

PostgreSQL SQL SHA256: `2b50685328428bf5f992cacbe97da8267bd03ce3a0c1bfdfc7227998b8694dc5`

## CHANNEL_OPS-015

2026-05各投放渠道消耗排名；请返回渠道名称、广告消耗；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, spend. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-05'.

Output: `channel_name, spend`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,ROUND(SUM(s.spend),2) spend FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE strftime(s.stat_date,'%Y-%m')='2026-05' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  ROUND(CAST(SUM(s.spend) AS DECIMAL), 2) AS spend
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `51017efb46c7a51ded7735f9ebac3f8550f0dfe969f49a65fbe4ac47ba3cd820`

PostgreSQL SQL SHA256: `deb7d28e4db48bd0360354868892d0135d41e6f3c8af0fb42f03ff407b514e2b`

## CHANNEL_OPS-016

以注册为目标的计划消耗和计划数；请返回投放目标、活动数量、广告消耗；聚合口径：去重数量按对应实体唯一标识计数，可加总指标按当前查询粒度求和。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: objective, campaign_count, spend. Filters: WHERE p.objective = '注册'.

Output: `objective, campaign_count, spend`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.objective,COUNT(DISTINCT p.ad_campaign_id) campaign_count,ROUND(SUM(s.spend),2) spend FROM ad_campaigns p JOIN ad_daily_stats s ON p.ad_campaign_id=s.ad_campaign_id WHERE p.objective='注册' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.objective,
  COUNT(DISTINCT p.ad_campaign_id) AS campaign_count,
  ROUND(CAST(SUM(s.spend) AS DECIMAL), 2) AS spend
FROM ad_campaigns AS p
JOIN ad_daily_stats AS s
  ON p.ad_campaign_id = s.ad_campaign_id
WHERE
  p.objective = '注册'
GROUP BY
  1
```

Original SQL SHA256: `0fc9c68026ce4dd23a0ad5d03fe99b582ee043398c213a174c0c5f37c5378fc4`

PostgreSQL SQL SHA256: `45be5dba41618bda82586f6123f382d59bf9c152d38bbfa020b11eabc20aaa80`

## CHANNEL_OPS-017

以激活为目标的计划消耗和计划数；请返回投放目标、活动数量、广告消耗；聚合口径：去重数量按对应实体唯一标识计数，可加总指标按当前查询粒度求和。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: objective, campaign_count, spend. Filters: WHERE p.objective = '激活'.

Output: `objective, campaign_count, spend`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.objective,COUNT(DISTINCT p.ad_campaign_id) campaign_count,ROUND(SUM(s.spend),2) spend FROM ad_campaigns p JOIN ad_daily_stats s ON p.ad_campaign_id=s.ad_campaign_id WHERE p.objective='激活' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.objective,
  COUNT(DISTINCT p.ad_campaign_id) AS campaign_count,
  ROUND(CAST(SUM(s.spend) AS DECIMAL), 2) AS spend
FROM ad_campaigns AS p
JOIN ad_daily_stats AS s
  ON p.ad_campaign_id = s.ad_campaign_id
WHERE
  p.objective = '激活'
GROUP BY
  1
```

Original SQL SHA256: `322288b563de2a8705b07f67cebf5b34b0eb6adbabff80ac4ddd153662d26be2`

PostgreSQL SQL SHA256: `dde128cddc520052c2506d13fda8b6aa767ea0b31934cefe199a50a09abd92bc`

## CHANNEL_OPS-018

以七日留存为目标的计划消耗和计划数；请返回投放目标、活动数量、广告消耗；聚合口径：去重数量按对应实体唯一标识计数，可加总指标按当前查询粒度求和。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: objective, campaign_count, spend. Filters: WHERE p.objective = '七日留存'.

Output: `objective, campaign_count, spend`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.objective,COUNT(DISTINCT p.ad_campaign_id) campaign_count,ROUND(SUM(s.spend),2) spend FROM ad_campaigns p JOIN ad_daily_stats s ON p.ad_campaign_id=s.ad_campaign_id WHERE p.objective='七日留存' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.objective,
  COUNT(DISTINCT p.ad_campaign_id) AS campaign_count,
  ROUND(CAST(SUM(s.spend) AS DECIMAL), 2) AS spend
FROM ad_campaigns AS p
JOIN ad_daily_stats AS s
  ON p.ad_campaign_id = s.ad_campaign_id
WHERE
  p.objective = '七日留存'
GROUP BY
  1
```

Original SQL SHA256: `d3866336be32be9bd1934a86a75a9604d858c5f424487e4b79c889d5c9dc5dc3`

PostgreSQL SQL SHA256: `c085110f93cca6b1020eb53fb93e4d80a004b73dbd8221ca4d2f7ed1aec125c6`

## CHANNEL_OPS-019

请汇总以注册为目标的计划消耗和计划数；请返回投放目标、活动数量、广告消耗；聚合口径：去重数量按对应实体唯一标识计数，可加总指标按当前查询粒度求和。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: objective, campaign_count, spend. Filters: WHERE p.objective = '注册'.

Output: `objective, campaign_count, spend`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.objective,COUNT(DISTINCT p.ad_campaign_id) campaign_count,ROUND(SUM(s.spend),2) spend FROM ad_campaigns p JOIN ad_daily_stats s ON p.ad_campaign_id=s.ad_campaign_id WHERE p.objective='注册' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.objective,
  COUNT(DISTINCT p.ad_campaign_id) AS campaign_count,
  ROUND(CAST(SUM(s.spend) AS DECIMAL), 2) AS spend
FROM ad_campaigns AS p
JOIN ad_daily_stats AS s
  ON p.ad_campaign_id = s.ad_campaign_id
WHERE
  p.objective = '注册'
GROUP BY
  1
```

Original SQL SHA256: `0fc9c68026ce4dd23a0ad5d03fe99b582ee043398c213a174c0c5f37c5378fc4`

PostgreSQL SQL SHA256: `45be5dba41618bda82586f6123f382d59bf9c152d38bbfa020b11eabc20aaa80`

## CHANNEL_OPS-020

请汇总以激活为目标的计划消耗和计划数；请返回投放目标、活动数量、广告消耗；聚合口径：去重数量按对应实体唯一标识计数，可加总指标按当前查询粒度求和。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: objective, campaign_count, spend. Filters: WHERE p.objective = '激活'.

Output: `objective, campaign_count, spend`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.objective,COUNT(DISTINCT p.ad_campaign_id) campaign_count,ROUND(SUM(s.spend),2) spend FROM ad_campaigns p JOIN ad_daily_stats s ON p.ad_campaign_id=s.ad_campaign_id WHERE p.objective='激活' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.objective,
  COUNT(DISTINCT p.ad_campaign_id) AS campaign_count,
  ROUND(CAST(SUM(s.spend) AS DECIMAL), 2) AS spend
FROM ad_campaigns AS p
JOIN ad_daily_stats AS s
  ON p.ad_campaign_id = s.ad_campaign_id
WHERE
  p.objective = '激活'
GROUP BY
  1
```

Original SQL SHA256: `322288b563de2a8705b07f67cebf5b34b0eb6adbabff80ac4ddd153662d26be2`

PostgreSQL SQL SHA256: `dde128cddc520052c2506d13fda8b6aa767ea0b31934cefe199a50a09abd92bc`

## CHANNEL_OPS-021

截至2026-01各月广告消耗及环比变化；请返回月份、广告消耗、环比变化率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, spend, mom. Filters: WHERE TO_CHAR(stat_date, 'YYYY-MM') <= '2026-01'.

Output: `month, spend, mom`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 1, "month_format_count": 2, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 3}`

Original DuckDB SQL:

```sql
WITH m AS (SELECT strftime(stat_date,'%Y-%m') AS month,SUM(spend) spend FROM ad_daily_stats WHERE strftime(stat_date,'%Y-%m')<='2026-01' GROUP BY 1) SELECT month,ROUND(spend,2) spend,ROUND((spend-LAG(spend) OVER(ORDER BY month))/NULLIF(LAG(spend) OVER(ORDER BY month),0),4) mom FROM m ORDER BY month
```

Explicit PostgreSQL SQL:

```sql
WITH m AS (
  SELECT
    TO_CHAR(stat_date, 'YYYY-MM') AS month,
    SUM(spend) AS spend
  FROM ad_daily_stats
  WHERE
    TO_CHAR(stat_date, 'YYYY-MM') <= '2026-01'
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

Original SQL SHA256: `852dee3b7bbb59c69c737a880c9beab31631d69378c72094a7385d6fe49dbfad`

PostgreSQL SQL SHA256: `8bb9604ffd456aa5170848cad88b64ec581fb63925fc8261471c9fa16acc172e`

## CHANNEL_OPS-022

截至2026-02各月广告消耗及环比变化；请返回月份、广告消耗、环比变化率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, spend, mom. Filters: WHERE TO_CHAR(stat_date, 'YYYY-MM') <= '2026-02'.

Output: `month, spend, mom`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 1, "month_format_count": 2, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 3}`

Original DuckDB SQL:

```sql
WITH m AS (SELECT strftime(stat_date,'%Y-%m') AS month,SUM(spend) spend FROM ad_daily_stats WHERE strftime(stat_date,'%Y-%m')<='2026-02' GROUP BY 1) SELECT month,ROUND(spend,2) spend,ROUND((spend-LAG(spend) OVER(ORDER BY month))/NULLIF(LAG(spend) OVER(ORDER BY month),0),4) mom FROM m ORDER BY month
```

Explicit PostgreSQL SQL:

```sql
WITH m AS (
  SELECT
    TO_CHAR(stat_date, 'YYYY-MM') AS month,
    SUM(spend) AS spend
  FROM ad_daily_stats
  WHERE
    TO_CHAR(stat_date, 'YYYY-MM') <= '2026-02'
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

Original SQL SHA256: `04f464b60a544779ef89f1af4692d3d54b537af6ac08d037be9d4c16dc36e368`

PostgreSQL SQL SHA256: `eadf02d1aafe30e73a231ef95b75977e65e51a02fcdaee6d09169a19138662d3`

## CHANNEL_OPS-023

截至2026-03各月广告消耗及环比变化；请返回月份、广告消耗、环比变化率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, spend, mom. Filters: WHERE TO_CHAR(stat_date, 'YYYY-MM') <= '2026-03'.

Output: `month, spend, mom`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 1, "month_format_count": 2, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 3}`

Original DuckDB SQL:

```sql
WITH m AS (SELECT strftime(stat_date,'%Y-%m') AS month,SUM(spend) spend FROM ad_daily_stats WHERE strftime(stat_date,'%Y-%m')<='2026-03' GROUP BY 1) SELECT month,ROUND(spend,2) spend,ROUND((spend-LAG(spend) OVER(ORDER BY month))/NULLIF(LAG(spend) OVER(ORDER BY month),0),4) mom FROM m ORDER BY month
```

Explicit PostgreSQL SQL:

```sql
WITH m AS (
  SELECT
    TO_CHAR(stat_date, 'YYYY-MM') AS month,
    SUM(spend) AS spend
  FROM ad_daily_stats
  WHERE
    TO_CHAR(stat_date, 'YYYY-MM') <= '2026-03'
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

Original SQL SHA256: `27399d240d145613ec9b5bcbcfa92799811846ed67aab642fa4e9213611437a9`

PostgreSQL SQL SHA256: `58ca9b5d9c2a6abb0926ec39ef92c9b2edc7028fa6e274397329f14c19abfd38`

## CHANNEL_OPS-024

截至2026-04各月广告消耗及环比变化；请返回月份、广告消耗、环比变化率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, spend, mom. Filters: WHERE TO_CHAR(stat_date, 'YYYY-MM') <= '2026-04'.

Output: `month, spend, mom`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 1, "month_format_count": 2, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 3}`

Original DuckDB SQL:

```sql
WITH m AS (SELECT strftime(stat_date,'%Y-%m') AS month,SUM(spend) spend FROM ad_daily_stats WHERE strftime(stat_date,'%Y-%m')<='2026-04' GROUP BY 1) SELECT month,ROUND(spend,2) spend,ROUND((spend-LAG(spend) OVER(ORDER BY month))/NULLIF(LAG(spend) OVER(ORDER BY month),0),4) mom FROM m ORDER BY month
```

Explicit PostgreSQL SQL:

```sql
WITH m AS (
  SELECT
    TO_CHAR(stat_date, 'YYYY-MM') AS month,
    SUM(spend) AS spend
  FROM ad_daily_stats
  WHERE
    TO_CHAR(stat_date, 'YYYY-MM') <= '2026-04'
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

Original SQL SHA256: `ea525f837387679952d37e4c008742fcea17f290653b7c44aca59774ae012a8f`

PostgreSQL SQL SHA256: `1030e38b6faa0fd0397f00cd33350d22e9a8a6179a7c2eb11640082b5166488e`

## CHANNEL_OPS-027

2026-02各渠道曝光、点击和点击率；请返回渠道名称、曝光量、点击数、点击率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, impressions, clicks, ctr. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-02'.

Output: `channel_name, impressions, clicks, ctr`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,SUM(s.impressions) impressions,SUM(s.clicks) clicks, ROUND(SUM(s.clicks)*1.0/NULLIF(SUM(s.impressions),0),4) ctr FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE strftime(s.stat_date,'%Y-%m')='2026-02' GROUP BY 1 ORDER BY 4 DESC,1
```

Explicit PostgreSQL SQL:

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
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
```

Original SQL SHA256: `28fbf5052e243b8f157e721aff0fed850adeb40d58d8f2e6ca874a2c52ff7d36`

PostgreSQL SQL SHA256: `10a9be1d2fa8ae518b0ac52647804a6f947fa9eac06d7ee2f396135dc7b775f7`

## CHANNEL_OPS-028

2026-03各渠道曝光、点击和点击率；请返回渠道名称、曝光量、点击数、点击率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, impressions, clicks, ctr. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-03'.

Output: `channel_name, impressions, clicks, ctr`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,SUM(s.impressions) impressions,SUM(s.clicks) clicks, ROUND(SUM(s.clicks)*1.0/NULLIF(SUM(s.impressions),0),4) ctr FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE strftime(s.stat_date,'%Y-%m')='2026-03' GROUP BY 1 ORDER BY 4 DESC,1
```

Explicit PostgreSQL SQL:

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
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
```

Original SQL SHA256: `d7fa9cdf55981f479d59225e4811fc0c412e266d074d0bffe0f4ea24122e021e`

PostgreSQL SQL SHA256: `9b92b93e5ee6466b1a1f427f93f5a9e3df0248381df4f5002e838479e4aaec5b`

## CHANNEL_OPS-029

2026-04各渠道曝光、点击和点击率；请返回渠道名称、曝光量、点击数、点击率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, impressions, clicks, ctr. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-04'.

Output: `channel_name, impressions, clicks, ctr`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,SUM(s.impressions) impressions,SUM(s.clicks) clicks, ROUND(SUM(s.clicks)*1.0/NULLIF(SUM(s.impressions),0),4) ctr FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE strftime(s.stat_date,'%Y-%m')='2026-04' GROUP BY 1 ORDER BY 4 DESC,1
```

Explicit PostgreSQL SQL:

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
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
```

Original SQL SHA256: `38528f8d84209adee138f0a973d4a70a1defa4f0b1821eb0ebb252c404b3010d`

PostgreSQL SQL SHA256: `1672b738a83c54f2c6d6db4808588647bbc609bf6a494631f71596f01f3cbb41`

## CHANNEL_OPS-030

2026-05各渠道曝光、点击和点击率；请返回渠道名称、曝光量、点击数、点击率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, impressions, clicks, ctr. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-05'.

Output: `channel_name, impressions, clicks, ctr`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,SUM(s.impressions) impressions,SUM(s.clicks) clicks, ROUND(SUM(s.clicks)*1.0/NULLIF(SUM(s.impressions),0),4) ctr FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE strftime(s.stat_date,'%Y-%m')='2026-05' GROUP BY 1 ORDER BY 4 DESC,1
```

Explicit PostgreSQL SQL:

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
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
```

Original SQL SHA256: `48a21449a532314856e79cbef0de8211f85fb1f38d9ccc6b6c2d25d1a4580dc1`

PostgreSQL SQL SHA256: `79cae56fec5cfc2fc6d2b49c0385d9305f5659b777766c19d1b0d35c310950bd`

## CHANNEL_OPS-036

注册目标计划的整体点击率；请返回投放目标、曝光量、点击数、点击率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: objective, impressions, clicks, ctr. Filters: WHERE p.objective = '注册'.

Output: `objective, impressions, clicks, ctr`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.objective,SUM(s.impressions) impressions,SUM(s.clicks) clicks, ROUND(SUM(s.clicks)*1.0/NULLIF(SUM(s.impressions),0),4) ctr FROM ad_campaigns p JOIN ad_daily_stats s ON p.ad_campaign_id=s.ad_campaign_id WHERE p.objective='注册' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.objective,
  SUM(s.impressions) AS impressions,
  SUM(s.clicks) AS clicks,
  ROUND(
    CAST(CAST(SUM(s.clicks) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(s.impressions), 0) AS DECIMAL),
    4
  ) AS ctr
FROM ad_campaigns AS p
JOIN ad_daily_stats AS s
  ON p.ad_campaign_id = s.ad_campaign_id
WHERE
  p.objective = '注册'
GROUP BY
  1
```

Original SQL SHA256: `f019f16e99fb61f8b92edec8be20778f439bfc2cc5dcfcd3206035b41e8b88a9`

PostgreSQL SQL SHA256: `8a4559bf2e3218fab1e5c177bd759faede3b3be60b4b03d32b0faa3311fe9dfe`

## CHANNEL_OPS-037

激活目标计划的整体点击率；请返回投放目标、曝光量、点击数、点击率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: objective, impressions, clicks, ctr. Filters: WHERE p.objective = '激活'.

Output: `objective, impressions, clicks, ctr`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.objective,SUM(s.impressions) impressions,SUM(s.clicks) clicks, ROUND(SUM(s.clicks)*1.0/NULLIF(SUM(s.impressions),0),4) ctr FROM ad_campaigns p JOIN ad_daily_stats s ON p.ad_campaign_id=s.ad_campaign_id WHERE p.objective='激活' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.objective,
  SUM(s.impressions) AS impressions,
  SUM(s.clicks) AS clicks,
  ROUND(
    CAST(CAST(SUM(s.clicks) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(s.impressions), 0) AS DECIMAL),
    4
  ) AS ctr
FROM ad_campaigns AS p
JOIN ad_daily_stats AS s
  ON p.ad_campaign_id = s.ad_campaign_id
WHERE
  p.objective = '激活'
GROUP BY
  1
```

Original SQL SHA256: `03a0fff1ca232e597c694dbc0792c3ff7e08039094babfc670afbd4b7bed336b`

PostgreSQL SQL SHA256: `9f871d4875c56b501f5df720154590b3578e1434575e579b464be19194e00712`

## CHANNEL_OPS-038

七日留存目标计划的整体点击率；请返回投放目标、曝光量、点击数、点击率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: objective, impressions, clicks, ctr. Filters: WHERE p.objective = '七日留存'.

Output: `objective, impressions, clicks, ctr`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.objective,SUM(s.impressions) impressions,SUM(s.clicks) clicks, ROUND(SUM(s.clicks)*1.0/NULLIF(SUM(s.impressions),0),4) ctr FROM ad_campaigns p JOIN ad_daily_stats s ON p.ad_campaign_id=s.ad_campaign_id WHERE p.objective='七日留存' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.objective,
  SUM(s.impressions) AS impressions,
  SUM(s.clicks) AS clicks,
  ROUND(
    CAST(CAST(SUM(s.clicks) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(s.impressions), 0) AS DECIMAL),
    4
  ) AS ctr
FROM ad_campaigns AS p
JOIN ad_daily_stats AS s
  ON p.ad_campaign_id = s.ad_campaign_id
WHERE
  p.objective = '七日留存'
GROUP BY
  1
```

Original SQL SHA256: `3d34039bfc836d6908a77848c6820f5a7290a0f57e8b0c00d541abb598d07930`

PostgreSQL SQL SHA256: `0a0cbd4e0d5282bff2659495976953149fe0a641dfb3c09a79e918fc83884520`

## CHANNEL_OPS-039

请汇总注册目标计划的整体点击率；请返回投放目标、曝光量、点击数、点击率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: objective, impressions, clicks, ctr. Filters: WHERE p.objective = '注册'.

Output: `objective, impressions, clicks, ctr`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.objective,SUM(s.impressions) impressions,SUM(s.clicks) clicks, ROUND(SUM(s.clicks)*1.0/NULLIF(SUM(s.impressions),0),4) ctr FROM ad_campaigns p JOIN ad_daily_stats s ON p.ad_campaign_id=s.ad_campaign_id WHERE p.objective='注册' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.objective,
  SUM(s.impressions) AS impressions,
  SUM(s.clicks) AS clicks,
  ROUND(
    CAST(CAST(SUM(s.clicks) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(s.impressions), 0) AS DECIMAL),
    4
  ) AS ctr
FROM ad_campaigns AS p
JOIN ad_daily_stats AS s
  ON p.ad_campaign_id = s.ad_campaign_id
WHERE
  p.objective = '注册'
GROUP BY
  1
```

Original SQL SHA256: `f019f16e99fb61f8b92edec8be20778f439bfc2cc5dcfcd3206035b41e8b88a9`

PostgreSQL SQL SHA256: `8a4559bf2e3218fab1e5c177bd759faede3b3be60b4b03d32b0faa3311fe9dfe`

## CHANNEL_OPS-040

请汇总激活目标计划的整体点击率；请返回投放目标、曝光量、点击数、点击率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: objective, impressions, clicks, ctr. Filters: WHERE p.objective = '激活'.

Output: `objective, impressions, clicks, ctr`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.objective,SUM(s.impressions) impressions,SUM(s.clicks) clicks, ROUND(SUM(s.clicks)*1.0/NULLIF(SUM(s.impressions),0),4) ctr FROM ad_campaigns p JOIN ad_daily_stats s ON p.ad_campaign_id=s.ad_campaign_id WHERE p.objective='激活' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.objective,
  SUM(s.impressions) AS impressions,
  SUM(s.clicks) AS clicks,
  ROUND(
    CAST(CAST(SUM(s.clicks) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(s.impressions), 0) AS DECIMAL),
    4
  ) AS ctr
FROM ad_campaigns AS p
JOIN ad_daily_stats AS s
  ON p.ad_campaign_id = s.ad_campaign_id
WHERE
  p.objective = '激活'
GROUP BY
  1
```

Original SQL SHA256: `03a0fff1ca232e597c694dbc0792c3ff7e08039094babfc670afbd4b7bed336b`

PostgreSQL SQL SHA256: `9f871d4875c56b501f5df720154590b3578e1434575e579b464be19194e00712`

## CHANNEL_OPS-041

2026-01点击率最高的前10个广告计划；请返回广告计划名称、曝光量、点击数、点击率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: ad_campaign_name, impressions, clicks, ctr. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-01'.

Output: `ad_campaign_name, impressions, clicks, ctr`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.ad_campaign_name,SUM(s.impressions) impressions,SUM(s.clicks) clicks, ROUND(SUM(s.clicks)*1.0/NULLIF(SUM(s.impressions),0),4) ctr FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id WHERE strftime(s.stat_date,'%Y-%m')='2026-01' GROUP BY 1 ORDER BY 4 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.ad_campaign_name,
  SUM(s.impressions) AS impressions,
  SUM(s.clicks) AS clicks,
  ROUND(
    CAST(CAST(SUM(s.clicks) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(s.impressions), 0) AS DECIMAL),
    4
  ) AS ctr
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
WHERE
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `2ed05e051b05200f8624ac98855bf48c838a4df8202154dfce087040e237897e`

PostgreSQL SQL SHA256: `8590c4cf66ee7d3633bc99cfa5b924c8583b2f6cf61b954a26e2795204d15159`

## CHANNEL_OPS-042

2026-02点击率最高的前10个广告计划；请返回广告计划名称、曝光量、点击数、点击率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: ad_campaign_name, impressions, clicks, ctr. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-02'.

Output: `ad_campaign_name, impressions, clicks, ctr`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.ad_campaign_name,SUM(s.impressions) impressions,SUM(s.clicks) clicks, ROUND(SUM(s.clicks)*1.0/NULLIF(SUM(s.impressions),0),4) ctr FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id WHERE strftime(s.stat_date,'%Y-%m')='2026-02' GROUP BY 1 ORDER BY 4 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.ad_campaign_name,
  SUM(s.impressions) AS impressions,
  SUM(s.clicks) AS clicks,
  ROUND(
    CAST(CAST(SUM(s.clicks) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(s.impressions), 0) AS DECIMAL),
    4
  ) AS ctr
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
WHERE
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `c419b65ff28566ad3c9156f8327e5d05e86899102b217882c01d80043aec20cf`

PostgreSQL SQL SHA256: `916a43a25f49032eeaf2a46623620b053e3716e33676f8029bb0e230b3e1255f`

## CHANNEL_OPS-043

2026-03点击率最高的前10个广告计划；请返回广告计划名称、曝光量、点击数、点击率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: ad_campaign_name, impressions, clicks, ctr. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-03'.

Output: `ad_campaign_name, impressions, clicks, ctr`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.ad_campaign_name,SUM(s.impressions) impressions,SUM(s.clicks) clicks, ROUND(SUM(s.clicks)*1.0/NULLIF(SUM(s.impressions),0),4) ctr FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id WHERE strftime(s.stat_date,'%Y-%m')='2026-03' GROUP BY 1 ORDER BY 4 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.ad_campaign_name,
  SUM(s.impressions) AS impressions,
  SUM(s.clicks) AS clicks,
  ROUND(
    CAST(CAST(SUM(s.clicks) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(s.impressions), 0) AS DECIMAL),
    4
  ) AS ctr
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
WHERE
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `d68eb5406f7bce64b26482ee669ad059003e44ee685232fcc210e7ed33598884`

PostgreSQL SQL SHA256: `d995bcf181c7af5b4cc8265d74cb4e654e1347ab325a8426f7701ed35f079e46`

## CHANNEL_OPS-044

2026-04点击率最高的前10个广告计划；请返回广告计划名称、曝光量、点击数、点击率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: ad_campaign_name, impressions, clicks, ctr. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-04'.

Output: `ad_campaign_name, impressions, clicks, ctr`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.ad_campaign_name,SUM(s.impressions) impressions,SUM(s.clicks) clicks, ROUND(SUM(s.clicks)*1.0/NULLIF(SUM(s.impressions),0),4) ctr FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id WHERE strftime(s.stat_date,'%Y-%m')='2026-04' GROUP BY 1 ORDER BY 4 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.ad_campaign_name,
  SUM(s.impressions) AS impressions,
  SUM(s.clicks) AS clicks,
  ROUND(
    CAST(CAST(SUM(s.clicks) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(s.impressions), 0) AS DECIMAL),
    4
  ) AS ctr
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
WHERE
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `db19d7799856c44bc4583adf2bb40ba78107dba9eca3693c1da179328f5c431e`

PostgreSQL SQL SHA256: `69d4a15f99f08f748bc191dfbf4f09441a8270169decaf438ff7301c44ad8d53`

## CHANNEL_OPS-045

2026-05点击率最高的前10个广告计划；请返回广告计划名称、曝光量、点击数、点击率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: ad_campaign_name, impressions, clicks, ctr. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-05'.

Output: `ad_campaign_name, impressions, clicks, ctr`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 1, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.ad_campaign_name,SUM(s.impressions) impressions,SUM(s.clicks) clicks, ROUND(SUM(s.clicks)*1.0/NULLIF(SUM(s.impressions),0),4) ctr FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id WHERE strftime(s.stat_date,'%Y-%m')='2026-05' GROUP BY 1 ORDER BY 4 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.ad_campaign_name,
  SUM(s.impressions) AS impressions,
  SUM(s.clicks) AS clicks,
  ROUND(
    CAST(CAST(SUM(s.clicks) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(s.impressions), 0) AS DECIMAL),
    4
  ) AS ctr
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
WHERE
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  4 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `59cb81ef0e732c4b8043d8b6dd17fd80dfba088ed473ff592c3de0ed701f61a6`

PostgreSQL SQL SHA256: `c2bc1eb11ac1050d65a805fe9dd46bd8ab5daeade00903e216e304316bf5018d`

## CHANNEL_OPS-046

信息流广告的平均点击成本；请返回渠道名称、平均点击成本；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, cpc. Filters: WHERE c.channel_name = '信息流广告'.

Output: `channel_name, cpc`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,ROUND(SUM(s.spend)/NULLIF(SUM(s.clicks),0),4) cpc FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='信息流广告' GROUP BY 1
```

Explicit PostgreSQL SQL:

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

Original SQL SHA256: `0a14343b01eaf15f5b3e7e18cf7b4e98cf98e8989dd9a83a27ee953f44f5a2e7`

PostgreSQL SQL SHA256: `90932c3f1ac15ef559cb05437ee5225cd80a3411fdc940b2d01f57e6eb22d9ef`

## CHANNEL_OPS-047

搜索广告的平均点击成本；请返回渠道名称、平均点击成本；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, cpc. Filters: WHERE c.channel_name = '搜索广告'.

Output: `channel_name, cpc`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,ROUND(SUM(s.spend)/NULLIF(SUM(s.clicks),0),4) cpc FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='搜索广告' GROUP BY 1
```

Explicit PostgreSQL SQL:

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
  c.channel_name = '搜索广告'
GROUP BY
  1
```

Original SQL SHA256: `d2e1d179ca669dfa750976449dc197e8b4f78cf80b503f07c767e31511d0779e`

PostgreSQL SQL SHA256: `cfb2a93e65c5837b2119efa9a1ed663a2ea5b7cb60ef999df4d7d0845e6ac332`

## CHANNEL_OPS-048

达人推广的平均点击成本；请返回渠道名称、平均点击成本；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, cpc. Filters: WHERE c.channel_name = '达人推广'.

Output: `channel_name, cpc`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,ROUND(SUM(s.spend)/NULLIF(SUM(s.clicks),0),4) cpc FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='达人推广' GROUP BY 1
```

Explicit PostgreSQL SQL:

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
  c.channel_name = '达人推广'
GROUP BY
  1
```

Original SQL SHA256: `398a3c3bf0349afef93cec590065bb35e4503f0da43c13f613bd0f63fe211312`

PostgreSQL SQL SHA256: `405b11c2ad4d7d05c88471c224ddf2166e49dfa89a1401aef1194f85a567ded5`

## CHANNEL_OPS-049

品牌广告的平均点击成本；请返回渠道名称、平均点击成本；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, cpc. Filters: WHERE c.channel_name = '品牌广告'.

Output: `channel_name, cpc`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,ROUND(SUM(s.spend)/NULLIF(SUM(s.clicks),0),4) cpc FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='品牌广告' GROUP BY 1
```

Explicit PostgreSQL SQL:

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
  c.channel_name = '品牌广告'
GROUP BY
  1
```

Original SQL SHA256: `b5eb5d20f4e11eadb6366426cd551eb7e725590c4db400d5cb7a59822de1fad1`

PostgreSQL SQL SHA256: `75b4bddf26743bc646d46004d83ca8295d2baaeaa0b6188912b09c025992cb10`

## CHANNEL_OPS-052

2026-02各渠道转化数、转化率和CPA；请返回渠道名称、转化数、转化率、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, conversions, conversion_rate, cpa. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-02'.

Output: `channel_name, conversions, conversion_rate, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 2, "month_format_count": 1, "substring_count": 0, "nullif_count": 2, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,SUM(s.conversions) conversions, ROUND(SUM(s.conversions)*1.0/NULLIF(SUM(s.clicks),0),4) conversion_rate, ROUND(SUM(s.spend)/NULLIF(SUM(s.conversions),0),2) cpa FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE strftime(s.stat_date,'%Y-%m')='2026-02' GROUP BY 1 ORDER BY 4,1
```

Explicit PostgreSQL SQL:

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
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  4,
  1
```

Original SQL SHA256: `3c554937ba232c997b525ab4067f322b838e0a1954a12f113257dc85b1af3459`

PostgreSQL SQL SHA256: `1db08d844e3718acc6d755594eca81507e4cfc25d26495c45cef7347e23cbc2e`

## CHANNEL_OPS-053

2026-03各渠道转化数、转化率和CPA；请返回渠道名称、转化数、转化率、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, conversions, conversion_rate, cpa. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-03'.

Output: `channel_name, conversions, conversion_rate, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 2, "month_format_count": 1, "substring_count": 0, "nullif_count": 2, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,SUM(s.conversions) conversions, ROUND(SUM(s.conversions)*1.0/NULLIF(SUM(s.clicks),0),4) conversion_rate, ROUND(SUM(s.spend)/NULLIF(SUM(s.conversions),0),2) cpa FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE strftime(s.stat_date,'%Y-%m')='2026-03' GROUP BY 1 ORDER BY 4,1
```

Explicit PostgreSQL SQL:

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
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  4,
  1
```

Original SQL SHA256: `e1f5cee97d82da5f768f56d4d9b613a3edc9eb88ca270ddf4012c47d9b71ba4a`

PostgreSQL SQL SHA256: `2f53353848bc8bb8b7e831cf8c314d71efc89b7779b81bcb537831625fe35414`

## CHANNEL_OPS-054

2026-04各渠道转化数、转化率和CPA；请返回渠道名称、转化数、转化率、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, conversions, conversion_rate, cpa. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-04'.

Output: `channel_name, conversions, conversion_rate, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 2, "month_format_count": 1, "substring_count": 0, "nullif_count": 2, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,SUM(s.conversions) conversions, ROUND(SUM(s.conversions)*1.0/NULLIF(SUM(s.clicks),0),4) conversion_rate, ROUND(SUM(s.spend)/NULLIF(SUM(s.conversions),0),2) cpa FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE strftime(s.stat_date,'%Y-%m')='2026-04' GROUP BY 1 ORDER BY 4,1
```

Explicit PostgreSQL SQL:

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
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  4,
  1
```

Original SQL SHA256: `400c2c5aac0cf51a1a1c3bbce1f96e1488edfff4e2515520e0e5b30eb922526a`

PostgreSQL SQL SHA256: `ca987bdb0ddc25c2df4ef090447a197a2e87beed7df1cc9ce453b89c7c0a2858`

## CHANNEL_OPS-055

2026-05各渠道转化数、转化率和CPA；请返回渠道名称、转化数、转化率、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, conversions, conversion_rate, cpa. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-05'.

Output: `channel_name, conversions, conversion_rate, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 2, "month_format_count": 1, "substring_count": 0, "nullif_count": 2, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,SUM(s.conversions) conversions, ROUND(SUM(s.conversions)*1.0/NULLIF(SUM(s.clicks),0),4) conversion_rate, ROUND(SUM(s.spend)/NULLIF(SUM(s.conversions),0),2) cpa FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE strftime(s.stat_date,'%Y-%m')='2026-05' GROUP BY 1 ORDER BY 4,1
```

Explicit PostgreSQL SQL:

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
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  4,
  1
```

Original SQL SHA256: `71cd58e80ed45338585655d6c66cc3501d13b2cca6478496a8d39d95aa352802`

PostgreSQL SQL SHA256: `64b0ea6a09e00cbb1e1a4efe1947c5dbf8d489da17c3fced1bf2705a22c1fbf4`

## CHANNEL_OPS-056

信息流广告CPA最低的前10个计划；请返回广告计划名称、转化数、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从低到高展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: ad_campaign_name, conversions, cpa. Filters: WHERE c.channel_name = '信息流广告'.

Output: `ad_campaign_name, conversions, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.ad_campaign_name,SUM(s.conversions) conversions,ROUND(SUM(s.spend)/NULLIF(SUM(s.conversions),0),2) cpa FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='信息流广告' GROUP BY 1 HAVING SUM(s.conversions)>0 ORDER BY 3,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.ad_campaign_name,
  SUM(s.conversions) AS conversions,
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
  c.channel_name = '信息流广告'
GROUP BY
  1
HAVING
  SUM(s.conversions) > 0
ORDER BY
  3,
  1
LIMIT 10
```

Original SQL SHA256: `896c3f124e37a728fd4ff03954aa65c65512c3b21b72df368f4b4d129c864970`

PostgreSQL SQL SHA256: `420b67dc486522a5147bc6769f5a18e6ab94eff7ba3df0889d9019874b1ed463`

## CHANNEL_OPS-057

搜索广告CPA最低的前10个计划；请返回广告计划名称、转化数、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从低到高展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: ad_campaign_name, conversions, cpa. Filters: WHERE c.channel_name = '搜索广告'.

Output: `ad_campaign_name, conversions, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.ad_campaign_name,SUM(s.conversions) conversions,ROUND(SUM(s.spend)/NULLIF(SUM(s.conversions),0),2) cpa FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='搜索广告' GROUP BY 1 HAVING SUM(s.conversions)>0 ORDER BY 3,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.ad_campaign_name,
  SUM(s.conversions) AS conversions,
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
  c.channel_name = '搜索广告'
GROUP BY
  1
HAVING
  SUM(s.conversions) > 0
ORDER BY
  3,
  1
LIMIT 10
```

Original SQL SHA256: `711fb38eb8e90c9d0a780f957477c61db6263c904d0d36015b0d50a0c76e6b5d`

PostgreSQL SQL SHA256: `a140b49680700dc6881438ac84fc115b83b29d7709b8fc9bf55b90937b46fda4`

## CHANNEL_OPS-058

达人推广CPA最低的前10个计划；请返回广告计划名称、转化数、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从低到高展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: ad_campaign_name, conversions, cpa. Filters: WHERE c.channel_name = '达人推广'.

Output: `ad_campaign_name, conversions, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.ad_campaign_name,SUM(s.conversions) conversions,ROUND(SUM(s.spend)/NULLIF(SUM(s.conversions),0),2) cpa FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='达人推广' GROUP BY 1 HAVING SUM(s.conversions)>0 ORDER BY 3,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.ad_campaign_name,
  SUM(s.conversions) AS conversions,
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
  c.channel_name = '达人推广'
GROUP BY
  1
HAVING
  SUM(s.conversions) > 0
ORDER BY
  3,
  1
LIMIT 10
```

Original SQL SHA256: `1300460efed8fc6dba224ad1b8b03bcfb3c46d4b68bcad3949e8f7e07b82160b`

PostgreSQL SQL SHA256: `71923e7180f463d7ffa7817cd1e2a2299c4249c5a8c51dfef8b8009090753cf9`

## CHANNEL_OPS-059

品牌广告CPA最低的前10个计划；请返回广告计划名称、转化数、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从低到高展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: ad_campaign_name, conversions, cpa. Filters: WHERE c.channel_name = '品牌广告'.

Output: `ad_campaign_name, conversions, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.ad_campaign_name,SUM(s.conversions) conversions,ROUND(SUM(s.spend)/NULLIF(SUM(s.conversions),0),2) cpa FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='品牌广告' GROUP BY 1 HAVING SUM(s.conversions)>0 ORDER BY 3,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.ad_campaign_name,
  SUM(s.conversions) AS conversions,
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
  c.channel_name = '品牌广告'
GROUP BY
  1
HAVING
  SUM(s.conversions) > 0
ORDER BY
  3,
  1
LIMIT 10
```

Original SQL SHA256: `b76035d72067fbd74128e6ae98dc6ed09b931d40e44b3bbbc264d388bd87e2b7`

PostgreSQL SQL SHA256: `22dcfcc79f06dc429b032a1ee620be26ea416fd472ef77b28e587268d9ab53be`

## CHANNEL_OPS-060

请汇总信息流广告CPA最低的前10个计划；请返回广告计划名称、转化数、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按核心指标从低到高展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: ad_campaign_name, conversions, cpa. Filters: WHERE c.channel_name = '信息流广告'.

Output: `ad_campaign_name, conversions, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.ad_campaign_name,SUM(s.conversions) conversions,ROUND(SUM(s.spend)/NULLIF(SUM(s.conversions),0),2) cpa FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='信息流广告' GROUP BY 1 HAVING SUM(s.conversions)>0 ORDER BY 3,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.ad_campaign_name,
  SUM(s.conversions) AS conversions,
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
  c.channel_name = '信息流广告'
GROUP BY
  1
HAVING
  SUM(s.conversions) > 0
ORDER BY
  3,
  1
LIMIT 10
```

Original SQL SHA256: `896c3f124e37a728fd4ff03954aa65c65512c3b21b72df368f4b4d129c864970`

PostgreSQL SQL SHA256: `420b67dc486522a5147bc6769f5a18e6ab94eff7ba3df0889d9019874b1ed463`

## CHANNEL_OPS-061

注册目标计划的平均CPA；请返回投放目标、转化数、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: objective, conversions, cpa. Filters: WHERE p.objective = '注册'.

Output: `objective, conversions, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.objective,SUM(s.conversions) conversions,ROUND(SUM(s.spend)/NULLIF(SUM(s.conversions),0),2) cpa FROM ad_campaigns p JOIN ad_daily_stats s ON p.ad_campaign_id=s.ad_campaign_id WHERE p.objective='注册' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.objective,
  SUM(s.conversions) AS conversions,
  ROUND(
    CAST(CAST(SUM(s.spend) AS DOUBLE PRECISION) / NULLIF(SUM(s.conversions), 0) AS DECIMAL),
    2
  ) AS cpa
FROM ad_campaigns AS p
JOIN ad_daily_stats AS s
  ON p.ad_campaign_id = s.ad_campaign_id
WHERE
  p.objective = '注册'
GROUP BY
  1
```

Original SQL SHA256: `844becd4ec21fe3c2d322df5bccffeefc420a1b328b00d471b045fd979ecd672`

PostgreSQL SQL SHA256: `f2e58dc004bfb17b9f5d8ad29436f646cf7448a132ae51a86f782cfaf5341d06`

## CHANNEL_OPS-062

激活目标计划的平均CPA；请返回投放目标、转化数、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: objective, conversions, cpa. Filters: WHERE p.objective = '激活'.

Output: `objective, conversions, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.objective,SUM(s.conversions) conversions,ROUND(SUM(s.spend)/NULLIF(SUM(s.conversions),0),2) cpa FROM ad_campaigns p JOIN ad_daily_stats s ON p.ad_campaign_id=s.ad_campaign_id WHERE p.objective='激活' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.objective,
  SUM(s.conversions) AS conversions,
  ROUND(
    CAST(CAST(SUM(s.spend) AS DOUBLE PRECISION) / NULLIF(SUM(s.conversions), 0) AS DECIMAL),
    2
  ) AS cpa
FROM ad_campaigns AS p
JOIN ad_daily_stats AS s
  ON p.ad_campaign_id = s.ad_campaign_id
WHERE
  p.objective = '激活'
GROUP BY
  1
```

Original SQL SHA256: `9bcac2a765153131a449b051075140ec18db2eabf4e777c3744c6a955b9ba493`

PostgreSQL SQL SHA256: `0ba02b4d99f5cf74f4e1bb63b10accd273376b41e625c944feed29778d0740fc`

## CHANNEL_OPS-063

七日留存目标计划的平均CPA；请返回投放目标、转化数、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: objective, conversions, cpa. Filters: WHERE p.objective = '七日留存'.

Output: `objective, conversions, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.objective,SUM(s.conversions) conversions,ROUND(SUM(s.spend)/NULLIF(SUM(s.conversions),0),2) cpa FROM ad_campaigns p JOIN ad_daily_stats s ON p.ad_campaign_id=s.ad_campaign_id WHERE p.objective='七日留存' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.objective,
  SUM(s.conversions) AS conversions,
  ROUND(
    CAST(CAST(SUM(s.spend) AS DOUBLE PRECISION) / NULLIF(SUM(s.conversions), 0) AS DECIMAL),
    2
  ) AS cpa
FROM ad_campaigns AS p
JOIN ad_daily_stats AS s
  ON p.ad_campaign_id = s.ad_campaign_id
WHERE
  p.objective = '七日留存'
GROUP BY
  1
```

Original SQL SHA256: `b58410623610011ba6fb3d8aa0e91968adfcf56f8d4063a85a91ef5110813578`

PostgreSQL SQL SHA256: `fb75d1f88d474d3f51e6196f8c1013ea12705299147a8dee0f5b2fef0138838f`

## CHANNEL_OPS-064

请汇总注册目标计划的平均CPA；请返回投放目标、转化数、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: objective, conversions, cpa. Filters: WHERE p.objective = '注册'.

Output: `objective, conversions, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.objective,SUM(s.conversions) conversions,ROUND(SUM(s.spend)/NULLIF(SUM(s.conversions),0),2) cpa FROM ad_campaigns p JOIN ad_daily_stats s ON p.ad_campaign_id=s.ad_campaign_id WHERE p.objective='注册' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.objective,
  SUM(s.conversions) AS conversions,
  ROUND(
    CAST(CAST(SUM(s.spend) AS DOUBLE PRECISION) / NULLIF(SUM(s.conversions), 0) AS DECIMAL),
    2
  ) AS cpa
FROM ad_campaigns AS p
JOIN ad_daily_stats AS s
  ON p.ad_campaign_id = s.ad_campaign_id
WHERE
  p.objective = '注册'
GROUP BY
  1
```

Original SQL SHA256: `844becd4ec21fe3c2d322df5bccffeefc420a1b328b00d471b045fd979ecd672`

PostgreSQL SQL SHA256: `f2e58dc004bfb17b9f5d8ad29436f646cf7448a132ae51a86f782cfaf5341d06`

## CHANNEL_OPS-065

请汇总激活目标计划的平均CPA；请返回投放目标、转化数、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: objective, conversions, cpa. Filters: WHERE p.objective = '激活'.

Output: `objective, conversions, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT p.objective,SUM(s.conversions) conversions,ROUND(SUM(s.spend)/NULLIF(SUM(s.conversions),0),2) cpa FROM ad_campaigns p JOIN ad_daily_stats s ON p.ad_campaign_id=s.ad_campaign_id WHERE p.objective='激活' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.objective,
  SUM(s.conversions) AS conversions,
  ROUND(
    CAST(CAST(SUM(s.spend) AS DOUBLE PRECISION) / NULLIF(SUM(s.conversions), 0) AS DECIMAL),
    2
  ) AS cpa
FROM ad_campaigns AS p
JOIN ad_daily_stats AS s
  ON p.ad_campaign_id = s.ad_campaign_id
WHERE
  p.objective = '激活'
GROUP BY
  1
```

Original SQL SHA256: `9bcac2a765153131a449b051075140ec18db2eabf4e777c3744c6a955b9ba493`

PostgreSQL SQL SHA256: `0ba02b4d99f5cf74f4e1bb63b10accd273376b41e625c944feed29778d0740fc`

## CHANNEL_OPS-071

查询截至2026-01（包含该月）的每月整体CPA，CPA按总消耗除以总转化数计算；请返回月份、转化数、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, conversions, cpa. Filters: WHERE TO_CHAR(stat_date, 'YYYY-MM') <= '2026-01'.

Output: `month, conversions, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 2, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT strftime(stat_date,'%Y-%m') AS month,SUM(conversions) conversions, ROUND(SUM(spend)/NULLIF(SUM(conversions),0),2) cpa FROM ad_daily_stats WHERE strftime(stat_date,'%Y-%m')<='2026-01' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  TO_CHAR(stat_date, 'YYYY-MM') AS month,
  SUM(conversions) AS conversions,
  ROUND(
    CAST(CAST(SUM(spend) AS DOUBLE PRECISION) / NULLIF(SUM(conversions), 0) AS DECIMAL),
    2
  ) AS cpa
FROM ad_daily_stats
WHERE
  TO_CHAR(stat_date, 'YYYY-MM') <= '2026-01'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `5ed33e62e7149239dc05fb02ab81f254fefa6a055795a8192cba7fe9386b05a6`

PostgreSQL SQL SHA256: `40114c66bd594fc5061f10a7b48d99cd3fc9a0336b367cdf745248ad8401b90c`

## CHANNEL_OPS-072

查询截至2026-02（包含该月）的每月整体CPA，CPA按总消耗除以总转化数计算；请返回月份、转化数、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, conversions, cpa. Filters: WHERE TO_CHAR(stat_date, 'YYYY-MM') <= '2026-02'.

Output: `month, conversions, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 2, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT strftime(stat_date,'%Y-%m') AS month,SUM(conversions) conversions, ROUND(SUM(spend)/NULLIF(SUM(conversions),0),2) cpa FROM ad_daily_stats WHERE strftime(stat_date,'%Y-%m')<='2026-02' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  TO_CHAR(stat_date, 'YYYY-MM') AS month,
  SUM(conversions) AS conversions,
  ROUND(
    CAST(CAST(SUM(spend) AS DOUBLE PRECISION) / NULLIF(SUM(conversions), 0) AS DECIMAL),
    2
  ) AS cpa
FROM ad_daily_stats
WHERE
  TO_CHAR(stat_date, 'YYYY-MM') <= '2026-02'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `353fe63e7a6d74265df19599572b5f52e14ea886d1e5b8c3e744245ec81d3462`

PostgreSQL SQL SHA256: `cf591963647e15156fcdabcf7998f43f1c68d3e3e2382745806840417463e5af`

## CHANNEL_OPS-073

查询截至2026-03（包含该月）的每月整体CPA，CPA按总消耗除以总转化数计算；请返回月份、转化数、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, conversions, cpa. Filters: WHERE TO_CHAR(stat_date, 'YYYY-MM') <= '2026-03'.

Output: `month, conversions, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 2, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT strftime(stat_date,'%Y-%m') AS month,SUM(conversions) conversions, ROUND(SUM(spend)/NULLIF(SUM(conversions),0),2) cpa FROM ad_daily_stats WHERE strftime(stat_date,'%Y-%m')<='2026-03' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  TO_CHAR(stat_date, 'YYYY-MM') AS month,
  SUM(conversions) AS conversions,
  ROUND(
    CAST(CAST(SUM(spend) AS DOUBLE PRECISION) / NULLIF(SUM(conversions), 0) AS DECIMAL),
    2
  ) AS cpa
FROM ad_daily_stats
WHERE
  TO_CHAR(stat_date, 'YYYY-MM') <= '2026-03'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `d0b8aa138c5cd12487494924b777044a43fff06b7c46090f879a2169730f5313`

PostgreSQL SQL SHA256: `40464a9ca504dc0e76c63b4d5dd52b10248ad9e07a0d8a5bfa104e6ae2896e2a`

## CHANNEL_OPS-074

查询截至2026-04（包含该月）的每月整体CPA，CPA按总消耗除以总转化数计算；请返回月份、转化数、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, conversions, cpa. Filters: WHERE TO_CHAR(stat_date, 'YYYY-MM') <= '2026-04'.

Output: `month, conversions, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 2, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT strftime(stat_date,'%Y-%m') AS month,SUM(conversions) conversions, ROUND(SUM(spend)/NULLIF(SUM(conversions),0),2) cpa FROM ad_daily_stats WHERE strftime(stat_date,'%Y-%m')<='2026-04' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  TO_CHAR(stat_date, 'YYYY-MM') AS month,
  SUM(conversions) AS conversions,
  ROUND(
    CAST(CAST(SUM(spend) AS DOUBLE PRECISION) / NULLIF(SUM(conversions), 0) AS DECIMAL),
    2
  ) AS cpa
FROM ad_daily_stats
WHERE
  TO_CHAR(stat_date, 'YYYY-MM') <= '2026-04'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `b3c354ed13b1f7aa2fe830e0d1f804e7535d99d2771d9c8a056eda36538227b6`

PostgreSQL SQL SHA256: `a5215b09995637cd8d4d501d3d301cbdfef5ffe495ce4571af517fbd7c429307`

## CHANNEL_OPS-075

查询截至2026-05（包含该月）的每月整体CPA，CPA按总消耗除以总转化数计算；请返回月份、转化数、CPA；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: month, conversions, cpa. Filters: WHERE TO_CHAR(stat_date, 'YYYY-MM') <= '2026-05'.

Output: `month, conversions, cpa`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 2, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT strftime(stat_date,'%Y-%m') AS month,SUM(conversions) conversions, ROUND(SUM(spend)/NULLIF(SUM(conversions),0),2) cpa FROM ad_daily_stats WHERE strftime(stat_date,'%Y-%m')<='2026-05' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  TO_CHAR(stat_date, 'YYYY-MM') AS month,
  SUM(conversions) AS conversions,
  ROUND(
    CAST(CAST(SUM(spend) AS DOUBLE PRECISION) / NULLIF(SUM(conversions), 0) AS DECIMAL),
    2
  ) AS cpa
FROM ad_daily_stats
WHERE
  TO_CHAR(stat_date, 'YYYY-MM') <= '2026-05'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `54f911e22ab2d2236c60bcc1d9380abcc1b98f70d07eb13ea9cb9ea1aad32b5a`

PostgreSQL SQL SHA256: `3174ba35e993327180c28d50d0411aba43b3697b596ac753d47c69c307af16ba`

## CHANNEL_OPS-081

2026-01各广告账户消耗和转化排名；请返回广告账户名称、广告消耗、转化数；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: account_name, spend, conversions. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-01'.

Output: `account_name, spend, conversions`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT a.account_name,ROUND(SUM(s.spend),2) spend,SUM(s.conversions) conversions FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN ad_accounts a ON p.ad_account_id=a.ad_account_id WHERE strftime(s.stat_date,'%Y-%m')='2026-01' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  a.account_name,
  ROUND(CAST(SUM(s.spend) AS DECIMAL), 2) AS spend,
  SUM(s.conversions) AS conversions
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
JOIN ad_accounts AS a
  ON p.ad_account_id = a.ad_account_id
WHERE
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `44e76074bb3ccb20daa48f005767323578edcb6b8a7bb848e78c76ab5884dd2c`

PostgreSQL SQL SHA256: `5d8b27270855555ad52c73bfb5c17fa7237d783304d59190c4933b48facec0fd`

## CHANNEL_OPS-082

2026-02各广告账户消耗和转化排名；请返回广告账户名称、广告消耗、转化数；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: account_name, spend, conversions. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-02'.

Output: `account_name, spend, conversions`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT a.account_name,ROUND(SUM(s.spend),2) spend,SUM(s.conversions) conversions FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN ad_accounts a ON p.ad_account_id=a.ad_account_id WHERE strftime(s.stat_date,'%Y-%m')='2026-02' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  a.account_name,
  ROUND(CAST(SUM(s.spend) AS DECIMAL), 2) AS spend,
  SUM(s.conversions) AS conversions
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
JOIN ad_accounts AS a
  ON p.ad_account_id = a.ad_account_id
WHERE
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `a62db5984ec8f296ea4dfa08e1de5759a0e175fac885cb2659eda4b7789a8536`

PostgreSQL SQL SHA256: `4d211e3757f691f25dd6555fae3c18f9c1bc21294558c18e05e57b8509953d93`

## CHANNEL_OPS-083

2026-03各广告账户消耗和转化排名；请返回广告账户名称、广告消耗、转化数；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: account_name, spend, conversions. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-03'.

Output: `account_name, spend, conversions`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT a.account_name,ROUND(SUM(s.spend),2) spend,SUM(s.conversions) conversions FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN ad_accounts a ON p.ad_account_id=a.ad_account_id WHERE strftime(s.stat_date,'%Y-%m')='2026-03' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  a.account_name,
  ROUND(CAST(SUM(s.spend) AS DECIMAL), 2) AS spend,
  SUM(s.conversions) AS conversions
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
JOIN ad_accounts AS a
  ON p.ad_account_id = a.ad_account_id
WHERE
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `a204801383d4096ff673af407cfa1a4279746cae9b93e441c0f5cb1b2560e129`

PostgreSQL SQL SHA256: `170356012dfb913c8839fa59f99e8c4fed0783fad5c8d895ef5b25de87895d64`

## CHANNEL_OPS-084

2026-04各广告账户消耗和转化排名；请返回广告账户名称、广告消耗、转化数；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: account_name, spend, conversions. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-04'.

Output: `account_name, spend, conversions`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT a.account_name,ROUND(SUM(s.spend),2) spend,SUM(s.conversions) conversions FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN ad_accounts a ON p.ad_account_id=a.ad_account_id WHERE strftime(s.stat_date,'%Y-%m')='2026-04' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  a.account_name,
  ROUND(CAST(SUM(s.spend) AS DECIMAL), 2) AS spend,
  SUM(s.conversions) AS conversions
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
JOIN ad_accounts AS a
  ON p.ad_account_id = a.ad_account_id
WHERE
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `cf6ce2dbfae616bb7ea674d06b2d9da8c809abf3cb02ec2ab5825d5981c07870`

PostgreSQL SQL SHA256: `aa2633b2210e2dcd511f43123183f9e6d7625c1f5c3127183ed4f108d94f368d`

## CHANNEL_OPS-085

2026-05各广告账户消耗和转化排名；请返回广告账户名称、广告消耗、转化数；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: account_name, spend, conversions. Filters: WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-05'.

Output: `account_name, spend, conversions`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT a.account_name,ROUND(SUM(s.spend),2) spend,SUM(s.conversions) conversions FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id JOIN ad_accounts a ON p.ad_account_id=a.ad_account_id WHERE strftime(s.stat_date,'%Y-%m')='2026-05' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  a.account_name,
  ROUND(CAST(SUM(s.spend) AS DECIMAL), 2) AS spend,
  SUM(s.conversions) AS conversions
FROM ad_daily_stats AS s
JOIN ad_campaigns AS p
  ON s.ad_campaign_id = p.ad_campaign_id
JOIN ad_accounts AS a
  ON p.ad_account_id = a.ad_account_id
WHERE
  TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `1ac1ca320b8bb11e028dab51c1b60a60600131f1708284e54cca81db996202d0`

PostgreSQL SQL SHA256: `a714e610088bb257c446186304956db79ef15d767acf5d6cac75098a5d44d0ff`

## CHANNEL_OPS-086

列出信息流广告预算最高的10个广告计划；请返回广告计划名称、预算、状态；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: ad_campaign_name, budget, status. Filters: WHERE c.channel_name = '信息流广告'.

Output: `ad_campaign_name, budget, status`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.ad_campaign_name,p.budget,p.status FROM ad_campaigns p JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='信息流广告' ORDER BY p.budget DESC,p.ad_campaign_name LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.ad_campaign_name,
  p.budget,
  p.status
FROM ad_campaigns AS p
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  c.channel_name = '信息流广告'
ORDER BY
  p.budget DESC NULLS LAST,
  p.ad_campaign_name
LIMIT 10
```

Original SQL SHA256: `740971329f674a749863e04f987498e752e085ccc6c3af5d5041a948c6eb987d`

PostgreSQL SQL SHA256: `292a3c150d05a908e55205dabec91b0ec01db960418ee6bba7c87a36b488bb07`

## CHANNEL_OPS-087

列出搜索广告预算最高的10个广告计划；请返回广告计划名称、预算、状态；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: ad_campaign_name, budget, status. Filters: WHERE c.channel_name = '搜索广告'.

Output: `ad_campaign_name, budget, status`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.ad_campaign_name,p.budget,p.status FROM ad_campaigns p JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='搜索广告' ORDER BY p.budget DESC,p.ad_campaign_name LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.ad_campaign_name,
  p.budget,
  p.status
FROM ad_campaigns AS p
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  c.channel_name = '搜索广告'
ORDER BY
  p.budget DESC NULLS LAST,
  p.ad_campaign_name
LIMIT 10
```

Original SQL SHA256: `dc47b92e2114e049a6f7b3d2beec673a8a49d1f3616d9c3ba938a1b2252fdce7`

PostgreSQL SQL SHA256: `06966aaffd51894574d1899dbfec21dd31c56e6881d6ee18a3b797d88ef6f88e`

## CHANNEL_OPS-088

列出达人推广预算最高的10个广告计划；请返回广告计划名称、预算、状态；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: ad_campaign_name, budget, status. Filters: WHERE c.channel_name = '达人推广'.

Output: `ad_campaign_name, budget, status`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.ad_campaign_name,p.budget,p.status FROM ad_campaigns p JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='达人推广' ORDER BY p.budget DESC,p.ad_campaign_name LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.ad_campaign_name,
  p.budget,
  p.status
FROM ad_campaigns AS p
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  c.channel_name = '达人推广'
ORDER BY
  p.budget DESC NULLS LAST,
  p.ad_campaign_name
LIMIT 10
```

Original SQL SHA256: `3de55e95cc9992b1aa4d4ceee97e7e2b5934d8df42d0a8bfe6df5fc3cac8ba2b`

PostgreSQL SQL SHA256: `c93f425474118789ada0967ab808b2983af736110fa1e397a96a976627242b33`

## CHANNEL_OPS-089

列出品牌广告预算最高的10个广告计划；请返回广告计划名称、预算、状态；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: ad_campaign_name, budget, status. Filters: WHERE c.channel_name = '品牌广告'.

Output: `ad_campaign_name, budget, status`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.ad_campaign_name,p.budget,p.status FROM ad_campaigns p JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='品牌广告' ORDER BY p.budget DESC,p.ad_campaign_name LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.ad_campaign_name,
  p.budget,
  p.status
FROM ad_campaigns AS p
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  c.channel_name = '品牌广告'
ORDER BY
  p.budget DESC NULLS LAST,
  p.ad_campaign_name
LIMIT 10
```

Original SQL SHA256: `82a5ff0de13c9e366a0dc262be1356c59a2b507ec3d5250483c3260290ab011c`

PostgreSQL SQL SHA256: `fd7a34a190b3d0c4de629b71073c37523a4498cf5cef02c5afefecc4b286ac00`

## CHANNEL_OPS-090

请汇总列出信息流广告预算最高的10个广告计划；请返回广告计划名称、预算、状态；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: ad_campaign_name, budget, status. Filters: WHERE c.channel_name = '信息流广告'.

Output: `ad_campaign_name, budget, status`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT p.ad_campaign_name,p.budget,p.status FROM ad_campaigns p JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='信息流广告' ORDER BY p.budget DESC,p.ad_campaign_name LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  p.ad_campaign_name,
  p.budget,
  p.status
FROM ad_campaigns AS p
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  c.channel_name = '信息流广告'
ORDER BY
  p.budget DESC NULLS LAST,
  p.ad_campaign_name
LIMIT 10
```

Original SQL SHA256: `740971329f674a749863e04f987498e752e085ccc6c3af5d5041a948c6eb987d`

PostgreSQL SQL SHA256: `292a3c150d05a908e55205dabec91b0ec01db960418ee6bba7c87a36b488bb07`

## CHANNEL_OPS-091

2026-01新开始和结束的广告计划数；请返回开始计划数、结束计划数；聚合口径：可加总指标按当前查询粒度求和。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: started_campaigns, ended_campaigns. Filters: none.

Output: `started_campaigns, ended_campaigns`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 2, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT SUM(CASE WHEN strftime(start_date,'%Y-%m')='2026-01' THEN 1 ELSE 0 END) started_campaigns, SUM(CASE WHEN strftime(end_date,'%Y-%m')='2026-01' THEN 1 ELSE 0 END) ended_campaigns FROM ad_campaigns
```

Explicit PostgreSQL SQL:

```sql
SELECT
  SUM(CASE WHEN TO_CHAR(start_date, 'YYYY-MM') = '2026-01' THEN 1 ELSE 0 END) AS started_campaigns,
  SUM(CASE WHEN TO_CHAR(end_date, 'YYYY-MM') = '2026-01' THEN 1 ELSE 0 END) AS ended_campaigns
FROM ad_campaigns
```

Original SQL SHA256: `91df1e54dbf3726adde6e7934228c5a3d70762c3a5c33944375ca240686521a5`

PostgreSQL SQL SHA256: `e49d64c27118328d110aca94c443f14e979bb459d3570c54a626abeb7343e7d5`

## CHANNEL_OPS-092

2026-02新开始和结束的广告计划数；请返回开始计划数、结束计划数；聚合口径：可加总指标按当前查询粒度求和。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: started_campaigns, ended_campaigns. Filters: none.

Output: `started_campaigns, ended_campaigns`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 2, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT SUM(CASE WHEN strftime(start_date,'%Y-%m')='2026-02' THEN 1 ELSE 0 END) started_campaigns, SUM(CASE WHEN strftime(end_date,'%Y-%m')='2026-02' THEN 1 ELSE 0 END) ended_campaigns FROM ad_campaigns
```

Explicit PostgreSQL SQL:

```sql
SELECT
  SUM(CASE WHEN TO_CHAR(start_date, 'YYYY-MM') = '2026-02' THEN 1 ELSE 0 END) AS started_campaigns,
  SUM(CASE WHEN TO_CHAR(end_date, 'YYYY-MM') = '2026-02' THEN 1 ELSE 0 END) AS ended_campaigns
FROM ad_campaigns
```

Original SQL SHA256: `d263cb9893d78e908fd0617be1358912eda1659f74f514269ace71e620b24c33`

PostgreSQL SQL SHA256: `8c6063a6f57728ed73c349483cf857d3fa19f1df0dbb14d857b1ac9796c541ec`

## CHANNEL_OPS-093

2026-03新开始和结束的广告计划数；请返回开始计划数、结束计划数；聚合口径：可加总指标按当前查询粒度求和。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: started_campaigns, ended_campaigns. Filters: none.

Output: `started_campaigns, ended_campaigns`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 2, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT SUM(CASE WHEN strftime(start_date,'%Y-%m')='2026-03' THEN 1 ELSE 0 END) started_campaigns, SUM(CASE WHEN strftime(end_date,'%Y-%m')='2026-03' THEN 1 ELSE 0 END) ended_campaigns FROM ad_campaigns
```

Explicit PostgreSQL SQL:

```sql
SELECT
  SUM(CASE WHEN TO_CHAR(start_date, 'YYYY-MM') = '2026-03' THEN 1 ELSE 0 END) AS started_campaigns,
  SUM(CASE WHEN TO_CHAR(end_date, 'YYYY-MM') = '2026-03' THEN 1 ELSE 0 END) AS ended_campaigns
FROM ad_campaigns
```

Original SQL SHA256: `3d39b490e3bb02e26e211e304b00f991a1128c56f4611a57e3f126c30ce094a7`

PostgreSQL SQL SHA256: `a5c7e6b99cf12c46bd2094430cd87c60d4964a67fb71037c53c59b4a00f26e57`

## CHANNEL_OPS-094

2026-04新开始和结束的广告计划数；请返回开始计划数、结束计划数；聚合口径：可加总指标按当前查询粒度求和。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: started_campaigns, ended_campaigns. Filters: none.

Output: `started_campaigns, ended_campaigns`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 2, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT SUM(CASE WHEN strftime(start_date,'%Y-%m')='2026-04' THEN 1 ELSE 0 END) started_campaigns, SUM(CASE WHEN strftime(end_date,'%Y-%m')='2026-04' THEN 1 ELSE 0 END) ended_campaigns FROM ad_campaigns
```

Explicit PostgreSQL SQL:

```sql
SELECT
  SUM(CASE WHEN TO_CHAR(start_date, 'YYYY-MM') = '2026-04' THEN 1 ELSE 0 END) AS started_campaigns,
  SUM(CASE WHEN TO_CHAR(end_date, 'YYYY-MM') = '2026-04' THEN 1 ELSE 0 END) AS ended_campaigns
FROM ad_campaigns
```

Original SQL SHA256: `b23d1875771b78af9734fdc468cbb51267a6909ce594f8b354388f27a32e100a`

PostgreSQL SQL SHA256: `ab75a1886c92d5a818fbfc6f548144b48190bf9382db67fc3856d9c416ce17db`

## CHANNEL_OPS-095

2026-05新开始和结束的广告计划数；请返回开始计划数、结束计划数；聚合口径：可加总指标按当前查询粒度求和。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: started_campaigns, ended_campaigns. Filters: none.

Output: `started_campaigns, ended_campaigns`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 2, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT SUM(CASE WHEN strftime(start_date,'%Y-%m')='2026-05' THEN 1 ELSE 0 END) started_campaigns, SUM(CASE WHEN strftime(end_date,'%Y-%m')='2026-05' THEN 1 ELSE 0 END) ended_campaigns FROM ad_campaigns
```

Explicit PostgreSQL SQL:

```sql
SELECT
  SUM(CASE WHEN TO_CHAR(start_date, 'YYYY-MM') = '2026-05' THEN 1 ELSE 0 END) AS started_campaigns,
  SUM(CASE WHEN TO_CHAR(end_date, 'YYYY-MM') = '2026-05' THEN 1 ELSE 0 END) AS ended_campaigns
FROM ad_campaigns
```

Original SQL SHA256: `2d3a9f3546fc07c2a0ac96bde2e365bd3f654cfb77f4f1d80a47b584b17bad87`

PostgreSQL SQL SHA256: `8e57950303c3fe2cf4076850b611d56a92fa9e0bcd3a36e23aea57567ffc6b94`

## CHANNEL_OPS-096

预算调整原因为转化成本偏高的调整次数和平均幅度；请返回调整原因、调整次数、平均调整幅度；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: adjustment_reason, adjustments, avg_change. Filters: WHERE adjustment_reason = '转化成本偏高'.

Output: `adjustment_reason, adjustments, avg_change`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT adjustment_reason,COUNT(*) adjustments, ROUND(AVG(new_budget-previous_budget),2) avg_change FROM budget_adjustments WHERE adjustment_reason='转化成本偏高' GROUP BY 1
```

Explicit PostgreSQL SQL:

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

Original SQL SHA256: `54aa4fa2bf743e711b524cb8041784997d802acf4980dc0a34afbc9f30434b67`

PostgreSQL SQL SHA256: `db9b9caffc246c0b3c295d71bdcb6129fb416574c9a5219d1d7c3a41bf1b8501`

## CHANNEL_OPS-097

预算调整原因为留存质量较好的调整次数和平均幅度；请返回调整原因、调整次数、平均调整幅度；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: adjustment_reason, adjustments, avg_change. Filters: WHERE adjustment_reason = '留存质量较好'.

Output: `adjustment_reason, adjustments, avg_change`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT adjustment_reason,COUNT(*) adjustments, ROUND(AVG(new_budget-previous_budget),2) avg_change FROM budget_adjustments WHERE adjustment_reason='留存质量较好' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  adjustment_reason,
  COUNT(*) AS adjustments,
  ROUND(CAST(AVG(new_budget - previous_budget) AS DECIMAL), 2) AS avg_change
FROM budget_adjustments
WHERE
  adjustment_reason = '留存质量较好'
GROUP BY
  1
```

Original SQL SHA256: `13a02ddd7c0274eef557d3329740e3e2404a0f0b467f046d394349d802466a80`

PostgreSQL SQL SHA256: `1b7905c42e296ec546d602fcd3674f2ceb7111f5c0e6f5540ce2e9bb3c6aab8a`

## CHANNEL_OPS-098

预算调整原因为阶段性加量的调整次数和平均幅度；请返回调整原因、调整次数、平均调整幅度；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: adjustment_reason, adjustments, avg_change. Filters: WHERE adjustment_reason = '阶段性加量'.

Output: `adjustment_reason, adjustments, avg_change`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT adjustment_reason,COUNT(*) adjustments, ROUND(AVG(new_budget-previous_budget),2) avg_change FROM budget_adjustments WHERE adjustment_reason='阶段性加量' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  adjustment_reason,
  COUNT(*) AS adjustments,
  ROUND(CAST(AVG(new_budget - previous_budget) AS DECIMAL), 2) AS avg_change
FROM budget_adjustments
WHERE
  adjustment_reason = '阶段性加量'
GROUP BY
  1
```

Original SQL SHA256: `57933dbd204839cb6c73311c9859baad6e6c08255b3e4a67b1e6e181ba1b5d99`

PostgreSQL SQL SHA256: `cd1025d01b8b082560919af7520d3c782533c6a34d031079326c7b0aee2e3bcb`

## CHANNEL_OPS-099

预算调整原因为素材衰退的调整次数和平均幅度；请返回调整原因、调整次数、平均调整幅度；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: adjustment_reason, adjustments, avg_change. Filters: WHERE adjustment_reason = '素材衰退'.

Output: `adjustment_reason, adjustments, avg_change`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT adjustment_reason,COUNT(*) adjustments, ROUND(AVG(new_budget-previous_budget),2) avg_change FROM budget_adjustments WHERE adjustment_reason='素材衰退' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  adjustment_reason,
  COUNT(*) AS adjustments,
  ROUND(CAST(AVG(new_budget - previous_budget) AS DECIMAL), 2) AS avg_change
FROM budget_adjustments
WHERE
  adjustment_reason = '素材衰退'
GROUP BY
  1
```

Original SQL SHA256: `c53b7dc9f2005e47261e779949cccc7de221dfb05529b35959127214a2943228`

PostgreSQL SQL SHA256: `5253c3adb643baedb42870a7d711df397c9e65b750f186c1bde6d4dafcc07f6c`

## CHANNEL_OPS-103

开屏创意的状态分布；请返回创意状态、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_status, creatives. Filters: WHERE creative_type = '开屏'.

Output: `creative_status, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT creative_status,COUNT(creative_id) creatives FROM ad_creatives WHERE creative_type='开屏' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  creative_status,
  COUNT(creative_id) AS creatives
FROM ad_creatives
WHERE
  creative_type = '开屏'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `8f6cfabadd6e3c29416f4027556785beddb44bafffab50e844a67cc93ec8cbf7`

PostgreSQL SQL SHA256: `bd83622ea6f329538c8ec14668694cd411ed2db7fd0cab07b58ddebc2c48aa13`

## CHANNEL_OPS-104

请汇总短视频创意的状态分布；请返回创意状态、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_status, creatives. Filters: WHERE creative_type = '短视频'.

Output: `creative_status, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT creative_status,COUNT(creative_id) creatives FROM ad_creatives WHERE creative_type='短视频' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

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

Original SQL SHA256: `a480179252226a8254f817560ac80a41847e9259ac3795cc828054c3e2897616`

PostgreSQL SQL SHA256: `6d917a1339c7501c7b55daa58b3e87f8d54b727aeea2788a1fe4d6b709f4385d`

## CHANNEL_OPS-105

请汇总图文创意的状态分布；请返回创意状态、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_status, creatives. Filters: WHERE creative_type = '图文'.

Output: `creative_status, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT creative_status,COUNT(creative_id) creatives FROM ad_creatives WHERE creative_type='图文' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

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

Original SQL SHA256: `7e657594958b967d01d7f40ce0584647b8e79a360b3f15c16e827358ba1537cd`

PostgreSQL SQL SHA256: `4105a7db489b81ad621b8e296f068b5465be7207b253ddf91d42305f9c9bbf52`

## CHANNEL_OPS-106

注册目标计划使用的创意类型分布；请返回创意类型、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_type, creatives. Filters: WHERE p.objective = '注册'.

Output: `creative_type, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creative_type,COUNT(c.creative_id) creatives FROM ad_creatives c JOIN ad_campaigns p ON c.ad_campaign_id=p.ad_campaign_id WHERE p.objective='注册' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creative_type,
  COUNT(c.creative_id) AS creatives
FROM ad_creatives AS c
JOIN ad_campaigns AS p
  ON c.ad_campaign_id = p.ad_campaign_id
WHERE
  p.objective = '注册'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `af7fbb17080ff8bce49605077679180aca11c7128fb632950f9699c3d98b3ed5`

PostgreSQL SQL SHA256: `cc02e31df54e96105c3c8879dd2817b8e3294a544ecf4d403b0d9664ed54962a`

## CHANNEL_OPS-107

激活目标计划使用的创意类型分布；请返回创意类型、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_type, creatives. Filters: WHERE p.objective = '激活'.

Output: `creative_type, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creative_type,COUNT(c.creative_id) creatives FROM ad_creatives c JOIN ad_campaigns p ON c.ad_campaign_id=p.ad_campaign_id WHERE p.objective='激活' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creative_type,
  COUNT(c.creative_id) AS creatives
FROM ad_creatives AS c
JOIN ad_campaigns AS p
  ON c.ad_campaign_id = p.ad_campaign_id
WHERE
  p.objective = '激活'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `020786b4d2fa696de8db98deeb729e223d42b4f057b9955455997739e1025d3e`

PostgreSQL SQL SHA256: `d9ec47831c5899d728bc271c7b1e10b18b1525637008e881edf3cbd4290b7f38`

## CHANNEL_OPS-108

七日留存目标计划使用的创意类型分布；请返回创意类型、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_type, creatives. Filters: WHERE p.objective = '七日留存'.

Output: `creative_type, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creative_type,COUNT(c.creative_id) creatives FROM ad_creatives c JOIN ad_campaigns p ON c.ad_campaign_id=p.ad_campaign_id WHERE p.objective='七日留存' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creative_type,
  COUNT(c.creative_id) AS creatives
FROM ad_creatives AS c
JOIN ad_campaigns AS p
  ON c.ad_campaign_id = p.ad_campaign_id
WHERE
  p.objective = '七日留存'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `032274e188e6d1c92591d9ccfdf48babd02cabc3de2e60cc7f326d33aab15fbe`

PostgreSQL SQL SHA256: `2e90cfcfbb420aa5501cfa6bfcd0d47c5716c6762f9e1003dc320003e31e5a84`

## CHANNEL_OPS-109

请汇总注册目标计划使用的创意类型分布；请返回创意类型、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_type, creatives. Filters: WHERE p.objective = '注册'.

Output: `creative_type, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creative_type,COUNT(c.creative_id) creatives FROM ad_creatives c JOIN ad_campaigns p ON c.ad_campaign_id=p.ad_campaign_id WHERE p.objective='注册' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creative_type,
  COUNT(c.creative_id) AS creatives
FROM ad_creatives AS c
JOIN ad_campaigns AS p
  ON c.ad_campaign_id = p.ad_campaign_id
WHERE
  p.objective = '注册'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `af7fbb17080ff8bce49605077679180aca11c7128fb632950f9699c3d98b3ed5`

PostgreSQL SQL SHA256: `cc02e31df54e96105c3c8879dd2817b8e3294a544ecf4d403b0d9664ed54962a`

## CHANNEL_OPS-110

请汇总激活目标计划使用的创意类型分布；请返回创意类型、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_type, creatives. Filters: WHERE p.objective = '激活'.

Output: `creative_type, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creative_type,COUNT(c.creative_id) creatives FROM ad_creatives c JOIN ad_campaigns p ON c.ad_campaign_id=p.ad_campaign_id WHERE p.objective='激活' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creative_type,
  COUNT(c.creative_id) AS creatives
FROM ad_creatives AS c
JOIN ad_campaigns AS p
  ON c.ad_campaign_id = p.ad_campaign_id
WHERE
  p.objective = '激活'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `020786b4d2fa696de8db98deeb729e223d42b4f057b9955455997739e1025d3e`

PostgreSQL SQL SHA256: `d9ec47831c5899d728bc271c7b1e10b18b1525637008e881edf3cbd4290b7f38`

## CHANNEL_OPS-111

信息流广告各创意主题的素材数量；请返回创意主题、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_theme, creatives. Filters: WHERE c.channel_name = '信息流广告'.

Output: `creative_theme, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cr.creative_theme,COUNT(cr.creative_id) creatives FROM ad_creatives cr JOIN ad_campaigns p ON cr.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='信息流广告' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cr.creative_theme,
  COUNT(cr.creative_id) AS creatives
FROM ad_creatives AS cr
JOIN ad_campaigns AS p
  ON cr.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  c.channel_name = '信息流广告'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `4c69deaf196efc45b025d4f0f3a641aa79393661e175d40e35bd34964a55914b`

PostgreSQL SQL SHA256: `55aedf0bc7d3674acf5e4ebbd04e935ccf6b3125e10f8d338c71e8c27cddf2f4`

## CHANNEL_OPS-112

搜索广告各创意主题的素材数量；请返回创意主题、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_theme, creatives. Filters: WHERE c.channel_name = '搜索广告'.

Output: `creative_theme, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cr.creative_theme,COUNT(cr.creative_id) creatives FROM ad_creatives cr JOIN ad_campaigns p ON cr.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='搜索广告' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cr.creative_theme,
  COUNT(cr.creative_id) AS creatives
FROM ad_creatives AS cr
JOIN ad_campaigns AS p
  ON cr.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  c.channel_name = '搜索广告'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `78125f766b6a5fd93c0bff05edc6b6b6b0998591660f8c734b2b29ee38e9cc02`

PostgreSQL SQL SHA256: `bf5424fbe827dbc47b1f64fb588aef6121b7336d87006f6d33ea0c97a5567c18`

## CHANNEL_OPS-113

达人推广各创意主题的素材数量；请返回创意主题、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_theme, creatives. Filters: WHERE c.channel_name = '达人推广'.

Output: `creative_theme, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cr.creative_theme,COUNT(cr.creative_id) creatives FROM ad_creatives cr JOIN ad_campaigns p ON cr.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='达人推广' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cr.creative_theme,
  COUNT(cr.creative_id) AS creatives
FROM ad_creatives AS cr
JOIN ad_campaigns AS p
  ON cr.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  c.channel_name = '达人推广'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `5fe7e9ce65f1f3c2a61068b26232eff14e845b4bc8b5abd724ab748d6ba3b37b`

PostgreSQL SQL SHA256: `37c097f03155cee2d570235d90e329ef9c85b81efcc3264d286c2fe88cbff8fa`

## CHANNEL_OPS-114

品牌广告各创意主题的素材数量；请返回创意主题、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_theme, creatives. Filters: WHERE c.channel_name = '品牌广告'.

Output: `creative_theme, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cr.creative_theme,COUNT(cr.creative_id) creatives FROM ad_creatives cr JOIN ad_campaigns p ON cr.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='品牌广告' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cr.creative_theme,
  COUNT(cr.creative_id) AS creatives
FROM ad_creatives AS cr
JOIN ad_campaigns AS p
  ON cr.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  c.channel_name = '品牌广告'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `5bf94b1ea5e2d851fcf44347c8c8120ae9dd48c3f274d6f833a32327d9e056af`

PostgreSQL SQL SHA256: `b54dc0dfe296b5b01010bb26b376aa5db5577f12173c5439ac915b12810dc9ce`

## CHANNEL_OPS-115

请汇总信息流广告各创意主题的素材数量；请返回创意主题、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_theme, creatives. Filters: WHERE c.channel_name = '信息流广告'.

Output: `creative_theme, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cr.creative_theme,COUNT(cr.creative_id) creatives FROM ad_creatives cr JOIN ad_campaigns p ON cr.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE c.channel_name='信息流广告' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cr.creative_theme,
  COUNT(cr.creative_id) AS creatives
FROM ad_creatives AS cr
JOIN ad_campaigns AS p
  ON cr.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  c.channel_name = '信息流广告'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `4c69deaf196efc45b025d4f0f3a641aa79393661e175d40e35bd34964a55914b`

PostgreSQL SQL SHA256: `55aedf0bc7d3674acf5e4ebbd04e935ccf6b3125e10f8d338c71e8c27cddf2f4`

## CHANNEL_OPS-116

active创意按投放渠道分布；请返回渠道名称、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, creatives. Filters: WHERE cr.creative_status = 'active'.

Output: `channel_name, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,COUNT(cr.creative_id) creatives FROM ad_creatives cr JOIN ad_campaigns p ON cr.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE cr.creative_status='active' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  COUNT(cr.creative_id) AS creatives
FROM ad_creatives AS cr
JOIN ad_campaigns AS p
  ON cr.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  cr.creative_status = 'active'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `ba7936482becd957f307b3d86726c992773ce952ccc95024c840c5f7e3aadbcd`

PostgreSQL SQL SHA256: `ec294a34d1e34c47bea233f7baf2ec2abc57ef2185cb6144a695f5802805a958`

## CHANNEL_OPS-117

paused创意按投放渠道分布；请返回渠道名称、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, creatives. Filters: WHERE cr.creative_status = 'paused'.

Output: `channel_name, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,COUNT(cr.creative_id) creatives FROM ad_creatives cr JOIN ad_campaigns p ON cr.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE cr.creative_status='paused' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  COUNT(cr.creative_id) AS creatives
FROM ad_creatives AS cr
JOIN ad_campaigns AS p
  ON cr.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  cr.creative_status = 'paused'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `f535381ebdd664aef7cd3c746c428793355e458bb69a2bbd93858d0c80c0b478`

PostgreSQL SQL SHA256: `c95a3e13d70420a4469900d60fe302c68096dec64d6b51dc4f5435140dc80380`

## CHANNEL_OPS-118

请汇总active创意按投放渠道分布；请返回渠道名称、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, creatives. Filters: WHERE cr.creative_status = 'active'.

Output: `channel_name, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,COUNT(cr.creative_id) creatives FROM ad_creatives cr JOIN ad_campaigns p ON cr.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE cr.creative_status='active' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  COUNT(cr.creative_id) AS creatives
FROM ad_creatives AS cr
JOIN ad_campaigns AS p
  ON cr.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  cr.creative_status = 'active'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `ba7936482becd957f307b3d86726c992773ce952ccc95024c840c5f7e3aadbcd`

PostgreSQL SQL SHA256: `ec294a34d1e34c47bea233f7baf2ec2abc57ef2185cb6144a695f5802805a958`

## CHANNEL_OPS-119

请汇总paused创意按投放渠道分布；请返回渠道名称、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, creatives. Filters: WHERE cr.creative_status = 'paused'.

Output: `channel_name, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,COUNT(cr.creative_id) creatives FROM ad_creatives cr JOIN ad_campaigns p ON cr.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE cr.creative_status='paused' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  COUNT(cr.creative_id) AS creatives
FROM ad_creatives AS cr
JOIN ad_campaigns AS p
  ON cr.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  cr.creative_status = 'paused'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `f535381ebdd664aef7cd3c746c428793355e458bb69a2bbd93858d0c80c0b478`

PostgreSQL SQL SHA256: `c95a3e13d70420a4469900d60fe302c68096dec64d6b51dc4f5435140dc80380`

## CHANNEL_OPS-120

请分析active创意按投放渠道分布；请返回渠道名称、创意数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, creatives. Filters: WHERE cr.creative_status = 'active'.

Output: `channel_name, creatives`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,COUNT(cr.creative_id) creatives FROM ad_creatives cr JOIN ad_campaigns p ON cr.ad_campaign_id=p.ad_campaign_id JOIN acquisition_channels c ON p.channel_id=c.channel_id WHERE cr.creative_status='active' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  COUNT(cr.creative_id) AS creatives
FROM ad_creatives AS cr
JOIN ad_campaigns AS p
  ON cr.ad_campaign_id = p.ad_campaign_id
JOIN acquisition_channels AS c
  ON p.channel_id = c.channel_id
WHERE
  cr.creative_status = 'active'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `ba7936482becd957f307b3d86726c992773ce952ccc95024c840c5f7e3aadbcd`

PostgreSQL SQL SHA256: `ec294a34d1e34c47bea233f7baf2ec2abc57ef2185cb6144a695f5802805a958`

## CHANNEL_OPS-121

使用短视频的计划平均有多少条创意；请返回创意类型、每个计划平均创意数；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_type, avg_creatives_per_campaign. Filters: WHERE creative_type = '短视频'.

Output: `creative_type, avg_creatives_per_campaign`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
WITH c AS (SELECT ad_campaign_id,COUNT(creative_id) cnt FROM ad_creatives WHERE creative_type='短视频' GROUP BY 1) SELECT '短视频' creative_type,ROUND(AVG(cnt),2) avg_creatives_per_campaign FROM c
```

Explicit PostgreSQL SQL:

```sql
WITH c AS (
  SELECT
    ad_campaign_id,
    COUNT(creative_id) AS cnt
  FROM ad_creatives
  WHERE
    creative_type = '短视频'
  GROUP BY
    1
)
SELECT
  '短视频' AS creative_type,
  ROUND(CAST(AVG(cnt) AS DECIMAL), 2) AS avg_creatives_per_campaign
FROM c
```

Original SQL SHA256: `d4ef637741443d1cc77e356aa37569e5349ab4d036b911fc2b0f632b5ab40897`

PostgreSQL SQL SHA256: `1aef087e3cd24e89c881e7a7efad4a5e90ce17ff781493c8ceb4dae6b5357945`

## CHANNEL_OPS-122

使用图文的计划平均有多少条创意；请返回创意类型、每个计划平均创意数；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_type, avg_creatives_per_campaign. Filters: WHERE creative_type = '图文'.

Output: `creative_type, avg_creatives_per_campaign`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
WITH c AS (SELECT ad_campaign_id,COUNT(creative_id) cnt FROM ad_creatives WHERE creative_type='图文' GROUP BY 1) SELECT '图文' creative_type,ROUND(AVG(cnt),2) avg_creatives_per_campaign FROM c
```

Explicit PostgreSQL SQL:

```sql
WITH c AS (
  SELECT
    ad_campaign_id,
    COUNT(creative_id) AS cnt
  FROM ad_creatives
  WHERE
    creative_type = '图文'
  GROUP BY
    1
)
SELECT
  '图文' AS creative_type,
  ROUND(CAST(AVG(cnt) AS DECIMAL), 2) AS avg_creatives_per_campaign
FROM c
```

Original SQL SHA256: `36f449b7e2e54842fd0a0b9d5740f30bb8471983b2963f7fc0c4a0816ac7f343`

PostgreSQL SQL SHA256: `6579d8b67ac88e7ba112daae3c841174319c5fbb164f94b2f02c52c89902f4da`

## CHANNEL_OPS-123

使用开屏的计划平均有多少条创意；请返回创意类型、每个计划平均创意数；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_type, avg_creatives_per_campaign. Filters: WHERE creative_type = '开屏'.

Output: `creative_type, avg_creatives_per_campaign`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
WITH c AS (SELECT ad_campaign_id,COUNT(creative_id) cnt FROM ad_creatives WHERE creative_type='开屏' GROUP BY 1) SELECT '开屏' creative_type,ROUND(AVG(cnt),2) avg_creatives_per_campaign FROM c
```

Explicit PostgreSQL SQL:

```sql
WITH c AS (
  SELECT
    ad_campaign_id,
    COUNT(creative_id) AS cnt
  FROM ad_creatives
  WHERE
    creative_type = '开屏'
  GROUP BY
    1
)
SELECT
  '开屏' AS creative_type,
  ROUND(CAST(AVG(cnt) AS DECIMAL), 2) AS avg_creatives_per_campaign
FROM c
```

Original SQL SHA256: `d8221f64582008e3b4c650b202a3b0073f4c34493359413124d26f9686b0cc12`

PostgreSQL SQL SHA256: `6e74278d8157f2d3b818a2568f19baf8d9234435c36919771f7b5c332aa67cef`

## CHANNEL_OPS-124

请汇总使用短视频的计划平均有多少条创意；请返回创意类型、每个计划平均创意数；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_type, avg_creatives_per_campaign. Filters: WHERE creative_type = '短视频'.

Output: `creative_type, avg_creatives_per_campaign`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
WITH c AS (SELECT ad_campaign_id,COUNT(creative_id) cnt FROM ad_creatives WHERE creative_type='短视频' GROUP BY 1) SELECT '短视频' creative_type,ROUND(AVG(cnt),2) avg_creatives_per_campaign FROM c
```

Explicit PostgreSQL SQL:

```sql
WITH c AS (
  SELECT
    ad_campaign_id,
    COUNT(creative_id) AS cnt
  FROM ad_creatives
  WHERE
    creative_type = '短视频'
  GROUP BY
    1
)
SELECT
  '短视频' AS creative_type,
  ROUND(CAST(AVG(cnt) AS DECIMAL), 2) AS avg_creatives_per_campaign
FROM c
```

Original SQL SHA256: `d4ef637741443d1cc77e356aa37569e5349ab4d036b911fc2b0f632b5ab40897`

PostgreSQL SQL SHA256: `1aef087e3cd24e89c881e7a7efad4a5e90ce17ff781493c8ceb4dae6b5357945`

## CHANNEL_OPS-125

请汇总使用图文的计划平均有多少条创意；请返回创意类型、每个计划平均创意数；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creative_type, avg_creatives_per_campaign. Filters: WHERE creative_type = '图文'.

Output: `creative_type, avg_creatives_per_campaign`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
WITH c AS (SELECT ad_campaign_id,COUNT(creative_id) cnt FROM ad_creatives WHERE creative_type='图文' GROUP BY 1) SELECT '图文' creative_type,ROUND(AVG(cnt),2) avg_creatives_per_campaign FROM c
```

Explicit PostgreSQL SQL:

```sql
WITH c AS (
  SELECT
    ad_campaign_id,
    COUNT(creative_id) AS cnt
  FROM ad_creatives
  WHERE
    creative_type = '图文'
  GROUP BY
    1
)
SELECT
  '图文' AS creative_type,
  ROUND(CAST(AVG(cnt) AS DECIMAL), 2) AS avg_creatives_per_campaign
FROM c
```

Original SQL SHA256: `36f449b7e2e54842fd0a0b9d5740f30bb8471983b2963f7fc0c4a0816ac7f343`

PostgreSQL SQL SHA256: `6579d8b67ac88e7ba112daae3c841174319c5fbb164f94b2f02c52c89902f4da`

## CHANNEL_OPS-127

first_click归因按渠道的用户数和平均置信度；请返回渠道名称、用户数、平均置信度；聚合口径：去重数量按对应实体唯一标识计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, users, avg_confidence. Filters: WHERE a.attribution_type = 'first_click'.

Output: `channel_name, users, avg_confidence`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,COUNT(DISTINCT a.user_id) users,ROUND(AVG(a.confidence_score),4) avg_confidence FROM channel_attributions a JOIN acquisition_channels c ON a.channel_id=c.channel_id WHERE a.attribution_type='first_click' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  COUNT(DISTINCT a.user_id) AS users,
  ROUND(CAST(AVG(a.confidence_score) AS DECIMAL), 4) AS avg_confidence
FROM channel_attributions AS a
JOIN acquisition_channels AS c
  ON a.channel_id = c.channel_id
WHERE
  a.attribution_type = 'first_click'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `b3e3222946f99f378560df71e10602a2657dfed35ea74804806e958f1b39634a`

PostgreSQL SQL SHA256: `e44a5e7a4439a19235cd9dcb801676d04043c298694e47a6dc55e1c4ce50625c`

## CHANNEL_OPS-128

view_through归因按渠道的用户数和平均置信度；请返回渠道名称、用户数、平均置信度；聚合口径：去重数量按对应实体唯一标识计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, users, avg_confidence. Filters: WHERE a.attribution_type = 'view_through'.

Output: `channel_name, users, avg_confidence`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,COUNT(DISTINCT a.user_id) users,ROUND(AVG(a.confidence_score),4) avg_confidence FROM channel_attributions a JOIN acquisition_channels c ON a.channel_id=c.channel_id WHERE a.attribution_type='view_through' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  COUNT(DISTINCT a.user_id) AS users,
  ROUND(CAST(AVG(a.confidence_score) AS DECIMAL), 4) AS avg_confidence
FROM channel_attributions AS a
JOIN acquisition_channels AS c
  ON a.channel_id = c.channel_id
WHERE
  a.attribution_type = 'view_through'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `e80dfe20daf31fde0867206b102da66f382bde65e737c996cd75a0fa14b7b5e8`

PostgreSQL SQL SHA256: `48e9ea172ff39d53068a6766618aea0ec965053559e776c52685dfd649899588`

## CHANNEL_OPS-129

请汇总last_click归因按渠道的用户数和平均置信度；请返回渠道名称、用户数、平均置信度；聚合口径：去重数量按对应实体唯一标识计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, users, avg_confidence. Filters: WHERE a.attribution_type = 'last_click'.

Output: `channel_name, users, avg_confidence`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,COUNT(DISTINCT a.user_id) users,ROUND(AVG(a.confidence_score),4) avg_confidence FROM channel_attributions a JOIN acquisition_channels c ON a.channel_id=c.channel_id WHERE a.attribution_type='last_click' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

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

Original SQL SHA256: `18dfe88791facae23df806b584bcc5f6fefea8576629ff5243a83649c29fa70b`

PostgreSQL SQL SHA256: `2eeafd7b704befe3cd9d4967acf4e78df5798b5077874ec7f3dd6ec9f781caff`

## CHANNEL_OPS-130

请汇总first_click归因按渠道的用户数和平均置信度；请返回渠道名称、用户数、平均置信度；聚合口径：去重数量按对应实体唯一标识计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, users, avg_confidence. Filters: WHERE a.attribution_type = 'first_click'.

Output: `channel_name, users, avg_confidence`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,COUNT(DISTINCT a.user_id) users,ROUND(AVG(a.confidence_score),4) avg_confidence FROM channel_attributions a JOIN acquisition_channels c ON a.channel_id=c.channel_id WHERE a.attribution_type='first_click' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  COUNT(DISTINCT a.user_id) AS users,
  ROUND(CAST(AVG(a.confidence_score) AS DECIMAL), 4) AS avg_confidence
FROM channel_attributions AS a
JOIN acquisition_channels AS c
  ON a.channel_id = c.channel_id
WHERE
  a.attribution_type = 'first_click'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `b3e3222946f99f378560df71e10602a2657dfed35ea74804806e958f1b39634a`

PostgreSQL SQL SHA256: `e44a5e7a4439a19235cd9dcb801676d04043c298694e47a6dc55e1c4ce50625c`

## CHANNEL_OPS-137

2026-02各渠道实际CPA与目标CPA差距；请返回渠道名称、实际CPA、目标CPA、目标差距；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, actual_cpa, target_cpa, gap. Filters: WHERE SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-02'; WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-02'.

Output: `channel_name, actual_cpa, target_cpa, gap`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 1, "month_format_count": 1, "substring_count": 1, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
WITH actual AS (SELECT p.channel_id,SUM(s.spend)/NULLIF(SUM(s.conversions),0) cpa FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id WHERE strftime(s.stat_date,'%Y-%m')='2026-02' GROUP BY 1) SELECT c.channel_name,ROUND(a.cpa,2) actual_cpa,t.target_cpa,ROUND(a.cpa-t.target_cpa,2) gap FROM channel_targets t JOIN acquisition_channels c ON t.channel_id=c.channel_id JOIN actual a ON t.channel_id=a.channel_id WHERE substr(t.target_month,1,7)='2026-02' ORDER BY gap,1
```

Explicit PostgreSQL SQL:

```sql
WITH actual AS (
  SELECT
    p.channel_id,
    CAST(SUM(s.spend) AS DOUBLE PRECISION) / NULLIF(SUM(s.conversions), 0) AS cpa
  FROM ad_daily_stats AS s
  JOIN ad_campaigns AS p
    ON s.ad_campaign_id = p.ad_campaign_id
  WHERE
    TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-02'
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
  SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-02'
ORDER BY
  gap,
  1
```

Original SQL SHA256: `63c237d0c16a1340f44914726e73f5b364b1164186499fb7edbd71928b60bc99`

PostgreSQL SQL SHA256: `17d4bf127c1b83ae99779b0f00f5ad2ed7e6b8bb32579ca7ee0bf003e09e85ec`

## CHANNEL_OPS-138

2026-03各渠道实际CPA与目标CPA差距；请返回渠道名称、实际CPA、目标CPA、目标差距；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, actual_cpa, target_cpa, gap. Filters: WHERE SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-03'; WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-03'.

Output: `channel_name, actual_cpa, target_cpa, gap`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 1, "month_format_count": 1, "substring_count": 1, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
WITH actual AS (SELECT p.channel_id,SUM(s.spend)/NULLIF(SUM(s.conversions),0) cpa FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id WHERE strftime(s.stat_date,'%Y-%m')='2026-03' GROUP BY 1) SELECT c.channel_name,ROUND(a.cpa,2) actual_cpa,t.target_cpa,ROUND(a.cpa-t.target_cpa,2) gap FROM channel_targets t JOIN acquisition_channels c ON t.channel_id=c.channel_id JOIN actual a ON t.channel_id=a.channel_id WHERE substr(t.target_month,1,7)='2026-03' ORDER BY gap,1
```

Explicit PostgreSQL SQL:

```sql
WITH actual AS (
  SELECT
    p.channel_id,
    CAST(SUM(s.spend) AS DOUBLE PRECISION) / NULLIF(SUM(s.conversions), 0) AS cpa
  FROM ad_daily_stats AS s
  JOIN ad_campaigns AS p
    ON s.ad_campaign_id = p.ad_campaign_id
  WHERE
    TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-03'
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
  SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-03'
ORDER BY
  gap,
  1
```

Original SQL SHA256: `386b4d172da2a5e22d853aa08b82bc371c70850f9f313c861bc5d4940fd8eb72`

PostgreSQL SQL SHA256: `ce317c56e8c41b68180ff65252f05cf3f78a3a2d57c0a4908cb6df05f291e686`

## CHANNEL_OPS-139

2026-04各渠道实际CPA与目标CPA差距；请返回渠道名称、实际CPA、目标CPA、目标差距；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, actual_cpa, target_cpa, gap. Filters: WHERE SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-04'; WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-04'.

Output: `channel_name, actual_cpa, target_cpa, gap`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 1, "month_format_count": 1, "substring_count": 1, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
WITH actual AS (SELECT p.channel_id,SUM(s.spend)/NULLIF(SUM(s.conversions),0) cpa FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id WHERE strftime(s.stat_date,'%Y-%m')='2026-04' GROUP BY 1) SELECT c.channel_name,ROUND(a.cpa,2) actual_cpa,t.target_cpa,ROUND(a.cpa-t.target_cpa,2) gap FROM channel_targets t JOIN acquisition_channels c ON t.channel_id=c.channel_id JOIN actual a ON t.channel_id=a.channel_id WHERE substr(t.target_month,1,7)='2026-04' ORDER BY gap,1
```

Explicit PostgreSQL SQL:

```sql
WITH actual AS (
  SELECT
    p.channel_id,
    CAST(SUM(s.spend) AS DOUBLE PRECISION) / NULLIF(SUM(s.conversions), 0) AS cpa
  FROM ad_daily_stats AS s
  JOIN ad_campaigns AS p
    ON s.ad_campaign_id = p.ad_campaign_id
  WHERE
    TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-04'
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
  SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-04'
ORDER BY
  gap,
  1
```

Original SQL SHA256: `3338c94304afa3ae525eecf0f3e927148f042c38326030046778cb685ec6ebd6`

PostgreSQL SQL SHA256: `1e07a009924880b1257fde3bb53c0e7075f152356c3d9f60ae6bf122e27eddee`

## CHANNEL_OPS-140

2026-05各渠道实际CPA与目标CPA差距；请返回渠道名称、实际CPA、目标CPA、目标差距；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, actual_cpa, target_cpa, gap. Filters: WHERE SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-05'; WHERE TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-05'.

Output: `channel_name, actual_cpa, target_cpa, gap`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 1, "month_format_count": 1, "substring_count": 1, "nullif_count": 1, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
WITH actual AS (SELECT p.channel_id,SUM(s.spend)/NULLIF(SUM(s.conversions),0) cpa FROM ad_daily_stats s JOIN ad_campaigns p ON s.ad_campaign_id=p.ad_campaign_id WHERE strftime(s.stat_date,'%Y-%m')='2026-05' GROUP BY 1) SELECT c.channel_name,ROUND(a.cpa,2) actual_cpa,t.target_cpa,ROUND(a.cpa-t.target_cpa,2) gap FROM channel_targets t JOIN acquisition_channels c ON t.channel_id=c.channel_id JOIN actual a ON t.channel_id=a.channel_id WHERE substr(t.target_month,1,7)='2026-05' ORDER BY gap,1
```

Explicit PostgreSQL SQL:

```sql
WITH actual AS (
  SELECT
    p.channel_id,
    CAST(SUM(s.spend) AS DOUBLE PRECISION) / NULLIF(SUM(s.conversions), 0) AS cpa
  FROM ad_daily_stats AS s
  JOIN ad_campaigns AS p
    ON s.ad_campaign_id = p.ad_campaign_id
  WHERE
    TO_CHAR(s.stat_date, 'YYYY-MM') = '2026-05'
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
  SUBSTRING(t.target_month FROM 1 FOR 7) = '2026-05'
ORDER BY
  gap,
  1
```

Original SQL SHA256: `3d1d16e2821ceb74379a9681a798c1554e0c21a94941f5b8c920082202f6d247`

PostgreSQL SQL SHA256: `892abf5c84a8dd0cfd387e6ebe74663edae73d26a9808c35cf3a66dd5779cee4`

## CHANNEL_OPS-142

activation转化按渠道分布；请返回渠道名称、转化数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, conversions. Filters: WHERE e.conversion_type = 'activation'.

Output: `channel_name, conversions`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,COUNT(e.conversion_event_id) conversions FROM channel_conversion_events e JOIN acquisition_channels c ON e.channel_id=c.channel_id WHERE e.conversion_type='activation' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  COUNT(e.conversion_event_id) AS conversions
FROM channel_conversion_events AS e
JOIN acquisition_channels AS c
  ON e.channel_id = c.channel_id
WHERE
  e.conversion_type = 'activation'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `a8a15f38269e67e49ebd10cb2ad8fc65a6c04b7d3c061bceba1389e1d2c3686f`

PostgreSQL SQL SHA256: `43ac3aee8bbbe1668258d1662c1e45166f492ab2406aa2d2a58095217af75256`

## CHANNEL_OPS-143

请汇总registration转化按渠道分布；请返回渠道名称、转化数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, conversions. Filters: WHERE e.conversion_type = 'registration'.

Output: `channel_name, conversions`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,COUNT(e.conversion_event_id) conversions FROM channel_conversion_events e JOIN acquisition_channels c ON e.channel_id=c.channel_id WHERE e.conversion_type='registration' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

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

Original SQL SHA256: `8d66241a70e9a954c2c9bf4bc1d5b69cbcadc3d236b0a1d888573d0b6478dcda`

PostgreSQL SQL SHA256: `b62127892214b4ef4eab4ba09ff9b8e4ac23d026dd8f138b61d712582336d91c`

## CHANNEL_OPS-144

请汇总activation转化按渠道分布；请返回渠道名称、转化数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, conversions. Filters: WHERE e.conversion_type = 'activation'.

Output: `channel_name, conversions`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,COUNT(e.conversion_event_id) conversions FROM channel_conversion_events e JOIN acquisition_channels c ON e.channel_id=c.channel_id WHERE e.conversion_type='activation' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.channel_name,
  COUNT(e.conversion_event_id) AS conversions
FROM channel_conversion_events AS e
JOIN acquisition_channels AS c
  ON e.channel_id = c.channel_id
WHERE
  e.conversion_type = 'activation'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `a8a15f38269e67e49ebd10cb2ad8fc65a6c04b7d3c061bceba1389e1d2c3686f`

PostgreSQL SQL SHA256: `43ac3aee8bbbe1668258d1662c1e45166f492ab2406aa2d2a58095217af75256`

## CHANNEL_OPS-145

请分析registration转化按渠道分布；请返回渠道名称、转化数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: channel_name, conversions. Filters: WHERE e.conversion_type = 'registration'.

Output: `channel_name, conversions`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.channel_name,COUNT(e.conversion_event_id) conversions FROM channel_conversion_events e JOIN acquisition_channels c ON e.channel_id=c.channel_id WHERE e.conversion_type='registration' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

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

Original SQL SHA256: `8d66241a70e9a954c2c9bf4bc1d5b69cbcadc3d236b0a1d888573d0b6478dcda`

PostgreSQL SQL SHA256: `b62127892214b4ef4eab4ba09ff9b8e4ac23d026dd8f138b61d712582336d91c`

## CHANNEL_OPS-146

信息流广告渠道不同归因方式的数量和置信度；请返回归因方式、归因数量、平均置信度；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: attribution_type, attributions, avg_confidence. Filters: WHERE c.channel_name = '信息流广告'.

Output: `attribution_type, attributions, avg_confidence`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT a.attribution_type,COUNT(*) attributions,ROUND(AVG(a.confidence_score),4) avg_confidence FROM channel_attributions a JOIN acquisition_channels c ON a.channel_id=c.channel_id WHERE c.channel_name='信息流广告' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  a.attribution_type,
  COUNT(*) AS attributions,
  ROUND(CAST(AVG(a.confidence_score) AS DECIMAL), 4) AS avg_confidence
FROM channel_attributions AS a
JOIN acquisition_channels AS c
  ON a.channel_id = c.channel_id
WHERE
  c.channel_name = '信息流广告'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `697cd33152527196a64c897af501b3f80d42d9bed6138686a919a8da46cfee21`

PostgreSQL SQL SHA256: `3731a008ad9d67963e42ebcb8b0c64f4995358f5759276994d35f0936ba79ca1`

## CHANNEL_OPS-147

搜索广告渠道不同归因方式的数量和置信度；请返回归因方式、归因数量、平均置信度；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: attribution_type, attributions, avg_confidence. Filters: WHERE c.channel_name = '搜索广告'.

Output: `attribution_type, attributions, avg_confidence`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT a.attribution_type,COUNT(*) attributions,ROUND(AVG(a.confidence_score),4) avg_confidence FROM channel_attributions a JOIN acquisition_channels c ON a.channel_id=c.channel_id WHERE c.channel_name='搜索广告' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  a.attribution_type,
  COUNT(*) AS attributions,
  ROUND(CAST(AVG(a.confidence_score) AS DECIMAL), 4) AS avg_confidence
FROM channel_attributions AS a
JOIN acquisition_channels AS c
  ON a.channel_id = c.channel_id
WHERE
  c.channel_name = '搜索广告'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `97852f7bfbc90d2aee5e6d5b829409be2967d043add005c815f24ecb5fc98e5f`

PostgreSQL SQL SHA256: `b801e0b34ca494558ddad2b8706edc2b73be22543d61a0cf10b0f980f57a4286`

## CHANNEL_OPS-148

达人推广渠道不同归因方式的数量和置信度；请返回归因方式、归因数量、平均置信度；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: attribution_type, attributions, avg_confidence. Filters: WHERE c.channel_name = '达人推广'.

Output: `attribution_type, attributions, avg_confidence`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT a.attribution_type,COUNT(*) attributions,ROUND(AVG(a.confidence_score),4) avg_confidence FROM channel_attributions a JOIN acquisition_channels c ON a.channel_id=c.channel_id WHERE c.channel_name='达人推广' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  a.attribution_type,
  COUNT(*) AS attributions,
  ROUND(CAST(AVG(a.confidence_score) AS DECIMAL), 4) AS avg_confidence
FROM channel_attributions AS a
JOIN acquisition_channels AS c
  ON a.channel_id = c.channel_id
WHERE
  c.channel_name = '达人推广'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `8cd8b591b3ab42a72dbd079584d8d3d85113d708157da3b529acb2afa6a2d5c4`

PostgreSQL SQL SHA256: `ae4e881667b8da98515447ffe9ab8b8c35c39b25e6cefc7346959ee35cffc0b7`

## CHANNEL_OPS-149

品牌广告渠道不同归因方式的数量和置信度；请返回归因方式、归因数量、平均置信度；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: attribution_type, attributions, avg_confidence. Filters: WHERE c.channel_name = '品牌广告'.

Output: `attribution_type, attributions, avg_confidence`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT a.attribution_type,COUNT(*) attributions,ROUND(AVG(a.confidence_score),4) avg_confidence FROM channel_attributions a JOIN acquisition_channels c ON a.channel_id=c.channel_id WHERE c.channel_name='品牌广告' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  a.attribution_type,
  COUNT(*) AS attributions,
  ROUND(CAST(AVG(a.confidence_score) AS DECIMAL), 4) AS avg_confidence
FROM channel_attributions AS a
JOIN acquisition_channels AS c
  ON a.channel_id = c.channel_id
WHERE
  c.channel_name = '品牌广告'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `67f3dc48d9db525c9dc3aa9e668f0fa55bd94afe343c9142c4217452ab9374f0`

PostgreSQL SQL SHA256: `e1071f47deed8d70139e4c2943fc390c38b7c8829f2e8d638fcb5dd1272e1f8d`

## CHANNEL_OPS-150

请汇总信息流广告渠道不同归因方式的数量和置信度；请返回归因方式、归因数量、平均置信度；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: attribution_type, attributions, avg_confidence. Filters: WHERE c.channel_name = '信息流广告'.

Output: `attribution_type, attributions, avg_confidence`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT a.attribution_type,COUNT(*) attributions,ROUND(AVG(a.confidence_score),4) avg_confidence FROM channel_attributions a JOIN acquisition_channels c ON a.channel_id=c.channel_id WHERE c.channel_name='信息流广告' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  a.attribution_type,
  COUNT(*) AS attributions,
  ROUND(CAST(AVG(a.confidence_score) AS DECIMAL), 4) AS avg_confidence
FROM channel_attributions AS a
JOIN acquisition_channels AS c
  ON a.channel_id = c.channel_id
WHERE
  c.channel_name = '信息流广告'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `697cd33152527196a64c897af501b3f80d42d9bed6138686a919a8da46cfee21`

PostgreSQL SQL SHA256: `3731a008ad9d67963e42ebcb8b0c64f4995358f5759276994d35f0936ba79ca1`

## CONTENT_OPS-003

2026-03每天的视频曝光量和播放量；请返回指标日期、曝光量、播放量；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, impressions, plays. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-03'.

Output: `metric_date, impressions, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date,SUM(impressions) impressions,SUM(play_count) plays FROM content_daily_metrics WHERE strftime(metric_date,'%Y-%m')='2026-03' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(impressions) AS impressions,
  SUM(play_count) AS plays
FROM content_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `318dd67f9c442519ecd6d59b3b7ee2b26f074d304e2d52bdaf5c5d3dc212102c`

PostgreSQL SQL SHA256: `ffd8f812426f9c52542ca1cab331dd500095fb3c78b29cecf741314d486f0ef2`

## CONTENT_OPS-004

2026-04每天的视频曝光量和播放量；请返回指标日期、曝光量、播放量；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, impressions, plays. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-04'.

Output: `metric_date, impressions, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date,SUM(impressions) impressions,SUM(play_count) plays FROM content_daily_metrics WHERE strftime(metric_date,'%Y-%m')='2026-04' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(impressions) AS impressions,
  SUM(play_count) AS plays
FROM content_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `89bb1fc789fa4ebca7805548b2f4c87003ecfaf2f87473a5ba14e8df65c386d9`

PostgreSQL SQL SHA256: `75b5de9d485cac0c07ee1a7c3ea9dd6ec990984a9e6c427f385aa86f16301c72`

## CONTENT_OPS-005

2026-05每天的视频曝光量和播放量；请返回指标日期、曝光量、播放量；聚合口径：可加总指标按当前查询粒度求和；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: metric_date, impressions, plays. Filters: WHERE TO_CHAR(metric_date, 'YYYY-MM') = '2026-05'.

Output: `metric_date, impressions, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT metric_date,SUM(impressions) impressions,SUM(play_count) plays FROM content_daily_metrics WHERE strftime(metric_date,'%Y-%m')='2026-05' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  metric_date,
  SUM(impressions) AS impressions,
  SUM(play_count) AS plays
FROM content_daily_metrics
WHERE
  TO_CHAR(metric_date, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `3e0d0d3a9f47dc37e6041376d383b42bb0929be46731facd4013a0e3890d85d3`

PostgreSQL SQL SHA256: `d3d4b71ffe660d58ac8ed648b6be55d8a4e91a8a32012ab996d20c313cd7f066`

## CONTENT_OPS-006

搞笑类内容的曝光量、播放量和播放率；请返回内容分类、曝光量、播放量、播放率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, impressions, plays, play_rate. Filters: WHERE cat.category_name = '搞笑'.

Output: `category_name, impressions, plays, play_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,SUM(m.impressions) impressions,SUM(m.play_count) plays, ROUND(SUM(m.play_count)*1.0/NULLIF(SUM(m.impressions),0),4) play_rate FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='搞笑' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  SUM(m.impressions) AS impressions,
  SUM(m.play_count) AS plays,
  ROUND(
    CAST(CAST(SUM(m.play_count) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(m.impressions), 0) AS DECIMAL),
    4
  ) AS play_rate
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '搞笑'
GROUP BY
  1
```

Original SQL SHA256: `8f3e392863442d19ee6cb41abc2e8526a50e7fe39ea3b4d1e2ac7b1c3b77dfd9`

PostgreSQL SQL SHA256: `e49b3caa5d21600c4ba330709e6ff912e92d9feecffbb9e41f0fcc75aeb988e7`

## CONTENT_OPS-007

生活类内容的曝光量、播放量和播放率；请返回内容分类、曝光量、播放量、播放率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, impressions, plays, play_rate. Filters: WHERE cat.category_name = '生活'.

Output: `category_name, impressions, plays, play_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,SUM(m.impressions) impressions,SUM(m.play_count) plays, ROUND(SUM(m.play_count)*1.0/NULLIF(SUM(m.impressions),0),4) play_rate FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='生活' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  SUM(m.impressions) AS impressions,
  SUM(m.play_count) AS plays,
  ROUND(
    CAST(CAST(SUM(m.play_count) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(m.impressions), 0) AS DECIMAL),
    4
  ) AS play_rate
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '生活'
GROUP BY
  1
```

Original SQL SHA256: `c26e5a82a8572695b49d1156c2fe57cf8d83f8ab9b0bc79486348e4220df1c6d`

PostgreSQL SQL SHA256: `f0807387238599054aa0d7d308a0020279d2e0282f626a5c1451b91a2fc83419`

## CONTENT_OPS-008

美食类内容的曝光量、播放量和播放率；请返回内容分类、曝光量、播放量、播放率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, impressions, plays, play_rate. Filters: WHERE cat.category_name = '美食'.

Output: `category_name, impressions, plays, play_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,SUM(m.impressions) impressions,SUM(m.play_count) plays, ROUND(SUM(m.play_count)*1.0/NULLIF(SUM(m.impressions),0),4) play_rate FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='美食' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  SUM(m.impressions) AS impressions,
  SUM(m.play_count) AS plays,
  ROUND(
    CAST(CAST(SUM(m.play_count) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(m.impressions), 0) AS DECIMAL),
    4
  ) AS play_rate
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '美食'
GROUP BY
  1
```

Original SQL SHA256: `6ef57c1219a9907d07765fa0d6e6a1d30b5eb3b613493f7c25554e5797922fa9`

PostgreSQL SQL SHA256: `3d3793227688f17427ae0642fb86dfea72c369a13ad581d4283ea5a403ba0323`

## CONTENT_OPS-009

知识类内容的曝光量、播放量和播放率；请返回内容分类、曝光量、播放量、播放率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, impressions, plays, play_rate. Filters: WHERE cat.category_name = '知识'.

Output: `category_name, impressions, plays, play_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,SUM(m.impressions) impressions,SUM(m.play_count) plays, ROUND(SUM(m.play_count)*1.0/NULLIF(SUM(m.impressions),0),4) play_rate FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='知识' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  SUM(m.impressions) AS impressions,
  SUM(m.play_count) AS plays,
  ROUND(
    CAST(CAST(SUM(m.play_count) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(m.impressions), 0) AS DECIMAL),
    4
  ) AS play_rate
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '知识'
GROUP BY
  1
```

Original SQL SHA256: `a7c49e6a54581db7ccfdaee680a05f9e13c6f46c973a1c106de33d59ff3c3142`

PostgreSQL SQL SHA256: `a97663496a01d8ef974ee8d8c54be49b2e9e1b17d0fd08b95f9073ac8c127c65`

## CONTENT_OPS-010

体育类内容的曝光量、播放量和播放率；请返回内容分类、曝光量、播放量、播放率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, impressions, plays, play_rate. Filters: WHERE cat.category_name = '体育'.

Output: `category_name, impressions, plays, play_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,SUM(m.impressions) impressions,SUM(m.play_count) plays, ROUND(SUM(m.play_count)*1.0/NULLIF(SUM(m.impressions),0),4) play_rate FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='体育' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  SUM(m.impressions) AS impressions,
  SUM(m.play_count) AS plays,
  ROUND(
    CAST(CAST(SUM(m.play_count) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(m.impressions), 0) AS DECIMAL),
    4
  ) AS play_rate
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '体育'
GROUP BY
  1
```

Original SQL SHA256: `06ec819ff99560366d7a14f0441dce0cbd8d6e3ea816c7802066795576575f1a`

PostgreSQL SQL SHA256: `faeadac66f631baffb14a0aa6f1cbd8d1fcceff219f6c4d07ce3dd78a5a7342e`

## CONTENT_OPS-011

首页推荐的曝光点击率和播放率；请返回推荐位置、曝光记录数、点击数、播放量、点击率、播放率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: position_name, exposures, clicks, plays, ctr, play_rate. Filters: WHERE e.position_name = '首页推荐'.

Output: `position_name, exposures, clicks, plays, ctr, play_rate`

Changes: `{"integer_truth_tests": [{"expression": "e.clicked", "table": "video_exposures", "column": "clicked", "physical_type": "bigint"}, {"expression": "e.clicked", "table": "video_exposures", "column": "clicked", "physical_type": "bigint"}], "round_numeric_cast_count": 2, "floating_division_count": 2, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT e.position_name,COUNT(*) exposures,SUM(CASE WHEN e.clicked THEN 1 ELSE 0 END) clicks, COUNT(p.play_id) plays,ROUND(SUM(CASE WHEN e.clicked THEN 1 ELSE 0 END)*1.0/COUNT(*),4) ctr, ROUND(COUNT(p.play_id)*1.0/COUNT(*),4) play_rate FROM video_exposures e LEFT JOIN video_plays p ON e.exposure_id=p.exposure_id WHERE e.position_name='首页推荐' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  e.position_name,
  COUNT(*) AS exposures,
  SUM(CASE WHEN e.clicked <> 0 THEN 1 ELSE 0 END) AS clicks,
  COUNT(p.play_id) AS plays,
  ROUND(
    CAST(CAST(SUM(CASE WHEN e.clicked <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS ctr,
  ROUND(CAST(CAST(COUNT(p.play_id) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL), 4) AS play_rate
FROM video_exposures AS e
LEFT JOIN video_plays AS p
  ON e.exposure_id = p.exposure_id
WHERE
  e.position_name = '首页推荐'
GROUP BY
  1
```

Original SQL SHA256: `843e175ee159c964c49af64faad48d64a4872dc13f246a642bda3b2d0035dce2`

PostgreSQL SQL SHA256: `018bc5260bb6ddc981f690d25893f43854755c297145bcb91cf16b01e973dad8`

## CONTENT_OPS-012

关注流的曝光点击率和播放率；请返回推荐位置、曝光记录数、点击数、播放量、点击率、播放率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: position_name, exposures, clicks, plays, ctr, play_rate. Filters: WHERE e.position_name = '关注流'.

Output: `position_name, exposures, clicks, plays, ctr, play_rate`

Changes: `{"integer_truth_tests": [{"expression": "e.clicked", "table": "video_exposures", "column": "clicked", "physical_type": "bigint"}, {"expression": "e.clicked", "table": "video_exposures", "column": "clicked", "physical_type": "bigint"}], "round_numeric_cast_count": 2, "floating_division_count": 2, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT e.position_name,COUNT(*) exposures,SUM(CASE WHEN e.clicked THEN 1 ELSE 0 END) clicks, COUNT(p.play_id) plays,ROUND(SUM(CASE WHEN e.clicked THEN 1 ELSE 0 END)*1.0/COUNT(*),4) ctr, ROUND(COUNT(p.play_id)*1.0/COUNT(*),4) play_rate FROM video_exposures e LEFT JOIN video_plays p ON e.exposure_id=p.exposure_id WHERE e.position_name='关注流' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  e.position_name,
  COUNT(*) AS exposures,
  SUM(CASE WHEN e.clicked <> 0 THEN 1 ELSE 0 END) AS clicks,
  COUNT(p.play_id) AS plays,
  ROUND(
    CAST(CAST(SUM(CASE WHEN e.clicked <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS ctr,
  ROUND(CAST(CAST(COUNT(p.play_id) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL), 4) AS play_rate
FROM video_exposures AS e
LEFT JOIN video_plays AS p
  ON e.exposure_id = p.exposure_id
WHERE
  e.position_name = '关注流'
GROUP BY
  1
```

Original SQL SHA256: `59bb1b291c287aac93562bc4eb65e95352a2db10e754a2db24ef7732f453dc42`

PostgreSQL SQL SHA256: `7c0614d530ff7ef6f48a74b40111c5fd6b9040dc0def9e0e2a963c7201fe9f06`

## CONTENT_OPS-013

同城的曝光点击率和播放率；请返回推荐位置、曝光记录数、点击数、播放量、点击率、播放率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: position_name, exposures, clicks, plays, ctr, play_rate. Filters: WHERE e.position_name = '同城'.

Output: `position_name, exposures, clicks, plays, ctr, play_rate`

Changes: `{"integer_truth_tests": [{"expression": "e.clicked", "table": "video_exposures", "column": "clicked", "physical_type": "bigint"}, {"expression": "e.clicked", "table": "video_exposures", "column": "clicked", "physical_type": "bigint"}], "round_numeric_cast_count": 2, "floating_division_count": 2, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT e.position_name,COUNT(*) exposures,SUM(CASE WHEN e.clicked THEN 1 ELSE 0 END) clicks, COUNT(p.play_id) plays,ROUND(SUM(CASE WHEN e.clicked THEN 1 ELSE 0 END)*1.0/COUNT(*),4) ctr, ROUND(COUNT(p.play_id)*1.0/COUNT(*),4) play_rate FROM video_exposures e LEFT JOIN video_plays p ON e.exposure_id=p.exposure_id WHERE e.position_name='同城' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  e.position_name,
  COUNT(*) AS exposures,
  SUM(CASE WHEN e.clicked <> 0 THEN 1 ELSE 0 END) AS clicks,
  COUNT(p.play_id) AS plays,
  ROUND(
    CAST(CAST(SUM(CASE WHEN e.clicked <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS ctr,
  ROUND(CAST(CAST(COUNT(p.play_id) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL), 4) AS play_rate
FROM video_exposures AS e
LEFT JOIN video_plays AS p
  ON e.exposure_id = p.exposure_id
WHERE
  e.position_name = '同城'
GROUP BY
  1
```

Original SQL SHA256: `8dde8c0f159306a7947e739159402914fa5437e1eaeb151e5950d06eae4b6a44`

PostgreSQL SQL SHA256: `22f71eb346934ac727da46ff2b8868f4105cc818a843b0ed573807cb9d389653`

## CONTENT_OPS-014

搜索结果的曝光点击率和播放率；请返回推荐位置、曝光记录数、点击数、播放量、点击率、播放率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: position_name, exposures, clicks, plays, ctr, play_rate. Filters: WHERE e.position_name = '搜索结果'.

Output: `position_name, exposures, clicks, plays, ctr, play_rate`

Changes: `{"integer_truth_tests": [{"expression": "e.clicked", "table": "video_exposures", "column": "clicked", "physical_type": "bigint"}, {"expression": "e.clicked", "table": "video_exposures", "column": "clicked", "physical_type": "bigint"}], "round_numeric_cast_count": 2, "floating_division_count": 2, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT e.position_name,COUNT(*) exposures,SUM(CASE WHEN e.clicked THEN 1 ELSE 0 END) clicks, COUNT(p.play_id) plays,ROUND(SUM(CASE WHEN e.clicked THEN 1 ELSE 0 END)*1.0/COUNT(*),4) ctr, ROUND(COUNT(p.play_id)*1.0/COUNT(*),4) play_rate FROM video_exposures e LEFT JOIN video_plays p ON e.exposure_id=p.exposure_id WHERE e.position_name='搜索结果' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  e.position_name,
  COUNT(*) AS exposures,
  SUM(CASE WHEN e.clicked <> 0 THEN 1 ELSE 0 END) AS clicks,
  COUNT(p.play_id) AS plays,
  ROUND(
    CAST(CAST(SUM(CASE WHEN e.clicked <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS ctr,
  ROUND(CAST(CAST(COUNT(p.play_id) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL), 4) AS play_rate
FROM video_exposures AS e
LEFT JOIN video_plays AS p
  ON e.exposure_id = p.exposure_id
WHERE
  e.position_name = '搜索结果'
GROUP BY
  1
```

Original SQL SHA256: `a81cbac4b0d3967bbe5e55a59483b5e69dc5d51312d026961e5492ac39611c90`

PostgreSQL SQL SHA256: `3c729093ce20580e8034bb3fe88d15db1aefb76fc09531af9a7620f59ef58650`

## CONTENT_OPS-015

话题页的曝光点击率和播放率；请返回推荐位置、曝光记录数、点击数、播放量、点击率、播放率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: position_name, exposures, clicks, plays, ctr, play_rate. Filters: WHERE e.position_name = '话题页'.

Output: `position_name, exposures, clicks, plays, ctr, play_rate`

Changes: `{"integer_truth_tests": [{"expression": "e.clicked", "table": "video_exposures", "column": "clicked", "physical_type": "bigint"}, {"expression": "e.clicked", "table": "video_exposures", "column": "clicked", "physical_type": "bigint"}], "round_numeric_cast_count": 2, "floating_division_count": 2, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT e.position_name,COUNT(*) exposures,SUM(CASE WHEN e.clicked THEN 1 ELSE 0 END) clicks, COUNT(p.play_id) plays,ROUND(SUM(CASE WHEN e.clicked THEN 1 ELSE 0 END)*1.0/COUNT(*),4) ctr, ROUND(COUNT(p.play_id)*1.0/COUNT(*),4) play_rate FROM video_exposures e LEFT JOIN video_plays p ON e.exposure_id=p.exposure_id WHERE e.position_name='话题页' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  e.position_name,
  COUNT(*) AS exposures,
  SUM(CASE WHEN e.clicked <> 0 THEN 1 ELSE 0 END) AS clicks,
  COUNT(p.play_id) AS plays,
  ROUND(
    CAST(CAST(SUM(CASE WHEN e.clicked <> 0 THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS ctr,
  ROUND(CAST(CAST(COUNT(p.play_id) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL), 4) AS play_rate
FROM video_exposures AS e
LEFT JOIN video_plays AS p
  ON e.exposure_id = p.exposure_id
WHERE
  e.position_name = '话题页'
GROUP BY
  1
```

Original SQL SHA256: `3ea696764e04765158e8d30ec26297a2c549c4002ed190a530de4ab6f92b8798`

PostgreSQL SQL SHA256: `72c114397f13ad1bc70035437b0a7027ab3db134089fd28a0ba256fefa738aa9`

## CONTENT_OPS-016

2026-01各内容分类播放量排名；请返回内容分类、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, plays. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-01'.

Output: `category_name, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,SUM(m.play_count) plays FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE strftime(m.metric_date,'%Y-%m')='2026-01' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  SUM(m.play_count) AS plays
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `c0060c79494cc09043c278e4dc1d12ae895d9413712ef6ca340d9f94fd561b71`

PostgreSQL SQL SHA256: `31ca6e834e7e7ce58c96122f8a904d1c4d69f28489d496a885f611c3cf925cce`

## CONTENT_OPS-017

2026-02各内容分类播放量排名；请返回内容分类、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, plays. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-02'.

Output: `category_name, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,SUM(m.play_count) plays FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE strftime(m.metric_date,'%Y-%m')='2026-02' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  SUM(m.play_count) AS plays
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `abc7a4b5d2b0e7f9eba7cc738547ad1adce762b1068187e26bf78d1a5e0e1ef1`

PostgreSQL SQL SHA256: `a6b54549a0ebf34b2c98cdd6a5b5e7f3c543ea56fa5bf1f37bfb64dfc54a47c0`

## CONTENT_OPS-018

2026-03各内容分类播放量排名；请返回内容分类、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, plays. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-03'.

Output: `category_name, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,SUM(m.play_count) plays FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE strftime(m.metric_date,'%Y-%m')='2026-03' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  SUM(m.play_count) AS plays
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `ea08fe05cd60140e83685cbe91c1e28357b3761c86ba2b5d50d6a0ff1cd94181`

PostgreSQL SQL SHA256: `6ef570f44d3ca7988fca3059a51d1f56617d31c4f99ddcd4c263c6a5d8033ee6`

## CONTENT_OPS-019

2026-04各内容分类播放量排名；请返回内容分类、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, plays. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-04'.

Output: `category_name, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,SUM(m.play_count) plays FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE strftime(m.metric_date,'%Y-%m')='2026-04' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  SUM(m.play_count) AS plays
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `4b4b087770e1282a0d6b1a68dc397a4e3d448f1876db6168b8d209fd277bfe3d`

PostgreSQL SQL SHA256: `ce261fc55f335d152354d0a01beba0cce18fac104037c0de44878a3ac856a8b6`

## CONTENT_OPS-020

2026-05各内容分类播放量排名；请返回内容分类、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, plays. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-05'.

Output: `category_name, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,SUM(m.play_count) plays FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE strftime(m.metric_date,'%Y-%m')='2026-05' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  SUM(m.play_count) AS plays
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `39c984b55ab73074e47014873d8ed684f1d660abdaa83bad16edfd95aed9e392`

PostgreSQL SQL SHA256: `36941bafbda425f0560cba1ea926a1c7af44d7813fcb4b3027751e4282e87eea`

## CONTENT_OPS-021

搞笑类播放量最高的前10条内容；请返回内容标题、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: content_title, plays. Filters: WHERE cat.category_name = '搞笑'.

Output: `content_title, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.content_title,SUM(m.play_count) plays FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='搞笑' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

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
  cat.category_name = '搞笑'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `d7038c53b7032062158801dfb267a4cb1c023f652fad0ce6844535d1b9a2d125`

PostgreSQL SQL SHA256: `43122951bf24841f2c417079909bcef939ef45f53cefdb6702ec079d8a091af4`

## CONTENT_OPS-022

生活类播放量最高的前10条内容；请返回内容标题、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: content_title, plays. Filters: WHERE cat.category_name = '生活'.

Output: `content_title, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.content_title,SUM(m.play_count) plays FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='生活' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

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
  cat.category_name = '生活'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `fcf88628ff228f7171bf8512b67ba64ed28c6fb6e8b157a3c313744d864e0321`

PostgreSQL SQL SHA256: `d379fdef09c8bfd20028a800b8884bd3ca046fc3a4ac7c8576a52be901d550ac`

## CONTENT_OPS-023

美食类播放量最高的前10条内容；请返回内容标题、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: content_title, plays. Filters: WHERE cat.category_name = '美食'.

Output: `content_title, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.content_title,SUM(m.play_count) plays FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='美食' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

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
  cat.category_name = '美食'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `c544ef9b8c9936853ece76251f36205bf64ca40d44430f2692dc212cd0ab0ac4`

PostgreSQL SQL SHA256: `e2bd744dcbeb2e1377b1471a546506d634bf885a959ea0d54bf63aad04202938`

## CONTENT_OPS-024

知识类播放量最高的前10条内容；请返回内容标题、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: content_title, plays. Filters: WHERE cat.category_name = '知识'.

Output: `content_title, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.content_title,SUM(m.play_count) plays FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='知识' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

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
  cat.category_name = '知识'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `f5a5a7bf9c5892d6114c8cecef71522bf7071cf32f9b71cc63836f298c7d16e3`

PostgreSQL SQL SHA256: `53daa43a00b60de4a986217ac778d7e74278ea0a7eaa31f5e3013852f1792f83`

## CONTENT_OPS-027

基于播放明细，计算生活类内容每次播放的平均观看时长和平均完播率；请返回内容分类、平均观看时长、平均完播率；聚合口径：平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, avg_watch_seconds, avg_completion_rate. Filters: WHERE cat.category_name = '生活'.

Output: `category_name, avg_watch_seconds, avg_completion_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,ROUND(AVG(p.watch_seconds),2) avg_watch_seconds, ROUND(AVG(p.completion_rate),4) avg_completion_rate FROM video_plays p JOIN contents c ON p.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='生活' GROUP BY 1
```

Explicit PostgreSQL SQL:

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
  cat.category_name = '生活'
GROUP BY
  1
```

Original SQL SHA256: `1336da7c4af1e21f96acb829ae00411c63e94ec7761ecf8c8801cbdba01e1f2d`

PostgreSQL SQL SHA256: `435749ebd7bf15cf54e2a31c1149e3f71f38b0bbfe4b5e025ed24cb75753bcc0`

## CONTENT_OPS-028

基于播放明细，计算美食类内容每次播放的平均观看时长和平均完播率；请返回内容分类、平均观看时长、平均完播率；聚合口径：平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, avg_watch_seconds, avg_completion_rate. Filters: WHERE cat.category_name = '美食'.

Output: `category_name, avg_watch_seconds, avg_completion_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,ROUND(AVG(p.watch_seconds),2) avg_watch_seconds, ROUND(AVG(p.completion_rate),4) avg_completion_rate FROM video_plays p JOIN contents c ON p.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='美食' GROUP BY 1
```

Explicit PostgreSQL SQL:

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
  cat.category_name = '美食'
GROUP BY
  1
```

Original SQL SHA256: `a8b33e2c8b01452e6cef0ef1e41f20188f2689484ae207008fa6ead4e79268dc`

PostgreSQL SQL SHA256: `a0347601de55fb0227ebbc4b27345252fef381fe0e7e258859baa334466bbb75`

## CONTENT_OPS-037

2026-02每天的有效互动数；请返回互动日期、互动数；聚合口径：数量指标按对应业务记录计数；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: interaction_date, interactions. Filters: WHERE valid_interaction <> 0 AND TO_CHAR(interacted_at, 'YYYY-MM') = '2026-02'.

Output: `interaction_date, interactions`

Changes: `{"integer_truth_tests": [{"expression": "valid_interaction", "table": "video_interactions", "column": "valid_interaction", "physical_type": "bigint"}], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT CAST(interacted_at AS DATE) interaction_date,COUNT(interaction_id) interactions FROM video_interactions WHERE valid_interaction AND strftime(interacted_at,'%Y-%m')='2026-02' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  CAST(interacted_at AS DATE) AS interaction_date,
  COUNT(interaction_id) AS interactions
FROM video_interactions
WHERE
  valid_interaction <> 0 AND TO_CHAR(interacted_at, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `988da06e1a355e00b611f85e0d013dcb14e33b1d532c6dc1f9c6e0ea7e63db30`

PostgreSQL SQL SHA256: `4748e379dce2fd49285c619bca6eecbba20b39ab21db0d97ebf4f1119f18f342`

## CONTENT_OPS-038

2026-03每天的有效互动数；请返回互动日期、互动数；聚合口径：数量指标按对应业务记录计数；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: interaction_date, interactions. Filters: WHERE valid_interaction <> 0 AND TO_CHAR(interacted_at, 'YYYY-MM') = '2026-03'.

Output: `interaction_date, interactions`

Changes: `{"integer_truth_tests": [{"expression": "valid_interaction", "table": "video_interactions", "column": "valid_interaction", "physical_type": "bigint"}], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT CAST(interacted_at AS DATE) interaction_date,COUNT(interaction_id) interactions FROM video_interactions WHERE valid_interaction AND strftime(interacted_at,'%Y-%m')='2026-03' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  CAST(interacted_at AS DATE) AS interaction_date,
  COUNT(interaction_id) AS interactions
FROM video_interactions
WHERE
  valid_interaction <> 0 AND TO_CHAR(interacted_at, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `126a02777fa4d586dcb619363ffe75401ebe612fd107c55ce0781f92512d3a3d`

PostgreSQL SQL SHA256: `68e9f038745e19500841245b987bf61c1d07ba66ee9ea32f77e7ee00e024a63a`

## CONTENT_OPS-039

2026-04每天的有效互动数；请返回互动日期、互动数；聚合口径：数量指标按对应业务记录计数；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: interaction_date, interactions. Filters: WHERE valid_interaction <> 0 AND TO_CHAR(interacted_at, 'YYYY-MM') = '2026-04'.

Output: `interaction_date, interactions`

Changes: `{"integer_truth_tests": [{"expression": "valid_interaction", "table": "video_interactions", "column": "valid_interaction", "physical_type": "bigint"}], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT CAST(interacted_at AS DATE) interaction_date,COUNT(interaction_id) interactions FROM video_interactions WHERE valid_interaction AND strftime(interacted_at,'%Y-%m')='2026-04' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  CAST(interacted_at AS DATE) AS interaction_date,
  COUNT(interaction_id) AS interactions
FROM video_interactions
WHERE
  valid_interaction <> 0 AND TO_CHAR(interacted_at, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `e80deda201b9f20af32c17f0141ff2c25988c370bafa6c60e8a8b1682f463e75`

PostgreSQL SQL SHA256: `2abc7b6720612e4967b8a7e6a3729fb21a1d90cf96772688d30c605e22b0ad68`

## CONTENT_OPS-040

2026-05每天的有效互动数；请返回互动日期、互动数；聚合口径：数量指标按对应业务记录计数；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: interaction_date, interactions. Filters: WHERE valid_interaction <> 0 AND TO_CHAR(interacted_at, 'YYYY-MM') = '2026-05'.

Output: `interaction_date, interactions`

Changes: `{"integer_truth_tests": [{"expression": "valid_interaction", "table": "video_interactions", "column": "valid_interaction", "physical_type": "bigint"}], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT CAST(interacted_at AS DATE) interaction_date,COUNT(interaction_id) interactions FROM video_interactions WHERE valid_interaction AND strftime(interacted_at,'%Y-%m')='2026-05' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  CAST(interacted_at AS DATE) AS interaction_date,
  COUNT(interaction_id) AS interactions
FROM video_interactions
WHERE
  valid_interaction <> 0 AND TO_CHAR(interacted_at, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `f2bdb9ef446e330d50487e07e85de52ce72dd804a81223633e4ad8ed43a1c5f2`

PostgreSQL SQL SHA256: `c4efe8b1f28b438a21401484bcd7a8cee9a6d9b99ec9d9fb7246f8148912d901`

## CONTENT_OPS-041

搞笑类内容整体互动率；请返回内容分类、互动数、播放量、互动率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, interactions, plays, interaction_rate. Filters: WHERE cat.category_name = '搞笑'.

Output: `category_name, interactions, plays, interaction_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,SUM(m.interaction_count) interactions,SUM(m.play_count) plays, ROUND(SUM(m.interaction_count)*1.0/NULLIF(SUM(m.play_count),0),4) interaction_rate FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='搞笑' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  SUM(m.interaction_count) AS interactions,
  SUM(m.play_count) AS plays,
  ROUND(
    CAST(CAST(SUM(m.interaction_count) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(m.play_count), 0) AS DECIMAL),
    4
  ) AS interaction_rate
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '搞笑'
GROUP BY
  1
```

Original SQL SHA256: `dac48ce160d33facb11de77605545c26a3a61664526ebe4256659c69f9da20dc`

PostgreSQL SQL SHA256: `76941fec2c2ba89c5e9c713d00e8e350e375b7f8a5f3b681bf3ada5e90d6e50f`

## CONTENT_OPS-042

生活类内容整体互动率；请返回内容分类、互动数、播放量、互动率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, interactions, plays, interaction_rate. Filters: WHERE cat.category_name = '生活'.

Output: `category_name, interactions, plays, interaction_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,SUM(m.interaction_count) interactions,SUM(m.play_count) plays, ROUND(SUM(m.interaction_count)*1.0/NULLIF(SUM(m.play_count),0),4) interaction_rate FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='生活' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  SUM(m.interaction_count) AS interactions,
  SUM(m.play_count) AS plays,
  ROUND(
    CAST(CAST(SUM(m.interaction_count) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(m.play_count), 0) AS DECIMAL),
    4
  ) AS interaction_rate
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '生活'
GROUP BY
  1
```

Original SQL SHA256: `4c9b1f64adb94230b43c84111dd6ac0e5ba75f2a287642391e3970302741b284`

PostgreSQL SQL SHA256: `8029bc5a84ca06cff25a25a2098c956763e31f1fac16f9162397ffbaf5e3b1be`

## CONTENT_OPS-043

美食类内容整体互动率；请返回内容分类、互动数、播放量、互动率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, interactions, plays, interaction_rate. Filters: WHERE cat.category_name = '美食'.

Output: `category_name, interactions, plays, interaction_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,SUM(m.interaction_count) interactions,SUM(m.play_count) plays, ROUND(SUM(m.interaction_count)*1.0/NULLIF(SUM(m.play_count),0),4) interaction_rate FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='美食' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  SUM(m.interaction_count) AS interactions,
  SUM(m.play_count) AS plays,
  ROUND(
    CAST(CAST(SUM(m.interaction_count) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(m.play_count), 0) AS DECIMAL),
    4
  ) AS interaction_rate
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '美食'
GROUP BY
  1
```

Original SQL SHA256: `e59c94be6e9ea093a0bb462aca40f2684e3e90ed20c1176548b9e0f7397d4c0f`

PostgreSQL SQL SHA256: `a72b20988a429d84a4ac9ba0aa8b6849ff2c3d7f37420a169e508df3df428e18`

## CONTENT_OPS-044

知识类内容整体互动率；请返回内容分类、互动数、播放量、互动率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, interactions, plays, interaction_rate. Filters: WHERE cat.category_name = '知识'.

Output: `category_name, interactions, plays, interaction_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,SUM(m.interaction_count) interactions,SUM(m.play_count) plays, ROUND(SUM(m.interaction_count)*1.0/NULLIF(SUM(m.play_count),0),4) interaction_rate FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='知识' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  SUM(m.interaction_count) AS interactions,
  SUM(m.play_count) AS plays,
  ROUND(
    CAST(CAST(SUM(m.interaction_count) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(m.play_count), 0) AS DECIMAL),
    4
  ) AS interaction_rate
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '知识'
GROUP BY
  1
```

Original SQL SHA256: `1a90417cf843264b550fffa5e3c81ff34f1bff6b265d697e3c6e822f14acbe6c`

PostgreSQL SQL SHA256: `f843ca3e6e31452ff2b72b741cb873f4a43687c2e35e46ea6bac40d781cdada9`

## CONTENT_OPS-045

体育类内容整体互动率；请返回内容分类、互动数、播放量、互动率；聚合口径：可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, interactions, plays, interaction_rate. Filters: WHERE cat.category_name = '体育'.

Output: `category_name, interactions, plays, interaction_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 1, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,SUM(m.interaction_count) interactions,SUM(m.play_count) plays, ROUND(SUM(m.interaction_count)*1.0/NULLIF(SUM(m.play_count),0),4) interaction_rate FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='体育' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  SUM(m.interaction_count) AS interactions,
  SUM(m.play_count) AS plays,
  ROUND(
    CAST(CAST(SUM(m.interaction_count) * 1.0 AS DOUBLE PRECISION) / NULLIF(SUM(m.play_count), 0) AS DECIMAL),
    4
  ) AS interaction_rate
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '体育'
GROUP BY
  1
```

Original SQL SHA256: `60f5849d4d2328db13a532b7f41d43c0cf3e759fa62b4a06108665992a369003`

PostgreSQL SQL SHA256: `4ff77fd6142e18016ca9ccf9720ea8e5a36dac6adc6ccc7d604ac56d69d90a5a`

## CONTENT_OPS-046

2026-01平均完播率最高的前10条内容；请返回内容标题、完播率；聚合口径：平均指标取算术平均；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: content_title, completion_rate. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-01'.

Output: `content_title, completion_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.content_title,ROUND(AVG(m.completion_rate),4) completion_rate FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id WHERE strftime(m.metric_date,'%Y-%m')='2026-01' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.content_title,
  ROUND(CAST(AVG(m.completion_rate) AS DECIMAL), 4) AS completion_rate
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `8ea076c6dff2ac6ec95b3749b2e22011aa61bf8c52a353fba43118adfaba5a2d`

PostgreSQL SQL SHA256: `9c42978677c3366e1013bd2723f4da25bbcaee87eeab3dd2c292b1c323c783ce`

## CONTENT_OPS-047

2026-02平均完播率最高的前10条内容；请返回内容标题、完播率；聚合口径：平均指标取算术平均；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: content_title, completion_rate. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-02'.

Output: `content_title, completion_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.content_title,ROUND(AVG(m.completion_rate),4) completion_rate FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id WHERE strftime(m.metric_date,'%Y-%m')='2026-02' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.content_title,
  ROUND(CAST(AVG(m.completion_rate) AS DECIMAL), 4) AS completion_rate
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `ca1092c4ddfde5e174cb20ee37bf278a511f505207ac6335c14873331c5426d1`

PostgreSQL SQL SHA256: `e1509c3629bf6fb5c65b14303ef2c0de3d2eef61768b0cb077ca52d68959f8fc`

## CONTENT_OPS-048

2026-03平均完播率最高的前10条内容；请返回内容标题、完播率；聚合口径：平均指标取算术平均；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: content_title, completion_rate. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-03'.

Output: `content_title, completion_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.content_title,ROUND(AVG(m.completion_rate),4) completion_rate FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id WHERE strftime(m.metric_date,'%Y-%m')='2026-03' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.content_title,
  ROUND(CAST(AVG(m.completion_rate) AS DECIMAL), 4) AS completion_rate
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `a961493b3bd3f85dfe48fd822260041c0caeb2f76595d1f6d3a6602afde9cc4a`

PostgreSQL SQL SHA256: `fe3e08fed99f1276e1409241890a615539c21b532cc2d77384e2b95e6e19e790`

## CONTENT_OPS-049

2026-04平均完播率最高的前10条内容；请返回内容标题、完播率；聚合口径：平均指标取算术平均；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: content_title, completion_rate. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-04'.

Output: `content_title, completion_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.content_title,ROUND(AVG(m.completion_rate),4) completion_rate FROM content_daily_metrics m JOIN contents c ON m.content_id=c.content_id WHERE strftime(m.metric_date,'%Y-%m')='2026-04' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.content_title,
  ROUND(CAST(AVG(m.completion_rate) AS DECIMAL), 4) AS completion_rate
FROM content_daily_metrics AS m
JOIN contents AS c
  ON m.content_id = c.content_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `4cad3e2c209c95fccb7ea75f70f62009c5f1dff57b9e5f1b75de91268dcc339c`

PostgreSQL SQL SHA256: `21f49b5bdae6ffe98aacdf9ba519744224576890719741d6614bc6797ea0fa83`

## CONTENT_OPS-053

美食类内容数量和平均视频时长；请返回内容分类、内容数量、平均视频时长；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, contents, avg_duration_seconds. Filters: WHERE cat.category_name = '美食'.

Output: `category_name, contents, avg_duration_seconds`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(c.content_id) contents,ROUND(AVG(c.duration_seconds),2) avg_duration_seconds FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='美食' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(c.content_id) AS contents,
  ROUND(CAST(AVG(c.duration_seconds) AS DECIMAL), 2) AS avg_duration_seconds
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '美食'
GROUP BY
  1
```

Original SQL SHA256: `962b3e9c5b85930e485c7863e413286ee3c8d533b3bd16204216df686a559303`

PostgreSQL SQL SHA256: `00d98c8fbcfaf75c66db5f4ef5d6d811613b783039ec372db8921e371c978de0`

## CONTENT_OPS-054

知识类内容数量和平均视频时长；请返回内容分类、内容数量、平均视频时长；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, contents, avg_duration_seconds. Filters: WHERE cat.category_name = '知识'.

Output: `category_name, contents, avg_duration_seconds`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(c.content_id) contents,ROUND(AVG(c.duration_seconds),2) avg_duration_seconds FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='知识' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(c.content_id) AS contents,
  ROUND(CAST(AVG(c.duration_seconds) AS DECIMAL), 2) AS avg_duration_seconds
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '知识'
GROUP BY
  1
```

Original SQL SHA256: `29937afc73136420812fe1dd8e066b7965c2006bb45491ef10f7828f712bb15e`

PostgreSQL SQL SHA256: `8a3e55ddc7f45f93e8ccdb81a0383cde3efd89528122cc160a489927d90cb102`

## CONTENT_OPS-055

体育类内容数量和平均视频时长；请返回内容分类、内容数量、平均视频时长；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, contents, avg_duration_seconds. Filters: WHERE cat.category_name = '体育'.

Output: `category_name, contents, avg_duration_seconds`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(c.content_id) contents,ROUND(AVG(c.duration_seconds),2) avg_duration_seconds FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='体育' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(c.content_id) AS contents,
  ROUND(CAST(AVG(c.duration_seconds) AS DECIMAL), 2) AS avg_duration_seconds
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '体育'
GROUP BY
  1
```

Original SQL SHA256: `7205576324e33a78760d7b950c54fb253b06737dc4c84ecf1d3cc15ddfc57cd5`

PostgreSQL SQL SHA256: `0829b1d6fd5534805cf6aef3aaf4769d77ce384fd72ebcc6a102f44e6193ea30`

## CONTENT_OPS-056

published内容按分类的数量分布；请返回内容分类、内容数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, contents. Filters: WHERE c.content_status = 'published'.

Output: `category_name, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(c.content_id) contents FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE c.content_status='published' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(c.content_id) AS contents
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  c.content_status = 'published'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `7253f0f9dbe25a50fbf1a5db6aa02660977b8a0f6c646a6e390ccee698c0c00c`

PostgreSQL SQL SHA256: `42aa48998998563840dc2e86feca6a3a14717fc1dfa82fdaddcf406edf99aada`

## CONTENT_OPS-057

removed内容按分类的数量分布；请返回内容分类、内容数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, contents. Filters: WHERE c.content_status = 'removed'.

Output: `category_name, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(c.content_id) contents FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE c.content_status='removed' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(c.content_id) AS contents
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  c.content_status = 'removed'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `27b9cd1480b8bc62d6c5850e32f89e6e197721ed306f6f8407699569b25a9002`

PostgreSQL SQL SHA256: `f606e46d3c534bb35a1e019c01d53b54a4aca1c6053a284352f970303ed02bae`

## CONTENT_OPS-058

请汇总published内容按分类的数量分布；请返回内容分类、内容数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, contents. Filters: WHERE c.content_status = 'published'.

Output: `category_name, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(c.content_id) contents FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE c.content_status='published' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(c.content_id) AS contents
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  c.content_status = 'published'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `7253f0f9dbe25a50fbf1a5db6aa02660977b8a0f6c646a6e390ccee698c0c00c`

PostgreSQL SQL SHA256: `42aa48998998563840dc2e86feca6a3a14717fc1dfa82fdaddcf406edf99aada`

## CONTENT_OPS-059

请汇总removed内容按分类的数量分布；请返回内容分类、内容数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, contents. Filters: WHERE c.content_status = 'removed'.

Output: `category_name, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(c.content_id) contents FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE c.content_status='removed' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(c.content_id) AS contents
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  c.content_status = 'removed'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `27b9cd1480b8bc62d6c5850e32f89e6e197721ed306f6f8407699569b25a9002`

PostgreSQL SQL SHA256: `f606e46d3c534bb35a1e019c01d53b54a4aca1c6053a284352f970303ed02bae`

## CONTENT_OPS-060

请分析published内容按分类的数量分布；请返回内容分类、内容数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, contents. Filters: WHERE c.content_status = 'published'.

Output: `category_name, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(c.content_id) contents FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE c.content_status='published' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(c.content_id) AS contents
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  c.content_status = 'published'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `7253f0f9dbe25a50fbf1a5db6aa02660977b8a0f6c646a6e390ccee698c0c00c`

PostgreSQL SQL SHA256: `42aa48998998563840dc2e86feca6a3a14717fc1dfa82fdaddcf406edf99aada`

## CONTENT_OPS-066

2026-01各分类新发布内容数量；请返回内容分类、内容数量；聚合口径：数量指标按对应业务记录计数；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, contents. Filters: WHERE TO_CHAR(c.published_at, 'YYYY-MM') = '2026-01'.

Output: `category_name, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(c.content_id) contents FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE strftime(c.published_at,'%Y-%m')='2026-01' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(c.content_id) AS contents
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  TO_CHAR(c.published_at, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `257f02815beb87abbe5089faa79ec9b98a187d58f79fabc3a37139cd26b8ccf5`

PostgreSQL SQL SHA256: `83a5ea455910305bf06b09b23ed814a31fbda352892417f9a04569d139588f15`

## CONTENT_OPS-067

2026-02各分类新发布内容数量；请返回内容分类、内容数量；聚合口径：数量指标按对应业务记录计数；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, contents. Filters: WHERE TO_CHAR(c.published_at, 'YYYY-MM') = '2026-02'.

Output: `category_name, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(c.content_id) contents FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE strftime(c.published_at,'%Y-%m')='2026-02' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(c.content_id) AS contents
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  TO_CHAR(c.published_at, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `8876550d40eeead0dcdadcce609940469474c16047310ac072efbe5cf99f6a65`

PostgreSQL SQL SHA256: `901fa2f953c877e15f7ba8f9d18d5b1a1bc711ab61acaeb39067f83f25a78921`

## CONTENT_OPS-068

2026-03各分类新发布内容数量；请返回内容分类、内容数量；聚合口径：数量指标按对应业务记录计数；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, contents. Filters: WHERE TO_CHAR(c.published_at, 'YYYY-MM') = '2026-03'.

Output: `category_name, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(c.content_id) contents FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE strftime(c.published_at,'%Y-%m')='2026-03' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(c.content_id) AS contents
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  TO_CHAR(c.published_at, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `8f35f8bdde4bebb403b5e9534834d64cbd501a9a741f51b49d991e0287a8b54f`

PostgreSQL SQL SHA256: `7840fc3ee7eec9fd0b963ca28de1403ad546d1a55c395bf0a21ed970a8237da1`

## CONTENT_OPS-069

2026-04各分类新发布内容数量；请返回内容分类、内容数量；聚合口径：数量指标按对应业务记录计数；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, contents. Filters: WHERE TO_CHAR(c.published_at, 'YYYY-MM') = '2026-04'.

Output: `category_name, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(c.content_id) contents FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE strftime(c.published_at,'%Y-%m')='2026-04' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(c.content_id) AS contents
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  TO_CHAR(c.published_at, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `1a202bf057f9579cf9003a0c4a544d6833e007301423c9079e3b5b00c6cc1526`

PostgreSQL SQL SHA256: `704d4596b2b65985c8c5ee208d798cc38777097a7366bc9c59af773e7ea06303`

## CONTENT_OPS-070

2026-05各分类新发布内容数量；请返回内容分类、内容数量；聚合口径：数量指标按对应业务记录计数；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, contents. Filters: WHERE TO_CHAR(c.published_at, 'YYYY-MM') = '2026-05'.

Output: `category_name, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(c.content_id) contents FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE strftime(c.published_at,'%Y-%m')='2026-05' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(c.content_id) AS contents
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  TO_CHAR(c.published_at, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `3fcb286dd834612e41d097bb771e974b1ece0307b4f9b19449f89cc4399fa506`

PostgreSQL SQL SHA256: `4dd2dab563137f68bcec53e2df53353a6bf95680c813152099e5c5876f284cc6`

## CONTENT_OPS-071

搞笑类内容的可见范围分布；请返回可见范围、内容数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: visibility, contents. Filters: WHERE cat.category_name = '搞笑'.

Output: `visibility, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.visibility,COUNT(c.content_id) contents FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='搞笑' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.visibility,
  COUNT(c.content_id) AS contents
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '搞笑'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `8d7fac2fbecdc2b9d4e167bbe9cc966ef096f32eee2788a0defa181bb966d760`

PostgreSQL SQL SHA256: `819b6b4b1c743f257677b08ae67eeed0be46323fe6ca17846887376b8e1a961b`

## CONTENT_OPS-072

生活类内容的可见范围分布；请返回可见范围、内容数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: visibility, contents. Filters: WHERE cat.category_name = '生活'.

Output: `visibility, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.visibility,COUNT(c.content_id) contents FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='生活' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.visibility,
  COUNT(c.content_id) AS contents
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '生活'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `285b6e38a084162a11240144bae4f6b9ca4089bb052fdb0de24e7d689e6a556b`

PostgreSQL SQL SHA256: `e4eb07959a1535e143a92e607fbed340212e797848d66ddbe27eef97f5fdedb7`

## CONTENT_OPS-073

美食类内容的可见范围分布；请返回可见范围、内容数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: visibility, contents. Filters: WHERE cat.category_name = '美食'.

Output: `visibility, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.visibility,COUNT(c.content_id) contents FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='美食' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.visibility,
  COUNT(c.content_id) AS contents
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '美食'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `1d14ee8d423350f25ed7b551eb11573104b899675df808071591037b2c009c5b`

PostgreSQL SQL SHA256: `b4764d94511f0264ec703d6782a6e8533865332102222901af7440ff51226a54`

## CONTENT_OPS-074

知识类内容的可见范围分布；请返回可见范围、内容数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: visibility, contents. Filters: WHERE cat.category_name = '知识'.

Output: `visibility, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.visibility,COUNT(c.content_id) contents FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='知识' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.visibility,
  COUNT(c.content_id) AS contents
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '知识'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `3631b7a95ecb8cdbc366a1fba73a0b153dffe45ca5501c1504dadca17b839565`

PostgreSQL SQL SHA256: `dd1d76936658f8081c4579fabc831a96c741840e24ec164d8d8554176b112446`

## CONTENT_OPS-075

体育类内容的可见范围分布；请返回可见范围、内容数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: visibility, contents. Filters: WHERE cat.category_name = '体育'.

Output: `visibility, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.visibility,COUNT(c.content_id) contents FROM contents c JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='体育' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.visibility,
  COUNT(c.content_id) AS contents
FROM contents AS c
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '体育'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `e200c032d44e19fb5606d9442683d31a7d5384549d038556318cad3906a090f6`

PostgreSQL SQL SHA256: `4550106eee4e651682679ba22b947d117551873c37591bd4f6ed56c1ff6f1464`

## CONTENT_OPS-078

成熟级创作者数量和状态分布；请返回创作者状态、创作者数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_status, creators. Filters: WHERE creator_level = '成熟'.

Output: `creator_status, creators`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT creator_status,COUNT(creator_id) creators FROM creators WHERE creator_level='成熟' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  creator_status,
  COUNT(creator_id) AS creators
FROM creators
WHERE
  creator_level = '成熟'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `314f5d5e1baa335a7d0824164b6e15a3fb274bdea08cf5f3790909a74ec8fa40`

PostgreSQL SQL SHA256: `4ffdcdfc9052811cc99871c63cfb224f210fa8b3c85941be342465060a39ca12`

## CONTENT_OPS-079

头部级创作者数量和状态分布；请返回创作者状态、创作者数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_status, creators. Filters: WHERE creator_level = '头部'.

Output: `creator_status, creators`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT creator_status,COUNT(creator_id) creators FROM creators WHERE creator_level='头部' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  creator_status,
  COUNT(creator_id) AS creators
FROM creators
WHERE
  creator_level = '头部'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `d511d73532ebe210aab2191ff8da83982f11b1a86ba4f1effae7704af5649320`

PostgreSQL SQL SHA256: `14af29f72a4c78411b3028aea7c68db08a414e86fee2aff2b716e0784199683b`

## CONTENT_OPS-080

请汇总新星级创作者数量和状态分布；请返回创作者状态、创作者数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_status, creators. Filters: WHERE creator_level = '新星'.

Output: `creator_status, creators`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT creator_status,COUNT(creator_id) creators FROM creators WHERE creator_level='新星' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

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

Original SQL SHA256: `ded5d20bd99178624576b6f89812f47864fe67fd5dd2af8fe5f5d7de4c90c3ee`

PostgreSQL SQL SHA256: `74232ac14d9de90a027fa4b65c567b5fa494c1dca2c1b456d354e76c892d38d5`

## CONTENT_OPS-081

主营搞笑的创作者粉丝数和质量分；请返回内容分类、创作者数量、平均粉丝数、平均质量分；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, creators, avg_followers, avg_quality_score. Filters: WHERE cat.category_name = '搞笑'.

Output: `category_name, creators, avg_followers, avg_quality_score`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(*) creators,ROUND(AVG(p.follower_count),2) avg_followers, ROUND(AVG(p.quality_score),2) avg_quality_score FROM creator_profiles p JOIN content_categories cat ON p.primary_category_id=cat.category_id WHERE cat.category_name='搞笑' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(*) AS creators,
  ROUND(CAST(AVG(p.follower_count) AS DECIMAL), 2) AS avg_followers,
  ROUND(CAST(AVG(p.quality_score) AS DECIMAL), 2) AS avg_quality_score
FROM creator_profiles AS p
JOIN content_categories AS cat
  ON p.primary_category_id = cat.category_id
WHERE
  cat.category_name = '搞笑'
GROUP BY
  1
```

Original SQL SHA256: `b9d0bcd14a29b8541c759158f2dac48dfcc550e9615b3fac9a29d9f23a10277e`

PostgreSQL SQL SHA256: `0d073142b4b6196206f62850316d59b19ff1513042a09245e74642f71b1bde44`

## CONTENT_OPS-082

主营生活的创作者粉丝数和质量分；请返回内容分类、创作者数量、平均粉丝数、平均质量分；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, creators, avg_followers, avg_quality_score. Filters: WHERE cat.category_name = '生活'.

Output: `category_name, creators, avg_followers, avg_quality_score`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(*) creators,ROUND(AVG(p.follower_count),2) avg_followers, ROUND(AVG(p.quality_score),2) avg_quality_score FROM creator_profiles p JOIN content_categories cat ON p.primary_category_id=cat.category_id WHERE cat.category_name='生活' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(*) AS creators,
  ROUND(CAST(AVG(p.follower_count) AS DECIMAL), 2) AS avg_followers,
  ROUND(CAST(AVG(p.quality_score) AS DECIMAL), 2) AS avg_quality_score
FROM creator_profiles AS p
JOIN content_categories AS cat
  ON p.primary_category_id = cat.category_id
WHERE
  cat.category_name = '生活'
GROUP BY
  1
```

Original SQL SHA256: `0fe5c5cd88d6bff0f5866f235c704b3514b7d9dd957c460b7c0a633b0ebd5d1d`

PostgreSQL SQL SHA256: `f2d8d0e6b35ce2034a94b34b88abea5b64605556819fdf6e65281bcfcdae190b`

## CONTENT_OPS-083

主营美食的创作者粉丝数和质量分；请返回内容分类、创作者数量、平均粉丝数、平均质量分；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, creators, avg_followers, avg_quality_score. Filters: WHERE cat.category_name = '美食'.

Output: `category_name, creators, avg_followers, avg_quality_score`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(*) creators,ROUND(AVG(p.follower_count),2) avg_followers, ROUND(AVG(p.quality_score),2) avg_quality_score FROM creator_profiles p JOIN content_categories cat ON p.primary_category_id=cat.category_id WHERE cat.category_name='美食' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(*) AS creators,
  ROUND(CAST(AVG(p.follower_count) AS DECIMAL), 2) AS avg_followers,
  ROUND(CAST(AVG(p.quality_score) AS DECIMAL), 2) AS avg_quality_score
FROM creator_profiles AS p
JOIN content_categories AS cat
  ON p.primary_category_id = cat.category_id
WHERE
  cat.category_name = '美食'
GROUP BY
  1
```

Original SQL SHA256: `d2ea7cb3b9d2763e35b8ca7078376efbc8a89a852e0650b45b85004872a910f1`

PostgreSQL SQL SHA256: `cb334ad3c883e9b9e3794304febbd9feba25c3d7950fd2f639e111a7b64c38a1`

## CONTENT_OPS-084

主营知识的创作者粉丝数和质量分；请返回内容分类、创作者数量、平均粉丝数、平均质量分；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, creators, avg_followers, avg_quality_score. Filters: WHERE cat.category_name = '知识'.

Output: `category_name, creators, avg_followers, avg_quality_score`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(*) creators,ROUND(AVG(p.follower_count),2) avg_followers, ROUND(AVG(p.quality_score),2) avg_quality_score FROM creator_profiles p JOIN content_categories cat ON p.primary_category_id=cat.category_id WHERE cat.category_name='知识' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(*) AS creators,
  ROUND(CAST(AVG(p.follower_count) AS DECIMAL), 2) AS avg_followers,
  ROUND(CAST(AVG(p.quality_score) AS DECIMAL), 2) AS avg_quality_score
FROM creator_profiles AS p
JOIN content_categories AS cat
  ON p.primary_category_id = cat.category_id
WHERE
  cat.category_name = '知识'
GROUP BY
  1
```

Original SQL SHA256: `8fae21dd7cc65df90a7a8dda4b7873aff85d34f458eb84df5d1478601eb59394`

PostgreSQL SQL SHA256: `c0ba94fc23451768c07a1b9b8c6a351c03dd3dfdc9706b3286aa6bb60120f38f`

## CONTENT_OPS-085

主营体育的创作者粉丝数和质量分；请返回内容分类、创作者数量、平均粉丝数、平均质量分；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, creators, avg_followers, avg_quality_score. Filters: WHERE cat.category_name = '体育'.

Output: `category_name, creators, avg_followers, avg_quality_score`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(*) creators,ROUND(AVG(p.follower_count),2) avg_followers, ROUND(AVG(p.quality_score),2) avg_quality_score FROM creator_profiles p JOIN content_categories cat ON p.primary_category_id=cat.category_id WHERE cat.category_name='体育' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(*) AS creators,
  ROUND(CAST(AVG(p.follower_count) AS DECIMAL), 2) AS avg_followers,
  ROUND(CAST(AVG(p.quality_score) AS DECIMAL), 2) AS avg_quality_score
FROM creator_profiles AS p
JOIN content_categories AS cat
  ON p.primary_category_id = cat.category_id
WHERE
  cat.category_name = '体育'
GROUP BY
  1
```

Original SQL SHA256: `00058efc63e3242a27c823cadb36acd38552d8aba139102e065764b5a56e131d`

PostgreSQL SQL SHA256: `b3e127cc69bc2119247a619edfdde4b300e74fc1ec0619ecc4c2b100b5afb929`

## CONTENT_OPS-086

2026年8月新星级创作者播放量前10名；请返回创作者名称、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_name, plays. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '新星'.

Output: `creator_name, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creator_name,SUM(m.play_count) plays FROM creator_daily_metrics m JOIN creators c ON m.creator_id=c.creator_id WHERE strftime(m.metric_date,'%Y-%m')='2026-08' AND c.creator_level='新星' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creator_name,
  SUM(m.play_count) AS plays
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

Original SQL SHA256: `ac6e5af1102d0d274104e12e35d16602537d477f773c24b06a945d2bd2671fc6`

PostgreSQL SQL SHA256: `21df18e20206483176533c8458d789fed9c93ac89806b60b1de768b422ae9680`

## CONTENT_OPS-087

2026年8月成长级创作者播放量前10名；请返回创作者名称、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_name, plays. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '成长'.

Output: `creator_name, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creator_name,SUM(m.play_count) plays FROM creator_daily_metrics m JOIN creators c ON m.creator_id=c.creator_id WHERE strftime(m.metric_date,'%Y-%m')='2026-08' AND c.creator_level='成长' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creator_name,
  SUM(m.play_count) AS plays
FROM creator_daily_metrics AS m
JOIN creators AS c
  ON m.creator_id = c.creator_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '成长'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `3bf84073cdf67b40b4184ae0454ca7b17085b07d66e4815b82729a02d1031b73`

PostgreSQL SQL SHA256: `249c0c4560973051e3cc6fb5ee96847a96a26d45798d7f928ef634c5f34a5d55`

## CONTENT_OPS-088

2026年8月成熟级创作者播放量前10名；请返回创作者名称、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_name, plays. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '成熟'.

Output: `creator_name, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creator_name,SUM(m.play_count) plays FROM creator_daily_metrics m JOIN creators c ON m.creator_id=c.creator_id WHERE strftime(m.metric_date,'%Y-%m')='2026-08' AND c.creator_level='成熟' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creator_name,
  SUM(m.play_count) AS plays
FROM creator_daily_metrics AS m
JOIN creators AS c
  ON m.creator_id = c.creator_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '成熟'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `06f689cf665bf8020625703c660f0d2fe62583045276cdc13d31dfda289fca9b`

PostgreSQL SQL SHA256: `d4c89ead71ff6eff15df0fa73e12e79e649f40d62ad30f446785877fee63d18d`

## CONTENT_OPS-089

2026年8月头部级创作者播放量前10名；请返回创作者名称、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_name, plays. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '头部'.

Output: `creator_name, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creator_name,SUM(m.play_count) plays FROM creator_daily_metrics m JOIN creators c ON m.creator_id=c.creator_id WHERE strftime(m.metric_date,'%Y-%m')='2026-08' AND c.creator_level='头部' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creator_name,
  SUM(m.play_count) AS plays
FROM creator_daily_metrics AS m
JOIN creators AS c
  ON m.creator_id = c.creator_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '头部'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `aed91307260aa02ff843e68c834d1e6fb9cf0e1fe1df0f843731aab21b23567a`

PostgreSQL SQL SHA256: `7689f8442b8a422b1bd14c8875825c06ee4169c4e0ce2914989d58ab8a85b7ab`

## CONTENT_OPS-090

请汇总2026年8月新星级创作者播放量前10名；请返回创作者名称、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_name, plays. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '新星'.

Output: `creator_name, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creator_name,SUM(m.play_count) plays FROM creator_daily_metrics m JOIN creators c ON m.creator_id=c.creator_id WHERE strftime(m.metric_date,'%Y-%m')='2026-08' AND c.creator_level='新星' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creator_name,
  SUM(m.play_count) AS plays
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

Original SQL SHA256: `ac6e5af1102d0d274104e12e35d16602537d477f773c24b06a945d2bd2671fc6`

PostgreSQL SQL SHA256: `21df18e20206483176533c8458d789fed9c93ac89806b60b1de768b422ae9680`

## CONTENT_OPS-091

2026年8月新星级创作者发布内容数前10名；请返回创作者名称、发布内容数；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_name, published_count. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '新星'.

Output: `creator_name, published_count`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creator_name,SUM(m.published_count) published_count FROM creator_daily_metrics m JOIN creators c ON m.creator_id=c.creator_id WHERE strftime(m.metric_date,'%Y-%m')='2026-08' AND c.creator_level='新星' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creator_name,
  SUM(m.published_count) AS published_count
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

Original SQL SHA256: `52ad95d17d5363b54f3c9833cffb2993fa51bc00e28618d17239cfb18e34737c`

PostgreSQL SQL SHA256: `3dc2c61be6363e3571ea368c2b2111612f4065ef662d2c2251b8301a3df80130`

## CONTENT_OPS-092

2026年8月成长级创作者发布内容数前10名；请返回创作者名称、发布内容数；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_name, published_count. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '成长'.

Output: `creator_name, published_count`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creator_name,SUM(m.published_count) published_count FROM creator_daily_metrics m JOIN creators c ON m.creator_id=c.creator_id WHERE strftime(m.metric_date,'%Y-%m')='2026-08' AND c.creator_level='成长' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creator_name,
  SUM(m.published_count) AS published_count
FROM creator_daily_metrics AS m
JOIN creators AS c
  ON m.creator_id = c.creator_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '成长'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `17e05708fcf54af8b923a8357c54bac3c26d49bfbd04756803e0ef84352b0cad`

PostgreSQL SQL SHA256: `0a8e1d514301495f289c8d2a9db62e93656387ddf96ec9990fc1d6f4e933a97b`

## CONTENT_OPS-093

2026年8月成熟级创作者发布内容数前10名；请返回创作者名称、发布内容数；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_name, published_count. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '成熟'.

Output: `creator_name, published_count`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creator_name,SUM(m.published_count) published_count FROM creator_daily_metrics m JOIN creators c ON m.creator_id=c.creator_id WHERE strftime(m.metric_date,'%Y-%m')='2026-08' AND c.creator_level='成熟' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creator_name,
  SUM(m.published_count) AS published_count
FROM creator_daily_metrics AS m
JOIN creators AS c
  ON m.creator_id = c.creator_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '成熟'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `55b2a7993fc72071dd08454f702ce7f72b8fe05bb2c24e68b80a29c091b3ae4e`

PostgreSQL SQL SHA256: `a9c29b14b31c36bdb14f2697f8868ec82912aa31bb48f2e38071d65d97d326c8`

## CONTENT_OPS-094

2026年8月头部级创作者发布内容数前10名；请返回创作者名称、发布内容数；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_name, published_count. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '头部'.

Output: `creator_name, published_count`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creator_name,SUM(m.published_count) published_count FROM creator_daily_metrics m JOIN creators c ON m.creator_id=c.creator_id WHERE strftime(m.metric_date,'%Y-%m')='2026-08' AND c.creator_level='头部' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creator_name,
  SUM(m.published_count) AS published_count
FROM creator_daily_metrics AS m
JOIN creators AS c
  ON m.creator_id = c.creator_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '头部'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `9cfc5d67daa728337b40cbce18f93127f9f64f1cd77aa9af64744a89bc593364`

PostgreSQL SQL SHA256: `d8e6b4c216042a0646bc85becabc4948e63c99477ccd495b698c2627c15e5619`

## CONTENT_OPS-095

请汇总2026年8月新星级创作者发布内容数前10名；请返回创作者名称、发布内容数；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_name, published_count. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '新星'.

Output: `creator_name, published_count`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creator_name,SUM(m.published_count) published_count FROM creator_daily_metrics m JOIN creators c ON m.creator_id=c.creator_id WHERE strftime(m.metric_date,'%Y-%m')='2026-08' AND c.creator_level='新星' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creator_name,
  SUM(m.published_count) AS published_count
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

Original SQL SHA256: `52ad95d17d5363b54f3c9833cffb2993fa51bc00e28618d17239cfb18e34737c`

PostgreSQL SQL SHA256: `3dc2c61be6363e3571ea368c2b2111612f4065ef662d2c2251b8301a3df80130`

## CONTENT_OPS-096

查询2026年8月新星级创作者的每日互动率算术平均值前10名；请返回创作者名称、互动率；聚合口径：平均指标取算术平均；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_name, interaction_rate. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '新星'.

Output: `creator_name, interaction_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creator_name,ROUND(AVG(m.interaction_rate),4) interaction_rate FROM creator_daily_metrics m JOIN creators c ON m.creator_id=c.creator_id WHERE strftime(m.metric_date,'%Y-%m')='2026-08' AND c.creator_level='新星' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

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

Original SQL SHA256: `9ac27d4b16f06920cc5828bff84ffdc181de8858dd8e7533c992a5ee730f6d4f`

PostgreSQL SQL SHA256: `192a2ae8796ab6ee263d11015eb04efd072ffe569d3cc1b14bb1c71614b302cb`

## CONTENT_OPS-097

查询2026年8月成长级创作者的每日互动率算术平均值前10名；请返回创作者名称、互动率；聚合口径：平均指标取算术平均；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_name, interaction_rate. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '成长'.

Output: `creator_name, interaction_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creator_name,ROUND(AVG(m.interaction_rate),4) interaction_rate FROM creator_daily_metrics m JOIN creators c ON m.creator_id=c.creator_id WHERE strftime(m.metric_date,'%Y-%m')='2026-08' AND c.creator_level='成长' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creator_name,
  ROUND(CAST(AVG(m.interaction_rate) AS DECIMAL), 4) AS interaction_rate
FROM creator_daily_metrics AS m
JOIN creators AS c
  ON m.creator_id = c.creator_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '成长'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `e6d29c6383fdd37690e11b2d5fedc6cb392e8c6c6dea9dd7d4cd97d30c57b4b3`

PostgreSQL SQL SHA256: `9db3e6627431def920fb53ce212549bf087ec77f10c153caaac67474a7316385`

## CONTENT_OPS-098

查询2026年8月成熟级创作者的每日互动率算术平均值前10名；请返回创作者名称、互动率；聚合口径：平均指标取算术平均；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_name, interaction_rate. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '成熟'.

Output: `creator_name, interaction_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creator_name,ROUND(AVG(m.interaction_rate),4) interaction_rate FROM creator_daily_metrics m JOIN creators c ON m.creator_id=c.creator_id WHERE strftime(m.metric_date,'%Y-%m')='2026-08' AND c.creator_level='成熟' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creator_name,
  ROUND(CAST(AVG(m.interaction_rate) AS DECIMAL), 4) AS interaction_rate
FROM creator_daily_metrics AS m
JOIN creators AS c
  ON m.creator_id = c.creator_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '成熟'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `3069300037830b6c2fb0d5f6c3b1813b54b39b24f9cfd9563527970202a1c6d1`

PostgreSQL SQL SHA256: `2550e71a44359dbd3669a7be4f4b83a5245c305d9bc1e4aa41319ec642a124c0`

## CONTENT_OPS-099

查询2026年8月头部级创作者的每日互动率算术平均值前10名；请返回创作者名称、互动率；聚合口径：平均指标取算术平均；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: creator_name, interaction_rate. Filters: WHERE TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '头部'.

Output: `creator_name, interaction_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT c.creator_name,ROUND(AVG(m.interaction_rate),4) interaction_rate FROM creator_daily_metrics m JOIN creators c ON m.creator_id=c.creator_id WHERE strftime(m.metric_date,'%Y-%m')='2026-08' AND c.creator_level='头部' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  c.creator_name,
  ROUND(CAST(AVG(m.interaction_rate) AS DECIMAL), 4) AS interaction_rate
FROM creator_daily_metrics AS m
JOIN creators AS c
  ON m.creator_id = c.creator_id
WHERE
  TO_CHAR(m.metric_date, 'YYYY-MM') = '2026-08' AND c.creator_level = '头部'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `dabc2400b9fa668cc3ac85bb8d167662c99b039bef3205435b4be3c259e26c11`

PostgreSQL SQL SHA256: `aa8449189b5bb0f71edc099627823c227005cd7c432728039ed832787490fc1e`

## CONTENT_OPS-102

trend类型内容标签的使用次数；请返回标签名称、使用次数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: tag_name, uses. Filters: WHERE t.tag_type = 'trend'.

Output: `tag_name, uses`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT t.tag_name,COUNT(r.content_id) uses FROM content_tags t JOIN content_tag_relations r ON t.content_tag_id=r.content_tag_id WHERE t.tag_type='trend' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  t.tag_name,
  COUNT(r.content_id) AS uses
FROM content_tags AS t
JOIN content_tag_relations AS r
  ON t.content_tag_id = r.content_tag_id
WHERE
  t.tag_type = 'trend'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `939bbaf793f113a7ae0a4f42dd085d4b45ad03384cf4c4043972842795dd7d93`

PostgreSQL SQL SHA256: `f12cbebdc14088c5da8913e47e142b450feb872edc716ca163362709039c1346`

## CONTENT_OPS-103

audience类型内容标签的使用次数；请返回标签名称、使用次数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: tag_name, uses. Filters: WHERE t.tag_type = 'audience'.

Output: `tag_name, uses`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT t.tag_name,COUNT(r.content_id) uses FROM content_tags t JOIN content_tag_relations r ON t.content_tag_id=r.content_tag_id WHERE t.tag_type='audience' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  t.tag_name,
  COUNT(r.content_id) AS uses
FROM content_tags AS t
JOIN content_tag_relations AS r
  ON t.content_tag_id = r.content_tag_id
WHERE
  t.tag_type = 'audience'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `39616b10dbf8b5c1f9806074869df9725a44a11e4995d370191a65120d9c497a`

PostgreSQL SQL SHA256: `23efe8619a0c4121a0a687ebced7e12b3f77a996bf9b0c1abe93dae2ac33d2d8`

## CONTENT_OPS-104

style类型内容标签的使用次数；请返回标签名称、使用次数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: tag_name, uses. Filters: WHERE t.tag_type = 'style'.

Output: `tag_name, uses`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT t.tag_name,COUNT(r.content_id) uses FROM content_tags t JOIN content_tag_relations r ON t.content_tag_id=r.content_tag_id WHERE t.tag_type='style' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  t.tag_name,
  COUNT(r.content_id) AS uses
FROM content_tags AS t
JOIN content_tag_relations AS r
  ON t.content_tag_id = r.content_tag_id
WHERE
  t.tag_type = 'style'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `a3a74a5ec672287b59526c9af1ea3417ee9305f380842821fbe449eadfe7fd5e`

PostgreSQL SQL SHA256: `7903ac20da4cd307092e73f067d33c21902506e2a7b3ad929161d6997d357f19`

## CONTENT_OPS-105

scene类型内容标签的使用次数；请返回标签名称、使用次数；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: tag_name, uses. Filters: WHERE t.tag_type = 'scene'.

Output: `tag_name, uses`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT t.tag_name,COUNT(r.content_id) uses FROM content_tags t JOIN content_tag_relations r ON t.content_tag_id=r.content_tag_id WHERE t.tag_type='scene' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  t.tag_name,
  COUNT(r.content_id) AS uses
FROM content_tags AS t
JOIN content_tag_relations AS r
  ON t.content_tag_id = r.content_tag_id
WHERE
  t.tag_type = 'scene'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `d7dd2802667ca2b8080b453a35c568bc3147f260747006d327036f47709a40c5`

PostgreSQL SQL SHA256: `6928c41070885aa95885116e716fc3055f16a7e51b6da0862545441efd4a0680`

## CONTENT_OPS-106

搞笑类内容中播放量最高的前10个标签；请返回标签名称、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: tag_name, plays. Filters: WHERE cat.category_name = '搞笑'.

Output: `tag_name, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT t.tag_name,SUM(m.play_count) plays FROM content_tag_relations r JOIN content_tags t ON r.content_tag_id=t.content_tag_id JOIN contents c ON r.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id JOIN content_daily_metrics m ON c.content_id=m.content_id WHERE cat.category_name='搞笑' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  t.tag_name,
  SUM(m.play_count) AS plays
FROM content_tag_relations AS r
JOIN content_tags AS t
  ON r.content_tag_id = t.content_tag_id
JOIN contents AS c
  ON r.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
JOIN content_daily_metrics AS m
  ON c.content_id = m.content_id
WHERE
  cat.category_name = '搞笑'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `b5ebc7e304b84c979010ed29108149334a0e99ef3a8e8359528c4eb81980f1c9`

PostgreSQL SQL SHA256: `d89e7183e8d2a09d02e63b977e8ab21dc4e8ffc5df89cce0871a1681fc245b1c`

## CONTENT_OPS-107

生活类内容中播放量最高的前10个标签；请返回标签名称、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: tag_name, plays. Filters: WHERE cat.category_name = '生活'.

Output: `tag_name, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT t.tag_name,SUM(m.play_count) plays FROM content_tag_relations r JOIN content_tags t ON r.content_tag_id=t.content_tag_id JOIN contents c ON r.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id JOIN content_daily_metrics m ON c.content_id=m.content_id WHERE cat.category_name='生活' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  t.tag_name,
  SUM(m.play_count) AS plays
FROM content_tag_relations AS r
JOIN content_tags AS t
  ON r.content_tag_id = t.content_tag_id
JOIN contents AS c
  ON r.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
JOIN content_daily_metrics AS m
  ON c.content_id = m.content_id
WHERE
  cat.category_name = '生活'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `93dbefe74ed2a1999893aeaba7feeeb5c52bd57b06a2ee5587b9e106465f4f65`

PostgreSQL SQL SHA256: `223f59d97cf0a42256bf44fc40379686ebf396412eaee3c53d02c4a9ab078a16`

## CONTENT_OPS-108

美食类内容中播放量最高的前10个标签；请返回标签名称、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: tag_name, plays. Filters: WHERE cat.category_name = '美食'.

Output: `tag_name, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT t.tag_name,SUM(m.play_count) plays FROM content_tag_relations r JOIN content_tags t ON r.content_tag_id=t.content_tag_id JOIN contents c ON r.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id JOIN content_daily_metrics m ON c.content_id=m.content_id WHERE cat.category_name='美食' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  t.tag_name,
  SUM(m.play_count) AS plays
FROM content_tag_relations AS r
JOIN content_tags AS t
  ON r.content_tag_id = t.content_tag_id
JOIN contents AS c
  ON r.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
JOIN content_daily_metrics AS m
  ON c.content_id = m.content_id
WHERE
  cat.category_name = '美食'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `888bbb73cdbcc33483d30a222f682d66cbbc76eed1135914b0310a430dc24ecb`

PostgreSQL SQL SHA256: `336681bb86985fd6c222cfd8b47f28354ffc85269e25bac2ae0538678f162f44`

## CONTENT_OPS-109

知识类内容中播放量最高的前10个标签；请返回标签名称、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: tag_name, plays. Filters: WHERE cat.category_name = '知识'.

Output: `tag_name, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT t.tag_name,SUM(m.play_count) plays FROM content_tag_relations r JOIN content_tags t ON r.content_tag_id=t.content_tag_id JOIN contents c ON r.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id JOIN content_daily_metrics m ON c.content_id=m.content_id WHERE cat.category_name='知识' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  t.tag_name,
  SUM(m.play_count) AS plays
FROM content_tag_relations AS r
JOIN content_tags AS t
  ON r.content_tag_id = t.content_tag_id
JOIN contents AS c
  ON r.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
JOIN content_daily_metrics AS m
  ON c.content_id = m.content_id
WHERE
  cat.category_name = '知识'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `0b00a41f0097cee392dba027119359b74a33d1a1bff13851cfb00655fca9c8f0`

PostgreSQL SQL SHA256: `05863d499c2453555ed0b857a2b5b2134747cc8a3aa3e886a779d4df7f0bd444`

## CONTENT_OPS-110

体育类内容中播放量最高的前10个标签；请返回标签名称、播放量；聚合口径：可加总指标按当前查询粒度求和；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: tag_name, plays. Filters: WHERE cat.category_name = '体育'.

Output: `tag_name, plays`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT t.tag_name,SUM(m.play_count) plays FROM content_tag_relations r JOIN content_tags t ON r.content_tag_id=t.content_tag_id JOIN contents c ON r.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id JOIN content_daily_metrics m ON c.content_id=m.content_id WHERE cat.category_name='体育' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  t.tag_name,
  SUM(m.play_count) AS plays
FROM content_tag_relations AS r
JOIN content_tags AS t
  ON r.content_tag_id = t.content_tag_id
JOIN contents AS c
  ON r.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
JOIN content_daily_metrics AS m
  ON c.content_id = m.content_id
WHERE
  cat.category_name = '体育'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `bfffcd21547a4f53bc78a8446e367930fd59d59a46030f2c86b167e43712bc8d`

PostgreSQL SQL SHA256: `ec14b2436cb45f5c7a019af13b5649698b880c3018f376873f4929ddc442b1f2`

## CONTENT_OPS-111

社会热点类热点话题热度前10；请返回热点话题名称、热度分、热点话题状态；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: topic_name, heat_score, topic_status. Filters: WHERE topic_type = '社会热点'.

Output: `topic_name, heat_score, topic_status`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT topic_name,heat_score,topic_status FROM trending_topics WHERE topic_type='社会热点' ORDER BY heat_score DESC,topic_name LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  topic_name,
  heat_score,
  topic_status
FROM trending_topics
WHERE
  topic_type = '社会热点'
ORDER BY
  heat_score DESC NULLS LAST,
  topic_name
LIMIT 10
```

Original SQL SHA256: `a11223147ec2323cbf0417c31a2c26bda7bedabb275844a365e303e301191aa5`

PostgreSQL SQL SHA256: `7ea0ab9090f8b17e002655fd4fc0696ec7044f1536d45ca27c0f84fa8fe6de42`

## CONTENT_OPS-112

平台活动类热点话题热度前10；请返回热点话题名称、热度分、热点话题状态；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: topic_name, heat_score, topic_status. Filters: WHERE topic_type = '平台活动'.

Output: `topic_name, heat_score, topic_status`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT topic_name,heat_score,topic_status FROM trending_topics WHERE topic_type='平台活动' ORDER BY heat_score DESC,topic_name LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  topic_name,
  heat_score,
  topic_status
FROM trending_topics
WHERE
  topic_type = '平台活动'
ORDER BY
  heat_score DESC NULLS LAST,
  topic_name
LIMIT 10
```

Original SQL SHA256: `f0116ce265f92bcfce7e4f22c4cfa1308ffbc2a5a80a98d8774f8d8aed1fdf36`

PostgreSQL SQL SHA256: `b50a2b159c956b0c237d2857d36d92b9bfe286645523aff9de7eb61f0a9acb68`

## CONTENT_OPS-113

娱乐类热点话题热度前10；请返回热点话题名称、热度分、热点话题状态；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: topic_name, heat_score, topic_status. Filters: WHERE topic_type = '娱乐'.

Output: `topic_name, heat_score, topic_status`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT topic_name,heat_score,topic_status FROM trending_topics WHERE topic_type='娱乐' ORDER BY heat_score DESC,topic_name LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  topic_name,
  heat_score,
  topic_status
FROM trending_topics
WHERE
  topic_type = '娱乐'
ORDER BY
  heat_score DESC NULLS LAST,
  topic_name
LIMIT 10
```

Original SQL SHA256: `4637b2c33ba1c1f2595d4c29484a2f87dc106dc190e612f5cff9ce21665c67f2`

PostgreSQL SQL SHA256: `8e0d5ecc9221ed420b6ac60c5578762ac0a4403ae54b2aed2a6bedda5243257d`

## CONTENT_OPS-114

赛事类热点话题热度前10；请返回热点话题名称、热度分、热点话题状态；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: topic_name, heat_score, topic_status. Filters: WHERE topic_type = '赛事'.

Output: `topic_name, heat_score, topic_status`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT topic_name,heat_score,topic_status FROM trending_topics WHERE topic_type='赛事' ORDER BY heat_score DESC,topic_name LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  topic_name,
  heat_score,
  topic_status
FROM trending_topics
WHERE
  topic_type = '赛事'
ORDER BY
  heat_score DESC NULLS LAST,
  topic_name
LIMIT 10
```

Original SQL SHA256: `7fab1d8e32dbc746765d977157d5567ef54239da4f178358e60657dabb9063f1`

PostgreSQL SQL SHA256: `b06e0a07c8234ab3bce4a30d36c12762f3449c560d0f15e5cc3009315265df70`

## CONTENT_OPS-115

节日类热点话题热度前10；请返回热点话题名称、热度分、热点话题状态；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: topic_name, heat_score, topic_status. Filters: WHERE topic_type = '节日'.

Output: `topic_name, heat_score, topic_status`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT topic_name,heat_score,topic_status FROM trending_topics WHERE topic_type='节日' ORDER BY heat_score DESC,topic_name LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  topic_name,
  heat_score,
  topic_status
FROM trending_topics
WHERE
  topic_type = '节日'
ORDER BY
  heat_score DESC NULLS LAST,
  topic_name
LIMIT 10
```

Original SQL SHA256: `a7cf113839a912761aa6ea44eb481c334bb8e54127c1b456b37b1254eaedc8a1`

PostgreSQL SQL SHA256: `f2e4f5fdd1e97d95602e4028fe4c18ed17acfc2573feccd78d3c1a8d4fc7d2d5`

## CONTENT_OPS-116

2026-01参与内容最多的前10个热点话题；请返回热点话题名称、内容数量；聚合口径：数量指标按对应业务记录计数；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: topic_name, contents. Filters: WHERE TO_CHAR(r.joined_at, 'YYYY-MM') = '2026-01'.

Output: `topic_name, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT t.topic_name,COUNT(r.content_id) contents FROM topic_content_relations r JOIN trending_topics t ON r.topic_id=t.topic_id WHERE strftime(r.joined_at,'%Y-%m')='2026-01' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  t.topic_name,
  COUNT(r.content_id) AS contents
FROM topic_content_relations AS r
JOIN trending_topics AS t
  ON r.topic_id = t.topic_id
WHERE
  TO_CHAR(r.joined_at, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `57163ac5a34e3876b679ce5fd9627bc9ffed0ce7413a4c758da2a33988be9e55`

PostgreSQL SQL SHA256: `a77fae2a40f9ece245ae6498788fc60d0ca6a7e51f5f4b375795b28231e7ff76`

## CONTENT_OPS-117

2026-02参与内容最多的前10个热点话题；请返回热点话题名称、内容数量；聚合口径：数量指标按对应业务记录计数；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: topic_name, contents. Filters: WHERE TO_CHAR(r.joined_at, 'YYYY-MM') = '2026-02'.

Output: `topic_name, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT t.topic_name,COUNT(r.content_id) contents FROM topic_content_relations r JOIN trending_topics t ON r.topic_id=t.topic_id WHERE strftime(r.joined_at,'%Y-%m')='2026-02' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  t.topic_name,
  COUNT(r.content_id) AS contents
FROM topic_content_relations AS r
JOIN trending_topics AS t
  ON r.topic_id = t.topic_id
WHERE
  TO_CHAR(r.joined_at, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `20b50982e66399c140b0dee22bceda24ee139c2a6f8453b15dbe8522b6128fa3`

PostgreSQL SQL SHA256: `cf42d390d7c1cac2a76d61f80b35f17b8da0f1566a157c79b1d57830b97d8244`

## CONTENT_OPS-118

2026-03参与内容最多的前10个热点话题；请返回热点话题名称、内容数量；聚合口径：数量指标按对应业务记录计数；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: topic_name, contents. Filters: WHERE TO_CHAR(r.joined_at, 'YYYY-MM') = '2026-03'.

Output: `topic_name, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT t.topic_name,COUNT(r.content_id) contents FROM topic_content_relations r JOIN trending_topics t ON r.topic_id=t.topic_id WHERE strftime(r.joined_at,'%Y-%m')='2026-03' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  t.topic_name,
  COUNT(r.content_id) AS contents
FROM topic_content_relations AS r
JOIN trending_topics AS t
  ON r.topic_id = t.topic_id
WHERE
  TO_CHAR(r.joined_at, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `c90465efd5928d2c93edf47682f87ade96d4d12ed439426827550a1e59ffb8eb`

PostgreSQL SQL SHA256: `a26d4c1f0f7dcd0e4921dd4dfe4dd896d9b548fc2c5a565fce02ec4dade0a530`

## CONTENT_OPS-119

2026-04参与内容最多的前10个热点话题；请返回热点话题名称、内容数量；聚合口径：数量指标按对应业务记录计数；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: topic_name, contents. Filters: WHERE TO_CHAR(r.joined_at, 'YYYY-MM') = '2026-04'.

Output: `topic_name, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT t.topic_name,COUNT(r.content_id) contents FROM topic_content_relations r JOIN trending_topics t ON r.topic_id=t.topic_id WHERE strftime(r.joined_at,'%Y-%m')='2026-04' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  t.topic_name,
  COUNT(r.content_id) AS contents
FROM topic_content_relations AS r
JOIN trending_topics AS t
  ON r.topic_id = t.topic_id
WHERE
  TO_CHAR(r.joined_at, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `d6b3977178c64f000c04761bc0db174cd1956c9bb3d73744507b96ba6dc4084b`

PostgreSQL SQL SHA256: `8c50f63f0ff24d1686838bfa1a4e423bef81d962f11dd1fcd0a3eb9fe1f7db2b`

## CONTENT_OPS-120

2026-05参与内容最多的前10个热点话题；请返回热点话题名称、内容数量；聚合口径：数量指标按对应业务记录计数；按核心指标从高到低展示；最多返回10行。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: topic_name, contents. Filters: WHERE TO_CHAR(r.joined_at, 'YYYY-MM') = '2026-05'.

Output: `topic_name, contents`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT t.topic_name,COUNT(r.content_id) contents FROM topic_content_relations r JOIN trending_topics t ON r.topic_id=t.topic_id WHERE strftime(r.joined_at,'%Y-%m')='2026-05' GROUP BY 1 ORDER BY 2 DESC,1 LIMIT 10
```

Explicit PostgreSQL SQL:

```sql
SELECT
  t.topic_name,
  COUNT(r.content_id) AS contents
FROM topic_content_relations AS r
JOIN trending_topics AS t
  ON r.topic_id = t.topic_id
WHERE
  TO_CHAR(r.joined_at, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
LIMIT 10
```

Original SQL SHA256: `1e1851f4fc8e98b96f4f9b667719e56df5f8324bcf42e5096de8073ccf402d04`

PostgreSQL SQL SHA256: `0d584ce3a17261aac90605a7afc883f03bceee545c63b5db5f47bdc72512f0a0`

## CONTENT_OPS-122

流量加热系数至少1.5的热点内容数量和平均排名；请返回最低流量加热系数、内容数量、平均排名；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: min_traffic_boost, contents, avg_ranking. Filters: WHERE traffic_boost >= 1.5.

Output: `min_traffic_boost, contents, avg_ranking`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT 1.5 min_traffic_boost,COUNT(content_id) contents,ROUND(AVG(ranking),2) avg_ranking FROM topic_content_relations WHERE traffic_boost>=1.5
```

Explicit PostgreSQL SQL:

```sql
SELECT
  1.5 AS min_traffic_boost,
  COUNT(content_id) AS contents,
  ROUND(CAST(AVG(ranking) AS DECIMAL), 2) AS avg_ranking
FROM topic_content_relations
WHERE
  traffic_boost >= 1.5
```

Original SQL SHA256: `69cc04de15ed96b5e7c63108382747d6ea479ca1ad5c85afdc27d3d82dba2832`

PostgreSQL SQL SHA256: `ef7aaacaffb0dba51ab2b24a9367113cfe60cbe27b3919ed8453106f31a4a35f`

## CONTENT_OPS-123

流量加热系数至少2.0的热点内容数量和平均排名；请返回最低流量加热系数、内容数量、平均排名；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: min_traffic_boost, contents, avg_ranking. Filters: WHERE traffic_boost >= 2.0.

Output: `min_traffic_boost, contents, avg_ranking`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT 2.0 min_traffic_boost,COUNT(content_id) contents,ROUND(AVG(ranking),2) avg_ranking FROM topic_content_relations WHERE traffic_boost>=2.0
```

Explicit PostgreSQL SQL:

```sql
SELECT
  2.0 AS min_traffic_boost,
  COUNT(content_id) AS contents,
  ROUND(CAST(AVG(ranking) AS DECIMAL), 2) AS avg_ranking
FROM topic_content_relations
WHERE
  traffic_boost >= 2.0
```

Original SQL SHA256: `97b15227764db12496a9c43e0264326fa46ee523513e67eba6166f42a7fec593`

PostgreSQL SQL SHA256: `daf213c8666f1401a0f713f2ad9be48426adc61273ece89e61e744e6bb595e1b`

## CONTENT_OPS-124

流量加热系数至少2.5的热点内容数量和平均排名；请返回最低流量加热系数、内容数量、平均排名；聚合口径：数量指标按对应业务记录计数，平均指标取算术平均；按核心指标从高到低展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: min_traffic_boost, contents, avg_ranking. Filters: WHERE traffic_boost >= 2.5.

Output: `min_traffic_boost, contents, avg_ranking`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT 2.5 min_traffic_boost,COUNT(content_id) contents,ROUND(AVG(ranking),2) avg_ranking FROM topic_content_relations WHERE traffic_boost>=2.5
```

Explicit PostgreSQL SQL:

```sql
SELECT
  2.5 AS min_traffic_boost,
  COUNT(content_id) AS contents,
  ROUND(CAST(AVG(ranking) AS DECIMAL), 2) AS avg_ranking
FROM topic_content_relations
WHERE
  traffic_boost >= 2.5
```

Original SQL SHA256: `4e30bdfc0eda9c4107b207275ce5dbbfc5cd8e93fd4d8a4cb3af56b09f2059f6`

PostgreSQL SQL SHA256: `767491edd337bdf5a39766486d19ed19dddeca2f4a2bda2e93a22e74da19f686`

## CONTENT_OPS-127

rejected审核状态按风险类型分布；请返回风险类型、审核数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: risk_type, audits. Filters: WHERE audit_status = 'rejected'.

Output: `risk_type, audits`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT risk_type,COUNT(audit_id) audits FROM content_audits WHERE audit_status='rejected' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  risk_type,
  COUNT(audit_id) AS audits
FROM content_audits
WHERE
  audit_status = 'rejected'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `a28dbf057049835d5922a15c22e7ad506565d528fb1451a008f77c0ea5e7aa67`

PostgreSQL SQL SHA256: `708c414a2c3208134777ab6985259a0e02542a877e1ba3fd286cfdaad797384b`

## CONTENT_OPS-128

limited审核状态按风险类型分布；请返回风险类型、审核数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: risk_type, audits. Filters: WHERE audit_status = 'limited'.

Output: `risk_type, audits`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT risk_type,COUNT(audit_id) audits FROM content_audits WHERE audit_status='limited' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  risk_type,
  COUNT(audit_id) AS audits
FROM content_audits
WHERE
  audit_status = 'limited'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `2ede2c058da81041179edad055e9f90a6560bfc724199f03d5b41e7aee6ce695`

PostgreSQL SQL SHA256: `4af4bd92a850bbfff26942509024b4efcca65f6205ef6968815d11809706b2b5`

## CONTENT_OPS-129

请汇总approved审核状态按风险类型分布；请返回风险类型、审核数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: risk_type, audits. Filters: WHERE audit_status = 'approved'.

Output: `risk_type, audits`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT risk_type,COUNT(audit_id) audits FROM content_audits WHERE audit_status='approved' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

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

Original SQL SHA256: `583ea545ba58dab6899eb65841e4dca8a752efdf3071817a0da34eac9c9e3dbb`

PostgreSQL SQL SHA256: `d04cdeaabcc741439ba4ff6f4439c21ccab901237e6e139d95acc6dbcbe2a81d`

## CONTENT_OPS-130

请汇总rejected审核状态按风险类型分布；请返回风险类型、审核数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: risk_type, audits. Filters: WHERE audit_status = 'rejected'.

Output: `risk_type, audits`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT risk_type,COUNT(audit_id) audits FROM content_audits WHERE audit_status='rejected' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  risk_type,
  COUNT(audit_id) AS audits
FROM content_audits
WHERE
  audit_status = 'rejected'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `a28dbf057049835d5922a15c22e7ad506565d528fb1451a008f77c0ea5e7aa67`

PostgreSQL SQL SHA256: `708c414a2c3208134777ab6985259a0e02542a877e1ba3fd286cfdaad797384b`

## CONTENT_OPS-131

搞笑类内容审核驳回率；请返回内容分类、审核数量、驳回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, audits, rejection_rate. Filters: WHERE cat.category_name = '搞笑'.

Output: `category_name, audits, rejection_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(*) audits, ROUND(SUM(CASE WHEN a.audit_status='rejected' THEN 1 ELSE 0 END)*1.0/COUNT(*),4) rejection_rate FROM content_audits a JOIN contents c ON a.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='搞笑' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(*) AS audits,
  ROUND(
    CAST(CAST(SUM(CASE WHEN a.audit_status = 'rejected' THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS rejection_rate
FROM content_audits AS a
JOIN contents AS c
  ON a.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '搞笑'
GROUP BY
  1
```

Original SQL SHA256: `9b58e4cedf3d3bec4537c0bb98e2b4ec1dae15e03e954f423cfbfaf81af43376`

PostgreSQL SQL SHA256: `a5a52088f4934b0ad7d4306a4407dcbc3c194c216741276ca8aa5781b74351f8`

## CONTENT_OPS-132

生活类内容审核驳回率；请返回内容分类、审核数量、驳回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, audits, rejection_rate. Filters: WHERE cat.category_name = '生活'.

Output: `category_name, audits, rejection_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(*) audits, ROUND(SUM(CASE WHEN a.audit_status='rejected' THEN 1 ELSE 0 END)*1.0/COUNT(*),4) rejection_rate FROM content_audits a JOIN contents c ON a.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='生活' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(*) AS audits,
  ROUND(
    CAST(CAST(SUM(CASE WHEN a.audit_status = 'rejected' THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS rejection_rate
FROM content_audits AS a
JOIN contents AS c
  ON a.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '生活'
GROUP BY
  1
```

Original SQL SHA256: `416c4ae4829c31cd3b461c094b41eb5f826b4cea01e8089b332a3117df356288`

PostgreSQL SQL SHA256: `5350f3d88861005b66dbe80229554da75683c9a6a392d3457dce0e13c8a2c9dd`

## CONTENT_OPS-133

美食类内容审核驳回率；请返回内容分类、审核数量、驳回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, audits, rejection_rate. Filters: WHERE cat.category_name = '美食'.

Output: `category_name, audits, rejection_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(*) audits, ROUND(SUM(CASE WHEN a.audit_status='rejected' THEN 1 ELSE 0 END)*1.0/COUNT(*),4) rejection_rate FROM content_audits a JOIN contents c ON a.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='美食' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(*) AS audits,
  ROUND(
    CAST(CAST(SUM(CASE WHEN a.audit_status = 'rejected' THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS rejection_rate
FROM content_audits AS a
JOIN contents AS c
  ON a.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '美食'
GROUP BY
  1
```

Original SQL SHA256: `4ccab5142ac97ff4e0332f7b43c89a663ebcf3aae7f0e4b10dc2c904b7a55f88`

PostgreSQL SQL SHA256: `ee6fd6efead18964df321eb10549e63c8b3d07024c84263f7cde701f65fe54b3`

## CONTENT_OPS-134

知识类内容审核驳回率；请返回内容分类、审核数量、驳回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, audits, rejection_rate. Filters: WHERE cat.category_name = '知识'.

Output: `category_name, audits, rejection_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(*) audits, ROUND(SUM(CASE WHEN a.audit_status='rejected' THEN 1 ELSE 0 END)*1.0/COUNT(*),4) rejection_rate FROM content_audits a JOIN contents c ON a.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='知识' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(*) AS audits,
  ROUND(
    CAST(CAST(SUM(CASE WHEN a.audit_status = 'rejected' THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS rejection_rate
FROM content_audits AS a
JOIN contents AS c
  ON a.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '知识'
GROUP BY
  1
```

Original SQL SHA256: `565d8d1174a04dcde6aa03e363ea3529fcf4c022c4204b73de9ec134f6a75893`

PostgreSQL SQL SHA256: `2535d4261a522835f2d7737d35731685fcef55fbb068deb95d891e5ad73be21c`

## CONTENT_OPS-135

体育类内容审核驳回率；请返回内容分类、审核数量、驳回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, audits, rejection_rate. Filters: WHERE cat.category_name = '体育'.

Output: `category_name, audits, rejection_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 1, "floating_division_count": 1, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(*) audits, ROUND(SUM(CASE WHEN a.audit_status='rejected' THEN 1 ELSE 0 END)*1.0/COUNT(*),4) rejection_rate FROM content_audits a JOIN contents c ON a.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE cat.category_name='体育' GROUP BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  cat.category_name,
  COUNT(*) AS audits,
  ROUND(
    CAST(CAST(SUM(CASE WHEN a.audit_status = 'rejected' THEN 1 ELSE 0 END) * 1.0 AS DOUBLE PRECISION) / COUNT(*) AS DECIMAL),
    4
  ) AS rejection_rate
FROM content_audits AS a
JOIN contents AS c
  ON a.content_id = c.content_id
JOIN content_categories AS cat
  ON c.category_id = cat.category_id
WHERE
  cat.category_name = '体育'
GROUP BY
  1
```

Original SQL SHA256: `b16991443743bd47296c6f118056924f54c831cc2234a4a3b1bb58129a3c0e01`

PostgreSQL SQL SHA256: `45404003fbefffcd24d78064568fa6d44d7ad6bd940ad2a34d9c87575913b653`

## CONTENT_OPS-139

虚假信息举报按内容分类分布；请返回内容分类、举报数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, reports. Filters: WHERE r.report_reason = '虚假信息'.

Output: `category_name, reports`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(r.report_id) reports FROM content_reports r JOIN contents c ON r.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE r.report_reason='虚假信息' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

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
  r.report_reason = '虚假信息'
GROUP BY
  1
ORDER BY
  2 DESC NULLS LAST,
  1
```

Original SQL SHA256: `00323b4ab7ee4e9c665d265cf1339150bf65ac02baff2486dbbc16eabe68547c`

PostgreSQL SQL SHA256: `5447a61eab1e18c9788c88dbda8664b096224c64061a3ce10ecb09aef11f34c7`

## CONTENT_OPS-140

请汇总不感兴趣举报按内容分类分布；请返回内容分类、举报数量；聚合口径：数量指标按对应业务记录计数。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: category_name, reports. Filters: WHERE r.report_reason = '不感兴趣'.

Output: `category_name, reports`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 2}`

Original DuckDB SQL:

```sql
SELECT cat.category_name,COUNT(r.report_id) reports FROM content_reports r JOIN contents c ON r.content_id=c.content_id JOIN content_categories cat ON c.category_id=cat.category_id WHERE r.report_reason='不感兴趣' GROUP BY 1 ORDER BY 2 DESC,1
```

Explicit PostgreSQL SQL:

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

Original SQL SHA256: `55a72689411e479d4c3cae4e5f15b6cb9835cef3c25424878a5055e133e219e9`

PostgreSQL SQL SHA256: `6c61ebc12e3922d6fb44ec2f999fe9b40cdfa0f0e73ace2177890ab5aeeead33`

## CONTENT_OPS-141

2026-01每天的举报数量；请返回举报日期、举报数量；聚合口径：数量指标按对应业务记录计数；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: report_date, reports. Filters: WHERE TO_CHAR(reported_at, 'YYYY-MM') = '2026-01'.

Output: `report_date, reports`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT CAST(reported_at AS DATE) report_date,COUNT(report_id) reports FROM content_reports WHERE strftime(reported_at,'%Y-%m')='2026-01' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  CAST(reported_at AS DATE) AS report_date,
  COUNT(report_id) AS reports
FROM content_reports
WHERE
  TO_CHAR(reported_at, 'YYYY-MM') = '2026-01'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `a1ae18a4232a9fd8f93dcae9f2f088a77795e603c851d860d32184d56aa54e4f`

PostgreSQL SQL SHA256: `046d9ec602bd053ceb0f53a59f3f4d101c13963cbae5f699d1bce17fcba4dd5a`

## CONTENT_OPS-142

2026-02每天的举报数量；请返回举报日期、举报数量；聚合口径：数量指标按对应业务记录计数；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: report_date, reports. Filters: WHERE TO_CHAR(reported_at, 'YYYY-MM') = '2026-02'.

Output: `report_date, reports`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT CAST(reported_at AS DATE) report_date,COUNT(report_id) reports FROM content_reports WHERE strftime(reported_at,'%Y-%m')='2026-02' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  CAST(reported_at AS DATE) AS report_date,
  COUNT(report_id) AS reports
FROM content_reports
WHERE
  TO_CHAR(reported_at, 'YYYY-MM') = '2026-02'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `d4917c522146e553b89cf39a076cad9ed5fab9b3cd6d5763415d46985124d641`

PostgreSQL SQL SHA256: `15073be2fd4c1cf13819142d708e3bcf91662ef70549541d1734235142f338db`

## CONTENT_OPS-143

2026-03每天的举报数量；请返回举报日期、举报数量；聚合口径：数量指标按对应业务记录计数；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: report_date, reports. Filters: WHERE TO_CHAR(reported_at, 'YYYY-MM') = '2026-03'.

Output: `report_date, reports`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT CAST(reported_at AS DATE) report_date,COUNT(report_id) reports FROM content_reports WHERE strftime(reported_at,'%Y-%m')='2026-03' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  CAST(reported_at AS DATE) AS report_date,
  COUNT(report_id) AS reports
FROM content_reports
WHERE
  TO_CHAR(reported_at, 'YYYY-MM') = '2026-03'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `063811f0f48ee440bbe1dd5e102d05afc884e30576188eca5335461709353ae6`

PostgreSQL SQL SHA256: `88fb8ffe84533362b17ba521d24823f0663bc2b84b42176320d5f690552a432b`

## CONTENT_OPS-144

2026-04每天的举报数量；请返回举报日期、举报数量；聚合口径：数量指标按对应业务记录计数；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: report_date, reports. Filters: WHERE TO_CHAR(reported_at, 'YYYY-MM') = '2026-04'.

Output: `report_date, reports`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT CAST(reported_at AS DATE) report_date,COUNT(report_id) reports FROM content_reports WHERE strftime(reported_at,'%Y-%m')='2026-04' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  CAST(reported_at AS DATE) AS report_date,
  COUNT(report_id) AS reports
FROM content_reports
WHERE
  TO_CHAR(reported_at, 'YYYY-MM') = '2026-04'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `4d45e8b9c6e336ab02719b2d4fb57f4d0210e88701bf44ea29450f38050f324d`

PostgreSQL SQL SHA256: `6e682a2c84248d794e78848696d996f81476fbd31633991300e4e01f87445636`

## CONTENT_OPS-145

2026-05每天的举报数量；请返回举报日期、举报数量；聚合口径：数量指标按对应业务记录计数；按时间升序展示。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: report_date, reports. Filters: WHERE TO_CHAR(reported_at, 'YYYY-MM') = '2026-05'.

Output: `report_date, reports`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 0, "floating_division_count": 0, "month_format_count": 1, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 1}`

Original DuckDB SQL:

```sql
SELECT CAST(reported_at AS DATE) report_date,COUNT(report_id) reports FROM content_reports WHERE strftime(reported_at,'%Y-%m')='2026-05' GROUP BY 1 ORDER BY 1
```

Explicit PostgreSQL SQL:

```sql
SELECT
  CAST(reported_at AS DATE) AS report_date,
  COUNT(report_id) AS reports
FROM content_reports
WHERE
  TO_CHAR(reported_at, 'YYYY-MM') = '2026-05'
GROUP BY
  1
ORDER BY
  1
```

Original SQL SHA256: `206ca38b0b350be41975e2505bde164a3295544d84c4d48974404edbbc4b93e5`

PostgreSQL SQL SHA256: `3f8d75e7ae34da3eac2f4c8861a36a52a9304f0b956fb56f451a7dd854476f98`

## CONTENT_OPS-146

machine审核方式的通过率和驳回率；请返回审核方式、审核数量、通过率、驳回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: review_mode, audits, approval_rate, rejection_rate. Filters: WHERE review_mode = 'machine'.

Output: `review_mode, audits, approval_rate, rejection_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 2, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT review_mode,COUNT(*) audits, ROUND(SUM(CASE WHEN audit_status='approved' THEN 1 ELSE 0 END)*1.0/COUNT(*),4) approval_rate, ROUND(SUM(CASE WHEN audit_status='rejected' THEN 1 ELSE 0 END)*1.0/COUNT(*),4) rejection_rate FROM content_audits WHERE review_mode='machine' GROUP BY 1
```

Explicit PostgreSQL SQL:

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
  review_mode = 'machine'
GROUP BY
  1
```

Original SQL SHA256: `82fe22ee0b45be59ff705e9773215e1a04dda23e0976ab6b0e66635293ea1237`

PostgreSQL SQL SHA256: `c2d1d217173bbd7d2e363033344c85d715f726530a9685eb8eb74fa39ba5d5c6`

## CONTENT_OPS-147

human审核方式的通过率和驳回率；请返回审核方式、审核数量、通过率、驳回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: review_mode, audits, approval_rate, rejection_rate. Filters: WHERE review_mode = 'human'.

Output: `review_mode, audits, approval_rate, rejection_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 2, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT review_mode,COUNT(*) audits, ROUND(SUM(CASE WHEN audit_status='approved' THEN 1 ELSE 0 END)*1.0/COUNT(*),4) approval_rate, ROUND(SUM(CASE WHEN audit_status='rejected' THEN 1 ELSE 0 END)*1.0/COUNT(*),4) rejection_rate FROM content_audits WHERE review_mode='human' GROUP BY 1
```

Explicit PostgreSQL SQL:

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

Original SQL SHA256: `7621f5332b8ed84d6a01949860667baa43bca777e0da91a256ac05763190c8ed`

PostgreSQL SQL SHA256: `817f14a2bb250ecd536a1fcefc34cded20f757c917c81c136376f5acdf4e6050`

## CONTENT_OPS-148

mixed审核方式的通过率和驳回率；请返回审核方式、审核数量、通过率、驳回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: review_mode, audits, approval_rate, rejection_rate. Filters: WHERE review_mode = 'mixed'.

Output: `review_mode, audits, approval_rate, rejection_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 2, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT review_mode,COUNT(*) audits, ROUND(SUM(CASE WHEN audit_status='approved' THEN 1 ELSE 0 END)*1.0/COUNT(*),4) approval_rate, ROUND(SUM(CASE WHEN audit_status='rejected' THEN 1 ELSE 0 END)*1.0/COUNT(*),4) rejection_rate FROM content_audits WHERE review_mode='mixed' GROUP BY 1
```

Explicit PostgreSQL SQL:

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
  review_mode = 'mixed'
GROUP BY
  1
```

Original SQL SHA256: `dad251cca9af049057b8edffc4447eed48433cb40cf7d92f5249de11928aba7d`

PostgreSQL SQL SHA256: `eb693e90f78664a4f6833ce89487c736ec575843b659224f05ef4c472ec507e7`

## CONTENT_OPS-149

请汇总machine审核方式的通过率和驳回率；请返回审核方式、审核数量、通过率、驳回率；聚合口径：数量指标按对应业务记录计数，可加总指标按当前查询粒度求和，比率按汇总后的分子除以分母。

Preserve original filters, join multiplicity, aggregate grain, numerator/denominator, window ordering, limits, aliases and frozen result/tie policy. Only explicit dialect/type adjustments are permitted. Outputs: review_mode, audits, approval_rate, rejection_rate. Filters: WHERE review_mode = 'machine'.

Output: `review_mode, audits, approval_rate, rejection_rate`

Changes: `{"integer_truth_tests": [], "round_numeric_cast_count": 2, "floating_division_count": 2, "month_format_count": 0, "substring_count": 0, "nullif_count": 0, "nulls_last_order_count": 0}`

Original DuckDB SQL:

```sql
SELECT review_mode,COUNT(*) audits, ROUND(SUM(CASE WHEN audit_status='approved' THEN 1 ELSE 0 END)*1.0/COUNT(*),4) approval_rate, ROUND(SUM(CASE WHEN audit_status='rejected' THEN 1 ELSE 0 END)*1.0/COUNT(*),4) rejection_rate FROM content_audits WHERE review_mode='machine' GROUP BY 1
```

Explicit PostgreSQL SQL:

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
  review_mode = 'machine'
GROUP BY
  1
```

Original SQL SHA256: `82fe22ee0b45be59ff705e9773215e1a04dda23e0976ab6b0e66635293ea1237`

PostgreSQL SQL SHA256: `c2d1d217173bbd7d2e363033344c85d715f726530a9685eb8eb74fa39ba5d5c6`

