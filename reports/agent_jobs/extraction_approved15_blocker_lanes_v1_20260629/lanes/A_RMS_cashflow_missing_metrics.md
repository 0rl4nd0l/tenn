# Lane A - RMS Cash-Flow Missing Metrics

Status: FIX_IMPLEMENTED_AND_VALIDATED

## Source Evidence

- Fixture: `financial-engine_v2/backend/tests/eval_fixtures/RMS_H_2025-12-31.json`.
- Document id: `rms_2025h1_appendix4d`.
- Fixture source says values are hand-verified from the RMS Appendix 4D and
  half-year report, AUD thousands.
- Expected metrics still missing in the post-PR #461 scorecard:
  `operating_cf=171179000`, `investing_cf=-211390000`,
  `financing_cf=-84747000`, `capex=-25239000`.
- Current actual payload has `revenue`, `ebit`, `np_attributable`, `cash_end`,
  and `shares_outstanding`, but all four cash-flow metrics above are null.
- Focused replay after the fix recovered:
  `operating_cf=171179000`, `investing_cf=-211390000`,
  `financing_cf=-84747000`, and `capex=-25239000`.
- Fresh row refs are from page 23 cash-flow rows:
  `Net cash provided by operating activities`,
  `Net cash used in investing activities`,
  `Net cash used in financing activities`, and
  `Payments for property, plant and equipment`.

## Failure Lineage

- Prior full approved-15 no-write replay accepted `RMS_H_2025-12-31`.
- Scorecard class: `missing_expected_metric`, count 4.
- Existing code already deterministically recovers preferred cash-flow capex and
  cash_end rows, but operating/investing/financing totals can remain null when
  the LLM omits them.
- Root cause: formal RMS heading is `STATEMENT OF CASH FLOWS`, while the
  statement-text overlay only admitted `consolidatedstatementofcashflows`.

## Remediation Eligibility

Final classification: `IMPLEMENTED_SINGLE_NARROW_FIX`.

The implemented fix only broadens the formal cash-flow statement marker from
`consolidatedstatementofcashflows` to also include `statementofcashflows`.
No gold-label, source-PDF, prompt, model, runtime, or production data mutation
was made.

## Validation Plan

- Focused unit validation: 2 tests passed, 254 deselected.
- Focused no-write replay: `RMS_H_2025-12-31` PASS, 1 accepted case,
  side-effect audit passed.
- Approved-15 scorecard rebuild: four RMS rows changed from
  `missing_expected_metric` to `present_correct`; `missing_expected_metric`
  count dropped from 4 to 0.

## Next Action

Use this fix as the only implementation in this run. Do not add QBE, DXS, or
BHP/MIN changes in this task card.
