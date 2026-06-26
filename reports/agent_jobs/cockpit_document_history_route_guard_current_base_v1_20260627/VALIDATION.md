# Validation

## Commands

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_document_history_route_guard_current_base_v1_20260627.md`
  - result: passed
- `python3 scripts/agent_job_registry.py check-overlap --repo-root . docs/agent_tasks/cockpit_document_history_route_guard_current_base_v1_20260627.md`
  - result: passed; no active overlap
- `python3 scripts/agent_job_registry.py claim --repo-root . docs/agent_tasks/cockpit_document_history_route_guard_current_base_v1_20260627.md`
  - result: passed
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
  - result: passed before implementation
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_docs_route_auth.py financial-engine_v2/backend/tests/test_local_api_key.py -q`
  - red result before implementation: 2 failed, 15 passed, 5 warnings
  - green result after implementation: 17 passed, 5 warnings
- `test -x cockpit-ui/node_modules/.bin/vitest`
  - result: failed; `vitest missing at cockpit-ui/node_modules/.bin/vitest`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_cockpit_docs_route_auth.py`
  - result: passed
- `python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_cockpit_docs_route_auth.py`
  - result: passed
- `git diff --check`
  - result: passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_document_history_route_guard_current_base_v1_20260627.md`
  - result: passed; no disallowed files
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/cockpit_document_history_route_guard_current_base_v1_20260627.md`
  - result: passed
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
  - result: passed after ledger append; no issues

## Not Run

- result: `PARTIAL`
- Local frontend Vitest did not run because `cockpit-ui/node_modules/.bin/vitest` is missing.
- No project dependencies or lockfiles were changed.
- Live backend/browser runtime smoke was not run.
- DB, Qdrant, Redis, news stores, memory stores, source PDFs, extraction outputs,
  prompts, gold labels, runtime/model/GPU/service config, and production data
  were not mutated.
