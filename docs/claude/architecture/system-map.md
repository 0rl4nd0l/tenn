# System Map

## Source Trace
- `docs/architecture/01_system_overview.md` (Confirmed)
- `docs/architecture/02_runtime_topology.md` (Confirmed — referenced)
- `docs/architecture/09_worker_and_celery_contract.md` (Confirmed — referenced)
- `financial-engine_v2/docker-compose.yml` (Confirmed — referenced)
- `docs/setup/runtime.md` (Confirmed)

---

## Component Map

```
┌─────────────────────────────────────────────────────────────────┐
│  HOST SERVICES (not in Docker)                                  │
│                                                                 │
│  ┌──────────────────┐    ┌──────────────────┐                  │
│  │  llama.cpp       │    │  Ollama          │                  │
│  │  :8001           │    │  :11434          │                  │
│  └──────────────────┘    └──────────────────┘                  │
│          ↑                        ↑                             │
│          │ (LLM_URL / LLAMACPP_URL)│ (OLLAMA_URL)              │
└──────────┼────────────────────────┼─────────────────────────── ┘
           │                        │
┌──────────┼────────────────────────┼─────────────────────────── ┐
│  DOCKER SERVICES                  │                             │
│                                   │                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI Backend  :8000                                  │  │
│  │  ─────────────────────────────────────────────────────   │  │
│  │  • API routes (/api/*, /rag/query, /chat)                │  │
│  │  • Model router (self-optimizing, finance-aware)         │  │
│  │  • Sync pipeline execution                               │  │
│  │  • RAG service                                           │  │
│  │  • Startup validation                                    │  │
│  └───────────────┬──────────────────────┬───────────────────┘  │
│                  │                      │                       │
│  ┌───────────────▼──┐    ┌─────────────▼────────────────────┐  │
│  │  Celery Worker   │    │  Qdrant  :6333                   │  │
│  │  (async tasks)   │    │  (vector store; RAG retrieval)   │  │
│  └──────────────────┘    └──────────────────────────────────┘  │
│           │                                                      │
│  ┌────────▼──────────┐   ┌──────────────────────────────────┐  │
│  │  Redis  :6379     │   │  Postgres  :5432                 │  │
│  │  (Celery broker)  │   │  (documents, extractions,        │  │
│  │  (result backend) │   │   financials, snapshots)         │  │
│  └───────────────────┘   └──────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  OpenBB Sidecar (optional)                               │  │
│  │  market data: profile, summary, statements               │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────── ┘

OPERATOR LAYER (not part of data path)
  Cockpit TUI → calls Backend API + reads local artifacts
```

---

## Responsibilities by Component

| Component | Owns | Does NOT own |
|-----------|------|-------------|
| FastAPI backend | API contract, model routing, sync pipeline, RAG query | Async task execution (→ Celery) |
| Celery worker | Async task queue execution | Route classification, API surface |
| Model router | Request classification, adaptive scoring, finance-task detection | Model weights, inference |
| Qdrant | Vector storage, similarity retrieval | Chunking, embedding generation |
| Postgres | Structured persistence | Vector similarity, document text |
| Ollama | Embedding generation, optional LLM generation | Financial logic, routing |
| llama.cpp | Local LLM inference (preferred for coding/agent) | Financial pipeline |
| OpenBB sidecar | Market data endpoints | Any financial-engine data path |

---

## Key Code Locations

| Component | Key Files |
|-----------|-----------|
| FastAPI entry | `financial-engine_v2/backend/app/main.py` |
| API routes | `financial-engine_v2/backend/app/api/routes.py` |
| Model router | `financial-engine_v2/backend/app/services/router.py` |
| RAG service | `financial-engine_v2/backend/app/services/rag.py` |
| Celery config | `financial-engine_v2/backend/app/celery_app.py` |
| Worker tasks | `financial-engine_v2/backend/app/worker_tasks.py` |
| Pydantic config | `financial-engine_v2/backend/app/core/config.py` |
| ORM models | `financial-engine_v2/backend/app/models/` |
| Model routing YAML | `financial-engine_v2/backend/app/config/` (Inferred) |
| Canonical boot | `financial-engine_v2/scripts/run_local_backend.sh` |

---

## Runtime Modes

| Mode | Services Running | Use Case |
|------|-----------------|----------|
| Isolated (default) | Backend only | Agent smoke testing, API development |
| Full local | Backend + Qdrant + llama.cpp (host) | End-to-end RAG testing |
| Full Docker | All Docker services + host Ollama/llama.cpp | Production-equivalent validation |

---

## Ownership

- **Platform/Ops:** GPU + host runtime (NVML, Ollama, llama.cpp)
- **ML Infra:** Model policy, Ollama behavior, embedding configuration
- **Backend:** FastAPI API, model router, RAG service
- **Data Pipeline:** Ingestion, chunking, Qdrant upsert
- **Cockpit operators:** Operator-layer tooling only
