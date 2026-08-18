# Validation

## Passed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/direct_startup_runtime_diagnostics_current_base_v3_20260627.md`
- `python3 scripts/agent_job_registry.py check-overlap --repo-root . docs/agent_tasks/direct_startup_runtime_diagnostics_current_base_v3_20260627.md`
- `uv run --with pytest pytest -q financial-engine_v2/backend/tests/test_startup_diagnostics.py scripts/test_run_local_backend_script.py`
  - Result: `4 passed, 1 warning`
  - Warning: pytest config option `asyncio_default_fixture_loop_scope` unknown in the ephemeral pytest environment
- `uv run --with ruff ruff check financial-engine_v2/backend/app/core/startup_diagnostics.py financial-engine_v2/backend/app/main.py financial-engine_v2/backend/tests/test_startup_diagnostics.py scripts/test_run_local_backend_script.py`
- `python3 -m py_compile financial-engine_v2/backend/app/core/startup_diagnostics.py financial-engine_v2/backend/app/main.py financial-engine_v2/backend/tests/test_startup_diagnostics.py scripts/test_run_local_backend_script.py`
- `bash -n financial-engine_v2/scripts/run_local_backend.sh`
- `git diff --check`

## Not Run

- Live backend startup, service smoke checks, DB/Qdrant/Redis access, or runtime
  mutation. These were hard-stopped by task scope.
