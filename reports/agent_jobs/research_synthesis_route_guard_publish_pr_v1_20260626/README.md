# Research Synthesis Route Guard Publish PR

Status: validated; draft PR pending

## Summary

This lane publishes the validated local issue #244 fix as a draft PR. It does
not merge the PR or close the issue.

## Worktree

- Worktree: `/home/l4nd0/tenn-issue244-research-synthesis-route-guard-v1-20260626`
- Branch: `safe/issue244-research-synthesis-route-guard-v1-20260626`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Initial HEAD: `857e76c3180cb0b1fb9fc360652d6a9b64543c86`

## Validation

Focused validation passed:

- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_research_route_auth.py -q`
  returned `4 passed`.
- `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/research.py financial-engine_v2/backend/tests/test_research_route_auth.py`
  passed.
- `python3 -m py_compile financial-engine_v2/backend/app/routes/research.py financial-engine_v2/backend/tests/test_research_route_auth.py`
  passed.
- `git diff --check` passed.

## Runtime Functionality Proof

This publish lane does not claim live backend/runtime functionality. It
publishes a route dependency/test/doc fix for the server-side research synthesis
route.

| Field | Required evidence |
| --- | --- |
| intended output | `POST /research/synthesize` rejects missing/wrong API keys before server-side synthesis when `settings.local_api_key` is configured, and matching keys still allow synthesis. |
| live output location | Local FastAPI TestClient route `/research/synthesize`; route dependency registry in `research.router`. No live backend service started. |
| pre-run max timestamp or count | `DATA_MISSING`; no live runtime baseline captured because this is a no-runtime publish lane. |
| post-run max timestamp or count | Focused TestClient evidence: route registers `require_api_key`; missing/wrong-key requests return 401 before the patched synthesis callable runs; matching-key request returns 200. |
| rows/files inserted or updated after run start | Source/test/docs files plus task/report artifacts committed in the draft PR branch. |
| readiness/gate status | Backend route-auth tests, ruff check, py_compile, and `git diff --check` passed. |
| exact command/query used | `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_research_route_auth.py -q`; `uv run --with ruff ruff check ...`; `python3 -m py_compile ...`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | Draft PR must be opened, reviewed, and merged before issue #244 can close; no live service smoke was run. |

result: PARTIAL

## PR

Pending.
