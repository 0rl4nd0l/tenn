## Summary

- add startup diagnostics for entrypoint, task mode, DB class, and feature flags
- warn on direct/unknown startup with production-like runtime settings
- mark canonical local backend startup with `TENN_BACKEND_ENTRYPOINT=run_local_backend`
- add focused tests for diagnostics and the script marker

Closes #280.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/direct_startup_runtime_diagnostics_current_base_v3_20260627.md`
- `python3 scripts/agent_job_registry.py check-overlap --repo-root . docs/agent_tasks/direct_startup_runtime_diagnostics_current_base_v3_20260627.md`
- `uv run --with pytest pytest -q financial-engine_v2/backend/tests/test_startup_diagnostics.py scripts/test_run_local_backend_script.py`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/core/startup_diagnostics.py financial-engine_v2/backend/app/main.py financial-engine_v2/backend/tests/test_startup_diagnostics.py scripts/test_run_local_backend_script.py`
- `python3 -m py_compile financial-engine_v2/backend/app/core/startup_diagnostics.py financial-engine_v2/backend/app/main.py financial-engine_v2/backend/tests/test_startup_diagnostics.py scripts/test_run_local_backend_script.py`
- `bash -n financial-engine_v2/scripts/run_local_backend.sh`
- `git diff --check`

## Runtime Proof

Diagnostics/report-contract validation passed. Live backend startup, service
smoke checks, DB/Qdrant/Redis access, and runtime mutation were intentionally
not run. Runtime functionality status is `PARTIAL` until a future live startup
produces fresh logs with the new fields.
