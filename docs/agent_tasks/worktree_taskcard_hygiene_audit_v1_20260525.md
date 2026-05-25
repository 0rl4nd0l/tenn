---
job_id: worktree_taskcard_hygiene_audit_v1_20260525
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/worktree_taskcard_hygiene_audit_v1_20260525.md
  - reports/agent_jobs/worktree_taskcard_hygiene_audit_v1_20260525/README.md
  - reports/agent_jobs/worktree_taskcard_hygiene_audit_v1_20260525/status.json
  - reports/agent_jobs/worktree_taskcard_hygiene_audit_v1_20260525/hygiene_inventory.json
  - reports/agent_jobs/worktree_taskcard_hygiene_audit_v1_20260525/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/worktree_taskcard_hygiene_audit_v1_20260525
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit GitHub #64: worktree and loose task-card hygiene audit v1.

# Scope

Classify the current worktree, branch, loose task-card, ignored-report, and registry hygiene state so future Codex/Claude jobs do not collide or misread stale work as current truth.

# Hard Boundaries

- Do not delete, prune, clean, reset, stash, checkout, restore, or move worktrees/files.
- Do not touch unrelated dirty work.
- Do not mutate registry except read/list, claim, and release for this task card.
- Do not mutate runtime config, services, data stores, or source files.
- Mutate only this task card and the listed report artifacts.

# Required Outputs

- Worktree inventory summary.
- Prunable worktree classification.
- Branch freshness summary.
- Loose task-card classification.
- Ignored report artifact visibility risks.
- Registry overlap risks.
- Safe cleanup prerequisites.

# Validation

Run and report task-card validate, registry list/check-overlap/claim/release, JSON validation, `git diff --check`, and task-card check-diff.
