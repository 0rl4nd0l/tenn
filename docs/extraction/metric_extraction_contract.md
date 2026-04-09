# Metric Extraction Evaluation Contract

This contract defines how synthetic extraction fixtures are scored in the hardening harness.
It is intentionally narrow: extraction quality is scored from expected numeric values and
known context fields only.

## Inputs

Each fixture under `backend/tests/fixtures/extraction_eval/*.json` defines:
- `fixture_id`
- `period_type`, `period_end`, `currency`, `scale`
- `metrics`: exact expected values (`null` is explicitly expected null)
- `expected_nulls`: metrics expected to be null
- `optional_metrics`: metrics allowed to abstain
- `tolerances`: optional per-metric relative tolerance overrides

Expected metric values are compared against the extracted payload's `metrics` field.

## Metric status classes

- `correct`: expected value matches extracted value within tolerance, or expected null is matched by null.
- `wrong`: numeric mismatch, or expected-null metric has a non-null extracted value.
- `missing`: expected value was provided but extraction omitted it (`null` in extracted).
- `abstain`: optional metric is missing in extraction.
- `quarantine`: fixture context does not align with extracted context (`period_end`, `currency`, or `scale`).

### Scoring semantics

Metric-level scores are:
- `correct` → `1.0`
- `abstain` → `0.5`
- `wrong`/`missing` → `0.0`
- `quarantine` is excluded from aggregates (cannot determine fidelity)

This intentionally treats wrong/implausible values as worse than abstention.

## Context checks

Fixtures are marked `quarantine` when any checked context field mismatches:
- `period_end`
- `currency`
- `scale`

When quarantined, all metrics in that fixture are excluded from aggregate scoring.

## Non-goals

- No DB writes, no embedding calls, no retrieval.
- No production metric thresholds are inferred from synthetic fixtures.
- No synthetic fixture is a benchmark claim for model quality.
