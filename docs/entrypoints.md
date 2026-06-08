## Entrypoints (Agent Canon)

### Canonical Execution (ENFORCED)

`financial-engine_v2/scripts/run_local_backend.sh` is the **ONLY** canonical execution path for this repository.

All agents MUST use this path.

The canonical path starts the FastAPI backend in isolated local mode. It is the
right default when a task needs the system "up" and reachable for API checks.

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
- In isolated local mode, background work runs synchronously (`TASK_MODE=sync`) and persistence defaults to SQLite under `financial-engine_v2/data/`.
- Docker/Celery/Redis/Qdrant/Ollama are optional infrastructure paths, not the default agent boot surface.

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

### Wrapper Contract

| Script | Intent | Inputs | Success | Failure / notes |
|--------|--------|--------|---------|-----------------|
| `scripts/start_system.sh` | Idempotently start the canonical backend. | `BASE_URL` (default `http://127.0.0.1:8000`), `START_WAIT_SECONDS` (default `1`), `LOG_FILE` (default `/tmp/tenn_backend.log`). | Exits `0` when `scripts/agent_check.sh` can reach `${BASE_URL}/api/health`, either before or after starting the backend. | Exits `1` when health is still unreachable after starting. Inspect `LOG_FILE`. |
| `scripts/agent_check.sh` | Fast health probe for agents and wrappers. | `BASE_URL` (default `http://127.0.0.1:8000`), `TIMEOUT_SECONDS` (default `3`). | Exits `0` after `curl -fsS` reaches `${BASE_URL}/api/health`. | Exits `1` when the API is not reachable within the timeout. |
| `scripts/validate_system.sh` | Validate an already running backend. | Inherits `BASE_URL` / `TIMEOUT_SECONDS` for the health probe. | Exits `0` when health passes and `financial-engine_v2/scripts/smoke_local.sh` passes or is absent/non-executable. | Exits `1` if health or smoke fails. Missing/non-executable smoke is reported as `SKIP`, not failure. |
| `scripts/enforce_canonical.sh` | Heuristic guardrail for startup drift. | `BASE_URL` (default `http://127.0.0.1:8000`). | Always exits `0`; prints `OK`/`WARNING` messages only. | Warns about unreachable health, `python run.py` batch processes, or missing `uvicorn app.main:app`. Does not start/stop processes. |

`agent_contract.json` is intentionally small so automation can discover:

```json
{
  "canonical_entrypoint": "financial-engine_v2/scripts/run_local_backend.sh",
  "recommended_wrapper": "scripts/start_system.sh",
  "healthcheck": "/api/health",
  "validation": "scripts/validate_system.sh"
}
```

### Canonical Backend Defaults

`financial-engine_v2/scripts/run_local_backend.sh` changes into `financial-engine_v2/`,
requires `.venv/bin/python`, and then `exec`s:

```bash
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
```

The script exports local-safe defaults before starting Uvicorn:

| Setting | Default in canonical local mode | Why it matters |
|---------|---------------------------------|----------------|
| `PYTHONPATH` | `financial-engine_v2/backend` | Imports `app.main:app`. |
| `DATABASE_URL` | `sqlite:///./data/fe_local.db` | Avoids requiring Postgres for local agent checks. |
| `TASK_MODE` | `sync` | `/api/backfill/*` runs inline instead of enqueueing Celery work. |
| `AUTO_CREATE_TABLES` | `true` | Lets local SQLite bootstrap without Alembic. |
| `ENABLE_EMBEDDINGS` | `false` | Avoids requiring Ollama embeddings during smoke checks. |
| `ENABLE_QDRANT` | `false` | Avoids requiring Qdrant during smoke checks. |
| `ENABLE_EXTRACTION` | `false` | Avoids LLM extraction during smoke checks. |
| `ENABLE_MARKETINDEX_FALLBACK` | `true` | Enables the bundled MarketIndex fallback data path for local backfill. |

Override these only when the task explicitly needs the heavier subsystem. For
example, use `PORT=8010 BASE_URL=http://127.0.0.1:8010 bash scripts/start_system.sh`
to run the canonical backend on a non-default port.

### Smoke Workflow

The canonical smoke script exercises the public API surface that defines "up" for
agent work:

```bash
bash scripts/start_system.sh
bash scripts/validate_system.sh
```

`financial-engine_v2/scripts/smoke_local.sh` performs:

1. `GET /api/health` and expects a reachable JSON health response.
2. `POST /api/backfill/ticker/${TICKER}?years=1&process_documents=false`.
3. `GET /api/docs?ticker=${TICKER}` and prints the returned document count.

Use `TICKER=RIO bash scripts/validate_system.sh` to smoke a different ticker.

### Troubleshooting

| Symptom | Likely cause | Check / fix |
|---------|--------------|-------------|
| `Missing virtualenv at .../.venv` | Dependencies were not installed in `financial-engine_v2/.venv` (or the repo-root venv is not symlinked there). | Create or link the venv, then install `financial-engine_v2/backend/requirements.txt` and `financial-engine_v2/worker/requirements.txt`. |
| `backend not reachable after start` | Uvicorn failed during import/startup, or the port is already occupied by a different process. | Read `${LOG_FILE:-/tmp/tenn_backend.log}`; retry with a different `PORT` and matching `BASE_URL`. |
| `agent_check` fails but backend logs look healthy | `BASE_URL` does not match the port or host used to start Uvicorn. | Export the same `BASE_URL` for `start_system.sh`, `agent_check.sh`, and `validate_system.sh`. |
| Smoke fails during backfill | Provider/network/data dependency issue, not basic API startup. | Confirm `/api/health` first, then inspect the backfill response and local data files under `financial-engine_v2/data/`. |
| `python run.py` is running | A batch workflow was started instead of canonical backend startup. | Stop it if it is not part of the task, then use `bash scripts/start_system.sh`. |
