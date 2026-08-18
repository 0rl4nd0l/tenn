# Chat Recency Malformed Date Current Base V2

Status: `LOCAL_FIX_VALIDATED_READY_TO_PUBLISH`

This task reapplies issue #261 to current canonical after PR #419 became
conflicted by adjacent source-weighting merges.

Current result:

- `source_weighting.py` isolates malformed `published_at` parse failures with
  neutral recency and visible warning metadata.
- `test_tenn_chat_and_weighting.py` covers direct malformed-date weighting,
  invalid half-life preservation, and chat strategy keeping the valid neighbor.
- Focused validation passes locally.

## Runtime Functionality Proof

result: `PARTIAL`

| Field | Required evidence |
| --- | --- |
| intended output | Chat source weighting keeps a malformed-date chunk isolated with neutral recency and preserves valid neighboring chat context. |
| live output location | Local source function `apply_weighting_to_chunk()` and focused tests; no live app process was started. |
| pre-run max timestamp or count | PR #419 was open but `DIRTY` / `CONFLICTING`; current-base regression coverage for this combined state was absent. |
| post-run max timestamp or count | Local current-base validation: `test_tenn_chat_and_weighting.py` 36 passed and `test_news_retrieval_eval.py` 34 passed. |
| rows/files inserted or updated after run start | Two source-controlled files updated locally: `source_weighting.py` and `test_tenn_chat_and_weighting.py`; no stores or queues touched. |
| readiness/gate status | Local fix validated; publish, GitHub checks, canonical merge containment, and issue close remain pending. |
| exact command/query used | Commands listed in `VALIDATION.md`, including focused pytest, ruff, py_compile, `git diff --check`, and task-card `check-diff`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | `PARTIAL` |
| remaining blocker | Push/open replacement PR, wait for GitHub checks, supersede PR #419, merge replacement PR, verify containment, then close issue #261. |
