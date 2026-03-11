# KoreaSignals n8n Runbook (Instance #2)

## Scope
This runbook covers import, wiring, and E2E checks for:
- `KoreaSignals_Collector_TikTok`
- `KoreaSignals_Aggregator`

Target n8n instance:
- `http://localhost:5679`

Workflow files:
- `/Users/spmac009/Documents/Southpole/workflows/koreasignals_collector.json`
- `/Users/spmac009/Documents/Southpole/workflows/koreasignals_aggregator.json`


## Instance #2 location (Southpole-only)

Canonical workspace root:
- `/Users/spmac009/Documents/Southpole`

Compose files for instance #2 now live only here:
- `/Users/spmac009/Documents/Southpole/docker/docker-compose.instance2.yml`
- `/Users/spmac009/Documents/Southpole/docker/.env.instance2`

Helper scripts:
- `/Users/spmac009/Documents/Southpole/scripts/instance2-up.sh`
- `/Users/spmac009/Documents/Southpole/scripts/instance2-down.sh`
- `/Users/spmac009/Documents/Southpole/scripts/instance2-logs.sh`

Daily operations from Southpole:
```bash
/Users/spmac009/Documents/Southpole/scripts/instance2-up.sh
/Users/spmac009/Documents/Southpole/scripts/instance2-logs.sh
/Users/spmac009/Documents/Southpole/scripts/instance2-down.sh
```

### Safe migration procedure (do not run both stacks together)

Step A: stop old instance #2 stack from traveltrend (avoid 5679 conflict):
```bash
cd /Users/spmac009/Documents/traveltrend/docker
docker compose -f docker-compose.instance2.yml down
```

Step B: start instance #2 from Southpole:
```bash
cd /Users/spmac009/Documents/Southpole/docker
docker compose -f docker-compose.instance2.yml up -d
```

Step C: verify:
```bash
curl -I http://localhost:5679 | head -n 1
```

Verify runtime env inside n8n container (`southpole2-n8n`):
```bash
docker exec -it southpole2-n8n sh -lc 'echo GSHEET_ID=$GSHEET_ID; echo APIFY_ACTOR=$APIFY_ACTOR; [ -n "$APIFY_TOKEN" ] && echo APIFY_TOKEN=SET || echo APIFY_TOKEN=MISSING'
```

Volume reuse policy:
- Compose is configured to reuse external volumes:
  - `n8n_instance2_n8n2_data`
  - `n8n_instance2_postgres2_data`
- If missing, `instance2-up.sh` creates empty volumes with those names and prints a warning (fresh data state).

## 1) Import into n8n instance #2
1. Open `http://localhost:5679`.
2. Import collector workflow JSON.
3. Import aggregator workflow JSON.
4. Keep both workflows inactive until credentials/env are wired.

## 2) Required env vars (instance #2)
Set these on n8n instance #2 (no secrets in repo):

Core:
- `GSHEET_ID=1ToBX-uQQDxSYEf_r0zSpbWAqcr4yt6PDoJ7bkkUOvjg`
- `GSHEET_RAW_TAB=raw_events`
- `GSHEET_DAILY_TAB=daily_metrics`
- `GSHEET_KEYWORD_TAB=keyword_totals`
- `GSHEET_SNIPPETS_TAB=top_snippets`

Collector / Apify:
- `APIFY_TOKEN`
- `APIFY_ACTOR=clockworks/tiktok-scraper` (workflow normalizes `/` -> `~`)
- `APIFY_RESULTS_PER_PAGE=20`
- `APIFY_TIMEOUT_SECS=180`
- `APIFY_WAIT_FOR_FINISH_SECS=180`
- optional: `MAX_ITEMS_PER_RUN=2000`

- `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` (required so Code nodes can read `$env.*`)
Aggregator optional:
- `TOP_SNIPPETS_N=5`

## 3) Wiring Credentials in n8n (Instance #2)
Attach your Google Sheets credential to these exact nodes.

Collector:
- `Ensure_RawEvents_Header`
- `Append_Raw_Events`

Aggregator:
- `Read_Raw_Events`
- `Clear_Daily_Metrics`
- `Write_Daily_Metrics`
- `Clear_Keyword_Totals`
- `Write_Keyword_Totals`
- `Clear_Top_Snippets`
- `Write_Top_Snippets`

Notes:
- Tabs are pre-created and must not be created at runtime.
- Workflows use range-based operations only.

## 4) Preflight / E2E Readiness (dryRun)

Collector dryRun:
```bash
curl -sS -X POST 'http://localhost:5679/webhook/koreasignals/collect' \
  -H 'Content-Type: application/json' \
  -d '{"keywords":["Gen Z travel","혼자여행"],"days":30,"dryRun":true}'
```

Expect:
- No external Apify call
- No Sheets write
- Response includes:
  - `dryRun: true`
  - `perJobSummary[]` with `bucket`, `keyword`, `query`
  - `perJobCap`, `resultsLimit`
  - `apifyRunUrl` (and URL template for dataset items)
  - `sheetsRangesWouldWrite`

Aggregator dryRun:
```bash
curl -sS -X POST 'http://localhost:5679/webhook/koreasignals/aggregate' \
  -H 'Content-Type: application/json' \
  -d '{"days":30,"dryRun":true}'
```

Expect:
- Executes no Google Sheets nodes (no read/write)
- Response includes:
  - `dryRun: true`
  - `wouldWriteRanges`
  - validation/status fields

## 5) Real collection run

Collector real run:
```bash
curl -sS -X POST 'http://localhost:5679/webhook/koreasignals/collect' \
  -H 'Content-Type: application/json' \
  -d '{"keywords":["Gen Z travel","혼자여행"],"days":30}'
```

Expect collector response:
- `ok`
- `jobsTotal`, `jobsSucceeded`, `jobsFailed`
- `startedAt`, `finishedAt`, `durationMs`
- per job:
  - `sampleRawItemTop1` (when items exist)
  - `top5MappedRows` with column labels and row preview
  - `durationMs`
- If Apify errors occur, structured error shape:
  - `ok:false`
  - `stage`
  - `error.code`, `error.httpStatus`, `error.message`, `error.retriable`

## 6) Aggregate run

Aggregator real run:
```bash
curl -sS -X POST 'http://localhost:5679/webhook/koreasignals/aggregate' \
  -H 'Content-Type: application/json' \
  -d '{"days":30}'
```

Expect aggregator response:
- `ok`
- `summary` object:
  - `rawRowsRead`, `windowRows`, `uniqueVideos`, `dailyRows`, `keywordRows`, `snippetRows`, `rejectedCount`
- previews:
  - `dailyPreviewTop3`
  - `keywordPreviewTop3`
  - `snippetsPreviewTop3`
- warning field when dedupe yields zero rows

## 7) E2E Smoke Test Checklist

Env access check:
```bash
docker exec -it southpole2-n8n sh -lc 'echo $N8N_BLOCK_ENV_ACCESS_IN_NODE'
```
Expected: `false`
Env var quick check from terminal:
```bash
docker inspect southpole2-n8n --format '{{json .Config.Env}}' | jq -r '.[]' | grep -E '^(GSHEET_ID|GSHEET_RAW_TAB|GSHEET_DAILY_TAB|GSHEET_KEYWORD_TAB|GSHEET_SNIPPETS_TAB|APIFY_ACTOR|APIFY_RESULTS_PER_PAGE|APIFY_TIMEOUT_SECS|APIFY_WAIT_FOR_FINISH_SECS|APIFY_TOKEN)='
```

1. Confirm env vars exist in instance #2 config (`GSHEET_ID`, tabs, `APIFY_*`).
2. Run collector dryRun and verify no writes, expected readiness fields present.
3. Run aggregator dryRun and verify no Google Sheets node executes; response should include `wouldWriteRanges` only (row counts null).
4. Run collector real mode and confirm `raw_events` row count increased.
5. Run aggregator real mode and confirm:
   - `daily_metrics!A1:Z` updated
   - `keyword_totals!A1:Z` updated
   - `top_snippets!A1:Z` updated
6. Confirm missing metrics remain blank/null (not forced 0).

## 8) Quick row-count formulas in Sheets
- raw_events rows: `=MAX(COUNTA(raw_events!A:A)-1,0)`
- daily_metrics rows: `=MAX(COUNTA(daily_metrics!A:A)-1,0)`
- keyword_totals rows: `=MAX(COUNTA(keyword_totals!A:A)-1,0)`
- top_snippets rows: `=MAX(COUNTA(top_snippets!A:A)-1,0)`


## Executed version certainty (n8n v2)
- Due to v2 duplication/ID confusion risk, rely on response `buildTag` to confirm the actually executed published workflow version.
- Current expected buildTag: `southpole2-2026-02-25-a`.
- If curl returns a different/missing buildTag, the published workflow is stale; re-import and re-publish.

## n8n v2 publish/active notes
- After importing workflow JSON, click **Save** and then **Activate/Publish** so production webhooks are updated.
- If webhook path behavior seems stale, deactivate + activate once.
- Use production webhook endpoints (`/webhook/...`) for real runs.
- Use test webhook endpoints only from n8n editor test mode.

## Creator listup output
- Aggregator response now includes creator rollup fields (no extra sheet tab required):
  - `creatorSummary`
  - `creatorsPreviewTopN`
  - `creatorsRejectedWithReason`
- Grouping key: `authorProfileUrl` or fallback `authorHandle`.

- Prefer Executions UI over DB querying for routine troubleshooting; DB queries are last resort only.
