# Financial observation contract

Ticket 06 promotes exactly the ten existing `CANONICAL_METRIC_FIELDS`. The legacy
`asx_periodic_financials` row remains the compatibility projection and the
workflow remains the sole transaction owner.

## Acceptance

An observation is staged only when all of the following are explicit and
unambiguous:

- source document ID, extraction run ID, and extractor version;
- ticker, a present numeric canonical metric value, period end, and period basis;
- an `ok` (not low-confidence) production extraction;
- a source row in one of the metric contract's allowed statement contexts,
  explicitly marked `statutory`, with no
  adjusted, underlying, non-statutory, or pro-forma marker;
- matching explicit source-text period-basis and period-end evidence;
- for currency metrics, a supported native currency explicitly present in the
  source cell evidence; for `shares_outstanding`, the closed `shares` unit;
- a closed source-scale vocabulary with non-unknown scale origin and raw source
  cell evidence; and
- structured metric provenance bound by the workflow to the same source
  document, metric, period, currency, and original source scale.

These gates establish the accounting/trust state:
`accounting_basis=statutory` and `trust_state=accepted`. Missing, unknown,
arbitrary, low-confidence, adjusted, or conflicting context abstains for that
metric without suppressing valid siblings. Document type never supplies a period basis. Values are already
normalized absolute values; observations store `scale=units`, retain native
currency or the `shares` unit, and preserve the contract unit kind, original
scale, and raw cell in provenance. Share counts are never treated as currency
or FX-converted.

## Identity and immutability

The source-context identity is document, extractor version, ticker, metric,
period end, period basis, accounting basis, currency, and scale. It deliberately
allows different documents, extractor versions, period bases, and accounting
bases for the same company period and metric.

A versioned, canonically serialized representation of that complete identity is
mapped to `observation_id` with UUIDv5. The extraction-run ID is intentionally
not part of either identity: a retry may have a new operational run while
retaining the same immutable source context and therefore the same observation
ID. Changing any source-context identity field changes the deterministic ID.

A PostgreSQL `INSERT ... ON CONFLICT DO NOTHING` makes a retry at the same
source-context identity a no-op without a query-before-add race. The seam does
not flush, commit, or roll back; the workflow remains sole transaction owner.
The accepted row is never updated.

## Compatibility read

`/financials` retains its existing rows and response fields. For each legacy
period identity, each accepted statutory metric independently overrides its
legacy field only when every accepted candidate for that metric agrees on
value, native currency/share unit, and absolute-unit scale and that unit/scale
context exactly matches the legacy row. Missing observations leave sparse
legacy values intact. Missing or mismatched legacy context, or candidate
disagreement, abstains only for that metric. No insertion-time or write-order
precedence is used.

Period-basis expansion, accounting-basis separation, and restatement precedence
remain outside Ticket 06.
