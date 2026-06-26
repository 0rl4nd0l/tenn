# Chat Session Coherence Range

## Summary

Local source fix complete and validated. This lane clamps
`compute_session_coherence()` to its documented `0.0` to `1.0` range and adds a
focused negative-cosine regression test.

Issue #258 was not closed from this local-fix lane because the fix was not yet
pushed, PR'd, or merged into canonical. Closing the GitHub issue before
publication would have overstated repository state.

Publication addendum, 2026-06-26: this fix is now published as draft PR #415:
`https://github.com/0rl4nd0l/tenn/pull/415`. Issue #258 remains open until the
draft PR is reviewed and merged into canonical.

GitHub status comment posted:
`https://github.com/0rl4nd0l/tenn/issues/258#issuecomment-4807361415`.

Publication status comment posted:
`https://github.com/0rl4nd0l/tenn/issues/258#issuecomment-4809403931`.

## Worktree

- Worktree: `/home/l4nd0/tenn-issue258-chat-session-coherence-range-v1-20260626`
- Branch: `safe/issue258-chat-session-coherence-range-v1-20260626`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Initial HEAD: `857e76c3180cb0b1fb9fc360652d6a9b64543c86`

## Artifacts

- `STATE.md`
- `VALIDATION.md`
- `status.json`
- `diff-check.json`

## Next Action

Review and merge draft PR #415; close #258 only after the validated fix is
accepted into canonical.
