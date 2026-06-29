# Lane B - QBE Revenue Source-Text False Positive

Status: PARK_NEXT_SOURCE_PROVEN_FIX_CANDIDATE

## Source Evidence

- Fixture: `financial-engine_v2/backend/tests/eval_fixtures/QBE_H_2025-06-30.json`.
- Document id: `qbe_20250630_h`.
- Fixture source says QBE reports in USD millions. Expected revenue is
  `10875000000`, from "Insurance revenue" and Appendix 4D revenue from
  ordinary activities.

## Failure Lineage

- Prior replay fail-closed `QBE_H_2025-06-30`.
- Scorecard class: `not_evaluated_no_actual_payload`, count 9, plus one
  `ambiguous_quarantined` net debt row.
- Prior source inspection classified
  `QBE_revenue_note_heading_false_positive` as source-proven but parked because
  it is a source-text/income-statement selection class with broader gate impact.
- Read-only scout confirmed the bad replay payload extracted
  `revenue=22000000` from `income_statement:page_17:2.1 Insurance revenue`,
  which triggered
  `validation_gate:accepted_output_scale_magnitude_risk:metric_revenue_ratio_high`.
- The fixture expects `revenue=10875000000` from formal statement
  `Insurance revenue` in USD millions.

## Remediation Eligibility

Final classification: `ELIGIBLE_BUT_NOT_SELECTED`.

This lane may be source-proven, but it is not automatically the safest one
source fix because a false-positive revenue value can trip validation before
any actual payload is supplied. It needs exact evidence of the bad row, the
correct row, and a containment test that does not weaken insurer revenue
selection.

## Validation Plan

- Focused test for QBE-style insurance revenue row selection or source-text
  rejection if selected.
- No-write replay for `QBE_H_2025-06-30`.
- Approved-15 scorecard/gate rebuild after the focused replay.

## Next Action

Open a separate implementation lane for targeted QBE formal-statement revenue
selection. Do not weaken the accepted-output magnitude gate.
