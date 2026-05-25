---
job_id: merge_parking_registry_surface_safe_extension_v1_20260525
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/merge_parking_registry_surface_safe_extension_v1_20260525.md
  - docs/agent_registry/merge_parking/REGISTRY.md
  - docs/agent_registry/merge_parking/schema.md
  - docs/agent_registry/merge_parking/parked/README.md
  - reports/agent_jobs/merge_parking_registry_surface_safe_extension_v1_20260525/README.md
  - reports/agent_jobs/merge_parking_registry_surface_safe_extension_v1_20260525/status.json
  - reports/agent_jobs/merge_parking_registry_surface_safe_extension_v1_20260525/validation.json
  - reports/agent_jobs/merge_parking_registry_surface_safe_extension_v1_20260525/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/merge_parking_registry_surface_safe_extension_v1_20260525
mutation_mode: safe_extension
production_data_access: false
---

# Task

Implement the safe child task recommended by `merge_parking_registry_surface_audit_design_v1_20260525`.

# Scope

Create a committed docs-owned merge parking registry surface with schema and empty parked-record directory documentation.

# Hard Boundaries

- Do not merge, rebase, cherry-pick, park, move, delete, prune, stash, reset, clean, checkout, or mutate any branch/worktree.
- Do not auto-register existing parked work.
- Do not touch backend, frontend, runtime, config, service, DB, Qdrant, news, memory, or financial-truth files.
- Mutate only this task card, the listed docs registry files, and listed report artifacts.

# Required Outputs

- `docs/agent_registry/merge_parking/REGISTRY.md`
- `docs/agent_registry/merge_parking/schema.md`
- `docs/agent_registry/merge_parking/parked/README.md`
- Report artifacts under `reports/agent_jobs/merge_parking_registry_surface_safe_extension_v1_20260525/`

# Validation

Run and report task-card validate, registry list/check-overlap/claim/release, docs content inspection, JSON validation, `git diff --check`, and task-card check-diff.
