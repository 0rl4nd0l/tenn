# Cockpit Operations Universe Backfill Review Gate v1

## Summary

Implemented the Operations slice of GitHub issue #51. The ASX Universe Announcement Backfill action now requires a successful Preview Run for the current history-window and document-processing settings before Run Backfill can dispatch the backend ops job.

## Scope

- Added review state keyed to the exact `universe_announcement_enrichment_backfill` args.
- Preview Run stores the reviewed command, impact, timeout, and guard message for the current settings.
- Run Backfill is disabled until the current settings have been previewed, and the run handler also blocks if review state is missing or stale.
- Changing either history window or process-documents resets the review state.
- Added focused component tests for the blocked, allowed, and reset paths.

## Boundaries

- No backend action routes changed.
- No API client contracts changed.
- No DB, Qdrant, news, memory, extraction, prompt, gold-label, model/runtime/GPU/service config, or production data writes.
- No live backfill, backend restart, model load, or production runtime action was run.
- This is a partial slice for #51; Holdings deletion, History re-run, Restart Backend, and other high-impact action gates remain open follow-up scope.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_operations_universe_backfill_review_gate_v1_20260602.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_operations_universe_backfill_review_gate_v1_20260602.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_operations_universe_backfill_review_gate_v1_20260602.md`
- `corepack pnpm --dir cockpit-ui install --frozen-lockfile`
- `corepack pnpm --dir cockpit-ui exec vitest run components/cockpit/operations/operations-screen.test.tsx`
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/operations/operations-screen.tsx components/cockpit/operations/operations-screen.test.tsx`
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_operations_universe_backfill_review_gate_v1_20260602.md`
