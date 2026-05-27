## Summary

Audit and, if safe, normalize server-side guard/auth behavior for broader
Cockpit action-control routes beyond the now-guarded restart route from #55.

## Lane

Primary lane: Runtime
Supporting lanes: Reporting, Repo Hygiene
Mode: audit_first

## Priority / Risk / Type / State

- Priority: P1
- Risk: High
- Type: security, control-plane
- State: ready

## Source Evidence

Found during #55 restart-route guard audit:

- `cockpit-ui/app/api/cockpit/action/execute/route.ts` proxies `POST /api/cockpit/action/execute` to the backend and copies request headers.
- `financial-engine_v2/backend/app/routes/cockpit_api.py` exposes `POST /api/cockpit/action/execute`.
- `financial-engine_v2/backend/app/routes/cockpit_api.py` exposes `POST /api/cockpit/action/jobs/{job_id}/stop`.
- `financial-engine_v2/backend/app/routes/cockpit_api.py` exposes long-running action launch routes such as marketplace scan/calibration/sync.
- These routes are adjacent to #51 high-impact UI confirmation coverage, but #51 does not prove server-side auth/CSRF guard parity.

## Why This Matters

The #55 fix guards the direct backend restart route before it can touch
filesystem or process-control code. Broader Cockpit action-control routes can
still launch or stop expensive/high-impact operations, so they need their own
server-side guard/auth audit rather than relying on UI confirmation alone.

## Required Task Card Path

`docs/agent_tasks/cockpit_action_control_route_guard_audit_v1_20260527.md`

## Required Report Path

`reports/agent_jobs/cockpit_action_control_route_guard_audit_v1_20260527/`

## Allowed Files / Surfaces

- Task card and report artifacts.
- Read-only audit of Cockpit BFF action routes, backend Cockpit action routes,
  action registry preview/execute paths, and existing tests.
- Minimal route/guard/test files only if the audit proves exact safe-extension
  scope and updates the task card allowlist before edits.

## Forbidden Files / Surfaces

- Live service start/stop/restart/reload.
- Live action execution against backend/Cockpit routes.
- DB, Qdrant, news, memory, or canonical financial truth mutation.
- Parser routing, extraction prompts, gold labels, model/runtime/GPU/service
  config changes.
- Broad auth rewrite or broad route refactor.
- Frontend action expansion.
- Branch cleanup, merge, rebase, reset, stash, prune, or delete.

## Validation

- Inventory every Cockpit action/control route exposed through BFF and backend.
- Classify each route as guarded, unguarded, unreachable, or `DATA_MISSING`.
- Identify who can call each route locally/remotely.
- Identify confirmation/intent/auth checks and tests per route.
- If implementation occurs, add focused negative-path tests proving rejected
  requests do not execute actions or terminate jobs.
- Task-card validate/check-diff.
- JSON report parse.
- `git diff --check`.
- Final registry read-only check.

## Hard Stops

- Any validation would execute, stop, restart, or mutate live runtime state.
- The proposed remediation relies only on UI confirmation.
- Route ownership or blast radius cannot be established.
- Fix scope expands into broad auth redesign without a separate task card.

## Definition of Done

- The broader action-control route auth/guard state is classified with evidence.
- Any unsafe route has either a validated minimal guardrail or a visible
  follow-up/blocker.
- #51 remains linked as adjacent UI-confirmation coverage.
- #55 remains the completed direct restart-route guard fix and is not reopened.

## DATA_MISSING

- Current live backend listener exposure was not probed during #55 because live
  runtime mutation was forbidden.
- Whether the broader backend Cockpit router should use one common auth
  dependency or route-specific intent guards remains design work for this
  follow-up.

## Follow-Up / Parking / Dependencies

- Follows #55 direct restart-route guard remediation.
- Adjacent to #51 one-click high-impact UI confirmation/review-state coverage.
