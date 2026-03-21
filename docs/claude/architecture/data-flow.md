# Data Flow

## Source Trace
- `docs/architecture/01_system_overview.md` (Confirmed)
- `docs/architecture/04_ingestion_pipeline.md` (Confirmed — referenced)
- `docs/architecture/05_pdf_extraction_and_chunking.md` (Confirmed — referenced)
- `docs/architecture/06_embeddings_and_vector_store.md` (Confirmed — referenced)
- `docs/architecture/07_rag_contract.md` (Confirmed — referenced)
- `docs/architecture/09_worker_and_celery_contract.md` (Confirmed — referenced)

---

## Ingestion Pipeline

```
ASX / Fallback providers
        │
        ▼ (1) Discover announcement metadata
  ┌─────────────┐
  │  Discovery  │
  └──────┬──────┘
         │
         ▼ (2) Persist deduplicated document rows
  ┌─────────────┐
  │  Postgres   │  (documents table)
  └──────┬──────┘
         │
         ▼ (3) Download PDFs → docs_root (DATA_ROOT/docs)
  ┌─────────────┐
  │  PDF Store  │  (filesystem, under DATA_ROOT)
  └──────┬──────┘
         │
         ▼ (4) Extract text (PyMuPDF primary; Docling/Tesseract for complex PDFs)
  ┌─────────────────────────┐
  │  Text Extraction        │
  │  - PyMuPDF              │
  │  - Docling (GPU-accel)  │
  │  - Tesseract (OCR)      │
  └──────────┬──────────────┘
             │
             ▼ (5) Chunk extracted text
  ┌─────────────┐
  │  Chunker    │
  └──────┬──────┘
         │
         ▼ (6) Route embedding request through model router
  ┌───────────────────┐
  │  Model Router     │  (embed role → Ollama / sentence-transformers)
  └────────┬──────────┘
           │
           ▼ (7) Embed chunks → upsert to Qdrant (deterministic vector IDs)
  ┌─────────────┐
  │  Qdrant     │  (commentary_chunks collection)
  └──────┬──────┘
         │
         ▼ (8, optional) Route extraction request → reasoning/deep_reasoning role
  ┌───────────────────────────────────┐
  │  Structured Extraction            │
  │  (financial rows, risk notes)     │
  └────────────────────┬──────────────┘
                       │
                       ▼ Persist extracted financials
                ┌─────────────┐
                │  Postgres   │  (financials, risk_notes tables)
                └─────────────┘
```

---

## RAG Query Flow

```
Client (POST /rag/query or /chat)
        │
        ▼
  ┌─────────────────┐
  │  FastAPI        │
  │  /rag/query     │
  └────────┬────────┘
           │
           ▼ Embed query (model router → embed role)
  ┌─────────────────┐
  │  Qdrant search  │  (commentary_chunks; optional commentary_chunks_v2 fallback)
  └────────┬────────┘
           │
           ▼ Retrieved chunks (grounding context)
  ┌─────────────────────────────────────┐
  │  LLM synthesis                      │
  │  (model router → router/reasoning   │
  │   role; llama.cpp or Ollama)        │
  └──────────────────┬──────────────────┘
                     │
                     ▼
              Grounded response
```

---

## Async Task Flow (Celery)

```
API trigger (POST /api/*)
        │
        ▼
  Celery task enqueued → Redis broker
        │
        ▼
  Worker picks up task
        │
        ▼
  Delegates to backend pipeline
  (same extraction / embedding logic as sync path)
        │
        ▼
  Result stored → Redis result backend
        │
        ▼
  API polls or client subscribes
```

---

## Model Router Decision Flow

```
Incoming request
        │
        ▼ Classify: semantic complexity + finance task detection
  ┌─────────────────────────────────────────┐
  │  Finance tasks detected:                │
  │  earnings, guidance, capital, balance,  │
  │  valuation, peer, filing, catalyst, RAG │
  └────────────┬────────────────────────────┘
               │
               ▼ Select model role (router/coding/reasoning/deep_reasoning/embed)
               │
               ▼ Adaptive scoring:
               │  latency×0.4 + throughput×0.3 + error×0.2 + queue×0.1 + gpu×0.1
               │
               ▼ Route to best available model endpoint
               │
               ▼ On overload or timeout → fallback
```

---

## Data Stores Summary

| Store | Data | Persistence |
|-------|------|-------------|
| Postgres | Documents, extractions, financials, risk notes, snapshots | Durable (Docker volume in Compose) |
| Qdrant | Embedding vectors with metadata | Durable (local volume) |
| Redis | Celery task queue + result cache | Ephemeral (configurable TTL) |
| Filesystem | PDFs under `DATA_ROOT/docs/` | Durable, DATA_ROOT must be writable |
| SQLite | Optional local Postgres substitute in `LOCAL_BACKEND_PROFILE=full` | Written to `/tmp` by local launcher |

---

## Key Invariants

- Vector IDs are **deterministic** — upsert is idempotent; changing ID generation logic breaks deduplication.
- `/chat` reads from `commentary_chunks` (not `asx_docs`).
- `DATA_ROOT` must be set; local launcher defaults to repo `data/`.
- Financial and risk rows written to Postgres must come from actual extraction — never fabricated.
