# Cockpit Action-Control Route Guard Audit

Generated: 2026-06-02T02:05:30+10:00

## Executive Result

This audit found no evidence that the broader Cockpit action-control routes have
server-side API-key or explicit control-intent dependencies. The backend
Cockpit router is included at `/api/cockpit` without router-level dependencies,
and the audited mutation-capable action routes do not declare route-local
`Depends(require_api_key)` or `X-Cockpit-Control-Intent` checks.

The BFF routes mostly copy incoming request headers through to the backend. That
is useful only if the backend enforces a guard. It is not itself a server-side
guard.

No implementation was attempted because these routes are high-risk control
surfaces and include contested backend and frontend files.

## Confirmed

- `financial-engine_v2/backend/app/routes/cockpit_api.py:114` creates the
  Cockpit API router with `APIRouter()` and no router-level dependency.
- `financial-engine_v2/backend/app/main.py:113-114` mounts the Cockpit API
  router at `/api/cockpit` without additional dependencies.
- `POST /api/cockpit/action/execute` can execute strategy-memory actions,
  chart actions, subprocess actions, or queued jobs.
- `POST /api/cockpit/action/jobs/{job_id}/stop` can set cancellation events,
  terminate registered subprocesses, kill them on timeout, and request pipeline
  cancellation.
- `POST /api/cockpit/marketplace/scans`,
  `POST /api/cockpit/marketplace/price-intelligence/calibrate`, and
  `POST /api/cockpit/marketplace/price-intelligence/tracked-products/{id}/ebay-sync`
  queue long-running marketplace jobs.
- Existing focused backend tests exercise happy-path execution and stop behavior
  without API-key setup or missing/wrong-key negative-path assertions.

## Route Classification

See `route_guard_matrix.json` for line-level route evidence. The important
classification is:

- `guarded`: none of the audited mutation-capable action/control routes.
- `unguarded_mutation`: action execute, job stop, marketplace scan launch,
  benchmark refresh, calibration launch, eBay sync launch, mission/match state
  mutations.
- `read_only_or_status`: action job GET, marketplace scan GET, marketplace
  health/list/read routes.
- `proxy_header_passthrough_only`: BFF routes that forward headers but do not
  establish their own guard.

## Recommended Safe Extension

Open a separate implementation task for the narrow backend guard fix. It should:

- add route-specific server-side guard dependencies to mutation-capable
  action/control routes;
- preserve read-only route access rules deliberately rather than by accident;
- add negative-path tests proving rejected requests do not run actions, stop
  jobs, launch marketplace scans, run benchmark refresh, calibration, or eBay
  sync;
- avoid broad auth redesign and avoid frontend-only confirmation as the trust
  boundary.

Suggested first implementation slice:

1. Guard `POST /api/cockpit/action/execute`.
2. Guard `POST /api/cockpit/action/jobs/{job_id}/stop`.
3. Guard marketplace job launch routes.
4. Leave read-only status/list routes as a separate decision.

## Hard Stops Preserved

- No live action route was called.
- No action, scan, calibration, eBay sync, benchmark refresh, job stop,
  runtime restart, DB/Qdrant/news/memory/canonical financial truth mutation, or
  service configuration change was performed.
- No contested backend or frontend product file was edited.
