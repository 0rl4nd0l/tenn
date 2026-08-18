## Summary

- Guard `GET /api/cockpit/docs` with the existing local API-key dependency.
- Keep the authenticated document-history payload unchanged, including `pdf_path`.
- Make Cockpit `listDocuments()` send the configured `X-API-Key`.
- Add backend route-auth coverage and API-client header coverage.
- Update the backend API surface doc for the guarded route contract.

Closes #239.

## Validation

- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_docs_route_auth.py financial-engine_v2/backend/tests/test_local_api_key.py -q`
  - red before implementation: 2 failed, 15 passed, 5 warnings
  - green after implementation: 17 passed, 5 warnings
- `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_cockpit_docs_route_auth.py`
- `python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_cockpit_docs_route_auth.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_document_history_route_guard_current_base_v1_20260627.md`

## Local Frontend Validation

- Blocked locally: `cockpit-ui/node_modules/.bin/vitest` is missing.
- No dependency install was performed and no lockfiles were changed.

## Runtime Proof

Runtime functionality proof is `PARTIAL`: focused backend route tests pass, but
no live backend/browser runtime was started and local frontend execution is
blocked by missing frontend dependencies.
