# Validation

## Passed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue242_context_diagnostics_review_fixes_current_base_v2_20260627.md`
  - exit 0
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py financial-engine_v2/backend/tests/test_context_endpoints.py financial-engine_v2/backend/tests/test_backend_api_client_context.py`
  - exit 0
  - `70 passed in 3.35s`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt ruff check financial-engine_v2/backend/app/api/context.py financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py financial-engine_v2/backend/tests/test_backend_api_client_context.py`
  - exit 0
  - `All checks passed!`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python3 -m py_compile financial-engine_v2/backend/app/api/context.py financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py financial-engine_v2/backend/tests/test_backend_api_client_context.py`
  - exit 0
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue242_context_diagnostics_review_fixes_current_base_v2_20260627.md --repo-root .`
  - exit 0
- `git diff --check`
  - exit 0
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
  - exit 0

## Blocked

- `vitest run cockpit-ui/lib/api-client.test.ts`
  - exit 127
  - `Command "vitest" not found`

## Not Run

- Live backend/API smoke.
- Browser UI smoke.

These were not run because this task stayed inside the approved code/test/report
scope and did not start services or mutate runtime state.
