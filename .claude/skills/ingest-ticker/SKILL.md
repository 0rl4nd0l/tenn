---
name: ingest-ticker
description: Run full history ticker sync for one or more ASX tickers. Wraps full_history_ticker_sync.py with venv activation and argument validation.
disable-model-invocation: true
---

# Ingest Ticker

Runs `scripts/full_history_ticker_sync.py` for the specified ticker(s).

## Usage

```
/ingest-ticker <TICKER> [<TICKER2> ...]
```

Examples:
- `/ingest-ticker CBA`
- `/ingest-ticker CBA BHP WBC`

## What This Does

1. Activates the project venv
2. Validates that each ticker argument is uppercase alphanumeric (ASX format)
3. Runs `full_history_ticker_sync.py` with `--tickers` argument
4. Reports success/failure per ticker

## Steps to Execute

```bash
# Activate venv
export PATH="/home/l4nd0/tenn/financial-engine_v2/.venv/bin:$PATH"

# Validate ticker format (uppercase, 2-5 chars, letters only)
# Run sync
python scripts/full_history_ticker_sync.py --tickers <TICKER>
```

## Prerequisites

- Backend must be running (`curl -sS http://127.0.0.1:8000/api/health`)
- Qdrant must be reachable on `:6333` (full profile)
- llama.cpp must be running on `:8001/v1` for extraction

If prerequisites are not met, report which service is unreachable before attempting the sync.

## Expected Output

The script emits JSON run metadata including:
- `script` name
- `git_branch` / `git_commit`
- Per-ticker result: `documents_found`, `ingested`, `skipped`, `errors`

Surface the per-ticker summary to the user after completion.
