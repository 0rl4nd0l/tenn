---
job_id: cockpit_gpu_activity_process_visibility_v1_20260601
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_gpu_activity_process_visibility_v1_20260601.md
  - cockpit-ui/components/cockpit/gpu-activity-dialog.tsx
  - cockpit-ui/components/cockpit/gpu-activity-dialog.test.tsx
  - cockpit-ui/components/cockpit/cockpit-sidebar.tsx
  - cockpit-ui/components/cockpit/cockpit-sidebar.test.tsx
  - reports/agent_jobs/cockpit_gpu_activity_process_visibility_v1_20260601/README.md
  - reports/agent_jobs/cockpit_gpu_activity_process_visibility_v1_20260601/status.json
  - reports/agent_jobs/cockpit_gpu_activity_process_visibility_v1_20260601/validation.json
  - reports/agent_jobs/cockpit_gpu_activity_process_visibility_v1_20260601/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_gpu_activity_process_visibility_v1_20260601
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit GPU Activity Process Visibility

## Issue

Refs #90.

Cockpit GPU Activity can show "No active GPU compute processes reported" when the GPU telemetry probe has failed. In that state, empty GPU/process arrays are not proof that the local GPU or llama-server is idle.

## Scope

This job is a Reporting-layer UI safe extension only. It changes Cockpit copy and focused tests so telemetry failure is visibly distinct from an idle GPU process list.

## Contract Boundaries

- Backend remains the source of truth for GPU telemetry.
- Cockpit only renders the backend-provided health/error state.
- No runtime, GPU, model, service, DB, Qdrant, memory, extraction, parser, prompt, or gold-label behavior changes.
- No llama-server process is started, stopped, restarted, or required for validation.

## Acceptance Criteria

- When GPU telemetry has an error and no process rows, the dialog does not claim there are no active GPU compute processes.
- Sidebar process copy also distinguishes unavailable process telemetry from a confirmed idle state.
- Existing process-count copy remains unchanged when backend telemetry reports processes.
- Focused regression tests cover degraded telemetry and normal process count paths.

## Validation Plan

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_gpu_activity_process_visibility_v1_20260601.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_gpu_activity_process_visibility_v1_20260601.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_gpu_activity_process_visibility_v1_20260601.md`
- `corepack pnpm --dir cockpit-ui exec vitest run components/cockpit/gpu-activity-dialog.test.tsx components/cockpit/cockpit-sidebar.test.tsx`
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/gpu-activity-dialog.tsx components/cockpit/gpu-activity-dialog.test.tsx components/cockpit/cockpit-sidebar.tsx components/cockpit/cockpit-sidebar.test.tsx`
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_gpu_activity_process_visibility_v1_20260601.md`
- `python3 scripts/agent_job_registry.py release cockpit_gpu_activity_process_visibility_v1_20260601`
