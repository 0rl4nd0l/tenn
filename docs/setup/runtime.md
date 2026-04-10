# Runtime Topology

## Canonical ports

| Port | Service | Purpose |
| --- | --- | --- |
| `8000` | backend | API and orchestration |
| `8001` | llama.cpp | OpenAI-compatible endpoint (canonical LLM port) |
| `8081` | OpenBB sidecar (optional) | Market data sidecar endpoint |
| `8081` (launcher default) | Cockpit web UI | Browser-served Textual UI when `cockpit start web/new` is used |
| `6333` | qdrant | Vector store |
| `6379` | redis | Celery broker/result backend |
| `11434` | ollama | Legacy compatibility runtime when explicitly enabled |

Note: `8081` is shared by two optional surfaces in local workflows. If you need
both local OpenBB sidecar and Cockpit web UI at the same time, move one of them
to a different host port (for Cockpit launcher flows, override `COCKPIT_WEB_PORT`
and/or `COCKPIT_NEW_PORT`).

## Start order

1. Start Qdrant on `6333`.
2. Start Redis on `6379` if you run Celery mode.
3. Start llama-server on `8001` (set `LLAMA_SERVER_PORT=8001`).
4. Start Ollama on `11434` only if you still run an explicit compatibility path that has not been migrated.
5. Start the backend on `8000`.

## Start commands

Primary user entrypoint:

```bash
cockpit start new
```

This launches the Cockpit browser UI on `http://127.0.0.1:8081` after starting the required local services.

Canonical backend start:

```bash
bash financial-engine_v2/scripts/run_local_backend.sh
```

The backend launcher above remains the canonical agent/bootstrap entrypoint. For humans using the local product, prefer `cockpit start new`.

Batch/orchestration path:

```bash
python run.py
```

Use `python run.py` for batch workflows and orchestrated runs. Do not use it as the canonical "backend is running" bootstrap path for agents.

Direct llama.cpp launcher from this repo:

```bash
bash scripts/run_llama_server.sh
```

Environment validation:

```bash
python scripts/check_environment.py
```

## Path policy

- Never hardcode `/data`.
- `DATA_ROOT` is the root for runtime files.
- Backend code derives report/doc paths from `settings.data_root`.
- Host and Docker both work by changing env values, not code paths.
