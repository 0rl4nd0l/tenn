# Domain Skill: News Substrate

## Source Trace
- `docs/architecture/15_news_substrate.md` (Confirmed)
- `docs/ops/news_baseline_policy.md` (Confirmed — referenced)
- `docs/ops/news_sparsity_investigation.md` (Confirmed — referenced)

---

## Architecture in One Line

One canonical RAG DB (`reports/qual_context/news.sqlite`) fed by many source-specific ingest modules, written through one orchestrator, consumed by one reader.

---

## The Single-DB Invariant

**Production uses exactly one news context DB:** `reports/qual_context/news.sqlite`

Do NOT create `news_newspaper4k.sqlite`, `news_rss.sqlite`, or `news_gdelt.sqlite`.
Use `corpus` labels to differentiate sources within the single DB.

---

## Layer Summary

| Layer | What It Does | Key Scripts |
|-------|-------------|-------------|
| 1 — Raw ingest | Source-specific ingest → `news_articles.sqlite` or JSONL | `fetch_daily_news.py`, `ingest_asx_rss_headlines.py`, `integrations/newspaper4k_au/collect_au_finance_news.py` |
| 2 — Schema | Normalize all sources to canonical article shape | `scripts/news_pipeline/canonical_article_schema.py` |
| 3 — RAG builder | Chunks → `news.sqlite` (`context_chunks` table) | `build_news_chunks.py`, `build_news_context_db.py` |
| 4 — Consumer | Reads only `news.sqlite`; filters by corpus | Cockpit, any RAG consumer |

**Orchestrator (single entrypoint):** `scripts/run_news_pipeline.py`

---

## Corpus Labels

Every chunk must have a non-empty `corpus`:
- `news_eodhd`
- `news_gdelt_v2`
- `news_rss_v2`
- `news_newspaper4k`
- `news_asx_rss`

Do not introduce new corpus labels without updating the baseline policy and verification script.

---

## Invariants

1. **Single DB** — one canonical path: `reports/qual_context/news.sqlite`
2. **Corpus labels** — every chunk has a non-empty corpus from the fixed set
3. **Unique chunk IDs** — `(chunk_id)` is primary key; zero duplicates
4. **Idempotent rebuild** — `run_news_pipeline.py --full-rebuild` produces a deterministic DB
5. **No fragmented DBs** — never reference `news_<source>.sqlite` for production RAG

---

## EODHD Fallback

EODHD live API is automatically enabled when:
- Local captures are missing
- `EODHD_API_KEY` is present in env

Do not document EODHD as always-on; it is a fallback. See `docs/ops/news_sparsity_investigation.md` for sparsity root cause analysis.

---

## Canonical Article Schema

Required fields after normalization: `document_id`, `ticker`, `title`, `body`, `source`, `published_at`, `corpus`, `url`, `provider`, `topic`, `description`.

Minimum for validation: at least one stable identifier + `published_at` + at least one of `title` or `body`.

Validate a JSONL file before Layer 3:
```bash
python scripts/validate_news_jsonl_schema.py <input.jsonl>
# --strict: require both title and body
```

---

## Verification

```bash
python scripts/verify_news_context_db.py
# Checks: count per corpus, count per ticker, zero duplicate chunk_id
# Exit non-zero on invariant failure
```

---

## Drift Detection

```bash
# Save baseline after a known-good run
python scripts/detect_news_context_drift.py --save-baseline

# Compare in CI or post-pipeline
python scripts/detect_news_context_drift.py --baseline reports/qual_context/news_baseline.json
```

Default tolerance: `--tolerance-pct 25` (corpus drop > 25% = drift).
Baseline file: `reports/qual_context/news_baseline.json` (committed to git).

**Do not manually edit the baseline.** Update only after a deliberate full rebuild:
```bash
python scripts/run_news_pipeline.py --full-rebuild --verify
python scripts/detect_news_context_drift.py --save-baseline
# Then commit: chore(news): update baseline after rebuild
```

---

## Full Rebuild

```bash
python scripts/run_news_pipeline.py --full-rebuild
```

Removes existing `news.sqlite` first, then runs all ingest and build steps deterministically.

Do not use `--full-rebuild` casually in production; it replaces all news context.

---

## Archived / Disabled

URL archive snapshot stage (`archive_news_urls.py`) is parked under `scripts/archive/legacy_cleanup_20260309/`. Do not re-enable without explicit task.

---

## What NOT to Do

- Do not write news chunks to any path other than `reports/qual_context/news.sqlite`.
- Do not skip `corpus` labeling.
- Do not fabricate article counts, corpus stats, or drift percentages.
- Do not modify drift tolerance thresholds to make failing checks pass.
- Do not merge new ingest sources without updating the canonical schema module and verification script.
