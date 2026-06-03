# Metric Extraction Contract

Canonical metric families stay fixed. Appendix 4D/4E ordinary-activities profit-after-tax rows may alias into the existing `np_attributable` family when they are explicit source-bound evidence.

For short Appendix 4D/4E wrapper documents only, the validation gate may accept exactly two canonical metrics when the wrapper is structurally identified, the canonical metrics are `revenue` and `np_attributable`, and the source also carries the required wrapper disclosure evidence and source-bound period/scale/currency context.

## Allowed Alias

- `profit after income tax expense from ordinary activities`
- `profit/(loss) after income tax expense from ordinary activities`

These are treated as deterministic aliases for `np_attributable` only.

## Exclusions

- `profit before tax`
- `total comprehensive income`
- `nta per security`
- dividends and distributions
- record-date rows

These remain disclosure-only and must not create new canonical metric families or reduce canonical `insufficient_metrics` counts.
