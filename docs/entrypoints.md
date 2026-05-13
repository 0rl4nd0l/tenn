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

#### Wrapper contract

| Wrapper | Primary use | Inputs | Success | Failure / skip behavior |
|---------|-------------|--------|---------|-------------------------|
| `scripts/agent_check.sh` | Fast health probe for automation. | `BASE_URL` (default `http://127.0.0.1:8000`), `TIMEOUT_SECONDS` (default `3`). | Exits `0` when `GET ${BASE_URL}/api/health` returns successfully. | Exits `1` when the backend is unreachable. |
| `scripts/start_system.sh` | Idempotent backend bootstrap. | `BASE_URL`, `START_WAIT_SECONDS` (default `1`), `LOG_FILE` (default `/tmp/tenn_backend.log`). | Exits `0` if the backend is already healthy or becomes healthy after launching `financial-engine_v2/scripts/run_local_backend.sh`. | Exits `1` and prints the log path if the launched backend is not reachable after the wait. |
| `scripts/validate_system.sh` | Post-start validation. | Uses `BASE_URL` through `scripts/agent_check.sh`. | Exits `0` when the healthcheck passes and the executable smoke script passes or is skipped. | Exits `1` if healthcheck or smoke fails. If `financial-engine_v2/scripts/smoke_local.sh` is missing or not executable, prints `SKIP` for smoke and preserves the healthcheck result. |
| `scripts/enforce_canonical.sh` | Heuristic diagnostics for agent startup drift. | `BASE_URL` (default `http://127.0.0.1:8000`). | Always exits `0`; prints OK/warning lines only. | Does not enforce or mutate runtime state. Warns when health is down, `python run.py` appears active, or no `uvicorn app.main:app` process is detected. |

#### API discovery

The backend is a FastAPI app mounted at `/api`. Use the generated OpenAPI document
as the source of truth for route discovery:

- Machine-readable schema: `GET /openapi.json`
- Interactive FastAPI docs: `GET /docs`
- TENN document listing endpoint: `GET /api/docs?ticker=BHP`

Do not confuse FastAPI's root `/docs` UI with TENN's `/api/docs` endpoint.

#### Troubleshooting

- `scripts/agent_check.sh` fails: confirm the backend is running and that `BASE_URL`
  matches the listener. In local isolated mode the default is `http://127.0.0.1:8000`.
- `scripts/start_system.sh` fails after launching: inspect `${LOG_FILE}` (default
  `/tmp/tenn_backend.log`) for import, dependency, database, or port-binding errors.
- `scripts/validate_system.sh` healthcheck passes but smoke fails: inspect
  `financial-engine_v2/scripts/smoke_local.sh`; it runs a one-year ticker backfill
  and then reads `/api/docs`, so provider/network or local data issues can fail it
  even when the API process is healthy.
- `scripts/enforce_canonical.sh` warns about `python run.py`: stop that process for
  agent startup work. `python run.py` is a batch workflow runner, not the canonical
  backend bootstrap path.
