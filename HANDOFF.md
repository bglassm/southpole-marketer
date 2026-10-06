# Southpole operator guide

Southpole is a local TikTok keyword research tool with optional AI DM drafts. The canonical [repository is public](https://github.com/bglassm/southpole-marketer); credentials and live research output stay local.

## Start

Install/run Docker Desktop, copy `.env.example` to `.env`, then use `start.command` (macOS), `start.bat` (Windows), or `bash scripts/up.sh`. Open `http://localhost:8080/ui`.

- Live collection needs `APIFY_TOKEN` and access to the configured Actor.
- Optional AI drafts need `OPENAI_API_KEY`.
- n8n needs `N8N_ENCRYPTION_KEY`.
- Mock collection needs no API key. See [REBUILD.md](REBUILD.md) for Docker and Python-only commands.

## Keyword-to-creator workflow

1. Enter comma/newline-separated keywords, lookback days and an optional run label.
2. Select **Run Collect + Aggregate**. Python collects TikTok data through Apify, normalizes it and writes local aggregates.
3. Inspect **Latest Creators Preview** and the HTML report/creator CSV links. The summary JSON and workbook are available in the run folder.
4. Optionally select **Generate DM Drafts** with a run, language, limit and brand context.
5. Review `dm/dm_review.html` or per-creator text files manually. No messages are sent.

Outputs live under `outputs/runs/<run_id>/`. Missing source metrics are not verified values. DM generation has no key-free fallback, and the review page does not persist approval decisions.

## Verification and limits

[GUI captures and mock evidence](docs/verification.md) use fixed fixtures, not live collection. The GUI has no mock selector; run the documented mock CLI/API request before opening the result preview. `bash scripts/verify.sh` checks file existence only and can pass with zero rows when fixtures age outside its seven-day window.

Comments, scoring and outreach state sync are separate API/CLI stages, not automatic stages of `/run`. The current n8n workflow only wraps `/run`; legacy KoreaSignals/Sheets files are separate. See [architecture](docs/architecture.md), [API/CLI](apps/pipeline/README.md), [roadmap](docs/roadmap.md).

No automatic DM sending, posting/scheduling, OAuth, multi-SNS collection or Clay integration is implemented. The API lacks user authentication and should not be exposed directly to the public internet.

Stop with `stop.command`, `stop.bat`, or `bash scripts/down.sh`. Check Docker health, port conflicts and local logs when troubleshooting; redact credentials before sharing logs. Preserve n8n state before resolving encryption-key mismatches. See [public-history review](docs/public-history-review.md) for unresolved historical identifiers and asset provenance.
