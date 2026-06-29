# Chat Context-Only Local News Sufficiency

## Result

VERIFIED: implemented issue #265 locally on
`safe/issue265-chat-context-only-local-news-current-base-v1-20260629`.

Direct `chat_with_tenn()` now marks recent/update/news prompts as
`missing_required_evidence` and `insufficient_for_recent_news` when local news
was retrieved only as `context_only` and no local-news source is
`claim_verified`.

## Scope

Files intentionally touched:

- `docs/agent_tasks/chat_context_only_local_news_sufficiency_v1_20260602.md`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/backend/tests/test_news_retrieval_eval.py`
- `financial-engine_v2/backend/tests/test_chat_route.py`
- `reports/agent_jobs/chat_context_only_local_news_sufficiency_v1_20260602/`

Files intentionally not touched:

- DB, Qdrant, Redis, news stores, memory stores, source PDFs, prompts, gold labels,
  runtime/model/GPU/service config, frontend/Cockpit surfaces, GitHub issues/PRs.

## Evidence

RED: focused regression failed before the code change because result labels were
only `context_only` and `local_news_context`.

GREEN: focused backend and route test files passed after the change.

System functionality was not runtime-proven; this was a safe backend metadata and
test change with no runtime/data mutation.

## Rebase

VERIFIED: canonical advanced after this worktree was created, and the branch was
rebased onto the remote canonical PR base before publication.

- Worktree base/head before local commit: `f60b5161cd121a41c5cc56048feb055f82ebdd10`
- Rebased canonical head: `55da116ad6b20adccb7a66931601895b3e8ab757`
- Local-only canonical commit `975f0ceae5774548355ebc90f471ae1ac2e8bd57` was
  intentionally not included in the PR branch because it is not on the remote
  PR base.
