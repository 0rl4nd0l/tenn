# Prunable / detached worktree audit

## Totals

- Total worktrees (`git worktree list`): `62`
- Prunable entries (`git worktree list --porcelain`): `3`
- Detached HEAD worktrees: `3`

## Prunable worktrees

| Path | Branch | Path exists | HEAD | In main/preserve ancestry | Recommendation |
|---|---|---|---|---|---|
| `/home/l4nd0/CLAUDEMAESTRO1` | `CLAUDEMAESTRO1` | no (`gitdir` missing) | `f52a7ef` | yes | Archive now; block cleanup until branch retention decision |
| `/home/l4nd0/Maestro1` | `Maestro1` | no (`gitdir` missing) | `79d325f` | no | Review for unique value before archive/delete |
| `/tmp/tenn-api-billing-notice` | detached | no (`gitdir` missing) | `b85e896` | yes | Archive/delete candidate; validate no pending references |

## Detached worktrees

| Path | HEAD | Branch availability | Commit in preserve | Dirty | Recommendation |
|---|---|---|---|---|---|
| `/tmp/tenn-baseline-944fd43` | `944fd43` | detached, no branch name | yes (present in preserve ancestry) | clean | Keep until provenance decision; then archive/delete |
| `/tmp/tenn-metric-coverage-provenance` | `2643426` | detached, no branch name | no | clean | Review for unique proof artifacts before deleting |
| `/tmp/tenn-api-billing-notice` | `b85e896` | detached, prunable missing path | yes | missing path | Low priority cleanup candidate |

## Recommendations

- No immediate safe deletion is suggested because `/tmp/tenn-api-billing-notice` and other detached entries are currently prunable or missing git metadata and should be validated for references before action.

