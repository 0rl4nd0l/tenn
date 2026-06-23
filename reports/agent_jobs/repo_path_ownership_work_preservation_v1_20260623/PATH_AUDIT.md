# Path Audit

## Required Commands

Captured:

- `pwd`
- `git rev-parse --show-toplevel`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git status --short --untracked-files=all`
- `git worktree list --porcelain`
- `git ls-remote origin refs/heads/migration/clean-runtime-baseline-reconstruct-v1`

The full guard JSON with audited paths is preserved in
`PATH_OWNERSHIP_CHECK.json`.

## Current Task Worktree

| Field | Value |
| --- | --- |
| pwd | `/home/l4nd0/tenn-repo-path-ownership-work-preservation-v1-20260623` |
| git top-level | `/home/l4nd0/tenn-repo-path-ownership-work-preservation-v1-20260623` |
| branch | `control-plane/repo-path-ownership-work-preservation-v1-20260623` |
| HEAD | `4881b5f57fd146243cebb4e246dfa55ae886fbad` after canonical merge |
| canonical remote | `bb4df393f046829cd5d81ba91cde0d5a70352260` |
| classification | `VALID_TASK_WORKTREE` after canonical merge; `DIRTY_RELATED_WORKTREE` during report closeout edits |

## Requested Known Paths

| Path | Resolved path | Classification | Notes |
| --- | --- | --- | --- |
| `/home/l4nd0/tenn` | `/home/l4nd0/tenn` | `STALE_PATH` | Clean when rechecked; branch `local/tenn-entrypoint-current-baseline-v1-20260623`; HEAD `fadd49daca28295228a3b2ac9b0cd8ec5a1af992`; merge-base `1a0f1a03741d692089a0125ecb2f10691b8da597`, not current canonical `bb4df393...`. |
| `/home/l4nd0/tenn-runtime` | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` | `RUNTIME_DIR` | Requested path indicates runtime surface and is not a usable git worktree. |
| `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` | `SPARSE_EVIDENCE_DIR` | Contains repo-like evidence directories but no usable git worktree. |
| `/home/l4nd0/tenn-control-plane-task-ledger-status-refresh-v1-20260623` | same | `STALE_PATH` | Branch `control-plane/tenn-git-guard-global-runner-preservation-v1-20260623`, HEAD `db5976b88ea3b5f971c927d8609a6423a3336da4`, ancestor of canonical. |
| `/home/l4nd0/tenn-repo-path-ownership-work-preservation-v1-20260623` | same | `VALID_TASK_WORKTREE` after canonical merge; `DIRTY_RELATED_WORKTREE` during report closeout edits | Fresh sibling worktree, updated onto PR #398 canonical. |

## Registered Worktrees

`git worktree list --porcelain` was read only. It showed many registered Tenn
worktrees. Relevant control-plane candidates included older task-ledger,
handoff, docs freshness, worker bridge, and guard-preservation worktrees; none
was an open exact match for this task. Stale or unrelated worktrees were not
cleaned or inspected deeply.

The protected path
`/home/l4nd0/tenn-cockpit-bff-proxy-missions-v1-20260623` did not appear in
the filtered worktree-list check.

## Starting-Point Decision

Result: use the fresh sibling task worktree.

Reason: the original `/home/l4nd0/tenn` checkout was not a current canonical
start path. Current live audit shows it is clean but stale relative to PR #397
canonical; the task work uses a fresh sibling worktree instead.
