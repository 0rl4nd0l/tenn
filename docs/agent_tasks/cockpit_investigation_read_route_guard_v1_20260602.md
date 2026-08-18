---
job_id: cockpit_investigation_read_route_guard_v1_20260602
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_investigation_read_route_guard_v1_20260602.md
  - cockpit-ui/app/api/cockpit/feedback/flags/[reportId]/investigation/route.ts
  - cockpit-ui/lib/codex-investigation-route.test.ts
  - cockpit-ui/components/cockpit/chat/chat-screen.tsx
  - reports/agent_jobs/cockpit_investigation_read_route_guard_v1_20260602/README.md
  - reports/agent_jobs/cockpit_investigation_read_route_guard_v1_20260602/status.json
  - reports/agent_jobs/cockpit_investigation_read_route_guard_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_investigation_read_route_guard_v1_20260602/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_investigation_read_route_guard_v1_20260602
mutation_mode: safe_extension
production_data_access: false
---

# Task

Gate the Cockpit Codex investigation read route before exposing local investigation paths and output tails.

# Context

GitHub issue #222 reports that `GET /api/cockpit/feedback/flags/{reportId}/investigation` and its `/cockpit-local/...` alias can return local investigation paths plus Codex output/stderr/launcher tails without a server-side operator/control-intent guard. UI hiding and deploy gating are adjacent work and must remain separate.

# Requirements

1. Validate this task card before implementation.
2. Inspect the shared active-job registry and open PR overlap before edits.
3. Claim this task if no unresolved overlap remains.
4. Reject missing or wrong read intent before resolving report paths or reading local investigation/log artifacts.
5. Preserve the accepted response shape for authorized reads.
6. Keep `/cockpit-local/.../investigation` behavior aligned through the existing re-export.
7. Preserve the current Cockpit chat polling flow by adding only the matching read-intent header.
8. Do not change deploy/spawn behavior, backend query orchestration, extraction, memory, Qdrant, parser code, runtime/GPU config, or financial truth.

# Validation

Run focused Cockpit UI tests for `cockpit-ui/lib/codex-investigation-route.test.ts`.

# Required Output

Write a short report to `reports/agent_jobs/cockpit_investigation_read_route_guard_v1_20260602/README.md` with:

- patch summary
- issue and PR/registry overlap evidence
- validation commands and results
- files intentionally not touched
- remaining blockers or follow-up work
