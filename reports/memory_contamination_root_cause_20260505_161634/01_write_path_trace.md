# Write Path Trace

## Commentary / YouTube Transcript

1. `commentary_ingest.ingest_transcript()` receives transcript text, source name/type, speaker, and published date. It stages commentary chunks for review and queues `extract_commentary_memo_task` with `source_id`, transcript text, speaker, source type, published date, LLM config, and memo path. It does not pass a primary ticker or linked ticker attribution. Evidence: `financial-engine_v2/backend/app/services/commentary_ingest.py:83-103`, `:232-249`.

2. `extract_commentary_memo_task()` builds a `CommentaryMemoExtractor` and calls `extract_and_store()`. Evidence: `financial-engine_v2/backend/app/tasks/commentary_tasks.py:9-21`.

3. `CommentaryMemoExtractor._prompt()` requests one JSON object with `claims`, `catalysts`, `risks`, `sentiment`, `time_horizon`, and `tickers`. Evidence: `financial-engine_v2/backend/app/services/commentary_memo_extractor.py:149-160`.

4. For long transcripts, `_extract_multipass()` merges all window-level tickers into one deduped memo-level `tickers` list. Evidence: `financial-engine_v2/backend/app/services/commentary_memo_extractor.py:204-274`.

5. `_normalize_memo()` stores that ticker list as `memo["tickers"]`; it does not attach per-statement ticker targets or evidence spans. Evidence: `financial-engine_v2/backend/app/services/commentary_memo_extractor.py:163-202`.

6. `extract_and_store()` stores the memo and routes it by default via `signals_from_commentary_memo(stored)` and `route_signals(...)`. Evidence: `financial-engine_v2/backend/app/services/commentary_memo_extractor.py:331-375`.

## News / Newspaper4k

1. News ingestion links article entities using `EntityLinker.link_article()` and persists both `entity_links` and `article_relevance`. Evidence: `scripts/news_pipeline/ingest.py:170-203`.

2. The news DB schema has separate `entity_links` and `article_relevance` tables; `article_relevance` includes `relation_type` and `is_primary`. Evidence: `scripts/news_pipeline/db.py:76-110`.

3. Chunk-build/retrieval surfaces preserve `linked_tickers`, `primary_ticker`, and `ticker_relevance_json` for news chunks. Evidence: `scripts/news_pipeline/db.py:746-783`, `scripts/news_pipeline/chunk_builder.py:131-164`, `scripts/load_news_to_qdrant.py:422-453`.

4. Memo dispatch does not pass those ticker/relevance fields to the memo extractor. It passes only `source_id`, `article_text`, `provider`, and `published_at`. Evidence: `scripts/load_news_to_qdrant.py:126-160`.

5. `NewsMemoExtractor._prompt()` asks the LLM for one memo-level `tickers` list. `_normalize_memo()` stores it, and `extract_and_store()` routes `signals_from_news_memo(stored)` by default. Evidence: `financial-engine_v2/backend/app/services/news_memo_extractor.py:135-190`, `:235-277`.

## Signal Router

1. `signals_from_commentary_memo()` and `signals_from_news_memo()` both read `memo["tickers"]` and normalize it as a single list. Evidence: `financial-engine_v2/backend/app/services/memory_signal_router.py:91-151`.

2. For every accepted statement, both functions call `_signals_for_statement(...)` with that same ticker list. Evidence: `financial-engine_v2/backend/app/services/memory_signal_router.py:117-143`, `:174-203`.

3. `_signals_for_statement()` emits a company signal for every ticker in the list, regardless of which ticker the statement actually discusses. Evidence: `financial-engine_v2/backend/app/services/memory_signal_router.py:238-267`.

4. `_market_signal_for_statement()` can add a sector or macro signal, but this is additional to company fanout, not a replacement. Evidence: `financial-engine_v2/backend/app/services/memory_signal_router.py:268-328`.

5. `route_signals()` persists sector/macro signals to market memory; all other signals are written to company memory under `entity_id`. Evidence: `financial-engine_v2/backend/app/services/memory_signal_router.py:208-235`.

## Company / Market Stores

1. `CompanyMemoryStore.update_company_memory()` inserts into `memory_entries` using exact `company_id`, statement, source, source_id, and metadata. Evidence: `financial-engine_v2/backend/app/services/company_memory.py:193-313`.

2. Duplicate checks are per `company_id + type + normalized_statement + active status`; there is no cross-company duplicate/fanout guard. Evidence: `financial-engine_v2/backend/app/services/company_memory.py:525-543`.

3. `MarketMemoryStore.update_market_memory()` inserts sector/macro state with source/source_id and optional linked tickers; duplicate checks are per sector or macro topic. Evidence: `financial-engine_v2/backend/app/services/market_memory.py:123-230`, `:622-640`.

## Retrieval

1. `CompanyMemoryStore.retrieve()` selects only `entities["primary_ticker"]`, lists active entries for that exact company_id, and ranks them. Evidence: `financial-engine_v2/backend/app/services/company_memory.py:439-460`.

2. `MarketMemoryStore.retrieve()` resolves a sector and also retrieves all active macro entries. Evidence: `financial-engine_v2/backend/app/services/market_memory.py:501-528`.

3. `QueryOrchestrator.build_plan()` includes company/market memory for risk, interpretation, and mixed queries, so contaminated rows can become answer input when selected. Evidence: `financial-engine_v2/backend/app/services/query_orchestrator.py:321-383`, `:687-708`.

