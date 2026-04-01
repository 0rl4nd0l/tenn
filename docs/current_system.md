# Current System

The active system is `financial-engine_v2`.

## Canonical backend startup (agents and local API work)
Use this path when you need the FastAPI system to be "up" in a deterministic way.

1. Create the root venv:
   - `python3 -m venv /workspace/.venv`
2. Install dependencies:
   - `/workspace/.venv/bin/pip install -r requirements.txt`
   - `/workspace/.venv/bin/python -m playwright install chromium` (needed for MarketIndex PDF download flows)
3. Start backend:
   - `bash scripts/start_system.sh`
4. Validate backend:
   - `bash scripts/validate_system.sh`

The canonical backend entrypoint used by wrappers is:
- `financial-engine_v2/scripts/run_local_backend.sh`

## Wrapper behavior (programmatic interface)
- `scripts/start_system.sh`
  - Checks `/api/health`; if backend is already reachable it exits successfully.
  - Otherwise starts `financial-engine_v2/scripts/run_local_backend.sh` in the background and rechecks health.
- `scripts/validate_system.sh`
  - Runs `scripts/agent_check.sh` and then `financial-engine_v2/scripts/smoke_local.sh` (if present/executable).
- `scripts/agent_check.sh`
  - Fast health probe for `${BASE_URL:-http://127.0.0.1:8000}/api/health`.

## Batch workflow runner (not system bootstrap)
- `python run.py`
  - Delegates to `financial-engine_v2/run.py`.
  - Runs configured ingestion workflows (full history and/or daily MarketIndex).
  - This is a workflow/batch entrypoint, not the canonical "backend is running" path.

## Legacy scripts
Old root scripts are archived under:
- `scripts/archive/legacy_root_20260218/`
