# State

## Evidence

- Issue #235 is open.
- PR #439 is open but `DIRTY` / `CONFLICTING` against
  `migration/clean-runtime-baseline-reconstruct-v1`.
- PR #439 head `cbbadbd4081fa6a1ff612883498fbba125c94ae8` had historical
  GitHub checks passing.
- PR #439 review comment required API-key forwarding for company-dump callers.
- Current canonical already contains `BackendApiClient.get_company_dump()`
  header forwarding and a focused assertion in
  `financial-engine_v2/backend/tests/test_backend_api_client_context.py`.

## Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | Backend memory read routes reject missing/wrong API keys when `LOCAL_API_KEY` is configured and still allow valid-key/local-dev reads. |
| live output location | Backend routes under `/api/context/memory`, `/api/context/memory/index`, `/api/context/thesis`, and `/api/context/company_dump`. |
| pre-run max timestamp or count | DATA_MISSING; no live backend/runtime mutation performed. |
| post-run max timestamp or count | DATA_MISSING; no live backend/runtime mutation performed. |
| rows/files inserted or updated after run start | 0 runtime rows/files; code/tests/report artifacts only. |
| readiness/gate status | Focused local tests and static checks passed; GitHub checks/review pending until PR is opened. |
| exact command/query used | See `VALIDATION.md`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | No live backend/browser runtime smoke was run. |

result: PARTIAL

## Boundaries

- No DB, Qdrant, Redis, news, memory-store, source-PDF, gold-label, service, or
  model/GPU state was mutated.
- Stale PR #439 branch was preserved unchanged.
