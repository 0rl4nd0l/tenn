## Entrypoints

### Canonical Execution

`financial-engine_v2/scripts/run_local_backend.sh` is the canonical local backend entrypoint for agents and reconciliation work.

### Preferred Boot Sequence

1. Ensure the project virtual environment exists and dependencies are installed.
2. Run `bash financial-engine_v2/scripts/run_local_backend.sh`.
3. Confirm health with `curl -sS http://127.0.0.1:8000/api/health`.
4. Run `bash financial-engine_v2/scripts/smoke_local.sh` when available.

### Supported Helper Scripts

- `scripts/start_system.sh`
  - Starts the canonical backend only if it is not already healthy.
- `scripts/validate_system.sh`
  - Runs the health check and local smoke script.

These helpers wrap the canonical launcher; they do not replace it.

### Supported But Non-Canonical Paths

- `uvicorn app.main:app ...`
  - Equivalent backend startup for debugging, but prefer the canonical script.
- `python run.py`
  - Batch workflow entrypoint, not the canonical definition of "system is running" for agent work.

### Prohibited For Routine Agent Bootstrap

- Cockpit UI / TUI paths as the primary way to decide backend readiness.
- Broad Docker bootstrap when the task only needs the local backend.
- Any alternate launcher that bypasses `financial-engine_v2/scripts/run_local_backend.sh` without a task-specific reason.

### Validation Baseline For Conservative Reconciliation

Use the smallest relevant validation after each small changeset:

1. `bash scripts/validate_system.sh` for launcher/runtime changes.
2. `curl -sS http://127.0.0.1:8000/api/health` for backend availability.
3. Targeted `pytest` or `python -m py_compile` for isolated code additions.

Avoid claiming a full baseline unless it was actually run in the current session.
