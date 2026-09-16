# Current System

The active system is `financial-engine_v2`.

Canonical agent entrypoints, wrappers, and public API: `docs/entrypoints.md`.

## Quick Start (after `git pull`)

Agent / API bootstrap (canonical):

1. Create/activate your main venv at repo root (`/workspace/.venv` in Cloud Agent environments).
2. Install dependencies:
   - `pip install -r requirements.txt`
   - `pip install -r financial-engine_v2/backend/requirements.txt`
   - `python -m playwright install chromium` (needed for MarketIndex PDF downloads)
3. Start the backend:
   - `bash financial-engine_v2/scripts/run_local_backend.sh`
   - or `bash scripts/start_system.sh` if you want the wrapper to start-and-healthcheck
4. Validate:
   - `bash financial-engine_v2/scripts/smoke_local.sh`

Batch ingestion (not system bootstrap):

- `python run.py` delegates to `financial-engine_v2/run.py` and runs configured workflows
  (full history and/or daily MarketIndex). It does **not** define “system is running”.

## What the canonical backend provides
- FastAPI app from `financial-engine_v2/backend/app/main.py`, mounted at `/api`.
- Isolated local defaults: SQLite, `TASK_MODE=sync`, embeddings/extraction/Qdrant off.
- Health is `GET /api/health`. Swagger UI is `GET /docs`; ticker document listing is `GET /api/docs`.

## Legacy scripts
Old root scripts are archived under:
- `scripts/archive/legacy_root_20260218/`
