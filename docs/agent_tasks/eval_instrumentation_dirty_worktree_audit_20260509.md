---
job_id: eval_instrumentation_dirty_worktree_audit_20260509
lane: Evaluation
owner: Claude
allowed_files:
  - docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md
  - reports/agent_jobs/eval_instrumentation_dirty_worktree_audit_20260509/**
approval_required: false
timeout_seconds: 2400
output_dir: reports/agent_jobs/eval_instrumentation_dirty_worktree_audit_20260509
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit the dirty worktree `/mnt/sdb2/home/l4nd0/tenn-eval-instrumentation-20260421` and classify its modified files by value, risk, lane ownership, and recommended next action.
