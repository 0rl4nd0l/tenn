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
   - Includes automatic post-ingestion announcement-type classification into folders under `data/asx/importance/{ticker}/{announcement_type}`.
   - Source docs are also sorted under `data/asx/docs/{ticker}/{announcement_type}` (configurable).
   - Saved PDF names are structured: `YYYY-MM-DD_<announcement-title>_<document_id>.pdf`

2. Daily MarketIndex announcement scraping + PDF download:
   - `python3 scripts/daily_marketindex_action.py`
   - `python3 scripts/daily_marketindex_action.py --download-limit 200`
   - Uses headed browser mode for download step (headless download is blocked).
   - Output JSON: `data/raw/marketindex_announcements.json`
   - Output PDFs: `data/marketindex/pdfs`
   - Daily PDF names are structured:
     `DD-MM-YY_<time>_<ticker>_<heading-slug>_<announcement-id>.pdf`

3. Daily ASX all-announcements ingest (separate from ticker backfill):
   - `python3 scripts/daily_asx_all_announcements_action.py --date 2026-02-18`
   - Ingests all announcements detected on ASX for the target day, inserts new docs, downloads PDFs, and classifies.
   - Output JSON: `reports/asx/daily_asx_all_announcements_report.json`

## Simplest Run (One Command)
If you want a single command with hardcoded defaults, use:

- `python3 run.py`

This wrapper runs:
- ticker full-history gathering
- daily MarketIndex scrape/download

All config is hardcoded in `run.py` under `CONFIG`.

Common edits in `run.py`:
- `CONFIG["workflow"]`: `"both"`, `"full_history"`, or `"daily_marketindex"`

## Announcement Type Classification (Manual Backfill)
Rebuild announcement-type folders for existing ingested docs:

- `python3 scripts/classify_announcement_importance.py --ticker BHP`
- `python3 scripts/classify_announcement_importance.py --ticker BHP,RIO --limit 500`

## Financial Rebuild + QA
Rebuild financial rows from already-downloaded docs (no re-download):

- `python3 scripts/rebuild_ticker_financials_from_docs.py --ticker BHP`
- `python3 scripts/rebuild_ticker_financials_from_docs.py --ticker BHP --since 2024-01-01 --limit 100`

Audit ticker financial quality (confidence, source-linkage, period gaps):

- `python3 scripts/audit_ticker_financials.py --ticker BHP`
- `CONFIG["full_history"]["tickers"]` or `CONFIG["full_history"]["use_asx10"]`
- `CONFIG["full_history"]["years"]`
- `CONFIG["daily_marketindex"]["download_limit"]`

## Cockpit TUI (v1)
Operate chat + ingestion + updater + verification from a single terminal UI.

Run:
- `python -m cockpit.main`
- or `./scripts/cockpit_tui.py`

CLI flags:
- `--config config/cockpit.yaml`
- `--profile default`
- `--read-only`
- `--no-web`

Key bindings:
- `c` chat
- `o` ingestion operations
- `u` updater + snapshot
- `v` verification
- `h` history
- `s` settings
- `q` quit

## Key environment variables
- `OLLAMA_URL` (default `http://host.docker.internal:11434`)
- `EMBED_MODEL` (default `nomic-embed-text`)
- `EXTRACT_MODEL` (default `llama3.1:8b`)
- `DOCS_ROOT` (default `/data/asx/docs`)

## Current model prompting + iteration setup
- Prompting is schema-first and centralized in `backend/app/services/extraction.py` (`build_prompt`).
  - Full PDF text is clipped to the first 18,000 characters before model input.
  - The prompt asks for strict JSON containing period fields, metrics, risk/guidance summaries, and confidence values.
- Extraction is a single-pass `/api/generate` call to Ollama (`backend/app/services/ollama.py`).
  - No temperature/top-p/etc overrides are currently passed; runtime uses Ollama model defaults.
  - The response parser extracts the first JSON object with regex and loads it.
- Versioning is lightweight but explicit:
  - `EXTRACTOR_VERSION="ollama_json_v1"`
  - `prompt_hash="v1"` stored on `extraction_runs`
- Iterations/retries today are operational retries around discovery/download, not multi-pass prompt refinement:
  - `scripts/full_history_ticker_sync.py` retries backfill connect errors and runs a resume phase.
  - `scripts/resume_pending_downloads.py` retries retryable network failures with linear backoff.
  - `scripts/marketindex_download_pdfs.py` includes a secondary pass for unresolved announcement links.
- Local isolated mode defaults extraction/embeddings OFF (`ENABLE_EXTRACTION=false`, `ENABLE_EMBEDDINGS=false`) for safe smoke testing; production workflows can enable processing via flags/env.


## Model improvement roadmap
If you want a practical setup for running now on limited hardware and scaling cleanly once an NVIDIA M40 is installed (including iterative evaluation, model selection, fine-tuning path, and a human-approved "commit to knowledge base" workflow for PDFs/books), see:

- `docs_model_iteration_playbook.md`

## Notes
- This discovery method is heuristic; ASX page structure may change. It’s modular (`backend/app/providers/asx_provider.py`).
- Missing metrics are stored as NULL by design.
