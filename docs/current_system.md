# Current System

The active runtime is `financial-engine_v2`.

## What Runs in Normal Agent Mode

Normal agent mode starts the FastAPI backend:

```bash
bash financial-engine_v2/scripts/run_local_backend.sh
```

That script runs `uvicorn app.main:app` from `financial-engine_v2/backend`,
with local-safe defaults:

- SQLite database: `sqlite:///./data/fe_local.db`
- synchronous task execution: `TASK_MODE=sync`
- automatic table creation: `AUTO_CREATE_TABLES=true`
- embeddings, Qdrant, and extraction disabled by default
- MarketIndex fallback enabled by default

The backend is considered up when this health route succeeds:

```bash
curl -sS http://127.0.0.1:8000/api/health
```

For the full startup contract, wrapper behavior, and troubleshooting map, see
`docs/entrypoints.md`.

## Quick Start After `git pull`

From the repository root:

```bash
python3 -m venv /workspace/.venv
/workspace/.venv/bin/pip install -r requirements.txt
/workspace/.venv/bin/pip install -r financial-engine_v2/backend/requirements.txt
test -e financial-engine_v2/.venv || ln -s /workspace/.venv financial-engine_v2/.venv
bash financial-engine_v2/scripts/run_local_backend.sh
```

Optional browser support for MarketIndex PDF downloads:

```bash
/workspace/.venv/bin/python -m playwright install chromium
```

Validate the backend:

```bash
bash scripts/agent_check.sh
bash scripts/validate_system.sh
```

## Public Backend Surface

FastAPI mounts routes from `financial-engine_v2/backend/app/api/routes.py` under
`/api`.

Common local checks:

```bash
curl -sS http://127.0.0.1:8000/api/health
curl -sS -X POST "http://127.0.0.1:8000/api/backfill/ticker/BHP?years=1&process_documents=false"
curl -sS "http://127.0.0.1:8000/api/docs?ticker=BHP"
```

## What `python run.py` Does

`python run.py` is a batch workflow runner, not the canonical backend startup
path for agents.

It delegates to `financial-engine_v2/run.py`, which reads the hardcoded
`CONFIG` block and runs one or more workflows:

- `full_history`
- `daily_marketindex`
- `daily_asx_marketwide`
- `both` (`full_history` plus `daily_marketindex`)

Use it only when the task is to run ingestion workflows. It may call external
providers and write reports under `financial-engine_v2/reports/`.

## Legacy Scripts

Old root scripts are archived under:

- `scripts/archive/legacy_root_20260218/`
