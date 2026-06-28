# Issue 249 Legacy Chat Route Auth Guard

Status: DONE_WITH_RISK

## Scope

Issue #249 covers the legacy chat router mounted at `POST /chat` and
`POST /api/chat`. The goal is to reject missing or wrong local API keys before
analysis-mode model/session side effects or strategy-controller writes can run.

## Files Changed

- `financial-engine_v2/backend/app/api/auth.py`
- `financial-engine_v2/backend/app/api/routes.py`
- `financial-engine_v2/backend/app/routes/chat.py`
- `financial-engine_v2/backend/tests/test_chat_route.py`
- `financial-engine_v2/backend/tests/test_local_api_key.py`
- `docs/agent_tasks/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628.md`
- `reports/agent_jobs/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628/`

## Result

- Moved the existing `require_api_key` helper into lightweight
  `app.api.auth`, while preserving `app.api.routes.require_api_key` for current
  importers and tests.
- Added `dependencies=[Depends(require_api_key)]` to the legacy chat route.
- Added focused tests for both `/chat` and `/api/chat` proving missing or wrong
  keys reject before `chat_with_tenn`, `record_turn`, `propose_change`,
  `confirm_change`, or `apply_change` can run.
- Added a matching-key analysis test proving the guarded route still calls
  legacy analysis behavior.
- Added route registration coverage for both legacy mounts.

## Runtime Functionality Proof

| Field | Evidence |
| --- | --- |
| intended output | Configured-key requests to `POST /chat` and `POST /api/chat` without the correct `X-API-Key` are rejected before model/session/strategy side effects. |
| live output location | FastAPI TestClient routes `POST /chat` and `POST /api/chat` from `financial-engine_v2/backend/tests/test_chat_route.py`. |
| pre-run max timestamp or count | DATA_MISSING; no live backend service baseline was started or queried. |
| post-run max timestamp or count | 13 focused chat-route tests passed; 5 targeted local-api-key tests passed. |
| rows/files inserted or updated after run start | 5 source/test files updated after run start; no data rows inserted or updated. |
| readiness/gate status | Focused route behavior passed in TestClient; full local `test_local_api_key.py` remains environment-limited by optional Cockpit route imports in the lightweight validation env. |
| exact command/query used | `PYTHONPATH=financial-engine_v2/backend uv run --with pytest ... python -m pytest financial-engine_v2/backend/tests/test_chat_route.py -q` and `... test_local_api_key.py -q -k 'chat or require_api_key'`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | No live backend service proof was run; full local `test_local_api_key.py` failed on pre-existing optional route omissions in the lightweight env. |

result: PARTIAL

## Boundaries

- No route removal, deprecation, broad chat ownership change, source/evidence
  envelope change, production data access, DB/Qdrant/Redis/news/memory write,
  extraction/prompt/parser/gold-label change, package/lockfile change, or
  service/runtime mutation.
