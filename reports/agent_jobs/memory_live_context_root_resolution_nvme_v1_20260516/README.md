# Memory Live Context Root Resolution NVMe v1

## Decision

Proceedable patch produced; live deployment still pending.

This branch targets the NVMe live-runtime code line at `fast/dev-storage-v1-20260513-170304`. It adds deterministic research-memory root selection to `source_registry.py`:

- `TENN_RESEARCH_MEMORY_ROOT` explicit override, when set
- existing research-memory stores before writable fallback creation
- `DATA_ROOT/reports/research_memory`
- `financial-engine_v2/data/reports/research_memory`
- legacy `backend/reports/research_memory`

## Current Live Evidence

The currently running backend still reports empty memory context:

- `/api/context/memory/index` company entries: `0`
- `/api/context/memory/index` market items: `0`
- live company path: `/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2/backend/reports/research_memory/company_memory.sqlite`
- live market path: `/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2/backend/reports/research_memory/market_memory.sqlite`

The cleaned populated store remains at:

`/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/reports/research_memory`

Import/path probe with:

`TENN_RESEARCH_MEMORY_ROOT=/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/reports/research_memory`

resolved:

- `RESEARCH_MEMORY_ROOT` to the cleaned root
- `DEFAULT_COMPANY_MEMORY_PATH` to the cleaned company DB
- `DEFAULT_MARKET_MEMORY_PATH` to the cleaned market DB

## Validation

- `python3 scripts/agent_job_contract.py validate ... --write-report`: passed
- registry claim: passed
- focused pytest: `3 passed`
- ruff on touched files: passed
- `git diff --check`: passed
- live read-only endpoint check: still empty before deployment/restart

## Deployment Boundary

No live SQLite data was copied or rewritten in this task. No backend restart was performed because another active runtime task is registered against the live NVMe worktree.

To make this live safely:

1. Integrate this branch into the live NVMe runtime branch.
2. Set `TENN_RESEARCH_MEMORY_ROOT` in the shared host-local backend env to the cleaned store path.
3. Restart the backend through the canonical launcher after the active runtime task is clear.
4. Recheck `/api/context/memory/index`; expected counts should be nonzero.
5. Rerun the Anthropic answer-path smoke with nonempty contexts.
