## Summary

- Guard `PATCH /api/cockpit/preferences` with the configured local API key.
- Preserve unauthenticated read-only `GET /api/cockpit/preferences`.
- Send `X-API-Key` from the Cockpit preference patch client path.
- Add focused backend and API-client regression coverage plus API-surface docs.

## Validation

- RED focused backend pytest: 3 failed, 20 passed, 5 warnings.
- GREEN focused backend pytest: 23 passed, 5 warnings.
- `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_preferences.py financial-engine_v2/backend/tests/test_local_api_key.py`
- `python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_preferences.py financial-engine_v2/backend/tests/test_local_api_key.py`
- `git diff --check`

## Local Test Gap

- Frontend Vitest was not run because
  `cockpit-ui/node_modules/.bin/vitest` is missing in this worktree.
- No dependency install was performed.

Fixes #225.
