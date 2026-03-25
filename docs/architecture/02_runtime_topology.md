# Runtime topology

Production runtime layout: Docker services for core stack plus a native llama.cpp service and local CPU embeddings. Cockpit is a **client**; the **backend** is the source of truth for retrieval.

---

## Docker services

| Service   | Role                                      | Port |
|----------|--------------------------------------------|------|
| backend  | API, embeddings, RAG retrieval, orchestration | 8000 |
| worker   | Celery tasks (ingestion, backfill, pipelines) | —    |
| postgres | Primary relational store                   | 5432 |
| redis    | Celery broker and cache                    | 6379 |
| qdrant   | Vector store for RAG                        | 6333 |

When OpenBB sidecar is used: **8081** (OpenBB sidecar HTTP API).

---

## Native services (host)

- **llama.cpp** — OpenAI-compatible LLM server, not in Docker. Default port **8001**. Backend and worker call it over the host network through `llamacpp_bridge`.
  - **Router mode** (default since 2026-03-25): launched with `--models-dir` + `--models-max 1` for zero-downtime model switching via `POST /models/load` API. Per-model config (pooling, embeddings) via `--models-preset` INI file at `~/.config/tenn/llamacpp-presets.ini`. Models are auto-evicted (LRU) when a new model is loaded, keeping VRAM usage bounded.
  - **Single-model mode** (legacy): launched with `-m <model.gguf>`. Model switching requires killing and restarting the server process.
  - Mode controlled by `LLAMA_SERVER_ROUTER_MODE=1` in `~/.config/tenn/llama-server.env`.
- **Sentence Transformers** — local CPU embedding runtime loaded in-process by the backend/worker; no separate container.

---

## Ports summary

**Canonical assignment** — these are fixed. Any code defaulting to a different port is a bug.
The corresponding env vars and their defaults are defined in `financial-engine_v2/.env.example`.

| Port  | Service          | Env var                    | Notes                    |
|-------|------------------|----------------------------|--------------------------|
| 8000  | backend          | `PORT`                     | FastAPI/uvicorn          |
| 8001  | llama.cpp (host) | `LLAMACPP_URL`             | LLM inference            |
| 5432  | postgres         | `DATABASE_URL`             | Primary DB               |
| 6379  | redis            | `REDIS_URL`                | Broker/cache             |
| 6333  | qdrant           | `QDRANT_URL`               | Vector store             |
| 11434 | ollama           | `OLLAMA_URL`               | Embeddings               |
| 8081  | OpenBB sidecar   | `OPENBB_SIDECAR_BASE_URL`  | Optional; market data    |

---

## Volumes

- **fe_qdrant** — Compose volume key for Qdrant persistence (`/qdrant/storage` in container). Actual Docker volume names may be Compose-project-prefixed (for example `financial-engine_v2_fe_qdrant`). Contains vector indexes; **must be backed up** for RAG recovery.
- **fe_pgdata** — Compose volume key for Postgres data (`/var/lib/postgresql/data`). Actual Docker volume names may be Compose-project-prefixed (for example `financial-engine_v2_fe_pgdata`). **Must be backed up** for database recovery.

Backup and restore procedures are described in [11_rebuild_and_recovery.md](11_rebuild_and_recovery.md).

---

## Operational considerations

### Docker root (NVMe relocation)

If Docker’s data root is moved (e.g. to NVMe for better I/O), all named volumes (including `fe_pgdata` and `fe_qdrant`) live under that root. After relocating:

- Ensure the new root has sufficient space and durable storage.
- Plan for downtime or use Docker’s own migration steps for the data root.
- Re-verify volume paths and backup/restore scripts against the new root.

This is an operational consideration only; no application config changes are required for a standard Docker root move.

---

## Client vs source of truth

- **Cockpit** is a **client**: it calls the backend API for chat, search, and retrieval. It does not talk to Qdrant or the vector store directly.
- **Backend** is the **source of truth for retrieval**: all RAG and vector search goes through the backend; the backend owns the contract with Qdrant and local CPU embeddings.
