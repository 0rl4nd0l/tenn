# Chat Session Coherence Range

## Summary

Local source fix complete and validated. This lane clamps
`compute_session_coherence()` to its documented `0.0` to `1.0` range and adds a
focused negative-cosine regression test.

Issue #258 is not closed from this lane because the fix is not pushed, PR'd, or
merged into canonical. Closing the GitHub issue before publication would
overstate repository state.

GitHub status comment posted:
`https://github.com/0rl4nd0l/tenn/issues/258#issuecomment-4807361415`.

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

Publish the branch or open a PR from
`safe/issue258-chat-session-coherence-range-v1-20260626`; close #258 only after
the validated fix is accepted into canonical.
