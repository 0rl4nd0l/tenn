# Appendix 4C cash profile contract

Ticket 08 extends the standalone `asx_appendix4c_parser` only. Its input remains
caller-supplied structured table rows and its output remains an in-memory,
report-local result with `canonical_write=false`. It is not imported by
production extraction routing and it invokes no extraction, OCR, model,
runtime, or persistence service.

## Profile fields

The focused profile has exactly these fields:

| Profile field | Deterministic Appendix 4C item |
| --- | --- |
| `customer_receipts` | 1.1 |
| `operating_cf` | 1.9 |
| `capex` | 2.1(c), payments for property, plant and equipment |
| `investing_cf` | 2.6 |
| `financing_cf` | 3.10 |
| `cash_end` | 4.6 or 5.5 |
| `unused_financing` | 7.5 |
| `estimated_funding_quarters` | 8.8 |

Values retain their disclosed sign. The parser does not derive capex from
investing cash flow, derive unused facilities from facility totals, or
recalculate estimated funding quarters.

`customer_receipts` is deliberately not `revenue`. Appendix 4C document type
never authorizes or emits revenue, profit, NPAT, or net debt.

## Evidence and periods

Every accepted observation carries the exact page, table, row, column, line
item, row label, column label, and source span. It also carries:

- the closed `period_basis` plus the source column label as period evidence;
- native currency and the source table/header context as currency evidence;
- source scale and the source table/header context as scale evidence; and
- the raw source cell.

Currency-valued fields abstain unless both native currency and scale are
explicitly resolved. Item 8.8 instead has unit `quarters`, scale `units`, no
currency, and explicit not-applicable currency evidence.

`current_quarter` maps to Ticket 07's `period_only`; `year_to_date` remains
`year_to_date`. The two identities occupy separate profile observations and
cannot overwrite each other. A generic single-value Appendix 4C column is
limited to `period_only`.

## Deterministic precedence and fallback boundary

Deterministic mappings always run first. The optional fallback seam accepts
only explicit values supplied by the caller and never calls a model. A
fallback value is accepted only when:

- its supported field/period pair remains missing after deterministic parsing;
- its line item is in the exact mapping table above;
- its column role matches its closed period basis;
- all row/cell coordinates are non-negative;
- raw cell, row, column, period, currency, scale, and source-span evidence are
  non-empty; and
- its unit/currency/scale combination is valid for the field.

Forbidden or unsupported fields, mismatched line items, ambiguous periods, and
incomplete evidence abstain. Missing fields are explicit `DATA_MISSING`, never
zero-filled or inferred.
