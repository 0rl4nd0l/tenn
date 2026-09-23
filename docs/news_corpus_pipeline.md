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
- Cockpit news retrieval defaults now pin to:
  - `rag.news_context.db_path=reports/qual_context/news.sqlite`
  - `rag.news_context.corpus_filter=news`
  - `rag.news_context.ticker_match_mode=soft`

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

## Nightly ingest wrapper

`financial-engine_v2/scripts/nightly_news.sh` is a separate path from `build_news_context_db.py`. It fetches provider articles, builds context chunks, and writes a health report. The script header records a host cron target of `0 2 * * *`; this repo does not install that crontab.

Run from anywhere:

```bash
financial-engine_v2/scripts/nightly_news.sh
```

The wrapper `cd`s to the repository root (`TENN_ROOT`).

### Phases

| Phase | What it does |
|---|---|
| `initializing` | Requires `scripts/fetch_daily_news.py`, `scripts/build_news_chunks.py`, a non-empty ticker universe, and the identity map. Counts tickers. |
| `fetch` | `scripts/fetch_daily_news.py` |
| `build` | `scripts/build_news_chunks.py --from-db <articles> --to-db <context>` |
| `health` | Reads fetch and chunk JSON plus both SQLite files. Non-empty `problems` exits 1. |
| `finish` | `on_exit` writes status JSON. Success marks this phase `success`; failure marks it `skipped`. |

Artifacts land in `NIGHTLY_NEWS_LOG_DIR` (default `reports/ops_checks/nightly`):

- `nightly_news_<stamp>.log`
- `nightly_news_<stamp>.status.json`
- `nightly_news_<stamp>.fetch.json`
- `nightly_news_<stamp>.chunks.json`
- `nightly_news_<stamp>.health.json`

Each pattern keeps the 30 newest files.

### Defaults that change behavior

| Variable | Default | Constraint |
|---|---|---|
| `NIGHTLY_NEWS_PROVIDERS` / `NEWS_PROVIDERS` | `newspaper4k` | Passed to `--providers`. Fetch accepts `newspaper4k`, `eodhd`, `gdelt`, `worldmonitor`. |
| `NIGHTLY_NEWS_SINCE_HOURS` | `36` | Lookback hours. |
| `NIGHTLY_NEWS_LANE` | `high_precision` | Also accepts `high_recall` at the fetch CLI. |
| `NIGHTLY_NEWS_MAX_TICKERS` | `0` | `0` means no cap. |
| `NIGHTLY_NEWS_DRY_RUN` | unset | `1` skips fetch and build. |
| `NIGHTLY_NEWS_PYTHON` | `python3` | When unset and `newspaper4k` is selected, fetch uses `integrations/newspaper4k_au/.venv/bin/python` if that binary is executable. Build still uses `NIGHTLY_NEWS_PYTHON` or `python3`. |
| `NIGHTLY_NEWS_EMBED_BACKEND` / `NEWS_EMBED_BACKEND` | `hash` | Chunk embed backend. |
| `NIGHTLY_NEWS_NEWSPAPER4K_NO_PLAYWRIGHT` | `1` | Adds `--newspaper4k-no-playwright`. |
| `NIGHTLY_NEWS_MIN_FETCHED` | `1` | Health floor. |
| `NIGHTLY_NEWS_MIN_UPSERTED` | `1` | Compared with provider `inserted` totals. |
| `NIGHTLY_NEWS_MIN_CHUNKS` | `1` | Compared with chunk `stats.chunks_written`. |
| `NIGHTLY_NEWS_MIN_CONTEXT_RECENT_CHUNKS` | same as min chunks | Recent `news_article` rows in the context DB. |
| `NIGHTLY_NEWS_MAX_ERRORS` | `0` | Health ceiling. |
| `NIGHTLY_NEWS_REQUIRE_CONTEXT_FRESH` | `1` | Any value other than `0` requires the context DB to change during the run. |

Artifact root, first match wins:

1. `TENN_NEWS_ARTIFACT_ROOT`
2. `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context` when that directory exists
3. `<repo>/reports/qual_context`

Databases default to `<artifact-root>/news_articles.sqlite` and `<artifact-root>/news.sqlite` (`TENN_NEWS_ARTICLES_DB`, `TENN_NEWS_CONTEXT_DB`). Ticker universe default is `financial-engine_v2/data/raw/asx_ticker_universe.txt`. Identity map default is `financial-engine_v2/config/ticker_identity_map.json`.

`NEWS_EODHD_API_KEY` is copied to `EODHD_API_KEY` only when the latter is empty. `NIGHTLY_NEWS_ALLOW_MISSING_EODHD_CAPTURES=1` forwards `--allow-missing-eodhd-captures`.

### Dry-run versus fetch dry-run

`NIGHTLY_NEWS_DRY_RUN=1` checks the scripts, ticker file, and identity map, counts tickers, and writes status plus health JSON with `dry_run: true`, zero totals, and phases `fetch` / `build` set to `skipped_dry_run`. It does not call the provider.

```bash
NIGHTLY_NEWS_DRY_RUN=1 financial-engine_v2/scripts/nightly_news.sh
```

`scripts/fetch_daily_news.py --dry-run` is a different contract. It prints a resolved plan JSON and exits without writes. The wrapper does not pass `--dry-run`.

### Health failures

Health exits 1 when any of these are true:

- fetch JSON has no provider `run_id`s
- a `run_id` is missing from `provider_runs`, or its `status` is not `success`
- `fetched`, `inserted`, or `chunks_written` is below its minimum
- `errors` is above `NIGHTLY_NEWS_MAX_ERRORS`
- context freshness is required and the context DB is missing, has no `context_chunks` table, or did not change versus the pre-run snapshot (`exists`, `size_bytes`, `mtime_ns`, `context_chunks_exists`, `total_chunks`, `max_published_at`)
- recent context chunks are below `NIGHTLY_NEWS_MIN_CONTEXT_RECENT_CHUNKS`

Recent chunks use `published_at >=` the earliest provider `window_start_utc`. When `context_chunks.doc_type` exists, only `news_article` rows count.

The status JSON `problems` list is the field to read after a health failure. `failed_phase` names the phase that exited non-zero.

### Cockpit news DB resolution

Checked-in profiles:

- `financial-engine_v2/config/cockpit.yaml` enables news context at `reports/qual_context/news.sqlite` with `corpus_filter: news` and `ticker_match_mode: soft`.
- `financial-engine_v2/config/cockpit.local.yaml` sets `rag.news_context.enabled: false`.

`financial-engine_v2/cockpit/core/config.py` overrides `db_path` in this order: `COCKPIT_NEWS_DB_PATH`, then `TENN_NEWS_CONTEXT_DB`, then `TENN_NEWS_ARTIFACT_ROOT/news.sqlite`. `COCKPIT_NEWS_CORPUS_FILTER` replaces the corpus filter. `COCKPIT_NEWS_TICKER_MATCH_MODE` must be `soft` or `strict`; anything else raises `ValueError`.

`resolve_news_context_db_path` then picks a file:

- `enabled: false` returns no news DB.
- The default relative path `reports/qual_context/news.sqlite` uses the newest existing file among the mounted nightly DB (`/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/news.sqlite`) and the repo-relative candidates.
- Any other explicit path, including an absolute path, is used as given. An absolute path is not replaced by a newer nightly file. If `enabled` is true and the file is missing, the resolved path is still returned for the caller to fail on.
- With no explicit path, the same newest-file search runs, then `reports/qual_context/news_eval.sqlite` under the repo or its parent.

### Wrapper checks

```bash
python3 -m unittest scripts/test_nightly_news_wrapper.py
python3 -m unittest financial-engine_v2/scripts/test_cockpit_news_context_path.py
```
