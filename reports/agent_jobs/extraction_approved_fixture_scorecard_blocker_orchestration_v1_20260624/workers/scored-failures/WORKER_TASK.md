# Worker Task

            worker_id: scored-failures
            source_task_file: reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/workers/scored-failures-task.md

            ## Task

            # Worker Task: Scored Failure Evidence

worker_id: scored-failures
task_tier: small
decision_limit: evidence_only

Inspect the current approved-fixture scorecard hard failures only:

- `missing_expected_metric`
- `present_wrong_value`

Use only these evidence surfaces:

- `reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/failure_rows.json`
- `reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/scorecard.json`
- `reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/replay_results.json`
- `financial-engine_v2/backend/tests/eval_fixtures/BHP_A_2021-06-30.json`
- `financial-engine_v2/backend/tests/eval_fixtures/MIN_H_2025-12-31.json`
- `financial-engine_v2/backend/tests/eval_fixtures/QBE_H_2025-06-30.json`
- `financial-engine_v2/backend/tests/eval_fixtures/EQR_Q_2025-12-31.json`
- `financial-engine_v2/backend/tests/eval_fixtures/GRE_Q_2024-12-31.json`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`

Questions to answer:

1. List each missing/wrong metric row with fixture, metric, expected value,
   actual value, support status, and scorecard reason.
2. Identify whether the row is likely parser-fixable, scorecard/gold-review
   only, or DATA_MISSING from the artifacts alone.
3. Identify the smallest source-inspection target for Codex to verify next
   (page/table/row if present in fixture provenance, otherwise fixture/source
   path to inspect).
4. Flag any evidence that suggests broad ontology, prompt, gold-label, DB, or
   source-PDF mutation would be needed.

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

