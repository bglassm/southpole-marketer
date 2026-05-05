# Southpole Repo Context

Southpole is a local-first TikTok research workflow for operators. It collects TikTok research data through Apify, normalizes and aggregates it, produces local reports/workbooks, scores creators, and generates DM drafts for human review.

## Architecture
- `docker-compose.yml` runs n8n and the pipeline service.
- `apps/pipeline` contains the Python service, CLI, operator UI, scoring, comment analysis, file writers, and DM draft generation.
- `n8n/workflows/southpole_run_pipeline.json` contains the n8n workflow export.
- `outputs/runs/<timestamp>_<slug>/` contains generated run artifacts.
- `outputs/operator_state/` contains generated outreach registry/history state.
- `state/n8n/` contains local n8n runtime state and must not be committed.

## Runtime Flow
1. Operator starts the stack with `start.command`, `start.bat`, or `scripts/up.sh`.
2. Operator opens `http://localhost:8080/ui`.
3. `Run Collect + Aggregate` collects data, normalizes rows, writes report/workbook outputs, and prepares scoring artifacts.
4. `Generate DM Drafts` reads a run's `creators.csv` and creates reviewable draft messages.

## Key APIs
- `GET /health`
- `GET /ui`
- `GET /runs`
- `POST /run`
- `POST /dm/generate`
- `POST /comments/targets`
- `POST /comments/collect`
- `POST /comments/analyze`
- `POST /scoring/creators`
- `POST /outreach/sync`

## Required Local Configuration
- Copy `.env.example` to `.env`.
- Fill `APIFY_TOKEN`, `N8N_ENCRYPTION_KEY`, and `OPENAI_API_KEY` for live operation.
- Optional/comment-specific: `APIFY_TIKTOK_COMMENTS_ACTOR_ID`, `OPENAI_ANALYSIS_MODEL`.

## Privacy And Safety Notes
- The repo is intended to be private.
- Real `.env`, run outputs, outreach state, and n8n databases are intentionally ignored.
- TikTok DM sending is not automated; generated messages are drafts for human review.
