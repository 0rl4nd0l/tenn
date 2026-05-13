---
job_id: dev_storage_fast_worktree_v1
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/dev_storage_fast_worktree_v1.md
  - reports/agent_jobs/dev_storage_fast_worktree_v1/**
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/dev_storage_fast_worktree_v1
mutation_mode: safe_extension
production_data_access: false
---

# Task

Create a fast active Tenn development worktree on NVMe/SSD without changing product code or deleting existing worktrees.

# Hard boundaries

- Do not edit Tenn product source files.
- Do not edit backend, frontend, extraction, memory, Qdrant, Postgres, SQLite, data, model, or runtime files.
- Do not run cleanup/prune/delete commands.
- Do not migrate dirty/uncommitted changes automatically.
- Do not use `/mnt/hdd-data` as the target for the new fast worktree.
- Do not overwrite any existing `/home/l4nd0/tenn-fast*` or `/mnt/ssd/tenn-fast*` path.
- If the current worktree has dirty product changes, leave them untouched and report that they remain in the original worktree.

# Allowed work

- Create this task card.
- Create `reports/agent_jobs/dev_storage_fast_worktree_v1/`.
- Run read-only repo/storage preflight checks.
- Create one new linked Git worktree under a fast filesystem if safe.
- Write a final report.
- Run non-mutating validation commands inside the new worktree.

# Validation

Required:
- `findmnt -T` for source repo and target path parent.
- `df -hT` for `/`, `/mnt/ssd`, `/mnt/hdd-data`.
- `git rev-parse --show-toplevel`.
- `git rev-parse --abbrev-ref HEAD`.
- `git rev-parse HEAD`.
- `git status --short --untracked-files=all`.
- `git worktree list --porcelain`.
- Verify new worktree path is on non-rotational/fast storage if possible.
- In new worktree: `git status --short --untracked-files=all`.
- In new worktree: identify branch/HEAD.
- Do not run full test suites unless explicitly requested.
