---
job_id: issue250_market_data_staging_write_guard_current_base_v1_20260627
lane: Financial Truth
supporting_lanes:
  - Runtime
  - Reporting
  - Evaluation
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/issue250_market_data_staging_write_guard_current_base_v1_20260627.md
  - financial-engine_v2/backend/app/api/routes.py
  - financial-engine_v2/backend/tests/test_market_data_route_auth.py
  - docs/architecture/19_backend_api_surface.md
  - reports/agent_jobs/issue250_market_data_staging_write_guard_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue250_market_data_staging_write_guard_current_base_v1_20260627/STATE.md
  - reports/agent_jobs/issue250_market_data_staging_write_guard_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue250_market_data_staging_write_guard_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue250_market_data_staging_write_guard_current_base_v1_20260627/PR_BODY.md
  - reports/agent_jobs/issue250_market_data_staging_write_guard_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue250_market_data_staging_write_guard_current_base_v1_20260627/validation.json
  - reports/agent_jobs/issue250_market_data_staging_write_guard_current_base_v1_20260627/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/issue250_market_data_staging_write_guard_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_UPDATED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/architecture/19_backend_api_surface.md
  - issue #250
docs_changed:
  - docs/architecture/19_backend_api_surface.md
docs_followup: NONE
reason: "Issue #250 changes the access contract for market-data GET routes when OpenBB staging writes are enabled."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused backend route guard and financial-truth boundary tests."
worker_model_allowed: false
worker_decision_limit: "No workers used; the issue is narrow and backend-local."
escalation_needed: false
related_issue: 250
---

# Market Data Staging Write Guard

## Objective

Close issue #250 from current canonical by ensuring public market-data GET
routes cannot trigger OpenBB staging writes without the configured local API key.

## Existing Work Classification

- `CONTINUE`: current issue #250 is open and ready.
- `NO_MATCHING_ACTIVE_WORK_FOUND`: fresh guard preflight and focused GitHub
  duplicate checks found no active PR or branch for this exact issue.
- `PRESERVE`: market-data provider behavior and OpenBB staging models remain in
  place; this task only adds the operator boundary for write-capable GET paths.

## Scope

- Keep public GET behavior when `openbb_sidecar_enable_staging_writes` is false.
- When OpenBB staging writes are enabled, require the configured local API key
  before `/api/price` sidecar refresh or persistence.
- When OpenBB staging writes are enabled, require the configured local API key
  before `/api/fundamentals/profile`, `/summary`, or `/statements` sidecar
  refresh or persistence.
- Add focused tests proving missing/wrong keys are denied before provider and
  persistence helpers.
- Add focused tests proving matching keys preserve the sidecar + staging path.
- Update the backend API surface document.

## Hard Stops

- Do not mutate production DB, Qdrant, Redis, news stores, memory stores, source
  PDFs, extraction outputs, prompts, gold labels, runtime/model/GPU/service
  config, or production data.
- Do not promote OpenBB staging payloads into canonical ASX financial metrics.
- Do not replace backend-owned market data with a client-side provider or
  parallel truth path.
- Do not weaken existing API-key gates on ingestion, backfill, process, or
  analysis routes.
- Stop if implementation requires production data access or active ownership on
  `financial-engine_v2/backend/app/api/routes.py`.

## Validation

- Task-card validate.
- Registry overlap check and claim.
- Ledger claimed and implementation state entries.
- RED focused pytest before implementation.
- GREEN focused pytest after implementation.
- Targeted Ruff check for touched Python files.
- `python3 -m py_compile` on touched Python files.
- `git diff --check`.
- Task-card `check-diff`, `check-report-artifacts`, and `check-closeout`.
