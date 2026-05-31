# Cockpit Marketplace Empty State Actionability V1

Implemented GitHub issue #93 for the Marketplace Matches and Alerts empty states.

## What changed

- Matches and Alerts now load mission context only after their primary endpoint returns `items: []`.
- Empty states distinguish no missions, missions with no recorded scan, scan errors/degraded state, scan-run zero results, and active filters hiding results.
- Mission-context failures show `DATA_MISSING` instead of implying a verified cause.
- Empty states include a visible next action: open mission setup, refresh, or clear filters.
- Regression tests cover empty states with and without mission context.

## Evidence

- `marketplace-matches-empty-state.png`
- `marketplace-alerts-empty-state.png`
- `marketplace-matches-empty-state-mobile.png`
- `marketplace-alerts-empty-state-mobile.png`

Screenshots were captured in a real browser with mocked empty Marketplace API responses so the UI evidence is deterministic and does not depend on local backend availability.
