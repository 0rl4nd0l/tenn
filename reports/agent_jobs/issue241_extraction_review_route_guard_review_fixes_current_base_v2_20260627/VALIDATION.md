# Validation

## Passed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue241_extraction_review_route_guard_review_fixes_current_base_v2_20260627.md`
  - Result: `ok: true`
- Review-fix validation:
  - `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_backend_api_client_context.py financial-engine_v2/backend/tests/test_extraction_review_route_auth.py financial-engine_v2/backend/tests/test_extraction_review_service.py`
  - Result: `55 passed`
  - `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt ruff check financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_backend_api_client_context.py`
  - Result: `All checks passed!`
  - `PYTHONPATH=financial-engine_v2/backend python3 -m py_compile financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_backend_api_client_context.py`
  - Result: exit 0
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_extraction_review_route_auth.py financial-engine_v2/backend/tests/test_extraction_review_service.py`
  - Result: `34 passed`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt ruff check financial-engine_v2/backend/app/api/extraction_review.py financial-engine_v2/backend/tests/test_extraction_review_route_auth.py`
  - Result: `All checks passed!`
- `python3 -m py_compile financial-engine_v2/backend/app/api/extraction_review.py financial-engine_v2/backend/tests/test_extraction_review_route_auth.py`
  - Result: exit 0
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue241_extraction_review_route_guard_review_fixes_current_base_v2_20260627.md --repo-root .`
  - Result: `ok: true`
- `git diff --check`
  - Result: exit 0
- `python3 scripts/agent_task_ledger.py validate`
  - Result: `ok: true`

## Blocked

- `pnpm --dir cockpit-ui exec vitest run lib/api-client.test.ts`
  - Result: blocked locally, `Command "vitest" not found`
  - No dependency installation was performed.

## Runtime Functionality

Status: `PARTIAL`

No live backend service or browser session was started. The focused TestClient
tests prove the guarded backend route contract in-process, and API-client
regressions are present but could not be executed locally because Vitest is
unavailable.
