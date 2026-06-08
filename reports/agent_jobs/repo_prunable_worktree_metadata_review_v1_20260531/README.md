# Repo Prunable Worktree Metadata Review

## Summary

This is an audit-only report for issue #146. It reviews stale Git worktree
metadata that can pollute branch and collision audits.

No cleanup was performed. `git worktree prune` was not run without `--dry-run`.

## Current Evidence

- GitHub issue checked: #146, open.
- Duplicate PR search for `worktree metadata prunable gitdir`: no matching PR.
- Registry overlap: active extraction Evaluation job exists, so this task uses
  validator lane `Reporting` while preserving requested primary lane
  `Repo Hygiene`; overlap check passed after that correction.
- `git worktree list --porcelain` inventory: 324 total entries.
- Prunable entries: 22.
- Metadata-only stale entries: 22.
- Needs-owner-review entries: 0.
- Present worktree entries: 302.
- `git worktree prune --dry-run` listed only
  `gitdir file points to non-existent location` removals.

## Classification

All 22 prunable entries were classified as `metadata_only_stale` because:

- each entry is marked prunable by Git;
- each path no longer exists on disk;
- each prune reason is `gitdir file points to non-existent location`;
- dry-run output names only stale metadata records under `.git/worktrees`.

## Artifacts

- `worktree_inventory.json`: parsed inventory with path, branch or detached
  state, prune reason, path existence, and classification.
- `prune_dry_run.txt`: exact dry-run prune output.
- `validation.json`: task-card validation.
- `status.json`: registry claim/release status.
- `diff-check.json`: task-card diff validation.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/repo_prunable_worktree_metadata_review_v1_20260531.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/repo_prunable_worktree_metadata_review_v1_20260531.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/repo_prunable_worktree_metadata_review_v1_20260531.md`
- `git status --short --untracked-files=all`
- `git worktree list --porcelain`
- `git worktree prune --dry-run`

## Next Safe Step

Actual cleanup is safe only after explicit operator approval and a fresh
registry/worktree preflight. The cleanup command would be:

```bash
git worktree prune
```

Do not run that command from this task card or PR.
