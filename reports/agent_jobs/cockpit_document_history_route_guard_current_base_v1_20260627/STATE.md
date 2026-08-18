# State

## Current State

- `VERIFIED`: worktree is `/home/l4nd0/tenn-issue239-cockpit-doc-history-guard-current-base-v1-20260627`.
- `VERIFIED`: branch is `safe/issue239-cockpit-doc-history-guard-current-base-v1-20260627`.
- `VERIFIED`: HEAD/base is `8a4ffe2837d2950602b222d226d2d516b2076ec0`.
- `VERIFIED`: issue #239 is open and has no matching open PR from live search.
- `VERIFIED`: active registry was empty before claim.
- `VERIFIED`: task card validates and registry overlap check passed.
- `VERIFIED`: registry claim succeeded for `cockpit_document_history_route_guard_current_base_v1_20260627`.
- `VERIFIED`: live task ledger was available and accepted `claimed` and `implementation_started` entries.

## Existing Work Classification

- `CONTINUE`: stale worktree `/home/l4nd0/tenn-issue239-cockpit-doc-history-guard-v1-20260626` has relevant uncommitted #239 work.
- `SUPERSEDED`: stale task `cockpit_document_history_route_guard_v1_20260626` is on base `857e76c3180cb0b1fb9fc360652d6a9b64543c86`, behind current canonical, and its task card forbids push and issue closeout.
- `ADOPT`: the current-base branch ports the bounded route/client/test changes while leaving the stale worktree untouched.

## Change

- `financial-engine_v2/backend/app/routes/cockpit_api.py`
  - adds `Depends(require_api_key)` to `GET /api/cockpit/docs`.
- `financial-engine_v2/backend/tests/test_cockpit_docs_route_auth.py`
  - proves missing API key is denied before opening the DB.
  - proves authenticated calls still return document-history rows.
- `financial-engine_v2/backend/tests/test_local_api_key.py`
  - includes `/api/cockpit/docs` in protected-route dependency coverage.
- `cockpit-ui/lib/api-client.ts`
  - makes `listDocuments()` send `X-API-Key` when configured.
- `cockpit-ui/lib/api-client.test.ts`
  - adds focused header coverage for `listDocuments()`.
- `docs/architecture/19_backend_api_surface.md`
  - documents the guarded `/api/cockpit/docs` access contract.

## Docs Impact Check

- `docs_impact`: `DOCS_UPDATED`
- `docs_checked`: `AGENTS.md`, `docs/README.md`, `docs/architecture/19_backend_api_surface.md`, issue #239
- `docs_changed`: `docs/architecture/19_backend_api_surface.md`
- `docs_followup`: `NONE`
- `reason`: issue #239 changes the access contract for `GET /api/cockpit/docs`.

## Model And Worker Routing

- `task_tier`: `medium`
- `recommended_model`: `standard coding model`
- `actual_model`: `Codex GPT-5`
- `why_this_model`: focused backend route guard, API-client header propagation, and tests.
- `worker_model_allowed`: `false`
- `worker_decision_limit`: no workers used; stale local work was inspected and ported by the orchestrator.
- `escalation_needed`: `false`

## Functionality Proof

- result: `PARTIAL`

| Field | Required evidence |
| --- | --- |
| intended output | Unauthenticated `GET /api/cockpit/docs` is denied when a local API key is configured; authenticated document-history loading still works. |
| live output location | FastAPI route `GET /api/cockpit/docs` and Cockpit API client `listDocuments()`. |
| pre-run max timestamp or count | `DATA_MISSING`; no live backend runtime baseline was captured. |
| post-run max timestamp or count | `DATA_MISSING`; no live backend runtime was started. |
| rows/files inserted or updated after run start | Zero runtime rows/files; source, docs, tests, and report artifacts changed only. |
| readiness/gate status | Local focused backend tests and static checks passed; local frontend Vitest blocked by missing dependency binary; GitHub checks pending until PR. |
| exact command/query used | `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_docs_route_auth.py financial-engine_v2/backend/tests/test_local_api_key.py -q` |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | `PARTIAL` |
| remaining blocker | No live backend/browser runtime was started; local frontend Vitest execution is blocked by missing `cockpit-ui/node_modules/.bin/vitest`. |

## Next Action

Open a PR for issue #239, wait for GitHub checks, merge only if checks are
green and merge state is clean, then close issue #239 and release the registry
claim.
