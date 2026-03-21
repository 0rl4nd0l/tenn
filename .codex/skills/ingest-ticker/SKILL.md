---
name: ingest-ticker
description: Run full history ticker sync for one or more ASX tickers with argument validation, venv setup, and prerequisite checks.
---

# Ingest Ticker

Use this skill to run ticker-specific ingestion safely.

## Workflow

1. Validate ticker arguments are uppercase ASX-style symbols.
2. Check prerequisites:
   - backend health on `http://127.0.0.1:8000/api/health`
   - Qdrant reachable on `:6333`
   - llama.cpp reachable on `:8001/v1`
3. Use the project venv:

```bash
export PATH="/home/l4nd0/tenn/financial-engine_v2/.venv/bin:$PATH"
```

4. Run:

```bash
python scripts/full_history_ticker_sync.py --tickers <TICKER...>
```

5. Summarize per-ticker results.

## Constraints

- If prerequisites fail, report the missing service instead of continuing.
