# Southpole Repo Context

## Architecture
- Docker stack (`docker/docker-compose.instance2.yml`):
  - `southpole2-postgres` (Postgres 16)
  - `southpole2-n8n` (n8n)
- n8n exposed on `127.0.0.1:5679`.
- Persistent volumes (external):
  - `n8n_instance2_postgres2_data`
  - `n8n_instance2_n8n2_data`

## Active workflows
- Collector: `KoreaSignals_Collector_TikTok` (`id=4QGwto8MFAMH0XCy`)
  - Webhook: `POST /webhook/koreasignals/collect`
  - Core flow: parse -> header/write guards -> jobs/split -> Apify -> map -> append -> finalize
  - Current conventions: `runId` end-to-end, `raw_events` ranges `A1:V1` and `A:V`
- Aggregator: `KoreaSignals_Aggregator` (`id=XWcJTb1oXxF1NZWt`)
  - Webhook: `POST /webhook/koreasignals/aggregate`
  - Reads `raw_events`, writes:
    - `daily_metrics`
    - `keyword_totals`
    - `top_snippets`
    - `creators`

## Service/data dependencies
- Apify API (`APIFY_TOKEN`, actor id).
- Google Sheets OAuth credential references on all Sheets nodes.
- Spreadsheet tabs must already exist (no tab creation in workflows).

## Operational constraints
- Exactly one `SplitInBatches` in Collector.
- Range-based Google Sheets operations only.
- Out-of-lookback rows are not dropped in Collector mapping; `inLookback` is marked.
- Deterministic DB overwrite is used when updating active workflow definitions.

## Known issues/history to watch
- UI imports may not overwrite active workflow rows reliably; verify by workflow id in DB.
- Missing Sheets credential refs cause runtime write/read failures.
- Apify runs can remain queued (`READY/RUNNING`) and require polling + timeout handling.
- Build tags are used to verify executed workflow version.
