# Source Weighting Final Score Contract

## Summary

Local scoped fix complete for issue #259.

`apply_source_weighting()` now treats source weight and credibility as one
resolved credibility dimension for final scoring:
`relevance_score * resolved_credibility * recency_decay`.

Issue #259 remains open because this fix is local only; no commit, push, PR, or
merge was performed in this lane.

## Worktree

- Worktree: `/home/l4nd0/tenn-issue259-source-weighting-final-score-v1-20260626`
- Branch: `safe/issue259-source-weighting-final-score-v1-20260626`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Initial HEAD: `857e76c3180cb0b1fb9fc360652d6a9b64543c86`

## Artifacts

- `STATE.md`
- `VALIDATION.md`
- `status.json`
- `diff-check.json`
