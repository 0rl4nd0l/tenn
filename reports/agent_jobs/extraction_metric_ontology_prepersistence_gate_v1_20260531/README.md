# Metric Ontology Pre-Persistence Gate

## Summary

This safe-extension slice hardens the report-local confirmed-metric payload
scorecard used before extraction canary or pre-persistence review.

The scorecard now separates approved scorecard aliases from broader metric
contract aliases. Supported actual-payload matching remains narrow, while
unsupported, persisted-only, planned, ambiguous, and internal-only metric
families are detected through their contract aliases and quarantined instead of
being treated as absent.

## Scope

- Lane: Financial Truth, with Evaluation support.
- Branch: `safe/extraction-metric-ontology-prepersist-v1-20260531`.
- Worktree: `/home/l4nd0/tenn-extraction-metric-ontology-prepersist-v1-20260531`.
- Execution mode: SAFE EXTENSION MODE.
- Runtime/backend/GPU work: not performed.
- Production data access: not used.

## Result

- Added safe scorecard alias mapping for cash/cash-equivalent names to
  `cash_end`.
- Added contract-family alias lookup for noncanonical actual payload detection.
- Updated payload value/evidence lookup to quarantine noncanonical contract
  aliases while preserving narrow matching for supported metrics.
- Added regressions for total equity, interest expense, finance costs, total
  assets, planned EPS, internal-only debt fields, and safe cash aliases.

## Full Goal Status

This contributes to all-ticker extraction hardening by improving the gate that
decides whether extracted metric payloads are safe enough for canary or
pre-persistence review. It does not complete full all-ticker extraction
graduation. Runtime canary execution, broader corpus scorecards, and final
graduation evidence remain separate open work.
