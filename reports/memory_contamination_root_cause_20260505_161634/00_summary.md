# Summary

## Verdict

Root cause classification: CONFIRMED multiple causes.

Primary cause: router fanout. `memory_signal_router._signals_for_statement()` writes every accepted statement once per memo-level ticker, then `route_signals()` persists each signal to `CompanyMemoryStore.update_company_memory()` under that ticker.

Upstream contributors: signal extraction and ticker/entity linking. Commentary/news memo extractors ask the LLM for one memo-level `tickers` list, not per-statement targets. News ingestion has `primary_ticker` and relevance rows for chunk payloads, but memo dispatch does not pass those into memory extraction. Commentary transcripts rely entirely on the LLM-extracted memo ticker list.

Alias contributor: alias fragmentation happens before write and is preserved by storage. The store writes the exact `company_id`/`entity_id` string and retrieval uses only `entities.primary_ticker`.

Not the primary cause: retrieval. Retrieval can surface contaminated rows, but the wrong rows already exist in company memory before retrieval.

## Largest Fanout Evidence

The largest cluster in `04A_memory_duplicate_fanout_clusters.csv` is from source `youtube_transcript:asx-daily-rundown-atlassian-lifts-tech-a2-milk-recall-shock-accent-group-all-time-lows:88e960386e503796`: `pettimed s capital raising at 1 cent per share`, 67 rows across 50 entities.

The stocktake contains 107 duplicate/fanout clusters: 43 commentary/youtube clusters totaling 1555 rows with a max 50 affected entities, and 64 newspaper4k clusters totaling 322 rows with a max 8 affected entities.

## Synthetic Proof

A temp-DB reproduction using a synthetic A2M primary memo with Atlassian/Pettimed/Chrysos/Accent/macro statements produced:

- 35 company-memory writes
- 1 market-memory write
- 7 entries per ticker across A2M, ATLASSIAN, PETTIMED, CHRYSOS, ACC
- each non-A2M company received the A2M product recall statement
- A2M received unrelated Atlassian/Pettimed/Chrysos/Accent/macro statements

The repo now includes a strict xfail synthetic fixture:

- `financial-engine_v2/backend/tests/test_memory_signal_router.py::test_multi_topic_commentary_does_not_fanout_primary_company_signal`

## Required Questions

1. Where does a memo/transcript/news item acquire its ticker list?  
   CONFIRMED: commentary/news memo extractors acquire `tickers` from LLM JSON. News chunking also has entity-linker/relevance tickers, but memo dispatch passes article text/provider/date, not `primary_ticker` or linked tickers.

2. Does the same statement get written once per ticker in that list?  
   CONFIRMED: yes, in `_signals_for_statement()`.

3. Is there any primary-company vs mentioned-company distinction?  
   CONFIRMED absent in memory signal routing. News chunk payloads have `primary_ticker`, but the memory memo route does not use it.

4. Is there any distinction between company signal, market recap, sector context, macro context, other-company event, transcript summary?  
   INFERRED partial: sector/macro signals can be created, but company fanout still occurs first for every ticker. There is no per-statement scope/target distinction for other-company events or transcript summaries.

5. Are raw dict-like payloads being stored as statements?  
   CONFIRMED likely by code and stocktake. Extractor `_normalize_list()` stringifies list items, including dicts, and stocktake found 82 raw dict-like rows.

6. Are source_id/source/title/published_at/evidence spans preserved?  
   CONFIRMED partial. `source`, `source_id`, and `published_at` are preserved in metadata for most rows. Stocktake provenance found no title, no evidence spans, and no ticker-attribution reason across 1998 rows.

7. Are duplicate/fanout checks performed before write?  
   CONFIRMED only within the emitted signal list and within the same company/type/statement/source. No cross-ticker fanout guard exists.

8. Does alias fragmentation happen before write, during write, or during retrieval?  
   CONFIRMED before/during write: extracted or linked ticker/entity strings become `entity_id`; store persists exact uppercase `company_id`. Retrieval then amplifies by searching only the primary ticker/company_id.

9. Does retrieval search only primary ticker/company_id?  
   CONFIRMED for company memory: `CompanyMemoryStore.retrieve()` uses `entities["primary_ticker"]` only.

10. Which code path created the largest fanout clusters in the stocktake CSV?  
    CONFIRMED: commentary/YouTube transcript memo extraction plus `memory_signal_router` fanout into company memory.

