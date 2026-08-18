# Validation

## Pre-Closeout

| Check | Result |
| --- | --- |
| Task-card validate | PASS |
| Registry read-only | PASS, `active_jobs=[]` |
| #329 readback | PASS, open before closeout |
| `git diff --check` | PASS |
| Task-card `check-diff` | PASS |

## GitHub Closeout

| Action | Result |
| --- | --- |
| Comment #329 | PASS, `https://github.com/0rl4nd0l/tenn/issues/329#issuecomment-4649121316` |
| Close #329 | PASS |

## Boundaries

- Actual `git worktree prune`: not run.
- Branch/ref deletion: not run.
- Real worktree-directory deletion: not run.
