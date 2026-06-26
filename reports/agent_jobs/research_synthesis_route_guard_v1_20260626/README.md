# Research Synthesis Route Guard

Status: DONE_WITH_RISK

Issue: #244

Branch: `safe/issue244-research-synthesis-route-guard-v1-20260626`

Worktree: `/home/l4nd0/tenn-issue244-research-synthesis-route-guard-v1-20260626`

## Current Evidence

- Fresh sibling worktree created from
  `origin/migration/clean-runtime-baseline-reconstruct-v1` at
  `857e76c3180cb0b1fb9fc360652d6a9b64543c86`.
- Clean-worktree guard preflight passed with `stop_reimplementation=false`.
- No open PR, branch, ledger entry, or active registry job directly overlapped
  issue #244 during preflight.

## Closeout

Implemented local issue #244 fix in the clean sibling worktree.

Changed:

- Added `require_api_key` dependency to `POST /research/synthesize`.
- Added focused backend route-auth tests proving:
  - route dependency registration,
  - missing/wrong keys return 401 before `synthesize_research()` runs,
  - matching keys allow synthesis.
- Documented the `/research/synthesize` authentication contract.

Validation:

- RED: focused route-auth tests failed before implementation with 3 expected
  failures and 1 passing matching-key test.
- GREEN: `test_research_route_auth.py` passed, 4 tests.
- Python lint passed for touched backend route/test files.
- `git diff --check` passed.
- Task-card validation and diff boundary checks passed.

## Runtime Functionality Proof

| Field | Evidence |
| --- | --- |
| intended output | `POST /research/synthesize` rejects missing/wrong API keys when `settings.local_api_key` is configured and does not run server-side synthesis before auth succeeds. |
| live output location | Local FastAPI TestClient route `/research/synthesize`; route dependency registry in `research.router`. No live backend service was started. |
| pre-run max timestamp or count | RED test evidence: 0/1 research synthesis routes registered `require_api_key`; 0/2 configured-key rejection cases returned 401; missing/wrong-key requests invoked the patched synthesis callable before the fix. No live timestamp captured. |
| post-run max timestamp or count | GREEN test evidence: 1/1 route registers `require_api_key`; 2/2 missing/wrong-key cases return 401 and do not call synthesis; matching key returns 200; `test_research_route_auth.py` passed 4 tests. |
| rows/files inserted or updated after run start | 0 production rows/files. Repo diff only: backend route/test, API-surface docs, task card, and report artifacts. |
| readiness/gate status | Backend route-auth gate passed; ruff passed; task-card/diff gates passed; branch local/unpublished; no live service smoke. |
| exact command/query used | `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_research_route_auth.py -q`; `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/research.py financial-engine_v2/backend/tests/test_research_route_auth.py`; `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/research_synthesis_route_guard_v1_20260626.md --repo-root .`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | Local branch must be published/merged before issue #244 can be closed; no live Cockpit/backend smoke was run. |

result: PARTIAL

Issue state:

- GitHub issue #244 received a closeout comment.
- Issue remains open because this branch is local/unpublished.

Unsafe actions avoided:

- No DB, Qdrant, Redis, news, memory, extraction, source document, runtime,
  service, model, GPU, lockfile, dependency install, merge, rebase, reset,
  stash, clean, or issue-close mutation was performed.
