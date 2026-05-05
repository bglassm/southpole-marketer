# Southpole

Southpole is a local-first TikTok research + DM draft workflow for operators.

- Operator UI: `http://localhost:8080/ui`
- Outputs: `outputs/runs/<timestamp>_<slug>/`
- Main actions in UI:
  1. `Run Collect + Aggregate`
  2. `Generate DM Drafts`

Canonical additive pipeline support is now included for:

- canonical normalized post rows
- comment target selection + comment collection
- comment analysis
- creator scoring
- outreach registry sync to `outputs/operator_state/`

Legacy outputs and existing `/run` + `/dm/generate` behavior remain compatible.

## Handoff Guides

- English handoff guide: `HANDOFF.md`
- Korean handoff guide: `HANDOFF.ko.md`

## Internal Docs (Technical)

- Output file schema: `docs/output-files.md`
- Pipeline service details: `apps/pipeline/README.md`
