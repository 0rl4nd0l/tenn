# Backend Restart Route Guard Security Audit

Generated: 2026-05-27T14:30:25+10:00

## Summary

Issue #55 is classified `ROOT_CAUSE_FIXED` for the direct Cockpit backend
restart route. The route now rejects unsafe requests before any filesystem or
process-control work is attempted.

The fix is intentionally route-local:

- `POST /api/cockpit/restart` now requires loopback access by default.
- Cross-origin and browser `Sec-Fetch-Site: cross-site` requests are denied.
- JSON content type is required.
- An explicit restart intent header is required.
- A JSON body with exact restart intent and confirmation is required.
- Remote restart is denied unless `COCKPIT_RESTART_ALLOW_REMOTE=1` and
  `X-Cockpit-Restart-Token` matches `COCKPIT_RESTART_TOKEN`.

Broader Cockpit action-control route auth parity remains outside #55 and is now
tracked by follow-up #121.

## Changed Files

- `docs/agent_tasks/backend_restart_route_guard_security_audit_v1_20260527.md`
- `cockpit-ui/app/api/cockpit/restart/route.ts`
- `cockpit-ui/lib/api-client.ts`
- `cockpit-ui/lib/restart-route-guard.test.ts`
- `reports/agent_jobs/backend_restart_route_guard_security_audit_v1_20260527/**`

No backend service was started, stopped, restarted, reloaded, or called through
the live restart endpoint.

## Issue Readback

- #55 was open, labelled `lane:runtime`, `lane:reporting`, `mode:audit`,
  `priority:p1`, `risk:high`, `state:ready`, `type:security`, and
  `type:control-plane`, milestone M6.
- #51 remains open and adjacent. It covers one-click high-impact UI
  confirmation/review state, not server-side restart-route auth.
- #121 was created as the follow-up for broader Cockpit action-control route
  server-side auth guard parity.

## Implementation

`cockpit-ui/app/api/cockpit/restart/route.ts` now validates the request before:

- `access(restartScript)`
- `pgrep -f "uvicorn app.main:app"`
- `kill <pid>`
- `spawn("bash", [restartScript])`

The existing `restartBackend()` helper now sends:

- `X-Cockpit-Restart-Intent: restart-backend`
- body `{ "intent": "restart-backend", "confirmation": "RESTART BACKEND" }`

Existing callers in Operations and chat slash-command paths continue to use the
same helper, so they inherit the route contract.

## Validation

Passed:

- `corepack pnpm --dir cockpit-ui exec vitest run lib/restart-route-guard.test.ts`
- `corepack pnpm --dir cockpit-ui exec vitest run lib/restart-route-guard.test.ts lib/api-client.test.ts`
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false`
- `git diff --check`

The focused route tests mock `access`, `execFile`, `spawn`, and `fetch`. They
prove rejected requests do not call filesystem or process-control functions.

One initial command, `corepack pnpm --dir cockpit-ui test --
lib/restart-route-guard.test.ts`, was not treated as final validation because
the package script expanded into the broader configured suite. It also exposed
an initial CJS mock issue in the new test, which was fixed before the focused
tests passed. The broader run included unrelated existing Home/Marketplace test
failures and is recorded in `validation.json`.

## Resolution Review

Verdict: `PASS_CLOSEOUT`

- Root cause: fixed for the direct restart route identified by #55.
- Regression risk: bounded to one route and one client helper.
- Security boundary: improved; no auth behavior was weakened.
- Runtime boundary: preserved; no live restart occurred.
- Backlog integrity: broader Cockpit action-control route auth risk is tracked
  by #121.

## DATA_MISSING

- Current live listener binding was not re-probed because this task forbids live
  runtime mutation and does not require starting services.
- GitHub Projects fields were not inspected or mutated.
- Broader Cockpit action-control route remediation is not included in #55; it is
  tracked by #121.

## Closeout Plan

After this implementation/report bundle is committed, #55 should receive a
closeout comment with branch, commit, changed files, validation, #121 follow-up,
and then close as `state:done-remediated`.
