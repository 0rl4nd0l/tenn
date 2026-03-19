# News Sparsity Investigation

**Date:** 2026-03-01  
**Scope:** Canonical news substrate (`reports/qual_context/news.sqlite`, `news_articles.sqlite`), ingest pipeline, and provider runs.

## Summary

News sparsity is primarily caused by **repeated API ingest failures**, not by lack of sources or configuration. Most EODHD and GDELT runs return **0 fetched, 0 inserted** and are marked `partial_failed` or `failed`. The only successful EODHD and GDELT runs are from 2026-02-25 and 2026-02-26 respectively; since then, ingest has not added new articles from those providers.

## 2026-03-08 update

Mitigations have been applied since this report was written:

- EODHD capture policy now auto-enables live fallback when captures are missing and `EODHD_API_KEY` is present (no extra flag required in that case).
- Ingest wrappers now finalize runs as `failed` even on interruptions (`KeyboardInterrupt` / `SystemExit`), preventing stale `running` rows for new runs.
- `fetch_daily_news.py` and `backfill_news.py` now auto-sweep stale `provider_runs` stuck in `running` (default older than 2 hours).
- Manual/ops sweep command added: `scripts/sweep_stale_news_runs.py`.

Current blocker remains upstream connectivity in this environment (DNS/network resolution failures across EODHD, GDELT, and WorldMonitor), which still yields zero new inserts when the providers cannot be reached.

---

## 1. Current state

### Canonical DB (`news.sqlite`)

| Metric | Value |
|--------|--------|
| **Total chunks** | 1,928 |
| **Baseline total** (from `news_baseline.json`) | 1,884 |

**By corpus:**

| Corpus | Chunks | Note |
|--------|--------|------|
| news_eodhd | 1,616 | ~84% of total |
| news_newspaper4k | 260 | |
| news_gdelt_v2 | 43 | |
| news_worldmonitor | 9 | |

**Temporal spread (chunks by day):**

- **news_eodhd:** 11 (Feb 23) + 17 (Feb 24) + **1,588 (Feb 25)** — almost all from a single day.
- **news_gdelt_v2:** 14 + 21 + 8 across Feb 24–26.
- **news_newspaper4k:** Spread Feb 4–27; 182 on Feb 27.
- **news_worldmonitor:** All 9 on Feb 19.

### Staging DB (`news_articles.sqlite`)

| Metric | Value |
|--------|--------|
| **Articles** | 254 |
| **Entity links** | 1,943 |
| **Date range** | 2026-02-19 → 2026-02-26 (~7 days) |

**By provider:** eodhd 202, gdelt 43, worldmonitor 9.

---

## 2. Root cause: ingest failures

### Provider run outcomes (recent)

From `provider_runs` in `news_articles.sqlite`:

- **EODHD**
  - **Only successful run with data:** `eodhd_daily_2e045081a015` (2026-02-25): 209 fetched, 202 inserted.
  - All other EODHD daily/backfill runs: **0 fetched, 0 inserted**, status `partial_failed` or `failed`.
- **GDELT**
  - **Only successful run with data:** `gdelt_daily_c546963baddc` (2026-02-26): 50 fetched, 43 inserted.
  - All other GDELT runs: **0 fetched, 0 inserted**, `partial_failed` or `failed`.
- **WorldMonitor**
  - One backfill: 9 fetched, 9 inserted (success). Daily runs: 0 fetched but status success (empty response).

### Failure reasons (from run reports)

**EODHD** (`provider_fetch_error`):

```text
EODHD capture contract not found. Add JSON/JSONL captures under
/home/l4nd0/tenn/reports/provider_captures/eodhd or use --allow-missing-eodhd-captures.
```

- Historical behavior (at report time) required explicit live flags or capture contracts.
- Current behavior auto-enables live fallback when captures are missing and `EODHD_API_KEY` is present.
- Offline/CI capture mode is still supported by placing JSON/JSONL files under `reports/provider_captures/eodhd`.

**GDELT** (`provider_fetch_error`):

```text
GDELT returned non-JSON payload: Expecting value: line 1 column 1 (char 0) | preview='Your query was too short or too long.'
```

- GDELT API is rejecting the request (query length or shape). Needs investigation of how the query/window is built (e.g. date range, ticker list) and GDELT API limits.

---

## 3. Orchestrator gap (historical)

At report time, `scripts/run_news_pipeline.py` invoking `fetch_daily_news.py` without explicit live flags caused EODHD failures when capture contracts were absent.

With current policy, live fallback occurs automatically when captures are missing and `EODHD_API_KEY` is present. Explicit flags are now optional overrides, not mandatory for this fallback path.

---

## 4. Other sparsity dimensions

- **RSS (ASX):** Architecture doc and scripts support `news_asx_rss` (e.g. `ingest_asx_rss_headlines.py` → JSONL → `build_news_context_db`). The current canonical DB has **no** `news_asx_rss` corpus; that path is not wired into `run_news_pipeline.py` by default. Adding RSS to the default pipeline would increase coverage.
- **Ticker skew:** Many ASX tickers have few or no chunks (e.g. BHP 9, WES 9); one company code (“BNZ”) has 812 chunks — may be name collision or one very active issuer. Optional follow-up: review entity linker and ticker list for coverage and noise.
- **WorldMonitor:** Only 9 articles total; design may be ASX-wide/theater signals rather than volume. No change suggested without product intent.

---

## 5. Recommendations

1. **Fix EODHD ingest (live API):**
   - Set `EODHD_API_KEY` in the environment that runs the pipeline.
   - With current policy, fallback to live is automatic when captures are missing and key is present.
   - Use `--allow-missing-eodhd-captures` only when you want explicit live mode override.

2. **Fix GDELT ingest:**
   - Reproduce the “query too short or too long” error (same date range and ticker list as in the failing run).
   - Adjust GDELT query construction (e.g. date range, number of tickers, or request shape) to stay within API limits; add tests or run a probe script so this is validated in CI or before backfill.

3. **Optional: add RSS to default pipeline:**
   - In `run_news_pipeline.py`, add a step to run `ingest_asx_rss_headlines.py` (or equivalent) and append the resulting JSONL to the canonical DB with corpus `news_asx_rss`, so RSS is part of the standard run.

---

## 6. EODHD vs ASX, and why GDELT is on a small period

### EODHD: little or no ASX in the mix

- The EODHD provider does two things in `fetch_window()` (see `scripts/news_pipeline/providers/eodhd.py`):
  1. **Market feed:** `fetch_market_window()` is called first — no symbol is passed, so the EODHD API returns **global market news** (US-heavy: PEP, FSLR, BlackRock dividends, etc.).
  2. **Per-ticker:** then for each ASX ticker it calls `fetch_symbol_window(ticker=...)` with `symbol_suffix=".AU"` (e.g. BHP.AU, CBA.AU).
- The **market** call is a single request with a high limit (e.g. 200 items) and dominates the result set. Symbol-specific ASX news is a smaller share unless the run is configured to emphasise symbols (e.g. more tickers, or skipping market).
- So “EODHD doesn’t seem to have any ASX” is expected with the current design: the bulk of what’s ingested is the **global market** feed; ASX content is in the per-symbol responses.
- **Fix applied:** `--eodhd-symbols-only` is available on `fetch_daily_news.py` and `run_news_pipeline.py`. When set, the provider skips the global market feed and fetches only per-symbol ASX news (`.AU`).

### GDELT: why it’s only a short period

- GDELT content **looks good** (ASX earnings, broker calls, commodities) but we only have **one successful run** (2026-02-26: 50 fetched, 43 inserted). All other GDELT runs in the DB are **failed** or **partial_failed** with 0 fetched.
- Failure reason: **GDELT API rejects the request** with `Your query was too short or too long.` So the “small period” is simply that **ingest has been failing almost every time**; the only data we have is from that single successful run.
- The query is built in `gdelt.py` from a base clause plus batched ticker clauses `(SYM OR SYM.AX OR "ASX:SYM")`. Defaults were 10 tickers × 5 batches; the full query string exceeded GDELT’s length limit.
- **Fix applied:** Defaults in `gdelt.py` and CLI are now `ticker_query_batch_size=5`, `max_ticker_batches=3`. Re-run daily (and optionally backfill) so more runs succeed and the covered period grows.

### Newspaper4k over a large window

- To run newspaper4k with an extended lookback and higher article cap (e.g. 90 days, 2000 articles), use the pipeline’s backfill step and override lookback/max-articles. Example (from repo root):

```bash
python scripts/run_news_pipeline.py \
  --run-newspaper4k-backfill \
  --newspaper4k-backfill-lookback-hours 2160 \
  --newspaper4k-backfill-max-articles 2000
```

- `2160` = 90 days; for 60 days use `1440`, for 30 days use `720`. Increase `--newspaper4k-backfill-max-articles` if you want more articles (e.g. `3000`). To only run the collector without rebuilding the full pipeline, use the integration script directly:

```bash
integrations/newspaper4k_au/.venv/bin/python integrations/newspaper4k_au/collect_au_finance_news.py \
  --sources-file integrations/newspaper4k_au/sources_finance_no_sub_plus_capitalbrief_kalkine.txt \
  --output-jsonl integrations/newspaper4k_au/out/au_finance_news_backfill.jsonl \
  --manifest-json integrations/newspaper4k_au/out/au_finance_manifest_backfill.json \
  --lookback-hours 2160 \
  --max-total-articles 2000
```

- Then append that JSONL via `run_news_pipeline.py --newspaper4k-jsonl integrations/newspaper4k_au/out/au_finance_news_backfill.jsonl` (and optionally skip API/chunk-builder steps as needed).

### Why so few articles from newspaper4k backfill?

Backfill can return “heaps” of candidates from the collector, but most get dropped by **URL and keyword gates** before they are written to JSONL:

1. **Finance URL path gate**  
   By default, every URL must contain one of: `/business`, `/markets`, `/market`, `/companies`, `/economy`, `/finance`, `/invest`, `/stocks`, `/shares`, `/wealth`, `/bank`, `/briefing`.  
   Sites that use other paths (e.g. Capital Brief, Kalkine) had **all** links counted as `url_filtered_non_finance_path` and dropped.

2. **Article URL shape gate**  
   Links must “look like” article URLs (e.g. date in path, or segment rules). Many valid article URLs from these domains were counted as `url_filtered_non_article_path` and dropped.

3. **RSS vs “backfill”**  
   For RSS sources (e.g. Guardian, ABC), the feed only exposes a small window (e.g. last 20–50 items). Lookback only filters by publish date; it does not increase how many items the feed returns. So you only get whatever the feed currently exposes that passes the gates.

4. **Discovery**  
   For `auto` sources, the collector first tries feed URLs, then scrapes the homepage for links. One discovery error (e.g. Capital Brief) can reduce how many candidates are even considered.

**Fix applied:** The pipeline now passes **`--finance-url-gate-exempt-domains`** and **`--article-url-gate-exempt-domains`** for `capitalbrief.com`, `kalkinemedia.com`, and `kalkinemedia.com.au` when running the newspaper4k collector (both daily and backfill). Links from these domains are no longer dropped solely for missing the generic path tokens or article-URL shape, so you should see more kept articles from those sources. Re-run the backfill to confirm. To add more sources or relax gates further, use the collector’s `--disable-finance-url-gate` or add more domains to the exempt lists.

**Monitoring:**
   - After fixes, run the pipeline (or daily job) and confirm `provider_runs` shows non-zero fetched/inserted for EODHD (and GDELT when fixed).
   - Re-run `verify_news_context_db.py` and refresh the baseline when appropriate; keep an eye on chunks-by-day to avoid single-day dominance.

---

## 6. Files and commands referenced

- **Verification:** `scripts/verify_news_context_db.py --db reports/qual_context/news.sqlite`
- **Orchestrator:** `scripts/run_news_pipeline.py` (see steps that call `fetch_daily_news.py`)
- **Ingest:** `scripts/fetch_daily_news.py` (EODHD live fallback auto when capture is missing + `EODHD_API_KEY`; explicit override `--allow-missing-eodhd-captures`)
- **Stale run cleanup:** `scripts/sweep_stale_news_runs.py`
- **Run reports:** `reports/qual_context/news_runs/<run_id>/report_summary.json`, `failure_bucket_samples/provider_fetch_error.jsonl`
- **Architecture:** `docs/architecture/15_news_substrate.md`
- **Baseline policy:** `docs/ops/news_baseline_policy.md`
