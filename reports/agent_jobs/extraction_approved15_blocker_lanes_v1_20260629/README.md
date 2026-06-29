# Approved-15 Blocker Lane Closeout

Status: PARTIAL

This report starts from `origin/migration/clean-runtime-baseline-reconstruct-v1`
after PR #461 and the prior handoff at
`/home/l4nd0/tenn-extraction-broad-approved15-current-canonical-v1-20260628/reports/agent_jobs/extraction_broad_approved15_current_canonical_v1_20260628/handoff/HANDOFF.md`.

## What Changed

- Created a clean task worktree:
  `/home/l4nd0/tenn-extraction-approved15-blocker-lanes-v1-20260629`.
- Created task card:
  `docs/agent_tasks/extraction_approved15_blocker_lanes_v1_20260629.md`.
- Created lane packets A-F under `lanes/`.
- Used read-only scouts for all six lanes.
- Implemented exactly one narrow source-proven fix: RMS formal
  `STATEMENT OF CASH FLOWS` pages are now accepted by the existing
  statement-text cash-flow recovery path.
- Added one focused regression test for the RMS formal-heading case.
- Ran focused unit validation, focused no-write RMS replay, and approved-15
  scorecard/gate rebuild.

## Result

The RMS fix removed the four remaining `missing_expected_metric` rows:

- `operating_cf`
- `investing_cf`
- `financing_cf`
- `capex`

The approved-15 gate remains blocked:

- `ambiguous_quarantined=73`
- `not_evaluated_no_actual_payload=18`
- `present_wrong_value=2`
- `missing_expected_metric=0`

## Main Artifacts

- `lanes/A_RMS_cashflow_missing_metrics.md`
- `lanes/B_QBE_revenue_source_text_false_positive.md`
- `lanes/C_DXS_mixed_source_scale.md`
- `lanes/D_BHP_MIN_np_attributable_wrong_value.md`
- `lanes/E_ambiguous_quarantined_grouping.md`
- `lanes/F_orchestrator_integration_gate.md`
- `no_write_replay_after_fix_rms/replay_results.json`
- `payload_scorecard_after_fix.json`
- `scorecard_gate_after_fix.json`
- `payload_scorecard_delta_after_fix.json`
- `failure_classes_after_fix.json`
- `row_level_failure_matrix_after_fix.json`

## Stop State

Report-local remediation is complete for this task card, but system
functionality is not fully proven. The scorecard gate is still blocked, so the
correct state is `PARTIAL`.
