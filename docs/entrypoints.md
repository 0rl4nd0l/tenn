## Entrypoints (Runtime Tasks Only)

This document is runtime context. Use it only when a task actually requires
starting, validating, or diagnosing the Tenn runtime.

Repo-hygiene, docs, task-card, hook, skill, registry, and report-only work
should not start services by default.

### Canonical Runtime Execution

`financial-engine_v2/scripts/run_local_backend.sh` is the preferred backend
startup path when a task requires the local runtime.

### Runtime Boot Sequence

1. Setup venv (canonical: `financial-engine_v2/.venv`).
   - Create: `python3 -m venv financial-engine_v2/.venv`
   - Activate (optional): `source financial-engine_v2/.venv/bin/activate`
2. Install dependencies (deterministic).
   - `pip install -r requirements.txt`
3. Run the system (canonical).
   - `LOCAL_BACKEND_PROFILE=isolated bash financial-engine_v2/scripts/run_local_backend.sh`
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

### Avoid Unless Explicitly Required

Do not use these paths unless a task explicitly requires them:

- `python run.py`
  - Why: runs batch workflows and may depend on external providers/network; it does not define “system is running” (API up) deterministically.
- Cockpit UI (`financial-engine_v2/scripts/cockpit_tui.py`, `python -m cockpit.main`)
  - Why: adds an interactive UI layer and optional bootstrap behaviors; increases nondeterminism for agents.
- Docker (`docker compose ...`)
  - Why: adds hidden dependencies (Docker daemon, Postgres/Redis/Qdrant, host Ollama) and longer startup surface area.

### Programmatic Interface

Use these wrappers for deterministic agent control:

- `scripts/start_system.sh`
  - Starts the canonical backend (if not already running), then uses bounded readiness retries via `scripts/agent_check.sh`.
- `scripts/validate_system.sh`
  - Runs `scripts/agent_check.sh` and then `financial-engine_v2/scripts/smoke_local.sh` (when available).
  - Set `COCKPIT_VALIDATE_ROUTING_SMOKE=1` to also run `scripts/cockpit smoke routing` after the standard smoke checks.
- `scripts/prepare_cloud_worktree.sh`
  - Creates a clean sibling worktree from current `HEAD` for Cursor Cloud or isolated PR review without modifying the dirty main worktree.
- `agent_contract.json`
  - Machine-readable pointers to the canonical entrypoint, wrapper, healthcheck route, and validation script.

For Cursor Cloud branch and PR workflow, see `docs/cloud_workflow.md`.

### Stable Validation Baseline (2026-03-19)

Validated command sequence:
1. `bash scripts/start_system.sh`
2. `bash scripts/validate_system.sh`
3. `python -m ruff check autodev financial-engine_v2/backend scripts`
4. `pytest autodev/tests`
5. `pytest financial-engine_v2/backend/tests`
6. `pytest scripts`
7. `bash scripts/run_canonical_dataset_checks.sh`
8. `python scripts/check_canonical_regression.py --baseline reports/baselines/canonical_eval_baseline_latest.json --news-report reports/news_eval_report.json --company-report reports/company_eval_report_v2.json --reference-report reports/eval_queries_report.json`
9. `python scripts/validate_financial_metrics_gates.py reports/financial_metrics.json --out-json reports/financial_metrics.gates.json`
10. `python scripts/validate_financial_coverage_gates.py reports/financial_metrics.json --out-json reports/financial_metrics.coverage_gates.json`

Current passing gate set:
- Ruff on `autodev`, `financial-engine_v2/backend`, and `scripts`
- Pytest on `autodev/tests`, `financial-engine_v2/backend/tests`, and `scripts`
- Canonical dataset eval + baseline regression gate
- Financial metrics gate
- Financial coverage gate

Environment notes:
- In restricted socket environments, health/smoke checks may print `SKIP due restricted environment`; this is non-fatal and exit semantics are unchanged.
- Canonical dataset checks support CPU fallback by default (`REQUIRE_CUDA=0`) and only hard-require GPU when `REQUIRE_CUDA=1`.
- Canonical regression fixtures that must exist:
  - `reports/baselines/canonical_eval_baseline_latest.json`
  - `reports/news_eval_queries.json`
  - `reports/company_eval_queries.json`
  - `reports/eval_queries.json`

Detailed runbook: `docs/validation_baseline.md`.
