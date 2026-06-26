# Validation

## RED

Command:

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_market_data_route_auth.py -q
```

Result: failed as expected before implementation.

Summary: `8 failed, 8 passed`. Failures showed enabled-staging market-data GETs
returned `200` and reached sidecar/persistence spies without the local API key.

## GREEN

Command:

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_market_data_route_auth.py -q
```

Result: passed.

Summary: `16 passed`.

## Additional Checks

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_local_api_key.py -q
```

Result: passed. Summary: `15 passed, 5 warnings`.

```bash
uv run --with ruff ruff check financial-engine_v2/backend/app/api/routes.py financial-engine_v2/backend/tests/test_market_data_route_auth.py
```

Result: passed.

```bash
python3 -m py_compile financial-engine_v2/backend/app/api/routes.py financial-engine_v2/backend/tests/test_market_data_route_auth.py
```

Result: passed.

```bash
git diff --check
```

Result: passed.

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue250_market_data_staging_write_guard_current_base_v1_20260627.md
```

Result: passed.

## Runtime Functionality Proof

Live backend service was not started. This task proves route auth behavior with
FastAPI/TestClient and does not claim live runtime functionality.

| Field | Required evidence |
| --- | --- |
| intended output | Market-data GET routes reject missing or wrong local API keys before OpenBB sidecar refresh or staging persistence when staging writes are enabled. |
| live output location | FastAPI TestClient mounted routes `/api/price`, `/api/fundamentals/profile`, `/api/fundamentals/summary`, and `/api/fundamentals/statements`; live backend service was not started. |
| pre-run max timestamp or count | DATA_MISSING; no live service or runtime store baseline was collected. |
| post-run max timestamp or count | DATA_MISSING; no live service or runtime store was probed after the run. |
| rows/files inserted or updated after run start | 0 runtime rows/files; only source, test, doc, task-card, and report files changed. |
| readiness/gate status | Focused pytest, shared API-key pytest, Ruff, py_compile, diff check, and task-card validation passed; live runtime gate is DATA_MISSING. |
| exact command/query used | `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_market_data_route_auth.py -q` |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | DATA_MISSING |
| remaining blocker | Live backend service was not started or probed; PR CI must also pass before merge. |

- result: DATA_MISSING
