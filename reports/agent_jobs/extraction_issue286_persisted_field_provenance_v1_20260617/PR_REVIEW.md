# PR Review

Decision: pass_with_risk

## Findings

None blocking.

## Scope Review

- VERIFIED: code changes are limited to the approved model, pipeline, migration,
  and focused DB integrity test file.
- VERIFIED: report/task-card changes are limited to the approved issue #286
  report bundle and task card.
- VERIFIED: no count-24 path is changed.
- VERIFIED: no prompt, source PDF, gold label, runtime, model/GPU/service,
  Qdrant, Redis, news, memory, or live DB path is changed.

## Behavioral Review

- The new `metric_provenance` JSON column is additive and nullable.
- `_upsert_financial_rows` reads structured `field_provenance` first, with
  legacy `metric_provenance` fallback.
- Provenance entries are persisted only when the metric key exists in the
  current payload and its coerced value is non-null.
- Existing row-level `source_document_id`, `confidence_metrics`,
  `period_start`, and `currency` assignment behavior is preserved.

## Residual Risk

- The existing upsert behavior still overwrites absent metrics with `None`.
  This slice preserves that behavior and clears provenance accordingly; it does
  not solve the broader weaker/null overwrite part of issue #286.
- Downstream API/UI exposure of `metric_provenance` is not added in this slice.
  The accepted scope is persistence only.
