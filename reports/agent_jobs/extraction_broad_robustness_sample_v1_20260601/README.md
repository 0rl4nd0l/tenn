# Extraction Broad Robustness Sample V1

## Summary

Ran one bounded broad extraction robustness sample against `/data/asx/docs`
after the docs-root resolver fix. The run used `llama.cpp` through the local
router on `8001` with seed `20260601`, requested `8` documents, and produced
robustness/status evidence only.

This is not a gold accuracy result. There is no ground truth in this helper,
and the artifacts do not authorize canary promotion, canonical writes, broad
backfill, or full extraction graduation.

## Result

- Documents sampled: `8`.
- Unique tickers: `8`.
- Status distribution: `ok=2`, `ok_low_confidence=1`, `failed=5`.
- Success rate: `37.5%`.
- Failure class: `validation_gate=5`.
- Runtime total: `741.9s`; max document time: `240.73s`.
- Successful/low-confidence documents had 7 non-null metrics each.

## Failure Digest

- `GTE`: `validation_gate:metric_label_mismatch:ebit:pre_tax`.
- `ARL`: `validation_gate:scale_unknown`.
- `HNG`: `validation_gate:scale_unknown`.
- `CAF`: `validation_gate:scale_unknown`.
- `TLS`: `validation_gate:scale_unknown`.

The run also surfaced non-blocking runtime/evaluation signals:

- non-AUD/CAD source downgrade to `ok_low_confidence`;
- balance-sheet JSON generation timeout followed by truncated-table retry;
- repeated broad-corpus `scale_unknown` blockers on documents classified under
  `financial_performance`.

## Boundaries

- Backend startup: false.
- Canary/process-document route: false.
- Real-gold eval route: false.
- Broad backfill: false.
- Database, Qdrant, news, memory, or canonical financial row mutation: false.
- Source PDF copy or mutation: false.
- Parser, prompt, schema, or model/GPU config change: false.
- Cockpit UI or GitHub mutation: false.

## Cleanup

Dedicated GPU activity token `0033b70bb5e4427d9891aaee8d860ec6` was cleared.
Ports `8000` and `8001` were closed after shutdown, no llama/broad extraction
processes remained, and Tesla M40 VRAM returned to `0 / 24576 MiB`.

## Next Safe Step

The dominant broad-sample blocker is `scale_unknown`, with one EBIT
pre-tax-label gate. The next safe hardening slice is a read-only classification
of the five failures into source-document classes and source-unit evidence
patterns before deciding whether to adjust candidate selection, source-document
classification, or Scale Policy V1.
