# Runtime Topology

## Canonical ports

| Port | Service | Purpose |
| --- | --- | --- |
| `8000` | backend | API and orchestration |
| `8001` | primary LLM | OpenAI-compatible endpoint used by routed LLM calls |
| `8080` | llama.cpp | Direct llama.cpp runtime |
| `6333` | qdrant | Vector store |
| `6379` | redis | Celery broker/result backend |
| `11434` | ollama | Legacy compatibility runtime when explicitly enabled |

## Start order

1. Start Qdrant on `6333`.
2. Start Redis on `6379` if you run Celery mode.
3. Start the direct llama.cpp server on `8080`.
4. Start the primary LLM endpoint on `8001` if you use a proxy/router in front of llama.cpp.
5. Start Ollama on `11434` only if you still run an explicit compatibility path that has not been migrated.
6. Start the backend on `8000`.

## Start commands

Backend:

```bash
python financial-engine_v2/run.py
```

Local isolated backend:

```bash
cd financial-engine_v2
./scripts/run_local_backend.sh
```

Direct llama.cpp launcher from this repo:

```bash
LLAMA_SERVER_PORT=8080 bash scripts/run_llama_server.sh
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
