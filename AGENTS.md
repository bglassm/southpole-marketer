# AGENTS.md

## Scope
- Repository root: Southpole local-first TikTok research and DM draft workflow.
- Primary runtime: Docker Compose with n8n plus the `apps/pipeline` Python service.
- Operator UI: `http://localhost:8080/ui` after startup.

## Working Rules For AI Agents
- Do not commit real secrets, tokens, local databases, logs, or generated run outputs.
- Treat `.env` as local-only. Use `.env.example` for required configuration names.
- Treat `outputs/runs/`, `outputs/operator_state/`, `state/n8n/`, and `data/` as local/generated data unless a `.gitkeep` is present.
- Preserve the current local-first workflow: collect, normalize, aggregate, score, then generate DM drafts for human review.
- Do not add automatic TikTok DM sending. This repo only prepares drafts/review artifacts.
- Keep changes portable across machines; avoid hard-coded absolute local paths.

## Important Entry Points
- Human handoff: `HANDOFF.md` and `HANDOFF.ko.md`
- Main README: `README.md`
- Pipeline service docs: `apps/pipeline/README.md`
- Output schema docs: `docs/output-files.md`
- Docker stack: `docker-compose.yml`
- n8n workflow export: `n8n/workflows/southpole_run_pipeline.json`
- Python package: `apps/pipeline/src/southpole_pipeline/`
- Legacy previous-snapshot files may exist under `docker/` and `workflows/`; prefer `docker-compose.yml` and `n8n/workflows/southpole_run_pipeline.json` for the current stack.

## Useful Commands
- Start stack: `bash scripts/up.sh`
- Stop stack: `bash scripts/down.sh`
- Import n8n workflows: `bash scripts/import-workflows.sh`
- Portability scan: `bash scripts/check-portability.sh`
- Mock verification: `bash scripts/verify.sh`

## Verification Expectations
- `scripts/check-portability.sh` should report no suspicious absolute paths.
- `scripts/verify.sh` should produce a mock run and confirm required output files.
- Generated artifacts should remain ignored unless explicitly requested.
