# State

Status: `DONE_WITH_RISK`

## Current State

Ran one no-extraction saved-artifact fixture replay against the broad-run provenance/risk surface from local commit `deba6e0b7013f04edbf0e89fe9b29384f5ffd0cc`.

Source artifact:

`reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/lbl_replay_summary.json`

Generated artifacts:

- `fixture_broad_run_record.json`
- `fixture_summary.json`
- `fixture_assertions.json`

## Result

- Fixture mode: `saved_artifact_no_extraction`
- Ticker: `LBL`
- Status: `ok`
- Non-null metrics: `7`
- Provenance available metrics: `revenue`, `ebit`, `np_attributable`, `operating_cf`, `investing_cf`, `financing_cf`, `cash_end`
- Provenance missing: none
- `accepted_output_scale_magnitude_risk.accepted_output`: `true`
- Risk level: `none`
- Risk flags: none
- Summary provenance coverage: present and non-empty
- Summary risk flag distribution: present and empty

## Task Ledger

- Live ledger: `DATA_MISSING`
- Committed ledger: `DATA_MISSING`
- Current ledger status: `DATA_MISSING`
- Ledger update result: `DATA_MISSING`
- Duplicate-work classification: `CONTINUE_VALIDATION_OF_LOCAL_COMMIT`

## Residual Risk

- This validates the output contract on one saved artifact only.
- It does not prove broad-run behavior across WHC/HCW/EDU-style risk cases.
- It did not run extraction, by design.
