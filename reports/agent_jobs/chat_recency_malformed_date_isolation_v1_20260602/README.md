# Chat Recency Malformed Date Isolation

## Summary

Local scoped fix complete for issue #261.

Malformed `published_at` values now use neutral recency at the source-weighting
boundary and retain visible malformed-date status/warning metadata instead of
crashing chat strategy weighting.

Issue #261 remains open because this fix is local only; no commit, push, PR, or
merge was performed in this lane.

## Worktree

- Worktree: `/home/l4nd0/tenn-issue261-malformed-date-isolation-v1-20260626`
- Branch: `safe/issue261-malformed-date-isolation-v1-20260626`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Initial HEAD: `857e76c3180cb0b1fb9fc360652d6a9b64543c86`

## Artifacts

- `STATE.md`
- `VALIDATION.md`
- `status.json`
- `diff-check.json`
