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

`agent_contract.json` fields:

| Field | Value |
|---|---|
| `canonical_entrypoint` | `financial-engine_v2/scripts/run_local_backend.sh` |
| `recommended_wrapper` | `scripts/start_system.sh` |
| `healthcheck` | `/api/health` |
| `validation` | `scripts/validate_system.sh` |

### Wrapper contract

Run the wrappers from the repository root.

| Script | Inputs | Success | Failure |
|---|---|---|---|
| `scripts/agent_check.sh` | `BASE_URL` default `http://127.0.0.1:8000`. `TIMEOUT_SECONDS` default `3` (connect and max time). | HTTP success from `GET $BASE_URL/api/health`. Exit 0. | Any curl failure. Exit 1. |
| `scripts/start_system.sh` | `BASE_URL` as above. `START_WAIT_SECONDS` default `1`. `LOG_FILE` default `/tmp/tenn_backend.log`. | Existing health check passes, or the canonical backend becomes reachable after the wait. Exit 0. | Health check still fails after the wait. Exit 1. The backend process is left running; the log path is printed. |
| `scripts/validate_system.sh` | Same `BASE_URL` / `TIMEOUT_SECONDS` as `agent_check.sh`, plus smoke's `TICKER` (default `BHP`). | Health check passes. Smoke passes when `financial-engine_v2/scripts/smoke_local.sh` is executable. Exit 0. | Health check fails, or an executable smoke script fails. Exit 1. A missing or non-executable smoke script is a skip and does not by itself fail validation. |
| `scripts/enforce_canonical.sh` | `BASE_URL` default `http://127.0.0.1:8000`. | Always exits 0. Prints a warning when health fails, when `python run.py` is in the process list, or when `uvicorn app.main:app` is absent. | No hard failure. |

`financial-engine_v2/scripts/run_local_backend.sh` binds `0.0.0.0` on `PORT` (default `8000`) and requires an executable virtualenv at `financial-engine_v2/.venv/bin/python`. `scripts/start_system.sh` does not set `PORT`. Health checks use `BASE_URL` only. For a non-default port, set both to the same endpoint, for example `PORT=8001` and `BASE_URL=http://127.0.0.1:8001`.

`START_WAIT_SECONDS=1` is often too short for a cold import. If the wrapper reports failure while `LOG_FILE` shows uvicorn still starting, rerun with a larger wait. A failed start does not stop the background pid.

FastAPI's own schema UI is `GET /docs`. Ticker document listing is `GET /api/docs?ticker=...`. Smoke and `agent_check.sh` use the `/api/...` routes.

### Smoke routes

`financial-engine_v2/scripts/smoke_local.sh` calls, in order:

1. `GET /api/health`
2. `POST /api/backfill/ticker/$TICKER?years=1&process_documents=false`
3. `GET /api/docs?ticker=$TICKER`

Route behavior, including `GET /api/price`, is documented in `financial-engine_v2/README.md`.
