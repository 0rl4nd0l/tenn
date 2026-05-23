# Validation

## Completed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521.md`
  - Result: passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521.md`
  - Result: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521.md`
  - Result: passed.
- `python3 financial-engine_v2/scripts/test_strategy_lab_artifact_schema.py`
  - Result: `Ran 6 tests in 0.001s` / `OK`.
- `PYTHONDONTWRITEBYTECODE=1 python3 financial-engine_v2/scripts/test_strategy_lab_artifact_schema.py`
  - Result: `Ran 6 tests in 0.001s` / `OK`.
- `jq empty` on copied raw summaries, normalized artifacts, and `status.json`
  - Result: passed.
- `git diff --check`
  - Result: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521.md`
  - Result: passed; `disallowed_files=[]`.
- `python3 scripts/agent_job_registry.py release strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521`
  - Result: passed; registry status is `released`.
- `python3 scripts/agent_job_registry.py list-active`
  - Result: `active_jobs=[]`.
- Final residue check:
  - no `__pycache__` files remain under `financial-engine_v2`.
  - no listeners or Docker containers matched QuantDinger sandbox ports `15080`, `15432`, or `16379`.
- Generated normalized artifacts:
  - `normalized_artifacts/backtest_run.json`
  - `normalized_artifacts/regime_breakdown.json`

## Final Git Status

`git status --short --untracked-files=all` shows only allowed untracked files:

- `docs/agent_tasks/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521.md`
- `docs/strategy_lab_quantdinger_artifact_schema.md`
- `financial-engine_v2/backend/app/services/strategy_lab_artifact_schema.py`
- `financial-engine_v2/scripts/fixtures/strategy_lab_artifact_schema/quantdinger_phase1_backtest_summary.json`
- `financial-engine_v2/scripts/fixtures/strategy_lab_artifact_schema/quantdinger_phase1_regime_summary.json`
- `financial-engine_v2/scripts/test_strategy_lab_artifact_schema.py`

`git status --short --ignored reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521` shows the ignored report bundle at:

- `reports/agent_jobs/strategy_lab_quantdinger_phase2_artifact_schema_v1_20260521/`
