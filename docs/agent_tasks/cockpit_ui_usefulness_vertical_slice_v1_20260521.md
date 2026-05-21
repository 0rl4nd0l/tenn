---
job_id: cockpit_ui_usefulness_vertical_slice_v1_20260521
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_ui_usefulness_vertical_slice_v1_20260521.md
  - reports/agent_jobs/cockpit_ui_usefulness_vertical_slice_v1_20260521/
  - reports/agent_jobs/cockpit_ui_usefulness_vertical_slice_v1_20260521/README.md
  - reports/agent_jobs/cockpit_ui_usefulness_vertical_slice_v1_20260521/validation.json
  - reports/agent_jobs/cockpit_ui_usefulness_vertical_slice_v1_20260521/diff-check.json
  - reports/agent_jobs/cockpit_ui_usefulness_vertical_slice_v1_20260521/status.json
  - cockpit-ui/components/cockpit/home/home-page.tsx
  - cockpit-ui/lib/cockpit-home-api.test.ts
  - cockpit-ui/
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_ui_usefulness_vertical_slice_v1_20260521
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit UI Usefulness Vertical Slice

Implement exactly one safe, user-visible Cockpit UI usefulness improvement after a short audit.

Primary scope:
- Improve one Cockpit Home or main analyst landing surface.
- Prefer existing BFF data and existing Cockpit conventions.
- Preserve honest DATA_MISSING, degraded, stale, and mock state rendering.

Exact planned UI/test files after preflight audit:
- `cockpit-ui/components/cockpit/home/home-page.tsx`
- `cockpit-ui/lib/cockpit-home-api.test.ts`

Chosen vertical slice:
- Add one compact Home "Useful Now" analyst-action panel using only the existing `CockpitHomeBffResponse`.
- Rank existing ready attention-queue items, resolvable Home news, and explicit DATA_MISSING/degraded blockers without fabricating data or upgrading evidence trust.

Boundaries:
- Do not edit backend, parser, extraction, memory, Qdrant, news store, runtime, model, GPU, provider, or production data surfaces.
- Keep changed files minimal under `cockpit-ui/`.
- The broad `cockpit-ui/` allowance remains from the orchestrator contract, but the exact intended edit set is listed above.

Required closeout:
- Run focused validation available for the changed UI.
- Run registry release if the job was claimed.
- Write the final report at `reports/agent_jobs/cockpit_ui_usefulness_vertical_slice_v1_20260521/README.md`.
