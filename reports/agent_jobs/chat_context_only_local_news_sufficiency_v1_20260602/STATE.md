# State

## Current State

VERIFIED: implementation and focused validation are complete.

- Branch: `safe/issue265-chat-context-only-local-news-current-base-v1-20260629`
- Worktree: `/home/l4nd0/tenn-issue265-chat-context-only-local-news-v1-20260629`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Base commit used by this worktree: `f60b5161cd121a41c5cc56048feb055f82ebdd10`
- Rebased onto canonical: `55da116ad6b20adccb7a66931601895b3e8ab757`
- Related issue: `#265`
- GitHub writes: approved by user `proceed`; push and draft PR pending
- Runtime/data mutations: not performed
- Rebase: performed onto `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Merge: not performed

## Behavior

`chat_with_tenn()` now separates two cases:

- No local-news source for a local-news-expected query: keep existing
  `missing_required_evidence` + `no_hit`.
- Local-news context exists for a recent/update/news query but none is
  `claim_verified`: add `missing_required_evidence` +
  `insufficient_for_recent_news`, without adding `no_hit`.

Generic `tell me about A2M` context-only behavior remains `context_only`.

## Next Action

Push the refreshed branch and open a draft PR for issue #265.
