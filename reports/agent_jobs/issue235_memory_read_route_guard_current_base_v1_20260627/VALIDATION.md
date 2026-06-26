# Validation

## Preflight

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue235-memory-read-route-guard-current-base-v1-20260627 --topic "issue235 memory read route guard current base" --json`: exit 0, `final_decision=pass`, `stop_reimplementation=false`, `path_ownership.classification=VALID_TASK_WORKTREE`.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue235_memory_read_route_guard_current_base_v1_20260627.md`: exit 0.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`: exit 0, active jobs empty before claim.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/issue235_memory_read_route_guard_current_base_v1_20260627.md --repo-root .`: exit 0.
- `python3 scripts/agent_task_ledger.py --repo-root . validate`: exit 0.

## RED

- Command:
  `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_memory_read_route_auth.py -q`
- Exit: 1.
- Result: 9 failed, 8 passed.
- Expected failures: four read routes lacked `require_api_key`, and missing or
  wrong configured API keys reached route work instead of returning 401.

## GREEN

- Command:
  `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_memory_read_route_auth.py -q`
- Exit: 0.
- Result: 17 passed.

## Existing Regression

- Command:
  `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_context_endpoints.py -q`
- Exit: 0.
- Result: 36 passed.

## Static Checks

- `uv run --with ruff ruff check financial-engine_v2/backend/app/api/context.py financial-engine_v2/backend/tests/test_memory_read_route_auth.py`: exit 0, all checks passed.
- `python3 -m py_compile financial-engine_v2/backend/app/api/context.py financial-engine_v2/backend/tests/test_memory_read_route_auth.py`: exit 0.
- `git diff --cached --check`: exit 0.

## Report Gates

- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue235_memory_read_route_guard_current_base_v1_20260627.md --repo-root .`: exit 0, no disallowed files.
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/issue235_memory_read_route_guard_current_base_v1_20260627.md --repo-root .`: exit 0.
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/issue235_memory_read_route_guard_current_base_v1_20260627.md --repo-root .`: exit 0.
- Registry release: exit 0; active record removed and report status updated.
- PR: https://github.com/0rl4nd0l/tenn/pull/439.
