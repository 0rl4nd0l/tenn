# Current System

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

## Local Backend API Status
Verified current local backend workflow lives under `financial-engine_v2/`.

Profiles:
- `LOCAL_BACKEND_PROFILE=isolated`
  - local API smoke mode
  - embeddings/Qdrant/extraction disabled
  - `/chat` degrades safely instead of returning `500`
- `LOCAL_BACKEND_PROFILE=full`
  - verified working with:
    - configured runtime DB/data roots (host-local `.env.local` may point at `/mnt/nvme/tenn/runtime-data`; isolated validation can still fall back to `/tmp/financial-engine_v2-fe_local_runtime.db`)
    - local Qdrant on `127.0.0.1:6333`
    - local llama.cpp on `127.0.0.1:8001/v1`
  - `/chat` returns grounded answers when `commentary_chunks` has data

Operational notes:
- `/chat` uses `commentary_chunks` with optional `commentary_chunks_v2` fallback support
- `asx_docs` is not the commentary chat collection
- local launcher precedence is `.env` then `.env.local`, with explicit shell env overriding both
- current host-local storage layout uses `/mnt/nvme/tenn/runtime-data` for runtime data and `/mnt/nvme/tenn/models` for llama.cpp GGUFs
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
