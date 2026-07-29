# Financial observation contract

Ticket 05 promotes only the existing `revenue` metric. The legacy
`asx_periodic_financials` row remains the compatibility projection and the
workflow remains the sole transaction owner.

## Acceptance

An observation is staged only when all of the following are explicit and
unambiguous:

- source document ID, extraction run ID, and extractor version;
- ticker, `revenue` value, period end, and period basis;
- an `ok` (not low-confidence) production extraction;
- an income-statement revenue source row explicitly marked `statutory`, with no
  adjusted, underlying, non-statutory, or pro-forma marker;
- matching explicit source-text period-basis and period-end evidence;
- a supported native currency explicitly present in the source cell evidence;
- a closed source-scale vocabulary with non-unknown scale origin and raw source
  cell evidence; and
- structured revenue provenance bound by the workflow to the same source
  document, metric, period, currency, and original source scale.

These gates establish the only Ticket 05 accounting/trust state:
`accounting_basis=statutory` and `trust_state=accepted`. Missing, unknown,
arbitrary, low-confidence, highlights-only, adjusted, or conflicting context
abstains. Document type never supplies a period basis. Values are already
normalized absolute values; observations store `scale=units`, retain native
currency, and preserve the original scale and raw cell in provenance.

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
period identity, an accepted statutory revenue observation overrides the
legacy revenue only when every accepted candidate agrees on value, native
currency, and absolute-unit scale and that currency/scale context exactly
matches the legacy row. Missing or mismatched legacy currency/scale context,
or any candidate disagreement, abstains from the override. No insertion-time
or write-order precedence is used.

Broader metric projection, period-basis expansion, accounting-basis separation,
and restatement precedence remain outside Ticket 05.
