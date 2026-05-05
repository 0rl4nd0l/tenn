# Validation

## Baseline Before Fix

```bash
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_memory_signal_router.py -q
```

Result:

```text
7 passed, 1 xfailed in 4.25s
```

```bash
financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/services/memory_signal_router.py financial-engine_v2/backend/tests/test_memory_signal_router.py
```

Result:

```text
All checks passed!
```

## Required Validation After Fix

```bash
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_memory_signal_router.py -q
```

Result:

```text
12 passed in 0.73s
```

```bash
financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/services/memory_signal_router.py financial-engine_v2/backend/tests/test_memory_signal_router.py
```

Result:

```text
All checks passed!
```

```bash
git diff --check
```

Result: passed with no output.

## Adjacent Focused Validation

```bash
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_company_memory.py financial-engine_v2/backend/tests/test_market_memory.py -q
```

Result:

```text
33 passed in 1.22s
```

## Live State

No live memory store, live database, ingestion pipeline, Qdrant index, or cleanup script was mutated or invoked.

