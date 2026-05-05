# Rebuild Guide

## 1. Prerequisites
- Install Docker Desktop.
- Clone this private repository.
- Ensure Docker Desktop is running before starting the stack.

## 2. Configure Environment
```bash
cp .env.example .env
```

Fill at least:
- `APIFY_TOKEN`
- `N8N_ENCRYPTION_KEY`
- `OPENAI_API_KEY`

Optional:
- `OPENAI_MODEL`
- `OPENAI_ANALYSIS_MODEL`
- `APIFY_TIKTOK_COMMENTS_ACTOR_ID`

## 3. Start
macOS:
```bash
./start.command
```

Windows:
```bat
start.bat
```

Shell fallback:
```bash
bash scripts/up.sh
```

## 4. Open UI
Go to:

```text
http://localhost:8080/ui
```

Use:
1. `Run Collect + Aggregate`
2. `Generate DM Drafts`

## 5. Verify
```bash
bash scripts/check-portability.sh
bash scripts/verify.sh
```

`verify.sh` uses mock data and should create a local run under `outputs/runs/`.

## 6. Stop
macOS:
```bash
./stop.command
```

Windows:
```bat
stop.bat
```

Shell fallback:
```bash
bash scripts/down.sh
```

## Notes For Manus AI
- Start with `AGENTS.md`, `README.md`, `HANDOFF.md`, and `REPO_CONTEXT.md`.
- Do not request or expose real `.env` values.
- Generated local artifacts are intentionally not part of the repository.
