## Tenn Issue Contract Normalization

Task: `cockpit_restart_route_guard_audit_v1_20260526`

Classification: normalized in place as a high-risk security/control-plane audit.

## Lane

Primary lane: Runtime
Supporting lanes: Reporting, Repo Hygiene
Mode: audit_first

## GitHub Tracking

Recommended labels applied by #106 normalization: `lane:runtime`, `lane:reporting`, `mode:audit`, `priority:p1`, `risk:high`, `state:ready`, `type:security`, `type:control-plane`

Milestone: M6 - Runtime / Local Automation

## Source Evidence

Original static audit evidence:

- `cockpit-ui/app/api/cockpit/restart/route.ts:82-119` exports `POST()` and performs restart work without a route-local authorization or CSRF-style guard.
- `cockpit-ui/app/api/cockpit/restart/route.ts:49-65` finds and kills `uvicorn app.main:app`.
- `cockpit-ui/app/api/cockpit/restart/route.ts:68-79` launches `financial-engine_v2/scripts/run_local_backend.sh` detached.
- `cockpit-ui/components/cockpit/operations/operations-screen.tsx:163-185` calls `restartBackend()` from the UI.
- The audited frontend was listening on `0.0.0.0:3000`.

The original audit did not POST to the endpoint because that would mutate live runtime state.

## Why This Matters

Any browser or script that can reach the Cockpit frontend port may be able to
attempt a backend restart. This is distinct from a UI confirmation problem:
server-side authorization must reject unsafe requests before touching processes.

## Required Task Card

`docs/agent_tasks/cockpit_restart_route_guard_audit_v1_20260526.md`

## Required Report Path

`reports/agent_jobs/cockpit_restart_route_guard_audit_v1_20260526/`

## Allowed Files / Surfaces

- Task card and report artifacts.
- Read-only inspection of restart route and Operations UI call sites.
- No-mutation route tests or static tests that prove unauthorized POSTs are rejected, only in a later task card.
- Focused route/UI files only in a later safe-extension task after registry overlap is clear.

## Forbidden Files / Surfaces

- Live backend restart during audit.
- Runtime/model/GPU/service config changes.
- DB, Qdrant, news, or memory mutation.
- Canonical financial truth mutation.
- Parser routing, extraction prompts, or gold labels.
- Broad operations redesign or unrelated high-impact action cleanup.
- Treating UI confirmation alone as a server-side auth fix.

## Validation

- Confirm current restart route behavior from code without calling the live endpoint.
- Verify whether the frontend remains LAN-bound in the current runtime.
- Duplicate-check against #51 and other restart/auth issues.
- Later remediation must prove unauthorized POST returns `403` and does not kill the backend.
- Later remediation must prove authorized restart still works and logs operator intent.

## Hard Stops

- Any validation would restart or kill the live backend.
- A proposed fix relies only on client-side confirmation.
- Current route state cannot be verified from code or safe tests.
- Required mutation touches service config or runtime launch behavior without a separate task card.

## Definition of Done

- The current risk is verified or marked `DATA_MISSING`.
- Any implementation task has exact route/test files, an auth/CSRF guard contract, and no live restart requirement for negative-path validation.
- #51 remains linked as adjacent UI-confirmation coverage, not an exact duplicate.
- No forbidden surfaces are changed.

## DATA_MISSING

- Current live listener binding proof for the active Cockpit frontend.
- Current restart route behavior at active HEAD after any recent Cockpit changes.
- Whether an operator token or nonce mechanism already exists elsewhere in the app.

## Follow-Up / Parking / Dependencies

- Adjacent but not duplicate: #51 covers one-click high-impact actions and UI confirmation.
- This issue covers server-side restart route guard/auth behavior.
