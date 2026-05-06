# Validation

## Focused Pair

Command:

```text
PYTHONPATH=financial-engine_v2/backend:financial-engine_v2 financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_query_orchestrator.py financial-engine_v2/backend/tests/test_sources.py -q
```

Result:

```text
38 passed in 1.28s
```

## Broad Backend Selector

Command:

```text
PYTHONPATH=financial-engine_v2/backend:financial-engine_v2 financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests -k "query_orchestrator or source or evidence or label or no_hit or degraded or a2m or financial_truth or memory" -q
```

Result:

```text
339 passed, 1153 deselected, 6 warnings in 10.57s
```

Warnings were dependency/deprecation warnings from `requests`, `pydantic`, and FastAPI startup/shutdown decorators; no test failures.

## Ruff

Command:

```text
financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/services/query_orchestrator.py financial-engine_v2/backend/tests/test_query_orchestrator.py financial-engine_v2/backend/tests/test_sources.py
```

Result:

```text
All checks passed!
```

## Diff Check

Command:

```text
git diff --check
```

Result: passed with no output.
