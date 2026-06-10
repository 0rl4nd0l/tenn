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
- Daily provider ingest stores canonical articles in `news_articles.sqlite`, then builds RAG chunks into `news.sqlite`.
- Deterministic news benchmark/eval fixture DB lives at: `reports/qual_context/news_eval.sqlite`.
- Query-time filters support selecting or excluding corpora (`--corpus-filter`, `--exclude-corpus-filter`).
- Cockpit news retrieval defaults now pin to:
  - `rag.news_context.db_path=reports/qual_context/news.sqlite`
  - `rag.news_context.corpus_filter=news`
  - `rag.news_context.ticker_match_mode=soft`

## Pipeline modes

Use the daily provider pipeline for operational refreshes, and the bulk builder
for research/evaluation datasets.

| Mode | Entrypoint | Writes | Use when |
| --- | --- | --- | --- |
| Daily operational ingest | `financial-engine_v2/scripts/nightly_news.sh` | `news_articles.sqlite`, `news.sqlite`, per-run reports, health JSON | Refreshing the ASX news context store from configured providers. |
| Bulk research build | `scripts/build_news_context_db.py` | `news.sqlite`, manifest JSON | Indexing gated HF/GDELT/local JSONL research datasets with explicit `--research-only-ack`. |

## Nightly operational pipeline

The cron wrapper `financial-engine_v2/scripts/nightly_news.sh` is the durable
operator entrypoint for daily news refreshes.

Cron target documented in the script:

```cron
0 2 * * * /home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh
```

Pipeline stages:

1. Validate prerequisites: ticker universe, ticker identity map, and required scripts.
2. Fetch articles with `scripts/fetch_daily_news.py`.
3. Build RAG-compatible chunks with `scripts/build_news_chunks.py`.
4. Write health JSON and fail the run if thresholds or freshness checks fail.

Default provider behavior:

- `NIGHTLY_NEWS_PROVIDERS` falls back to `NEWS_PROVIDERS`, then `newspaper4k`.
- `newspaper4k` uses the `daily` source profile by default.
- Playwright fetching is disabled by default for nightly `newspaper4k`
  (`NIGHTLY_NEWS_NEWSPAPER4K_NO_PLAYWRIGHT=1`).
- Chunk embeddings default to hash embeddings for the wrapper
  (`NIGHTLY_NEWS_EMBED_BACKEND`, then `NEWS_EMBED_BACKEND`, then `hash`).

Safe validation:

```bash
NIGHTLY_NEWS_DRY_RUN=1 bash financial-engine_v2/scripts/nightly_news.sh
```

Dry run validates config and writes success status/health files, but skips fetch
and chunk build and does not create `news_articles.sqlite`.

### Artifact and database paths

The wrapper resolves the news artifact root in this order:

1. `TENN_NEWS_ARTIFACT_ROOT`
2. `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context` when that directory exists
3. `{repo}/reports/qual_context`

Key outputs:

| Output | Default path |
| --- | --- |
| Operational logs/status | `reports/ops_checks/nightly/` |
| Run log | `nightly_news_<timestamp>.log` |
| Status JSON | `nightly_news_<timestamp>.status.json` |
| Fetch JSON | `nightly_news_<timestamp>.fetch.json` |
| Chunk build JSON | `nightly_news_<timestamp>.chunks.json` |
| Health JSON | `nightly_news_<timestamp>.health.json` |
| Canonical articles DB | `{artifact_root}/news_articles.sqlite` |
| RAG context DB | `{artifact_root}/news.sqlite` |
| Provider run reports | `{artifact_root}/news_runs/` |

Override paths with:

| Env var | Purpose |
| --- | --- |
| `NIGHTLY_NEWS_LOG_DIR` | Directory for wrapper logs and JSON status artifacts. |
| `TENN_NEWS_ARTIFACT_ROOT` | Shared root for news DB artifacts and provider run reports. |
| `TENN_NEWS_ARTICLES_DB` | Exact canonical article SQLite path. |
| `TENN_NEWS_CONTEXT_DB` | Exact RAG context SQLite path consumed by Cockpit. |
| `TENN_NEWS_RUNS_ROOT` | Exact provider run report root. |

The wrapper keeps the newest 30 artifacts per file type in the log directory.

### Health gates and troubleshooting

Health JSON is written after fetch and build. A non-empty `problems` array makes
the wrapper exit non-zero during the `health` phase.

| Env var | Default | Failure it catches |
| --- | --- | --- |
| `NIGHTLY_NEWS_MIN_FETCHED` | `1` | Providers returned no articles. |
| `NIGHTLY_NEWS_MIN_UPSERTED` | `1` | All fetched articles were duplicates/rejected. |
| `NIGHTLY_NEWS_MIN_CHUNKS` | `1` | Chunk builder wrote no context chunks. |
| `NIGHTLY_NEWS_MIN_CONTEXT_RECENT_CHUNKS` | `NIGHTLY_NEWS_MIN_CHUNKS` | Context DB lacks enough recent news chunks for the fetch window. |
| `NIGHTLY_NEWS_MAX_ERRORS` | `0` | Provider run reported errors. |
| `NIGHTLY_NEWS_REQUIRE_CONTEXT_FRESH` | `1` | Context DB did not change during the current run. |

Common failure checks:

- `context SQLite fallback missing`: confirm `TENN_NEWS_CONTEXT_DB` or
  `TENN_NEWS_ARTIFACT_ROOT` points to the same location Cockpit reads.
- `context SQLite fallback did not change during current run`: inspect the
  matching `*.chunks.json`; duplicate-only fetches can build no new context.
- `inserted/upserted 0 below minimum 1`: provider output was seen, but every
  article was deduped or rejected. Check the fetch JSON and provider run report.
- Missing ticker inputs: verify `NEWS_TICKERS_FILE` and
  `NEWS_IDENTITY_MAP_PATH`.

Relevant tests:

- `scripts/test_nightly_news_wrapper.py`
- `financial-engine_v2/scripts/test_cockpit_news_context_path.py`

### Cockpit news context DB resolution

Cockpit reads the same `news.sqlite` context store. Environment precedence in
`cockpit.core.config.apply_runtime_flags` is:

1. `COCKPIT_NEWS_DB_PATH`
2. `TENN_NEWS_CONTEXT_DB`
3. `TENN_NEWS_ARTIFACT_ROOT/news.sqlite`
4. `config/cockpit.yaml` (`reports/qual_context/news.sqlite`)

When the configured path is the default relative
`reports/qual_context/news.sqlite`, startup resolves the newest existing file
among the nightly NVMe artifact path and repo-relative candidates. Explicit
absolute paths are not overridden. This prevents a stale ignored repo-local DB
from masking fresher nightly output.

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
