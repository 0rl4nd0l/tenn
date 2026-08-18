# Worker Task: Fail-Closed Fixture Evidence

worker_id: failclosed-fixtures
task_tier: small
decision_limit: evidence_only

Inspect current fail-closed payload blockers from the approved 15-fixture
replay:

- ANZ: accepted-output scale/magnitude revenue ratio risk
- DXS: mixed source scales / payload source scale mismatch / revenue ratio risk
- SEG: wrapper missing disclosure evidence

Use only these evidence surfaces:

- `reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/failure_rows.json`
- `reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/replay_results.json`
- `reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/scorecard.json`
- `financial-engine_v2/backend/tests/eval_fixtures/ANZ_H_2025-03-31.json`
- `financial-engine_v2/backend/tests/eval_fixtures/DXS_H_2025-12-31.json`
- `financial-engine_v2/backend/tests/eval_fixtures/SEG_H_2025-12-31.json`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`

Questions to answer:

1. List each fail-closed fixture with error, non-null metric count, scale,
   currency, and scorecard impact.
2. Classify each as likely parser-fixable, scorecard/gold-review only,
   source-wrapper/evidence issue, or DATA_MISSING from the artifacts alone.
3. Identify the smallest source-inspection target for Codex to verify next.
4. Flag any case that appears unsafe for a narrow fix because it involves
   mixed entity scope, mixed unit scale, candidate-review expectations, or
   missing exact source evidence.

Do not edit files. Do not run git mutation commands. Do not decide final
implementation.

Return the standard worker result fields:

worker_id:
task_tier:
model:
decision_limit:
summary:
findings:
evidence_paths:
confidence:
risks:
recommended_next_action:
stop_condition_hit:
