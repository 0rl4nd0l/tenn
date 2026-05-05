# Tests To Add

## Added In This Audit

- `test_multi_topic_commentary_does_not_fanout_primary_company_signal`
  - status: strict xfail
  - file: `financial-engine_v2/backend/tests/test_memory_signal_router.py`
  - storage: pytest tmp_path only
  - purpose: prove current fanout bug and lock desired future behavior

## Add With The Later Fix

1. Router unit test: multi-topic commentary should route A2M recall only to A2M and rates/inflation only to market memory.

2. Router unit test: a statement mentioning Atlassian should not be written under A2M unless it explicitly states an A2M relationship.

3. Router unit test: multi-ticker sector statement creates sector memory with linked tickers and no company-memory writes.

4. News memo test: source article with `primary_ticker=A2M` and mentioned companies does not fanout every summary statement.

5. Commentary extractor test: non-list/dict-like LLM output is rejected or normalized structurally instead of stored as `str(dict)`.

6. Provenance test: routed signals retain `source`, `source_id`, `source_title`, `published_at`, and evidence span/quote when available.

7. Alias test: extracted aliases are not used as canonical company IDs unless validated by an ASX identity map.

8. Retrieval regression: company memory retrieval remains exact primary ticker and does not silently search alias groups until canonicalization is explicitly implemented.

## Do Not Add Yet

Do not add live replay/chat tests for contaminated prompts until there is a non-mutating replay harness. Current live chat probes can write session state and auto-flag artifacts.

