# Southpole repository context

Canonical repository: [bglassm/southpole-marketer](https://github.com/bglassm/southpole-marketer), public. This repository is distinct from SocialHub and `flux-marketing-research-tool`; their features and results are not implementation evidence here.

## Current implementation

- `apps/pipeline/`: Python/FastAPI API, embedded operator GUI, CLI, collector, normalization/aggregation, HTML/CSV/XLSX writers.
- `GET /ui`: keyword/day input, `Run Collect + Aggregate`, optional `Generate DM Drafts`, run selection and creator preview.
- `POST /run`: TikTok Apify collection, or `mock_file` through API/CLI, followed by local processing. Does not run all later stages.
- `POST /dm/generate`: explicit OpenAI draft generation from a run's `creators.csv`; no sending and no local fallback if credentials are missing.
- Comment target/collection/analysis, deterministic creator scoring and outreach registry sync are separate API/CLI operations.
- `outputs/runs/`: per-run artifacts. `outputs/operator_state/`: CSV/JSONL outreach state. Both are local/ignored.

## Runtime boundaries

`docker-compose.yml` starts Python and n8n. The GUI calls Python directly; it does not require an imported n8n workflow. `n8n/workflows/southpole_run_pipeline.json` wraps `/run` via manual/webhook triggers. It does not orchestrate DM or all enrichment stages.

`docker/docker-compose.instance2.yml` and `workflows/` preserve the older n8n/Postgres/Google Sheets architecture. They are not prerequisites for the current local-file pipeline. See [current architecture](docs/architecture.md) and [legacy runbook](docs/runbook.md).

## Configuration and evidence

Use `.env.example` locally. `APIFY_TOKEN` is for live collection, `OPENAI_API_KEY` for optional AI drafts, `N8N_ENCRYPTION_KEY` for n8n. Mock collection requires no API keys. Comment collection also needs an appropriate comment Actor configuration.

[Verification](docs/verification.md) distinguishes mock runs from unverified live calls. [Public-history review](docs/public-history-review.md) records remaining identifiers and rights questions in older commits. [Roadmap](docs/roadmap.md) covers future scope separately.

Automatic messaging, publishing, multi-SNS collection, OAuth and Clay are not implemented. Campaign IDs in CSV state are not a campaign-management product. Government-support plans are not evidence of this product's delivery or performance.
