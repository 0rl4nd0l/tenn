## Summary

- Require the existing local API-key dependency on direct Cockpit watchlist and holdings read/write routes.
- Add focused tests for missing/wrong key denial, correct-key CRUD behavior, no state mutation on denial, and route dependency registration.
- Document the local personal-data route contract in the backend API surface docs.

Closes #226.

## Validation

- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_api_watchlist.py financial-engine_v2/backend/tests/test_cockpit_api_holdings.py financial-engine_v2/backend/tests/test_local_api_key.py -q`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_watchlist.py financial-engine_v2/backend/tests/test_cockpit_api_holdings.py financial-engine_v2/backend/tests/test_local_api_key.py`
- `python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_watchlist.py financial-engine_v2/backend/tests/test_cockpit_api_holdings.py financial-engine_v2/backend/tests/test_local_api_key.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue226_personal_portfolio_route_guard_current_base_v1_20260627.md`
- `python3 scripts/agent_task_ledger.py validate`
- `python3 scripts/agent_job_registry.py list-active --read-only`

## Runtime Functionality Proof

- result: PARTIAL
- Local focused tests prove the intended route behavior in FastAPI `TestClient`.
- A live backend route probe was not run, and this branch is not merged yet.
