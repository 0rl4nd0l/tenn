# Validation

## Passed

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue242_context_diagnostics_review_fixes_current_base_v1_20260627.md
```

Result: `PASS`

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py financial-engine_v2/backend/tests/test_context_endpoints.py financial-engine_v2/backend/tests/test_backend_api_client_context.py
```

Result: `PASS`, 69 passed.

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt ruff check financial-engine_v2/backend/app/api/context.py financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py financial-engine_v2/backend/tests/test_backend_api_client_context.py
```

Result: `PASS`

The same pytest and ruff commands were rerun after addressing PR #448 automated
review comments about internal helper calls and announcement-context redaction:
`69 passed` and `All checks passed!`.

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

## GitHub

```bash
git push -u origin safe/issue242-context-diagnostics-review-fixes-current-base-v1-20260627
```

Result: `BLOCKED`

Reason: local hook required repo-venv `ruff` and `pytest`, which are absent.
Focused equivalent validation had already passed through `uv`.

```bash
TENN_ALLOW_MISSING_HOOK_TOOLS=1 git push -u origin safe/issue242-context-diagnostics-review-fixes-current-base-v1-20260627
```

Result: `PASS`

The hook skipped missing local lint/test tools and still ran markdown hygiene.

```bash
gh pr create --repo 0rl4nd0l/tenn --base migration/clean-runtime-baseline-reconstruct-v1 --head safe/issue242-context-diagnostics-review-fixes-current-base-v1-20260627
```

Result: `PASS`, opened PR #448.

## Pending Final Checks

- Live PR #448 GitHub checks.
