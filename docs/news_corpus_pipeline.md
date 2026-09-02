# News Corpus Pipeline (Experimental)

## Compliance status

Dataset target: `Brianferrell787/financial-news-multisource` (Hugging Face).

Compliance readout from dataset card:
- Access is **gated**.
- Dataset `license` is **`other`**.
- Card states article content remains under each original publisher's copyright/terms.

Operational decision in this repo:
- Treat news ingestion/indexing as **research-only (R&D)** by default.
- The ingestion script requires explicit acknowledgement flag: `--research-only-ack`.
- Production use should only proceed after legal review of source-level redistribution/serving rights.

## Isolation of concerns

- Filing metric extraction pipeline is unchanged.
- News uses separate corpus label: `corpus=news`.
- News is written to a separate DB artifact by default: `reports/qual_context/news.sqlite`.
- Deterministic news benchmark/eval fixture DB lives at: `reports/qual_context/news_eval.sqlite`.
- Query-time filters support selecting or excluding corpora (`--corpus-filter`, `--exclude-corpus-filter`).
- Cockpit's checked-in production config pins news retrieval to:
  - `rag.news_context.db_path=reports/qual_context/news.sqlite`
  - `rag.news_context.corpus_filter=news`
  - `rag.news_context.ticker_match_mode=soft`
- `financial-engine_v2/config/cockpit.local.yaml` disables news context for lightweight local runs.

## Nightly ASX news operations

The operational wrapper is `financial-engine_v2/scripts/nightly_news.sh`. It is the cron-friendly path for
collecting daily ASX news, updating the RAG-compatible SQLite fallback, and writing machine-readable health
artifacts. The script derives the repo root from its own path, then runs from the repository root.

Default cron target documented in the wrapper:

```cron
0 2 * * * /home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh
```

### Runtime flow

| Phase | Codepath | Output |
| --- | --- | --- |
| `initializing` | validates `scripts/fetch_daily_news.py`, `scripts/build_news_chunks.py`, ticker universe, and identity map | exits before fetch if required inputs are missing |
| `fetch` | `scripts/fetch_daily_news.py` | writes/updates `news_articles.sqlite` and per-provider reports under `news_runs/` |
| `build` | `scripts/build_news_chunks.py` | writes `context_chunks` into `news.sqlite` |
| `health` | inline wrapper health check | validates fetch/upsert/chunk counts, provider run status, context freshness, and recent chunks |
| `finish` | wrapper exit trap | writes final status JSON and prunes old nightly artifacts |

The wrapper's `NIGHTLY_NEWS_DRY_RUN=1` path is not the same as
`scripts/fetch_daily_news.py --dry-run`. Wrapper dry-run validates required
inputs and writes status/health JSON without calling fetch or build. The fetch
script's `--dry-run` flag prints a resolved run plan and exits without writes.

### Default paths and artifacts

Unless overridden, the wrapper writes operational logs to `reports/ops_checks/nightly/` and news artifacts to
`reports/qual_context/`. On hosts with `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context`, that
mounted artifact root is preferred. The exit trap keeps the 30 most recent files of each `nightly_news_*`
pattern in the log directory.

| Artifact | Default or pattern | Purpose |
| --- | --- | --- |
| article store | `reports/qual_context/news_articles.sqlite` | canonical fetched articles and provider run metadata |
| context DB | `reports/qual_context/news.sqlite` | RAG-compatible `context_chunks` for cockpit news context |
| run reports | `reports/qual_context/news_runs/<run_id>/` | provider-level ingest reports |
| wrapper log | `reports/ops_checks/nightly/nightly_news_<stamp>.log` | stdout/stderr from the wrapper and child commands |
| status JSON | `nightly_news_<stamp>.status.json` | top-level status, phase statuses, effective config, paths, and artifact existence |
| fetch JSON | `nightly_news_<stamp>.fetch.json` | JSON emitted by `fetch_daily_news.py`, including provider run IDs |
| chunk JSON | `nightly_news_<stamp>.chunks.json` | JSON emitted by `build_news_chunks.py`, including chunk stats |
| health JSON | `nightly_news_<stamp>.health.json` | health totals, thresholds, context before/after snapshot, and problem list |

### Common configuration knobs

The wrapper accepts `NIGHTLY_NEWS_*` variables first, with selected `NEWS_*` fallbacks for compatibility.

| Variable | Default | Notes |
| --- | --- | --- |
| `NIGHTLY_NEWS_DRY_RUN` | `0` | `1` validates inputs and writes status/health JSON without fetch/build writes. |
| `NIGHTLY_NEWS_PYTHON` | `python3` | If unset and provider includes `newspaper4k`, the wrapper uses `integrations/newspaper4k_au/.venv/bin/python` when present. |
| `NIGHTLY_NEWS_PROVIDERS` | `newspaper4k` | Comma-separated: `newspaper4k,eodhd,gdelt,worldmonitor`. |
| `NIGHTLY_NEWS_SINCE_HOURS` | `36` | Lookback window passed to fetch. |
| `NIGHTLY_NEWS_LANE` | `high_precision` | Entity-link lane; `high_recall` is also accepted by fetch/build scripts. |
| `NIGHTLY_NEWS_MAX_TICKERS` | `0` | Optional cap for safe test runs; `0` means no cap. |
| `NIGHTLY_NEWS_TICKERS` | empty | Explicit comma/space ticker list; overrides file-driven selection. |
| `NIGHTLY_NEWS_ASX_WIDE` | `0` | `1` asks providers for ASX-wide news instead of ticker-expanded queries. |
| `TENN_NEWS_ARTIFACT_ROOT` | host mount or `reports/qual_context` | Base directory for `news_articles.sqlite`, `news.sqlite`, and `news_runs/`. |
| `TENN_NEWS_ARTICLES_DB` | `${TENN_NEWS_ARTIFACT_ROOT}/news_articles.sqlite` | Override only when splitting article and context stores deliberately. |
| `TENN_NEWS_CONTEXT_DB` | `${TENN_NEWS_ARTIFACT_ROOT}/news.sqlite` | Shared with cockpit as a config/env override. |
| `NIGHTLY_NEWS_MIN_FETCHED` | `1` | Health fails when total fetched articles are below this threshold. |
| `NIGHTLY_NEWS_MIN_UPSERTED` | `1` | Health fails on duplicate-only runs by default. |
| `NIGHTLY_NEWS_MIN_CHUNKS` | `1` | Health fails if the build writes too few chunks. |
| `NIGHTLY_NEWS_MIN_CONTEXT_RECENT_CHUNKS` | `NIGHTLY_NEWS_MIN_CHUNKS` | Health fails if recent chunks within the current fetch window are below this value. |
| `NIGHTLY_NEWS_MAX_ERRORS` | `0` | Health fails if provider errors exceed this value. |
| `NIGHTLY_NEWS_REQUIRE_CONTEXT_FRESH` | `1` | `0` disables the "context DB changed this run" freshness check. |
| `NIGHTLY_NEWS_EMBED_BACKEND` / `NEWS_EMBED_BACKEND` | `hash` | Embedding backend passed to `build_news_chunks.py`. |

Provider-specific knobs mirror `scripts/fetch_daily_news.py`: GDELT retry/batch settings use
`NIGHTLY_NEWS_GDELT_*`, and newspaper4k source/limit/timeout settings use `NIGHTLY_NEWS_NEWSPAPER4K_*`.
By default `NIGHTLY_NEWS_NEWSPAPER4K_NO_PLAYWRIGHT=1` (RSS-only, no Playwright). The default
newspaper4k source profile is `daily`.

### Safe smoke checks

Validate the wrapper contract without external network writes:

```bash
NIGHTLY_NEWS_DRY_RUN=1 \
NIGHTLY_NEWS_LOG_DIR=/tmp/tenn-nightly-news-smoke \
TENN_NEWS_ARTIFACT_ROOT=/tmp/tenn-news-artifacts \
financial-engine_v2/scripts/nightly_news.sh
```

Run a bounded provider test:

```bash
NIGHTLY_NEWS_PROVIDERS=eodhd \
NIGHTLY_NEWS_MAX_TICKERS=1 \
NIGHTLY_NEWS_LOG_DIR=/tmp/tenn-nightly-news-smoke \
TENN_NEWS_ARTIFACT_ROOT=/tmp/tenn-news-artifacts \
NEWS_EODHD_CAPTURE_DIR=reports/provider_captures/eodhd \
financial-engine_v2/scripts/nightly_news.sh
```

For live EODHD use, set `NEWS_EODHD_API_KEY`. By default the EODHD provider expects capture contracts; set
`NIGHTLY_NEWS_ALLOW_MISSING_EODHD_CAPTURES=1` (or `NEWS_ALLOW_MISSING_EODHD_CAPTURES=1`) only when
intentional live access without captures is acceptable.

### Cockpit news DB path precedence

Cockpit resolves the news context DB from config plus environment overrides
(`financial-engine_v2/cockpit/core/config.py`):

1. `COCKPIT_NEWS_DB_PATH`
2. `TENN_NEWS_CONTEXT_DB`
3. `TENN_NEWS_ARTIFACT_ROOT/news.sqlite`
4. configured `rag.news_context.db_path`

Optional retrieval overrides:

- `COCKPIT_NEWS_CORPUS_FILTER` sets `rag.news_context.corpus_filter`
- `COCKPIT_NEWS_TICKER_MATCH_MODE` must be `soft` or `strict`

When the configured path is the default relative `reports/qual_context/news.sqlite`,
`resolve_news_context_db_path()` chooses the freshest existing file among the nightly
artifact root (`/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/news.sqlite`),
the repo-relative path, and the parent-repo-relative path. An explicit absolute DB path
is not overridden by the nightly artifact root. If no news DB exists and news context is
not explicitly required, cockpit can fall back to `reports/qual_context/news_eval.sqlite`
when present.

### Troubleshooting quick map

| Symptom | Where to look | Likely cause |
| --- | --- | --- |
| `failed_phase=initializing` | status JSON and log | missing script, ticker universe (`financial-engine_v2/data/raw/asx_ticker_universe.txt`), or `financial-engine_v2/config/ticker_identity_map.json` |
| `fetched 0 below minimum` | health JSON `problems`, provider report | empty provider response, capture fixture missing, or too-narrow `NIGHTLY_NEWS_SINCE_HOURS` |
| `inserted/upserted 0 below minimum 1` | health JSON `totals.deduped` | duplicate-only run; lower `NIGHTLY_NEWS_MIN_UPSERTED` only for intentional idempotence checks |
| `context SQLite fallback did not change during current run` | health JSON `context.before/after` | build did not update `news.sqlite`, wrong `TENN_NEWS_CONTEXT_DB`, or freshness check should be disabled for a replay |
| `context recent news chunks 0 below minimum` | health JSON `context.recent_cutoff_utc` | articles are outside the fetch window or `published_at` is missing/stale |
| cockpit does not see nightly news | cockpit startup config and resolved DB path | set `COCKPIT_NEWS_DB_PATH` or share `TENN_NEWS_CONTEXT_DB` / `TENN_NEWS_ARTIFACT_ROOT` with the wrapper; local profile disables news context |

## Build commands

Connected (HF gated dataset, token required):

```bash
export HF_TOKEN=...
python3 scripts/build_news_context_db.py \
  --dataset-id Brianferrell787/financial-news-multisource \
  --split train \
  --dataset-cache-dir /tmp/hf_cache \
  --db sqlite \
  --out reports/qual_context/news.sqlite \
  --embed-backend sentence-transformers \
  --embed-model BAAI/bge-large-en-v1.5 \
  --st-device cpu \
  --row-batch-size 512 \
  --progress-every 50000 \
  --manifest-json reports/qual_context/news_build_manifest.json \
  --manifest-write-every 1 \
  --reset-output \
  --reset-dedupe-db \
  --research-only-ack
```

Offline/local JSONL mode:

```bash
python3 scripts/build_news_context_db.py \
  --input-path reports/news_eval_input/news_sample.jsonl \
  --db sqlite \
  --out reports/qual_context/news.sqlite \
  --embed-backend sentence-transformers \
  --embed-model BAAI/bge-large-en-v1.5 \
  --st-device cpu \
  --row-batch-size 512 \
  --manifest-json reports/qual_context/news_build_manifest.json \
  --manifest-write-every 1 \
  --research-only-ack
```

Scaling note:
- For very large splits, first run with `--max-rows` (for example `10000`) to validate end-to-end.
- `--dedupe-db` persists URL/exact/near dedupe state to resume long runs safely.
- Use `--reset-output --reset-dedupe-db` only when intentionally starting from scratch.

## GDELT supplement path

If you want broader source discovery without depending on a single curated dataset, you can pull from GDELT DOC API and feed it into the same `build_news_context_db.py` pipeline.

Step 1: fetch GDELT article candidates to JSONL.

```bash
python3 scripts/fetch_gdelt_doc_api.py \
  --query "(ASX OR Australian shares OR RBA) AND (earnings OR guidance OR downgrade)" \
  --timespan 7days \
  --max-records 250 \
  --out reports/news_eval_input/gdelt_doc_asx.jsonl
```

Step 2: index that JSONL with the existing news corpus builder.

```bash
python3 scripts/build_news_context_db.py \
  --input-path reports/news_eval_input/gdelt_doc_asx.jsonl \
  --corpus news \
  --doc-type news_article \
  --db sqlite \
  --out reports/qual_context/news.sqlite \
  --embed-backend sentence-transformers \
  --embed-model BAAI/bge-large-en-v1.5 \
  --st-device cpu \
  --use-default-asx-allowlist \
  --ticker-allowlist-drop-nonmatching \
  --row-batch-size 512 \
  --manifest-json reports/qual_context/news_gdelt_manifest.json \
  --manifest-write-every 1 \
  --research-only-ack
```

Notes:
- `fetch_gdelt_doc_api.py` backfills article page text by default; use `--skip-article-fetch` for metadata-only mode.
- If you run metadata-only mode, lower `--min-text-chars` on `build_news_context_db.py` or most rows will be filtered as short.
- GDELT is best treated as a discovery/index layer; preserve original URL/source metadata for attribution and downstream filtering.
- Ticker contamination controls:
  - `--use-default-asx-allowlist` loads `financial-engine_v2/data/raw/asx_ticker_universe.txt`.
  - `--ticker-allowlist-drop-nonmatching` drops rows that mention tickers but none are in the allowlist.
  - If you omit `--ticker-allowlist-drop-nonmatching`, non-allowlisted tickers are stripped and rows are kept as generic `NEWS`.

Step 3: audit corpus quality after indexing.

```bash
python3 scripts/audit_news_context_db.py \
  --db reports/qual_context/news.sqlite \
  --corpus-filter news_gdelt \
  --doc-type-filter news_article \
  --use-default-asx-allowlist \
  --out-json reports/qual_context/news_gdelt_audit.json
```

Audit output includes:
- metadata coverage (`doc_date`, `published_at`, `ticker`, `url`)
- estimated article/chunk distribution
- ticker allowlist drift (`unknown_ticker_chunk_rate_pct`)
- source/domain/ticker top lists

Manifest output includes:
- rows in/kept/dropped by reason
- output chunk count and flush batch count
- dedupe DB cardinalities
- ticker coverage (`kept_rows_with_ticker`, `unique_tickers`)

## Retrieval filters

Example query (ticker/source/date filtered):

```bash
python3 scripts/build_news_context_db.py \
  --input-path reports/news_eval_input/news_sample.jsonl \
  --db sqlite \
  --out reports/qual_context/news.sqlite \
  --embed-backend sentence-transformers \
  --embed-model BAAI/bge-large-en-v1.5 \
  --st-device cpu \
  --research-only-ack \
  --query "delivery outlook margin pressure" \
  --doc-type-filter news_article \
  --ticker-filter TSLA \
  --source-filter "Yahoo Finance" \
  --date-from 2026-01-01 \
  --date-to 2026-12-31 \
  --top-k 8
```

## Sentiment feature pilot (advisory-only)

To borrow the useful part of lightweight news-sentiment bots without introducing
auto-trading behavior, build daily ticker/window sentiment features from
`reports/qual_context/news.sqlite`.

```bash
python3 scripts/build_news_sentiment_features.py \
  --news-db reports/qual_context/news.sqlite \
  --windows 7,30,90 \
  --half-life-days 7 \
  --as-of-date 2026-02-24 \
  --out-json reports/news_sentiment_features.json \
  --out-csv reports/news_sentiment_features.csv \
  --out-sqlite reports/news_sentiment_features.sqlite
```

Outputs:
- `reports/news_sentiment_features.json`: run metadata + ticker-window rows.
- `reports/news_sentiment_features.csv`: easy review/slicing by ticker/window.
- `reports/news_sentiment_features.sqlite`:
  - `news_sentiment_article_scores` (per-article scored records)
  - `news_sentiment_ticker_windows` (recency-weighted aggregates)
- If your corpus is historical/stale, recent windows like `7,30,90` may return zero rows.
  Use `--as-of-date` aligned to the backtest date or larger windows for retrospective analysis.

Optional LLM article scorer (fallbacks to lexical if unavailable):

```bash
python3 scripts/build_news_sentiment_features.py \
  --news-db reports/qual_context/news.sqlite \
  --scorer ollama \
  --ollama-endpoint http://127.0.0.1:11434 \
  --ollama-model qwen2.5:7b-instruct
```
