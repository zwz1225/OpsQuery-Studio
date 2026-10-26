-- Generated preparation artifact; not executed by preflight.

-- Connect as askdata_import to askdata_m1_test. Schema must already exist.

BEGIN;

CREATE TABLE "askdata_ops"."acquisition_channels" (
  "channel_id" text,
  "channel_name" text,
  "channel_type" text,
  "owner_team" text,
  "enabled" bigint,
  PRIMARY KEY ("channel_id")
);

CREATE TABLE "askdata_ops"."ad_accounts" (
  "ad_account_id" text,
  "account_name" text,
  "channel_id" text,
  "account_status" text,
  "currency" text,
  PRIMARY KEY ("ad_account_id")
);

CREATE TABLE "askdata_ops"."ad_campaigns" (
  "ad_campaign_id" text,
  "ad_campaign_name" text,
  "ad_account_id" text,
  "channel_id" text,
  "objective" text,
  "budget" bigint,
  "start_date" date,
  "end_date" date,
  "status" text,
  PRIMARY KEY ("ad_campaign_id")
);

CREATE TABLE "askdata_ops"."ad_creatives" (
  "creative_id" text,
  "ad_campaign_id" text,
  "creative_name" text,
  "creative_type" text,
  "creative_theme" text,
  "creative_status" text,
  PRIMARY KEY ("creative_id")
);

CREATE TABLE "askdata_ops"."ad_daily_stats" (
  "ad_stat_id" text,
  "ad_campaign_id" text,
  "stat_date" date,
  "impressions" bigint,
  "clicks" bigint,
  "conversions" bigint,
  "spend" double precision,
  "click_through_rate" double precision,
  "cost_per_conversion" double precision,
  PRIMARY KEY ("ad_stat_id")
);

CREATE TABLE "askdata_ops"."budget_adjustments" (
  "adjustment_id" text,
  "ad_campaign_id" text,
  "adjusted_at" timestamp without time zone,
  "previous_budget" bigint,
  "new_budget" bigint,
  "adjustment_reason" text,
  "operator_name" text,
  PRIMARY KEY ("adjustment_id")
);

CREATE TABLE "askdata_ops"."channel_attributions" (
  "attribution_id" text,
  "user_id" text,
  "channel_id" text,
  "ad_campaign_id" text,
  "attribution_type" text,
  "attributed_at" timestamp without time zone,
  "confidence_score" double precision,
  PRIMARY KEY ("attribution_id")
);

CREATE TABLE "askdata_ops"."channel_conversion_events" (
  "conversion_event_id" text,
  "user_id" text,
  "channel_id" text,
  "ad_campaign_id" text,
  "conversion_type" text,
  "converted_at" timestamp without time zone,
  "conversion_value" bigint,
  PRIMARY KEY ("conversion_event_id")
);

CREATE TABLE "askdata_ops"."channel_targets" (
  "channel_target_id" text,
  "target_month" text,
  "channel_id" text,
  "spend_target" bigint,
  "registration_target" bigint,
  "activation_target" bigint,
  "target_cpa" double precision,
  PRIMARY KEY ("channel_target_id")
);

CREATE TABLE "askdata_ops"."content_audits" (
  "audit_id" text,
  "content_id" text,
  "audited_at" timestamp without time zone,
  "audit_status" text,
  "risk_type" text,
  "review_mode" text,
  PRIMARY KEY ("audit_id")
);

CREATE TABLE "askdata_ops"."content_categories" (
  "category_id" text,
  "category_name" text,
  "category_level" bigint,
  "enabled" bigint,
  PRIMARY KEY ("category_id")
);

CREATE TABLE "askdata_ops"."content_daily_metrics" (
  "content_metric_id" text,
  "metric_date" date,
  "content_id" text,
  "impressions" bigint,
  "play_count" bigint,
  "watch_seconds" bigint,
  "interaction_count" bigint,
  "play_rate" double precision,
  "completion_rate" double precision,
  PRIMARY KEY ("content_metric_id")
);

CREATE TABLE "askdata_ops"."content_reports" (
  "report_id" text,
  "user_id" text,
  "content_id" text,
  "report_reason" text,
  "reported_at" timestamp without time zone,
  "process_status" text,
  PRIMARY KEY ("report_id")
);

CREATE TABLE "askdata_ops"."content_tag_relations" (
  "content_tag_relation_id" text,
  "content_id" text,
  "content_tag_id" text,
  "confidence_score" double precision,
  "source" text,
  PRIMARY KEY ("content_tag_relation_id")
);

CREATE TABLE "askdata_ops"."content_tags" (
  "content_tag_id" text,
  "tag_name" text,
  "tag_type" text,
  "enabled" bigint,
  PRIMARY KEY ("content_tag_id")
);

CREATE TABLE "askdata_ops"."contents" (
  "content_id" text,
  "creator_id" text,
  "category_id" text,
  "content_title" text,
  "duration_seconds" bigint,
  "published_at" timestamp without time zone,
  "content_status" text,
  "visibility" text,
  "quality_score" double precision,
  PRIMARY KEY ("content_id")
);

CREATE TABLE "askdata_ops"."creator_daily_metrics" (
  "creator_metric_id" text,
  "metric_date" date,
  "creator_id" text,
  "play_count" bigint,
  "interaction_count" bigint,
  "published_count" bigint,
  "interaction_rate" double precision,
  PRIMARY KEY ("creator_metric_id")
);

CREATE TABLE "askdata_ops"."creator_profiles" (
  "creator_id" text,
  "primary_category_id" text,
  "follower_count" bigint,
  "published_content_count" bigint,
  "quality_score" double precision,
  "creator_type" text,
  "snapshot_date" date,
  PRIMARY KEY ("creator_id")
);

CREATE TABLE "askdata_ops"."creators" (
  "creator_id" text,
  "creator_name" text,
  "creator_level" text,
  "joined_at" timestamp without time zone,
  "creator_status" text,
  PRIMARY KEY ("creator_id")
);

CREATE TABLE "askdata_ops"."growth_daily_metrics" (
  "metric_id" text,
  "metric_date" date,
  "channel_id" text,
  "new_users" bigint,
  "activated_users" bigint,
  "day1_retained_users" bigint,
  "day7_retained_users" bigint,
  "daily_active_users" bigint,
  PRIMARY KEY ("metric_id")
);

CREATE TABLE "askdata_ops"."growth_targets" (
  "target_id" text,
  "target_month" text,
  "channel_id" text,
  "new_user_target" bigint,
  "activation_rate_target" double precision,
  "day7_retention_target" double precision,
  "owner_name" text,
  PRIMARY KEY ("target_id")
);

CREATE TABLE "askdata_ops"."recall_campaigns" (
  "recall_campaign_id" text,
  "campaign_name" text,
  "target_segment" text,
  "touch_channel" text,
  "start_date" date,
  "end_date" date,
  "status" text,
  PRIMARY KEY ("recall_campaign_id")
);

CREATE TABLE "askdata_ops"."recall_results" (
  "recall_result_id" text,
  "touch_id" text,
  "user_id" text,
  "recalled" bigint,
  "returned_at" timestamp without time zone,
  "active_days_after_recall" bigint,
  PRIMARY KEY ("recall_result_id")
);

CREATE TABLE "askdata_ops"."recall_touches" (
  "touch_id" text,
  "recall_campaign_id" text,
  "user_id" text,
  "touch_channel" text,
  "sent_at" timestamp without time zone,
  "delivered" bigint,
  "clicked" bigint,
  PRIMARY KEY ("touch_id")
);

CREATE TABLE "askdata_ops"."topic_content_relations" (
  "topic_content_id" text,
  "topic_id" text,
  "content_id" text,
  "joined_at" timestamp without time zone,
  "ranking" bigint,
  "traffic_boost" double precision,
  PRIMARY KEY ("topic_content_id")
);

CREATE TABLE "askdata_ops"."trending_topics" (
  "topic_id" text,
  "topic_name" text,
  "topic_type" text,
  "start_date" date,
  "end_date" date,
  "heat_score" bigint,
  "topic_status" text,
  PRIMARY KEY ("topic_id")
);

CREATE TABLE "askdata_ops"."user_activations" (
  "activation_id" text,
  "registration_id" text,
  "user_id" text,
  "is_activated" bigint,
  "activated_at" timestamp without time zone,
  "activation_seconds" bigint,
  "activation_rule" text,
  PRIMARY KEY ("activation_id")
);

CREATE TABLE "askdata_ops"."user_churn_events" (
  "churn_event_id" text,
  "user_id" text,
  "identified_date" date,
  "churn_level" text,
  "inactive_days" bigint,
  "churn_reason" text,
  PRIMARY KEY ("churn_event_id")
);

CREATE TABLE "askdata_ops"."user_daily_activity" (
  "activity_id" text,
  "user_id" text,
  "activity_date" date,
  "active_minutes" bigint,
  "session_count" bigint,
  "play_count" bigint,
  "interaction_count" bigint,
  "is_valid_active" bigint,
  PRIMARY KEY ("activity_id")
);

CREATE TABLE "askdata_ops"."user_devices" (
  "device_id" text,
  "user_id" text,
  "device_type" text,
  "device_level" text,
  "app_version" text,
  "first_seen_at" timestamp without time zone,
  PRIMARY KEY ("device_id")
);

CREATE TABLE "askdata_ops"."user_lifecycle_snapshots" (
  "snapshot_id" text,
  "user_id" text,
  "snapshot_date" date,
  "lifecycle_stage" text,
  "active_days" bigint,
  "days_since_last_active" bigint,
  "engagement_score" double precision,
  PRIMARY KEY ("snapshot_id")
);

CREATE TABLE "askdata_ops"."user_profiles" (
  "user_id" text,
  "gender" text,
  "age_group" text,
  "region" text,
  "province" text,
  "city" text,
  "city_tier" text,
  "primary_interest" text,
  "updated_at" timestamp without time zone,
  PRIMARY KEY ("user_id")
);

CREATE TABLE "askdata_ops"."user_registrations" (
  "registration_id" text,
  "user_id" text,
  "channel_id" text,
  "registered_at" timestamp without time zone,
  "registration_method" text,
  "platform" text,
  "registration_status" text,
  PRIMARY KEY ("registration_id")
);

CREATE TABLE "askdata_ops"."user_retention" (
  "retention_id" text,
  "user_id" text,
  "channel_id" text,
  "registration_date" date,
  "retention_day" bigint,
  "observation_date" date,
  "is_retained" bigint,
  PRIMARY KEY ("retention_id")
);

CREATE TABLE "askdata_ops"."user_sessions" (
  "session_id" text,
  "user_id" text,
  "device_id" text,
  "channel_id" text,
  "started_at" timestamp without time zone,
  "ended_at" timestamp without time zone,
  "duration_seconds" bigint,
  "landing_page" text,
  PRIMARY KEY ("session_id")
);

CREATE TABLE "askdata_ops"."user_tag_relations" (
  "relation_id" text,
  "user_id" text,
  "tag_id" text,
  "tag_score" double precision,
  "assigned_at" timestamp without time zone,
  "source" text,
  PRIMARY KEY ("relation_id")
);

CREATE TABLE "askdata_ops"."user_tags" (
  "tag_id" text,
  "tag_name" text,
  "tag_type" text,
  "enabled" bigint,
  PRIMARY KEY ("tag_id")
);

CREATE TABLE "askdata_ops"."users" (
  "user_id" text,
  "nickname" text,
  "register_channel_id" text,
  "registered_at" timestamp without time zone,
  "account_status" text,
  "register_platform" text,
  PRIMARY KEY ("user_id")
);

CREATE TABLE "askdata_ops"."video_exposures" (
  "exposure_id" text,
  "user_id" text,
  "content_id" text,
  "position_name" text,
  "exposed_at" timestamp without time zone,
  "clicked" bigint,
  "recommendation_source" text,
  PRIMARY KEY ("exposure_id")
);

CREATE TABLE "askdata_ops"."video_interactions" (
  "interaction_id" text,
  "play_id" text,
  "user_id" text,
  "content_id" text,
  "interaction_type" text,
  "interacted_at" timestamp without time zone,
  "valid_interaction" bigint,
  PRIMARY KEY ("interaction_id")
);

CREATE TABLE "askdata_ops"."video_plays" (
  "play_id" text,
  "exposure_id" text,
  "user_id" text,
  "content_id" text,
  "played_at" timestamp without time zone,
  "watch_seconds" bigint,
  "completion_rate" double precision,
  "completed" bigint,
  "network_type" text,
  PRIMARY KEY ("play_id")
);

COMMIT;
