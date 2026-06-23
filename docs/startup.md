## Startup (Full Stack)

Documentation status: full-stack Docker/user-launcher runbook. This file does
not override `docs/entrypoints.md`, which remains the runtime entrypoint context
for agent tasks. During the 2026-06-23 docs audit, `README.md` and
`docs/entrypoints.md` identified `financial-engine_v2/scripts/run_local_backend.sh`
as the canonical agent backend bootstrap path; the Docker-only statement below
applies to this full-stack mode unless fresh runtime evidence says otherwise.

This repo’s **full system mode** is Docker Compose. The backend must run **only in Docker**.

### CLI usage

Install (one-time, optional):

```bash
mkdir -p ~/.local/bin
ln -sf /home/l4nd0/tenn/scripts/cockpit ~/.local/bin/cockpit
```

Commands:

```bash
cockpit start new # main user entrypoint: full system + Next.js Cockpit UI on http://127.0.0.1:8081
cockpit start     # full system (docker compose) + launch Cockpit TUI
cockpit stop      # stop containers
cockpit status    # show services
cockpit logs      # stream logs
cockpit doctor    # diagnose system
```

Recommended user entrypoint:
- `cockpit start new`
- Served on `http://127.0.0.1:8081`
- Starts the full stack, then launches the browser UI

### Configuration

Edit:
- `scripts/start_config.env`

Key values:
- `ENGINE_ROOT`: path to `financial-engine_v2/`
- `COMPOSE_FILE`: path to `financial-engine_v2/docker-compose.yml`
- `COMPOSE_ENV_FILE`: env file used by compose and backend container startup (default `.env.docker` under `ENGINE_ROOT`)
- `BACKEND_HEALTH_URL`: host health endpoint (default `http://127.0.0.1:8000/api/health`)
- `OLLAMA_URL_HOST`: host Ollama endpoint used by diagnostics (default `http://127.0.0.1:11434`)
- `OLLAMA_URL_CONTAINER`: Ollama URL written into `.env.docker` for backend/worker startup (default `http://127.0.0.1:11434` because compose uses host networking)
- `EMBED_MODEL_ON_STARTUP`: embedding model written into `.env.docker` before backend restart (default `nomic-embed-text`)
- `BACKEND_START_TIMEOUT`: backend readiness timeout for startup
- `TERMINAL_MODE`: how `cockpit start` launches the TUI (`auto | gnome-terminal | tmux`)
- `COCKPIT_NEW_PORT`: host port for `cockpit start new` (default `8081`)
- `ENABLE_EMBEDDINGS_ON_STARTUP`: forces backend `ENABLE_EMBEDDINGS` (default `false` in this environment)
- `ENABLE_QDRANT_ON_STARTUP`: forces backend `ENABLE_QDRANT` (default `false` in this environment)
- `LLAMA_SERVER_CACHE_TYPE_K` / `LLAMA_SERVER_CACHE_TYPE_V`: optional host overrides for llama.cpp KV-cache types; leave unset on Tesla M40 unless validated for the selected model/runtime

Docker vs host routing:
- **Host tools** (doctor, host-run cockpit launcher) should use `127.0.0.1` / `localhost`.
- **Backend/worker containers** run with host networking in this stack, so `127.0.0.1` is the correct host-service URL for Ollama from those services.

Docker packaging notes:
- The backend and worker images build from the `financial-engine_v2/` repo root so Docker can include both `backend/` and the shared Python package at `shared/`.
- Compose still bind-mounts both `backend/` and `shared/` for local live-code iteration; the image itself remains bootable without those dev mounts.

### Deterministic runtime

The CLI uses explicit interpreter selection:
- Prefer `financial-engine_v2/.venv/bin/python` when present
- Otherwise fall back to `python3`

No venv activation is used.

### RAG / Embeddings Behavior

By default, the system starts in full-functionality mode:

```bash
ENABLE_EMBEDDINGS_ON_STARTUP=true
ENABLE_QDRANT_ON_STARTUP=true
ENABLE_EXTRACTION_ON_STARTUP=true
EMBED_MODEL_ON_STARTUP=nomic-embed-text
```

`cockpit restart backend` now reapplies these defaults into `.env.docker`, ensures the Ollama embedding model is present when embeddings are enabled, recreates the compose backend/worker services, and then starts the local llama.cpp runtimes used by cockpit.

### Doctor

Run:

```bash
cockpit doctor
```

Checks:
- Docker installed + daemon reachable
- Compose container status (`docker compose ps`)
- Backend health (`/api/health`)
- Ollama reachability on host (`OLLAMA_URL_HOST`)
- Python interpreter availability (`financial-engine_v2/.venv/bin/python` vs `python3`)
- Port conflicts (8000/5432/6379/6333/11434)
- URL sanity: warns if compose `.env` uses `localhost` for container-to-host calls

Common fixes:
- Docker missing/daemon unreachable: install Docker + ensure service running + user permissions.
- Backend unhealthy: `cockpit logs` and check `backend` service logs.
- Ollama unreachable: start Ollama on host, or update `OLLAMA_URL_HOST` / `.env` routing. `cockpit restart backend` pulls `EMBED_MODEL_ON_STARTUP` if Ollama is reachable and embeddings are enabled.
- Port conflicts: stop conflicting process or run fewer local services.
