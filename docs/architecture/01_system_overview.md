# System overview

This repository currently documents two active runtime surfaces:

1. `financial-engine_v2` for financial document ingestion, retrieval, extraction, and operator workflows.
2. Tenn/OpenClaw local operations tooling for coding and maintenance workflows.

The source-of-truth application runtime is the financial engine. OpenClaw usage in this repo is operational orchestration for local agent sessions and llama.cpp service management; the current repo docs do not define a robotics actuator-control runtime.

## Financial engine components

| Component | Role | Evidence |
|-----------|------|----------|
| FastAPI backend | API surface, sync pipeline execution, RAG query endpoint, startup validation | `financial-engine_v2/backend/app/main.py`, `financial-engine_v2/backend/app/api/routes.py` |
| Celery worker | Async task entrypoints delegating to backend pipeline and routed LLM code; current source-of-truth Celery surface lives in the backend app | `financial-engine_v2/backend/app/celery_app.py`, `financial-engine_v2/backend/app/worker_tasks.py`, `docs/architecture/09_worker_and_celery_contract.md` |
| Model router | Metadata-aware, finance-aware request classification plus self-optimizing routing across configured router/coding/reasoning/deep_reasoning roles from `model_routing.yaml`; the checked-in local profile currently uses `llama3.1:8b` for generation and `nomic-embed-text` for embeddings | `financial-engine_v2/backend/app/services/router.py`, `docs/architecture/model-routing.md` |
| Postgres | Structured persistence for documents, extractions, financial rows, snapshots | `financial-engine_v2/backend/app/models/`, `financial-engine_v2/docker-compose.yml` |
| Qdrant | Runtime vector store for backend RAG | `financial-engine_v2/backend/app/services/rag.py`, `docs/architecture/06_embeddings_and_vector_store.md` |
| Ollama | Embedding and optional generation backend for runtime financial workflows | `financial-engine_v2/backend/app/core/config.py`, `docs/architecture/06_embeddings_and_vector_store.md` |
| OpenBB sidecar | Optional market-data sidecar for profile, summary, and statements endpoints | `financial-engine_v2/openbb_sidecar/README.md`, `financial-engine_v2/docker-compose.yml` |
| Cockpit | Operator client layered on top of backend APIs and local context artifacts | `financial-engine_v2/cockpit/`, `financial-engine_v2/config/cockpit.yaml` |

## Financial engine flow

1. Discover announcement metadata from ASX and optional fallback providers.
2. Persist deduplicated document rows in Postgres.
3. Download PDFs to `docs_root`.
4. Extract text and chunk per document.
5. Route embedding and generation requests through the backend self-optimizing model router.
6. Embed chunks via the routed embedding role and upsert deterministic vector IDs into Qdrant.
7. Optionally extract structured financial and risk rows back into Postgres through the routed reasoning or deep-reasoning role.
8. Serve retrieval through `POST /rag/query` and operational APIs under `/api/*`.

See:

- `04_ingestion_pipeline.md`
- `06_embeddings_and_vector_store.md`
- `07_rag_contract.md`
- `09_worker_and_celery_contract.md`
- `model-routing.md`

## Self-optimizing routing

The backend router keeps the existing `llm_cpu`, `llm_gpu`, and `embed` queue split, but it now combines:

- semantic complexity detection
- rolling per-model performance summaries
- rolling per finance-task performance summaries
- explicit finance task detection for earnings, guidance, capital allocation, balance-sheet risk, valuation, peer comparison, filing summary, catalyst detection, and RAG synthesis
- adaptive model scoring
- overload and timeout fallbacks

The active score weights are `latency=0.4`, `throughput=0.3`, `error=0.2`, `queue=0.1`, and `gpu=0.1`.

## OpenClaw/Tenn ops surface

The repo also carries local operations documentation for OpenClaw session orchestration and llama.cpp host management:

- OpenClaw config source of truth: `~/.openclaw/openclaw.json`
- llama.cpp launcher: `scripts/run_llama_server.sh`
- local ops loop: `docs/ops/openclaw_ops_loop.md`

These docs govern local agent/runtime operations. They are separate from the financial-engine backend data path above.
