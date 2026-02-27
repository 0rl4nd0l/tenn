# TENN Migration Report

Date: 2026-02-26 (UTC)  
Repository: `/home/l4nd0/tenn`  
Prepared for: context-free project migration of TENN/financial-engine stack

## 1. Executive Summary

TENN is currently a local-first ASX ingestion/extraction platform with an operational backend, large script-based orchestration layer, and a terminal cockpit. The active runtime is `financial-engine_v2`, with root `run.py` delegating into that subtree.

The system is functional for ingestion, download, extraction, and structured persistence, but migration should be treated as controlled re-platforming rather than simple file copy. There are known drifts and a few verified defects that should be resolved before production cutover in a new project.

Primary migration priorities:
1. Preserve path and env assumptions used by scripts and providers.
2. Resolve worker/task path divergence.
3. Resolve `update_ticker_financials` script/test drift.
4. Re-validate with canonical checks and health gates in the target project.

## 2. Scope and Evidence Base

This report is based on direct source and artifact inspection in this repo on 2026-02-26.

Reviewed domains:
1. Runtime entrypoints and docs.
2. Backend API, providers, pipeline, DB models, Alembic migrations.
3. Celery worker paths and parity tests.
4. Orchestration scripts and quality gates.
5. Cockpit TUI runtime, controls, and persistence.
6. Canonical dataset/eval workflows and health reporting.
7. Research-only integrations and legacy/archive boundaries.

## 3. System Topology

### 3.1 Active Entry Points

1. Root launcher: `run.py`
   - Delegates to `financial-engine_v2/run.py`.
2. Primary runtime launcher: `financial-engine_v2/run.py`
   - Hardcoded `CONFIG`.
   - Default `workflow="both"`:
     - `full_history_ticker_sync.py`
     - `daily_marketindex_action.py`
3. Local backend launcher: `financial-engine_v2/scripts/run_local_backend.sh`
4. Cockpit launcher:
   - `python -m cockpit.main`
   - `financial-engine_v2/scripts/cockpit_tui.py` (bootstrap wrapper)

### 3.2 Runtime Profiles

1. One-command local orchestrator:
   - SQLite default, sync tasks, extraction/embeddings disabled, MarketIndex fallback enabled.
2. Docker stack:
   - `postgres`, `redis`, `qdrant`, `backend`, `worker`.
3. Isolated local backend mode:
   - Uvicorn + SQLite + memory broker defaults.
4. Cockpit operator mode:
   - TUI with job execution, verification, watchlist, alerts, optional web/RAG/DB diagnostics.

## 4. Component Inventory and Behavior

### 4.1 Backend/API

Framework: FastAPI (`backend/app/main.py`, `backend/app/api/routes.py`)

Current API surface:
1. `GET /api/health`
2. `GET /api/docs?ticker=...`
3. `GET /api/financials?ticker=...`
4. `GET /api/risk?document_id=...`
5. `GET /api/price?ticker=...&range=...&interval=...&exchange=...`
6. `POST /api/backfill/asx20`
7. `POST /api/backfill/ticker/{ticker}`

### 4.2 Database Schema

Tables:
1. `documents`
2. `extraction_runs`
3. `asx_periodic_financials`
4. `asx_risk_notes`

Key persistence behavior:
1. Partial unique index on non-empty `documents.source_url` for dedupe.
2. `documents.pdf_sha256` stores both hash and operational marker states (example: `blocked_marketindex_403`).
3. Financial table primary key: `(ticker, period_end, period_type)`.

### 4.3 Discovery and Ingestion Pipeline

Main behavior in `backend/app/services/pipeline.py` and `pipeline_service.py`:
1. Discover ASX announcements by ticker/date.
2. Optional MarketIndex fallback merge.
3. Normalize source URLs and dedupe.
4. Insert documents with canonical pathing.
5. Download PDF with signature checks and HTML fallback extraction.
6. Process document:
   - text extraction
   - chunking
   - optional embedding/Qdrant
   - optional Ollama extraction
   - upsert financial and risk rows
7. Classify announcement importance and optional output materialization.

Failure taxonomy implemented:
1. `ocr_or_text_unavailable`
2. `parser_timeout`
3. `llm_invalid_json`
4. `provider_network`
5. `corrupted_pdf`
6. `unknown`

### 4.4 MarketIndex Handling

Two modes:
1. Daily MarketIndex ingest + downloader (`daily_marketindex_action.py`, `marketindex_download_pdfs.py`)
2. Headed recovery for blocked docs (`recover_marketindex_headed.py`, `marketindex_headed_recovery.py`)

Important rules:
1. Headless mode is blocked for MarketIndex download/recovery.
2. Quality gate in downloader:
   - `min_download_count`
   - `min_success_ratio`
   - fail only when both thresholds are missed.
3. Marker statuses support blocked/unresolved tracking.

### 4.5 Worker Paths

There are two `backfill_ticker` implementations:
1. Backend-wrapped Celery task: `backend/app/worker_tasks.py`
2. Legacy/duplicated worker task: `worker/worker_app/tasks.py`

Risk:
1. Worker behavior drift depending on which path is active.
2. Migration must select one authoritative task path.

### 4.6 Cockpit Subsystem

Cockpit provides:
1. Chat + command routing.
2. Action registry to run operational scripts.
3. Runtime job guards (single active job + heavy action conflict checks).
4. Verification checks for missing PDFs, blocked docs, extraction failures, low confidence rows.
5. Persistent state DB (`~/.financial_engine_cockpit/state.db` by default).
6. Optional web fetch, qualitative context retrieval, and read-only DB diagnostics.

Guardrails:
1. SQL diagnostics restricted to SELECT/CTE style and blocked write tokens.
2. Explicit access toggles (`web`, `rag`, `dbdiag`) and resume handling.

### 4.7 Script Ecosystem

Observed script volumes:
1. `financial-engine_v2/scripts`: 71 Python scripts, 38 `test_*.py`.
2. root `scripts`: 91 Python scripts, 47 `test_*.py`.

Major script categories:
1. Ingestion orchestration (`full_history_ticker_sync.py`, `daily_*`, `asx_enrichment_*`, `resume_pending_downloads.py`).
2. MarketIndex scraping/downloading/recovery.
3. Extraction backlog and failure classification.
4. RAG context DB build/query/eval.
5. Health snapshots and gating.
6. Scoring/coverage/analysis utilities.
7. Governance/context refresh hooks.

### 4.8 Optional Isolated Integration

`integrations/newspaper4k_au` is intentionally isolated:
1. Dedicated venv.
2. JSONL output only.
3. No production DB writes.
4. Intended as optional research upstream.

## 5. Finished, Unfinished, and Partial Features

### 5.1 Finished / Operational

1. ASX discovery and document insertion flow.
2. PDF download and canonical storage pathing.
3. End-to-end extraction pipeline with optional embeddings/Qdrant/Ollama.
4. Financial/risk persistence and query endpoints.
5. MarketIndex daily action and headed recovery pipeline.
6. Quality-gated orchestration reports.
7. Cockpit operator workflows and guardrails.
8. Canonical dataset check scripts and scoring framework.

### 5.2 Explicitly Out of Scope (Current Phase)

Per runtime README:
1. Frontend UI.
2. Factor scoring/signals/proposals.
3. Broker execution.

### 5.3 Partial / Drifted

1. Worker implementation split (backend wrapper vs legacy worker code).
2. News corpus marked research-only with compliance gating.
3. Ops hardening worksheet contains unresolved placeholder command tokens.
4. `log_change_impact.py` intentionally defaults several fields to `TBD`.
5. Some docs no longer perfectly align with latest extraction/runtime code path details.

## 6. Verified Defects and Risks

### 6.1 Verified in Current Tree

1. `update_ticker_financials.py` references `args.zero_rows_policy` in dry-run plan, but parser does not define it.
2. `test_update_ticker_financials_quality_gate.py` fails in current tree (3 errors) due script/test contract drift.
3. API Celery enqueue routes do not pass `years` and `process_documents` values into queued task args.

### 6.2 Structural Migration Risks

1. Path-coupled defaults:
   - scripts assume relative project layout.
2. Marker-overloaded `pdf_sha256` field:
   - hashes and status markers share one column.
3. Mixed local and container defaults:
   - wrong profile in migration can silently alter behavior.
4. Canonical checks may hard-fail without GPU unless explicitly overridden.
5. Legacy artifacts can be mistaken for active runtime assets.

## 7. Current Operational Metrics Snapshot

### 7.1 Headline Coverage Eval

Artifact: `reports/analysis/asx_headline_coverage_eval.json`  
Timestamp: `2026-02-25T11:10:56Z`

1. Baseline corpus (`news`) strong/medium chunk rate: `25.5825`
2. RSS corpus (`news_asx_rss`) strong/medium chunk rate: `12.3288`
3. Delta percentage points: `-13.2537`
4. Zero-hit tickers increased from `339` to `363`

### 7.2 Health Snapshot

Artifact: `reports/research_engine_health.json`  
Timestamp: `2026-02-25T04:01:05Z`

1. `overall_status`: `degraded`
2. GPU unavailable in snapshot.
3. News drift flags include low ticker coverage and stale news.
4. Structured extraction coverage shown as `0.0` in that sampled snapshot.

### 7.3 Recent Scorecard Baseline

Latest aggregate scorecard by mtime:
`reports/score_runs/run_20260226_174000_asx_noocr_ab/aggregate_scorecard.json`

Totals:
1. Precision: `0.995614`
2. Recall: `1.0`
3. F1: `0.997802`
4. Listed gates: passing in this run.

## 8. Dependency and Environment Profile

### 8.1 Core Dependencies

Backend/worker requirements include:
1. FastAPI/Uvicorn
2. SQLAlchemy + Alembic
3. Celery + Redis
4. Qdrant client
5. PyMuPDF
6. Playwright
7. Textual
8. httpx/BeautifulSoup/lxml

### 8.2 Environment Toggles With Behavior Impact

Critical env vars:
1. `DATABASE_URL`
2. `TASK_MODE` (`sync` vs `celery`)
3. `AUTO_CREATE_TABLES`
4. `ENABLE_EMBEDDINGS`
5. `ENABLE_QDRANT`
6. `ENABLE_EXTRACTION`
7. `ENABLE_MARKETINDEX_FALLBACK`
8. `MARKETINDEX_ANNOUNCEMENTS_FILE`
9. `OLLAMA_URL`, `EMBED_MODEL`, `EXTRACT_MODEL`

Migration implication:
1. Runtime behavior changes significantly by env profile.
2. Profile pinning is required in target project.

## 9. Migration Readiness Assessment

### 9.1 Ready

1. Core ingestion and extraction architecture is coherent.
2. DB schema and migration chain are clearly defined.
3. Script-driven operations and report outputs are mature.
4. Cockpit provides practical operational control plane.

### 9.2 Not Ready Without Remediation

1. Worker path divergence unresolved.
2. `update_ticker_financials` script/test drift unresolved.
3. Celery route parameter propagation gap unresolved.
4. Target project needs explicit runtime profile contract to avoid accidental mode switching.

## 10. Migration Recommendations

Pre-cutover recommendations:
1. Choose one authoritative Celery task implementation and remove/retire the other path.
2. Fix `update_ticker_financials` parser/runtime/test contract and make suite green.
3. Update API enqueue routes to pass `years` and `process_documents` when enqueuing.
4. Define profile contracts:
   - local-isolated
   - docker-celery
   - cockpit-assisted
5. Keep legacy/archive assets separated from active runtime in target repo.
6. Add migration acceptance gate requiring:
   - smoke tests
   - selected regression tests
   - health snapshot
   - canonical checks

## 11. Deliverables Pair

This report is paired with:
1. `docs/migration/MIGRATION_RUNBOOK.md` (execution steps and rollback)

