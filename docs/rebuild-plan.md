# Rebuild Plan Summary

## What was kept

- n8n as the operator-facing orchestrator.
- Apify collection source (`clockworks/tiktok-scraper`).
- keyword/day input model for each run.

## What was discarded

- Google Sheets as a pipeline dependency.
- legacy multi-instance runtime complexity.
- shared mutable central output table behavior.

## Clean stack decision

- Single Docker Compose stack.
- Services:
  - `n8n` (SQLite storage)
  - `pipeline` (collector + normalizer + aggregator + report writer)
- Deterministic local ports:
  - `5678` for n8n
  - `8080` for pipeline API

## Operator commands

1. Start:

```bash
./scripts/up.sh
./scripts/import-workflows.sh
```

2. Run collect + aggregate:

- n8n workflow execute, or
- `./scripts/run-helper.sh "kw1,kw2" 7 "slug"`

3. Verify:

```bash
./scripts/verify.sh
```

4. Shutdown clean:

```bash
./scripts/down.sh
```
