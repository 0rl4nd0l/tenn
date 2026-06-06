# Post-PR297 Count-16 Failure Taxonomy

Generated: 2026-06-06T02:09:44.182377Z

Scope: audit of the 13 failed documents from the preserved post-PR297 count-16 validation. No sample rerun, broad extraction, backfill, service restart, DB mutation, Qdrant mutation, news mutation, memory mutation, source PDF edit, prompt change, gold-label change, or schema change was performed.

## Summary

- Failed documents audited: 13
- Bucket counts: `{"candidate_selection_errors": 1, "document_family_policy_gaps": 1, "eligible_financial_docs_with_missing_scale_evidence": 5, "eligible_financial_docs_with_suspicious_scale_evidence": 2, "true_noncandidate_docs": 4}`
- `scale_unknown` failures are heterogeneous, not one global fix.
- The classifier-low-confidence failures are valid abstentions, but they expose candidate-selection gaps.

## Fixes Made

- Added source-bound support for smart-apostrophe thousands markers such as `$A’000` / `$’000`.
- Added a conservative early source-text fallback for explicit `$000` / `$A’000` scale evidence when parsed tables do not expose scale.
- Added focused unit tests and updated the metric extraction contract.

## Next Targeted Repair

Create a bounded candidate-exclusion taxonomy slice for meeting notices/proxy forms, board-change notices, operational project updates, share-sale gross-proceeds announcements, and pre-results re-presentation documents. That slice should update candidate/scorecard reason taxonomy and tests together.

## Bounded Sample Decision

Another bounded sample is not justified yet. Run focused unit/report-local validation for the repaired classes first; consider a new bounded sample only after candidate-exclusion taxonomy and selected-table scale-binding are tested.

## DATA_MISSING

- Post-fix pass/fail outcome for the original 13 failed documents is DATA_MISSING because no sample rerun was allowed.
- Docling-native behavior remains DATA_MISSING because the prior validation used PyMuPDF fallback for all 16 documents.
- WHC 2022 parser/table coverage root cause remains DATA_MISSING without Docling-native parse evidence.
- AZJ nearest-$100,000 rounding policy remains DATA_MISSING pending separate source-bound design.
