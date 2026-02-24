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
  --research-only-ack
```

Scaling note:
- For very large splits, first run with `--max-rows` (for example `10000`) to validate end-to-end.
- `--dedupe-db` persists URL/exact/near dedupe state to resume long runs safely.
- Use `--reset-output --reset-dedupe-db` only when intentionally starting from scratch.

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
