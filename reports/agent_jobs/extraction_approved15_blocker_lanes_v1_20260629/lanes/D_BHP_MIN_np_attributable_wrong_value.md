# Lane D - BHP/MIN NP Attributable Wrong-Value Audit

Status: PARK_NEXT_SOURCE_PROVEN_FIX_CANDIDATE

## Source Evidence

- BHP fixture:
  `financial-engine_v2/backend/tests/eval_fixtures/BHP_A_2021-06-30.json`.
- MIN fixture:
  `financial-engine_v2/backend/tests/eval_fixtures/MIN_H_2025-12-31.json`.
- BHP expected `np_attributable=11304000000`, row "Attributable to BHP
  shareholders".
- MIN expected `np_attributable=495000000`, row "Equity holders of the parent".

## Failure Lineage

- Prior replay accepted both BHP and MIN actual payloads.
- Scorecard class: `present_wrong_value`, count 2.
- Current actual BHP value is `3451000000`, sourced from
  "Profit after taxation from Continuing operations".
- Current actual MIN value is `573000000`, sourced from
  "PROFIT/(LOSS) AFTER TAX FOR THE HALF-YEAR" instead of the owner-attributable
  row.
- Read-only scout confirmed owner-row recognizers already exist, but generic
  after-tax rows can outrank or survive over explicit owner-attributable rows.

## Remediation Eligibility

Final classification: `ELIGIBLE_BUT_NOT_SELECTED`.

This lane needs row-level source audit before any fix. It likely involves
owner-attributable row precedence, which could be valuable but broader than RMS
cash-flow recovery.

## Validation Plan

- If selected, focused unit tests for owner-attributable row precedence in BHP
  and MIN-style statements.
- No-write replay for both `BHP_A_2021-06-30` and `MIN_H_2025-12-31`.
- Approved-15 scorecard/gate rebuild.

## Next Action

Open a separate narrow fix lane for owner-attributable row precedence and
replacement, with BHP and MIN focused tests plus focused replays.
