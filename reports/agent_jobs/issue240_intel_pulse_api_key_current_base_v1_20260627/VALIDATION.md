# Validation

## Passed

- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_cockpit_intel_pulse_route_auth.py`
  - Result: `39 passed, 5 warnings`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_intel_pulse_route_auth.py financial-engine_v2/backend/tests/test_local_api_key.py`
  - Result: `All checks passed!`
- `python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_intel_pulse_route_auth.py financial-engine_v2/backend/tests/test_local_api_key.py`
  - Result: exit 0
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue240_intel_pulse_api_key_current_base_v1_20260627.md`
  - Result: `ok: true`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue240_intel_pulse_api_key_current_base_v1_20260627.md --repo-root .`
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
and API-client tests prove the guarded route contract in-process, but they do
not prove live deployed cockpit functionality.
