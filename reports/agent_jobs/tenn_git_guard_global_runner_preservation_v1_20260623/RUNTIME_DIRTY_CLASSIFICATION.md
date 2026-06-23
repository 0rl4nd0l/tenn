# Greyhound Runtime Dirty Classification

Runtime checkout:
`/mnt/tenn-nvme2/tenn/offloaded-home/l4nd0/greyhound-runtime-master-live-20260621`

Guard smoke:

- `guard_support_status=PASS`
- `registry_status=PASS`
- `ledger_status=DATA_MISSING`
- `data_missing_sources=["ledger:committed", "ledger:live"]`
- `base=origin/codex/runtime-master-live-20260621`
- `merge_base=c96363fbcd708bba78ecfb69e4bc4dacb183d867`

Git dirt summary:

- 70 status rows.
- 25 tracked modified files.
- 45 untracked files.
- 2 untracked code files: `tests/test_report_output_dir_guard.py` and `utils/report_output_dir_guard.py`.

## Evidence-Chain Fix Bucket

These files are part of the bounded evidence-chain fix and validation surface:

- `scripts/run_shadow_non_tgr_rf_evaluation.py`
- `scripts/daily_race_ingest_shadow_orchestrator.py`
- `scripts/shadow_autopilot_daemon.py`
- `tests/test_daily_race_ingest_shadow_orchestrator.py`
- `tests/test_shadow_autopilot_daemon.py`
- `tests/test_report_output_dir_guard.py`
- `utils/report_output_dir_guard.py`
- `artifacts/full_evidence_orchestration_20260525/accurate_predictions_review_board_20260623T154631+1000_report_only/root_cause_packet_20260623T164947+1000_report_only/IMPLEMENTATION_CLOSEOUT.md`

## Existing Runtime Work Bucket

The remaining modified scripts/tests appear to be broader active runtime work
around official-result capture, aggregation, challenger/report packets, shadow
status, and feature gates. They are not safe to silently absorb into one commit:

- `scripts/aggregate_forward_shadow_results.py`
- `scripts/autonomous_official_result_capture.py`
- `scripts/build_high_accuracy_refinement_packet.py`
- `scripts/build_market_residual_challenger_packet.py`
- `scripts/build_market_residual_regime_audit.py`
- `scripts/build_pre_race_gated_challenger_packet.py`
- `scripts/build_promotion_distance_report.py`
- `scripts/build_rank_first_hypothesis_watchlist.py`
- `scripts/build_rolling_model_comparison_packet.py`
- `scripts/build_time_split_gated_challenger_packet.py`
- `scripts/build_unified_evidence_dataset.py`
- `scripts/collect_shadow_odds_snapshots.py`
- `scripts/forward_shadow_status_report.py`
- `scripts/join_forward_shadow_results.py`
- `scripts/shadow_autopilot_v1.py`
- `scripts/shadow_feature_activation_gate.py`
- `tests/test_aggregate_forward_shadow_results.py`
- `tests/test_autonomous_official_result_capture.py`
- `tests/test_forward_shadow_status_report.py`
- `tests/test_shadow_autopilot_v1.py`

## Report And Evidence Artifacts

Untracked artifacts include review-board outputs, daemon/output-dir guard
reports, official-result capture report-only outputs, and execute-append-only
official-result evidence. They should be preserved or committed only by an
owner-approved runtime closeout lane.

## Stop State

Do not promote. Do not train. Do not mutate DB/runtime services/registry. Do not
rewrite snapshots. Do not weaken identity, source, official-result, or pre-jump
timing gates. The next runtime owner should split this dirt into coherent commit
groups or write a fresh owner-boundary manifest before staging anything.
