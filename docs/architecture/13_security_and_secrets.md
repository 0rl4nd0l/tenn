# Security and secrets

This document records the current secret-bearing configuration surfaces and the minimum handling rules verified in this repo. It does not introduce new security features; it describes how the existing runtime is wired.

## Secret-bearing files and config surfaces

| Surface | Purpose | Handling rule |
|---------|---------|---------------|
| `financial-engine_v2/.env` | Backend, worker, database, Qdrant, Ollama, and sidecar settings loaded by Pydantic and Compose | Keep local only; do not commit real credentials |
| `~/.openclaw/openclaw.json` | OpenClaw models, gateway auth token, workspace/runtime defaults | Treat as host-local secret config; do not mirror secrets into repo docs |
| `~/.config/tenn/llama-server.env` | Host override file for llama.cpp port, host, model path, mmap/profile overrides | Host-local only; use for live overrides instead of editing committed launcher defaults |
| `integrations/newspaper4k_au/secrets/` | Optional local cookie/header material for gated scraping flows | Keep outside versioned docs and source control |

## Current secret-loading paths

- Backend settings are loaded from `financial-engine_v2/.env` via `financial-engine_v2/backend/app/core/config.py`.
- Docker services consume the same `.env` through `financial-engine_v2/docker-compose.yml`.
- OpenClaw runtime settings are read from `~/.openclaw/openclaw.json`.
- The local llama.cpp service can be overridden through `~/.config/tenn/llama-server.env`.

## Operational rules

- Prefer environment variables or host-local config files over hard-coded secrets.
- Keep documentation examples sanitized; never paste live gateway tokens, API keys, cookies, or database passwords into markdown.
- When OpenAI planner auth is needed for OpenClaw, bootstrap it from 1Password via `scripts/openclaw_sync_openai_auth_from_1password.py` rather than storing the secret in repo files.
- Treat generated reports and manifests as potentially sensitive if they include local paths, source URLs, or operational metadata.

## Network and service boundaries

- The backend exposes the financial API on port `8000` in Compose.
- Qdrant, Redis, and Postgres stay behind the local Docker/network boundary unless explicitly published.
- The local llama.cpp endpoint is host-local and may differ between the checked-in launcher default and the live host override; verify against `~/.openclaw/openclaw.json` and `~/.config/tenn/llama-server.env` before documenting a live port.

## Related docs

- `02_runtime_topology.md`
- `10_failure_model.md`
- `docs/ops/openclaw_ops_loop.md`
