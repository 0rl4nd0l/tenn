# Current System

The active system is `financial-engine_v2`.

## Quick Start (agent/backend mode)
1. Create/activate your main venv at repo root.
2. Install dependencies:
   - `pip install -r requirements.txt`
   - `pip install -r financial-engine_v2/backend/requirements.txt`
3. Run:
   - `bash financial-engine_v2/scripts/run_local_backend.sh`
4. Validate:
   - `bash scripts/validate_system.sh`

This starts the FastAPI backend in isolated local mode. The system is considered
running when `GET /api/health` responds successfully.

## What `python run.py` does
- Delegates to `financial-engine_v2/run.py`
- Runs the configured workflows (full history and/or daily MarketIndex) from one command.
- Prints a warning because it is a batch runner, not the canonical backend
  startup path for agents.

## Legacy scripts
Old root scripts are archived under:
- `scripts/archive/legacy_root_20260218/`
