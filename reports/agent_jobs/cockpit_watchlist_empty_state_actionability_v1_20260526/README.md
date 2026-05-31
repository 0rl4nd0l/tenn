# Cockpit Watchlist Empty State Actionability V1

## Summary

Resolved GitHub issue #92 by replacing the Watchlist dead-end empty state with source-grounded portfolio-holding suggestions when holdings are available, and an explicit `DATA_MISSING` state when no candidate source is available.

## Scope

- The Watchlist screen now loads existing holdings context only when the watchlist is empty.
- Empty Watchlist candidates show a visible source reason such as `Source: Current holding in Core portfolio`.
- A suggested ticker can be added through the existing `/api/cockpit/watchlist` endpoint without retyping it.
- Duplicate/add failures remain visible inline.
- Backend, runtime, financial truth, memory, extraction, parser, and gold-label surfaces were not changed.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_watchlist_empty_state_actionability_v1_20260526.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_watchlist_empty_state_actionability_v1_20260526.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_watchlist_empty_state_actionability_v1_20260526.md`
- `corepack pnpm --dir cockpit-ui install --frozen-lockfile`
- `corepack pnpm --dir cockpit-ui exec vitest run components/cockpit/watchlist/watchlist-screen.test.tsx`
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/watchlist/watchlist-screen.tsx components/cockpit/watchlist/watchlist-screen.test.tsx`
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit`
- `corepack pnpm --dir cockpit-ui build`
- `corepack pnpm --dir cockpit-ui exec node -e "...page.getByText('DATA_MISSING: no current holdings or watchlist suggestion source is available.').waitFor(...)..."`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_watchlist_empty_state_actionability_v1_20260526.md`

## Evidence

- Screenshot: `reports/agent_jobs/cockpit_watchlist_empty_state_actionability_v1_20260526/watchlist-empty-state.png`
- Diff gate: `reports/agent_jobs/cockpit_watchlist_empty_state_actionability_v1_20260526/diff-check.json`

## Runtime Note

The browser screenshot was captured with the backend unavailable, so it proves the degraded `DATA_MISSING` path. Component tests prove the holdings-backed candidate path and one-click add payload without requiring production data access.
