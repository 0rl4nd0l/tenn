# Validation

## RED

Command:

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_chat_route.py financial-engine_v2/backend/tests/test_local_api_key.py -q
```

Result: failed as expected before implementation.

Summary: `20 failed, 22 passed, 5 warnings`. Failures showed `/chat` and
`/api/chat` had no API-key dependency and missing/wrong keys returned `200`
instead of `401`.

## GREEN

Command:

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_chat_route.py financial-engine_v2/backend/tests/test_local_api_key.py -q
```

Result: passed.

Summary: `42 passed, 5 warnings`.

## Static And Contract Checks

```bash
uv run --with ruff ruff check financial-engine_v2/backend/app/routes/chat.py financial-engine_v2/backend/tests/test_chat_route.py financial-engine_v2/backend/tests/test_local_api_key.py
```

Result: passed.

```bash
python3 -m py_compile financial-engine_v2/backend/app/routes/chat.py financial-engine_v2/backend/tests/test_chat_route.py financial-engine_v2/backend/tests/test_local_api_key.py
```

Result: passed.

```bash
git diff --check
```

Result: passed.

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue249_legacy_chat_route_guard_current_base_v1_20260627.md
```

Result: passed.

## Runtime Proof

Live backend service was not started. This task proves route auth behavior with
FastAPI/TestClient and does not claim live runtime functionality.

| Field | Required evidence |
| --- | --- |
| intended output | Legacy `POST /chat` and `POST /api/chat` reject missing or wrong local API keys before analysis or strategy side effects. |
| live output location | FastAPI TestClient mounted routes `/chat` and `/api/chat`; live backend service was not started. |
| pre-run max timestamp or count | DATA_MISSING; no live service or runtime store baseline was collected. |
| post-run max timestamp or count | DATA_MISSING; no live service or runtime store was probed after the run. |
| rows/files inserted or updated after run start | 0 runtime rows/files; only source, test, doc, task-card, and report files changed. |
| readiness/gate status | Focused pytest, Ruff, py_compile, diff check, and task-card validation passed; live runtime gate is DATA_MISSING. |
| exact command/query used | `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_chat_route.py financial-engine_v2/backend/tests/test_local_api_key.py -q` |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | DATA_MISSING |
| remaining blocker | Live backend service was not started or probed; PR CI must also pass before merge. |

- result: DATA_MISSING
