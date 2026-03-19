# System Flags, Settings, and Env Vars That Limit/Break Functionality

This document captures non-cockpit runtime controls across backend, worker, ingestion, and news pipeline that can suppress features or cause hard failures.

## Hard-fail and high-risk runtime controls

| Control | Impact | Failure mode | Source |
|---|---|---|---|
| `DATABASE_URL` (required by Alembic env) | Required for migration execution. | Missing variable raises `KeyError` in migration runtime. | `financial-engine_v2/backend/app/alembic/env.py` |
| `OLLAMA_URL`, `EMBED_MODEL` model drift vs stored runtime model file | Enforced model consistency for RAG index compatibility. | Backend startup raises `RuntimeError` on embedding model mismatch; explicit rebuild required. | `financial-engine_v2/backend/app/main.py` |
| `ENABLE_QDRANT=true` + unavailable Qdrant | RAG startup validation depends on Qdrant connectivity/collection checks. | Startup validation fails or RAG query fails at runtime. | `financial-engine_v2/backend/app/main.py`, `financial-engine_v2/backend/app/services/rag.py` |
| `ENABLE_EMBEDDINGS=false` | Disables embedding generation and RAG query path. | `/rag/query` errors with backend disabled state. | `financial-engine_v2/backend/app/services/rag.py`, `financial-engine_v2/backend/app/services/pipeline.py` |
| `ENABLE_QDRANT=false` | Disables vector-store usage. | `/rag/query` errors with qdrant disabled state; no vector upsert in processing. | `financial-engine_v2/backend/app/services/rag.py`, `financial-engine_v2/backend/app/services/pipeline.py` |
| `ENABLE_EXTRACTION=false` | Disables financial metric extraction from documents. | Processing completes with `skipped_extraction`; no new financial rows from model extraction. | `financial-engine_v2/backend/app/services/pipeline.py` |

## Execution mode and throughput controls

| Control | Default | Limiting behavior | Source |
|---|---|---|---|
| `TASK_MODE` (`celery` or `sync`) | `celery` | In `celery` mode, no worker/broker means jobs enqueue but do not execute; in `sync`, API thread does all work and can block. | `financial-engine_v2/backend/app/core/config.py`, `financial-engine_v2/backend/app/api/routes.py` |
| `BACKFILL_CONCURRENCY` | `1` | Very low value throttles backfill throughput significantly; very high values can overload Ollama/IO. | `financial-engine_v2/backend/app/core/config.py`, `financial-engine_v2/backend/app/services/pipeline.py` |
| `EMBEDDING_BATCH_SIZE` | `32` | Oversized values can increase memory pressure or model timeouts; undersized values reduce throughput. | `financial-engine_v2/backend/app/core/config.py`, `financial-engine_v2/backend/app/services/pipeline.py` |

## Market data routing and sidecar gates

| Control | Behavior | Functional risk | Source |
|---|---|---|---|
| `MARKET_DATA_MODE` | `yahoo` or `openbb_sidecar` (invalid values silently coerce to `yahoo`) | Mis-typed value may silently route to Yahoo instead of intended sidecar path. | `financial-engine_v2/backend/app/api/routes.py` |
| `OPENBB_SIDECAR_BASE_URL` / `OPENBB_SIDECAR_TIMEOUT_SECONDS` | Defines sidecar endpoint/timeouts. | If sidecar is down/unreachable while mode is sidecar, price/fundamental calls fail. | `financial-engine_v2/backend/app/api/routes.py` |
| `OPENBB_SIDECAR_ENABLE_STAGING_WRITES=false` | Disables snapshot persistence from sidecar responses. | Functionality works, but no staging tables are written (can look like missing data persistence). | `financial-engine_v2/backend/app/api/routes.py` |

## Storage/path settings that commonly break host runs

| Control | Risk | Source |
|---|---|---|
| `DOCS_ROOT` default container path (`/data/asx/docs`) | Host-side scripts can fail with permission/path issues if not remapped to writable local path. | `financial-engine_v2/.env.example`, `financial-engine_v2/README.md` |
| `IMPORTANCE_OUTPUT_ROOT` | Wrong/unwritable path breaks materialization/copy outputs. | `financial-engine_v2/backend/app/core/config.py`, `financial-engine_v2/README.md` |
| `AUTO_CREATE_TABLES=false` | Fresh DBs without migrations/tables can fail at read/write time. | `financial-engine_v2/backend/app/core/config.py`, `financial-engine_v2/backend/app/main.py` |

## Data suppression controls (intentional filters that can look like missing data)

| Control | Limiting effect | Source |
|---|---|---|
| `financial-engine_v2/config/ticker_quarantine.json` | Entire tickers excluded from future universe sync runs. | `financial-engine_v2/scripts/ticker_quarantine.py`, `docs/ops/ticker_quarantine.md` |
| `financial-engine_v2/config/document_quarantine_rules.json` | Specific documents/substrings excluded from ingestion/extraction (currently includes 29M subsidiary filters). | `financial-engine_v2/config/document_quarantine_rules.json`, `docs/ops/ticker_quarantine.md` |
| `--no-quarantine` in sync scripts | Disables quarantine filtering and updates, re-allowing potentially noisy/non-ASX symbols. | `docs/ops/ticker_quarantine.md` |

## News pipeline controls that can suppress yield

| Control | Limiting behavior | Source |
|---|---|---|
| EODHD capture policy + API key | Live fallback is auto-enabled when captures are missing and `EODHD_API_KEY` is present. | `scripts/news_pipeline/cli_common.py` |
| `EODHD_API_KEY` missing when captures absent | Prevents EODHD live fallback; provider fetch fails when no capture contract exists. | `scripts/fetch_daily_news.py`, `scripts/backfill_news.py` |
| `--no-sweep-stale-runs` | Disables stale run auto-heal; interrupted runs can remain `running` until manual cleanup. | `scripts/fetch_daily_news.py`, `scripts/backfill_news.py` |
| `--sweep-stale-runs-hours` too high | Delays stale-run cleanup and can leave operational status noisy for longer windows. | `scripts/fetch_daily_news.py`, `scripts/backfill_news.py`, `scripts/news_pipeline/db.py` |
| `--embed-backend hash` (default in orchestrator) | Runs with cheap hash embeddings (fast, but lower semantic quality than model embeddings). | `scripts/run_news_pipeline.py` |
| Aggressive limits (`--max-tickers`, `--max-days`, provider batch caps) | Artificially reduces ingest coverage and recall. | `scripts/fetch_daily_news.py`, `scripts/backfill_news.py`, `scripts/news_pipeline/cli_common.py` |

## Priority checks to run before blaming model quality

- Verify `DATABASE_URL` points to the intended DB and schema is initialized.
- Verify `ENABLE_EMBEDDINGS`, `ENABLE_QDRANT`, and `ENABLE_EXTRACTION` match intended mode.
- Verify `TASK_MODE` aligns with available worker/broker runtime.
- Verify `OLLAMA_URL`, `EMBED_MODEL`, and `EXTRACT_MODEL` are reachable and installed.
- Verify `DOCS_ROOT`/`IMPORTANCE_OUTPUT_ROOT` are writable in the current execution context (host vs container).
- Verify quarantine lists/rules are not unintentionally suppressing target tickers/docs.
