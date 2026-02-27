# Contextualization Workflow (RAG)

Use `scripts/build_qualitative_context_db.py` to build vector context stores.

## 1) Company filings corpus (targeted sections, ASX-native)

This is for per-company reasoning from MD&A, risk, chairman commentary, and cashflow commentary.

```bash
python3 scripts/build_qualitative_context_db.py \
  --pdf-dir financial-engine_v2/data/asx/docs \
  --db sqlite \
  --out reports/qual_context/company.sqlite \
  --embed-backend hash \
  --content-scope targeted \
  --fallback-fulltext \
  --corpus company
```

MarketIndex fallback only (if ASX source is unavailable):

```bash
python3 scripts/build_qualitative_context_db.py \
  --pdf-dir financial-engine_v2/data/marketindex/pdfs \
  --db sqlite \
  --out reports/qual_context/company.sqlite \
  --embed-backend hash \
  --content-scope targeted \
  --fallback-fulltext \
  --corpus company
```

## 2) Reference knowledge corpus (full text)

This is for strategy/valuation/background context from study docs and research papers.

```bash
python3 scripts/build_qualitative_context_db.py \
  --pdf-dir reports/usb_pdfs \
  --db sqlite \
  --out reports/qual_context/reference.sqlite \
  --embed-backend hash \
  --content-scope fulltext \
  --corpus reference
```

## 3) Query company corpus only

```bash
python3 scripts/build_qualitative_context_db.py \
  --pdf-dir financial-engine_v2/data/asx/docs \
  --db sqlite \
  --out reports/qual_context/company.sqlite \
  --embed-backend hash \
  --content-scope targeted \
  --corpus company \
  --query "cash flow outlook and key risks" \
  --company SEG \
  --corpus-filter company
```

## 4) Query reference corpus only

```bash
python3 scripts/build_qualitative_context_db.py \
  --pdf-dir reports/usb_pdfs \
  --db sqlite \
  --out reports/qual_context/reference.sqlite \
  --embed-backend hash \
  --content-scope fulltext \
  --corpus reference \
  --query "valuation cash flow risk" \
  --corpus-filter reference
```

## 5) Query by doc type and date window

```bash
python3 scripts/build_qualitative_context_db.py \
  --pdf-dir financial-engine_v2/data/asx/docs \
  --db sqlite \
  --out reports/qual_context/company.sqlite \
  --embed-backend hash \
  --content-scope targeted \
  --corpus company \
  --query "guidance downgrade cash flow risk" \
  --corpus-filter company \
  --doc-type-filter announcement \
  --date-from 2026-01-01 \
  --date-to 2026-12-31
```

## 6) News corpus (isolated experimental module)

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

## 7) Query news by ticker/source/date

```bash
python3 scripts/build_news_context_db.py \
  --input-path reports/news_eval_input/news_sample.jsonl \
  --db sqlite \
  --out reports/qual_context/news.sqlite \
  --embed-backend sentence-transformers \
  --embed-model BAAI/bge-large-en-v1.5 \
  --st-device cpu \
  --research-only-ack \
  --query "delivery outlook and margin pressure" \
  --corpus-filter news \
  --doc-type-filter news_article \
  --ticker-filter TSLA \
  --source-filter "Yahoo Finance" \
  --date-from 2026-01-01 \
  --date-to 2026-12-31
```

## Notes
- `--corpus` tags stored rows so different corpora can coexist safely.
- `--corpus-filter` constrains retrieval to one corpus.
- `--exclude-corpus-filter` can be used to exclude one corpus label at query-time.
- `--doc-type-filter` constrains retrieval to `announcement|annual_report|presentation|textbook|research|news_article|other`.
- `--ticker-filter` and `--source-filter` constrain retrieval on normalized metadata.
- `--date-from` and `--date-to` apply inclusive `YYYY-MM-DD` filtering when `doc_date` metadata is available.
- `--content-scope fulltext` is the right mode for contextual/reference PDFs.
- `--content-scope targeted` remains best for filing-specific qualitative extraction.

## Canonical checks

Use the consolidated checker to refresh all canonical retrieval reports:

```bash
scripts/run_canonical_dataset_checks.sh
```

Canonical output reports:
- `reports/news_eval_report.json` (fixture/news eval via `hash`)
- `reports/company_eval_report_v2.json` (company eval via `sentence-transformers`)
- `reports/eval_queries_report.json` (reference eval via `hash`)

Canonical DB map:
- `reports/qual_context/company.sqlite` -> `reports/qual_context/company_bge_v2.sqlite`
- `reports/qual_context/news_eval.sqlite` -> `reports/qual_context/news_eval_hash.sqlite`
- `reports/qual_context/reference.sqlite` -> `reports/usb_qual_context/reference_fulltext.sqlite`
