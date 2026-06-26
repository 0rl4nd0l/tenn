# Validation

## Passed

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue242_context_diagnostics_review_fixes_current_base_v1_20260627.md
```

Result: `PASS`

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py financial-engine_v2/backend/tests/test_context_endpoints.py financial-engine_v2/backend/tests/test_backend_api_client_context.py
```

Result: `PASS`, 68 passed.

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt ruff check financial-engine_v2/backend/app/api/context.py financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py financial-engine_v2/backend/tests/test_backend_api_client_context.py
```

Result: `PASS`

```bash
python3 -m py_compile financial-engine_v2/backend/app/api/context.py financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py financial-engine_v2/backend/tests/test_backend_api_client_context.py
```

Result: `PASS`

## Blocked

```bash
pnpm --dir cockpit-ui exec vitest run lib/api-client.test.ts
```

Result: `BLOCKED`

Output:

```text
undefined
ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL Command "vitest" not found
```

## Pending Final Checks

- `python3 -m json.tool reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v1_20260627/status.json`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue242_context_diagnostics_review_fixes_current_base_v1_20260627.md --repo-root .`
- `git diff --check`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
