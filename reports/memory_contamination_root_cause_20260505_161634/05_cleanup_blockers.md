# Cleanup Blockers

Cleanup remains blocked.

## Must Preserve Before Cleanup

Preserve these artifacts before any expire/archive/canonicalization job:

- `company_memory.sqlite`, `market_memory.sqlite`, and WAL/SHM state if the DB is live
- full `memory_entries` and `change_log` rows, including row IDs
- `source`, `source_id`, `first_seen_at`, `last_seen_at`, `metadata_json`, confidence/materiality/status
- `commentary_memos.jsonl` and `news_memos.jsonl`
- `source_registry.jsonl`
- commentary chunk staging/index records for implicated transcripts
- news article DB tables: `articles`, `entity_links`, `article_relevance`, `article_versions`
- Qdrant/news chunk payloads if a cleanup later requires retrieval/index consistency checks
- the stocktake report folder and this root-cause report folder

## Why Cleanup Is Blocked

1. The write path is still unsafe. Cleaning before fixing fanout would allow contamination to recur.

2. Provenance is partial. Stocktake provenance reports no source titles, no evidence spans/quotes, no ticker-attribution reason, and no originating pipeline job ID across 1998 rows.

3. Alias identity is not authoritative. The alias matrix marks many canonicalization guesses as inferred and HIGH risk.

4. Some rows may be valid but stored under fragmented aliases. String similarity alone is not safe cleanup authority.

5. LLM outputs must not be used as cleanup authority.

## Blocked Operations

Do not perform these in this lane:

- hard delete memory rows
- expire memory rows
- rewrite statements
- rewrite `company_id`/alias scopes
- normalize aliases in live storage
- reprocess live news/transcripts
- upsert or rebuild Qdrant
- migrate DB schemas
- tune ranking/retrieval to hide contaminated rows
- change synthesis or source labels

## Minimum Unblock Conditions

Cleanup can only move to a separate approved cleanup lane after:

- write-path fix has landed and passed synthetic + fixture tests
- memory DB snapshot is backed up
- source and row preservation manifest is generated
- candidate cleanup list is row-ID based with human-readable source evidence
- operation is reversible, preferably expire/archive rather than delete

