# Approved 15-Fixture Replay Scorecard State

- status: DONE_WITH_RISK
- branch: safe/extraction-approved-15-fixture-replay-scorecard-v1-20260623
- base: origin/migration/clean-runtime-baseline-reconstruct-v1
- head_before_commit: c4eab101bf749fb8d9b148390cc53b002eb1f2b9
- task_scope: safe_execution
- mutation_mode: safe_extension
- production_data_access: false
- docs_impact: DOCS_NOT_REQUIRED

## Current Results

- Fixture manifest: 15 fixtures, 15 resolved.
- No-write replay: PARTIAL.
- Accepted payloads: 11.
- Fail-closed payloads: 4.
- Failed payloads: 0.
- #97 scorecard gate: fail / blocked.
- Blocking result classes: ambiguous_quarantined=73,
  not_evaluated_no_actual_payload=16, missing_expected_metric=4,
  present_wrong_value=4.
- Current scorecard result classes match the before-fix scorecard; no count-24
  or count-32 claim is made.

## Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | Report-local approved 15-fixture replay artifacts, #97 scorecard artifacts, and a bounded TCL source-scale recovery check. |
| live output location | `reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/`; no production DB/API/store output targeted. |
| pre-run max timestamp or count | DATA_MISSING; no live production output baseline was captured because this was a no-write replay/report-local safe extension. |
| post-run max timestamp or count | 15 fixture manifest rows, 15 replay cases, 146 metric expectation rows, 11 accepted payloads, 4 fail-closed payloads. |
| rows/files inserted or updated after run start | Report-local artifacts only; production rows/files inserted or updated: 0. |
| readiness/gate status | Scorecard gate remains blocked; pre-persistence promotion is not ready. |
| exact command/query used | `python3 scripts/run_pytest_with_fallback.py --base-python /usr/bin/python3 --overlay-package 'pytest>=8.3.3,<10' --overlay-package 'pytest-asyncio>=0.24.0,<2' --overlay-package 'respx>=0.23.1,<0.24' --overlay-package 'python-dateutil==2.9.0.post0' --overlay-package 'pydantic==2.9.2' --overlay-package 'pydantic-settings==2.6.1' --overlay-package 'pymupdf==1.24.10' --overlay-package 'SQLAlchemy==2.0.36' --overlay-package 'beautifulsoup4==4.12.3' --overlay-package 'qdrant-client==1.12.1' -- financial-engine_v2/backend/tests/test_multipass_extraction.py -q` |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | The approved 15-fixture scorecard gate still fails with ambiguous, missing, not-evaluated, and wrong-value classes; no production functionality or promotion readiness is proven. |

result: PARTIAL

## Merge Gate Notes

- Owner approved GitHub mutation for this merge gate on 2026-06-23 with
  `merge if safe`.
- Merge is only safe after task-card validation, report-artifact validation,
  diff allowlist, focused/full extractor tests, lint, GitHub checks, and live
  PR mergeability all pass.
