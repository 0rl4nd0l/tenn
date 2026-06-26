# Issue 226 Personal Portfolio Route Guard

Closeout status: DONE_WITH_RISK

Issue #226 asked for direct backend protection on Cockpit local personal
portfolio surfaces. This lane added the existing `require_api_key` dependency to
the direct `/api/cockpit/watchlist` and `/api/cockpit/holdings` read/write
routes, added RED/GREEN backend coverage for denial and authenticated behavior,
and documented the route contract.

Draft PR: https://github.com/0rl4nd0l/tenn/pull/444

## Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | Direct backend requests to `/api/cockpit/watchlist*` and `/api/cockpit/holdings*` deny missing or wrong `X-API-Key` when `settings.local_api_key` is configured, without changing authenticated CRUD behavior. |
| live output location | Local FastAPI `TestClient` route responses and temporary Cockpit `StateStore` contents in focused backend tests; no live deployed backend was started or probed. |
| pre-run max timestamp or count | RED focused pytest: 21 failed, 41 passed. Missing or wrong keys returned normal route responses such as 200/409, and route-registration checks found no API-key dependency on the seven target routes. |
| post-run max timestamp or count | GREEN focused pytest: 62 passed, 5 warnings. Route-registration checks and missing/wrong-key denial tests now pass. |
| rows/files inserted or updated after run start | Denied test requests inserted or updated 0 holdings/watchlist rows; existing BHP watchlist/holding rows remained present and unchanged. Code/docs/tests/report files changed only under the task-card allowlist. |
| readiness/gate status | Local route guard gate passed; task-card, ledger, registry, Ruff, py_compile, and diff checks passed. Draft PR #444 is open; live deployment/API probe and PR checks are pending. |
| exact command/query used | `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_api_watchlist.py financial-engine_v2/backend/tests/test_cockpit_api_holdings.py financial-engine_v2/backend/tests/test_local_api_key.py -q` |
| result: PARTIAL | Local code behavior is proven by focused tests, but the route guard is not proven on a live deployed backend and the PR is not merged. |
| remaining blocker | Make PR #444 ready for review, wait for green checks, merge/deploy after approval, and run a live backend route probe with configured `LOCAL_API_KEY` before claiming WORKING. |

## Files Touched

- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_watchlist.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_holdings.py`
- `financial-engine_v2/backend/tests/test_local_api_key.py`
- `docs/architecture/19_backend_api_surface.md`
- `docs/agent_tasks/issue226_personal_portfolio_route_guard_current_base_v1_20260627.md`
- `reports/agent_jobs/issue226_personal_portfolio_route_guard_current_base_v1_20260627/*`

## Unsafe Actions Avoided

- No production DB, Qdrant, Redis, news store, source PDF, extraction output,
  prompt, runtime, model, GPU, or service state was mutated.
- No frontend behavior was changed; current Cockpit browser paths already send
  `X-API-Key`.
- No merge, rebase, reset, stash, branch deletion, or issue closure was
  performed.
