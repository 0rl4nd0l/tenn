# Cockpit Home Mobile Status Header Wrap

## Scope

- GitHub issue: #43, Cockpit landing page mobile status/header chips overflow off-screen.
- Lane: Reporting.
- Execution mode: SAFE EXTENSION MODE.
- Target layer: Next.js Cockpit UI presentation layer only.
- Contract boundary: backend routes, BFF data contracts, financial truth, provenance, memory, runtime services, Docker, and environment files were not changed.

## Changes

- `cockpit-ui/components/cockpit/home/data-health-strip.tsx`
  - Changed the small-viewport layout from a horizontal scroll strip to a responsive one-column/two-column grid.
  - Added `min-w-0`, truncation, and stable alignment so labels and values remain inside the viewport.
- `cockpit-ui/components/cockpit/home/market-status-header.tsx`
  - Stacked and wrapped the status header on narrow viewports.
  - Kept desktop alignment with the existing row layout at wider breakpoints.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_mobile_status_header_wrap_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_home_mobile_status_header_wrap_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_home_mobile_status_header_wrap_v1_20260525.md`: passed.
- `corepack pnpm exec eslint components/cockpit/home/data-health-strip.tsx components/cockpit/home/market-status-header.tsx --max-warnings=0`: passed.
- `corepack pnpm exec tsc --noEmit --pretty false`: passed.
- Browser smoke at `390x844` against `/`: passed. `System Status`, `Backend liveness`, `Holdings`, and `Market movers` were visible; no critical status/header text was off the right edge; `documentElement.scrollWidth` was `390`.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_mobile_status_header_wrap_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py release cockpit_home_mobile_status_header_wrap_v1_20260525`: passed.

## Result

- Collision risk: LOW.
- Disallowed files: none.
- Commit: recorded in the issue closeout comment and final agent report.
