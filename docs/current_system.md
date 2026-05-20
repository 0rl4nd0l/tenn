# Current System

The active system is `financial-engine_v2`.

## Quick Start (after `git pull`)
1. Create/activate the shared venv at repo root and ensure
   `financial-engine_v2/.venv` exists or symlinks to it.
2. Install dependencies:
   - `pip install -r requirements.txt`
   - `pip install -r financial-engine_v2/backend/requirements.txt`
   - `python -m playwright install chromium` (needed for MarketIndex PDF downloads)
3. Run and validate the canonical backend:
   - `bash financial-engine_v2/scripts/run_local_backend.sh`
   - `bash financial-engine_v2/scripts/smoke_local.sh`

## Runtime model
- `financial-engine_v2/scripts/run_local_backend.sh` starts the FastAPI backend
  in isolated local mode.
- The system is considered running when `GET /api/health` responds.
- Local isolated mode uses SQLite, sync tasks, and disables embeddings,
  extraction, and Qdrant by default.

## What `python run.py` does
- Delegates to `financial-engine_v2/run.py`
- Runs configured batch workflows, such as full-history ingestion and daily
  MarketIndex collection.
- Does not start the canonical backend API and should not be used as the default
  agent startup path.

## Legacy scripts
Old root scripts are archived under:
- `scripts/archive/legacy_root_20260218/`
