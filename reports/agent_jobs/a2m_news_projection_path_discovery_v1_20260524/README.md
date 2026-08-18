# A2M News Projection Path Discovery

Status: `complete_with_data_missing_classified`.

## Confirmed

- Qdrant `news_chunks` is reachable and reports `22324` points.
- Read-only Qdrant counts show `24` A2M-matching points using `ticker`, `primary_ticker`, or `tickers`.
- Qdrant scroll samples were requested with `with_vectors=false`; returned points did not include vector fields.
- Existing retrieval code for backend chat uses `HybridRetriever("news_chunks")` and ticker matching across `ticker`, `primary_ticker`, and `tickers`.
- `reports/qual_context/news_articles.sqlite` and `reports/qual_context/news.sqlite` are the configured/default SQLite paths, but they were absent at checked canonical, NVMe, and old HDD paths.
- Cockpit `state.db` exists and is readable in immutable mode, but it is not the canonical news corpus and has no A2M `update_events` or `market_update_followups`.

## Conclusion

This is not an A2M ticker-alias retrieval failure. Qdrant contains A2M evidence and the current backend chat retrieval/filter path can see list-linked A2M payloads.

SQLite/projection parity remains `DATA_MISSING` because the canonical article/context SQLite files are absent. The most likely classification is: Qdrant was populated from a source corpus that is no longer present at the checked local paths, while the documented SQLite fallback/projection is absent or unmaterialized.

## DATA_MISSING

- Whether `news_articles.sqlite` was moved to an unchecked mount/path.
- Whether nightly `--refresh-sqlite-fallback` is currently succeeding, skipped, or writing elsewhere.
- Direct parity between source SQLite rows and Qdrant payloads, because the source SQLite file is absent.
- Live chat synthesis visibility, intentionally not invoked because it may write chat or memory events.

## Next Safe Step

Create a read-only news runtime path health check that reports:

- configured article DB path exists/readable;
- configured fallback DB path exists/readable;
- Qdrant `news_chunks` point count and A2M count;
- latest nightly summary/log path;
- whether fallback refresh produced `news.sqlite`.

Do not reindex/resync until the missing source path is resolved or a deliberate rebuild task is approved.
