# Current System

Documentation status: runtime snapshot/reference. For agent navigation and the
current active/archive docs map, start with `docs/README.md`. Runtime claims in
this file, especially host paths, services, models, ports, and validation state,
must be reverified in the current turn before being treated as current evidence.

The active system is `financial-engine_v2`.

## Quick Start (after `git pull`)
1. Create/activate your main venv at repo root.
2. Install dependencies:
   - `pip install -r financial-engine_v2/backend/requirements.txt`
   - `pip install -r financial-engine_v2/worker/requirements.txt`
   - `python -m playwright install chromium`
3. Run:
   - `bash financial-engine_v2/scripts/run_local_backend.sh`

This is the canonical backend bootstrap path. `python run.py` is still a supported batch/orchestration command, but it is not the canonical backend startup path for agents.

## PDF Extraction Learning Loop

The extraction pipeline (`services/extraction/`) has an adaptive learning loop that improves routing over time. Two paths: fast (deterministic preference updates from metrics) and slow (LLM review every N runs). Enable via `learning_loop.enabled = True` in pipeline orchestrator config.

## OpenCode Shared-Server Mode

When running multiple OpenCode sessions (e.g., via agent-orchestrator), use shared-server mode to avoid ~2 GB RAM per session. Start the server once, attach clients to it:

```bash
scripts/opencode-server start           # starts server on port 4096
export OPENCODE_SERVER_URL=http://localhost:4096  # orchestrator uses attach mode
scripts/opencode-server attach          # interactive TUI client
```

The agent-orchestrator's OpenCode adapter auto-detects `OPENCODE_SERVER_URL` and uses `opencode attach` instead of `opencode run`. See `agent-orchestrator/README.md` for details.

## Local Backend API Status
Documented local backend workflow lives under `financial-engine_v2/`.

The 2026-06-23 docs audit did not prove backend runtime functionality. Treat
the profile details below as configured/documented state until a runtime task
revalidates endpoints and backing stores.

Profiles:
- `LOCAL_BACKEND_PROFILE=isolated`
  - local API smoke mode
  - embeddings/Qdrant/extraction disabled
  - `/chat` degrades safely instead of returning `500`
- `LOCAL_BACKEND_PROFILE=full`
  - configured/documented for:
    - runtime DB/data roots (2026-06-23 launcher/verifier evidence points at `/mnt/tenn-nvme2/tenn/financial-engine_v2/data`; isolated validation can still fall back to `/tmp/financial-engine_v2-fe_local_runtime.db`)
    - local Qdrant on `127.0.0.1:6333`
    - local llama.cpp on `127.0.0.1:8001/v1`
  - `/chat` returns grounded answers when `commentary_chunks` has data

Operational notes:
- `/chat` uses `commentary_chunks` with optional `commentary_chunks_v2` fallback support
- `asx_docs` is not the commentary chat collection
- local launcher precedence is `.env` then `.env.local`, with explicit shell env overriding both
- 2026-06-23 checked launcher/verifier evidence points runtime data at `/mnt/tenn-nvme2/tenn/financial-engine_v2/data` and llama.cpp GGUFs at `/mnt/tenn-nvme2/tenn/models`; reverify before runtime work
- llama.cpp launcher defaults no longer force quantized KV cache; on Tesla M40, enable `LLAMA_SERVER_CACHE_TYPE_K` / `LLAMA_SERVER_CACHE_TYPE_V` only after verifying the target model can load without Flash Attention errors
- root Ollama store has been pruned to `qwen2.5:32b` and `gpt-oss:20b-cloud`, with inactive models archived under `.archives/ollama-root-store-2026-04-07`

Canonical local launcher:
- `financial-engine_v2/scripts/run_local_backend.sh`

Canonical detailed runtime notes:
- `financial-engine_v2/README.md`

## What `python run.py` does
- Delegates to `financial-engine_v2/run.py`
- Runs the configured workflows (`both`, `full_history`, `daily_marketindex`, or `daily_asx_marketwide`) from one command.
- Use it for batch workflows, not as the primary "system is running" bootstrap command.

Canonical setup references:
- `docs/setup/environment.md`
- `docs/setup/runtime.md`
- `docs/setup/troubleshooting.md`
- `docs/entrypoints.md`

## Repo Scope
`financial-engine_v2/` is the active engine.
Root `scripts/` still contains auxiliary pipelines, tests, and utilities, but legacy root launcher scripts were archived under:
- `scripts/archive/legacy_root_20260218/`
