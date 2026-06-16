# Agent Task Ledger Summary

This committed summary is a durable snapshot of recent task-ledger state. It is
not expected to be complete on day one; use it with the branch-independent live
ledger and current repo/GitHub evidence.

## Active Tasks

List claimed or in-progress tasks that future agents should continue, adopt, or
avoid duplicating.

| Task ID | Owner | Branch | Worktree | Status | Touched Files | Next Action |
| --- | --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD | TBD | TBD |

## Open PRs

List open PRs that may make new work unnecessary.

| PR | Task ID | Branch | Summary | Classification | Next Action |
| --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | OPEN_PR_WAIT | TBD |

## Merged Work

List merged work that is canonical and should be reused instead of reimplemented.

| PR/Commit | Task ID | Canonical Base | Summary | Next Action |
| --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | MERGED_USE_CANONICAL |

## Stale Preserve Candidates

List stale branches, reports, task cards, or worktrees that may contain valuable
work but need owner approval before adoption, cleanup, or supersede.

| Candidate | Evidence | Classification | Owner Decision Needed |
| --- | --- | --- | --- |
| TBD | TBD | STALE_PRESERVE | TBD |

## Owner-Boundary Items

List work that needs Orlando's decision before agents proceed.

| Item | Why It Is Boundary | Options | Recommended Next Action |
| --- | --- | --- | --- |
| TBD | TBD | continue/adopt/supersede/park | TBD |

## Next Actions

- Refresh this summary from the live ledger and current PR/issue state before
  relying on it.
- Record `DATA_MISSING` when the live ledger, committed ledger, GitHub, task
  cards, reports, branches, worktrees, or touched-file evidence cannot be read.
- Classify similar work before coding as `ACTIVE_CONTINUE`, `OPEN_PR_WAIT`,
  `MERGED_USE_CANONICAL`, `STALE_PRESERVE`, `SUPERSEDED_IGNORE`,
  `OWNER_BOUNDARY`, or `UNKNOWN_ASK`.
