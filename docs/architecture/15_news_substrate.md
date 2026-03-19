# 15. Canonical News Substrate

## Purpose

News is the **canonical news substrate** for Tenn: one RAG store, one logical workflow, many ingest sources. This document defines the architecture so the system does not fragment into multiple news DBs or hidden paths.

## Design principles

- **One canonical news RAG DB:** `reports/qual_context/news.sqlite`. No `news_newspaper4k.sqlite`, `news_rss.sqlite`, or `news_gdelt.sqlite` in production.
- **Deterministic rebuildability:** Full refresh from scratch must be reproducible and idempotent.
- **Provenance by corpus:** Every chunk has a `corpus` label (e.g. `news_eodhd`, `news_gdelt_v2`, `news_newspaper4k`, `news_asx_rss`). Cockpit and tooling filter by corpus when needed.
- **No hidden ingestion path:** All sources are explicit; the orchestrator is the single entrypoint for “run news pipeline”.
- **Idempotent full refresh:** Re-running the full pipeline with `--full-rebuild` replaces the canonical DB; incremental runs update/append.
- **No silent duplication:** Chunk IDs are globally unique (`chunk_id` primary key); verification script checks for duplicates and missing invariants.

## Layer 1 — Raw ingest (many sources, stay separate)

Ingest modules remain **source-specific**. Do not merge into one monster script.

| Source | Entrypoint / location | Output |
|--------|----------------------|--------|
| EODHD API | `fetch_daily_news.py` (provider `eodhd`) | Writes to `news_articles.sqlite` |
| GDELT API | `fetch_daily_news.py` (provider `gdelt`) | Writes to `news_articles.sqlite` |
| WorldMonitor | `fetch_daily_news.py` (provider `worldmonitor`) | Writes to `news_articles.sqlite` |
| URL archive snapshots (local/rendered) | `archive_news_urls.py` | Archived/disabled (implementation parked under `scripts/archive/legacy_cleanup_20260309/`) |
| RSS / Atom | `ingest_asx_rss_headlines.py` | JSONL (fed to Layer 3) |
| newspaper4k (Kalkine, AFR, etc.) | `integrations/newspaper4k_au/collect_au_finance_news.py` | JSONL (fed to Layer 3) |
| GDELT DOC JSONL | `fetch_gdelt_doc_api.py` | JSONL (fed to Layer 3) |
| Hugging Face dataset | `build_news_context_db.py --dataset-id ...` | Direct to Layer 3 (optional) |

Notes:
- EODHD live fallback is automatically enabled when local captures are missing and `EODHD_API_KEY` is present.
- `fetch_daily_news.py` / `backfill_news.py` auto-finalize stale `provider_runs` rows stuck in `running` before new ingest starts.

## Layer 2 — Canonical article schema

All ingest paths that feed the **single** RAG builder must produce (or be converted to) a canonical article shape.

**Canonical keys (after normalization):** `document_id`, `ticker`, `title`, `body`, `source`, `published_at`, `corpus`, `url`, `provider`, `topic`, `description`.

**Required for validation:** at least one stable identifier (`document_id` / `id` / `record_id` / `guid`), `published_at` (or `date`), and at least one of `title` or `body` (or `text` / `content`).

**Enforcement:**

- **Schema module:** `scripts/news_pipeline/canonical_article_schema.py` — defines `CANONICAL_KEYS`, `validate_canonical_article(row)`, and `normalize_to_canonical(row)`.
- **CLI validator:** `scripts/validate_news_jsonl_schema.py <input.jsonl>` — validates a JSONL file before Layer 3; use for newspaper4k or any JSONL ingest. Optional `--strict` (require both title and body), `--max-errors`, `--out-json`.

Chunk builder for API-sourced articles reads from `news_articles.sqlite` (schema: `articles` + `entity_links`) and maps to the same logical fields when writing chunks.

## Layer 3 — Single RAG builder target

All news chunks are written to **one** SQLite DB:

- **Path:** `reports/qual_context/news.sqlite`
- **Table:** `context_chunks` (see qualitative context / RAG contract docs)
- **Writers:**
  1. `build_news_chunks.py`: reads `news_articles.sqlite`, writes chunks with corpus labels `news_eodhd`, `news_gdelt_v2`, `news_rss_v2` (from provider).
  2. `build_news_context_db.py`: reads JSONL (newspaper4k, RSS, GDELT, or HF), writes chunks with configurable corpus (e.g. `news_newspaper4k`, `news_asx_rss`, `news`).

Never use a different output path for production news (e.g. no `news_newspaper4k.sqlite`). Use corpus labels to differentiate.

## Layer 4 — Consumer

- **Cockpit** (and any other consumer) reads only `reports/qual_context/news.sqlite`, configured via `rag.news_context.db_path`.
- Filtering by corpus is done with `corpus_filter` / `exclude_corpus_filter` when needed.

## Orchestrator

- **Single entrypoint:** `scripts/run_news_pipeline.py`
- Responsibilities:
  0. Preflight stale-run sweep in `news_articles.sqlite` (finalize old `running` rows before ingest).
  1. Run API ingests (EODHD, GDELT, WorldMonitor) → `news_articles.sqlite`.
  2. Optionally run newspaper4k collector → JSONL.
  3. Optionally run RSS ingest → JSONL.
  4. Archive snapshot stage is currently parked/disabled.
  5. Run `build_news_chunks.py` (articles → `news.sqlite`).
  6. Run `build_news_context_db.py` for each JSONL source into the **same** `news.sqlite` (no `--reset-output` after the first write).
  7. Log counts per corpus.
  8. Optionally run verification script (counts, duplicate check, invariants).

- **Full rebuild:** With `--full-rebuild`, remove existing `news.sqlite` first, then run all steps so the DB is rebuilt from scratch and remains deterministic.

## Verification

- **Script:** `scripts/verify_news_context_db.py`
- Checks:
  - Count per corpus.
  - Count per ticker (or company).
  - Duplicate `chunk_id` (must be zero).
- Exit non-zero if any invariant fails.

## Drift detection

- **Script:** `scripts/detect_news_context_drift.py`
- Compares current `news.sqlite` to a saved baseline (corpus counts, total chunks).
- **Baseline:** Save with `--save-baseline` (writes `reports/qual_context/news_baseline.json` by default). After a known-good run, run once with `--save-baseline`; then in CI or after pipeline runs use `--baseline` to compare.
- **Rules:** `--tolerance-pct 25` (default): flag drift if any baseline corpus drops by more than 25%. `--fail-on-new-corpus`: treat new corpora as drift. Missing baseline corpus is drift by default; use `--no-fail-on-missing-corpus` to allow.
- **Output:** JSON report with `drift_detected`, `reasons`, `actual`, `baseline`, `deltas`. Exit 1 if drift detected.
- Use in CI or as a post-pipeline check to catch regressions or unexpected changes.

## Invariants (lock down)

1. **Single DB:** Production uses exactly one news context DB path: `reports/qual_context/news.sqlite`.
2. **Corpus labels:** Every chunk has a non-empty `corpus` from a fixed set (eodhd, gdelt, worldmonitor, rss, newspaper4k, etc.).
3. **Unique chunk IDs:** `(chunk_id)` is primary key; no duplicate IDs across all sources.
4. **Idempotent rebuild:** `run_news_pipeline.py --full-rebuild` produces a deterministic DB from current ingest state.
5. **No fragmented DBs:** Do not create or reference `news_<source>.sqlite` for production RAG.

## Baseline update policy

- **Committed:** `reports/qual_context/news_baseline.json` is in git. Update only after a deliberate full rebuild (see `docs/ops/news_baseline_policy.md`).
- **Ritual:** `run_news_pipeline.py --full-rebuild --verify` then `detect_news_context_drift.py --save-baseline` then commit with message `chore(news): update baseline after rebuild`.

## Tests

- **Schema:** `scripts/test_news_canonical_schema.py` — `normalize_to_canonical()`, `validate_canonical_article()` strict/non-strict.
- **Drift:** `scripts/test_detect_news_context_drift.py` — missing corpus triggers drift, tolerance behaviour, `--no-fail-on-missing-corpus`.

## References

- RAG contract and schema: `07_rag_contract.md`, `build_qualitative_context_db.py` (ChunkRecord, store_sqlite).
- News pipeline scripts: `fetch_daily_news.py`, `build_news_chunks.py`, `build_news_context_db.py`.
- Archived snapshot stage (parked): `scripts/archive/legacy_cleanup_20260309/archive_news_urls.py`.
- Stale-run sweep utility: `scripts/sweep_stale_news_runs.py`.
- Canonical schema: `scripts/news_pipeline/canonical_article_schema.py`; validator CLI: `validate_news_jsonl_schema.py`.
- Drift harness: `scripts/detect_news_context_drift.py`; baseline path: `reports/qual_context/news_baseline.json`; hash signals: `chunk_id_sample_hash`, `doc_id_sample_hash`, `top_sources_hash`.
- Baseline policy: `docs/ops/news_baseline_policy.md`.
- Isolated collector: `integrations/newspaper4k_au/README.md`.
