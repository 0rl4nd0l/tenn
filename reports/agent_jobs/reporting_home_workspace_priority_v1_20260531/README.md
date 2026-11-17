# Reporting Home Workspace Priority V1

## Result

Resolved GitHub issue #42 by moving Cockpit Home's Strategy Lab status and artifact-review cards below the primary Home workspace content.

## Scope

- Changed `cockpit-ui/components/cockpit/home/home-page.tsx` so `{children}` render before the Strategy Lab block.
- Added `data-testid="home-strategy-lab-section"` for a stable DOM-order regression assertion.
- Updated `cockpit-ui/lib/cockpit-home-api.test.ts` with route-aware Home page fetch mocks and a regression test proving `home-useful-now-panel` precedes the Strategy Lab block.

## Safety

- Target system layer: Client.
- No backend, RAG, financial truth, memory, extraction, runtime, route, dependency, or lockfile changes.
- Strategy Lab API routes, fetch behavior, status labels, and read-only DATA_MISSING/error behavior remain unchanged.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/reporting_home_workspace_priority_v1_20260531.md` - passed
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/reporting_home_workspace_priority_v1_20260531.md` - passed
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/reporting_home_workspace_priority_v1_20260531.md` - passed
- `corepack pnpm --dir cockpit-ui install --frozen-lockfile` - passed
- `corepack pnpm --dir cockpit-ui exec vitest run lib/cockpit-home-api.test.ts` - passed, 16 tests
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/home/home-page.tsx lib/cockpit-home-api.test.ts` - passed
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit` - passed
- `corepack pnpm --dir cockpit-ui build` - passed
- `git diff --check` - passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/reporting_home_workspace_priority_v1_20260531.md` - passed
