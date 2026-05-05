# Southpole Handoff Guide (English)

## What Southpole does

Southpole helps operators run TikTok research locally and prepare creator outreach drafts.

From the Operator UI, there are only 2 main actions:

1. `Run Collect + Aggregate`
2. `Generate DM Drafts`

Each run creates a new timestamped output folder under `outputs/runs/`.

## What Southpole does NOT do yet

- It does **not** send TikTok DMs automatically.
- It does **not** auto-install Docker Desktop.

This phase supports draft generation and manual review only.

## Before first use (required)

1. Docker Desktop installed.
2. `.env` file in project root.
3. Required values in `.env`:
   - `APIFY_TOKEN`
   - `N8N_ENCRYPTION_KEY`
   - `OPENAI_API_KEY`

Optional values:

- `OPENAI_MODEL`
- `TZ`

## Start (non-technical path)

Double-click one file:

- macOS: `start.command`
- Windows: `start.bat`

What the start launcher does automatically:

1. Checks Docker installation.
2. If Docker is missing, opens Docker Desktop download page.
3. If Docker is installed but not running, launches Docker Desktop and waits.
4. Starts Southpole stack and waits for health.
5. Opens Operator UI in browser:
   - `http://localhost:8080/ui`

## How to use the UI

Open: `http://localhost:8080/ui`

### Button 1: Run Collect + Aggregate

Fill:

- `keywords` (comma or newline separated)
- `days`
- optional `run label`

Click `Run Collect + Aggregate`.

Result:

- New run folder is created.
- `report.html`, `creators.csv`, and summary files are generated.

### Button 2: Generate DM Drafts

Fill:

- run folder (latest by default)
- `language_mode` (`ko`, `en`, `auto`)
- optional `brand_context`
- `limit`

Click `Generate DM Drafts`.

Result:

- DM draft files are created in that run folder:
  - `dm/dm_drafts.csv`
  - `dm/dm_drafts.json`
  - `dm/dm_review.html`
  - `dm/messages/*.txt`

## Where outputs are saved

All outputs are local, per run:

- `outputs/runs/<timestamp>_<slug>/`

Common files:

- `report.html`
- `summary.json`
- `keyword_totals.csv`
- `creators.csv`
- `daily_metrics.csv`
- `raw_events.csv`
- `raw_events.jsonl`
- `southpole_run_<timestamp>.xlsx`
- `dm/` (after DM generation)

## Stop

Double-click one file:

- macOS: `stop.command`
- Windows: `stop.bat`

This stops the Docker stack cleanly.

## Troubleshooting

### Docker is not installed

- Start launcher opens Docker Desktop download page.
- Install Docker Desktop, then run launcher again.

### Docker is installed but not running

- Launcher attempts to start Docker Desktop automatically.
- If timeout happens, open Docker Desktop manually and run launcher again.

### UI does not open automatically

1. Open browser manually: `http://localhost:8080/ui`
2. If still unavailable, run start launcher again.
3. If needed, ask a technical teammate to check Docker logs:
   - `docker compose logs --tail=200`

### Stack start fails

Check:

1. Docker Desktop is healthy.
2. `.env` exists and required keys are filled.
3. No port conflict on `5678` or `8080`.

## Launcher behavior note

Docker installation is **detect + open download page only**.
It is **not** automatic installation.

## Internal verification (for technical teammate)

- Portability scan:
  - `bash scripts/check-portability.sh`
- Mock verification:
  - `bash scripts/verify.sh`
