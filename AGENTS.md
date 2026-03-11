# AGENTS.md

## Scope
- Workspace root: `/Users/spmac009/Documents/Southpole`
- Primary stack: local n8n instance #2 (`southpole2-*`) with Postgres via Docker Compose.

## Working rules
- Keep edits concise and repository-native.
- Do not add managerial/handoff prose.
- Do not commit real secrets.
- Prefer deterministic DB apply for n8n workflow changes over UI-only imports.
- Do not change webhook paths unless explicitly requested.
- Keep workflows range-based for Google Sheets operations (no tab creation operations).

## Runtime topology
- Compose file: `/Users/spmac009/Documents/Southpole/docker/docker-compose.instance2.yml`
- Env file (local only): `/Users/spmac009/Documents/Southpole/docker/.env.instance2`
- n8n URL: `http://localhost:5679`
- Postgres container: `southpole2-postgres`
- n8n container: `southpole2-n8n`

## Workflow IDs (must stay stable)
- Collector: `4QGwto8MFAMH0XCy` (`/webhook/koreasignals/collect`)
- Aggregator: `XWcJTb1oXxF1NZWt` (`/webhook/koreasignals/aggregate`)

## Workflow apply policy
- Preferred: deterministic SQL overwrite into `workflow_entity` and active `workflow_history` row for the exact workflow id.
- After DB apply, restart `southpole2-n8n`.
- Verify by querying `workflow_entity.nodes::text` for expected markers (`buildTag`, `runId`, gate expressions, ranges).

## Credentials policy
- Keep only credential references (`id`, `name`) in workflow JSON.
- Never place OAuth tokens/keys into tracked files.
- Ensure all Google Sheets nodes include `googleSheetsOAuth2Api` credential references.

## Useful commands
- Up: `/Users/spmac009/Documents/Southpole/scripts/instance2-up.sh`
- Down: `/Users/spmac009/Documents/Southpole/scripts/instance2-down.sh`
- Logs: `/Users/spmac009/Documents/Southpole/scripts/instance2-logs.sh`

## Verification expectations
- Collector `dryRun=true`: runs scrape/mapping preview but no append.
- Collector `dryRun=false`: header/write path executes and appends rows.
- Aggregator `dryRun=false`: reads `raw_events`, writes aggregate tabs.
- Aggregator `dryRun=true`: compute preview only, no sheet writes.
