# Decisions

## D1: Use additive JSON column

Decision: use an additive JSON column on `ASXPeriodicFinancial`, keyed by metric.

Grade: VERIFIED from current model shape and board approval.

Reason: this is the narrowest approved schema path and matches existing JSON use in the backend model layer. A normalized child table remains a larger design option outside this approved slice.

## D2: Persist only field-coupled provenance

Decision: `_upsert_financial_rows` must persist provenance only for metrics whose coerced value is actually written.

Grade: VERIFIED from issue #286 acceptance criteria and board minority objection.

Reason: provenance must not drift from the metric value it supports.

## D3: Preserve row-level behavior

Decision: keep existing `source_document_id`, `confidence_metrics`, `period_start`, and `currency` assignments.

Grade: VERIFIED from owner requirement and existing tests.

Reason: this slice adds per-metric evidence without changing the row-level contract.

## D4: Treat PR #289 as stale partial evidence

Decision: inspect but do not adopt PR #289 wholesale.

Grade: VERIFIED from `gh pr view 289` and `git show`.

Reason: PR #289 was broad, merged to a temporary branch, and persisted whole-payload provenance without the new field-coupled behavior required here.
