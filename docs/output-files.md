# Output Files

Southpole stays local-file-first.

Each run writes to:

- `outputs/runs/<timestamp>_<slug>/`

Legacy compatibility files remain first-class, and canonical/comment/scoring artifacts are additive.

## Legacy Run Files (unchanged)

- `raw_events.jsonl`
- `raw_events.csv`
- `keyword_totals.csv`
- `creators.csv`
- `daily_metrics.csv`
- `report.html`
- `southpole_run_<timestamp>.xlsx`
- `summary.json`

## Canonical Post Artifacts (new additive)

- `raw/source_items.jsonl`
- `normalized/content_items.csv`
- `normalized/creator_profiles.csv`

### `normalized/content_items.csv` schema

- `run_id`
- `platform`
- `content_type`
- `keyword`
- `matched_keywords`
- `source`
- `source_record_id`
- `raw_ref`
- `platform_content_id`
- `canonical_content_id`
- `platform_creator_id`
- `canonical_creator_id`
- `creator_handle`
- `creator_name`
- `creator_profile_url`
- `creator_followers`
- `content_url`
- `published_at`
- `local_date`
- `text`
- `hashtags`
- `music_title`
- `region`
- `language`
- `views`
- `likes`
- `comments_count`
- `shares`
- `saves`
- `engagements`
- `collected_at`

### `normalized/creator_profiles.csv` schema

- `run_id`
- `platform`
- `platform_creator_id`
- `canonical_creator_id`
- `creator_handle`
- `creator_name`
- `creator_profile_url`
- `creator_followers`
- `keywords`
- `primary_keyword`
- `posts`
- `total_views`
- `total_likes`
- `total_comments`
- `total_shares`
- `avg_views`
- `avg_engagements`
- `engagement_rate_by_views`
- `first_seen_at`
- `last_seen_at`
- `top_platform_content_id`
- `top_canonical_content_id`
- `top_content_url`

## Comments Artifacts (additive)

- `comments/comment_targets.csv` (when targets are built)
- `comments/raw_comments.jsonl` (when comments are collected)
- `comments/comment_items.csv` (when comments are collected)
- `comments/comment_insights.csv` (when analyzed)
- `comments/comment_metrics.csv` (when analyzed)
- `comments/comment_topics.csv` (when analyzed)
- `comments/comment_report.html` (when analyzed)

### `comments/comment_targets.csv` schema

- `run_id`
- `selected_from_run_id`
- `platform`
- `content_type`
- `platform_content_id`
- `canonical_content_id`
- `platform_creator_id`
- `canonical_creator_id`
- `creator_handle`
- `content_url`
- `keyword`
- `selection_mode`
- `selection_reason`
- `selected_by`
- `selection_note`
- `requested_comment_limit`
- `selected_at`

### `comments/comment_items.csv` schema

- `run_id`
- `platform`
- `content_type`
- `source`
- `source_record_id`
- `raw_ref`
- `platform_content_id`
- `canonical_content_id`
- `platform_comment_id`
- `canonical_comment_id`
- `content_owner_platform_creator_id`
- `content_owner_canonical_creator_id`
- `comment_author_platform_creator_id`
- `comment_author_canonical_creator_id`
- `comment_author_handle`
- `comment_author_name`
- `parent_platform_comment_id`
- `parent_canonical_comment_id`
- `published_at`
- `text`
- `language`
- `likes`
- `reply_count`
- `collected_at`

### `comments/comment_insights.csv` schema

- `run_id`
- `platform`
- `canonical_content_id`
- `canonical_comment_id`
- `sentiment_label`
- `sentiment_score`
- `intent_label`
- `pain_point_label`
- `pain_point_detail`
- `product_interest_label`
- `topic_tags`
- `purchase_signal`
- `confidence`
- `analysis_model`
- `analyzed_at`

### `comments/comment_metrics.csv` schema

- `run_id`
- `platform`
- `canonical_content_id`
- `comments_analyzed`
- `positive_count`
- `neutral_count`
- `negative_count`
- `purchase_signal_count`
- `avg_sentiment_score`
- `top_intent_label`
- `top_pain_point_label`
- `analyzed_at`

### `comments/comment_topics.csv` schema

- `run_id`
- `platform`
- `canonical_content_id`
- `topic_tag`
- `mentions`
- `analyzed_at`

## Scoring Artifacts (additive)

- `scoring/creator_scores.csv`

### `scoring/creator_scores.csv` schema

- `run_id`
- `platform`
- `canonical_creator_id`
- `creator_handle`
- `creator_name`
- `score_total`
- `score_content_fit`
- `score_comment_quality`
- `score_purchase_signal`
- `score_engagement`
- `score_consistency`
- `score_risk`
- `reason_summary`
- `recommended_action`
- `scoring_version`
- `scored_at`

## Outreach Artifacts

Run-local:

- `outreach/outreach_candidates.csv`

Long-lived operator state:

- `outputs/operator_state/outreach_registry.csv`
- `outputs/operator_state/outreach_history.jsonl`

### `outreach/outreach_candidates.csv` schema

- `run_id`
- `platform`
- `canonical_creator_id`
- `creator_handle`
- `creator_name`
- `score_total`
- `recommended_action`
- `campaign_id`
- `owner`
- `status`
- `draft_path`
- `notes`
- `created_at`

### `outputs/operator_state/outreach_registry.csv` schema

- `platform`
- `canonical_creator_id`
- `campaign_id`
- `creator_handle`
- `creator_name`
- `owner`
- `status`
- `draft_path`
- `notes`
- `latest_run_id`
- `latest_score_total`
- `created_at`
- `updated_at`
- `first_seen_at`
- `last_contacted_at`
- `last_replied_at`
- `closed_at`
- `outcome_code`
- `outcome_note`

## DM Artifacts (existing additive phase)

- `dm/dm_drafts.csv`
- `dm/dm_drafts.json`
- `dm/dm_review.html`
- `dm/messages/<rank>_<creator_slug>.txt`

## Raw Payload Policy

- Raw collector payloads remain in JSONL files.
- Canonical CSV rows do not embed full raw JSON blobs.
- Canonical rows keep source provenance through:
  - `source`
  - `source_record_id`
  - `raw_ref` (example: `raw/source_items.jsonl#L12`)

