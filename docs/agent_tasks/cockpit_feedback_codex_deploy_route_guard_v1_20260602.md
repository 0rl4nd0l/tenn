---
job_id: cockpit_feedback_codex_deploy_route_guard_v1_20260602
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_feedback_codex_deploy_route_guard_v1_20260602.md
  - cockpit-ui/app/api/cockpit/feedback/flags/[reportId]/deploy/route.ts
  - cockpit-ui/app/cockpit-local/feedback/flags/[reportId]/deploy/route.ts
  - cockpit-ui/lib/codex-investigation-route.test.ts
  - cockpit-ui/components/cockpit/chat/chat-screen.tsx
  - reports/agent_jobs/cockpit_feedback_codex_deploy_route_guard_v1_20260602/README.md
  - reports/agent_jobs/cockpit_feedback_codex_deploy_route_guard_v1_20260602/status.json
  - reports/agent_jobs/cockpit_feedback_codex_deploy_route_guard_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_feedback_codex_deploy_route_guard_v1_20260602/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_feedback_codex_deploy_route_guard_v1_20260602
mutation_mode: safe_extension
production_data_access: false
---

# Task

Gate the Cockpit Codex flagged-report deploy route before spawning the local investigator.

# Context

GitHub issue #215 reports that `POST /api/cockpit/feedback/flags/{reportId}/deploy` and its `/cockpit-local/.../deploy` alias can launch `scripts/cockpit_flag_investigator.py --once --apply` from a plain POST. PR #248 covers read-only investigation status access and is the stack base for this task; this task covers the deploy/spawn side effect only.

# Requirements

1. Validate this task card before implementation.
2. Inspect the shared active-job registry and open PR overlap before edits.
3. Claim this task if no unresolved overlap remains.
4. Reject missing or wrong deploy intent before validating report ids, resolving local report paths, refreshing backend flag packets, writing launcher state, or calling `spawn`.
5. Preserve successful queued/failed/completed/running report behavior after explicit authorization.
6. Keep `/cockpit-local/.../deploy` behavior aligned through the existing re-export.
7. Preserve the current Cockpit chat deploy flow by adding only the matching deploy-intent header.
8. Prove rejected requests do not call `spawn` and therefore do not pass `--apply`.
9. Do not run live deploy, live Codex investigator, or live flagged-report repair.
10. Do not change backend query orchestration, extraction, memory, Qdrant, parser code, runtime/GPU config, or financial truth.

# Validation

Run focused Cockpit UI tests for `cockpit-ui/lib/codex-investigation-route.test.ts`.

# Required Output

Write a short report to `reports/agent_jobs/cockpit_feedback_codex_deploy_route_guard_v1_20260602/README.md` with:

- patch summary
- issue and PR/registry overlap evidence
- validation commands and results
- files intentionally not touched
- remaining blockers or follow-up work
