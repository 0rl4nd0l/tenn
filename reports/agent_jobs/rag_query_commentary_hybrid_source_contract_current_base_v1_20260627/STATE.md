# State

## Current State

- `VERIFIED`: worktree is `/home/l4nd0/tenn-issue252-rag-query-contract-current-base-v1-20260627`.
- `VERIFIED`: branch is `safe/issue252-rag-query-contract-current-base-v1-20260627`.
- `VERIFIED`: HEAD/base is `6dc50b558c4ec88157d4353d9c493a80ed0e91d5`.
- `VERIFIED`: task card validates and registry overlap check found no active jobs.
- `VERIFIED`: registry claim succeeded for `rag_query_commentary_hybrid_source_contract_current_base_v1_20260627`.
- `VERIFIED`: live task ledger was available at `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry/task-ledger.jsonl`.
- `VERIFIED`: ledger entries were appended for `claimed` and `implementation_started`.

## Change

- `financial-engine_v2/backend/app/main.py`
  - narrowed `RagQueryRequest.source` to `Literal["asx_docs", "news"]`.
  - removed the `commentary` and `hybrid` 501 branches from `/rag/query`.
- `financial-engine_v2/backend/tests/test_rag_query_route_contract.py`
  - added route-contract coverage for accepted `asx_docs` and `news` values.
  - added regression coverage that `commentary` and `hybrid` return 422 before retrieval runs.
- `docs/architecture/19_backend_api_surface.md`
  - updated `/rag/query` accepted-source documentation to match backend validation.
  - records that commentary and hybrid retrieval remain owned by `/chat` until backend support exists.

## Guard And Collision Notes

- Portable guard rerun after creating the task card classified the worktree as
  `DIRTY_RELATED_WORKTREE` because the task card itself was untracked and
  overlapped the topic. This was expected task-setup dirt.
- Task-card validation, registry read-only list, registry overlap check, and
  registry claim all passed before source edits.
- `check-diff` passed with no disallowed files.

## Docs Impact Check

- `docs_impact`: `DOCS_UPDATED`
- `docs_checked`: `AGENTS.md`, `docs/README.md`, `docs/architecture/19_backend_api_surface.md`, issue #252
- `docs_changed`: `docs/architecture/19_backend_api_surface.md`
- `docs_followup`: `NONE`
- `reason`: issue #252 changes the public `/rag/query` request contract, so the API surface doc must match.

## Model And Worker Routing

- `task_tier`: `medium`
- `recommended_model`: `standard coding model`
- `actual_model`: `Codex GPT-5`
- `why_this_model`: focused backend API contract and route-test change.
- `worker_model_allowed`: `false`
- `worker_decision_limit`: no workers used; scope was narrow and source-local.
- `escalation_needed`: `false`

## Runtime Functionality Proof

- result: `PARTIAL`

| Field | Required evidence |
| --- | --- |
| intended output | `/rag/query` accepts `asx_docs` and `news`, rejects `commentary` and `hybrid` at request validation. |
| live output location | FastAPI route `POST /rag/query` in `financial-engine_v2/backend/app/main.py`; focused TestClient route test. |
| pre-run max timestamp or count | `DATA_MISSING`; no live backend runtime baseline was captured. |
| post-run max timestamp or count | `DATA_MISSING`; no live backend runtime was started. |
| rows/files inserted or updated after run start | Zero runtime rows/files; source, docs, tests, and report artifacts changed only. |
| readiness/gate status | Local focused route-contract tests and static checks passed; GitHub checks pending until PR. |
| exact command/query used | `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_rag_query_route_contract.py -q` |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | `PARTIAL` |
| remaining blocker | Live backend runtime was not started; runtime functionality is not proven by this report. |

## Next Action

Open a PR for issue #252, wait for GitHub checks, merge only if checks are
green and merge state is clean, then close issue #252 and release the registry
claim.
