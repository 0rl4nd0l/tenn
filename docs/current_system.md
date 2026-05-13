# Current System

The active system is `financial-engine_v2`.

## Quick Start (after `git pull`)

Use this path when you want to run the configured batch workflows.

1. Create/activate your main venv at repo root.
2. Install dependencies:
   - `pip install -r requirements.txt`
   - `python -m playwright install chromium`
3. Run:
   - `python run.py`

## Canonical backend startup

Use the agent canonical path when the goal is to start and validate the FastAPI
backend API:

- Docs: `entrypoints.md`
- Start: `bash financial-engine_v2/scripts/run_local_backend.sh`
- Validate: `bash scripts/validate_system.sh`

## What `python run.py` does
- Delegates to `financial-engine_v2/run.py`
- Runs the configured workflows (full history and/or daily MarketIndex) from one command.
- It is a batch runner, not the backend API bootstrap path.

## Legacy scripts
Old root scripts are archived under:
- `scripts/archive/legacy_root_20260218/`
