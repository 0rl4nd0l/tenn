# Extraction Broad Approved-15 Current-Canonical Replay

Status: PARTIAL

Worktree: `/home/l4nd0/tenn-extraction-broad-approved15-current-canonical-v1-20260628`
Branch: `safe/extraction-broad-approved15-current-canonical-v1-20260628`
Canonical head: `7a0bab4ca9337c6c9d735f23d5898d9b306ecc2d`
Latest fetched origin head: `87e49247a0ddbf5e35fd6b7c2b61ea5a1fe9d74c`

## Result

- Full post-SEG approved-15 no-write replay: 15 cases, 11 accepted payloads, 4 fail-closed payloads, 0 infrastructure failures, side-effect audit passed.
- Selected exactly one remaining source-proven blocker class: `CSL_revenue_narrative_false_positive`.
- Implemented narrow source-text guard: CSL-style future-sales narrative revenue can be replaced from formal statement text when available; if still sourced from rejected narrative text, the `revenue` metric is cleared fail-closed instead of retained as a false positive.
- Focused CSL no-write replay: PASS / `ok_low_confidence`, 1 accepted payload, revenue absent, 9 non-null metrics retained, side-effect audit passed.
- Final report-local scorecard has 12 actual payload documents and remains blocked with 97 blocking rows.
- Final result-class summary: 49 `present_correct`, 4 `missing_expected_metric`, 2 `present_wrong_value`, 18 `not_evaluated_no_actual_payload`, 73 `ambiguous_quarantined`, 0 `missing_evidence`, 0 `unsupported_correctly_abstained`, 0 `wrong_period`, 0 `wrong_unit_currency_scale`.
- Latest fetched origin drift is recorded in `canonical_drift.json`; it does not touch the extraction service, focused extraction tests, no-write replay runner, scorecard builder, confirmed-metric fixtures, or source-asset map used by this lane.

Report-only complete; system functionality not proven. No DB, Qdrant, Redis, news, runtime, backfill, production data, source PDF, gold-label, prompt, model, service, branch, or GitHub mutation was performed.

## Primary Artifacts

- `no_write_replay_after_fix_seg/validation.json`
- `no_write_replay_after_fix_csl/validation.json`
- `payload_scorecard_after_fix.json`
- `scorecard_gate_after_fix.json`
- `payload_scorecard_delta_after_fix.json`
- `failure_classes_after_fix.json`
- `row_level_failure_matrix_after_fix.json`
- `source_inspection.json`
- `validation.json`
- `handoff/HANDOFF.md`
