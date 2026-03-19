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
