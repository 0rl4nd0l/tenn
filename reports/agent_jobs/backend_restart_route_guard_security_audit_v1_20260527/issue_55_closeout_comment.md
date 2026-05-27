Implemented and validated the direct backend restart route guard.

Branch: `migration/clean-runtime-baseline-reconstruct-v1`
Commit: `49c6e98e` (`fix(cockpit): guard backend restart route`)

Changed files:
- `cockpit-ui/app/api/cockpit/restart/route.ts`
- `cockpit-ui/lib/api-client.ts`
- `cockpit-ui/lib/restart-route-guard.test.ts`
- `docs/agent_tasks/backend_restart_route_guard_security_audit_v1_20260527.md`
- `reports/agent_jobs/backend_restart_route_guard_security_audit_v1_20260527/**`

Root-cause verdict: `ROOT_CAUSE_FIXED_FOR_DIRECT_RESTART_ROUTE`.

What changed:
- `POST /api/cockpit/restart` now rejects unsafe requests before `access`, `pgrep`, `kill`, `spawn`, or backend health polling.
- Default restart access is loopback-only.
- Cross-origin and `Sec-Fetch-Site: cross-site` requests are denied.
- Requests must be JSON and include `X-Cockpit-Restart-Intent: restart-backend`.
- Request body must include `{ "intent": "restart-backend", "confirmation": "RESTART BACKEND" }`.
- Remote restart remains denied by default and requires explicit env opt-in plus `X-Cockpit-Restart-Token`.
- Existing client helper now sends the explicit restart intent contract.

Validation:
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/backend_restart_route_guard_security_audit_v1_20260527.md` PASS
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/backend_restart_route_guard_security_audit_v1_20260527.md` PASS
- `corepack pnpm --dir cockpit-ui exec vitest run lib/restart-route-guard.test.ts` PASS, 5 tests
- `corepack pnpm --dir cockpit-ui exec vitest run lib/restart-route-guard.test.ts lib/api-client.test.ts` PASS, 7 tests
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false` PASS
- `jq empty reports/agent_jobs/backend_restart_route_guard_security_audit_v1_20260527/*.json` PASS
- `git diff --check` PASS

Runtime safety:
- No service start, stop, restart, reload, or endpoint POST was performed.
- Route tests mock process operations and prove rejected requests do not reach process-control calls.

DATA_MISSING:
- Current live listener binding was not re-probed because live runtime mutation was forbidden.
- GitHub Projects fields were not inspected or mutated.
- Broader Cockpit action-control route auth parity is outside this issue and is tracked in #121.

Closing #55 as `state:done-remediated` for the direct restart route. #51 remains the adjacent UI confirmation/review-state issue.
