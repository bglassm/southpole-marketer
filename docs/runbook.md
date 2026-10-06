# Legacy KoreaSignals n8n runbook

This is a historical reference for the n8n/Postgres/Google Sheets instance on port **5679**. It is not the runtime used by the current Southpole Operator GUI. For the maintained Python/local-file flow, use [REBUILD.md](../REBUILD.md) and [architecture](architecture.md).

## Preserved components

- `workflows/koreasignals_collector.json`: TikTok collector workflow.
- `workflows/koreasignals_aggregator.json`: Sheets-based aggregation.
- `workflows/_all*.json`: older workflow exports; not the current import target.
- `docker/docker-compose.instance2.yml`: n8n plus Postgres with pre-existing external volumes.
- `scripts/instance2-up.sh`, `instance2-down.sh`, `instance2-logs.sh`: legacy helpers.

The root `docker-compose.yml` and `n8n/workflows/southpole_run_pipeline.json` are a separate, current configuration. Root `scripts/import-workflows.sh` imports that current wrapper, not these older exports.

## Historical setup prerequisites

The legacy compose file expects local `docker/.env.instance2` configuration and external volumes named `n8n_instance2_n8n2_data` and `n8n_instance2_postgres2_data`. The helper may create empty volumes when missing; it does not restore old data. Review the configuration and back up existing state before using it.

Use a spreadsheet and credentials you control. Configuration names include:

```text
GSHEET_ID=<YOUR_SPREADSHEET_ID>
GSHEET_RAW_TAB=raw_events
GSHEET_DAILY_TAB=daily_metrics
GSHEET_KEYWORD_TAB=keyword_totals
GSHEET_SNIPPETS_TAB=top_snippets
APIFY_ACTOR=clockworks/tiktok-scraper
```

Keep `APIFY_TOKEN`, Google credentials, encryption keys and database passwords in local secret storage. Existing compose defaults are not deployment credentials. Do not print `docker inspect ... .Config.Env` or token values into reports.

## Reference operations

From this repository's root, with local prerequisites already configured:

```bash
bash scripts/instance2-up.sh
bash scripts/instance2-logs.sh
bash scripts/instance2-down.sh
```

The legacy UI is `http://localhost:5679`. Import only the intended historical collector/aggregator exports, attach your own Google Sheets credentials, and review all write targets before activation. The aggregator can clear/rewrite its target sheet ranges. Do not use an inherited spreadsheet ID.

Historical webhooks are `/webhook/koreasignals/collect` and `/webhook/koreasignals/aggregate`. A dry run is a readiness check, not proof of a successful real collection or sheet update. No legacy n8n, Sheets or Looker service was executed in the current mock verification.

## Historical identifiers

Personal machine paths and a literal spreadsheet ID have been removed from the current document. Old commits and the unchanged historical branch can still contain them. See [public-history review](public-history-review.md) for file/commit references and follow-up actions; removing current text does not remove Git history.
