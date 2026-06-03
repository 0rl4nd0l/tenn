# Current System

The active system is `financial-engine_v2`.

## Canonical local backend quick start

Use this path for deterministic agent/local validation:

1. Create or activate the Python environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
   - `pip install -r financial-engine_v2/backend/requirements.txt`
   - `python -m playwright install chromium` when MarketIndex headed recovery is needed.
3. Start the backend:
   - `bash financial-engine_v2/scripts/run_local_backend.sh`
4. Smoke test:
   - `bash financial-engine_v2/scripts/smoke_local.sh`
   - or `curl -sS http://127.0.0.1:8000/api/health`

See `docs/entrypoints.md` for the canonical entrypoint contract.

## What `python run.py` does

`python run.py` delegates to `financial-engine_v2/run.py` and runs configured batch workflows. It is supported as a batch runner, but it is **not** the canonical startup path for validating that the backend API is running.

## Local isolated backend defaults

`financial-engine_v2/scripts/run_local_backend.sh` sets safe local defaults:

- SQLite database: `financial-engine_v2/data/fe_local.db`
- `TASK_MODE=sync`
- `AUTO_CREATE_TABLES=true`
- `ENABLE_EMBEDDINGS=false`
- `ENABLE_QDRANT=false`
- `ENABLE_EXTRACTION=false`
- `ENABLE_MARKETINDEX_FALLBACK=true`
- `API_KEY=local-dev-key`
- `TENN_API_KEY=local-dev-key`

All non-health API routes require `X-API-Key` or `Authorization: Bearer ...`. The backend reads `API_KEY` first and falls back to `TENN_API_KEY` when `API_KEY` is unset.

MarketIndex fallback documents may be inserted but require headed-browser recovery before normal PDF processing.

## Cockpit UI status

In the current checkout, `cockpit-ui/` is not a tracked source tree. It contains build/cache artifacts such as `.next/`, `node_modules/`, and `test-results/`, but no tracked `package.json`, `app/`, `components/`, `lib/`, or test source.

Do not treat `cockpit-ui/.next` artifacts as editable source. Restore the Cockpit source tree before attempting frontend fixes.

See `docs/audit_and_cockpit_status.md` for the current audit and Cockpit route-surface findings.

## Legacy scripts

Old root scripts are archived under:

- `scripts/archive/legacy_root_20260218/`
