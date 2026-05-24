---
job_id: disk_pressure_safe_cleanup_audit_v1_20260524
title: Disk pressure safe cleanup audit
owner: Codex
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Runtime/Ops
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
approval_required: false
timeout_seconds: 10800
output_dir: reports/agent_jobs/disk_pressure_safe_cleanup_audit_v1_20260524
allowed_files:
  - docs/agent_tasks/disk_pressure_safe_cleanup_audit_v1_20260524.md
  - reports/agent_jobs/disk_pressure_safe_cleanup_audit_v1_20260524/
forbidden:
  - rm
  - git_clean
  - docker_prune
  - worktree_prune
  - moving_files
  - deleting_caches
  - service_restarts
  - db_mutation
  - qdrant_mutation
  - news_mutation
  - memory_mutation
  - model_mutation
---

# Disk Pressure Safe Cleanup Audit

## Objective

Audit root disk pressure and produce a safe cleanup or migration plan for Tenn without deleting, moving, pruning, restarting, or mutating runtime/data stores.

## Mode

`AUDIT ONLY`

The audit may write only this task card and the report directory:

- `reports/agent_jobs/disk_pressure_safe_cleanup_audit_v1_20260524/`

## Required Evidence

Collect current-turn evidence from:

- `df -hT / /home /tenn /mnt/tenn-nvme2 /mnt/nvme /mnt/sdb2`
- `du -xhd1 / | sort -h | tail -30`
- `du -xhd1 /home/l4nd0 | sort -h | tail -40`
- `du -xhd1 /tenn 2>/dev/null | sort -h | tail -40`
- `du -xhd1 /home/l4nd0/.cursor-server 2>/dev/null | sort -h | tail -40`
- `du -xhd1 /home/l4nd0/.codex 2>/dev/null | sort -h | tail -40`
- `docker system df -v`
- `git -C /home/l4nd0/tenn worktree list`
- `find /home/l4nd0 -maxdepth 2 -type d \( -name node_modules -o -name .next -o -name .pytest_cache -o -name .ruff_cache -o -name test-results -o -name playwright-report \) -prune -print`
- `find /home/l4nd0 -maxdepth 2 -type d -name 'tenn-*' -print`
- registry active jobs via `python3 scripts/agent_job_registry.py list-active`
- large files over 1G on the root filesystem without crossing into `/mnt/tenn-nvme2` where possible

## Required Classifications

Classify cleanup candidates as exactly one of:

1. `SAFE_DELETE_AFTER_APPROVAL`
2. `SAFE_MOVE_TO_TENN_NVME2_AFTER_APPROVAL`
3. `CACHE_REBUILDABLE_BUT_USEFUL`
4. `ACTIVE_RUNTIME_DO_NOT_TOUCH`
5. `REPO_EVIDENCE_DO_NOT_TOUCH`
6. `UNKNOWN_NEEDS_USER_REVIEW`

## Deliverable

Write:

- `reports/agent_jobs/disk_pressure_safe_cleanup_audit_v1_20260524/README.md`

The report must include:

- confirmed disk usage
- biggest directories and files
- active runtime paths that must not be touched
- cleanup candidate table with path, size, classification, risk, proposed command, and rollback if any
- estimated space recoverable by low-risk cleanup
- exact commands for future cleanup, clearly marked `DO NOT RUN IN THIS AUDIT`
- final recommendation

## Hard Stops

Stop and report instead of cleaning if any cleanup, migration, delete, prune, restart, or data-store mutation appears necessary. Do not run `rm`, `git clean`, `docker prune`, `git worktree prune`, move commands, cache deletion commands, service restarts, or DB/Qdrant/news/memory/model mutation.
