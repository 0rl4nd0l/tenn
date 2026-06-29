# Validation

## Passed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628.md`
  - Result: passed.
- `PYTHONPATH=financial-engine_v2/backend uv run --with pytest --with fastapi==0.115.6 --with pydantic==2.9.2 --with pydantic-settings==2.6.1 --with sqlalchemy==2.0.36 --with httpx==0.27.2 --with numpy==1.26.4 --with rank-bm25==0.2.2 --with qdrant-client==1.12.1 --with python-dateutil==2.9.0.post0 python -m pytest financial-engine_v2/backend/tests/test_chat_route.py -q`
  - Result: 13 passed, 1 warning.
- `PYTHONPATH=financial-engine_v2/backend uv run --with pytest --with fastapi==0.115.6 --with pydantic==2.9.2 --with pydantic-settings==2.6.1 --with sqlalchemy==2.0.36 --with httpx==0.27.2 --with numpy==1.26.4 --with rank-bm25==0.2.2 --with qdrant-client==1.12.1 --with python-dateutil==2.9.0.post0 --with celery==5.4.0 --with pymupdf==1.24.10 --with beautifulsoup4==4.12.3 --with lxml==5.3.0 python -m pytest financial-engine_v2/backend/tests/test_local_api_key.py -q -k 'chat or require_api_key'`
  - Result: 5 passed, 32 deselected, 6 warnings.
- `uv run --with ruff ruff check financial-engine_v2/backend/app/api/auth.py financial-engine_v2/backend/app/api/routes.py financial-engine_v2/backend/app/routes/chat.py financial-engine_v2/backend/tests/test_chat_route.py financial-engine_v2/backend/tests/test_local_api_key.py`
  - Result: passed.
- `python3 -m py_compile financial-engine_v2/backend/app/api/auth.py financial-engine_v2/backend/app/api/routes.py financial-engine_v2/backend/app/routes/chat.py financial-engine_v2/backend/tests/test_chat_route.py financial-engine_v2/backend/tests/test_local_api_key.py`
  - Result: passed.
- `git diff --check`
  - Result: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628.md --repo-root .`
  - Result: passed. `disallowed_files: []`.
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
  - Result: passed.

## Partial / Environment-Limited

- Full `test_local_api_key.py` was run in a lightweight ephemeral dependency
  environment after adding declared import dependencies through `uv --with`.
  Result: 20 passed, 17 failed.
- The failures were all `route not found` assertions for pre-existing optional
  Cockpit/marketplace routes that were not mounted in this lightweight local
  environment. The new `/chat` and `/api/chat` route-registration rows passed
  under the targeted `-k 'chat or require_api_key'` run.

## Validation Status

DONE_WITH_RISK: focused acceptance tests and static checks passed; full local
route-registry file remains environment-limited outside CI/full backend deps.
