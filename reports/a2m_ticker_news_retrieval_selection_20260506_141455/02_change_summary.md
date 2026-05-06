# Change Summary

Exact retrieval path modified:

1. `financial-engine_v2/backend/app/services/tenn_chat.py`

   - Added `_resolve_chat_ticker()` using the shared ticker inference helper.
   - Changed `chat_with_tenn()` so ticker-specific queries call `query_rag(query=..., ticker=normalized_ticker, top_k=10)`.
   - Kept `news_chunks` retrieval ticker-filtered when a ticker is resolved.
   - Added `_ensure_ticker_news_context()` so top ticker-filtered news rows are merged into the context bundle instead of being silently displaced by broad commentary ranking.
   - Preserved `chunk_id`, `article_id`, `document_id`, `ticker`, and `provider` in context rows and source metadata.

2. `financial-engine_v2/cockpit/core/agent_loop.py`

   - Added a narrow ticker-news prefetch gate for ticker-specific company/recent/overview/news turns.
   - Before the LLM loop, the agent calls `search_news` with `{"query": message, "ticker": <resolved ticker>, "limit": 5}` when the gate passes.
   - The resulting `search_news` payload is added to `evidence`, `tool_traces`, and the model context with source metadata intact.
   - The guard skips market-wide, command, previous-tool, correction, thesis-save, holdings, portfolio, and financial fact lookup turns.

No new retrieval system or parallel chat path was added.
