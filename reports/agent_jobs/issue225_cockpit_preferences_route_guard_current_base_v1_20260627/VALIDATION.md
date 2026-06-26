# Validation

## RED

Command:

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_api_preferences.py financial-engine_v2/backend/tests/test_local_api_key.py -q
```

Result: exit 1. Expected RED after tests were corrected to use valid runtime
target values.

Summary:

- 3 failed, 20 passed, 5 warnings.
- Missing/wrong-key preference PATCH returned `200` instead of `401`.
- `PATCH /api/cockpit/preferences` did not register `require_api_key`.

## GREEN

Command:

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_api_preferences.py financial-engine_v2/backend/tests/test_local_api_key.py -q
```

Result: exit 0, `23 passed, 5 warnings`.

## Static Checks

Command:

```bash
uv run --with ruff ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_preferences.py financial-engine_v2/backend/tests/test_local_api_key.py
```

Result: exit 0, all checks passed.

Command:

```bash
python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_preferences.py financial-engine_v2/backend/tests/test_local_api_key.py
```

Result: exit 0.

Command:

```bash
git diff --check
```

Result: exit 0.

## Frontend Test Gap

Command:

```bash
if [ -x cockpit-ui/node_modules/.bin/vitest ]; then (cd cockpit-ui && ./node_modules/.bin/vitest run lib/api-client.test.ts); else echo 'vitest executable missing: cockpit-ui/node_modules/.bin/vitest'; fi
```

Result: exit 0 with message
`vitest executable missing: cockpit-ui/node_modules/.bin/vitest`.

No dependency install was performed because this safe-extension lane does not
allow broad dependency mutation.

## Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | `PATCH /api/cockpit/preferences` rejects missing/wrong `X-API-Key` before mutating Cockpit routing preferences and accepts a matching key when `settings.local_api_key` is configured. |
| live output location | In-process FastAPI TestClient route `/api/cockpit/preferences`; deployed/live Cockpit backend listener was not probed. |
| pre-run max timestamp or count | RED focused pytest after adding tests: 3 failed, 20 passed, 5 warnings; missing/wrong-key PATCH returned `200` and route dependency registration was absent. |
| post-run max timestamp or count | GREEN focused pytest after implementation: 23 passed, 5 warnings. |
| rows/files inserted or updated after run start | In TestClient denial cases, `fake_service.state_store.get_preferences()` remained `{}`; no production rows/files were inserted or updated. |
| readiness/gate status | Local backend route gate passed; frontend Vitest gate is `DATA_MISSING` because `cockpit-ui/node_modules/.bin/vitest` is absent; GitHub PR checks pending until PR creation. |
| exact command/query used | `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_api_preferences.py financial-engine_v2/backend/tests/test_local_api_key.py -q` |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | No live deployed route probe and no local Vitest execution because frontend dependencies are missing; PR checks must confirm full repository gate. |

result: PARTIAL
