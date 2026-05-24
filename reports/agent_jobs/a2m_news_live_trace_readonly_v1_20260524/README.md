# A2M News Live Trace Read-Only

Read-only A2M trace completed without Qdrant or SQLite mutation.

Findings:
- Qdrant `news_chunks` has 24 A2M-matching points across 4 unique articles.
- Keyword-only HybridRetriever trace surfaced 8 A2M chunks across 4 articles with vectors disabled.
- Qdrant collection point count was unchanged before/after the trace.
- Canonical/live news SQLite paths checked for `news.sqlite` and `news_articles.sqlite` were absent, so SQLite storage/projection parity remains DATA_MISSING.
- HybridRetriever/Tenn chat ticker filters cover `ticker`, `primary_ticker`, and `tickers`; the separate `rag.query_news_chunks` helper covers `ticker` and `tickers` only.

No blind reindex/resync, Qdrant write, news SQLite write, entity-linker rewrite, or live chat synthesis call was run.
