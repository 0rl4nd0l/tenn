---
job_id: cockpit_telemetry_command_redaction_v1_20260602
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_telemetry_command_redaction_v1_20260602.md
  - cockpit-ui/app/api/cockpit/metrics/gpu/route.ts
  - cockpit-ui/app/api/cockpit/metrics/host/route.ts
  - cockpit-ui/app/api/cockpit/health/route.ts
  - cockpit-ui/lib/process-command-redaction.ts
  - cockpit-ui/lib/process-command-redaction.test.ts
  - reports/agent_jobs/cockpit_telemetry_command_redaction_v1_20260602/README.md
  - reports/agent_jobs/cockpit_telemetry_command_redaction_v1_20260602/status.json
  - reports/agent_jobs/cockpit_telemetry_command_redaction_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_telemetry_command_redaction_v1_20260602/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_telemetry_command_redaction_v1_20260602
mutation_mode: safe_extension
production_data_access: false
---

# Task

Redact process-command secrets from Cockpit telemetry BFF payloads.

# Context

GitHub issue #218 reports that the Cockpit GPU metrics, host metrics, and aggregated health BFF routes return raw process command lines to the browser. Those command lines can include secret-bearing flags or environment assignments such as API keys and tokens. This task is stacked on PR #178 because that PR already touches `cockpit-ui/app/api/cockpit/metrics/gpu/route.ts` and `cockpit-ui/app/api/cockpit/health/route.ts`.

# Requirements

1. Validate this task card before implementation.
2. Inspect the shared active-job registry and open PR overlap before edits.
3. Claim this task if no unresolved overlap remains.
4. Add a shared process-command redaction helper for Cockpit telemetry.
5. Redact spaced and equals-form secret-bearing CLI flags before returning telemetry JSON.
6. Redact secret-bearing environment assignments before returning telemetry JSON.
7. Apply redaction in `/api/cockpit/metrics/gpu`, `/api/cockpit/metrics/host`, and `/api/cockpit/health`.
8. Preserve useful non-secret process labels, PIDs, command names, task labels, and resource metrics.
9. Do not weaken or replace the separate route access-gate follow-up tracked by #223.
10. Do not run live process probes beyond focused tests; do not change runtime/model/GPU/service configuration.
11. Do not change backend query orchestration, extraction, memory, Qdrant, parser code, or financial truth.

# Validation

Run focused Cockpit UI tests for the process-command redaction helper and, where practical, targeted route-level tests or lint/TypeScript over touched files.

# Required Output

Write a short report to `reports/agent_jobs/cockpit_telemetry_command_redaction_v1_20260602/README.md` with:

- patch summary
- issue and PR/registry overlap evidence
- validation commands and results
- files intentionally not touched
- remaining blockers or follow-up work
