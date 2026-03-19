# Current System

The active system is `financial-engine_v2`.

## Quick Start (after `git pull`)
1. Create/activate your main venv at repo root.
2. Install dependencies:
   - `pip install -r requirements.txt`
   - `python -m playwright install chromium`
3. Run:
   - `python run.py`

## Local Backend API Status
Verified current local backend workflow lives under `financial-engine_v2/`.

Profiles:
- `LOCAL_BACKEND_PROFILE=isolated`
  - local API smoke mode
  - embeddings/Qdrant/extraction disabled
  - `/chat` degrades safely instead of returning `500`
- `LOCAL_BACKEND_PROFILE=full`
  - verified working with:
    - local SQLite in `/tmp`
    - local Qdrant on `127.0.0.1:6333`
    - local llama.cpp on `127.0.0.1:8001/v1`
  - `/chat` returns grounded answers when `commentary_chunks` has data

Operational notes:
- `/chat` uses `commentary_chunks` with optional `commentary_chunks_v2` fallback support
- `asx_docs` is not the commentary chat collection
- local launcher precedence is `.env` then `.env.local`, with explicit shell env overriding both
- local launcher forces `DATA_ROOT` to the repo `data/` path unless `DATA_ROOT` is explicitly set

Canonical local launcher:
- `financial-engine_v2/scripts/run_local_backend.sh`

Canonical detailed runtime notes:
- `financial-engine_v2/README.md`

## What `python run.py` does
- Delegates to `financial-engine_v2/run.py`
- Runs the configured workflows (`both`, `full_history`, `daily_marketindex`, or `daily_asx_marketwide`) from one command.

Canonical setup references:
- `docs/setup/environment.md`
- `docs/setup/runtime.md`
- `docs/setup/troubleshooting.md`

## Repo Scope
`financial-engine_v2/` is the active engine.
Root `scripts/` still contains auxiliary pipelines, tests, and utilities, but legacy root launcher scripts were archived under:
- `scripts/archive/legacy_root_20260218/`
