---
job_id: cockpit_telemetry_route_access_guard_v1_20260602
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_telemetry_route_access_guard_v1_20260602.md
  - cockpit-ui/app/api/cockpit/metrics/host/route.ts
  - cockpit-ui/app/api/cockpit/metrics/gpu/route.ts
  - cockpit-ui/app/api/cockpit/health/route.ts
  - cockpit-ui/lib/cockpit-bff-auth.ts
  - cockpit-ui/lib/cockpit-api-headers.ts
  - cockpit-ui/lib/cockpit-api-headers.test.ts
  - cockpit-ui/lib/telemetry-route-access-guard.test.ts
  - cockpit-ui/lib/api-client.ts
  - cockpit-ui/components/cockpit/gpu-activity-dialog.tsx
  - cockpit-ui/components/cockpit/host-activity-dialog.tsx
  - reports/agent_jobs/cockpit_telemetry_route_access_guard_v1_20260602/README.md
  - reports/agent_jobs/cockpit_telemetry_route_access_guard_v1_20260602/status.json
  - reports/agent_jobs/cockpit_telemetry_route_access_guard_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_telemetry_route_access_guard_v1_20260602/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_telemetry_route_access_guard_v1_20260602
mutation_mode: safe_extension
production_data_access: false
---

# Task

Gate Cockpit host/GPU telemetry BFF routes before exposing local machine state.

# Context

GitHub issue #223 reports that Cockpit telemetry BFF routes expose host, GPU, process, hostname, platform, and health state without checking an operator credential. This task is stacked on PR #264 because #264 redacts process command secrets in the same telemetry routes and is itself stacked on PR #178's GPU display changes.

# Requirements

1. Validate this task card before implementation.
2. Inspect the shared active-job registry and open PR overlap before edits.
3. Claim this task if no unresolved overlap remains.
4. Require a Cockpit API-key/operator credential before running local host/GPU probes in `/api/cockpit/metrics/host`.
5. Require a Cockpit API-key/operator credential before running local host/GPU probes in `/api/cockpit/metrics/gpu`.
6. Gate `/api/cockpit/health` before backend health reads or local host/GPU probes.
7. Preserve authenticated Cockpit UI health, host, and GPU diagnostic fetches by sending the configured browser API key.
8. Keep #218 process-command redaction intact; do not treat auth as a substitute for redaction.
9. Do not run live telemetry probes beyond mocked/focused tests.
10. Do not change backend query orchestration, extraction, memory, Qdrant, parser code, runtime/GPU/service configuration, or financial truth.

# Validation

Run focused Cockpit UI tests for telemetry route access guard and browser API-key header helper, then targeted ESLint and TypeScript for touched files.

# Required Output

Write a short report to `reports/agent_jobs/cockpit_telemetry_route_access_guard_v1_20260602/README.md` with:

- patch summary
- issue and PR/registry overlap evidence
- validation commands and results
- files intentionally not touched
- remaining blockers or follow-up work
