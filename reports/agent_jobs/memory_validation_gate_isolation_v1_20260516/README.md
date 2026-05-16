# Memory Validation Gate Isolation v1

## Summary

Extracted memory integrity validation from `scripts/validate_system.sh` into `scripts/validate_memory_integrity.sh`.

The regular system validation path still runs memory integrity as step 4, but the memory gate can now be executed directly without requiring the backend runtime smoke to pass.

## Validation

Passed:
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/memory_validation_gate_isolation_v1_20260516.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/memory_validation_gate_isolation_v1_20260516.md`
- `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest scripts/test_validate_system_routing_smoke.py scripts/test_validate_memory_integrity_script.py -q` (`7 passed`)
- `bash -n scripts/validate_system.sh && bash -n scripts/validate_memory_integrity.sh`
- `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m ruff check scripts/test_validate_system_routing_smoke.py scripts/test_validate_memory_integrity_script.py`
- `TENN_MEMORY_MARKET_DB=/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/reports/research_memory/market_memory.sqlite TENN_MEMORY_COMPANY_DB=/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/reports/research_memory/company_memory.sqlite TENN_MEMORY_FALLBACK_ROOT=/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/backend/reports/research_memory scripts/validate_memory_integrity.sh`
- `git diff --check`

Partial:
- `PATH=/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin:$PATH ... bash scripts/validate_system.sh`
  - healthcheck passed
  - memory integrity step passed through `scripts/validate_memory_integrity.sh`
  - overall script exited 1 because `financial-engine_v2/scripts/smoke_local.sh` reported `Backend not running in sync mode`

## Boundary

No backend endpoint behavior, live memory database content, memory write path, retrieval, Qdrant, Postgres, financial truth, embeddings, Cockpit UI, or `financial-engine_v2/scripts/smoke_local.sh` behavior was changed.
