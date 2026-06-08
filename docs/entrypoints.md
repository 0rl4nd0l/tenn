## Entrypoints (Agent Canon)

### Canonical Execution (ENFORCED)

`financial-engine_v2/scripts/run_local_backend.sh` is the **ONLY** canonical execution path for this repository.

All agents MUST use this path.

### Agent Boot Sequence (deterministic)

1. Setup venv (preferred: `/workspace/.venv`).
   - Create: `python3 -m venv /workspace/.venv`
   - Activate (optional): `source /workspace/.venv/bin/activate`
2. Install dependencies (deterministic).
   - `/workspace/.venv/bin/pip install -r requirements.txt`
   - `/workspace/.venv/bin/python -m playwright install chromium` (required for MarketIndex download flows)
3. Run the system (canonical).
   - `bash scripts/start_system.sh`
4. Validate (smoke).
   - `bash scripts/validate_system.sh`
5. Confirm health.
   - `curl -sS http://127.0.0.1:8000/api/health`

Underlying canonical entrypoint used by wrappers:
- `financial-engine_v2/scripts/run_local_backend.sh`

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
  - Checks health first; exits quickly if backend is already running.
  - If unhealthy, starts `financial-engine_v2/scripts/run_local_backend.sh` in background and rechecks health.
  - Writes backend output to `${LOG_FILE:-/tmp/tenn_backend.log}`.
- `scripts/validate_system.sh`
  - Runs `scripts/agent_check.sh` and then `financial-engine_v2/scripts/smoke_local.sh`.
  - Returns non-zero if either step fails.
- `scripts/agent_check.sh`
  - Probes `${BASE_URL:-http://127.0.0.1:8000}/api/health` with short curl timeout defaults.
- `scripts/enforce_canonical.sh`
  - Heuristic warnings only (never hard-fails): reports non-canonical usage signals such as `python run.py`.
- `agent_contract.json`
  - Machine-readable pointers to the canonical entrypoint, wrapper, healthcheck route, and validation script.

### Troubleshooting quick checks

- Healthcheck failing:
  - `bash scripts/agent_check.sh`
  - If start was attempted, inspect `${LOG_FILE:-/tmp/tenn_backend.log}`.
- Wrong target host/port:
  - Override `BASE_URL`, e.g. `BASE_URL=http://127.0.0.1:8001 bash scripts/validate_system.sh`.
- Missing venv error from canonical script:
  - Create it at `/workspace/.venv` and ensure `financial-engine_v2/.venv` points to it as expected by the script.
