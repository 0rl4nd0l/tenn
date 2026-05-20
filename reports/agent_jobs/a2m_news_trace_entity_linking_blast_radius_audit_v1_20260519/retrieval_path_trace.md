# Retrieval Path Trace

Status: `confirmed_static` for route ownership and filter semantics; live A2M ranks are `DATA_MISSING`.

## Storage to Qdrant Projection

`scripts/load_news_to_qdrant.py` reads `articles`, `entity_links`, and `article_relevance` from the news articles DB. `_iter_chunks()` emits:

- `article_id`
- `url`
- `title`
- `provider`
- `language`
- `published_at`
- `tickers`
- `primary_ticker`
- `text`

`_build_chunk_payload()` writes Qdrant payload fields:

- `corpus: news`
- `article_id`
- `chunk_id`
- `provider`
- `ticker`
- `tickers`
- `primary_ticker`
- `published_at`
- `language`
- `title`
- `url`
- `source_type: news_article`
- `text`

Important behavior: `ticker` is `primary_ticker` when available, the single linked ticker when exactly one ticker exists, or empty when multiple tickers exist and no primary ticker is resolved.

## `/rag/query` News Path

Owners:

- `financial-engine_v2/backend/app/main.py`
- `financial-engine_v2/backend/app/services/rag.py`
- `financial-engine_v2/cockpit/integrations/backend_api.py`
- `financial-engine_v2/cockpit/core/tools.py`

`POST /rag/query` with `source: news` calls `query_news_chunks()`. The ticker filter uses a Qdrant `should` filter matching either:

- payload key `ticker`
- payload key `tickers`

For ticker-scoped queries it expands the candidate limit to between 12 and 64 before deduping/ranking. This path is used by:

- Cockpit News Screen;
- Cockpit agent `search_news`;
- `ToolRouter.get_news_context()`;
- `QualContextReader`.

## Backend Chat Path

Owners:

- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/backend/app/services/hybrid_retriever.py`

`chat_with_tenn()` currently:

- resolves an explicit or inferred ticker;
- calls announcement/document `query_rag()`;
- retrieves commentary from `HybridRetriever("commentary_chunks")`;
- retrieves news from `HybridRetriever("news_chunks")`;
- filters news with `_filter_news_by_ticker()`;
- preserves up to three ticker-news rows with `_ensure_ticker_news_context()`.

The risk is that `HybridRetriever._build_ticker_filter()` only filters on payload key `ticker`, and `_filter_news_by_ticker()` also only checks `chunk["ticker"]`. It does not currently match payload `tickers` or `primary_ticker` separately.

This means `/rag/query source=news` can retrieve a point whose `tickers` contains the requested ticker, while backend chat can miss or drop the same point if top-level `ticker` is empty or another primary ticker.

## Ranking and Synthesis

Prior A2M selection work added `_ensure_ticker_news_context()` so top ticker-filtered news rows are retained even when broad commentary ranks higher. Existing tests prove this for a fixture with top-level `ticker: A2M`.

Missing coverage:

- a chat fixture where payload `tickers` contains `A2M` but top-level `ticker` is empty;
- a chat fixture where payload `tickers` contains `A2M` but top-level `ticker` is another symbol;
- route-parity fixture comparing `/rag/query`, ToolExecutor `search_news`, News Screen mapping, and backend `chat_with_tenn`.

## Home, Commentary, News Screen, and Intel Pulse

Home news should remain separate from general news retrieval. The current route-parity audit found Home BFF news uses `/api/commentary/recent`, which proxies backend `/api/commentary/recent`; that backend route filters source registry records to commentary/transcript source types.

News Screen uses `/rag/query` with `source: news`, so it is Qdrant news retrieval, not Home commentary.

Cockpit agent `search_news` uses `ToolRouter.get_news_context()`, which prefers backend `/rag/query source=news` and falls back to SQLite only if a reader is configured.

Intel Pulse was not proven to use the same A2M news path in this audit.
