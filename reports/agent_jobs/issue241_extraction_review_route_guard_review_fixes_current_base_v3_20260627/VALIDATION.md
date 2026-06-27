# Validation

## Passed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue241_extraction_review_route_guard_review_fixes_current_base_v3_20260627.md`
  - exit 0
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue241_extraction_review_route_guard_review_fixes_current_base_v3_20260627.md --repo-root .`
  - exit 0
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_backend_api_client_context.py financial-engine_v2/backend/tests/test_extraction_review_route_auth.py financial-engine_v2/backend/tests/test_extraction_review_service.py`
  - exit 0
  - `55 passed in 2.42s`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt ruff check financial-engine_v2/backend/app/api/extraction_review.py financial-engine_v2/backend/tests/test_extraction_review_route_auth.py financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_backend_api_client_context.py`
  - exit 0
  - `All checks passed!`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python3 -m py_compile financial-engine_v2/backend/app/api/extraction_review.py financial-engine_v2/backend/tests/test_extraction_review_route_auth.py financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_backend_api_client_context.py`
  - exit 0
- `git diff --check`
  - exit 0
- `python3 scripts/agent_task_ledger.py validate`
  - exit 0

## Blocked

- `vitest run cockpit-ui/lib/api-client.test.ts`
  - exit 127
  - `Command "vitest" not found`

## Post-Review Fix

Codex review on PR #453 flagged a P2 loading-state collapse in the snippet
image panel. The follow-up fix adds a stable minimum height and in-flow
placeholder for pending guarded blob fetches.

- `git diff --check`
  - exit 0
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue241_extraction_review_route_guard_review_fixes_current_base_v3_20260627.md --repo-root .`
  - exit 0
- `vitest run cockpit-ui/lib/api-client.test.ts`
  - exit 127
  - `Command "vitest" not found`

## Not Run

- Live backend/API smoke.
- Browser UI smoke.

These were not run because this task stayed inside the approved code/test/report
scope and did not start services or mutate runtime state.
