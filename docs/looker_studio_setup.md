# Looker Studio Setup (KoreaSignals)

## Data source
1. Open Looker Studio -> Create -> Data Source.
2. Choose Google Sheets connector.
3. Select spreadsheet:
   - `1ToBX-uQQDxSYEf_r0zSpbWAqcr4yt6PDoJ7bkkUOvjg`
4. Add these tabs as separate data sources:
   - `daily_metrics`
   - `keyword_totals`
   - `top_snippets`

## Field types
Set field types explicitly:

`daily_metrics`
- `date_kst`: Date (format `YYYY-MM-DD`)
- `bucket`: Text
- `keyword`: Text
- `videos_count`: Number
- `play_sum`, `digg_sum`, `share_sum`, `comment_sum`: Number
- `play_avg`, `digg_avg`, `share_avg`, `comment_avg`: Number

`keyword_totals`
- `bucket`, `keyword`: Text
- `videos_count`: Number
- `play_sum`, `digg_sum`, `share_sum`, `comment_sum`: Number
- `play_per_video`, `digg_per_video`, `share_per_video`, `comment_per_video`: Number

`top_snippets`
- `bucket`, `keyword`, `id`: Text
- `createDateKST`: Date
- `createTimeISO`: Date & Time
- `playCount`, `diggCount`, `shareCount`, `commentCount`, `authorFollowers`: Number
- `text`, `videoUrl`, `authorNickName`: Text

## Recommended report pages
1. Overview
- Scorecards: total videos, total plays, total likes, total comments
- Time series: `date_kst` vs `play_sum`
- Filters: `bucket`, `keyword`, `date_kst`

2. Keyword Performance
- Table from `keyword_totals`
- Metrics: `videos_count`, `play_sum`, `play_per_video`, `digg_per_video`, `comment_per_video`
- Sort by `play_sum` desc

3. Top Snippets
- Table from `top_snippets`
- Dimensions: `bucket`, `keyword`, `authorNickName`, `text`, `videoUrl`
- Metrics: `playCount`, `diggCount`, `commentCount`, `shareCount`
- Sort by `playCount` desc

## Null/blank metric handling
The workflows preserve missing metrics as null/blank. In Looker Studio:
- Keep nulls as null for quality checks.
- If needed for charts, add calculated fields like:
  - `play_sum_filled = IFNULL(play_sum, 0)`

## Refresh and validation
1. Run collector webhook, then aggregator webhook.
2. Refresh data sources in Looker Studio.
3. Validate row counts match sheet tabs.
4. Spot-check top snippets against `top_snippets` tab values.
