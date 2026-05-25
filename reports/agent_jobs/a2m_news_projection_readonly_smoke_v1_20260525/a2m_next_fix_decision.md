# A2M Next Fix Decision

## Selected Next Action

`a2m_news_projection_status_reporting_safe_extension_v1_20260525`

## Why

The read-only smoke proves that A2M can be retrieved by the current Qdrant-backed user-visible news query route. It also proves that canonical NVMe SQLite projection files are absent and legacy `/mnt/sdb2` SQLite files contain A2M evidence outside the current consumer path.

The smallest safe next step is therefore not data repair. It is status/reporting clarity: distinguish Qdrant retrieval health, canonical SQLite projection health, legacy SQLite provenance, and article-detail fallback availability in durable status/reporting artifacts.

## Boundaries For The Next Task

- File-bounded and task-carded.
- No DB, Qdrant, news-store, memory, or production-data writes.
- No projection rebuild, ingestion, resync, reindex, backfill, or refresh.
- No Cockpit route behavior change unless a later exact-files task card and registry check explicitly allow it.
- No source-label, alias, parser, extraction, or metric-scoring changes.

## Deferred Actions

- `news_projection_path_contract_test_v1_20260525`: useful later, but the current smoke first needs status/reporting language pinned down.
- `a2m_projection_rebuild_planning_audit_v1_20260525`: not the smallest next step because user-visible Qdrant retrieval works and no rebuild target is approved.
- `a2m_news_projection_path_metadata_safe_extension_v1_20260525`: partially relevant, but less direct than status/reporting because the observed gap is what operators and users can see.
- `no-op/defer`: not selected because a safe, non-data-mutating reporting/status improvement is justified.
