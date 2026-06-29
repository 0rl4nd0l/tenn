## Summary

Fixes #249.

- Gate legacy `POST /chat` and `POST /api/chat` with the existing local
  `X-API-Key` dependency when `settings.local_api_key` is configured.
- Move `require_api_key` into lightweight `app.api.auth` and preserve the
  existing `app.api.routes.require_api_key` import surface.
- Add focused denial-before-side-effect tests for analysis and strategy modes,
  plus matching-key behavior coverage for both legacy mounts.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628.md`
- `PYTHONPATH=financial-engine_v2/backend uv run --with pytest ... python -m pytest financial-engine_v2/backend/tests/test_chat_route.py -q` -> 13 passed
- `PYTHONPATH=financial-engine_v2/backend uv run --with pytest ... python -m pytest financial-engine_v2/backend/tests/test_local_api_key.py -q -k 'chat or require_api_key'` -> 5 passed, 32 deselected
- `uv run --with ruff ruff check financial-engine_v2/backend/app/api/auth.py financial-engine_v2/backend/app/api/routes.py financial-engine_v2/backend/app/routes/chat.py financial-engine_v2/backend/tests/test_chat_route.py financial-engine_v2/backend/tests/test_local_api_key.py`
- `python3 -m py_compile financial-engine_v2/backend/app/api/auth.py financial-engine_v2/backend/app/api/routes.py financial-engine_v2/backend/app/routes/chat.py financial-engine_v2/backend/tests/test_chat_route.py financial-engine_v2/backend/tests/test_local_api_key.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628.md --repo-root .`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`

Partial local validation:

- Full `test_local_api_key.py` in the lightweight ephemeral env had 20 passed,
  17 failed on pre-existing optional Cockpit/marketplace `route not found`
  assertions. The new chat route rows passed under the targeted run above.

## Scope

No route removal/deprecation, source/evidence-envelope change, runtime/service
mutation, production data access, DB/Qdrant/Redis/news/memory write, package,
or lockfile change.
