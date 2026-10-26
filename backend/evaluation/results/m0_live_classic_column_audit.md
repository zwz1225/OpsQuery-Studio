# M0 server classic 49: column contract audit

> Read-only local analysis of the original server reports. The original scores and report files remain unchanged. The 42 reviewed mappings were subsequently added as explicit per-case `column_aliases` on 2026-09-29.

## Run validation

- Live run `e9386862501a48f896e22e568e98cce7`: complete, 49 scored, 49 loose passes, 7 strict passes.
- Gold run `167eccf453974eafaaca285e0409ddc4`: complete, 430 scored.
- Data, schema, application, evaluator, and evaluation code digests match across both runs.
- Live case IDs match the 49 classic cases. Gold case IDs match all 430 source cases.
- All 49 saved SQL statements executed successfully against the matching local data snapshot.
- All 42 strict failures have the same number and order of columns as Gold, and a unique value mapping. Column names are the first failing contract check.

## Seven strict passes

`GROWTH_OPS-026`, `GROWTH_OPS-061`, `GROWTH_OPS-062`, `GROWTH_OPS-063`, `GROWTH_OPS-064`, `GROWTH_OPS-086`, `CONTENT_OPS-029`.

## Observed column mappings in 42 strict failures

These observed mappings were reviewed against each question and SQL projection, then approved as explicit `column_aliases` annotations for these 42 cases. The table records the mappings seen in the original run.

| Case | Expected column -> actual column (changed names only) |
| --- | --- |
| `GROWTH_OPS-001` | `value` -> `new_users` |
| `GROWTH_OPS-002` | `value` -> `activated_users` |
| `GROWTH_OPS-003` | `value` -> `day1_retained_users` |
| `GROWTH_OPS-004` | `value` -> `day7_retained_users` |
| `GROWTH_OPS-005` | `value` -> `daily_active_users` |
| `GROWTH_OPS-006` | `value` -> `new_users` |
| `GROWTH_OPS-066` | `users` -> `user_count` |
| `GROWTH_OPS-101` | `users` -> `user_count` |
| `GROWTH_OPS-131` | `touches` -> `touch_count` |
| `GROWTH_OPS-149` | `actual_rate` -> `actual_activation_rate`, `gap` -> `target_gap` |
| `GROWTH_OPS-150` | `actual_rate` -> `actual_activation_rate`, `gap` -> `target_gap` |
| `CHANNEL_OPS-001` | `spend` -> `ad_spend` |
| `CHANNEL_OPS-002` | `spend` -> `ad_spend` |
| `CHANNEL_OPS-003` | `spend` -> `ad_spend` |
| `CHANNEL_OPS-004` | `spend` -> `ad_spend` |
| `CHANNEL_OPS-005` | `spend` -> `ad_spend` |
| `CHANNEL_OPS-066` | `conversions` -> `conversion_count`, `avg_value` -> `avg_conversion_value` |
| `CHANNEL_OPS-067` | `conversions` -> `conversion_count`, `avg_value` -> `avg_conversion_value` |
| `CHANNEL_OPS-068` | `conversions` -> `conversion_count`, `avg_value` -> `avg_conversion_value` |
| `CHANNEL_OPS-069` | `conversions` -> `conversion_count` |
| `CHANNEL_OPS-070` | `conversions` -> `conversion_count`, `avg_value` -> `avg_conversion_value` |
| `CHANNEL_OPS-076` | `campaigns` -> `ad_campaign_count`, `budget` -> `total_budget` |
| `CHANNEL_OPS-077` | `campaigns` -> `ad_campaign_count`, `budget` -> `total_budget` |
| `CHANNEL_OPS-078` | `campaigns` -> `ad_campaign_count`, `budget` -> `total_budget` |
| `CHANNEL_OPS-079` | `campaigns` -> `ad_campaign_count`, `budget` -> `total_budget` |
| `CHANNEL_OPS-101` | `creative_status` -> `创意状态`, `creatives` -> `创意数量` |
| `CHANNEL_OPS-141` | `conversions` -> `conversion_count` |
| `CONTENT_OPS-001` | `plays` -> `play_count` |
| `CONTENT_OPS-030` | `category_name` -> `内容分类`, `avg_watch_seconds` -> `平均观看时长`, `avg_completion_rate` -> `平均完播率` |
| `CONTENT_OPS-031` | `category_name` -> `内容分类`, `interactions` -> `互动数` |
| `CONTENT_OPS-032` | `category_name` -> `内容分类`, `interactions` -> `互动数` |
| `CONTENT_OPS-033` | `category_name` -> `内容分类`, `interactions` -> `互动数` |
| `CONTENT_OPS-034` | `category_name` -> `内容分类`, `interactions` -> `互动数` |
| `CONTENT_OPS-035` | `category_name` -> `content_category`, `interactions` -> `interaction_count` |
| `CONTENT_OPS-036` | `interactions` -> `interaction_count` |
| `CONTENT_OPS-051` | `category_name` -> `内容分类`, `contents` -> `内容数量`, `avg_duration_seconds` -> `平均视频时长` |
| `CONTENT_OPS-076` | `creators` -> `creator_count` |
| `CONTENT_OPS-121` | `contents` -> `content_count` |
| `CONTENT_OPS-126` | `audits` -> `audit_count` |
| `CONTENT_OPS-136` | `category_name` -> `content_category`, `reports` -> `report_count` |
| `CONTENT_OPS-137` | `category_name` -> `content_category`, `reports` -> `report_count` |
| `CONTENT_OPS-138` | `category_name` -> `内容分类`, `reports` -> `举报数量` |

## Interpretation limits

- Loose comparison permutes result columns by value. Its 49/49 score applies to this data snapshot and does not prove semantic SQL correctness on different data.
- The original strict 7/49 measures canonical column-name adherence before alias annotations. No rescored result is claimed here; a separate offline rescore is the next step.
- The saved benchmark cases omit returned column names. This audit reconstructed them by replaying saved SQL against data with the same digest. Future runs should persist actual and expected columns in each case result.
