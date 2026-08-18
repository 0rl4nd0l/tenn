---
job_id: repo_prunable_worktree_metadata_review_v1_20260531
lane: Reporting
requested_primary_lane: Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/repo_prunable_worktree_metadata_review_v1_20260531.md
  - reports/agent_jobs/repo_prunable_worktree_metadata_review_v1_20260531/README.md
  - reports/agent_jobs/repo_prunable_worktree_metadata_review_v1_20260531/status.json
  - reports/agent_jobs/repo_prunable_worktree_metadata_review_v1_20260531/worktree_inventory.json
  - reports/agent_jobs/repo_prunable_worktree_metadata_review_v1_20260531/prune_dry_run.txt
  - reports/agent_jobs/repo_prunable_worktree_metadata_review_v1_20260531/diff-check.json
  - reports/agent_jobs/repo_prunable_worktree_metadata_review_v1_20260531/validation.json
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/repo_prunable_worktree_metadata_review_v1_20260531
mutation_mode: audit_only
production_data_access: false
---

# Repo Prunable Worktree Metadata Review

Audit-only task for issue #146.

## Lane

Validator lane: Reporting.

Requested primary lane: Repo Hygiene.

## Objective

Review stale `git worktree` metadata before branch and collision audits rely on
worktree inventory. Capture current inventory and dry-run cleanup output without
mutating Git metadata.

## Scope

Allowed:

- Create this task card and report artifacts.
- Run read-only registry and GitHub duplicate checks.
- Run `git worktree list --porcelain`.
- Run `git worktree prune --dry-run`.
- Classify prunable entries as metadata-only stale, owner-review-needed, or
  `DATA_MISSING`.

Forbidden:

- Do not run actual `git worktree prune`.
- Do not delete branches, delete worktree directories, reset, stash, clean,
  merge, rebase, or checkpoint the shared branch.
- Do not modify product/backend/frontend/runtime/data/memory/extraction files.
- Do not change canonical financial truth, parser routing, prompts, gold
  labels, model/runtime/GPU/service config, or production data.
- Do not touch unrelated dirty work.

## Acceptance Criteria

- Current prunable worktree metadata entries are inventoried with path, branch
  or detached state, gitdir target, prune reason, and path-existence status.
- `git worktree prune --dry-run` output is captured.
- The report distinguishes report-only review from actual cleanup.
- No forbidden surfaces are changed.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/repo_prunable_worktree_metadata_review_v1_20260531.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/repo_prunable_worktree_metadata_review_v1_20260531.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/repo_prunable_worktree_metadata_review_v1_20260531.md`
- `git status --short --untracked-files=all`
- `git worktree list --porcelain`
- `git worktree prune --dry-run`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/repo_prunable_worktree_metadata_review_v1_20260531.md`
- release the registry claim before final report
