# Validation

## Commands

See `validation/commands.log` for the command transcript.

Key checks:

- Focused unit validation:
  `uv run --isolated --with python-dateutil --with pydantic-settings --with 'pytest>=8.3.3' --with 'pytest-asyncio>=0.24.0' --env-file /dev/null python -m pytest -q financial-engine_v2/backend/tests/test_multipass_extraction.py -k "statement_text_overlay_recovers_rms_statement_of_cash_flows_heading or statement_text_overlay_recovers_fragmented_full_statements_over_wrapper"`
  -> `2 passed, 254 deselected`.
- Focused no-write RMS replay:
  report-local selected-case harness over prior approved-15 input manifest
  -> `PASS`, one RMS case accepted, side-effect audit passed.
- Scorecard rebuild:
  `missing_expected_metric` dropped from 4 to 0; gate still failed because
  `ambiguous_quarantined=73`, `not_evaluated_no_actual_payload=18`, and
  `present_wrong_value=2`.
- Contract checks:
  `git diff --check`, task-card `validate`, task-card `check-diff`,
  `check-report-artifacts`, and `check-closeout` passed.

## Functionality Proof

result: PARTIAL

| Field | Required evidence |
| --- | --- |
| intended output | Report-local approved-15 no-write extraction evidence and one narrow RMS extractor behavior improvement. |
| live output location | `reports/agent_jobs/extraction_approved15_blocker_lanes_v1_20260629/*`; no production DB/API/queue/store surface was written or checked for fresh rows. |
| pre-run max timestamp or count | Prior post-PR #461 scorecard: 12 actual payload docs; `missing_expected_metric=4`; gate failed. |
| post-run max timestamp or count | New scorecard: 12 actual payload docs; `missing_expected_metric=0`; gate still failed. |
| rows/files inserted or updated after run start | 0 production rows; report-local artifacts plus tracked code/test/task-card changes only. |
| readiness/gate status | `scorecard_gate_after_fix.json`: `gate_status=fail`, `decision=blocked`. |
| exact command/query used | Focused pytest, report-local focused RMS replay, and scorecard rebuild commands in `validation/commands.log`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | QBE and DXS no-actual-payload rows, BHP/MIN wrong-value rows, and ambiguous quarantine policy/source-evidence rows. |

## Validation Risk

The replay required an isolated full backend environment under
`/tmp/tenn-uv-cache-approved15-blocker-lanes-v1-20260629`; this did not modify
repo dependency files but did populate a temporary package cache.

## Publish Check

`gh auth status` failed because the saved GitHub token is no longer valid.
Local commit can proceed, but push and PR creation require refreshed GitHub
authentication.
