# Validation

## Passed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_phase3g_mergeback_v1_20260524.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_phase3g_mergeback_v1_20260524.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/strategy_lab_phase3g_mergeback_v1_20260524.md --repo-root .`
- `git cherry-pick --no-commit 6d8ecff855a8c7f27d5b270bd0ed01473d696ffb`
- `git diff --check`
- `git diff --cached --check`
- Allowlisted existing JSON validation: 62 checked, 0 failed.
- `python3 -m unittest tests.strategy_lab.test_strategy_lab_mocked_adapter_phase3b_reconciled tests.strategy_lab.test_strategy_lab_offline_mock_transport_phase3c -v`: 23 tests passed.

## Not Available

- `python3 -m pytest tests/strategy_lab/test_strategy_lab_mocked_adapter_phase3b_reconciled.py tests/strategy_lab/test_strategy_lab_offline_mock_transport_phase3c.py` failed because `pytest` is not installed in this environment.

## Boundary Proof

- Staged cherry-pick file count before merge-back report files: 151.
- Staged cherry-pick Cockpit path count: 0.
- Staged cherry-pick `financial-engine_v2` path count: 0.
- Shared checkout was inspected read-only and left untouched.
