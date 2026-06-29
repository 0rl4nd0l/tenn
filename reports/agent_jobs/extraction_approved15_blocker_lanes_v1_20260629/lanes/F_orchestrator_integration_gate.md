# Lane F - Orchestrator Integration Gate

Status: GATE_EXECUTED_PARTIAL

## Source Evidence

- Prior scorecard gate after PR #461 remains blocked:
  `missing_expected_metric=4`, `present_wrong_value=2`,
  `ambiguous_quarantined=73`, `not_evaluated_no_actual_payload=18`.
- Actual payload document count is 12 of 15.
- After the RMS fix, gate remains blocked:
  `ambiguous_quarantined=73`, `not_evaluated_no_actual_payload=18`,
  `present_wrong_value=2`; `missing_expected_metric=0`.
- Actual payload document count remains 12 of 15.

## Failure Lineage

- The current gate is pre-persistence and report-local. It never grants
  canonical writes and never runs extraction by itself.
- Focused replay after any single fix must feed the approved-15 payload map and
  scorecard/gate rebuild.

## Remediation Eligibility

Final classification: `ORCHESTRATOR_ONLY_PARTIAL`.

This lane should not change extraction logic. Its job is to keep the validation
contract honest and stop `PARTIAL` unless all blocking result classes are gone
with source-bound evidence.

## Validation Plan

- Verify focused replay outputs and side-effect audit after any fix.
- Verify scorecard/gate rebuilt from report-local payloads.
- Verify task-card check-diff and report-artifact checks.
- Final stop state remains `PARTIAL`; the scorecard gate is not fully
  unblocked.

## Next Action

Use Lane F gate artifacts as the stop condition. Next implementation should
start a separate task card for QBE or BHP/MIN, not continue this one.
