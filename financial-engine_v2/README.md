# Financial Engine (Local) — v2 “Operational Ingestion”
Generated: 2026-02-17 07:53:15

## Objective
Local-first ingestion + retrieval + extraction pipeline for ASX periodic documents (quarterly/half-year/annual).
Cold PDFs on disk, hot metrics in Postgres, embeddings in Qdrant, jobs via Celery/Redis, extraction/embeddings via Ollama.

Target: start with ASX20 backfill (5 years) and scale to ASX300+.

## What works now (no stubs for ingestion)
- ASX announcements discovery (parses ASX announcements HTML for PDF links)
- PDF download to filesystem + SHA256
  - Filenames use `YYYY-MM-DD_<announcement-title>_<document_id>.pdf`
  - Path is normalized at download time, so even previously inserted rows write to readable filenames on first successful download
- PDF text extraction (PyMuPDF)
- Chunking
- Real embeddings via Ollama `/api/embeddings` (configurable model; default `nomic-embed-text`)
- Qdrant upsert with real vectors
- LLM JSON extraction via Ollama `/api/generate` (configurable model; missing values remain NULL)
- Postgres tables: `documents`, `extraction_runs`, `asx_periodic_financials`, `asx_risk_notes`
- API endpoints:
  - GET `/api/health`
  - GET `/api/docs?ticker=BHP`
  - GET `/api/financials?ticker=BHP`
  - GET `/api/risk?document_id=...`
  - POST `/api/backfill/asx20`
  - POST `/api/backfill/ticker/{ticker}`

## What isn’t included (next phase)
- Frontend UI
- Factor scoring / signals / proposals
- Broker execution

## Quickstart
1. Install Docker + Docker Compose (Ubuntu)
2. Ensure Ollama is installed on the host and running
3. `cp .env.example .env`
4. `docker compose up -d --build`
5. `docker compose exec backend alembic upgrade head`
6. Pull models on host:
   - `ollama pull nomic-embed-text`
   - `ollama pull llama3.1:8b` (or any extract model you prefer)
7. Start backfill:
   - `curl -X POST http://localhost:8000/api/backfill/asx20`

## Local Isolated Mode (No Docker)
Run this mode when you want to validate functionality without touching your existing stack.

1. Create env and install deps:
   - `python3 -m venv .venv`
   - `.venv/bin/pip install -r backend/requirements.txt -r worker/requirements.txt`
   - `.venv/bin/playwright install chromium`
2. Start backend in isolated local mode:
   - `./scripts/run_local_backend.sh`
3. Smoke test:
   - `curl http://localhost:8000/api/health`
   - `curl "http://localhost:8000/api/docs?ticker=BHP"`
   - `curl -X POST "http://localhost:8000/api/backfill/ticker/BHP?years=1&process_documents=false"`
   - or run `./scripts/smoke_local.sh`

Defaults in local mode:
- SQLite database at `./data/fe_local.db`
- Sync task mode (`TASK_MODE=sync`)
- Auto-create tables enabled
- Embeddings/Qdrant/LLM extraction disabled by default
- MarketIndex fallback enabled by default (`ENABLE_MARKETINDEX_FALLBACK=true`) using `../data/raw/marketindex_announcements.json`
- If MarketIndex URLs return Cloudflare `403`, those docs are marked `blocked_marketindex_403` and skipped
- MarketIndex documents are treated as headed-only and marked `blocked_marketindex_headed_required` in local non-headed mode

## Headed MarketIndex Recovery (Manual)
Use this manual command after backfill to recover blocked/pending MarketIndex docs with a headed browser session.

- `python3 scripts/recover_marketindex_headed.py`
- `python3 scripts/recover_marketindex_headed.py --ticker BHP`
- `python3 scripts/recover_marketindex_headed.py --ticker BHP,RIO --limit 20`
- `python3 scripts/recover_marketindex_headed.py --dry-run`

Key behavior:
- Headless mode is blocked (`--headless` exits with code `2`)
- Defaults target all blocked/pending MarketIndex docs across tickers
- Report path default: `reports/marketindex_headed_recovery_report.json`
- Fails with code `3` when `--min-recovered-count` is not met

Recommended sequence:
1. Run sync backfill (`/api/backfill/ticker/{ticker}` or `/api/backfill/asx20`)
2. Run headed MarketIndex recovery CLI
3. Run PDF integrity audit before enabling extraction/embeddings

## Production CLIs
These are the two production workflows currently packaged.

1. Ticker-based full announcement history gathering:
   - `python3 scripts/full_history_ticker_sync.py --ticker BHP --years 10`
   - `python3 scripts/full_history_ticker_sync.py --ticker BHP,RIO,CSL --years 10`
   - `python3 scripts/full_history_ticker_sync.py --asx10 --years 10`
   - Includes retry handling and automatic pending-download resume.
   - Saved PDF names are structured: `YYYY-MM-DD_<announcement-title>_<document_id>.pdf`

2. Daily MarketIndex announcement scraping + PDF download:
   - `python3 scripts/daily_marketindex_action.py`
   - `python3 scripts/daily_marketindex_action.py --download-limit 200`
   - Uses headed browser mode for download step (headless download is blocked).
   - Output JSON: `data/raw/marketindex_announcements.json`
   - Output PDFs: `data/marketindex/pdfs`
   - Daily PDF names are structured:
     `DD-MM-YY_<time>_<ticker>_<heading-slug>_<announcement-id>.pdf`

## Simplest Run (One Command)
If you want a single command with hardcoded defaults, use:

- `python3 run.py`

This wrapper runs:
- ticker full-history gathering
- daily MarketIndex scrape/download

All config is hardcoded in `run.py` under `CONFIG`.

Common edits in `run.py`:
- `CONFIG["workflow"]`: `"both"`, `"full_history"`, or `"daily_marketindex"`
- `CONFIG["full_history"]["tickers"]` or `CONFIG["full_history"]["use_asx10"]`
- `CONFIG["full_history"]["years"]`
- `CONFIG["daily_marketindex"]["download_limit"]`

## Key environment variables
- `OLLAMA_URL` (default `http://host.docker.internal:11434`)
- `EMBED_MODEL` (default `nomic-embed-text`)
- `EXTRACT_MODEL` (default `llama3.1:8b`)
- `DOCS_ROOT` (default `/data/asx/docs`)

## Notes
- This discovery method is heuristic; ASX page structure may change. It’s modular (`backend/app/providers/asx_provider.py`).
- Missing metrics are stored as NULL by design.
