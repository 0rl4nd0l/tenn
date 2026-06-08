---
job_id: repo_prunable_worktree_metadata_prune_cleanup_v1_20260608
lane: Reporting
supporting_lanes:
  - Repo Hygiene
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/repo_prunable_worktree_metadata_prune_cleanup_v1_20260608.md
  - reports/agent_jobs/repo_prunable_worktree_metadata_prune_cleanup_v1_20260608/README.md
  - reports/agent_jobs/repo_prunable_worktree_metadata_prune_cleanup_v1_20260608/status.json
  - reports/agent_jobs/repo_prunable_worktree_metadata_prune_cleanup_v1_20260608/worktree_inventory.json
  - reports/agent_jobs/repo_prunable_worktree_metadata_prune_cleanup_v1_20260608/prune_dry_run.txt
  - reports/agent_jobs/repo_prunable_worktree_metadata_prune_cleanup_v1_20260608/validation.md
  - reports/agent_jobs/repo_prunable_worktree_metadata_prune_cleanup_v1_20260608/diff-check.json
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/repo_prunable_worktree_metadata_prune_cleanup_v1_20260608
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
requested_primary_lane: Repo Hygiene
requested_mutation_mode: approval_packet_only
github_issue: 329
github_mutation_allowed: false
actual_prune_allowed: false
---

# Repo Prunable Worktree Metadata Prune Cleanup v1 - 2026-06-08

## Objective

Prepare the #329 approval packet by refreshing worktree inventory and capturing
`git worktree prune --dry-run` output.

## Scope

Allowed:

- Create this task card and report artifacts.
- Run read-only registry checks.
- Run `git worktree list --porcelain`.
- Run `git worktree prune --dry-run`.
- Classify prunable entries as metadata-only stale, needs owner review, or
  `DATA_MISSING`.

Forbidden:

- Do not run actual `git worktree prune`.
- Do not delete branches or branch refs.
- Do not delete real worktree directories.
- Do not reset, stash, clean, rebase, merge, or cherry-pick.
- Do not modify product/backend/frontend/runtime/data/memory/extraction files.
- Do not change canonical financial truth, parser routing, prompts, gold
  labels, model/runtime/GPU/service config, or production data.
- Do not close #329.

## Acceptance Criteria

- Fresh inventory records all current worktree entries and prunable entries.
- Fresh dry-run prune output is captured.
- Any dry-run entry whose real path exists is marked as a hard stop.
- Actual cleanup remains blocked pending explicit operator approval.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/repo_prunable_worktree_metadata_prune_cleanup_v1_20260608.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root . --read-only`
- `python3 -m json.tool reports/agent_jobs/repo_prunable_worktree_metadata_prune_cleanup_v1_20260608/status.json`
- `python3 -m json.tool reports/agent_jobs/repo_prunable_worktree_metadata_prune_cleanup_v1_20260608/worktree_inventory.json`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/repo_prunable_worktree_metadata_prune_cleanup_v1_20260608.md`

## Hard Stops

- Active overlapping registry job.
- Dry-run output implies branch/ref deletion or real worktree-directory
  deletion.
- Any prunable path still exists on disk.
- Operator approval for actual prune is absent.
