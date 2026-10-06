# Runtime transition record

The maintained implementation uses a Python/FastAPI operator GUI and local per-run artifacts. Google Sheets and the legacy multi-instance runtime are not dependencies of that flow.

| Configuration | Purpose | Entry points |
| --- | --- | --- |
| Current Python service | TikTok collection, normalization/aggregation, local reports, optional AI drafts | `apps/pipeline/`, `/ui`, CLI |
| Current n8n wrapper | Manual/webhook call to Python `/run` | root Compose, `n8n/workflows/` |
| Legacy KoreaSignals | n8n/Postgres/Sheets collector and aggregator | `docker/`, `workflows/`, [legacy runbook](runbook.md) |

GUI requests go directly to Python; n8n is not the GUI backend. Comments, scoring, outreach sync and drafts are separate explicit operations.

Use [REBUILD.md](../REBUILD.md) for reproducible setup, [architecture](architecture.md) for current component boundaries, and [roadmap](roadmap.md) for future scope. Historical configurations are retained as reference, not live-service acceptance evidence.
