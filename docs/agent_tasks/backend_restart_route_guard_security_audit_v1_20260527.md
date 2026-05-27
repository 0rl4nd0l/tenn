---
job_id: backend_restart_route_guard_security_audit_v1_20260527
lane: Reporting
requested_primary_lane: Runtime
supporting_lanes:
  - Reporting
  - Repo Hygiene
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/backend_restart_route_guard_security_audit_v1_20260527.md
  - reports/agent_jobs/backend_restart_route_guard_security_audit_v1_20260527/README.md
  - reports/agent_jobs/backend_restart_route_guard_security_audit_v1_20260527/status.json
  - reports/agent_jobs/backend_restart_route_guard_security_audit_v1_20260527/control_surface_inventory.md
  - reports/agent_jobs/backend_restart_route_guard_security_audit_v1_20260527/control_surface_inventory.json
  - reports/agent_jobs/backend_restart_route_guard_security_audit_v1_20260527/route_guard_decision.json
  - reports/agent_jobs/backend_restart_route_guard_security_audit_v1_20260527/follow_up_issue_body.md
  - reports/agent_jobs/backend_restart_route_guard_security_audit_v1_20260527/follow_up_issue_readback.json
  - reports/agent_jobs/backend_restart_route_guard_security_audit_v1_20260527/github_readback.json
  - reports/agent_jobs/backend_restart_route_guard_security_audit_v1_20260527/validation.json
  - reports/agent_jobs/backend_restart_route_guard_security_audit_v1_20260527/diff-check.json
  - reports/agent_jobs/backend_restart_route_guard_security_audit_v1_20260527/issue_55_closeout_comment.md
  - cockpit-ui/app/api/cockpit/restart/route.ts
  - cockpit-ui/lib/api-client.ts
  - cockpit-ui/lib/restart-route-guard.test.ts
allowed_repo_files:
  - docs/agent_tasks/backend_restart_route_guard_security_audit_v1_20260527.md
  - reports/agent_jobs/backend_restart_route_guard_security_audit_v1_20260527/**
  - cockpit-ui/app/api/cockpit/restart/route.ts
  - cockpit-ui/lib/api-client.ts
  - cockpit-ui/lib/restart-route-guard.test.ts
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 10800
output_dir: reports/agent_jobs/backend_restart_route_guard_security_audit_v1_20260527
mutation_mode: safe_extension
requested_mutation_mode: audit_first_route_guard_safe_extension
production_data_access: false
allowed_github_mutation:
  - "read issue #55 and adjacent issue #51"
  - "comment on issue #55 only after audit report and validation artifacts exist"
  - "close issue #55 only if route guard root cause is fixed and validation proves the negative path does not trigger restart work"
  - "update issue #55 labels only for closeout state if it closes"
  - "create one follow-up issue only if the audit finds broader Cockpit control-route auth risk with no duplicate tracker"
---

# Backend Restart Route Guard Security Audit

Mode detail: audit-first / safe-extension.

## Objective

Audit the backend restart route and adjacent control surfaces, then implement
only the smallest additive guardrail if the route ownership and testable blast
radius are clear. Prevent unsafe backend restart/control actions from being
exposed without explicit route-local guard and intent boundaries.

## Target Issue

- #55 `Cockpit backend restart route has no local auth or CSRF guard while frontend is LAN-bound`
- Adjacent: #51 one-click high-impact action confirmation/review state.

## Audit Finding Before Implementation

The exact route-local execution path is:

- `cockpit-ui/app/api/cockpit/restart/route.ts`
- client helper `cockpit-ui/lib/api-client.ts::restartBackend`
- Operations UI caller `cockpit-ui/components/cockpit/operations/operations-screen.tsx`
- chat slash command caller `cockpit-ui/components/cockpit/chat/chat-screen.tsx`

The route kills `uvicorn app.main:app` and launches
`financial-engine_v2/scripts/run_local_backend.sh`. The current issue is not
covered by #51 because #51 is client-side confirmation/review coverage; #55 is
server-side route guard coverage.

## Safe Extension Scope

Add a route-local guard that rejects unsafe restart requests before filesystem
checks or process operations:

- deny cross-origin requests when `Origin` is present and does not match the
  request origin;
- deny browser `Sec-Fetch-Site: cross-site` requests;
- deny non-loopback host access by default;
- allow remote restart only when explicitly opted in by environment and a
  server-side restart token header matches;
- require JSON content type;
- require an explicit restart intent header and body confirmation.

Update the existing client helper to send the required explicit intent header
and JSON confirmation body. Add focused Vitest route tests that mock all process
operations and prove rejected requests do not call `access`, `pgrep`, `kill`, or
`spawn`.

## Allowed Scope

- Read-only inspection of current GitHub issues, repo routes, frontend callers,
  backend control routes, scripts, and tests.
- Write this task card and the declared report bundle.
- Edit only `cockpit-ui/app/api/cockpit/restart/route.ts`.
- Edit only `cockpit-ui/lib/api-client.ts`.
- Add only `cockpit-ui/lib/restart-route-guard.test.ts`.
- Comment and close #55 only if validation proves the restart guard risk is
  addressed for this route.
- Create one follow-up issue only if the audit identifies broader Cockpit
  control-route auth risk that is outside #55 and not already tracked.

## Forbidden

- Live service start, stop, restart, reload, or endpoint POST.
- DB, Qdrant, news, memory, or canonical financial truth mutation.
- Parser routing, extraction prompt, gold label, model/runtime/GPU/service
  config changes.
- Broad auth rewrite or route refactor.
- Frontend action expansion.
- Unrelated dirty-work cleanup.
- Branch cleanup, merge, rebase, reset, stash, prune, or delete.
- Pull request mutation.
- Closing #51 or broad high-impact-action issues.

## Validation

- Print branch, HEAD, status, remote, and worktree.
- Registry `list-active --read-only`.
- Read #55 and #51.
- Search restart/control routes, scripts, auth/guard code, and tests.
- Classify restart/control surfaces as guarded, unguarded, unreachable, or
  `DATA_MISSING`.
- Run focused Vitest tests for the restart route guard.
- Run relevant client/route tests if needed.
- Static grep/readback proving the restart path has route-local guard checks.
- JSON validation for report artifacts.
- Task-card validate/check-diff.
- `git diff --check`.
- Final registry `list-active --read-only`.
- Final git status.
- GitHub readback if #55 is commented or closed.

## Hard Stops

- Any validation would restart or kill the live backend.
- The route ownership cannot be established.
- The proposed fix relies only on UI confirmation.
- Tests cannot prove rejected requests avoid process operations.
- The safe-extension patch touches service config, runtime launch behavior, or
  unrelated action surfaces.
- Active registry overlap creates unresolved high collision risk.

## Definition of Done

- Restart route/control-surface inventory is recorded.
- The restart route rejects unauthorized or cross-site requests before touching
  process-control code.
- Existing callers send the explicit restart intent contract.
- Focused tests prove rejection and authorized loopback behavior without live
  runtime mutation.
- #55 is either closed with evidence or left open with blockers and follow-up
  links.

## DATA_MISSING

- Current live listener binding was not re-probed because this task forbids
  live runtime mutation and does not require a server start.
- Broader backend Cockpit control routes are inventoried, but broad backend API
  auth remediation is outside this issue's safe-extension scope.
