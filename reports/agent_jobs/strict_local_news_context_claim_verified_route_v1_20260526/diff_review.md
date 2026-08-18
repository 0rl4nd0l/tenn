# Diff Review

## Scope

Changed files stayed inside the task-card allowlist:

- `financial-engine_v2/cockpit/core/chat.py`
- `financial-engine_v2/cockpit/tests/test_chat_ticker_detection.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- task card and report bundle

## Architecture Review

- Backend remains the owner of retrieval and source-pack assembly.
- The change reuses the existing `ChatController._try_news_shortcircuit` path.
- No direct DB, Qdrant, or news-store access was added.
- No DB, Qdrant, or news-store mutation was performed.
- No reindex, resync, backfill, projection repair, migration, parser routing,
  canonical financial truth write, or memory write was performed.
- No runtime, model, GPU, Docker, systemd, env, volume, or UI config file was
  changed.
- No one-off ticker alias hardcoding was added.
- `chat_evidence_guard.py` was not changed.

## Source-Grounding Review

The implementation does not relabel context-only sources. It only causes
literal `local_news_context` ticker prompts to use the same direct news
retrieval path as `news for TICKER`.

Successful news hits still flow through `news_search` evidence and are marked
`claim_verified + local_news_context` by the existing source-pack builder.
No-hit, context-only, and degraded evidence remains unverified and continues to
trigger guarded `DATA_MISSING`.

## Validation Review

Focused tests cover:

- strict `local_news_context` prompts use the news short-circuit without LLM
- verified `news_search` evidence satisfies local-news-only prompts
- no-hit `news_search` evidence remains guarded `DATA_MISSING`
- existing source-pack semantics for context-only/no-hit/degraded rows
- existing local-news evidence guard behavior

`git diff --check` and task-card `check-diff --no-write-report` passed.
