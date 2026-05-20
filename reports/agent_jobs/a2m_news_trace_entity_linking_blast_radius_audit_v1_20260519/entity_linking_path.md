# Entity Linking Path

Status: `confirmed_static`, with live A2M article rows `DATA_MISSING`.

## Owner Files

- `financial-engine_v2/config/ticker_identity_map.json`
- `scripts/news_pipeline/entity_linker.py`
- `scripts/news_pipeline/ingest.py`
- `scripts/news_pipeline/db.py`
- `scripts/news_pipeline/relevance.py`
- `scripts/test_news_pipeline_entity_linker.py`
- `scripts/test_load_news_qdrant_corpus_payload.py`

## Current A2M Identity

`A2M` is present in `ticker_identity_map.json` with:

- canonical names: `The a2 Milk Company Limited`, `The a2 Milk Company`
- aliases: `The a2 Milk Company`, `a2 Milk Company`, `A2 Milk`
- `news_entity_linking_enabled: true`

This means A2M is added to the effective news-linking ticker universe even when it is absent from the raw ticker universe fixture.

## Linker Mechanics

`EntityLinker` builds three relevant classes of links:

- explicit symbols: `ASX:A2M`, `ASX: A2M`, and `A2M.AX`, high precision and high recall;
- strict aliases: configured non-ambiguous aliases such as `A2 Milk`, high precision and high recall;
- ticker tokens: case-sensitive plain ticker tokens for non-stopword tickers, high recall only.

Generic one-word aliases are filtered by `_should_keep_alias()`, and strict stopword tickers such as `GOLD` and `GOOD` are not plain-token matched. Explicit symbol forms are still allowed for stopword-like tickers.

## Current Static Test Evidence

Passed directly:

- `test_default_identity_map_links_a2m_recall_article`
- `test_default_identity_map_links_a2m_alias_forms`
- `test_identity_map_can_opt_in_ticker_missing_from_universe`
- all 9 tests in `scripts/test_load_news_qdrant_corpus_payload.py`

Partially blocked:

- full `scripts/test_news_pipeline_entity_linker.py` ran 11 tests, with 7 passing and 4 errors because `financial-engine_v2/data/raw/asx_ticker_universe.txt` is missing in this checkout.

## A2M-Specific Conclusion

The current static code and fixtures are sufficient to say the present entity-linking implementation should link core A2M recall wording containing `A2 Milk`, `The a2 Milk Company`, `ASX:A2M`, `ASX: A2M`, or `A2M.AX`.

They are not sufficient to say the actual historical recall article is currently present in the active news DB, has current `entity_links` rows, has current `article_relevance` rows, or has corresponding Qdrant `news_chunks` points.

## Remaining Entity-Linking Drift

The prior A2M retrieval-selection report states that three core recall articles were A2M-linked, while some A2 Milk recall-mention articles were not fully linked. That remains a corpus coverage risk unless a read-only live DB trace confirms current rows and current alias coverage.
