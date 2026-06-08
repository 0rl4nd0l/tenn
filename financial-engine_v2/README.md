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
  - GET `/api/price?ticker=BHP&range=1mo&interval=1d&exchange=ASX`
    - Returns `400` for invalid query params and `502` for upstream provider failures.
  - POST `/api/backfill/asx20`
  - POST `/api/backfill/ticker/{ticker}`

## What isn’t included (next phase)
- Frontend UI
- Factor scoring / signals / proposals
- Broker execution

## Canonical Execution (Agents)

Canonical entrypoint documentation: `../docs/entrypoints.md`.

Canonical (isolated backend mode, no Docker):
- `bash scripts/run_local_backend.sh`
- Validate: `bash scripts/smoke_local.sh`

Docker is supported for full infrastructure, but it is not the default path for agents.

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
- MarketIndex marker states you may see in `documents.pdf_sha256`:
  - `blocked_marketindex_403` (Cloudflare `403`)
  - `blocked_marketindex_headed_required` (non-headed mode cannot fetch)
  - `blocked_marketindex_no_candidate` (no candidate PDF link found during headed recovery)
  - `blocked_marketindex_headed_error` (headed recovery fetch/runtime failure)
- Successful headed recovery rewrites marker values to a real file SHA256 hash.

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
These are the operational ingestion workflows currently packaged.

1. Ticker-based full announcement history gathering:
   - `python3 scripts/full_history_ticker_sync.py --ticker BHP --years 10`
   - `python3 scripts/full_history_ticker_sync.py --ticker BHP,RIO,CSL --years 10`
   - `python3 scripts/full_history_ticker_sync.py --asx10 --years 10`
   - `python3 scripts/full_history_ticker_sync.py --ticker-universe-file data/raw/asx_ticker_universe.txt --max-tickers 50 --years 10`
   - `python3 scripts/full_history_ticker_sync.py --ticker BHP --years 10 --health-json ../reports/research_engine_health.json --allow-warning`
   - Includes retry handling and automatic pending-download resume.
   - Runs a preflight health gate using `--health-json` (default `../reports/research_engine_health.json`).
     - `overall_status=degraded` blocks execution.
     - `overall_status=warning` blocks unless `--allow-warning` is set.
     - Missing snapshot only warns and allows execution.
   - Includes optional ticker pacing controls (`--ticker-delay-seconds`, `--ticker-delay-jitter-seconds`) and per-ticker progress logs.
   - Includes automatic post-ingestion announcement-type classification into folders under `data/asx/importance/{ticker}/{announcement_type}`.
   - Source docs are also sorted under `data/asx/docs/{ticker}/{announcement_type}` (configurable).
   - Saved PDF names are structured: `YYYY-MM-DD_<announcement-title>_<document_id>.pdf`
   - JSON reports include `run_metadata` (script, python version, git branch/commit/dirty flag) for provenance.

2. Daily MarketIndex announcement scraping + PDF download:
   - `python3 scripts/daily_marketindex_action.py`
   - `python3 scripts/daily_marketindex_action.py --download-limit 200`
   - Uses headed browser mode for download step (headless download is blocked).
   - Output JSON: `data/raw/marketindex_announcements.json`
   - Output PDFs: `data/marketindex/pdfs`
   - JSON reports include `run_metadata` (script, python version, git branch/commit/dirty flag).
   - Daily PDF names are structured:
     `DD-MM-YY_<time>_<ticker>_<heading-slug>_<announcement-id>.pdf`

3. Daily ASX all-announcements ingest (separate from ticker backfill):
   - `python3 scripts/daily_asx_all_announcements_action.py --date 2026-02-18`
   - `python3 scripts/daily_asx_all_announcements_action.py --date 2026-02-18 --process-documents`
   - Ingests all announcements detected on ASX for the target day, inserts new docs, downloads PDFs, and classifies.
   - Best for a single explicit day (`--date`). For lookback windows and fallback ticker sweep behavior, use `daily_asx_marketwide_action.py`.
   - For multi-day pacing/throttle controls, use `asx_enrichment_sweep_action.py` (`--request-delay-ms`, `--request-jitter-ms`, `--failure-backoff-ms`).
   - Output JSON: `reports/asx/daily_asx_all_announcements_report.json`
   - JSON reports include `run_metadata` (script, python version, git branch/commit/dirty flag).

4. Daily ASX market-wide lookback (rolling window + optional fallback):
   - `python3 scripts/daily_asx_marketwide_action.py --days 1`
   - `python3 scripts/daily_asx_marketwide_action.py --days 3 --fallback-max-tickers 500`
   - `python3 scripts/daily_asx_marketwide_action.py --days 1 --disable-marketwide-fallback`
   - Uses market-wide discovery first, then optional fallback ticker sweep when market-wide results are empty.
   - Output JSON: `reports/asx/daily_asx_marketwide_action_report.json`

5. Bulk ASX enrichment + long-horizon runs:
   - Sweep window (ingest/download/classify with guardrails):
     - `python3 scripts/asx_enrichment_sweep_action.py --end-date 2026-02-18 --days-back 30`
     - `python3 scripts/asx_enrichment_sweep_action.py --days-back 365 --max-new-docs 5000 --download-existing-missing`
   - Chunked long-horizon runner (calls sweep script in chunks and writes rollup):
     - `python3 scripts/run_asx_enrichment_chunked.py --total-days-back 1825 --chunk-days 14`
   - Probe known system tickers (from DB) for broad backfill coverage:
     - `python3 scripts/probe_all_system_tickers.py --years 5`
   - Constraint: in `asx_enrichment_sweep_action.py`, `--process-documents` disables embeddings by default unless `--with-embeddings` is explicitly set.

## Simplest Run (One Command)
If you want a single command with hardcoded defaults, use:

- `python3 run.py`

This wrapper runs:
- default: ticker full-history gathering + daily MarketIndex scrape/download (`workflow="both"`)
- optional: ASX market-wide workflow only (`workflow="daily_asx_marketwide"`)

All config is hardcoded in `run.py` under `CONFIG`.

Common edits in `run.py`:
- `CONFIG["workflow"]`: `"both"`, `"full_history"`, `"daily_marketindex"`, or `"daily_asx_marketwide"`
- `CONFIG["daily_asx_marketwide"]["days"]` / `["process_documents"]` / `["skip_download"]`

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
- or `./scripts/cockpit_tui.py` (recommended wrapper with auto-bootstrap)

Wrapper bootstrap behavior (`./scripts/cockpit_tui.py`):
- Ensures `.env` exists (creates from `.env.example` when missing).
- Ensures `HOST_UID` and `HOST_GID` defaults exist in `.env`.
- Runs `docker compose up -d` for default services:
  - `postgres,redis,qdrant,worker,backend`
- Runs `docker compose exec -T backend alembic upgrade head`.

CLI flags:
- `--config config/cockpit.yaml`
- `--profile default`
- `--read-only`
- `--no-web`

Wrapper-only flags:
- `--no-boot` (skip bootstrap and launch cockpit immediately)
- `--no-build` (skip compose build during bootstrap)
- `--no-migrate` (skip Alembic migration during bootstrap)
- `--services postgres,redis,qdrant,worker,backend` (override boot services)
- `--env-file .env`

Key bindings:
- `c` chat
- `o` ingestion operations
- `u` updater + snapshot
- `v` verification
- `h` history
- `s` settings
- `q` quit

Operational controls:
- Single active action at a time (new runs are blocked while one job is running).
- "Kill Running Action" is available in both Chat and Operations screens for long-running jobs.
- Cockpit action id `daily_asx_marketwide` currently runs `scripts/daily_asx_all_announcements_action.py` with `--date` semantics (single-day ingest).

## Key environment variables
- `OLLAMA_URL` (default `http://host.docker.internal:11434`)
- `EMBED_MODEL` (default `nomic-embed-text`)
- `EXTRACT_MODEL` (`.env.example` sets `llama3.1:8b`; config/local launcher fallback is `llama3:latest`)
- `DOCS_ROOT` (default `/data/asx/docs`)
- `ENABLE_IMPORTANCE_CLASSIFICATION` (default `true`; enable/disable post-ingestion announcement classification)
- `IMPORTANCE_OUTPUT_ROOT` (default `data/asx/importance`)
- `IMPORTANCE_MATERIALIZE_OUTPUT` (default `false`; write JSON artifacts for classified docs)
- `IMPORTANCE_INCLUDE_PDF_TEXT` (default `true`; include extracted text in classification artifact payloads)
- `IMPORTANCE_LINK_MODE` (default `symlink`; falls back to copy when symlink is unavailable)
- `IMPORTANCE_SORT_SOURCE_DOCS` (default `true`; sort source PDFs into `{ticker}/{announcement_type}` folders)

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


## Resource folder workflow (custom-GPT style)
You can now run a folder-driven workflow where you drop PDFs/TXT/MD files and curate what becomes analysis context.

Script: `scripts/resource_library_workflow.py`

1. Initialize folders:
   - `python3 scripts/resource_library_workflow.py init`
2. Add files to `data/resource_library/inbox/`
3. Ingest into review candidates:
   - `python3 scripts/resource_library_workflow.py ingest` (heuristic mode by default)
   - `python3 scripts/resource_library_workflow.py ingest --use-llm` (Ollama opt-in)
4. Review and approve/reject/edit takeaways:
   - `python3 scripts/resource_library_workflow.py review`
5. Build analysis context pack from approved resources:
   - `python3 scripts/resource_library_workflow.py build-context --query "BHP earnings outlook and debt risk"`

Approved resources become a reusable local knowledge layer that can be injected into report prompts.
Dependencies for this workflow:
- `pymupdf` for PDF text extraction
- `httpx` + reachable Ollama endpoint when using `--use-llm`

## Model improvement roadmap
If you want a practical setup for running now on limited hardware and scaling cleanly once an NVIDIA M40 is installed (including iterative evaluation, model selection, fine-tuning path, and a human-approved "commit to knowledge base" workflow for PDFs/books), see:

- `docs_model_iteration_playbook.md` (includes a dedicated section on training combined financial + news analysis reports with citation gates)

## Analysis report schema + citation gate validator
Phase-E scaffolding now includes a strict JSON-first report contract and a citation/evidence gate validator.

Validate a report:
- `python3 scripts/validate_analysis_report.py --report scripts/fixtures/analysis_report_schema/report_valid.json --evidence scripts/fixtures/analysis_report_schema/evidence_bundle_valid.json`

Run tests:
- `python3 scripts/test_analysis_report_schema.py`

## Agent context auto-refresh
To keep Codex context current as the system evolves:

- Refresh digest + update `~/.codex/config.toml` block:
  - `make context-refresh`
- Check whether current workspace changes are significant:
  - `make context-check`
- Install a pre-push notifier hook:
  - `make hooks-install`

The context refresher writes:
- markdown digest: `reports/agent_context_digest.md`
- JSON snapshot: `reports/agent_context_snapshot.json`
- config block markers in `~/.codex/config.toml`:
  - `# BEGIN TENN_AGENT_CONTEXT`
  - `# END TENN_AGENT_CONTEXT`

## Notes
- This discovery method is heuristic; ASX page structure may change. It’s modular (`backend/app/providers/asx_provider.py`).
- Missing metrics are stored as NULL by design.
