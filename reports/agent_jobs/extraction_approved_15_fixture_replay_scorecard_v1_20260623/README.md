# Approved 15-Fixture Replay Scorecard

This report packet preserves the current approved 15-fixture no-write replay,
the #97 extracted-payload scorecard, and one narrow extraction scale fallback.

## Summary

- Fixture sources resolved: 15/15.
- Replay status: PARTIAL.
- Accepted payload count: 12.
- Fail-closed payload count: 3.
- Scorecard gate: fail / blocked.
- Current scorecard blockers: ambiguous_quarantined=73,
  not_evaluated_no_actual_payload=16, missing_expected_metric=4,
  present_wrong_value=4.
- Code change: when table extraction drops a standalone statement unit row,
  recover explicit scale from text on pages whose extracted table captions
  identify formal financial statements; abstain when statement pages disagree.

## Safety

- No DB, Qdrant, Redis, source-PDF, gold-label, prompt, model, GPU, runtime,
  service, backfill, count-24/count-32, or production-data mutation.
- Existing report artifacts show no count claim and no pre-persistence
  promotion readiness.
- `logs/tcl_after_fix_replay.log` records a bounded TCL rerun changing that
  case from `validation_gate:scale_validation:suspect_underscaled` to
  `status=ok`; the after-fix full 15-fixture replay improved payload coverage
  to 12/15 accepted, but the scorecard artifacts remain blocked and must not be
  represented as passing.
