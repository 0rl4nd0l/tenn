# Memory Signal Router Fanout Guard v1

Lane: Memory
Branch: preserve/dirty-work-20260430T065748Z
Worktree: /mnt/sdb2/home/l4nd0/tenn
Execution mode: SAFE EXTENSION MODE after preflight audit
Contested surfaces touched: financial-engine_v2/backend/app/services/memory_signal_router.py
Collision risk: MEDIUM
Decision: proceed

## Scope

This change implements the smallest safe router/write-path guard for new company-memory writes from commentary/news memos.

Exact root cause addressed: `memory_signal_router.py` previously applied one memo-level ticker list to every extracted statement, so one multi-company memo could write each statement into every ticker scope before `CompanyMemoryStore` persisted it.

## Files Changed

- financial-engine_v2/backend/app/services/memory_signal_router.py
- financial-engine_v2/backend/tests/test_memory_signal_router.py
- reports/memory_signal_router_fanout_guard_20260505_164348/*

## Result

- The existing strict xfail was converted to a passing regression test.
- Single-company memo behavior remains covered and passing.
- Ambiguous multi-ticker memo statements no longer emit company-memory writes.
- Existing sector/macro market-memory routing remains available for supported market statements.
- Historical contaminated rows were not touched.

## Validation

Required validation passed:

```bash
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_memory_signal_router.py -q
# 12 passed in 0.73s

financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/services/memory_signal_router.py financial-engine_v2/backend/tests/test_memory_signal_router.py
# All checks passed!

git diff --check
# passed
```

Adjacent focused validation passed:

```bash
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_company_memory.py financial-engine_v2/backend/tests/test_market_memory.py -q
# 33 passed in 1.22s
```

