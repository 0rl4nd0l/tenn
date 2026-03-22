# Project Overview

## Source Trace
- `docs/architecture/01_system_overview.md` (Confirmed)
- `financial-engine_v2/README.md` (Confirmed)
- `README.md` (Confirmed)
- `agent_contract.json` (Confirmed)

---

## What This Is

**Tenn** is a financial document ingestion, retrieval, and analysis system targeting ASX (Australian Securities Exchange) announcements.

Active runtime: `financial-engine_v2/` — a FastAPI + Celery + Postgres + Qdrant stack with llama.cpp as the primary inference service (Ollama retained only as a legacy compatibility option for backend pipelines that have not migrated).

Secondary surface: OpenClaw/Tenn local ops tooling — orchestration for local agent coding sessions and llama.cpp host management.

There is **no robotics or actuator-control runtime** in this repository.

---

## Components

| Component | Role | Key Files |
|-----------|------|-----------|
| FastAPI backend | API surface, sync pipeline, RAG query, startup validation | `financial-engine_v2/backend/app/main.py` |
| Celery worker | Async task execution; delegates to backend pipeline | `financial-engine_v2/backend/app/celery_app.py`, `worker_tasks.py` |
| Model router | Self-optimizing request classification across router/coding/reasoning/deep_reasoning roles | `financial-engine_v2/backend/app/services/router.py` |
| Postgres | Structured persistence (documents, extractions, financial rows, snapshots) | `financial-engine_v2/backend/app/models/` |
| Qdrant | Vector store for RAG retrieval | `financial-engine_v2/backend/app/services/rag.py` |
| Ollama | Legacy embedding/generation backend kept for compatibility | `financial-engine_v2/backend/app/core/config.py` |
| llama.cpp | Preferred local coding/agent inference endpoint and worker routing target | `scripts/run_llama_server.sh` |
| OpenBB sidecar | Optional market-data sidecar | `financial-engine_v2/openbb_sidecar/` |
| Cockpit | Operator TUI layered on backend APIs | `financial-engine_v2/cockpit/` |

---

## Hardware Context

Host: Tesla M40 (24GB VRAM) + GT1030, Ubuntu.
- GPU-first inference; CPU fallback is supported but not preferred.
- Maxwell-era GPU (M40); Ollama/CUDA requires mitigation (see `docs/ops/02_ollama_m40_validation_and_mitigation.md`).

---

## Canonical Ports

| Port | Service |
|------|---------|
| 8000 | FastAPI backend (API) |
| 8001 | Primary LLM (OpenAI-compatible) |
| 8080 | llama.cpp direct endpoint |
| 6333 | Qdrant vector store |
| 6379 | Redis (Celery broker/result) |
| 11434 | Ollama inference (legacy compatibility only) |
| 5432 | Postgres (Docker mode only) |

---

## Key Env Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATA_ROOT` | `./data` | Root for runtime data, reports |
| `LLM_URL` | `http://127.0.0.1:8001` | Primary OpenAI-compatible endpoint |
| `LLAMACPP_URL` | `http://127.0.0.1:8080` | Direct llama.cpp |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama API |
| `QDRANT_URL` | `http://127.0.0.1:6333` | Vector store |
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Celery broker |

Full env spec: `docs/setup/environment.md`.

---

## Machine-Readable Agent Contract

```json
{
  "canonical_entrypoint": "financial-engine_v2/scripts/run_local_backend.sh",
  "recommended_wrapper": "scripts/start_system.sh",
  "healthcheck": "/api/health",
  "validation": "scripts/validate_system.sh"
}
```

Source: `agent_contract.json`
