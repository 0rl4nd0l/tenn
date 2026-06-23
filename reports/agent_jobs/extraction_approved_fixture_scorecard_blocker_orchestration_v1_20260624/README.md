# Approved Fixture Scorecard Blocker Orchestration v1

## Result

Status: PARTIAL / DONE_WITH_RISK. The source-proven scored extraction errors were fixed, but the #97 gate remains blocked by policy/gold-review classes outside this safe extension.

Final replay: 12 accepted, 0 failed, 3 fail-closed, side-effect audit passed. Runtime: 1829.298s.

Final scorecard: {'ambiguous_quarantined': 73, 'missing_evidence': 0, 'missing_expected_metric': 0, 'not_evaluated_no_actual_payload': 16, 'present_correct': 57, 'present_wrong_value': 0, 'unsupported_correctly_abstained': 0, 'wrong_period': 0, 'wrong_unit_currency_scale': 0}

Evaluation counts: {'exact': 39, 'tolerated': 5, 'missing': 0, 'null': 13, 'wrong': 0, 'abstain': 0, 'unsupported': 0, 'quarantine': 73, 'missing_evidence': 0, 'wrong_period': 0, 'wrong_unit_currency_scale': 0, 'not_evaluated_no_actual': 16}

Top blocker: ambiguous_quarantined=73. Secondary blocker: not_evaluated_no_actual_payload=16 from fail-closed ANZ, DXS, and SEG payloads.

Count-24 justified: no. The scorecard gate is still fail / blocked.

## Before / After

Before current orchestration: {'ambiguous_quarantined': 73, 'missing_evidence': 0, 'missing_expected_metric': 4, 'not_evaluated_no_actual_payload': 16, 'present_correct': 49, 'present_wrong_value': 4, 'unsupported_correctly_abstained': 0, 'wrong_period': 0, 'wrong_unit_currency_scale': 0}

After current orchestration: {'ambiguous_quarantined': 73, 'missing_evidence': 0, 'missing_expected_metric': 0, 'not_evaluated_no_actual_payload': 16, 'present_correct': 57, 'present_wrong_value': 0, 'unsupported_correctly_abstained': 0, 'wrong_period': 0, 'wrong_unit_currency_scale': 0}

## Source-Proven Fixes

- BHP cash_end: page 46 ending cash row, not net increase/decrease cash movement.
- BHP shares_outstanding: page 53 dual-listed ordinary shares on issue prose, not weighted-average EPS rows or provision prose.
- MIN EBIT/NPAT: formal profit-from-operations and equity-holders-of-parent rows.
- QBE/RMS capex: exact PP&E rows, with mine-development rows rejected for PPE-only capex.
- EQR/GRE Appendix 5B: current-quarter section totals recovered from section summary rows.
- QBE/RMS shares: number-of-shares table evidence preferred over dollar balance/equity rows.

See `source_inspection.json` for row-level evidence.

## Runtime Functionality Proof

result: PARTIAL

| Field | Required evidence |
| --- | --- |
| intended output | Report-local current approved-15 actual payloads and #97 extracted-payload scorecard |
| live output location | `reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/replay_results_after_fix.json`, `scorecard_after_fix.json`, `scorecard_gate_after_fix.json` |
| pre-run max timestamp or count | Prior report scorecard had missing_expected_metric=4 and present_wrong_value=4; current run started after focused BHP smoke |
| post-run max timestamp or count | Final scorecard has missing_expected_metric=0 and present_wrong_value=0; present_correct=57 |
| rows/files inserted or updated after run start | Report-local artifacts updated; canonical DB/cache/source/gold unchanged; side_effect_pass=true |
| readiness/gate status | scorecard gate=fail; decision=blocked |
| exact command/query used | See `validation.json` command list and `raw_replay_after_fix/input_manifest.json` |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | ambiguous_quarantined=73 and not_evaluated_no_actual_payload=16 from fail-closed ANZ/DXS/SEG |

## Artifacts

- `BOARD.md`, `BOARD_DECISION.json`, `NEXT_GOAL.md`
- `replay_results_after_fix.json`
- `scorecard_after_fix.json`
- `scorecard_gate_after_fix.json`
- `failure_classes_after_fix.json`
- `source_inspection.json`
- `validation.json`
- `raw_replay_after_fix/`
