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
  → text_extract (PyMuPDF) → chunking → embeddings (Qdrant upsert)
  → LLM extraction (Ollama JSON) → Postgres (documents, extraction_runs, asx_periodic_financials)
```

Pipeline tasks can run in two modes set by `TASK_MODE`:
- `sync` — direct call in the API request (used in local mode)
- `celery` — dispatched to a Celery worker via Redis broker (production)

### LLM Backend Endpoints

Three endpoints, two required and one optional (`core/config.py`):

| Endpoint | Purpose | Default |
|----------|---------|---------|
| `LLAMACPP_URL` | Chat, routing, coding | `http://127.0.0.1:8001` |
| `EXTRACTION_LLAMACPP_URL` | PDF extraction (multipass, commentary) | Falls back to `LLAMACPP_URL` |
| `OLLAMA_URL` | Embeddings (`nomic-embed-text`) | `http://127.0.0.1:11434` |

When `EXTRACTION_LLAMACPP_URL` is set, extraction calls route to a dedicated llama.cpp instance. This allows running an instruct model (e.g. `qwen2.5-14b-instruct`) for extraction while keeping a coder model on the chat server. When unset, all LLM calls share `LLAMACPP_URL` (single-server mode).

The app **fails to start** if `LLAMACPP_URL` and `OLLAMA_URL` resolve to the same host:port. This prevents silent backend aliasing.

### Model Routing (`backend/app/services/router.py`)

Requests are classified by heuristic pattern matching into task types (`coding`, `reasoning`, `deep_reasoning`, `router`). Config lives in `backend/app/config/model_routing.yaml`. Routing decisions feed an adaptive optimizer (`router_optimizer.py`) that uses latency/throughput/error/GPU metrics.

### RAG / Retrieval

- ASX document collection: `asx_docs` (Qdrant)
- Commentary collection: `commentary_chunks` (primary), `commentary_chunks_v2` (optional fallback)
- `/chat` uses commentary collections, not `asx_docs`
- Hybrid retrieval: `hybrid_retriever.py` (dense + optional reranking via `reranker.py`)
- Query entrypoint: `POST /api/chat` → `tenn_chat.py` → `retrieval_orchestrator.py`

### Key Services

| File | Role |
|------|------|
| `backend/app/main.py` | FastAPI app, startup validation (Qdrant dimension check, embedding model mismatch guard) |
| `backend/app/core/config.py` | `Settings` (pydantic-settings), URL normalization for sqlite/redis/qdrant, LLM endpoint conflict check |
| `backend/app/services/pipeline.py` | Core ingestion: download → extract → embed → persist |
| `backend/app/services/embeddings.py` | Qdrant upsert, collection management, dimension validation |
| `backend/app/services/llm.py` | `embed_texts`, `generate_json`, `get_routing_decision` — all LLM calls go through here |
| `backend/app/services/extraction.py` | `build_prompt` for financial JSON extraction; clips to first 18,000 chars |
| `backend/app/services/router.py` | Task-type classifier + adaptive model selector |
| `backend/app/api/routes.py` | Backfill, docs, financials, ingest endpoints |
| `backend/app/routes/chat.py` | `/chat` endpoint |

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

---

## Production Scripts

All in `scripts/`. Key ones:

- `full_history_ticker_sync.py` — bulk backfill by ticker(s)
- `daily_marketindex_action.py` — headed browser scrape (headless blocked)
- `daily_asx_all_announcements_action.py` — market-wide daily ingest
- `ingest_transcript.py` — commentary ingest into Qdrant
- `recover_marketindex_headed.py` — recover blocked MarketIndex PDFs

All production JSON reports include `run_metadata` (script, python version, git branch/commit/dirty).
