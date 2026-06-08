---
job_id: cockpit_operations_universe_backfill_review_gate_v1_20260602
title: Cockpit Operations universe backfill review gate
owner: Codex
lane: Reporting
primary_lane: Reporting
supporting_lanes:
  - Evaluation
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/cockpit_operations_universe_backfill_review_gate_v1_20260602
allowed_files:
  - docs/agent_tasks/cockpit_operations_universe_backfill_review_gate_v1_20260602.md
  - reports/agent_jobs/cockpit_operations_universe_backfill_review_gate_v1_20260602/README.md
  - reports/agent_jobs/cockpit_operations_universe_backfill_review_gate_v1_20260602/status.json
  - reports/agent_jobs/cockpit_operations_universe_backfill_review_gate_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_operations_universe_backfill_review_gate_v1_20260602/diff-check.json
  - cockpit-ui/components/cockpit/operations/operations-screen.tsx
  - cockpit-ui/components/cockpit/operations/operations-screen.test.tsx
---

# Cockpit Operations Universe Backfill Review Gate v1

## Objective

Address the Operations ASX Universe Announcement Backfill slice of GitHub issue #51 by requiring a successful preview for the current backfill settings before the UI can dispatch the queued backfill job.

## Scope

- Add client-side review state to the Operations ASX Universe Announcement Backfill panel.
- Keep Preview Run as the gate that records command, impact, timeout, and guard details for the current settings.
- Disable or block Run Backfill until the current history-window and process-documents settings have a successful preview.
- Reset the review state when either setting changes.
- Add focused component coverage proving an ungated run cannot call `startActionJob`.

## Forbidden

- Do not touch backend action routes, API client contracts, Holdings, History, chat suggested-action files, DB/Qdrant/news/memory, extraction, prompts, gold labels, model/runtime/GPU/service config, or production data.
- Do not run live backfill, start/restart backend, or load models.
- Do not claim #51 is fully fixed; this slice only covers Operations universe backfill review gating.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_operations_universe_backfill_review_gate_v1_20260602.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_operations_universe_backfill_review_gate_v1_20260602.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_operations_universe_backfill_review_gate_v1_20260602.md`
- `corepack pnpm --dir cockpit-ui exec vitest run components/cockpit/operations/operations-screen.test.tsx`
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/operations/operations-screen.tsx components/cockpit/operations/operations-screen.test.tsx`
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_operations_universe_backfill_review_gate_v1_20260602.md`
