## Entrypoints (Agent Canon)

### Canonical Execution (ENFORCED)

`financial-engine_v2/scripts/run_local_backend.sh` is the **ONLY** canonical execution path for this repository.

All agents MUST use this path.

### Agent Boot Sequence (deterministic)

1. Setup venv (preferred: `/workspace/.venv`).
   - Create: `python3 -m venv /workspace/.venv`
   - Activate (optional): `source /workspace/.venv/bin/activate`
2. Install dependencies (deterministic).
   - `pip install -r requirements.txt`
   - `pip install -r financial-engine_v2/backend/requirements.txt`
3. Run the system (canonical).
   - `bash financial-engine_v2/scripts/run_local_backend.sh`
4. Validate (smoke).
   - `bash financial-engine_v2/scripts/smoke_local.sh`
5. Confirm health.
   - `curl -sS http://127.0.0.1:8000/api/health`

### System Mental Model

- Core system = **FastAPI backend**.
- The system is considered **running** when the API is reachable (at least `/api/health`).

### Entrypoint Classification Table

| Entrypoint | Status | Description |
|------------|--------|------------|
| `financial-engine_v2/scripts/run_local_backend.sh` | **CANONICAL** | Main execution path for agents (backend API in isolated mode). |
| `uvicorn app.main:app ...` | **SUPPORTED** | Equivalent backend API start (prefer the canonical script). |
| `financial-engine_v2/docker-compose.yml` | **SUPPORTED** | Full infrastructure mode (Postgres/Redis/Qdrant/worker; host Ollama expected). |
| `financial-engine_v2/scripts/cockpit_tui.py` / `python -m cockpit.main` | **SUPPORTED** | Operator UI layer; depends on backend API and optional infra. |
| `python run.py` | **SUPPORTED (batch)** | Batch orchestrator (runs workflows; not system bootstrap). |

### Prohibited Paths (for agents)

Agents MUST NOT use these paths unless a task explicitly requires them:

- `python run.py`
  - Why: runs batch workflows and may depend on external providers/network; it does not define “system is running” (API up) deterministically.
- Cockpit UI (`financial-engine_v2/scripts/cockpit_tui.py`, `python -m cockpit.main`)
  - Why: adds an interactive UI layer and optional bootstrap behaviors; increases nondeterminism for agents.
- Docker (`docker compose ...`)
  - Why: adds hidden dependencies (Docker daemon, Postgres/Redis/Qdrant, host Ollama) and longer startup surface area.

### Programmatic Interface

Use these wrappers for deterministic agent control:

- `scripts/start_system.sh`
  - Starts the canonical backend (if not already running), waits briefly, then runs `scripts/agent_check.sh`.
- `scripts/validate_system.sh`
  - Runs `scripts/agent_check.sh` and then `financial-engine_v2/scripts/smoke_local.sh` (when available).
- `agent_contract.json`
  - Machine-readable pointers to the canonical entrypoint, wrapper, healthcheck route, and validation script.

### Wrapper Contracts

| Wrapper | Intent | Inputs | Success | Failure / skip behavior |
|---------|--------|--------|---------|--------------------------|
| `scripts/agent_check.sh` | Check whether the backend API is reachable. | `BASE_URL` (default `http://127.0.0.1:8000`), `TIMEOUT_SECONDS` (default `3`). | Exits `0` after `GET /api/health` succeeds. | Exits `1` when the healthcheck cannot be reached. |
| `scripts/start_system.sh` | Idempotently start the canonical local backend for agents. | `BASE_URL`, `START_WAIT_SECONDS` (default `1`), `LOG_FILE` (default `/tmp/tenn_backend.log`). | Exits `0` if the API was already healthy or becomes healthy after launch. | Exits `1` and prints the backend PID/log path if healthcheck still fails. |
| `scripts/validate_system.sh` | Validate a running backend. | Inherits `BASE_URL` through `agent_check.sh`; uses `financial-engine_v2/scripts/smoke_local.sh` when executable. | Exits `0` only when healthcheck and executable smoke script pass. | Exits `1` on healthcheck or smoke failure; logs a smoke skip if the script is missing or not executable. |
| `scripts/enforce_canonical.sh` | Heuristic guardrail for humans/agents. | `BASE_URL`. | Always exits `0`; prints OK/warning messages only. | Does not mutate runtime state and does not hard-fail. |

### Local Backend Runtime Defaults

`financial-engine_v2/scripts/run_local_backend.sh` runs from `financial-engine_v2/`, sets `PYTHONPATH=backend`, and requires `.venv/bin/python` under `financial-engine_v2/`.

Defaults supplied by the script:

- SQLite database: `sqlite:///./data/fe_local.db`
- `TASK_MODE=sync`
- `AUTO_CREATE_TABLES=true`
- `ENABLE_EMBEDDINGS=false`
- `ENABLE_QDRANT=false`
- `ENABLE_EXTRACTION=false`
- `ENABLE_MARKETINDEX_FALLBACK=true`
- `PORT=8000` unless overridden

This means local smoke runs exercise discovery/download and API plumbing without requiring Celery, Redis, Postgres, Qdrant, Ollama extraction, or embeddings.

### API Smoke Surface

The canonical smoke path covers the public endpoints below:

```bash
curl -sS "${BASE_URL:-http://127.0.0.1:8000}/api/health"
curl -sS -X POST "${BASE_URL:-http://127.0.0.1:8000}/api/backfill/ticker/${TICKER:-BHP}?years=1&process_documents=false"
curl -sS "${BASE_URL:-http://127.0.0.1:8000}/api/docs?ticker=${TICKER:-BHP}"
```

Constraints verified from `backend/app/api/routes.py`:

- In sync mode, `/api/backfill/ticker/{ticker}` uppercases the ticker and passes `years` and `process_documents` into `backfill_ticker_sync`.
- In sync mode, `/api/backfill/asx20` loops across the `ASX20` universe with the same query parameters.
- In Celery mode, the API currently enqueues only ticker symbols for backfill tasks; query parameters are not forwarded to the queued task call.

### Troubleshooting

- **`Missing virtualenv at .../.venv`**: create the environment in `financial-engine_v2/` or ensure the repo-root venv is symlinked there, then install backend and worker requirements.
- **`agent_check` fails immediately after `start_system`**: inspect the `LOG_FILE` printed by `scripts/start_system.sh`; increase `START_WAIT_SECONDS` only if the backend is still booting.
- **Smoke backfill is slow or blocked**: the smoke script uses `process_documents=false`, so extraction/embeddings are not expected. Remaining delays usually come from provider/network behavior during discovery/download.
- **`python run.py` warning appears**: this is expected; `python run.py` is a batch workflow launcher, not the canonical agent startup path.
