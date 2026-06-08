# Current System

The active system is `financial-engine_v2`.

## Quick Start (backend API)
Use this when you need the backend service running and health-checkable.

1. Create venv at repo root (`/workspace/.venv`) and install dependencies:
   - `pip install -r requirements.txt`
   - `pip install -r financial-engine_v2/backend/requirements.txt`
2. Ensure `financial-engine_v2/.venv` resolves to that venv (symlink is commonly used in this repo).
3. Start the canonical backend:
   - `bash financial-engine_v2/scripts/run_local_backend.sh`
4. Validate:
   - `bash scripts/agent_check.sh`
   - Optional: `bash scripts/validate_system.sh`

Canonical entrypoint details and wrappers: `docs/entrypoints.md`.

## Batch Runner (not service bootstrap)
`python run.py` is a batch orchestration path. It delegates to `financial-engine_v2/run.py`
and runs configured workflows; it is **not** the canonical startup path for agent/system liveness.

Use it when you explicitly want batch workflow execution rather than "backend is running" semantics.

## Common Setup Pitfalls
- `run_local_backend.sh` expects `financial-engine_v2/.venv/bin/python`.
- `scripts/start_system.sh` default wait (`START_WAIT_SECONDS=1`) may be too short on slower hosts.
- `scripts/validate_system.sh` can report `SKIP` for smoke if `financial-engine_v2/scripts/smoke_local.sh` is missing or not executable.

## Legacy scripts
Old root scripts are archived under:
- `scripts/archive/legacy_root_20260218/`
