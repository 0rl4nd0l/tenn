# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Parent operating instructions (safety rules, entrypoints, pre-task/pre-write checks, secret handling) live in `../CLAUDE.md`. Read that first.
>
> **SYSTEM CONTRACT:** [docs/architecture/SYSTEM_CONTRACT.md](../docs/architecture/SYSTEM_CONTRACT.md) is the authoritative system specification. All changes to backend, extraction, RAG, embeddings, or worker tasks MUST comply with it. If in doubt, read the contract before acting.

---

## Commands

```bash
# Activate venv
export PATH="$PWD/.venv/bin:$PATH"

# Start (isolated — no Qdrant/embeddings/extraction)
LOCAL_BACKEND_PROFILE=isolated ./scripts/run_local_backend.sh

# Start (full — requires Qdrant on :6333, llama.cpp on :8001/v1)
LOCAL_BACKEND_PROFILE=full ./scripts/run_local_backend.sh

# Health check
curl -sS http://127.0.0.1:8000/api/health

# Lint
python -m ruff check backend scripts

# Tests
pytest backend/tests
pytest backend/tests/test_model_routing.py  # single test file

# DB migrations (Docker only)
docker compose exec backend alembic upgrade head

# Agent context refresh (updates ~/.codex/config.toml)
make context-refresh

# Agent context + Tenn developer_instructions profile
make codex-prompt-refresh

# Alternate Codex prompt profiles
CODEX_PROFILE=bug make codex-prompt-refresh
CODEX_PROFILE=review make codex-prompt-refresh
CODEX_PROFILE=extraction make codex-prompt-refresh
CODEX_PROFILE=audit make codex-prompt-refresh
```

---

## Architecture

### Ingestion Pipeline

`pipeline.py` is the core ingestion service. The data flow is:

```
ASX/MarketIndex provider → PDF download + SHA256
  → PDF structure extraction (PyMuPDF find_tables — tables + sections)
  → chunking → embeddings (Qdrant upsert)
  → Multipass LLM extraction (llama.cpp JSON, + prose fallback for shares_outstanding)
  → Postgres (documents, extraction_runs, asx_periodic_financials)
```

**PDF extraction backend:** PyMuPDF `find_tables()` is the default (`EXTRACTION_BACKEND=pymupdf`).
Docling is available as opt-in via `EXTRACTION_BACKEND=docling` but is much slower (120s+ vs ~1-25s)
and typically times out on ASX filings. Both backends produce the same `StructuredDocument` interface.

Pipeline tasks can run in two modes set by `TASK_MODE`:
- `sync` — direct call in the API request (used in local mode)
- `celery` — dispatched to a Celery worker via Redis broker (production)

### LLM Backend Endpoints

Two endpoints (`core/config.py`):

| Endpoint | Purpose | Default |
|----------|---------|---------|
| `LLAMACPP_URL` | Chat, routing, coding, extraction | `http://127.0.0.1:8001` |
| `OLLAMA_URL` | Embeddings (`nomic-embed-text`) | `http://127.0.0.1:11434` |

A single llama-server runs in **router mode** on port 8001 (`--models-dir /mnt/nvme/tenn/models --models-max 1`). All GGUFs in the models directory are available; clients select per-request via the `model` field. Only one model occupies VRAM at a time. Default chat model: `qwen3-30b-a3b-instruct` (MoE 30B/3B-active, llmfit score 94.0). Extraction requests `qwen2.5-14b-instruct` by model name; the router loads it on demand.

Current host storage alignment (2026-04-07):

- runtime data: `/mnt/nvme/tenn/runtime-data`
- llama.cpp GGUF directory: `/mnt/nvme/tenn/models`
- root Ollama store: `/usr/share/ollama/.ollama/models` is not the primary Tenn serving path
- retained root Ollama models: `qwen2.5:32b`, `gpt-oss:20b-cloud`
- archived inactive root Ollama models: `/mnt/sdb2/home/l4nd0/tenn/.archives/ollama-root-store-2026-04-07`

`EXTRACTION_LLAMACPP_URL` is a legacy override for running a dedicated extraction server on a separate port. When unset (default), extraction uses `LLAMACPP_URL` via router mode.

The app **fails to start** if `LLAMACPP_URL` and `OLLAMA_URL` resolve to the same host:port. This prevents silent backend aliasing.

### Model Routing (`backend/app/services/router.py`)

Requests are classified by heuristic pattern matching into task types (`coding`, `reasoning`, `deep_reasoning`, `router`). Config lives in `backend/app/config/model_routing.yaml`. Routing decisions feed an adaptive optimizer (`router_optimizer.py`) that uses latency/throughput/error/GPU metrics.

### RAG / Retrieval

- ASX document collection: `asx_docs` (Qdrant)
- Commentary collection: `commentary_chunks` (primary), `commentary_chunks_v2` (optional fallback)
- `/chat` uses commentary collections, not `asx_docs`
- Hybrid retrieval: `hybrid_retriever.py` (dense + optional reranking via `reranker.py`)
- Query entrypoint: `POST /api/chat` → `tenn_chat.py` → `retrieval_orchestrator.py`

### Chat Learning Loop

The `/chat` endpoint includes a learning loop that improves quality over time:

- **Fast path (deterministic):** Computes composite quality metric (retrieval precision + model confidence + session coherence) → updates `chat_preferences.json` with learned retrieval params and router role preferences
- **Slow path (periodic LLM review):** Reviews session transcripts → patches skill files (`chat_skill.md`, `tenn-learned.md`)
- **Rule 0 integration:** Both `retrieval_orchestrator.py` and `router_optimizer.py` check `chat_preferences.json` at startup and apply learned preferences when available
- **Rollback protection:** Snapshot mechanism (`.prev` files) for regression guard

Quality metric components:
- **Retrieval precision (0.4 weight):** avg `final_score` from retrieved chunks
- **Model confidence (0.35 weight):** router optimizer confidence score
- **Session coherence (0.25 weight):** `1 - cosine_similarity(current_query, prev_query)` — detects user rephrasing

See [docs/architecture/20_chat_learning_loop.md](../docs/architecture/20_chat_learning_loop.md) for full design.

### Key Services

| File | Role |
|------|------|
| `backend/app/main.py` | FastAPI app, startup validation (Qdrant dimension check, embedding model mismatch guard) |
| `backend/app/core/config.py` | `Settings` (pydantic-settings), URL normalization for sqlite/redis/qdrant, LLM endpoint conflict check |
| `backend/app/services/pipeline.py` | Core ingestion: download → extract → embed → persist |
| `backend/app/services/docling_extract.py` | PDF → `StructuredDocument` (tables + sections). Default: PyMuPDF `find_tables()`. Opt-in: docling via `EXTRACTION_BACKEND=docling` |
| `backend/app/services/multipass_extraction.py` | 4-pass LLM extraction: classify → locate tables → extract metrics → reconcile (+ prose fallback for shares_outstanding) |
| `backend/app/services/embeddings.py` | Qdrant upsert, collection management, dimension validation |
| `backend/app/services/llm.py` | `embed_texts`, `generate_json`, `get_routing_decision` — all LLM calls go through here |
| `backend/app/services/extraction.py` | `build_prompt` for financial JSON extraction; clips to first 18,000 chars |
| `backend/app/services/router.py` | Task-type classifier + adaptive model selector |
| `backend/app/services/router_optimizer.py` | Adaptive model routing with learned role preferences (Rule 0) |
| `backend/app/services/retrieval_orchestrator.py` | Multi-source retrieval coordinator with learned params (Rule 0) |
| `backend/app/services/chat_preferences.py` | Chat learning loop: atomic preference I/O, snapshot/rollback |
| `backend/app/services/chat_quality_scorer.py` | Chat learning loop: composite quality metric computation |
| `backend/app/services/chat_preference_updater.py` | Chat learning loop: quality turns → preferences with min sample thresholds |
| `backend/app/services/chat_skill_reviewer.py` | Chat learning loop: LLM-driven skill patching (slow path) |
| `backend/app/services/analysis_rag_adapter.py` | Thin adapter: embed query → Qdrant search → normalized hits for analysis modules |
| `backend/app/api/routes.py` | Backfill, docs, financials, ingest endpoints |
| `backend/app/routes/chat.py` | `/chat` endpoint with quality scoring integration |

### DB Models (Postgres/SQLite via SQLAlchemy)

- `documents` — one row per PDF, SHA256, source URL
- `extraction_runs` — one per document extraction attempt, stores `extractor_version` and `prompt_hash`
- `asx_periodic_financials` — structured financial metrics extracted by LLM
- `asx_risk_notes` — risk/guidance summaries
- `openbb_snapshots` — market data staging

Migrations: `backend/app/alembic/versions/`

---

## Critical Invariants

- **Embedding model changes require a full collection rebuild.** Startup enforces this via `reports/runtime_embedding_model.txt` — if the stored model differs from `EMBED_MODEL` and Qdrant has live vectors, startup aborts.
- **Vector ID format is `document_id:chunk_index`** — do not change without rebuilding the collection.
- **Distance metric is `COSINE`** — changing this requires a collection rebuild.
- **`LLAMACPP_URL` must not include `/v1`** in env; the launcher and config layer strip it during normalization. The stored default in `Settings` is without `/v1`.
- **`DATA_ROOT` controls all derived paths** (`DATABASE_URL`, `DOCS_ROOT`, `MARKETINDEX_ANNOUNCEMENTS_FILE`, `IMPORTANCE_OUTPUT_ROOT`) unless each is explicitly overridden via shell env.
- **Shell env wins over `.env` / `.env.local`** in the local launcher — this is explicit by design.

---

## Local Profiles

| Profile | DB | Embeddings | Qdrant | Extraction | Use for |
|---------|----|-----------|--------|-----------|---------|
| `isolated` | SQLite `/tmp/` | off | off | off | smoke tests, API shape validation |
| `full` | configured | on | on | configurable | real RAG/chat testing |

`ENABLE_EXTRACTION=false` is safe with `LOCAL_BACKEND_PROFILE=full` — `/chat` works without extraction.

Validation note: in isolated mode, `run_local_backend.sh` may fall back to `/tmp/financial-engine_v2-fe_local_runtime.db` when the configured SQLite path is unsuitable for the isolated profile. That does not change the migrated docs root used for local storage-pressure validation.

---

## Production Scripts

All in `scripts/`. Key ones:

- `full_history_ticker_sync.py` — bulk backfill by ticker(s)
- `daily_marketindex_action.py` — headed browser scrape (headless blocked)
- `daily_asx_all_announcements_action.py` — market-wide daily ingest
- `ingest_transcript.py` — commentary ingest into Qdrant
- `recover_marketindex_headed.py` — recover blocked MarketIndex PDFs

All production JSON reports include `run_metadata` (script, python version, git branch/commit/dirty).
