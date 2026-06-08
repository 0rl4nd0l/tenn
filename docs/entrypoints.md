## Entrypoints (Agent Canon)

This page defines the deterministic startup contract for agents and
automation. It is verified against:

- `agent_contract.json`
- `financial-engine_v2/scripts/run_local_backend.sh`
- `scripts/start_system.sh`
- `scripts/agent_check.sh`
- `scripts/validate_system.sh`
- `scripts/enforce_canonical.sh`

### Canonical Execution (ENFORCED)

`financial-engine_v2/scripts/run_local_backend.sh` is the canonical
execution path for agents.

The system is considered **running** when the FastAPI backend is reachable at
`/api/health`.

### Agent Boot Sequence

From the repository root:

```bash
python3 -m venv /workspace/.venv
/workspace/.venv/bin/pip install -r requirements.txt
/workspace/.venv/bin/pip install -r financial-engine_v2/backend/requirements.txt
test -e financial-engine_v2/.venv || ln -s /workspace/.venv financial-engine_v2/.venv
bash financial-engine_v2/scripts/run_local_backend.sh
```

Validate from another terminal:

```bash
bash scripts/agent_check.sh
bash scripts/validate_system.sh
curl -sS http://127.0.0.1:8000/api/health
```

### System Mental Model

- Core system = **FastAPI backend** (`financial-engine_v2/backend/app/main.py`).
- FastAPI mounts public routes from `app.api.routes` under `/api`.
- Local agent mode uses SQLite, synchronous tasks, and disabled
  extraction/embedding/vector-store work by default.
- `python run.py` is a batch workflow runner, not the API startup path.

### Entrypoint Classification

| Entrypoint | Status | Use |
|------------|--------|-----|
| `financial-engine_v2/scripts/run_local_backend.sh` | **CANONICAL** | Starts the backend API in isolated local mode. |
| `scripts/start_system.sh` | **RECOMMENDED WRAPPER** | Starts the canonical backend only when `/api/health` is not already reachable. |
| `scripts/agent_check.sh` | **HEALTHCHECK** | Checks `${BASE_URL}/api/health` and exits non-zero on failure. |
| `scripts/validate_system.sh` | **VALIDATION** | Runs `agent_check.sh`, then `financial-engine_v2/scripts/smoke_local.sh` if executable. |
| `scripts/enforce_canonical.sh` | **ADVISORY GUARDRAIL** | Emits warnings about non-canonical state; always exits `0`. |
| `uvicorn app.main:app ...` | **SUPPORTED** | Equivalent manual backend start when using the same env as the canonical script. |
| `financial-engine_v2/docker-compose.yml` | **SUPPORTED** | Full infrastructure mode with Postgres/Redis/Qdrant/worker; not the agent default. |
| `financial-engine_v2/scripts/cockpit_tui.py` / `python -m cockpit.main` | **SUPPORTED UI** | Operator UI layer; depends on the backend API and optional infrastructure. |
| `python run.py` | **SUPPORTED BATCH** | Runs configured ingestion workflows; does not define "system is running." |

### Wrapper Contracts

| Script | Inputs | Success | Failure / notes |
|--------|--------|---------|-----------------|
| `financial-engine_v2/scripts/run_local_backend.sh` | `PORT` (default `8000`), `DATABASE_URL` (default local SQLite), `TASK_MODE` (default `sync`), feature flags such as `ENABLE_EMBEDDINGS=false`, `ENABLE_QDRANT=false`, `ENABLE_EXTRACTION=false` | Replaces the shell with `uvicorn app.main:app --host 0.0.0.0 --port ${PORT}` | Requires `financial-engine_v2/.venv/bin/python` and `.venv/bin/uvicorn`; in Cursor Cloud this is usually a symlink to `/workspace/.venv`. |
| `scripts/start_system.sh` | `BASE_URL` (default `http://127.0.0.1:8000`), `START_WAIT_SECONDS` (default `1`), `LOG_FILE` (default `/tmp/tenn_backend.log`), and `PORT` when using a non-default backend port | Exits `0` if backend was already healthy or becomes healthy after start | Starts `run_local_backend.sh` in the background, then fails with the backend PID and log path if health is still unavailable. For non-default ports, set `PORT` and make `BASE_URL` point at the same port. |
| `scripts/agent_check.sh` | `BASE_URL` (default `http://127.0.0.1:8000`), `TIMEOUT_SECONDS` (default `3`) | Prints reachable healthcheck and exits `0` | Exits `1` when `${BASE_URL}/api/health` is not reachable within timeout. |
| `scripts/validate_system.sh` | Same health inputs as `agent_check.sh`; optional executable `financial-engine_v2/scripts/smoke_local.sh` | Exits `0` when health succeeds and smoke succeeds or is skipped because the smoke script is missing/not executable | Exits `1` if health or smoke fails. |
| `scripts/enforce_canonical.sh` | `BASE_URL` (default `http://127.0.0.1:8000`) | Always exits `0` | Warns when health is down, `python run.py` is detected, or no `uvicorn app.main:app` process is detected. It does not mutate runtime state. |

### Public API Surface Used by Smoke Tests

The canonical smoke path depends on these routes from
`financial-engine_v2/backend/app/api/routes.py`:

```text
GET  /api/health
POST /api/backfill/ticker/{ticker}?years=1&process_documents=false
GET  /api/docs?ticker={ticker}
```

Other public routes currently exposed by the same router:

```text
GET  /api/financials?ticker={ticker}
GET  /api/risk?document_id={document_id}
GET  /api/price?ticker={ticker}&range=1mo&interval=1d&exchange=ASX
POST /api/backfill/asx20?years=1&process_documents=false
```

### Troubleshooting

| Symptom | Check | Likely fix |
|---------|-------|------------|
| `Missing virtualenv at .../.venv` | `test -x financial-engine_v2/.venv/bin/python` | Create or symlink the venv, then install backend requirements. |
| `agent_check` fails | `curl -sS http://127.0.0.1:8000/api/health` | Start with `bash scripts/start_system.sh` or inspect the log named by `LOG_FILE`. |
| Smoke backfill hangs or reaches external providers | Confirm `TASK_MODE=sync` and `process_documents=false` | Use the canonical script defaults for isolated local checks. |
| Agent started `python run.py` | `bash scripts/enforce_canonical.sh` | Stop the batch runner unless the task explicitly requires workflow ingestion. |
| Docker/Cockpit path is tempting | Compare against this table | Use only for tasks that explicitly need full infrastructure or operator UI behavior. |
