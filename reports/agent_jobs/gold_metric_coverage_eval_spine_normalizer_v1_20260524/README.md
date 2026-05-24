# Gold Metric Coverage Eval Spine Normalizer

Implemented a narrow offline normalizer under `scripts/reporting/`.

Outputs:
- `normalized_manifest.json`
- `scorecards.csv`
- `metric_expectations.csv`

Boundary semantics preserved:
- `canonical_core` is only the strict 10-document / 24-check no-regression proof.
- `expanded_required` is only the 15-document / 39-check required-metric proof where available.
- `confirmed_metric_coverage` is breadth inventory, not current accuracy proof.
- `confirmed_unscored`, `ambiguous_or_derived`, and `unsupported` rows do not become accuracy claims.

No extraction logic, parser routing, prompts, gold labels, canonical financial truth, database, Qdrant, news, or memory store was modified.
