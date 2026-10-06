# AGENTS.md

## Scope
- Canonical public repository: `https://github.com/bglassm/southpole-marketer`.
- Maintain the local-first TikTok pipeline in `apps/pipeline/`.
- Operator GUI: `http://localhost:8080/ui`; Python/FastAPI implements collection, aggregation and optional AI DM drafts.
- Root Compose runs the pipeline plus an optional n8n caller. Legacy `docker/` and `workflows/` are historical KoreaSignals/Sheets configurations, not the current GUI backend.

## Working rules
- Never commit real secrets, tokens, databases, logs, private identifiers or live run data. `.env` is local-only; use `.env.example` for configuration names.
- `outputs/runs/`, `outputs/operator_state/`, `state/n8n/`, `data/` are generated/local except `.gitkeep`.
- Small explicitly requested mock evidence may be reviewed and placed under `docs/evidence/`; label fixtures and test instrumentation. Never promote it to evidence of live collection or AI success.
- Preserve collect → normalize → aggregate. Comments, scoring, outreach sync and DM generation are separate explicit steps; do not describe them as automatically run by `/run`.
- No automatic TikTok DM sending. DM output is for human review. Posting, multi-SNS collection, OAuth and Clay are future scope, not implemented features.
- Keep instructions portable and use relative paths. Do not copy real Sheets IDs or company email addresses into examples.
- Public visibility does not establish asset rights or a software license. Preserve unresolved provenance notes.
- Do not rewrite history, force push, change visibility, or create replacement repositories without explicit authorization.
- Keep current implementation and future requirements separate. Missing reference materials remain unverified; do not infer their contents. Government-support business documents are separate context, not product achievements.

## Entry points
- `README.md`, `HANDOFF.ko.md`, `HANDOFF.md`, `REBUILD.md`, `REPO_CONTEXT.md`
- `docs/architecture.md`, `docs/roadmap.md`, `docs/verification.md`
- `apps/pipeline/README.md`, `docs/output-files.md`
- `docker-compose.yml`, `n8n/workflows/southpole_run_pipeline.json`
- Legacy only: `docs/runbook.md`, `docs/looker_studio_setup.md`, `docker/`, `workflows/`

## Verification
- `bash scripts/check-portability.sh`: inspect findings rather than allowlisting personal paths.
- `bash scripts/verify.sh`: Docker mock file-existence check; old fixture dates can yield zero rows. Verify row counts separately as described in `docs/verification.md`.
- Run real external collection/AI calls only with explicit authorization and local credentials; never print credentials.
- Documentation-only changes need link/diff checks and evidence consistency, not new product functionality.
