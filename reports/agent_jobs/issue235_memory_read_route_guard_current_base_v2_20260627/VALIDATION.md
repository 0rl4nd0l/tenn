# Validation

## Passed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue235_memory_read_route_guard_current_base_v2_20260627.md`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue235_memory_read_route_guard_current_base_v2_20260627.md --repo-root . --no-write-report`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_memory_read_route_auth.py financial-engine_v2/backend/tests/test_backend_api_client_context.py`
  - result: `41 passed`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt ruff check financial-engine_v2/backend/app/api/context.py financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_memory_read_route_auth.py financial-engine_v2/backend/tests/test_backend_api_client_context.py`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m py_compile financial-engine_v2/backend/app/api/context.py financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_memory_read_route_auth.py financial-engine_v2/backend/tests/test_backend_api_client_context.py`
- `git diff --check`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`

## Pending

- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue235_memory_read_route_guard_current_base_v2_20260627.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/issue235_memory_read_route_guard_current_base_v2_20260627.md --repo-root .`
- GitHub checks and fresh review after the replacement PR is opened.
