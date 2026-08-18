# Decisions

1. Continue in the current-canonical worktree and preserve the stale source checkout untouched.
2. Treat report-local replay and scorecard artifacts as evidence, not production functionality proof.
3. Use the full post-SEG approved-15 replay as the denominator before selecting another blocker class.
4. Select exactly one remaining source-proven blocker class after the full replay: `CSL_revenue_narrative_false_positive`.
5. Keep the fix narrow: reject CSL-style future-sales narrative revenue source text, prefer formal statement text if recoverable, otherwise clear only the rejected `revenue` metric.
6. Park RMS, QBE, DXS, and BHP/MIN classes for separate source-bound passes.
7. Stop PARTIAL because the scorecard gate remains blocked and this lane remains no-write/report-local.
