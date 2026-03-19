# Financial Engine V2 orchestration scripts

These scripts provide deterministic local startup and cleanup for the backend and worker services.

## What each script does

- `scripts/run_backend.sh`
  - Loads `config/system.env`
  - Activates the project `.venv`
  - Exports `PYTHONPATH=backend` and `DATA_ROOT` defaults
  - Kills existing project uvicorn processes before startup
  - Starts the backend on `127.0.0.1:8000` with uvicorn
- `scripts/run_worker.sh`
  - Loads `config/system.env`
  - Activates the project `.venv`
  - Exports `PYTHONPATH=backend` and `DATA_ROOT` defaults
  - Starts the celery worker from `app.celery_app.celery`
- `scripts/reset_env.sh`
  - Kills project-scoped `uvicorn` and `celery` processes
  - Cleans temporary `/tmp` artifacts matching `financial-engine_v2`

### Archive

Current script snapshots are stored under `scripts/archive/`.

## Exact commands to run the system

1. Reset environment:
   - `./scripts/reset_env.sh`
2. Start backend:
   - `./scripts/run_backend.sh`
3. Start worker (in a separate terminal):
   - `./scripts/run_worker.sh`

## Rules

DO NOT start services manually — always use scripts
