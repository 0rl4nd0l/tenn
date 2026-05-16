# Smoke Sync Mode Gate v1

## Status

Implemented after the Evaluation lane blocker released.

The local smoke script now skips the mutating sync-backfill step by default and preserves the old strict behavior behind `SMOKE_REQUIRE_SYNC_BACKFILL=1`.

## Investigation Notes

Current code evidence:

- `financial-engine_v2/scripts/smoke_local.sh` requires `/api/backfill/ticker/{ticker}?years=1&process_documents=true` to return `{"mode": "sync", ...}`.
- `financial-engine_v2/backend/app/api/routes.py` returns `{"mode": "celery", ...}` from the same endpoint when `settings.task_mode` is not `sync`.
- `docs/architecture/08_backfill_contract.md` defines both sync and worker/celery response shapes as valid endpoint behavior.
- `financial-engine_v2/scripts/run_local_backend.sh` sets `TASK_MODE=sync` for isolated/full profiles unless an existing `TASK_MODE` override is present.

## Validation

Passed:
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/smoke_sync_mode_gate_v1_20260516.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/smoke_sync_mode_gate_v1_20260516.md`
- `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest scripts/test_smoke_local_mode_handling.py -q` (`3 passed`)
- `bash -n financial-engine_v2/scripts/smoke_local.sh`
- `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m ruff check scripts/test_smoke_local_mode_handling.py`
- `PATH=/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin:$PATH TENN_MEMORY_MARKET_DB=/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/reports/research_memory/market_memory.sqlite TENN_MEMORY_COMPANY_DB=/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/reports/research_memory/company_memory.sqlite TENN_MEMORY_FALLBACK_ROOT=/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/backend/reports/research_memory bash scripts/validate_system.sh`

Live `validate_system.sh` result:
- healthcheck: OK
- smoke: OK
- sync backfill: skipped by default
- docs endpoint: `BHP` count `138`
- RAG query: `3` hits
- cockpit routing smoke: skipped by default
- memory integrity: OK

Live memory gate evidence:
- active market linked ticker count: 37
- active company memory rows: 81
- fallback SQLite files: 0
- company duplicate statement fanout clusters: 0
- company source fanout clusters: 0

## Boundary

No backend route behavior, startup script behavior, live data, Qdrant, Postgres, financial truth, embeddings, or Cockpit UI behavior was changed.
