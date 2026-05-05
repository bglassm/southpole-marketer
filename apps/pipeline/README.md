# Pipeline Service

This service keeps the existing MVP pipeline shape and adds canonical/comment/scoring/outreach flows without removing legacy outputs.

Core path:

1. collect via Apify
2. normalize
3. aggregate
4. write local files
5. generate report + workbook
6. generate DM drafts from `creators.csv`

Additive path:

1. build comment targets
2. collect comments
3. analyze comments
4. score creators
5. sync outreach state

## API

- `GET /health`
- `GET /ui` (operator web UI)
- `GET /runs`
- `GET /runs/{run_id}/creators`
- `POST /run`
- `POST /dm/generate`
- `POST /comments/targets`
- `POST /comments/collect`
- `POST /comments/analyze`
- `POST /scoring/creators`
- `POST /outreach/sync`

## CLI

Run from container or from local environment with `PYTHONPATH=/app/src` (container) or `PYTHONPATH=apps/pipeline/src` (repo root).

```bash
python -m southpole_pipeline.cli run --keywords "kbeauty,oliveyoung" --days 7 --slug local
python -m southpole_pipeline.cli dm --run-dir 2026-03-12_184500_local --language-mode ko --limit 10
python -m southpole_pipeline.cli comments-targets --run-dir 2026-03-12_184500_local --max-targets 20
python -m southpole_pipeline.cli comments-collect --run-dir 2026-03-12_184500_local
python -m southpole_pipeline.cli comments-analyze --run-dir 2026-03-12_184500_local --limit 200
python -m southpole_pipeline.cli score-creators --run-dir 2026-03-12_184500_local
python -m southpole_pipeline.cli outreach-sync --run-dir 2026-03-12_184500_local --campaign-id spring-2026
```

Mock run:

```bash
python -m southpole_pipeline.cli run \
  --keywords "kbeauty,oliveyoung" \
  --days 7 \
  --slug mock \
  --mock-file /app/fixtures/mock_apify_items.json
```

## New Environment Variables

- `APIFY_TIKTOK_COMMENTS_ACTOR_ID` (required only for live comment collection)
- `OPENAI_ANALYSIS_MODEL` (optional, falls back to `OPENAI_MODEL`)
- `OPERATOR_STATE_ROOT` (default: sibling of `OUTPUT_ROOT`, typically `outputs/operator_state`)

## Compatibility Notes

- Existing `POST /run` and `POST /dm/generate` behavior remains.
- Legacy output files (`raw_events.*`, `keyword_totals.csv`, `creators.csv`, `daily_metrics.csv`) remain unchanged.
- DM generation still uses `creators.csv` as primary source in this phase.

