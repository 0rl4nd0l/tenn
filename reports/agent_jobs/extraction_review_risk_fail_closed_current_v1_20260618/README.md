# Review-Risk Fail-Closed Current Canonical

Status: `DONE`.

This safe extension preserves the local accepted-output review-risk fail-closed
gate on current canonical and proves the behavior with saved count-24 JSON only.

Implemented:

- Added a broad-run fail-closed helper for accepted outputs whose
  `accepted_output_scale_magnitude_risk.risk_level` is `review`.
- Wired the gate into broad-run row assembly while preserving risk/provenance
  metadata.
- Added focused tests for summary grouping, review-risk fail-closed behavior,
  info-risk pass-through, and already-failed row preservation.
- Added a saved-artifact replay over approved count-24 JSON only.

Replay result:

- WHC and EDU move from `ok` to `failed` with
  `validation_gate:accepted_output_scale_magnitude_risk`.
- NSR and CAE remain accepted `info`-risk rows.
- Projected status distribution: 14 `failed`, 9 `ok`, 1 `ok_low_confidence`.

No PDF extraction, count sample, broad extraction, backfill, runtime service,
data-store, source-PDF, prompt, gold-label, schema, issue mutation, merge, or
production mutation is in scope. After local commit preservation, the owner
approved only pushing this branch and opening a PR for the bounded diff.
