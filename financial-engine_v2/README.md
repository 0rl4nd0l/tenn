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
   - `python3 scripts/full_history_ticker_sync.py --ticker-universe-file data/raw/asx_ticker_universe.txt --max-tickers 50 --years 10`
   - Includes retry handling and automatic pending-download resume.
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

3. One-day ASX all-announcements ingest (separate from ticker backfill):
   - `python3 scripts/daily_asx_all_announcements_action.py --date 2026-02-18`
   - `python3 scripts/daily_asx_all_announcements_action.py --dry-run --date 2026-02-18`
   - Cockpit action id `daily_asx_marketwide` runs this script. It does not run `scripts/daily_asx_marketwide_action.py`.
   - `--date` is `YYYY-MM-DD` (default: today UTC). Discovery uses `ASXProvider.discover_daily_all`.
   - For today UTC, discovery tries the ASX today page first, then the announcements page, including `timeframe=D` and an empty parameter set. An earlier UTC day uses the announcements page and dated parameters only.
   - This script has no ticker fallback and no request-pacing flags. Pacing lives on the enrichment sweep below.
   - New rows are inserted, then PDFs are downloaded unless `--skip-download`. `--process-documents` runs extraction after a successful download.
   - A `marketindex_headed_required` download error increments `processing.skipped_download` and does not fail the run. Other download or extraction failures are appended to `processing.errors`.
   - Classification runs when `enable_importance_classification` is true (the config default) and at least one new document id was inserted. A classification exception is stored on the report and does not by itself change `status`.
   - Output JSON: `reports/asx/daily_asx_all_announcements_report.json`. The report is written before exit. `status` is `partial_failure` and the process exits `1` when `processing.errors` is non-empty. An empty discovery day can still exit `0`. Cockpit's quality gate for action `daily_asx_marketwide` fails that case, because it requires at least one of `discovery.found`, `insert.inserted`, or `processing.processed` to be greater than 0. The one-day report has no `discovery.provider_metrics`, so the gate's request-failure check stays at 0.
   - `--dry-run` prints a plan and does not write the report or touch the database.
   - JSON reports include `run_metadata` (script, python version, git branch/commit/dirty flag).

4. Lookback ASX market-wide ingest:
   - `python3 scripts/daily_asx_marketwide_action.py --days 1`
   - `python3 scripts/daily_asx_marketwide_action.py --dry-run --days 2 --disable-marketwide-fallback`
   - `run.py` calls this script only when `CONFIG["workflow"]` is `daily_asx_marketwide`. Workflow `both` does not include it.
   - `--days` is a lookback from now UTC and must be `> 0` (default `1`). This is a different entrypoint from the cockpit action of the same name.
   - Discovery calls `ASXProvider.discover_marketwide`. If that returns nothing and `--disable-marketwide-fallback` is unset, the script reads the first existing MarketIndex announcements JSON (`data/raw/marketindex_announcements.json`, or `settings.marketindex_announcements_file` when that file is elsewhere). It keeps symbols of length 2–5, drops rows whose date parses (day-first) to before the lookback, and keeps rows with a missing or unparseable date. The list is capped with `--fallback-max-tickers` (default `250`), then each ticker is passed to `discover`. Rows are deduped by `source_url`. Per-ticker discovery errors are skipped.
   - Download, headed-skip, extraction, and classification rules match the one-day script.
   - Output JSON: `reports/asx/daily_asx_marketwide_action_report.json`. Same `partial_failure` / exit `1` rule. `--dry-run` does not write the report.

5. Multi-day ASX enrichment sweep:
   - `python3 scripts/asx_enrichment_sweep_action.py --end-date 2026-02-18 --days-back 7 --skip-download`
   - `python3 scripts/asx_enrichment_sweep_action.py --dry-run --days-back 2`
   - Cockpit action id `asx_enrichment_sweep` runs this script.
   - Days before today UTC use per-ticker discovery when historical fallback is enabled and `--fallback-max-tickers` is `> 0`. Today UTC tries `discover_daily_all` first, then that per-ticker path if the page is empty. `--no-historical-fallback` keeps only `discover_daily_all`.
   - Ticker order is the universe file (`data/raw/asx_ticker_universe.txt` by default), then MarketIndex JSON tickers, then distinct tickers already in the database, then the ASX20 seed, capped by `--fallback-max-tickers` (default `1000`).
   - A ticker/day is skipped when every stored document for that ticker on that UTC day has a local PDF and a `pdf_sha256` that does not start with `blocked_`. `--no-skip-complete-ticker-days` probes those tickers again.
   - Pacing applies only on the per-ticker path. Defaults: `request_delay_ms=700`, `request_jitter_ms=900`, `failure_backoff_ms=2500`, `max_consecutive_failures=50`. A successful ticker sleeps `request_delay_ms` plus a random `0..request_jitter_ms`. A failure sleeps `failure_backoff_ms` times the streak first (streak capped at 6). If the streak is still under the cap, it then sleeps the normal delay and continues. At the cap it stops that day after the backoff.
   - `--download-existing-missing` also downloads discovered rows already in the database when the local PDF is missing or the hash is empty or `blocked_`. The CLI default is off. Cockpit appends the flag unless `download_existing_missing` is false.
   - `--process-documents` turns embeddings and Qdrant off for that run unless `--with-embeddings` is also set.
   - Classification uses the same `enable_importance_classification` default as the one-day script. The sweep id list also includes recovered existing rows, not only new inserts.
   - Early stop: `--max-new-docs` (default `0` means no cap), `--max-errors` (default `100`), or `--stop-after-empty-days` consecutive days with zero inserts (default `10`; `0` disables that stop). `stop_reason` is `completed_requested_window`, `max_new_docs_reached:<n>`, `max_errors_reached:<n>`, or `consecutive_empty_days:<n>`.
   - Output JSON: `reports/asx/asx_enrichment_sweep_report.json`. Any processing error sets `status` to `partial_failure` and exits `1`. Cockpit's quality gate also fails this action when `totals.days_completed` is 0 or `totals.errors` is greater than 0.
   - `--dry-run` prints the plan and does not write the report.

6. Chunked enrichment for long history:
   - `python3 scripts/run_asx_enrichment_chunked.py --dry-run --total-days-back 28 --chunk-days 14`
   - `python3 scripts/run_asx_enrichment_chunked.py --end-date 2026-02-18 --total-days-back 1825 --chunk-days 14`
   - Cockpit action id `asx_enrichment_chunked`. Each chunk is one sweep. Defaults: 1825 days, 14-day chunks, `--download-existing-missing` on, `max_consecutive_failures=20`, `max_errors=500`.
   - A failed chunk is recorded and the next chunk still runs. Rollup `status` becomes `partial_failure`, and the process exits `1` after the last chunk.
   - Per-chunk JSON: `reports/asx/asx_enrichment_chunk_<index>_<YYYYMMDD>.json`. Rollup: `reports/asx/asx_enrichment_chunked_rollup.json`, rewritten after every chunk. `--dry-run` does not run sweeps or write the rollup.

## Simplest Run (One Command)
If you want a single command with hardcoded defaults, use:

- `python3 run.py`

`CONFIG["workflow"]` selects the steps:

- `both` (default): ticker full-history gathering, then daily MarketIndex scrape/download
- `full_history` or `daily_marketindex`: only that step
- `daily_asx_marketwide`: only `scripts/daily_asx_marketwide_action.py` (the lookback script, not the cockpit one-day action)

All config is hardcoded in `run.py` under `CONFIG`.

Common edits in `run.py`:
- `CONFIG["workflow"]`: `"both"`, `"full_history"`, `"daily_marketindex"`, or `"daily_asx_marketwide"`
- `CONFIG["full_history"]["tickers"]` or `CONFIG["full_history"]["use_asx10"]`
- `CONFIG["full_history"]["years"]`
- `CONFIG["daily_marketindex"]["download_limit"]`
- `CONFIG["daily_asx_marketwide"]["days"]`, `process_documents`, and `skip_download`

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
