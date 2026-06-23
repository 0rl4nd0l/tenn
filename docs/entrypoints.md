## Entrypoints (Runtime Tasks Only)

This document is runtime context. Use it only when a task actually requires
starting, validating, or diagnosing the Tenn runtime.

Repo-hygiene, docs, task-card, hook, skill, registry, and report-only work
should not start services by default.

### Runtime Mode Contract

Tenn has three supported runtime modes. The mode names below are validated by
`scripts/runtime_entrypoint_contract.py` and mirrored in `agent_contract.json`.

#### Agent-Local Backend Mode

`financial-engine_v2/scripts/run_local_backend.sh` is the canonical backend
startup path for agent runtime tasks and focused backend validation. Use
`scripts/start_system.sh` when a task needs the agent-local backend to be
started or checked deterministically.

This mode starts the backend API only. It does not make Docker Compose or the
Cockpit browser UI the default agent runtime.

#### Full-Stack Cockpit Mode

`cockpit start new` is the canonical operator full-stack entrypoint. It starts
the Docker Compose infrastructure and launches the Next.js Cockpit UI at
`http://127.0.0.1:8081`. Use `docs/startup.md` for this mode.

This mode is supported for UI/full-system tasks, but it should not be used for
ordinary repo-hygiene, docs, task-card, hook, skill, registry, or report-only
work.

#### Batch Mode

`python run.py` is supported for batch workflow execution. It is not a system
bootstrap contract and does not define “the system is running.”

### Runtime Boot Sequence

1. Setup venv (canonical: `financial-engine_v2/.venv`).
   - Create: `python3 -m venv financial-engine_v2/.venv`
   - Activate (optional): `source financial-engine_v2/.venv/bin/activate`
2. Install dependencies (deterministic).
   - `pip install -r requirements.txt`
3. Run the Agent-Local Backend Mode.
   - `LOCAL_BACKEND_PROFILE=isolated bash financial-engine_v2/scripts/run_local_backend.sh`
4. Validate (smoke).
   - `bash financial-engine_v2/scripts/smoke_local.sh`
5. Confirm health.
   - `curl -sS http://127.0.0.1:8000/api/health`

### System Mental Model

- Core system = **FastAPI backend**.
- The system is considered **running** when the API is reachable (at least `/api/health`).

### Entrypoint Classification Table

| Entrypoint | Mode | Status | Description |
|------------|------|--------|------------|
| `financial-engine_v2/scripts/run_local_backend.sh` | Agent-Local Backend Mode | **CANONICAL FOR AGENTS** | Main execution path for focused backend/runtime validation. |
| `scripts/start_system.sh` | Agent-Local Backend Mode | **CANONICAL WRAPPER** | Starts or checks the local backend with bounded readiness. |
| `uvicorn app.main:app ...` | Agent-Local Backend Mode | **SUPPORTED** | Equivalent backend API start (prefer the canonical script). |
| `cockpit start new` | Full-Stack Cockpit Mode | **CANONICAL FOR OPERATORS** | Full Docker Compose infrastructure plus Next.js Cockpit UI on `http://127.0.0.1:8081`. |
| `financial-engine_v2/docker-compose.yml` | Full-Stack Cockpit Mode | **SUPPORTED INFRASTRUCTURE** | Compose file used by `scripts/cockpit` for Postgres/Redis/Qdrant/backend/worker. |
| `financial-engine_v2/scripts/cockpit_tui.py` / `python -m cockpit.main` | Full-Stack Cockpit Mode | **SUPPORTED UI** | Operator UI layer; depends on backend API and optional infra. |
| `python run.py` | Batch Mode | **SUPPORTED BATCH** | Batch orchestrator; not system bootstrap. |

### Avoid Unless Explicitly Required

Do not use these paths unless a task explicitly requires them:

- `python run.py`
  - Why: runs batch workflows and may depend on external providers/network; it does not define “system is running” (API up) deterministically.
- Cockpit UI (`financial-engine_v2/scripts/cockpit_tui.py`, `python -m cockpit.main`)
  - Why: adds an interactive UI layer and optional bootstrap behaviors; increases nondeterminism for agents.
- Full-Stack Cockpit Mode (`cockpit start new` / `docker compose ...`)
  - Why: adds Docker daemon, Postgres/Redis/Qdrant, host Ollama, and UI startup surface area.

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
  - Machine-readable pointers to the Agent-Local Backend Mode entrypoint,
    wrapper, healthcheck route, validation script, and supported runtime modes.

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

Last documented passing gate set; not rerun during the 2026-06-23 docs audit:
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
