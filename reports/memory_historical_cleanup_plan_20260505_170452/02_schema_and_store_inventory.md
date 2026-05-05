# Schema And Store Inventory

## Required Questions

- Current company memory schema: SQLite database `company_memory.sqlite` with `company_memory`, `memory_entries`, `change_log`, indexes on `(company_id, status)` and `(company_id, normalized_statement)`, and `entry_id INTEGER PRIMARY KEY AUTOINCREMENT`.
- Reversible status field: partially. `memory_entries.status` currently supports `active` and `expired` in `CompanyMemoryStore._VALID_STATUSES`; there is no supported `quarantined` status.
- Audit trail table: yes, `change_log(change_id, company_id, entry_id, event_type, details_json, created_at)`.
- Stable row ids: yes, copied DB shows `entry_id` 1..1998 with 1998 distinct ids.
- Provenance fields: `source`, `source_id`, `first_seen_at`, `last_seen_at`, `metadata_json`; metadata often carries `published_at`, `speaker` or `provider`, sentiment, family/kind, themes, and time refs. Stocktake provenance shows source titles and evidence spans are incomplete.
- Preserve original row unchanged: not through the current `expire_entry` API because it mutates `status`, `closed_at`, and `last_seen_at`. It can preserve row text/source fields if a full snapshot and change-log event are kept first.
- Status-only rather than delete: yes for `expired`; no for `quarantined` until schema and store validators are extended.
- Quarantine without losing row text: not today. It requires a new allowed status and retrieval filter review. Do not emulate quarantine through delete, rewrite, or alias mutation.
- Defer alias cleanup while reducing contamination: yes. Clear duplicate fanout copies can be proposed for expiry while alias canonicalization remains blocked.
- Safe quarantine/expiry candidates: high-confidence duplicate fanout rows whose statement explicitly names a different target and where matching target rows are preserved in the same cluster. See `memory_rows_expire_candidates.csv`.
- Rows to preserve despite noise: matching target rows, already expired rows, and rows that are raw dict-like but may contain valid company-specific evidence pending review.
- Rows requiring manual review: raw dict-like rows, source-title/evidence-span gaps, ambiguous aliases, market/macro wrong-store rows before any rehome, and low-information statements.
- Cleanup remaining blocked: quarantine, alias canonicalization, market/macro rehome, raw payload normalization, any delete/rewrite, and any live mutation before approval gates.

## Store Paths Found

- Live candidate company DB: `financial-engine_v2/data/reports/research_memory/company_memory.sqlite`.
- Live candidate market DB: `financial-engine_v2/data/reports/research_memory/market_memory.sqlite`.
- Empty/local backend fallback company DB: `financial-engine_v2/backend/reports/research_memory/company_memory.sqlite` had zero rows in the copied read.

## Copied DB Counts

```json
{
  "candidate_counts": {
    "alias_merge_candidate_later": 53,
    "do_not_touch_blocked": 167,
    "macro_memory_rehome_candidate_later": 147,
    "manual_review": 316,
    "market_memory_rehome_candidate_later": 69,
    "no_action_preserve": 34,
    "status_expire_candidate": 1212
  },
  "classification_counts": {
    "blocked_uncertain_signal_quality": 167,
    "candidate_alias_merge_later": 7,
    "candidate_expire_duplicate_fanout": 1212,
    "candidate_manual_review": 127,
    "candidate_raw_payload_review": 189,
    "preserve_company_alias": 46,
    "preserve_company_specific": 34,
    "preserve_macro_context_but_wrong_store": 147,
    "preserve_market_context_but_wrong_store": 69
  },
  "company_change_log_rows": 2471,
  "company_memory_rows": 1998,
  "company_scopes": 83,
  "db_duplicate_clusters": 108,
  "market_memory_counts": {
    "change_log": 30,
    "macro_state": 8,
    "market_memory": 2,
    "sector_states": 22
  },
  "stocktake_alias_groups": 16,
  "stocktake_duplicate_clusters": 107,
  "stocktake_provenance_rows": 1998,
  "stocktake_scope_rows": 16
}
```

## Current Cleanup Semantics

The current `CompanyMemoryStore.expire_entry()` preserves statement/source fields but updates `status`, `closed_at`, and `last_seen_at`, and writes a `change_log` event. This supports a future status-expire cleanup after backup and approval. It does not support quarantine.
