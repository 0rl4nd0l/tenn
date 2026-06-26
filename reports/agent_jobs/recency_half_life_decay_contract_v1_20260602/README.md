# Recency Half-Life Decay Contract

## Summary

Local source fix complete and validated. This lane makes
`compute_recency_decay()` implement true half-life semantics for
`half_life_days` and adds fixed-timestamp source-weighting tests.

Issue #260 is not closed from this lane because the fix is not pushed, PR'd, or
merged into canonical. Closing the GitHub issue before publication would
overstate repository state.

GitHub status comment posted:
`https://github.com/0rl4nd0l/tenn/issues/260#issuecomment-4807424121`.

## Worktree

- Worktree: `/home/l4nd0/tenn-issue260-recency-half-life-decay-v1-20260626`
- Branch: `safe/issue260-recency-half-life-decay-v1-20260626`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Initial HEAD: `857e76c3180cb0b1fb9fc360652d6a9b64543c86`

## Artifacts

- `STATE.md`
- `VALIDATION.md`
- `status.json`
- `diff-check.json`

## Next Action

Publish the branch or open a PR from
`safe/issue260-recency-half-life-decay-v1-20260626`; close #260 only after the
validated fix is accepted into canonical.
