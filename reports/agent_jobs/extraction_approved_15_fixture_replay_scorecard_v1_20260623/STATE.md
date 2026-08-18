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
- Accepted payloads: 12.
- Fail-closed payloads: 3.
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
| post-run max timestamp or count | 15 fixture manifest rows, 15 replay cases, 146 metric expectation rows, 12 accepted payloads, 3 fail-closed payloads. |
| rows/files inserted or updated after run start | Report-local artifacts only; production rows/files inserted or updated: 0. |
| readiness/gate status | Scorecard gate remains blocked; pre-persistence promotion is not ready. |
| exact command/query used | `UV_CACHE_DIR=/tmp/tenn-uv-cache-approved15-afterfix2-20260623 REPORT_DIR=reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623 uv run --python 3.10 ... python - <<'PY'` using `scripts/extraction_no_write_replay.py` `_run_cases` over the 15-row fixture manifest; see `validation.json` for the full command family and artifact names. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | The approved 15-fixture scorecard gate still fails with ambiguous, missing, not-evaluated, and wrong-value classes; no production functionality or promotion readiness is proven. |

result: PARTIAL

## Closeout Notes

- PR #401 landed first on `migration/clean-runtime-baseline-reconstruct-v1`.
- The source-proven TCL scale fallback was later published through PR #404.
- Final local report artifacts reflect the after-fix full replay and remain
  blocked for count-24/count-32 purposes.
