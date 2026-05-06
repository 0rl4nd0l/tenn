# A2M Ticker News Retrieval Selection v1

Lane: Query Orchestration
Execution mode: SAFE EXTENSION MODE
Worktree: `/mnt/sdb2/home/l4nd0/tenn`
Branch: `preserve/dirty-work-20260430T065748Z`

This report records the read-side retrieval selection change for A2M/company ticker chat queries. The implementation does not ingest, reprocess, reindex, mutate Qdrant, mutate `reports/qual_context/news.sqlite`, mutate memory stores, change source-label wording, or change financial truth.

Changed path:

- Backend chat: `chat_with_tenn()` now resolves a ticker from explicit input or ticker-like query text, passes it into `query_rag()`, runs ticker-filtered `news_chunks` retrieval, and preserves top ticker-filtered news rows in context.
- Cockpit agent loop: ticker-specific recent/company overview turns now prefetch `search_news` with the resolved ticker before broad tool-less synthesis can satisfy grounding with non-news evidence.

Report files:

- `00_summary.md`
- `01_preflight.md`
- `02_change_summary.md`
- `03_retrieval_selection_contract.md`
- `04_tests_and_validation.md`
- `05_remaining_source_label_risk.md`
- `06_remaining_entity_linking_drift.md`
- `07_next_codex_prompt_source_label_semantics.md`
