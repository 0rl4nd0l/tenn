---
job_id: worker_gpu_worker_provenance_env_parity_audit_v1_20260525
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/worker_gpu_worker_provenance_env_parity_audit_v1_20260525.md
  - reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/README.md
  - reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/status.json
  - reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/worker_runtime_inventory.json
  - reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/provenance_gap_register.json
  - reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit GitHub #58: worker runtime provenance audit v1.

# Scope

Inventory how Tenn reports worker identity, runtime identity, model/runtime references, and evidence provenance across task reports, scripts, config references, and docs.

# Hard Boundaries

- No source edits, config edits, service changes, data-store changes, runtime changes, or live worker operations.
- Mutate only this task card and the listed report artifacts.

# Required Outputs

- `worker_runtime_inventory.json`
- `provenance_gap_register.json`
- Recommended child task if needed.

# Validation

Run and report task-card validate, registry list/check-overlap/claim/release, JSON validation, `git diff --check`, and task-card check-diff.
