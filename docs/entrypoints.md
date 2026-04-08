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

### Wrapper Contracts (source: scripts/)

| Interface | Purpose | Inputs / knobs | Success criteria | Failure behavior |
|-----------|---------|----------------|------------------|------------------|
| `scripts/agent_check.sh` | Fast liveness gate | `BASE_URL` (default `http://127.0.0.1:8000`), `TIMEOUT_SECONDS` (default `3`) | `GET ${BASE_URL}/api/health` succeeds via `curl -fsS` | exits `1` when health is not reachable in timeout |
| `scripts/start_system.sh` | Idempotent startup wrapper | `BASE_URL`, `START_WAIT_SECONDS` (default `1`), `LOG_FILE` (default `/tmp/tenn_backend.log`) | returns `0` when backend is already healthy or becomes healthy after start | exits `1` when health is still unavailable after wait |
| `scripts/validate_system.sh` | Composite validation | Uses `scripts/agent_check.sh`; optional `financial-engine_v2/scripts/smoke_local.sh` | returns `0` when healthcheck passes and smoke passes (or smoke is skipped) | exits `1` if healthcheck fails or smoke fails |
| `scripts/enforce_canonical.sh` | Heuristic warning layer | `BASE_URL` | always returns `0` after printing warnings/OK checks | **warning-only** by design (no hard fail) |
| `agent_contract.json` | Machine-readable pointers | n/a | fields resolve to canonical startup and validation artifacts | stale values can desync automation; verify against scripts during updates |

### Deterministic Automation Workflow

Use this sequence for non-interactive runs:

1. Start or confirm backend:
   - `bash scripts/start_system.sh`
2. Validate health + smoke:
   - `bash scripts/validate_system.sh`
3. (Optional) diagnostics-only enforcement hints:
   - `bash scripts/enforce_canonical.sh`

Concrete overrides:

```bash
BASE_URL="http://127.0.0.1:8000" START_WAIT_SECONDS=4 LOG_FILE="/tmp/tenn_backend.log" \
  bash scripts/start_system.sh

BASE_URL="http://127.0.0.1:8000" TIMEOUT_SECONDS=5 \
  bash scripts/agent_check.sh
```

### Setup and Pitfalls

- `financial-engine_v2/scripts/run_local_backend.sh` expects a venv at `financial-engine_v2/.venv`.
  - In this repo, `/workspace/.venv` is typically symlinked into `financial-engine_v2/.venv`.
- `START_WAIT_SECONDS=1` is intentionally aggressive.
  - On slower hosts, increase it (for example `START_WAIT_SECONDS=4`) before treating startup as failed.
- `validate_system.sh` does **not** fail when smoke script is missing/non-executable.
  - It logs `SKIP` and preserves current pass/fail state from health + smoke outcomes.
- `financial-engine_v2/scripts/smoke_local.sh` uses `python3` in step `3/3` for JSON shaping.
  - If `python3` is missing in `PATH`, smoke can fail even with a healthy API.

### Troubleshooting Map

| Symptom | Check | Typical cause | Fix |
|---------|-------|---------------|-----|
| `start_system.sh` returns `FAIL: backend not reachable after start` | inspect `LOG_FILE` (`/tmp/tenn_backend.log`) | backend startup error or wait window too short | fix logged startup error; retry with higher `START_WAIT_SECONDS` |
| `agent_check.sh` fails immediately | `curl "${BASE_URL}/api/health"` | wrong `BASE_URL`/port, service not running | correct `BASE_URL` or start backend via canonical script |
| `validate_system.sh` health OK but smoke FAIL | run `financial-engine_v2/scripts/smoke_local.sh` directly | backfill/docs endpoint issue or missing local prerequisites | resolve endpoint/data issue, then rerun validate |
| `enforce_canonical.sh` prints warnings in healthy system | inspect process checks (`python run.py`, `uvicorn app.main:app`) | heuristic process matching, mixed workloads | treat as advisory; rely on `start_system` + `validate_system` for gating |
