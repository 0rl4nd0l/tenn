# Lane C - DXS Mixed Source/Scale Investigation

Status: PARK_NOT_YET_ELIGIBLE

## Source Evidence

- Fixture: `financial-engine_v2/backend/tests/eval_fixtures/DXS_H_2025-12-31.json`.
- Document id: `dxs_20251231_h`.
- Fixture source says DXS is AUD millions, with values hand-verified from pages
  12, 13, 16, and 36.

## Failure Lineage

- Prior replay fail-closed `DXS_H_2025-12-31`.
- Scorecard class: `not_evaluated_no_actual_payload`, count 9, plus one
  `ambiguous_quarantined` net debt row.
- Prior source inspection classified DXS as `source_proven=PARTIAL` due to
  intertwined scale/source-policy behavior.
- Read-only scout confirmed the replay payload failed closed on
  `mixed_metric_source_scales,payload_scale_differs_from_metric_source_scale`.
- The bad income rows came from a page-51 thousands table, while the expected
  DXS truth is page-12 consolidated statement values in AUD millions.

## Remediation Eligibility

Final classification: `PARK_NOT_YET_SOURCE_PROVEN_FOR_ONE_FIX`.

This is not a first-choice one-fix lane unless the worker finds a single
deterministic source-precedence bug with a narrow focused validation path. Any
global accepted-output scale/magnitude gate relaxation is forbidden.

## Validation Plan

- If selected, create a focused DXS regression for the exact source/scale class.
- No-write replay for `DXS_H_2025-12-31`.
- Approved-15 scorecard/gate rebuild.

## Next Action

Keep fail-closed behavior. A future lane must inspect parser/table debug and
prove a narrow consolidated-statement precedence rule before implementation.
