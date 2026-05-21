---
job_id: cockpit_ui_usefulness_integrate_taskcard_preserve_draft_only_v1_20260521
lane: Reporting
owner: codex
allowed_files:
  - docs/agent_tasks/cockpit_ui_usefulness_integrate_taskcard_preserve_draft_only_v1_20260521.md
  - docs/agent_tasks/cockpit_ui_usefulness_integrate_v1_20260521.md
  - docs/agent_tasks/phase3g_collision_cockpit_taskcard_audit_v1_20260521.md
  - reports/agent_jobs/phase3g_collision_cockpit_taskcard_audit_v1_20260521/README.md
  - reports/agent_jobs/phase3g_collision_cockpit_taskcard_audit_v1_20260521/preflight.md
  - reports/agent_jobs/phase3g_collision_cockpit_taskcard_audit_v1_20260521/blocking_file_classification.md
  - reports/agent_jobs/phase3g_collision_cockpit_taskcard_audit_v1_20260521/phase3g_unblock_options.md
  - reports/agent_jobs/phase3g_collision_cockpit_taskcard_audit_v1_20260521/recommendation.md
  - reports/agent_jobs/phase3g_collision_cockpit_taskcard_audit_v1_20260521/status.json
  - reports/agent_jobs/phase3g_collision_cockpit_taskcard_audit_v1_20260521/diff-check.json
  - reports/agent_jobs/cockpit_ui_usefulness_integrate_taskcard_preserve_draft_only_v1_20260521/README.md
  - reports/agent_jobs/cockpit_ui_usefulness_integrate_taskcard_preserve_draft_only_v1_20260521/preflight.md
  - reports/agent_jobs/cockpit_ui_usefulness_integrate_taskcard_preserve_draft_only_v1_20260521/preservation.md
  - reports/agent_jobs/cockpit_ui_usefulness_integrate_taskcard_preserve_draft_only_v1_20260521/validation.md
  - reports/agent_jobs/cockpit_ui_usefulness_integrate_taskcard_preserve_draft_only_v1_20260521/status.json
  - reports/agent_jobs/cockpit_ui_usefulness_integrate_taskcard_preserve_draft_only_v1_20260521/diff-check.json
approval_required: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/cockpit_ui_usefulness_integrate_taskcard_preserve_draft_only_v1_20260521
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit UI Usefulness Integrate Task-Card Preserve Draft Only

## Scope

Preserve the approved Cockpit integration task-card draft artifact:

- `docs/agent_tasks/cockpit_ui_usefulness_integrate_v1_20260521.md`

Also checkpoint the immediately preceding collision-audit task card and report bundle from `phase3g_collision_cockpit_taskcard_audit_v1_20260521`, because those audit artifacts were created to classify this blocker and would otherwise remain unrelated dirty work in the Phase 3G target checkout.

## Forbidden

- Do not edit Cockpit product code.
- Do not edit Strategy Lab docs, tests, task cards, or reports.
- Do not touch runtime/backend code, stores, dependencies, services, tokens, production data, or paper/live/trading paths.
- Do not touch `docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md`.
- Do not stage broad directories or unrelated dirty work.
