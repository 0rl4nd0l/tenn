# DATA_MISSING

This audit ran with `production_data_access: false`.

## Missing Data

- Current active runtime `news_articles.sqlite` was not queried.
- Current active runtime `news.sqlite` was not queried.
- Qdrant `news_chunks` was not queried or scrolled.
- No live `/rag/query` request was run.
- No live backend `chat_with_tenn()` request was run.
- No Cockpit chat/reporting session trace for the original A2M failure was available.
- The referenced prior `reports/a2m_news_trace_20260506_110151` directory was not present in this checkout.
- The current checkout does not contain `reports/qual_context/news_articles.sqlite` or `reports/qual_context/news.sqlite`.
- The current checkout does not contain `financial-engine_v2/data/raw/asx_ticker_universe.txt`, which blocks some default-universe entity-linker tests.
- `.cursor/rules/` architecture rule files were not present in this worktree, so architecture-rule validation is limited to code/report inspection.

## Exact Read-Only Follow-Up Needed

Run a separate approved read-only trace task that permits production data access for these read-only probes only:

1. Open the active news articles DB in SQLite read-only URI mode.
2. Query `articles` for titles/body/URLs containing `A2M`, `A2 Milk`, `The a2 Milk Company`, and recall terms.
3. Query `entity_links` and `article_relevance` for the matched `article_id` values.
4. Query or scroll Qdrant `news_chunks` read-only for those `article_id` values and for ticker filters matching `ticker=A2M` and `tickers contains A2M`.
5. Compare ranks from `/rag/query source=news` semantics with backend chat `HybridRetriever("news_chunks")` semantics without running any chat session that writes artifacts.

Do not run loaders, resyncs, ingestion, backfills, or write-mode Qdrant/SQLite operations in that follow-up.
