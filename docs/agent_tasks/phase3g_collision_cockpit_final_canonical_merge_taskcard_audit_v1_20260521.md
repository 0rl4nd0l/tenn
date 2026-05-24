---
job_id: phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521
lane: Reporting
owner: codex
allowed_files:
  - docs/agent_tasks/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521.md
  - reports/agent_jobs/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521/README.md
  - reports/agent_jobs/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521/preflight.md
  - reports/agent_jobs/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521/blocking_file_classification.md
  - reports/agent_jobs/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521/phase3g_unblock_options.md
  - reports/agent_jobs/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521/recommendation.md
  - reports/agent_jobs/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521/status.json
  - reports/agent_jobs/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521/diff-check.json
approval_required: true
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/phase3g_collision_cockpit_final_canonical_merge_taskcard_audit_v1_20260521
mutation_mode: audit_only
production_data_access: false
---

# Phase 3G Collision Cockpit Final Canonical Merge Task-Card Audit

## Scope

Audit-only repo-hygiene collision triage for the remaining Phase 3G Strategy Lab consolidation blocker caused by unrelated Cockpit task-card dirt:

- `docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md`

## Allowed Writes

- This task card.
- The exact report files listed in `allowed_files`.

## Forbidden Writes and Actions

- Do not edit, clean, remove, stage, unstage, commit, merge, cherry-pick, stash, or reset `docs/agent_tasks/cockpit_ui_usefulness_final_canonical_merge_v1_20260521.md`.
- Do not edit Cockpit product code.
- Do not edit Strategy Lab docs, tests, task cards, or reports.
- Do not touch runtime, backend, product code, Tenn stores, dependencies, services, tokens, production data, paper/live/trading paths, or unrelated dirty work.

## Required Output

Classify the blocking Cockpit final canonical merge task-card artifact, report registry and report-bundle evidence, and recommend the smallest safe unblock path for Phase 3G without letting Strategy Lab absorb unrelated Cockpit work.
