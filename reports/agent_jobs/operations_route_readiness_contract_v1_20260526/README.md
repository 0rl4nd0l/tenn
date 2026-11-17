# Operations Route Readiness Contract V1

## Summary

Resolved GitHub issue #110 by adding an explicit Operations UI readiness marker after the client route hydrates and updating the Cockpit smoke test to wait for that marker instead of relying on network-idle behavior.

## Scope

- Added `data-testid="operations-ready"` and `data-operations-ready="true"` to the hydrated Operations route content.
- Updated the Operations smoke test to assert the route URL and readiness marker.
- Preserved Operations polling, SSE job streaming, action execution, backend routes, runtime configuration, memory, extraction, and financial-truth surfaces.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/operations_route_readiness_contract_v1_20260526.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/operations_route_readiness_contract_v1_20260526.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/operations_route_readiness_contract_v1_20260526.md`
- `corepack pnpm --dir cockpit-ui install --frozen-lockfile`
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/operations/operations-screen.tsx tests/smoke.spec.ts`
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit`
- `corepack pnpm --dir cockpit-ui build`
- `COCKPIT_E2E_BASE_URL=http://127.0.0.1:3111 corepack pnpm --dir cockpit-ui exec playwright test tests/smoke.spec.ts --project=chromium -g "should navigate to Operations page"`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/operations_route_readiness_contract_v1_20260526.md`

## Evidence

- Screenshot: `reports/agent_jobs/operations_route_readiness_contract_v1_20260526/operations-ready.png`
- Diff gate: `reports/agent_jobs/operations_route_readiness_contract_v1_20260526/diff-check.json`
