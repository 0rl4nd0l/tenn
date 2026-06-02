# Extraction Low Confidence Case Audit V1

## Verdict

The two remaining `ok_low_confidence` cases from bounded sample commit
`758a2861` are not broad extraction failures, but they are not clean strict-ok
evidence.

- `NSM` is a real half-year report. Hard gates passed, but
  `confidence_metrics=0.695` put it below the strict-ok cutoff. The extracted
  loss, cash-flow, cash, and capex-like exploration/evaluation values are
  source-supported. The sampled `shares_outstanding=18,913,652` matched the
  dollar issued-capital amount rather than the number-of-shares row, so a narrow
  abstention guard was added and tested.
- `WBC` is a 1Q24 quarterly update, not formal financial statements. It
  contains explicit AUD `$m` financial-summary values and supports the two
  extracted metrics under current bank-revenue policy, but it lacks cash-flow,
  balance-sheet, and share-count statements. Keep it `ok_low_confidence` rather
  than filtering or promoting it as strict-ok.

## Root Cause

The exact low-confidence reason for both cases is the soft confidence gate:
hard validation gates passed, `confidence_metrics` was above the failure
threshold `0.60`, and below the strict-ok cutoff `0.70`.

`NSM`: `0.695`, six non-null metrics, formal half-year report.

`WBC`: `0.667`, two non-null metrics, structurally sparse quarterly update.

## Recommendation

A larger bounded sample is justified only as another bounded validation step
after this fix, not as full extraction/backfill or canonical promotion. The next
sample should preserve full payload `row_refs` and `provenance` for every
low-confidence case, because the committed sample artifact is too lossy to prove
row-level evidence after the fact.

No prompt/gold-label changes were made. No full extraction/backfill was run.

## DATA_MISSING

- The committed sample artifact lacks per-metric `row_refs`, provenance,
  source page numbers, thinking, and full payloads.
- The previous report says the raw broad-test JSON was staged under `/tmp`; that
  raw payload is not in the committed report bundle.
- The exact NSM `shares_outstanding` row_ref from the sample is missing, but
  the source PDF and sampled value were sufficient to apply a fail-closed
  dollar-column abstention guard.
