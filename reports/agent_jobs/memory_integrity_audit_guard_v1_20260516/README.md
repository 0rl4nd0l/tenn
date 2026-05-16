# Memory integrity audit guard v1

Status: completed; registry released.

## Scope

Extended `scripts/audit_memory_integrity.py`, a read-only JSON audit for active market-memory linked ticker invariants and fallback SQLite quarantine drift. The audit now also checks company-memory active rows for ticker-like company IDs, duplicate statement fanout, broad source fanout, and manual-review exclusions. `scripts/validate_system.sh` now runs the audit as a regular validation step when the local ignored memory DB files are present.

## Live audit result

- OK: `True`
- Issue count: `0`
- Active distinct linked tickers: `19`
- Active company-memory entries: `40`
- Company duplicate statement clusters: `0`
- Company source fanout clusters: `0`
- Invalid company IDs: `0`
- Fallback SQLite files: `0`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/memory_integrity_audit_guard_v1_20260516.md` -> passed
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/memory_integrity_audit_guard_v1_20260516.md` -> passed
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/memory_integrity_audit_guard_v1_20260516.md` -> passed
- `python3 scripts/agent_job_registry.py release memory_integrity_audit_guard_v1_20260516` -> passed
- `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest -q scripts/test_audit_memory_integrity.py` -> 6 passed
- `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m ruff check scripts/audit_memory_integrity.py scripts/test_audit_memory_integrity.py` -> passed
- `python3 -m py_compile scripts/audit_memory_integrity.py` -> passed
- `bash -n scripts/validate_system.sh` -> passed
- Live read-only audit with market/company/fallback checks -> passed
- `git diff --check` -> passed

Full `scripts/validate_system.sh` was not run because the existing smoke step performs a sync backfill; the memory-integrity command it wires in was run directly against the live read-only DB paths.
