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

## Pre-persistence truth gates

The live extractor has conservative source-bound gates before canonical row or
Qdrant persistence. These gates fail the extraction instead of correcting values:

- Advisory-only document titles such as `Quarterly Report Advisory` are blocked
  before metric extraction.
- `ebit` is blocked when the row evidence is explicitly EBITDA rather than EBIT.
- Explicit source-unit values in row evidence, for example `$44.1 million`, must
  be within tolerance of the normalized metric value; 100x or larger
  over/under-scale mismatches are blocked.
- Explicit source-period evidence, for example annual `year ended` wording, must
  agree with the payload `period_type`. Ambiguous source-period evidence is
  diagnostic only and does not infer a corrected period.

## Non-goals

- No DB writes, no embedding calls, no retrieval.
- No production metric thresholds are inferred from synthetic fixtures.
- No synthetic fixture is a benchmark claim for model quality.

## Reporting helper

Generate a deterministic scorecard JSON directly from the synthetic fixture set:

```bash
python financial-engine_v2/scripts/extraction_eval_scorecard.py
```

Optional actual payload file (fixture_id -> extracted payload mapping):

```bash
python financial-engine_v2/scripts/extraction_eval_scorecard.py \
  --actuals-json /path/to/actuals.json
```

Output is a stable JSON object with keys including:
- `total_fixture_count`
- `total_metric_expectations`
- `correct_count`
- `wrong_count`
- `missing_count`
- `abstained_count`
- `quarantined_count`
- `period_correctness_summary`
- `currency_correctness_summary`
- `scale_correctness_summary`
- `fixture_summaries`

## Real-document gold eval pilot

The real-gold pilot keeps real document labels separate from synthetic fixtures
and evaluates an extracted JSON payload map against labelled expectations.

### Pilot semantics (trust vs metric status)

Each real fixture is first evaluated with the existing metric evaluator, then mapped to
a trust outcome using deterministic rules:

- `trusted`: context matches and every required metric is `correct`.
- `abstain`: context matches and at least one required metric is `wrong`, `missing`,
  or `abstain`.
- `quarantine`: any context mismatch (`period_end`, `currency`, or `scale`), in which case
  every metric is marked `quarantine`.

For real fixtures, `missing` means a required metric in the fixture is not present in
`metrics` in the extraction payload. It is **not** treated as `abstain`; `abstain`
metric status is only used when extraction marks an optional metric absent in an
optional list, and this pilot does not define optional metrics today.

Interpretation pattern in scorecards:

- `abstain` is not an error state by itself; it means "not fully reliable for trust." A
  document can be `abstain` with `wrong_count: 1`, `missing_count: 1`, or both.
- `trust_triggers` (or `context_mismatches` for quarantine) explains why trust is not
  `trusted`.
- `trusted` requires the per-document metric statuses in aggregate to be clean and
  context-aligned.

### Real gold fixture format

Place fixtures under `backend/tests/fixtures/extraction_gold/*.json` using:

- `document_id`: stable document key (e.g., filing id)
- `period_type`, `period_end`, `currency`, `scale`: context expected by extractor
- `metrics`: required numeric/null expectations for this pilot document
- optional `tolerances`: per-metric relative tolerance
- optional `expected_trust`: one of `trusted`, `abstain`, `quarantine`

Example:

```json
{
  "document_id": "real_trusted_match",
  "period_type": "A",
  "period_end": "2024-12-31",
  "currency": "AUD",
  "scale": "thousands",
  "metrics": {
    "revenue": 1500000,
    "ebit": 120000
  },
  "tolerances": {
    "revenue": 0.01,
    "ebit": 0.02
  },
  "expected_trust": "trusted"
}
```

### Running the real gold scorecard

```bash
python financial-engine_v2/scripts/extraction_gold_eval_scorecard.py \
  --actuals-json path/to/actuals.json
```

`actuals.json` must be a map keyed by `document_id` with extractor output payloads:

```json
{
  "real_trusted_match": {
    "period_end": "2024-12-31",
    "period_type": "A",
    "currency": "AUD",
    "scale": "thousands",
    "metrics": {
      "revenue": 1500000,
      "ebit": 120000
    }
  }
}
```

The output includes per-document trust outcomes and fixture separation status:

- `trusted_count`
- `abstained_count`
- `quarantined_count`
- `trust_check_summary`
- `fixture_summaries`

Per-entry `fixture_summaries` fields are designed to be read together:

- `trust`: final trust outcome.
- `trust_triggers`: metric-level blockers when `trust=abstain` (for example
  `revenue:missing`).
- `context_mismatches`: context blockers when `trust=quarantine`.
- `wrong_count`, `missing_count`, etc.: diagnostic metric quality bucket totals.

Example of a clean non-contradictory interpretation:

- `trusted` with `wrong_count: 0`, `missing_count: 0` -> reliable extraction for this fixture.
- `abstain` with `missing_count: 1` -> required metric unavailable, intentionally
  non-trustworthy for downstream decisions.
- `quarantine` with non-empty `context_mismatches` -> fixture context does not match
  source slice; metric values are considered inconclusive.

### Pilot scope and limits

- It is a **pilot only**: no pipeline or schema changes.
- Trust is derived from fixture metrics + context checks; it does not replace existing
  extraction accuracy gates.
- A document is `quarantine` if any context field mismatches, even when metric values
  match.
- A document is `abstain` when required metrics are missing or wrong without a
  context mismatch.
- Missing fixtures or missing output keys are evaluated in the same deterministic,
  non-LLM fixture flow.
