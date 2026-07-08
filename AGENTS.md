# AGENTS.md

## Cursor Cloud specific instructions

### Project overview
TENN is a Python-based ASX financial data ingestion/extraction engine. The active runtime is `financial-engine_v2/`. See `README.md` and `financial-engine_v2/README.md` for full docs.

### Virtual environment
The venv lives at `/workspace/.venv` (symlinked into `financial-engine_v2/.venv` for `run_local_backend.sh`). Activate with `source /workspace/.venv/bin/activate` or invoke directly via `/workspace/.venv/bin/python`.

### Running the backend (local isolated mode, no Docker)
The simplest way to run the backend without Docker/Postgres/Redis:

```
cd /workspace/financial-engine_v2
PYTHONPATH=backend \
DATABASE_URL=sqlite:///./data/fe_local.db \
TASK_MODE=sync AUTO_CREATE_TABLES=true \
ENABLE_EMBEDDINGS=false ENABLE_QDRANT=false ENABLE_EXTRACTION=false \
ENABLE_MARKETINDEX_FALLBACK=true \
/workspace/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or use the convenience script: `financial-engine_v2/scripts/run_local_backend.sh` (requires `.venv` inside `financial-engine_v2/`).

Key local-mode defaults: SQLite DB at `data/fe_local.db`, sync task mode (no Celery/Redis), embeddings/extraction/Qdrant disabled.

### Running tests
```
cd /workspace/financial-engine_v2
PYTHONPATH=backend \
DATABASE_URL=sqlite:///./data/fe_test.db \
TASK_MODE=sync AUTO_CREATE_TABLES=true \
ENABLE_EMBEDDINGS=false ENABLE_QDRANT=false ENABLE_EXTRACTION=false \
/workspace/.venv/bin/python -m pytest scripts/ -v \
  --ignore=scripts/test_asx_provider_observability.py \
  --ignore=scripts/test_extraction_window_sampling.py
```

The two ignored test files have pre-existing import errors (reference symbols removed from the codebase). 12 additional failures are pre-existing (Celery config issues in isolated mode).

### Smoke test
```
curl http://127.0.0.1:8000/api/health
curl -X POST "http://127.0.0.1:8000/api/backfill/ticker/BHP?years=1&process_documents=false"
curl "http://127.0.0.1:8000/api/docs?ticker=BHP"
```

### Gotchas
- The `.env.example` in `financial-engine_v2/` targets Docker mode (Postgres URLs, `TASK_MODE=celery`). For local dev, override env vars as shown above or use `run_local_backend.sh`.
- Playwright Chromium is needed for MarketIndex PDF downloads. Install with: `/workspace/.venv/bin/python -m playwright install chromium`.
- No lint tooling (flake8/ruff/mypy) is configured in this repo. CI uses an external "Sloppy" scan tool; see `docs/sloppy_workflows.md` for scan/fix triggers, artifacts, and skip/fail-closed behavior.
- Tests live in `financial-engine_v2/scripts/test_*.py` (not a standard `tests/` directory). They use `unittest` and `pytest`, with `sys.path` manipulation to import from `backend/`.
