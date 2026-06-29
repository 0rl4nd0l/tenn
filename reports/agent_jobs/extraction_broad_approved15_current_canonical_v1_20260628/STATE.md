# State

Status: PARTIAL

VERIFIED:
- Current-canonical sibling worktree is on `safe/extraction-broad-approved15-current-canonical-v1-20260628` at canonical head `7a0bab4ca9337c6c9d735f23d5898d9b306ecc2d` plus local task diff.
- Latest fetched `origin/migration/clean-runtime-baseline-reconstruct-v1` is `87e49247a0ddbf5e35fd6b7c2b61ea5a1fe9d74c`, seven commits after the worktree head.
- Canonical drift audit found no changes to the extraction service, focused extraction test file, no-write replay runner, scorecard builder, confirmed-metric fixtures, or source-asset map used by this lane.
- Portable guard classified the worktree as dirty related work, expected for this continuation lane.
- Registry read-only check reported no active overlapping jobs.
- Task-card validation passed after the CSL replay artifact allowlist update.
- Full post-SEG approved-15 no-write replay ran with temp DATA_ROOT/cache/output and loopback LLM only: 15 cases, 11 accepted, 4 fail-closed, 0 infrastructure failures, side-effect audit passed.
- One remaining source-proven class was selected and fixed: `CSL_revenue_narrative_false_positive`.
- Focused CSL replay after the fix passed and accepted `CSL_H_2025-12-31` as `ok_low_confidence` with no revenue metric retained.
- Final scorecard was rebuilt from the full post-SEG replay plus focused CSL replay and remains blocked.

DATA_MISSING:
- No production DB/API/output freshness proof was collected because this lane forbids production/runtime/data mutation.
- Broad count-24/count-32 behavior was not checked because this task forbids those runs.

Remaining blockers:
- Scorecard gate remains blocked: 97 blocking rows.
- Remaining separate classes include RMS cash-flow missing metrics, QBE revenue source-text false positive, DXS mixed scale/source selection, and BHP/MIN `np_attributable` wrong-value rows.
- CSL rows remain `ambiguous_quarantined` under the current #97 scoring policy even after an actual payload is available, so aggregate scorecard counts are unchanged by the focused CSL replay.
