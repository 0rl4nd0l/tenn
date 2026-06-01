# Extraction Canary Source Review Fixture Bridge V1

## Summary

This slice converts the seven accepted canary runtime payloads into
source-reviewable real-gold evidence without running extraction or treating
runtime output as truth.

New source-reviewed canary fixtures were added for AM5, AQX, ATM, and CRS.
Existing CLV and CTM canary fixtures now include `source_document_id` metadata.
The new rekey helper maps actual payloads exported by source document id to
real-gold fixture ids for deterministic scoring.

## Source Review

Source labels were verified with `pdftotext` against local PDFs under
`/data/asx/docs`:

- AM5: half-year raw AUD values; other income is not revenue and loss before
  tax is not EBIT.
- AQX: half-year raw AUD values; loss before tax is not EBIT.
- ATM: annual IDR values; source statements are expressed in millions of Rupiah
  and fixture expectations are raw IDR after applying that source scale.
- CRS: half-year raw AUD values; interest income is not revenue and loss before
  tax is not EBIT.

The source review artifact is `source_verification.json`.

## Canary Actual Probe

Input actuals:

`reports/agent_jobs/extraction_canary_actual_payload_exporter_v1_20260601/canary_actual_payloads.json`

Rekey command:

```bash
financial-engine_v2/.venv/bin/python scripts/rekey_real_gold_actuals_by_source_document.py \
  --fixtures-dir financial-engine_v2/backend/tests/fixtures/extraction_gold \
  --actuals-json reports/agent_jobs/extraction_canary_actual_payload_exporter_v1_20260601/canary_actual_payloads.json \
  --out-json reports/agent_jobs/extraction_canary_source_review_fixture_bridge_v1_20260601/canary_actuals_real_gold_keyed.json \
  --summary-json reports/agent_jobs/extraction_canary_source_review_fixture_bridge_v1_20260601/source_document_rekey_summary.json \
  --require-all-actuals-matched
```

Result: all seven canary actual payloads matched source-reviewed fixtures.

Canary-only scorecard result:

- total fixtures: 7
- trusted: 4
- abstained: 2
- quarantined: 1
- trusted payloads: AM5, CLV, CRS, CTM
- blockers:
  - AAU: wrong `np_attributable`
  - AQX: loss before tax promoted to `ebit`
  - ATM: scale context mismatch (`trillions` runtime payload vs source
    statements expressed in millions of Rupiah)

This is a real blocker for broad extraction graduation. The accepted canary
runtime status is not enough to claim source-correct extraction across these
documents.

## Boundaries

This task did not run extraction, start/reload runtime services, mutate SQLite,
write canonical rows, mutate Qdrant/news/memory stores, edit source PDFs, change
prompts, change schemas, touch Cockpit UI, or mutate GitHub state.

## Validation

- `pytest`: 41 passed
- targeted Ruff: passed
- `py_compile`: passed
- JSON artifact validation: passed
- seven-payload rekey: passed
- canary-only real-gold scorecard: generated and fail-closed on three source
  correctness blockers
- `git diff --check`: passed

## Next Safe Step

Create a follow-up extraction hardening card for:

- AAU attributable-profit selection
- AQX EBIT abstention when only loss before tax is present
- ATM IDR scale normalization from statements expressed in millions of Rupiah
