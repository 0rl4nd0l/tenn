# Financial Engine (Local) — v2 “Operational Ingestion”
Generated: 2026-03-18 18:35:00

## Objective
Local-first ingestion + retrieval + extraction pipeline for ASX periodic documents (quarterly/half-year/annual).
Cold PDFs on disk, hot metrics in Postgres, embeddings in Qdrant, jobs via Celery/Redis, extraction/embeddings via Ollama.

Target: start with ASX20 backfill (5 years) and scale to ASX300+.

Canonical setup docs now live in:
- `../docs/setup/environment.md`
- `../docs/setup/runtime.md`
- `../docs/setup/troubleshooting.md`

If this README conflicts with those setup docs, the `docs/setup/*` files are the source of truth.

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
  - POST `/api/rag/query`
  - Compatibility route: POST `/rag/query`
  - GET `/api/price`
  - GET `/api/fundamentals/profile`
  - GET `/api/fundamentals/summary`
  - GET `/api/fundamentals/statements`
  - POST `/api/chat`
  - Compatibility route: POST `/chat`

## Current Verified Local State (2026-03-18)
- `LOCAL_BACKEND_PROFILE=isolated ./scripts/run_local_backend.sh` starts a safe local API with embeddings/Qdrant/extraction disabled and `/chat` returning a degraded-but-stable response instead of a `500`.
- `LOCAL_BACKEND_PROFILE=full ./scripts/run_local_backend.sh` is now verified working locally against:
  - SQLite in `/tmp`
  - local Qdrant on `127.0.0.1:6333`
  - local llama.cpp on `127.0.0.1:8001/v1`
- `/chat` is verified end-to-end for local commentary retrieval plus llama.cpp JSON generation.
- `/chat` uses commentary collections, not `asx_docs`.
  - Primary collection: `commentary_chunks`
  - Optional secondary collection: `commentary_chunks_v2`
- `commentary_chunks_v2` is optional at runtime. If only `commentary_chunks` exists, the retriever now falls back cleanly.
- Local launcher precedence is now:
  - `.env`
  - `.env.local`
  - explicit shell env wins over both
- Local launcher also forces `DATA_ROOT` to the repo `data/` directory unless you explicitly override `DATA_ROOT`, which avoids accidental `/data/...` Docker paths in local runs.

## Stable Validation Baseline (2026-03-19)
Validated command sequence:
1. `bash scripts/start_system.sh`
2. `bash scripts/validate_system.sh`
3. `python -m ruff check autodev financial-engine_v2/backend scripts`
4. `pytest autodev/tests`
5. `pytest financial-engine_v2/backend/tests`
6. `pytest scripts`
7. `bash scripts/run_canonical_dataset_checks.sh`
8. `python scripts/check_canonical_regression.py --baseline reports/baselines/canonical_eval_baseline_latest.json --news-report reports/news_eval_report.json --company-report reports/company_eval_report_v2.json --reference-report reports/eval_queries_report.json`
9. `python scripts/validate_financial_metrics_gates.py reports/financial_metrics.json --out-json reports/financial_metrics.gates.json`
10. `python scripts/validate_financial_coverage_gates.py reports/financial_metrics.json --out-json reports/financial_metrics.coverage_gates.json`

Current passing gate set:
- Ruff on `autodev`, `financial-engine_v2/backend`, and `scripts`
- Pytest on `autodev/tests`, `financial-engine_v2/backend/tests`, and `scripts`
- Canonical dataset eval + canonical regression baseline gate
- Financial metrics gate
- Financial coverage gate

Operational notes:
- In restricted socket environments, health and smoke checks may print `SKIP due restricted environment`; this is expected and non-fatal.
- Canonical dataset checks support CPU fallback by default (`REQUIRE_CUDA=0`), and only fail for missing CUDA when `REQUIRE_CUDA=1`.
- Canonical regression requires these baseline fixtures:
  - `reports/baselines/canonical_eval_baseline_latest.json`
  - `reports/news_eval_queries.json`
  - `reports/company_eval_queries.json`
  - `reports/eval_queries.json`
- Detailed baseline runbook: `../docs/validation_baseline.md`

## What isn’t included (next phase)
- Web frontend UI
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
   - `export PATH="$PWD/.venv/bin:$PATH"`
   - `LOCAL_BACKEND_PROFILE=isolated ./scripts/run_local_backend.sh`
3. Smoke test:
   - `curl http://localhost:8000/api/health`
   - `curl "http://localhost:8000/api/docs?ticker=BHP"`
   - `curl -X POST "http://localhost:8000/api/backfill/ticker/BHP?years=1&process_documents=false"`
   - `curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message":"What drives mining stock returns?","mode":"analysis"}'`
   - or run `./scripts/smoke_local.sh`

Defaults in local mode:
- SQLite database at `./data/fe_local.db`
- Sync task mode (`TASK_MODE=sync`)
- Auto-create tables enabled
- Embeddings/Qdrant/LLM extraction disabled by default
- MarketIndex fallback enabled by default (`ENABLE_MARKETINDEX_FALLBACK=true`) using `../data/raw/marketindex_announcements.json`
- `.env.local` is loaded when present before profile defaults are applied
- `LOCAL_BACKEND_PROFILE=full` enables embeddings, Qdrant, and extraction for local runs
- If the default SQLite file is unreadable in isolated mode, launcher fallback is `./data/fe_local_runtime.db`
- Local llama.cpp/auth env support includes `LLAMACPP_URL`, `LLM_API_KEY`, and `EMBEDDING_API_KEY`
- Explicit shell env now overrides `.env` and `.env.local` for local runs
- Local runs default `DATA_ROOT` to `./data`, not `/data`
- If MarketIndex URLs return Cloudflare `403`, those docs are marked `blocked_marketindex_403` and skipped
- MarketIndex documents are treated as headed-only and marked `blocked_marketindex_headed_required` in local non-headed mode

## Local Full Mode (Verified)
Use this mode when you want real `/chat` responses from local Qdrant + llama.cpp.

Prerequisites:
- active venv or `export PATH="$PWD/.venv/bin:$PATH"`
- Qdrant running on `127.0.0.1:6333`
- llama.cpp server running on `127.0.0.1:8001/v1`
- matching local auth key, e.g. `local-openai-key`
- commentary data loaded into `commentary_chunks`

Known-good command:

```bash
cd ~/tenn/financial-engine_v2
export PATH="$PWD/.venv/bin:$PATH"

LOCAL_BACKEND_PROFILE=full \
DATABASE_URL=sqlite:////tmp/financial-engine_v2-full.db \
DOCS_ROOT="$HOME/tenn/financial-engine_v2/data/asx/docs" \
QDRANT_URL=http://127.0.0.1:6333 \
QDRANT_TIMEOUT_SECONDS=120 \
LLAMACPP_URL=http://127.0.0.1:8001/v1 \
LLAMACPP_TIMEOUT_SECONDS=180 \
LLM_API_KEY=local-openai-key \
EMBEDDING_API_KEY=local-openai-key \
EMBED_MODEL=nomic-embed-text \
EMBEDDING_MODEL=nomic-embed-text \
EXTRACT_MODEL=qwen2.5-coder-14b \
ENABLE_EXTRACTION=false \
./scripts/run_local_backend.sh
```

Expected launcher output:
- `data_root=/home/.../financial-engine_v2/data`
- `database=sqlite:////tmp/financial-engine_v2-full.db`
- `docs_root=/home/.../financial-engine_v2/data/asx/docs`

Smoke test:

```bash
curl http://127.0.0.1:8000/api/health

curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What drives mining stock returns?","mode":"analysis"}'
```

Notes:
- `/chat` can work with `ENABLE_EXTRACTION=false`; extraction is not required for commentary-based chat.
- If `/chat` returns a degraded response saying retrieval is unavailable, first check that `commentary_chunks` exists and contains points.
- If `/chat` times out in full mode, increase `LLAMACPP_TIMEOUT_SECONDS` to `300`.
- `commentary_chunks_v2` is optional.
- Keep the embedding model aligned with your commentary collection dimension. The checked-in commentary tests assume `nomic-embed-text` style 768-d embeddings.
- If `LLAMACPP_URL` is your only local llama.cpp server and it is serving a chat GGUF, set `EMBEDDING_URL` to a separate embedding runtime or rebuild the commentary collections for that model's embedding dimension.

Example commentary ingest:

```bash
cd ~/tenn/financial-engine_v2

PYTHONPATH=backend \
QDRANT_URL=http://127.0.0.1:6333 \
LLAMACPP_URL=http://127.0.0.1:8001/v1 \
LLM_API_KEY=local-openai-key \
EMBEDDING_API_KEY=local-openai-key \
EMBED_MODEL=nomic-embed-text \
EMBEDDING_MODEL=nomic-embed-text \
./.venv/bin/python scripts/ingest_transcript.py \
  <transcript-path> \
  --source-name "<source-name>" \
  --source-type youtube_transcript \
  --speaker "<speaker>" \
  --published-at "2026-03-18T00:00:00Z" \
  --topic-tags "mining,stocks,commentary"
```

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
These are the packaged production-style workflows currently checked in.

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

3. Daily ASX all-announcements ingest (separate from ticker backfill):
   - `python3 scripts/daily_asx_all_announcements_action.py --date 2026-02-18`
   - Ingests all announcements detected on ASX for the target day, inserts new docs, downloads PDFs, and classifies.
   - Includes conservative ASX request pacing defaults in sweep mode (`request_delay_ms=700`, `request_jitter_ms=900`, `failure_backoff_ms=2500`).
   - Output JSON: `reports/asx/daily_asx_all_announcements_report.json`
   - JSON reports include `run_metadata` (script, python version, git branch/commit/dirty flag).

## Simplest Run (One Command)
If you want a single command with hardcoded defaults, use:

- `python3 run.py`

This wrapper runs:
- ticker full-history gathering
- daily MarketIndex scrape/download
- or daily ASX market-wide ingest when `CONFIG["workflow"] = "daily_asx_marketwide"`

All config is hardcoded in `run.py` under `CONFIG`.

Common edits in `run.py`:
- `CONFIG["workflow"]`: `"both"`, `"full_history"`, `"daily_marketindex"`, or `"daily_asx_marketwide"`

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

Operational controls:
- Single active action at a time (new runs are blocked while one job is running).
- "Kill Running Action" is available in both Chat and Operations screens for long-running jobs.

## Key environment variables
- `OLLAMA_URL` (default `http://127.0.0.1:11434`)
- `LLAMACPP_URL` (default `http://127.0.0.1:8001/v1` from the local launcher)
- `LLAMACPP_URL` and `OLLAMA_URL` must point to different endpoints; startup fails fast if they match.
- `EMBED_MODEL` (default `nomic-embed-text`)
- `EXTRACT_MODEL` (default `llama3:latest`)
- `DOCS_ROOT` (default `./data/asx/docs` in local mode)
- `LLM_API_KEY` and `EMBEDDING_API_KEY` for llama.cpp-compatible auth headers
- `MARKET_DATA_MODE` (`yahoo` or `openbb_sidecar`)
- `OPENBB_SIDECAR_BASE_URL`

## LLM Backend Configuration
You MUST configure separate endpoints:

- `LLAMACPP_URL=http://127.0.0.1:8001/v1`
- `OLLAMA_URL=http://127.0.0.1:11434`

The application will fail to start if:
- both URLs resolve to the same host:port
- llama.cpp endpoint behaves like Ollama
- Ollama endpoint is unreachable

This prevents silent backend aliasing.

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
- Refresh digest + install a Tenn `developer_instructions` profile into `~/.codex/config.toml`:
  - `make codex-prompt-refresh`
  - optional override: `DEVELOPER_INSTRUCTIONS_FILE=/path/to/prompt.md make codex-prompt-refresh`
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
  - `# BEGIN TENN_DEVELOPER_INSTRUCTIONS`
  - `# END TENN_DEVELOPER_INSTRUCTIONS`
- bundled repo prompt profile:
  - `codex_prompts/tenn-default.md`

## Notes
- This discovery method is heuristic; ASX page structure may change. It’s modular (`backend/app/providers/asx_provider.py`).
- Missing metrics are stored as NULL by design.
