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
- `scripts/agent_check.sh`
  - Single health probe against `${BASE_URL}/api/health`.
- `scripts/enforce_canonical.sh`
  - Heuristic warnings only. It always exits `0` and never starts or stops the backend.
- `agent_contract.json`
  - Machine-readable pointers to the canonical entrypoint, wrapper, healthcheck route, and validation script.

### Wrapper contract

| Wrapper | Inputs / defaults | Success | Failure |
| --- | --- | --- | --- |
| `financial-engine_v2/scripts/run_local_backend.sh` | Requires `financial-engine_v2/.venv/bin/python`. `PORT=8000`. Isolated defaults: SQLite `data/fe_local.db`, `TASK_MODE=sync`, `AUTO_CREATE_TABLES=true`, embeddings/Qdrant/extraction off, MarketIndex fallback on. | `exec`s uvicorn (does not return). | Exit `1` if `.venv` is missing. |
| `scripts/start_system.sh` | `BASE_URL=http://127.0.0.1:8000`, `START_WAIT_SECONDS=1`, `LOG_FILE=/tmp/tenn_backend.log`. | Exit `0` if `/api/health` is already up, or becomes reachable after the wait. | Exit `1` if the backend is still unreachable after start. |
| `scripts/agent_check.sh` | `BASE_URL=http://127.0.0.1:8000`, `TIMEOUT_SECONDS=3`. | Exit `0` when `GET ${BASE_URL}/api/health` succeeds. | Exit `1` when the probe fails. |
| `scripts/validate_system.sh` | Uses `agent_check.sh` then `smoke_local.sh` if that script is executable. | Exit `0` when health passes and smoke passes or is skipped. | Exit `1` if health or smoke fails. |
| `financial-engine_v2/scripts/smoke_local.sh` | `BASE_URL=http://127.0.0.1:8000`, `TICKER=BHP`. Hits health, ticker backfill (`years=1&process_documents=false`), then `/api/docs`. | Exit `0` when all three curl steps succeed. | Non-zero from `set -e` / curl failures. |

`run_local_backend.sh` binds uvicorn with `--port "${PORT:-8000}"`. Health wrappers and smoke use `BASE_URL`, not `PORT`. If you change the listen port, set both:

```bash
PORT=9000 BASE_URL=http://127.0.0.1:9000 bash scripts/start_system.sh
PORT=9000 BASE_URL=http://127.0.0.1:9000 bash scripts/validate_system.sh
```

`START_WAIT_SECONDS` defaults to `1`. That is often too short for a cold uvicorn start; raise it if `start_system.sh` reports "backend not reachable after start" while the process is still booting. The backend log is `/tmp/tenn_backend.log` unless `LOG_FILE` is set.

### Public API (isolated backend)

`financial-engine_v2/backend/app/main.py` mounts `app.api.routes` at `/api`. FastAPI's own Swagger UI remains at `/docs` and the schema at `/openapi.json`. Do not confuse Swagger `/docs` with ticker document listing `/api/docs`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness. Returns `{"status":"ok"}`. |
| `GET` | `/api/docs?ticker=BHP` | Documents for a ticker, newest `published_at` first. |
| `GET` | `/api/financials?ticker=BHP` | Periodic financial rows for a ticker. |
| `GET` | `/api/risk?document_id=...` | Risk/guidance note for one document; missing rows return null summaries. |
| `GET` | `/api/price?ticker=BHP` | Yahoo-backed price snapshot plus history. Optional `range` (default `1mo`), `interval` (default `1d`), `exchange` (default `ASX`). |
| `POST` | `/api/backfill/asx20` | Backfill ASX20. Query: `years` (default `1`), `process_documents` (default `false`). |
| `POST` | `/api/backfill/ticker/{ticker}` | Backfill one ticker. Same query params as ASX20. |

`/api/price` maps exchange suffixes in `MarketPriceProvider`: `ASX` → `.AX`, `LSE` → `.L`, `TSX` → `.TO`, `HKEX` → `.HK`; `NYSE`/`NASDAQ` use the bare ticker. If `ticker` already contains a `.`, no suffix is added. Empty ticker/range/interval returns HTTP 400; provider/network failures return HTTP 502. Isolated local mode does not need this route for smoke tests.

Backfill uses `TASK_MODE`: `sync` runs `backfill_ticker_sync` inline; otherwise the API enqueues Celery `backfill_ticker` tasks. Canonical isolated mode is `TASK_MODE=sync`.

### Troubleshooting

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| `Missing virtualenv at financial-engine_v2/.venv` | Canonical script requires a venv inside `financial-engine_v2/` | Create it or symlink `/workspace/.venv` → `financial-engine_v2/.venv`. |
| Health check hits the wrong port | `PORT` and `BASE_URL` diverged | Set both to the same host/port. |
| `start_system.sh` exits 1 immediately | Default 1s wait, or backend crashed | Read `LOG_FILE`; increase `START_WAIT_SECONDS`. |
| `enforce_canonical.sh` "passed" but API is down | That script never fails | Use `scripts/agent_check.sh` or `scripts/validate_system.sh`. |
| Swagger `/docs` vs empty ticker docs | Wrong path | Use `/api/docs?ticker=BHP` for stored documents. |

