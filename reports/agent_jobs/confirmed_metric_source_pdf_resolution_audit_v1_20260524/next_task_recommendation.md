# Next Task Recommendation

Recommend exactly one next task:

`confirmed_metric_scoring_gap_safe_extension_v1_20260524`

## Rationale

The source-PDF blocker has been resolved for the current confirmed metric coverage fixture set:

- 15/15 fixture source groups resolve through the existing allowlisted `/data/asx/docs` source root.
- 146/146 rows have openable local source PDFs through the source-route resolver.
- 73/146 rows are `CONFIRMED_SOURCE_EVIDENCED` and scorecard-scored-ready.
- 70/146 rows remain `CANDIDATE_REVIEW_REQUIRED` and must stay excluded.
- 3/146 rows remain `AMBIGUOUS_OR_DERIVED` and must stay excluded.

The next safe unit of progress is not a source-route audit or PDF-copying task. It is a bounded scoring-gap safe extension that produces or normalizes a confirmed metric coverage scoring artifact for the 73 eligible rows while preserving candidate/ambiguous exclusions and profile labels.

## Required Guardrails

- No canonical truth writes.
- No parser routing changes.
- No Docling config changes.
- No extraction prompt broadening.
- No source PDF copying, downloading, moving, or import.
- No fixture-label mutation unless separately approved as a human review task.
- No source-route allowlist weakening.
- No broad metric extraction accuracy claim.
- Score only the confirmed/scored-ready profile denominator unless a separate reviewed label process promotes more rows.

## Why Not The Other Options

- `metric_extraction_coverage_map_safe_extension_v1_20260524`: useful, but lower leverage now that the source-PDF blocker is classified.
- `appendix5b_gate_floor_status_audit_v1_20260524`: useful, but unrelated to the current confirmed-coverage source-PDF unblock.
- `source_route_allowlist_audit_v1_20260524`: not needed now; the existing allowlist resolves all fixture PDFs.
- `human_source_review_queue_v1_20260524`: still needed later for candidate rows, but the first safe next step is to score the already confirmed 73-row denominator.
- `no-op/defer`: not appropriate because there is a bounded safe next task.
