# Financial observation and result-disclosure contract

Tickets 07-09 retain exactly the ten existing `CANONICAL_METRIC_FIELDS`. The legacy
`asx_periodic_financials` row remains the compatibility projection and the
workflow remains the sole transaction owner.

## Structured period input

`period_observations` is the explicit multi-period collection. Each member is a
complete observation context with its own `metrics`, `field_provenance`,
`period_end`, `period_basis`, `source_period_type`, `source_period_evidence`,
and `source_period_end_evidence`. Members are evaluated independently. The
single-period top-level shape and the public revenue-only alias remain
compatibility paths.

New quarterly members use the closed bases `period_only` and `year_to_date`.
Their metric source cell must bind a non-negative `column_index`, non-empty
`header_cell` and `raw_value`, and respectively the exact `column_role`
`current_quarter` or `year_to_date`. Comparative, prior-period, generic date,
announcement-date, inferred, metadata-only, unknown, or mismatched columns
abstain; they are never relabelled from a numeric value or date.

## Acceptance

An observation is staged only when all of the following are explicit and
unambiguous:

- source document ID, extraction run ID, and extractor version;
- ticker, a present numeric canonical metric value, period end, and period basis;
- an `ok` (not low-confidence) production extraction;
- a source row in one of the metric contract's allowed statement contexts,
  explicitly marked both `consolidated` and `statutory`, with no
  adjusted, underlying, non-statutory, or pro-forma marker;
- matching basis-specific source-text period-scope and reporting-period-end
  evidence;
- for currency metrics, a supported native currency explicitly present in the
  source cell evidence; for `shares_outstanding`, the closed `shares` unit;
- a closed source-scale vocabulary with non-unknown scale origin and raw source
  cell evidence; and
- structured metric provenance bound by the workflow to the same source
  document, metric, period, currency, and original source scale, with explicit
  `accounting_basis=statutory` and `consolidation_scope=consolidated`.

These gates establish the accounting/trust state:
`accounting_basis=statutory` and `trust_state=accepted`. Missing, unknown,
parent-only, arbitrary, low-confidence, adjusted, or conflicting context abstains for that
metric without suppressing valid siblings. Document type never supplies a period basis. Values are already
normalized absolute values; observations store `scale=units`, retain native
currency or the `shares` unit, and preserve the contract unit kind, original
scale, and raw cell in provenance. Share counts are never treated as currency
or FX-converted.

## Identity and immutability

The source-context identity is document, extractor version, ticker, metric,
period end, period basis, accounting basis, currency, and scale. It deliberately
allows different documents, extractor versions, period bases, and accounting
bases for the same company period and metric. Thus `period_only` and
`year_to_date` always have distinct immutable identities even when every other
identity member matches.

A versioned, canonically serialized representation of that complete identity is
mapped to `observation_id` with UUIDv5. The extraction-run ID is intentionally
not part of either identity: a retry may have a new operational run while
retaining the same immutable source context and therefore the same observation
ID. Changing any source-context identity field changes the deterministic ID.

A PostgreSQL `INSERT ... ON CONFLICT DO NOTHING` makes a retry at the same
source-context identity a no-op without a query-before-add race. The seam does
not flush, commit, or roll back; the workflow remains sole transaction owner.
The accepted row is never updated.

## Non-statutory disclosure lane

Explicit `adjusted`, `underlying`, `normalized`, and `pro_forma` values are
never financial observations and never participate in canonical projection.
They may be staged in `financial_result_disclosures` only when the candidate
has an explicit consolidated scope, closed accounting basis, exact source
label containing the corresponding source term, document-bound provenance
that repeats that exact label and basis, and a non-empty reconciliation whose
items each retain their source label, numeric value, and source reference.

Disclosure identity adds the exact source label to the source-context identity,
so differently labelled management measures do not collide. Inserts are
immutable and idempotent. Missing or contradictory basis, scope, label,
provenance, or reconciliation evidence causes disclosure abstention. The
disclosure table has no canonical-profile read path.

## Compatibility read

`/financials` retains its existing rows and response fields. For each legacy
period identity, each accepted statutory metric independently overrides its
legacy field only when every accepted candidate for that metric agrees on
value, native currency/share unit, and absolute-unit scale and that unit/scale
context exactly matches the legacy row. Missing observations leave sparse
legacy values intact. Missing or mismatched legacy context, or candidate
disagreement, abstains only for that metric. No insertion-time or write-order
precedence is used.

Accepted `period_only` and `year_to_date` observations are appended as
deterministically ordered, basis-labelled, sparse `observation_only` rows.
Conflicting metrics abstain independently. These rows never replace or
overwrite legacy `Q`, `H`, or `A` rows.

Restatement precedence remains outside Ticket 09.
