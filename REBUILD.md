# Rebuild (Fresh Mac)

## 1) Prerequisites
- Install Docker Desktop.
- Ensure these paths exist:
  - `/Users/spmac009/Documents/Southpole`
  - `/Users/spmac009/Documents/Southpole/docker`

## 2) Restore local secrets
1. Copy `.env.example` to `docker/.env.instance2`.
2. Fill required secrets/ids in `docker/.env.instance2`:
   - `N8N_BASIC_AUTH_USER`
   - `N8N_BASIC_AUTH_PASSWORD`
   - `N8N_ENCRYPTION_KEY`
   - `APIFY_TOKEN`
   - `GSHEET_ID`
   - `POSTGRES2_PASSWORD`

## 3) Start services
```bash
cd /Users/spmac009/Documents/Southpole
/Users/spmac009/Documents/Southpole/scripts/instance2-up.sh
```

## 4) Expected ports/services
- n8n editor/webhook: `http://localhost:5679`
- Postgres: internal Docker network (`southpole2-postgres:5432`)

## 5) Restore/verify workflows in DB
- Collector workflow id: `4QGwto8MFAMH0XCy`
- Aggregator workflow id: `XWcJTb1oXxF1NZWt`

Verify ids exist:
```bash
docker exec -i southpole2-postgres psql -U n8n2 -d n8n2 -c "select id, name, active from workflow_entity where id in ('4QGwto8MFAMH0XCy','XWcJTb1oXxF1NZWt');"
```

## 6) Runtime checks
Collector (non-dry run):
```bash
curl -sS -X POST 'http://localhost:5679/webhook/koreasignals/collect' \
  -H 'Content-Type: application/json' \
  -d '{"keywords":["Gen Z travel"],"days":30,"dryRun":false}'
```

Aggregator (non-dry run):
```bash
curl -sS -X POST 'http://localhost:5679/webhook/koreasignals/aggregate' \
  -H 'Content-Type: application/json' \
  -d '{"days":30,"dryRun":false}'
```

Expected:
- Collector response includes `buildTag`, `runId`, and non-error `perJobSummary`.
- Aggregator response includes `buildTag`, non-null summary counts when raw data exists.

## 7) Shutdown
```bash
cd /Users/spmac009/Documents/Southpole
/Users/spmac009/Documents/Southpole/scripts/instance2-down.sh
```
