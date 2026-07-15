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

## Find out-of-universe backfill candidates from news signals

`scripts/backfill_missing_universe_announcements.py` compares explicit ASX ticker
references in the normalized article store with the checked-in ticker universe.
Use it to find news-referenced tickers absent from the configured universe. This
does not inspect existing announcement records, so an out-of-universe candidate
is not proof that its announcements are missing.

The workflow reads:

- `reports/qual_context/news_articles.sqlite`: normalized source articles in the
  `articles` table. This is not the chunked retrieval DB (`news.sqlite`).
- `financial-engine_v2/data/raw/asx_ticker_universe.txt`: the current comparison
  universe.

It recognizes explicit signals such as `ASX:BHP`, `ASX-BHP`, `BHP.AX`,
`XASX:BHP`, MarketIndex `/asx/bhp/announcements` URLs, and
`mapped_tickers=BHP,RIO` metadata. Candidate extraction, especially free-form
`mapped_tickers` body metadata, can produce false positives. Review the evidence
before executing a backfill. The workflow does not add candidates to the ticker
universe file.

The normalized store is produced by `scripts/fetch_daily_news.py` and the
`financial-engine_v2/scripts/nightly_news.sh` wrapper. The nightly wrapper can
place artifacts under `TENN_NEWS_ARTIFACT_ROOT` or a mounted artifact root
instead of the repository default. In that case, pass its reported
`news_articles_db` path with `--news-articles-db`.

### Plan and review

Run from the repository root without `--execute` first:

```bash
python3 scripts/backfill_missing_universe_announcements.py \
  --source-lookback-days 30 \
  --min-article-count 2 \
  --max-missing-tickers 25
```

The default scans every provider in the store. Add a comma-separated
`--providers worldmonitor,gdelt` filter only when those providers are present.
`--source-lookback-days 0` scans all articles, and
`--max-missing-tickers 0` selects every candidate. The plan is printed as JSON
to stdout and written to:

| Artifact | Default path | Contents |
| --- | --- | --- |
| Plan/result JSON | `reports/asx/missing_universe_announcement_backfill_plan.json` | Filters, candidate evidence, selected tickers, and execution state |
| Ticker list | `reports/asx/missing_universe_tickers.txt` | Selected out-of-universe tickers, one per line |
| Child report | `financial-engine_v2/reports/asx/missing_universe_full_history_report.json` | Created or refreshed only when the child backfill runs |

Review `missing_universe_candidates` in the JSON. Each candidate includes its
article count, providers, matched signal types, date range, and sample titles.
Use `--news-articles-db`, `--tickers-file`, `--out-json`, and
`--out-missing-tickers` to override the inputs or plan outputs.

### Execute the backfill

`--execute` performs a fresh scan; it does not replay an immutable saved plan.
It immediately runs the newly selected set without pausing for confirmation.
Keep the article DB and ticker universe unchanged and repeat the same filters;
afterward, compare `selected_missing_tickers` with the reviewed list for audit.
This workflow cannot guarantee execute-from-plan semantics.

```bash
python3 scripts/backfill_missing_universe_announcements.py \
  --source-lookback-days 30 \
  --min-article-count 2 \
  --max-missing-tickers 25 \
  --announcement-years 1 \
  --execute
```

Execution invokes
`financial-engine_v2/scripts/full_history_ticker_sync.py` once with the selected
tickers. By default it discovers and downloads announcements, then retries
pending downloads. Add `--process-documents` only when extraction/embedding
processing is also required. The child uses `financial-engine_v2/.venv/bin/python`
when available; otherwise it uses the current interpreter. Override this with
`--python-bin`.

Before the child starts, the wrapper checks:

- Health snapshot: `reports/research_engine_health.json` by default. Missing
  snapshots warn but do not block. Malformed JSON, JSON objects with an invalid
  status, and `degraded` snapshots block. `warning` blocks unless
  `--allow-warning` is explicitly supplied. A valid non-object JSON value is a
  setup error that can exit before the result is rewritten.
- DNS: at least one configured ASX host must resolve. Fix network/DNS failures
  rather than using `--skip-dns-preflight` routinely.

Use `--full-history-health-json` to select another health snapshot and
`--dns-hosts` to replace the comma-separated host list. A preflight block exits
with code `2`; a failed child exits with code `1`. In both cases, inspect
`execution.preflight`, `stderr_tail`, and `stdout_tail` in the plan/result JSON.
Preflight runs only when `--execute` selects at least one ticker; plan mode
leaves `execution.command` empty and health preflight `{}`. It does not validate
the child interpreter or script path before the health and DNS checks.

For automation, interpret the normal JSON result with the process exit code:

| Exit | Result fields | Meaning |
| --- | --- | --- |
| `0` | `execution.requested=false` | Plan generated; `execution.success` remains `false` because no execution was requested |
| `0` | `requested=true`, `ran=false`, `success=true`, no selected tickers | Successful no-op; the fresh scan found nothing to backfill |
| `0` | `requested=true`, `ran=true`, `success=true` | Child backfill completed successfully |
| `1` | `ran=true`, `success=false` | Child backfill failed; inspect the output tails |
| `2` | `ran=false`, `success=false`, non-empty `preflight.blocked_reasons` | Health or DNS preflight blocked execution |

Input/setup exceptions can exit before the result JSON is rewritten. Treat a
non-zero process exit plus a missing or stale `generated_at_utc` as a wrapper
setup failure, not as a current execution result.

Common problems:

- `no such table: articles`: `--news-articles-db` points at the chunked
  `news.sqlite` or another incompatible DB; use the normalized article store.
- No selected tickers: check `stats.articles_scanned`, loosen provider/lookback
  filters, or lower `--min-article-count`. Articles without an explicit ticker
  signal are intentionally ignored.
- Health warning/degraded: inspect or regenerate the health snapshot before
  retrying. Use `--allow-warning` only when the warning is understood.
- Child report not embedded in the result: an unchanged pre-existing report is
  deliberately ignored; inspect the child return code and output tails.

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
