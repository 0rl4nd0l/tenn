---
job_id: redis_role_audit_v1_20260525
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/redis_role_audit_v1_20260525.md
  - reports/agent_jobs/redis_role_audit_v1_20260525/README.md
  - reports/agent_jobs/redis_role_audit_v1_20260525/status.json
  - reports/agent_jobs/redis_role_audit_v1_20260525/redis_usage_inventory.json
  - reports/agent_jobs/redis_role_audit_v1_20260525/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/redis_role_audit_v1_20260525
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit GitHub #59: Redis role audit v1.

# Scope

Classify Redis usage and role boundaries in Tenn: required, optional, disabled, stale, queue-only, cache-like, or involved in worker/task execution.

# Hard Boundaries

- No service starts/stops.
- No Docker, env, config, source, runtime, DB, Qdrant, news, memory, or financial-truth changes.
- Mutate only this task card and the listed report artifacts.

# Required Outputs

- Redis usage inventory.
- Required vs optional runtime expectation classification.
- Risk/gap register.
- Recommended child task if needed.

# Validation

Run and report task-card validate, registry list/check-overlap/claim/release, JSON validation, `git diff --check`, and task-card check-diff.
