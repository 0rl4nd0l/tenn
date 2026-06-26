# Chat Recency Malformed Date Publish PR

Status: validation passed; draft PR pending

## Summary

This lane publishes the validated local issue #261 fix as a draft PR. It does
not merge the PR or close the issue.

## Worktree

- Worktree: `/home/l4nd0/tenn-issue261-malformed-date-isolation-v1-20260626`
- Branch: `safe/issue261-malformed-date-isolation-v1-20260626`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Initial HEAD: `857e76c3180cb0b1fb9fc360652d6a9b64543c86`

## Validation

Focused validation passed:

- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py -q`
  returned `28 passed`.
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_news_retrieval_eval.py -q`
  returned `34 passed`.
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
  passed.
- `python3 -m py_compile financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
  passed.
- `git diff --check` passed.

## Runtime Functionality Proof

This publish lane does not claim live backend/runtime functionality. It
publishes a local source-weighting/chat-strategy fix for malformed timestamp
metadata.

| Field | Required evidence |
| --- | --- |
| intended output | Malformed `published_at` values do not crash `apply_weighting_to_chunk()` or `_apply_chat_strategy()`; the malformed source remains visibly marked. |
| live output location | Local Python tests for `financial-engine_v2/backend/app/services/source_weighting.py` and `_apply_chat_strategy()`; no live backend service started. |
| pre-run max timestamp or count | `DATA_MISSING`; no live runtime baseline captured because this is a no-runtime publish lane. |
| post-run max timestamp or count | Focused local evidence: chat/source-weighting suite returned `28 passed`; news retrieval eval suite returned `34 passed`. |
| rows/files inserted or updated after run start | Source/test/task/report artifacts prepared for draft PR publication. |
| readiness/gate status | Backend pytest suites, ruff check, py_compile, and `git diff --check` passed. |
| exact command/query used | `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py -q`; `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_news_retrieval_eval.py -q`; `uv run --with ruff ruff check ...`; `python3 -m py_compile ...`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | Draft PR publication, review, and merge are still pending; no live service smoke was run. |

result: PARTIAL
