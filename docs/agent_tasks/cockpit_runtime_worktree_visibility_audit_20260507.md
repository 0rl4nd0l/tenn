---
job_id: cockpit_runtime_worktree_visibility_audit_20260507
lane: Reporting
owner: Claude
allowed_files:
  - docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md
  - reports/agent_jobs/cockpit_runtime_worktree_visibility_audit_20260507/**
approval_required: false
timeout_seconds: 1800
output_dir: reports/agent_jobs/cockpit_runtime_worktree_visibility_audit_20260507
mutation_mode: audit_only
production_data_access: false
---

# Task

Audit the currently running Cockpit runtime and repo/worktree/branch state to determine whether Cockpit upgrades exist in unmerged or stale worktrees/branches but are not visible in the current browser/runtime.

# Hard boundaries

- Do not edit source code.
- Do not merge, cherry-pick, rebase, reset, stash, clean, delete branches, prune worktrees, or commit.
- Do not kill, restart, or replace running Cockpit/backend/LLM processes.
- Do not mutate Tenn runtime databases, Qdrant, Postgres, SQLite stores, news stores, company memory, market memory, financial truth, or gold/eval data.
- Do not "fix" the runtime. Report exact evidence and recommended next action only.
- Allowed writes are only this task card and report artifacts under reports/agent_jobs/cockpit_runtime_worktree_visibility_audit_20260507/.
