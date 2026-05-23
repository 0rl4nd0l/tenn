# Quarantine And Error Policy

## Summary

The future adapter must fail closed. Invalid output is quarantined, not normalized into a valid Strategy Lab artifact.

## Quarantine Required

- Sidecar output contains broker credentials, exchange keys, token fields, account fields, paper orders, live orders, quick-trade, bot activation, or kill-switch data.
- Sidecar output sets `canonical_financial_truth=true`.
- Sidecar output sets `execution_allowed=true`.
- Sidecar output attempts Tenn DB, Qdrant, news, memory, financial-truth, parser/extraction, gold-label, source-registry, Cockpit, or runtime writes.
- Sidecar output uses `financial_truth` or generic `source-backed` labels.
- Sidecar output lacks `raw_payload_ref`.
- Sidecar output is malformed or fails schema validation.
- Sidecar output has an unexpected `artifact_type`.
- Sidecar output lacks assumptions or limitations.

## DATA_MISSING Instead Of Guessing

The adapter may carry explicit `DATA_MISSING` for:

- Benchmark object and benchmark returns.
- Explicit provider field.
- Strategy code hash.
- Raw payload hash in design-only tasks.
- Regime segment start/end times.
- Sample size by regime.
- Exact candle count.
- Structured tuning result shape.

If a required field is missing but not represented as `DATA_MISSING`, quarantine the output.

## No Store Writes

Quarantine and pending-review artifacts must not write:

- Tenn DB.
- Qdrant.
- News stores.
- Memory stores.
- Financial-truth stores.
- Parser, extraction, or gold-label files.
- Source registry.
- Cockpit UI/backend.
- Runtime/backend code.

## Human Review

All normalized sidecar artifacts remain `PENDING_REVIEW`. `human_review_decision` is Tenn-owned only and cannot be emitted by QuantDinger or any sidecar.
