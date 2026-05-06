# Retrieval Selection Contract

For ticker/company-specific chat queries:

- If a ticker is explicitly supplied or inferred from the query, ticker-filtered local news retrieval is attempted or included before broad no-ticker semantic retrieval is treated as complete.
- Ticker-filtered news rows keep `article_id`, `chunk_id`, `ticker`, `provider`, `published_at`, `url`, and score metadata through context/source assembly where those fields are present.
- If ticker-filtered news exists, the top ticker-news rows are retained in the synthesis context even when broad commentary chunks also score highly.
- If no ticker is resolved, backend chat keeps broad semantic behavior and sends `ticker=None`.
- If no ticker-filtered news exists, current degraded/empty-context behavior remains stable.
- Holdings/local personal data routing is excluded from the agent-loop ticker-news prefetch.

Explicit non-changes:

- No ingestion.
- No Qdrant mutation.
- No `news.sqlite` mutation.
- No company, market, thesis, session, or operational memory mutation.
- No source-label wording or source drawer UI changes.
- No financial truth changes.

A2M case:

- The implementation does not live-query Qdrant or SQLite for A2M.
- The synthetic regression uses audited A2M recall metadata and proves that when ticker-filtered A2M recall evidence is returned, it is included in prompt/context and source metadata rather than dropped before synthesis.
