# CTM Spaced-Year Canary Rerun

## Outcome

Accepted. CTM document `035c6758-7aed-41a6-9e84-ad154125d431` was rerun through
`POST /api/process/document/{document_id}` at HEAD `63a992ae` after the
Docling spaced-year detector fix.

Run `233900e7-1683-4ff4-bded-abb68824c0e3` completed with
`extraction_status=ok`, `financial_rows_written=1`, `persisted=true`, and
`reviewable_metrics_count=8`.

## Persisted Row Evidence

The new row for CTM persisted as:

- `period_type=A`
- `period_end=2025-12-31`
- `currency=AUD`
- `confidence_metrics=0.917`
- `ebit=-15111363`
- `np_attributable=-14308070`
- `operating_cf=-13225929`
- `investing_cf=-2167611`
- `financing_cf=22024529`
- `capex=-2123497`
- `cash_end=24577181`
- `shares_outstanding=562827818`

`extraction_runs.structured_json` recorded
`source_period_end_evidence.reason=year_ended_explicit_date` and
`source_period_type_correction.reason=year_ended_explicit_date`, so the prior
`validation_gate:period_source_mismatch:payload=H:source=A:year_ended_source_phrase`
blocker did not recur.

## Runtime Evidence

Preflight passed with backend health `ok`, worker `pong`,
`OLLAMA_URL=http://127.0.0.1:11434`, CTM source PDF present, exactly one CTM
document row, and no active CTM run before submission.

Dedicated runtime units used for this rerun:

- `tenn-llama-router-ctm-spaced-20260601.service`
- `tenn-backend-ctm-spaced-20260601.service`
- `tenn-llm-gpu-worker-ctm-spaced-20260601.service`

All three units were stopped after completion. Cleanup evidence shows ports
`:8000` and `:8001` no longer listening, no matching runtime processes, no
`/tmp/llama-server.lock`, and the Tesla M40 back to `0 / 24576 MiB`.

## Scope Boundary

This is bounded CTM canary evidence only. It completes the CTM rerun after the
spaced-year source-period fix, but it is not a broad backfill, not a full ticker
universe run, and not a claim that extraction is graduated across all tickers.
