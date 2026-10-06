# Legacy Looker Studio reference

This document describes the historical KoreaSignals Google Sheets reporting layout. It is not an implemented dashboard or required dependency of the current Southpole Python pipeline. Current outputs are local CSV/JSON/HTML/XLSX files; there is no automatic Looker synchronization.

## Data sources

For a separately configured legacy deployment, choose a spreadsheet you own (`<YOUR_SPREADSHEET_ID>`) in Looker Studio's Google Sheets connector. Do not reuse a spreadsheet identifier from old repository history.

Add `daily_metrics`, `keyword_totals` and `top_snippets` as separate sources only if the legacy workflows produce those tabs. The current pipeline's similarly named CSV files are not a guarantee of the same schema; compare [output schemas](output-files.md) before any manual import.

## Historical field layout

| Source | Dimensions | Metrics |
| --- | --- | --- |
| `daily_metrics` | `date_kst` (Date), `bucket`, `keyword` | `videos_count`, `play_sum`, `digg_sum`, `share_sum`, `comment_sum`, averages |
| `keyword_totals` | `bucket`, `keyword` | `videos_count`, sums and per-video metrics |
| `top_snippets` | `id`, `bucket`, `keyword`, dates, text and post/profile references | play/like/comment/share/follower counts where available |

Potential report pages are an overview, keyword table and top-snippet table. Missing metrics should remain missing for quality review; display-only `IFNULL` expressions do not make missing measurements observed data.

## Validation and access

Confirm data ownership, spreadsheet sharing and report sharing separately. Compare row counts and sample records before sharing a report. These steps are a configuration reference, not evidence that this repository operates a live Looker service. See the [legacy runbook](runbook.md) and [public-history review](public-history-review.md).
