# Cockpit GPU Activity Process Visibility

## Summary

Refs #90.

This safe-extension slice keeps Cockpit GPU Activity from presenting failed GPU/process telemetry as a confirmed idle GPU state. When the backend GPU probe reports an error and returns empty arrays, the sidebar and dialog now render a telemetry-unavailable state instead of "No active GPU compute processes".

## Boundaries

- Frontend Reporting/UI only.
- No backend route changes.
- No runtime, model, GPU, service, DB, Qdrant, news, memory, extraction, parser, prompt, gold-label, or financial-truth changes.
- No llama-server process was started, stopped, restarted, or required.

## Files

- `cockpit-ui/components/cockpit/gpu-activity-dialog.tsx`
- `cockpit-ui/components/cockpit/gpu-activity-dialog.test.tsx`
- `cockpit-ui/components/cockpit/cockpit-sidebar.tsx`
- `cockpit-ui/components/cockpit/cockpit-sidebar.test.tsx`
- `docs/agent_tasks/cockpit_gpu_activity_process_visibility_v1_20260601.md`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_gpu_activity_process_visibility_v1_20260601.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_gpu_activity_process_visibility_v1_20260601.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_gpu_activity_process_visibility_v1_20260601.md`
- `corepack pnpm --dir cockpit-ui install --frozen-lockfile`
- `corepack pnpm --dir cockpit-ui exec vitest run components/cockpit/gpu-activity-dialog.test.tsx components/cockpit/cockpit-sidebar.test.tsx`
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/gpu-activity-dialog.tsx components/cockpit/gpu-activity-dialog.test.tsx components/cockpit/cockpit-sidebar.tsx components/cockpit/cockpit-sidebar.test.tsx`
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false`

## Notes

Dependency install produced pnpm's standard ignored-build-scripts warning for `sharp` and `unrs-resolver`; no build scripts were approved or run.
